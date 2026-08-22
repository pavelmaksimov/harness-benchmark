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
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from benchmark.attempt_diagnostics import diagnose_attempt

logger = logging.getLogger("hb.rework")

REWORK_FILENAME = "rework.json"
HB_REWORK_ATTEMPTS = "HB_REWORK_ATTEMPTS"
HB_TRANSIENT_RETRIES = "HB_TRANSIENT_RETRIES"
HB_REWORK_FEEDBACK = "HB_REWORK_FEEDBACK"
DEFAULT_FEEDBACK_STRATEGY = "current-first"
LEGACY_FEEDBACK_STRATEGY = "all-failures"
FEEDBACK_STRATEGIES = {DEFAULT_FEEDBACK_STRATEGY, LEGACY_FEEDBACK_STRATEGY, "v1"}
FEEDBACK_STRATEGY_VERSION = "current-first-v1"
FEEDBACK_MAX_CURRENT_TESTS = 20
FEEDBACK_MAX_CONTEXT_TESTS = 5
_KNOWN_GROUPS = ("Core", "Functionality", "Error", "Regression")
_CHECKPOINT_RE = re.compile(r"checkpoint_(\d+)", re.IGNORECASE)

_INSTALLED = False


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


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


def _checkpoint_number(value: Any) -> int | None:
    match = _CHECKPOINT_RE.search(str(value))
    return int(match.group(1)) if match else None


