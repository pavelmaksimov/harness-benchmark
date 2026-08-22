"""Rework loop hook: when a checkpoint's tests fail, send the task back to
the agent with explicit feedback instead of stopping the trajectory.

Flow inside one SCB checkpoint:

1. ``AgentRunner._run_checkpoint`` runs solve + eval as usual.
2. If the eval failed the pass policy (Core tests), the hook re-invokes
   ``_run_checkpoint`` for the *same* checkpoint with the original prompt
   plus a ``[REWORK ATTEMPT N]`` feedback block listing the failing tests.
   The workspace keeps the previous attempt's code, so the agent fixes
   in place.
3. Each attempt re-evaluates; the loop stops when an attempt passes, when
   the agent errors / hits the rate limit, when the evaluation is an
   infrastructure failure (bench problem, not a model defect — see the
   failure-triage rule), or when ``max_attempts`` extra attempts are used.
4. Per-attempt outcomes are persisted to ``<checkpoint>/rework.json``;
   the harness-side ``benchmark/rework.py`` turns them into failure records
   and run-level statistics.

The hook is installed from ``benchmark/scb_main.py`` and
``harness_sitecustomize`` (so ProcessPool workers get it too) when
``HB_REWORK_ATTEMPTS`` is set to a positive integer.  The patch is a
runtime monkeypatch on the vendored SCB runner — the vendor tree itself
stays untouched (see benchmark-core rule: prefer overrides over forks).
"""

from __future__ import annotations

import functools
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("hb.rework")

REWORK_FILENAME = "rework.json"
HB_REWORK_ATTEMPTS = "HB_REWORK_ATTEMPTS"
_KNOWN_GROUPS = ("Core", "Functionality", "Error", "Regression")

_INSTALLED = False


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _token_field(usage: dict[str, Any], *keys: str) -> int | None:
    """Read token counts from both flat and nested adapter usage shapes."""
    for key in keys:
        if key in usage and usage[key] is not None:
            return int(usage[key])
    tokens = usage.get("net_tokens") or usage.get("current_tokens") or {}
    if isinstance(tokens, dict):
        aliases = {
            "input_tokens": "input",
            "output_tokens": "output",
            "cache_read_tokens": "cache_read",
            "cache_write_tokens": "cache_write",
            "reasoning_tokens": "reasoning",
        }
        for key in keys:
            if key in tokens and tokens[key] is not None:
                return int(tokens[key])
            alias = aliases.get(key)
            if alias and alias in tokens and tokens[alias] is not None:
                return int(tokens[alias])
    return None


def _count(value: Any) -> int | None:
    return None if value is None else int(value)


def _number(value: Any) -> float | None:
    return None if value is None else float(value)


def _group_name(bucket_name: Any) -> str:
    name = str(bucket_name)
    for group in _KNOWN_GROUPS:
        if name == group or name.endswith(f"-{group}") or name.endswith(f"_{group}"):
            return group
    return name


def _failed_tests_by_group(evaluation: dict[str, Any]) -> dict[str, list[str]]:
    tests = evaluation.get("tests") or {}
    grouped: dict[str, list[str]] = {}
    for bucket_name, bucket in tests.items():
        if not isinstance(bucket, dict):
            continue
        failed = bucket.get("failed") or []
        if failed:
            grouped.setdefault(_group_name(bucket_name), []).extend(str(name) for name in failed)
    return grouped