def _failed_test_items(evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    tests = evaluation.get("tests") or {}
    items: list[dict[str, Any]] = []
    if not isinstance(tests, dict):
        return items
    for bucket_name, bucket in tests.items():
        if not isinstance(bucket, dict):
            continue
        group = _group_name(bucket_name)
        source_checkpoint = _checkpoint_number(bucket_name)
        for name in bucket.get("failed") or []:
            items.append(
                {
                    "name": str(name),
                    "bucket": str(bucket_name),
                    "group": group,
                    "source_checkpoint": source_checkpoint,
                }
            )
    return items


def _failed_tests_by_group(evaluation: dict[str, Any]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for item in _failed_test_items(evaluation):
        grouped.setdefault(item["group"], []).append(item["name"])
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
    return [item["name"] for item in _failed_test_items(evaluation)]


def _unique_names(items: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for item in items:
        name = str(item["name"])
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _previous_evaluation(
    checkpoint_dir: Path,
    current_checkpoint: int | None,
) -> dict[str, Any] | None:
    if current_checkpoint is None or current_checkpoint <= 1:
        return None
    return _read_json(
        checkpoint_dir.parent / f"checkpoint_{current_checkpoint - 1}" / "evaluation.json"
    )


def _feedback_context(
    checkpoint_dir: Path,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Split failures into actionable current tests and regression context."""
    current_checkpoint = _checkpoint_number(checkpoint_dir.name)
    items = _failed_test_items(evaluation)
    if current_checkpoint is None:
        current_checkpoint = next(
            (
                item["source_checkpoint"]
                for item in items
                if item["source_checkpoint"] is not None
                and item["group"] != "Regression"
            ),
            None,
        )

    current_items = [
        item
        for item in items
        if (
            item["source_checkpoint"] == current_checkpoint
            or (
                item["source_checkpoint"] is None
                and item["group"] != "Regression"
            )
        )
    ]
    current_policy = [item for item in current_items if item["group"] == "Core"]
    current_other = [item for item in current_items if item["group"] != "Core"]
    regressions = [item for item in items if item["group"] == "Regression"]
    classified = {id(item) for item in current_items + regressions}
    other = [item for item in items if id(item) not in classified]

    previous = _previous_evaluation(checkpoint_dir, current_checkpoint)
    previous_names = set(failed_test_names(previous)) if previous else set()
    regression_names = _unique_names(regressions)
    if previous is None:
        regression_new: list[str] = []
        regression_persistent = regression_names
    else:
        regression_new = [name for name in regression_names if name not in previous_names]
        regression_persistent = [name for name in regression_names if name in previous_names]

    failed_by_bucket: dict[str, list[str]] = {}
    for item in items:
        failed_by_bucket.setdefault(item["bucket"], []).append(item["name"])

    return {
        "strategy_version": FEEDBACK_STRATEGY_VERSION,
        "current_checkpoint": current_checkpoint,
        "policy_failures": _unique_names(current_policy),
        "current_other_failures": _unique_names(current_other),
        "regression_new_failures": regression_new,
        "regression_persistent_failures": regression_persistent,
        "other_failures": _unique_names(other),
        "regression_comparison_available": previous is not None,
        "all_failed_tests": _unique_names(items),
        "failed_tests_by_bucket": failed_by_bucket,
        "failure_items": items,
    }


def _append_limited(
    lines: list[str],
    label: str,
    names: list[str],
    *,
    limit: int,
) -> int:
    if not names:
        return 0
    shown = names[:limit]
    lines.append(label)
    lines.extend(f"- {name}" for name in shown)
    omitted = len(names) - len(shown)
    if omitted:
        lines.append(f"- ... and {omitted} more omitted from feedback")
    return omitted


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


def _feedback_strategy(value: str | None = None) -> str:
    strategy = value or os.environ.get(HB_REWORK_FEEDBACK, DEFAULT_FEEDBACK_STRATEGY)
    if strategy == "v1":
        strategy = LEGACY_FEEDBACK_STRATEGY
    return strategy if strategy in FEEDBACK_STRATEGIES else DEFAULT_FEEDBACK_STRATEGY


def _feedback_metadata(
    context: dict[str, Any],
    strategy: str,
) -> dict[str, Any]:
    categories = {
        "policy_failures": context["policy_failures"],
        "current_other_failures": context["current_other_failures"],
        "regression_new_failures": context["regression_new_failures"],
        "regression_persistent_failures": context["regression_persistent_failures"],
        "other_failures": context["other_failures"],
    }
    if strategy == LEGACY_FEEDBACK_STRATEGY:
        shown = {name: len(values) for name, values in categories.items()}
        omitted = {name: 0 for name in categories}
    else:
        limits = {
            "policy_failures": FEEDBACK_MAX_CURRENT_TESTS,
            "current_other_failures": FEEDBACK_MAX_CONTEXT_TESTS,
            "regression_new_failures": FEEDBACK_MAX_CONTEXT_TESTS,
            "regression_persistent_failures": FEEDBACK_MAX_CONTEXT_TESTS,
            "other_failures": FEEDBACK_MAX_CONTEXT_TESTS,
        }
        shown = {
            name: min(len(values), limits[name]) for name, values in categories.items()
        }
        omitted = {
            name: len(values) - shown[name] for name, values in categories.items()
        }
    return {
        "strategy": strategy,
        "strategy_version": (
            FEEDBACK_STRATEGY_VERSION
            if strategy == DEFAULT_FEEDBACK_STRATEGY
            else f"{LEGACY_FEEDBACK_STRATEGY}-v1"
        ),
        "limits": {
            "policy_failures": FEEDBACK_MAX_CURRENT_TESTS,
            "context_failures": FEEDBACK_MAX_CONTEXT_TESTS,
        },
        "shown_counts": shown,
        "omitted_counts": omitted,
        "regression_comparison_available": context["regression_comparison_available"],
    }


def build_transient_feedback(retry: int) -> str:
    """Prompt used when the provider ended a response before completion."""
    return "\n".join(
        [
            f"[TRANSIENT RETRY {retry}]",
            (
                "The previous agent response ended unexpectedly before the task was "
                "complete. Inspect the current workspace and continue implementing "
                "the checkpoint; preserve any valid work already present."
            ),
            "Use the normal verification workflow and finish the requested change.",
        ]
    )


def build_feedback(
    checkpoint_dir: Path,
    attempt: int,
    *,
    strategy: str | None = None,
) -> str | None:
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
    strategy = _feedback_strategy(strategy)
    context = _feedback_context(checkpoint_dir, evaluation)
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
        "Group metrics:",
    ]
    for group, result in _group_results(evaluation).items():
        lines.append(
            f"- {group}: passed={result['passed']} failed={result['failed']} "
            f"total={result['total']}"
        )
    if strategy == LEGACY_FEEDBACK_STRATEGY:
        lines.extend(["Failing tests:", *(f"- {name}" for name in failed)])
        lines.append("Failing tests by group:")
        for group, names in _failed_tests_by_group(evaluation).items():
            lines.append(f"- {group}:")
            lines.extend(f"  - {name}" for name in names)
        return "\n".join(lines)

    current_checkpoint = context["current_checkpoint"]
    checkpoint_label = (
        f"checkpoint_{current_checkpoint}"
        if current_checkpoint is not None
        else "the current checkpoint"
    )
    lines.append("")
    lines.append(f"Current policy failures for {checkpoint_label} (fix these first):")
    if context["policy_failures"]:
        shown = context["policy_failures"][:FEEDBACK_MAX_CURRENT_TESTS]
        lines.extend(f"- {name}" for name in shown)
        omitted = len(context["policy_failures"]) - len(shown)
        if omitted:
            lines.append(f"- ... and {omitted} more omitted from feedback")
    else:
        lines.append("- none identified from the evaluation buckets")

    _append_limited(
        lines,
        "Current non-policy failures (informational):",
        context["current_other_failures"],
        limit=FEEDBACK_MAX_CONTEXT_TESTS,
    )
    if context["other_failures"]:
        _append_limited(
            lines,
            "Unclassified failures (informational):",
            context["other_failures"],
            limit=FEEDBACK_MAX_CONTEXT_TESTS,
        )

    new_regressions = context["regression_new_failures"]
    persistent_regressions = context["regression_persistent_failures"]
    if new_regressions or persistent_regressions:
        if context["regression_comparison_available"]:
            lines.append(
                "Regression failures (fix newly introduced ones after current policy): "
                f"new={len(new_regressions)} persistent={len(persistent_regressions)}"
            )
        else:
            lines.append(
                "Regression failures (prior comparison unavailable; "
                f"total={len(new_regressions) + len(persistent_regressions)}):"
            )
        _append_limited(
            lines,
            "New regression failures:",
            new_regressions,
            limit=FEEDBACK_MAX_CONTEXT_TESTS,
        )
        _append_limited(
            lines,
            "Persistent regression failures:",
            persistent_regressions,
            limit=FEEDBACK_MAX_CONTEXT_TESTS,
        )
    lines.append(
        "The complete failed-test inventory is preserved in rework.json; "
        "do not treat persistent historical failures as new requirements."
    )
    return "\n".join(lines)


def _attempt_record(
    attempt: int,
    passed_policy: bool | None,
    checkpoint_dir: Path,
    *,
    stage: str | None = None,
    feedback_strategy: str | None = None,
) -> dict[str, Any]:
    """Snapshot one attempt's outcome from the checkpoint artifacts."""
    evaluation = _read_json(checkpoint_dir / "evaluation.json") or {}
    inference = _read_json(checkpoint_dir / "inference_result.json") or {}
    groups = _group_results(evaluation)
    usage = _usage_record(inference)
    diagnostics = diagnose_attempt(
        checkpoint_dir,
        inference=inference,
        evaluation=evaluation,
    )
    feedback_context = _feedback_context(checkpoint_dir, evaluation)
    feedback_strategy = _feedback_strategy(feedback_strategy)
    return {
        "attempt": attempt,
        "stage": stage or ("creation" if attempt == 1 else "rework"),
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
        "failure_class": diagnostics["failure_class"],
        "confidence": diagnostics["confidence"],
        "signals": diagnostics["signals"],
        "message_path": diagnostics["message_path"],
        "truncation_output_threshold": diagnostics["output_threshold"],
        "diagnostics": diagnostics,
        "feedback_context": feedback_context,
        "feedback_metadata": _feedback_metadata(feedback_context, feedback_strategy),
        "feedback_strategy": feedback_strategy,
    }


class ReworkLog:
    """Accumulates per-attempt outcomes and persists them as rework.json."""

    def __init__(
        self,
        checkpoint_dir: Path,
        max_attempts: int,
        *,
        max_transient_retries: int = 0,
        feedback_strategy: str | None = None,
    ) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_attempts = max_attempts
        self.max_transient_retries = max_transient_retries
        self.feedback_strategy = _feedback_strategy(feedback_strategy)
        self.attempts: list[dict[str, Any]] = []

    def record(
        self,
        attempt: int,
        passed_policy: bool | None,
        checkpoint_dir: Path,
        *,
        stage: str | None = None,
    ) -> None:
        self.attempts.append(
            _attempt_record(
                attempt,
                passed_policy,
                checkpoint_dir,
                stage=stage,
                feedback_strategy=self.feedback_strategy,
            )
        )

    @property
    def fixed(self) -> bool:
        return bool(self.attempts and self.attempts[-1].get("passed_policy"))

    def write(self) -> Path:
        truncation_attempts = sum(
            1
            for attempt in self.attempts
            if (attempt.get("diagnostics") or {}).get("detected")
        )
        data = {
            "checkpoint": self.checkpoint_dir.name,
            "max_additional_attempts": self.max_attempts,
            "max_transient_retries": self.max_transient_retries,
            "feedback_strategy": self.feedback_strategy,
            "attempts_total": len(self.attempts),
            "semantic_attempts_total": sum(
                1 for attempt in self.attempts if attempt.get("stage") != "transient_retry"
            ),
            "transient_retries_total": sum(
                1 for attempt in self.attempts if attempt.get("stage") == "transient_retry"
            ),
            "provider_truncation_attempts": truncation_attempts,
            "provider_truncation_recovered": bool(truncation_attempts and self.fixed),
            "provider_truncation_unresolved": bool(truncation_attempts and not self.fixed),
            "fixed": self.fixed,
            "attempts": self.attempts,
        }
        path = self.checkpoint_dir / REWORK_FILENAME
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return path


def _prompt_snapshot(checkpoint_dir: Path) -> tuple[Path | None, str | None]:
    for candidate in (
        checkpoint_dir / "agent" / "prompt.txt",
        checkpoint_dir / "prompt.txt",
    ):
        if candidate.exists():
            try:
                return candidate, candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return candidate, None
    return None, None


def install_rework_hook(
    max_attempts: int,
    transient_retries: int = 0,
    feedback_strategy: str | None = None,
) -> None:
    """Wrap ``AgentRunner._run_checkpoint`` with the rework loop.

    Idempotent: the wrapper is installed once per process (sitecustomize may
    also install it in workers spawned before ``benchmark.scb_main`` ran).
    """
    global _INSTALLED
    if _INSTALLED or (max_attempts <= 0 and transient_retries <= 0):
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
        initial_evaluation = _read_json(checkpoint_dir / "evaluation.json")
        if initial_evaluation and initial_evaluation.get("infrastructure_failure"):
            return summary
        log = ReworkLog(
            checkpoint_dir,
            max_attempts,
            max_transient_retries=transient_retries,
            feedback_strategy=feedback_strategy,
        )
        # SCB resumes by comparing the *saved* prompt against what the current
        # config would render (SPEC_CHANGED invalidation). A rework-solved
        # checkpoint stores the feedback-laden prompt, so restore the first
        # attempt's prompt once the trajectory stays green, or every later
        # resume would re-run an already-passing checkpoint.
        prompt_path, first_prompt = _prompt_snapshot(checkpoint_dir)
        log.record(1, summary.passed_policy, checkpoint_dir, stage="creation")
        semantic_retries = 0
        transient_retries_used = 0
        attempt_number = 1
        try:
            while True:
                if summary.passed_policy or summary.had_error:
                    break
                if self.metrics_tracker.state in (
                    AgentStateEnum.ERROR,
                    AgentStateEnum.HIT_RATE_LIMITED,
                ):
                    break

                diagnostics = log.attempts[-1].get("diagnostics") or {}
                if diagnostics.get("detected") and transient_retries_used < transient_retries:
                    transient_retries_used += 1
                    attempt_number += 1
                    transient_feedback = build_transient_feedback(transient_retries_used)
                    original_template = self.run_spec.template
                    self.run_spec.template = (
                        f"{original_template}\n\n{_escape_jinja(transient_feedback)}"
                    )
                    try:
                        summary = original(self, checkpoint, checkpoint_save_dir, False)
                    finally:
                        self.run_spec.template = original_template
                    log.record(
                        attempt_number,
                        summary.passed_policy,
                        checkpoint_dir,
                        stage="transient_retry",
                    )
                    continue

                if semantic_retries >= max_attempts:
                    break
                feedback = build_feedback(
                    checkpoint_dir,
                    attempt=semantic_retries + 1,
                    strategy=log.feedback_strategy,
                )
                if feedback is None:
                    break
                semantic_retries += 1
                attempt_number += 1
                original_template = self.run_spec.template
                self.run_spec.template = f"{original_template}\n\n{_escape_jinja(feedback)}"
                try:
                    summary = original(self, checkpoint, checkpoint_save_dir, False)
                finally:
                    self.run_spec.template = original_template
                log.record(
                    attempt_number,
                    summary.passed_policy,
                    checkpoint_dir,
                    stage="rework",
                )
        finally:
            log.write()
            # Restore unconditionally: feedback left in prompt.txt makes SCB's
            # resume mark this and all later checkpoints SPEC_CHANGED-invalid.
            if prompt_path is not None and first_prompt is not None:
                try:
                    current = prompt_path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    current = None
                if current != first_prompt:
                    prompt_path.write_text(first_prompt, encoding="utf-8")
        return summary

    AgentRunner._run_checkpoint = _run_checkpoint_with_rework
    logger.info(
        "rework hook installed",
        max_additional_attempts=max_attempts,
        max_transient_retries=transient_retries,
        feedback_strategy=_feedback_strategy(feedback_strategy),
    )