def _group_results(evaluation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pass_counts = evaluation.get("pass_counts") or {}
    total_counts = evaluation.get("total_counts") or {}
    failed_by_group = _failed_tests_by_group(evaluation)
    names = list(_KNOWN_GROUPS)
    for group in (*pass_counts.keys(), *total_counts.keys(), *failed_by_group.keys()):
        group = str(group)
        if group not in names:
            names.append(group)

    results: dict[str, dict[str, Any]] = {}
    for group in names:
        passed = _count(pass_counts.get(group))
        total = _count(total_counts.get(group))
        failed_tests = failed_by_group.get(group, [])
        failed = total - passed if passed is not None and total is not None else None
        if failed is None and failed_tests:
            failed = len(failed_tests)
        if passed is None and total is None and not failed_tests:
            continue
        results[group] = {
            "passed": passed,
            "failed": failed,
            "total": total,
            "failed_tests": failed_tests,
        }
    return results


def _usage_record(inference: dict[str, Any]) -> dict[str, Any]:
    usage = inference.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    reported_cost = usage.get("cost")
    return {
        "input_tokens": _token_field(usage, "input_tokens", "input"),
        "output_tokens": _token_field(usage, "output_tokens", "output"),
        "cache_read_tokens": _token_field(usage, "cache_read_tokens", "cache_read"),
        "cache_write_tokens": _token_field(usage, "cache_write_tokens", "cache_write"),
        "reasoning_tokens": _token_field(usage, "reasoning_tokens", "reasoning"),
        "steps": _count(usage.get("steps")),
        "elapsed_seconds": _number(inference.get("elapsed")),
        "reported_cost_usd": _number(reported_cost),
    }


def failed_test_names(evaluation: dict[str, Any]) -> list[str]:
    """Collect failed test node names from the per-bucket tests dict."""
    failed: list[str] = []
    for names in _failed_tests_by_group(evaluation).values():
        failed.extend(names)
    return failed


def _escape_jinja(text: str) -> str:
    """Neutralize Jinja delimiters so feedback can never be parsed as template.

    The feedback block is appended to the checkpoint prompt *template*; test
    names or messages containing ``{{``/``{%`` would otherwise break rendering.
    """
    return (
        text.replace("{{", "{ {")
        .replace("}}", "} }")
        .replace("{%", "{ %")
        .replace("%}", "% }")
    )


def build_feedback(checkpoint_dir: Path, attempt: int) -> str | None:
    """Build a rework feedback block from the checkpoint's evaluation.json.

    Returns ``None`` when there is nothing to fix: no evaluation, no failing
    tests, or an infrastructure failure (infra errors are runner/problem
    packaging defects and must not trigger rework).
    """
    evaluation = _read_json(checkpoint_dir / "evaluation.json")
    if not evaluation:
        return None
    if evaluation.get("infrastructure_failure"):
        return None
    failed = failed_test_names(evaluation)
    if not failed:
        return None
    lines = [
        f"[REWORK ATTEMPT {attempt}]",
        (
            "The solution did not pass the checkpoint test suite. Fix the code "
            "in this workspace so the failing tests pass while keeping the "
            "already-passing behavior intact."
        ),
        (
            "Results: "
            f"pass_counts={json.dumps(evaluation.get('pass_counts') or {})} "
            f"total_counts={json.dumps(evaluation.get('total_counts') or {})}"
        ),
        "Failing tests:",
        *(f"- {name}" for name in failed),
        "Group metrics:",
    ]
    for group, result in _group_results(evaluation).items():
        lines.append(
            f"- {group}: passed={result['passed']} failed={result['failed']} "
            f"total={result['total']}"
        )
    lines.append("Failing tests by group:")
    for group, names in _failed_tests_by_group(evaluation).items():
        lines.append(f"- {group}:")
        lines.extend(f"  - {name}" for name in names)
    return "\n".join(lines)


def _attempt_record(attempt: int, passed_policy: bool | None, checkpoint_dir: Path) -> dict[str, Any]:
    """Snapshot one attempt's outcome from the checkpoint artifacts."""
    evaluation = _read_json(checkpoint_dir / "evaluation.json") or {}
    inference = _read_json(checkpoint_dir / "inference_result.json") or {}
    groups = _group_results(evaluation)
    usage = _usage_record(inference)
    return {
        "attempt": attempt,
        "stage": "creation" if attempt == 1 else "rework",
        "passed_policy": passed_policy,
        "pass_counts": evaluation.get("pass_counts"),
        "total_counts": evaluation.get("total_counts"),
        "failed_tests": failed_test_names(evaluation),
        "failed_tests_by_group": {
            group: result["failed_tests"] for group, result in groups.items() if result["failed_tests"]
        },
        "groups": groups,
        "core": groups.get("Core"),
        "usage": usage,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cache_read_tokens": usage["cache_read_tokens"],
        "cache_write_tokens": usage["cache_write_tokens"],
        "reasoning_tokens": usage["reasoning_tokens"],
        "steps": usage["steps"],
        "elapsed_seconds": usage["elapsed_seconds"],
        "reported_cost_usd": usage["reported_cost_usd"],
        "infrastructure_failure": bool(evaluation.get("infrastructure_failure")),
        "duration": evaluation.get("duration"),
    }


class ReworkLog:
    """Accumulates per-attempt outcomes and persists them as rework.json."""

    def __init__(self, checkpoint_dir: Path, max_attempts: int) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_attempts = max_attempts
        self.attempts: list[dict[str, Any]] = []

    def record(self, attempt: int, passed_policy: bool | None, checkpoint_dir: Path) -> None:
        self.attempts.append(_attempt_record(attempt, passed_policy, checkpoint_dir))

    @property
    def fixed(self) -> bool:
        return bool(self.attempts and self.attempts[-1].get("passed_policy"))

    def write(self) -> Path:
        data = {
            "checkpoint": self.checkpoint_dir.name,
            "max_additional_attempts": self.max_attempts,
            "attempts_total": len(self.attempts),
            "fixed": self.fixed,
            "attempts": self.attempts,
        }
        path = self.checkpoint_dir / REWORK_FILENAME
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return path


def install_rework_hook(max_attempts: int) -> None:
    """Wrap ``AgentRunner._run_checkpoint`` with the rework loop.

    Idempotent: the wrapper is installed once per process (sitecustomize may
    also install it in workers spawned before ``benchmark.scb_main`` ran).
    """
    global _INSTALLED
    if _INSTALLED or max_attempts <= 0:
        return
    _INSTALLED = True

    from slop_code.agent_runner.runner import AgentRunner, AgentStateEnum

    original: Callable[..., Any] = AgentRunner._run_checkpoint

    @functools.wraps(original)
    def _run_checkpoint_with_rework(
        self: Any,
        checkpoint: Any,
        checkpoint_save_dir: Path,
        is_first_checkpoint: bool,
    ) -> Any:
        summary = original(self, checkpoint, checkpoint_save_dir, is_first_checkpoint)
        # Only test failures trigger rework: no eval / agent errors / rate
        # limits / concurrent-eval mode are not reworkable.
        if summary.had_error:
            return summary
        if self.run_spec.skip_evaluation or self.run_spec.concurrent_evaluation:
            return summary
        if summary.passed_policy is not False:
            return summary
        if self.metrics_tracker.state in (
            AgentStateEnum.ERROR,
            AgentStateEnum.HIT_RATE_LIMITED,
        ):
            return summary

        checkpoint_dir = Path(checkpoint_save_dir)
        log = ReworkLog(checkpoint_dir, max_attempts)
        # SCB resumes by comparing the *saved* prompt against what the current
        # config would render (SPEC_CHANGED invalidation). A rework-solved
        # checkpoint stores the feedback-laden prompt, so restore the first
        # attempt's prompt once the trajectory stays green, or every later
        # resume would re-run an already-passing checkpoint.
        prompt_path = checkpoint_dir / "prompt.txt"
        first_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else None
        log.record(1, summary.passed_policy, checkpoint_dir)
        feedback = build_feedback(checkpoint_dir, attempt=1)
        if feedback is None:
            return summary

        for attempt in range(2, max_attempts + 2):
            original_template = self.run_spec.template
            self.run_spec.template = f"{original_template}\n\n{_escape_jinja(feedback)}"
            try:
                summary = original(self, checkpoint, checkpoint_save_dir, False)
            except BaseException:
                log.write()
                raise
            finally:
                self.run_spec.template = original_template
            log.record(attempt, summary.passed_policy, checkpoint_dir)
            if summary.passed_policy or summary.had_error:
                break
            if self.metrics_tracker.state in (
                AgentStateEnum.ERROR,
                AgentStateEnum.HIT_RATE_LIMITED,
            ):
                break
            feedback = build_feedback(checkpoint_dir, attempt=attempt)
            if feedback is None:
                break
        log.write()
        # Restore unconditionally: feedback left in prompt.txt makes SCB's
        # resume mark this and all later checkpoints SPEC_CHANGED-invalid,
        # so finalize would classify the whole run incomplete.
        if first_prompt is not None:
            current = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else None
            if current != first_prompt:
                prompt_path.write_text(first_prompt, encoding="utf-8")
        return summary

    AgentRunner._run_checkpoint = _run_checkpoint_with_rework
    logger.info(
        "rework hook installed",
        max_additional_attempts=max_attempts,
    )