"""Shared SCB catalogs and offline desired-state validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from benchmark.arms import get_arm
from benchmark.paths import MODELS_DIR, PROBLEMS_DIR, SUPPORTED_AGENTS

THINKING_PRESETS = frozenset(("none", "disabled", "low", "medium", "high", "xhigh", "max"))


@dataclass(frozen=True)
class ValidationIssue:
    scope: str
    message: str
    level: str = "error"

    def render(self) -> str:
        return f"{self.level}: {self.scope}: {self.message}"


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return not any(issue.level == "error" for issue in self.issues)

    def render(self) -> str:
        if not self.issues:
            return "valid: desired configuration and local catalogs"
        return "\n".join(issue.render() for issue in self.issues)


def load_catalogs() -> tuple[Any, Any]:
    """Load SCB providers and models exactly as the SCB entrypoint does."""
    import slop_code.agent_runner.agents  # noqa: F401
    from slop_code.agent_runner.credentials import ProviderCatalog
    from slop_code.common.llms import ModelCatalog

    ProviderCatalog.ensure_loaded()
    ModelCatalog.ensure_loaded()
    if MODELS_DIR.is_dir():
        ModelCatalog.load_from_directory(MODELS_DIR)
    return ProviderCatalog, ModelCatalog


def catalog_snapshot() -> dict[str, list[dict[str, Any]]]:
    """Return provider and model names plus their non-secret routing metadata."""
    providers, models = load_catalogs()
    provider_rows = []
    for name in providers.list_providers():
        definition = providers.get(name)
        provider_rows.append(
            {
                "name": name,
                "credential_type": definition.credential_type.value if definition else None,
                "env_var": definition.env_var if definition else None,
                "file_path": definition.file_path if definition else None,
                "description": definition.description if definition else "",
            }
        )

    model_rows = []
    for name in models.list_models():
        definition = models.get(name)
        if definition is None:
            continue
        agent_routes = {
            agent: settings.get("provider_name")
            for agent, settings in definition.agent_specific.items()
            if isinstance(settings, dict) and settings.get("provider_name")
        }
        model_rows.append(
            {
                "name": name,
                "internal_name": definition.internal_name,
                "catalog_provider": definition.provider,
                "aliases": list(definition.aliases),
                "provider_slugs": dict(definition.provider_slugs),
                "agents": sorted(definition.agent_specific),
                "agent_routes": agent_routes,
            }
        )
    return {"providers": provider_rows, "models": model_rows}


def render_catalog(snapshot: dict[str, list[dict[str, Any]]], kind: str = "all") -> str:
    """Render exact catalog identifiers without exposing credentials."""
    sections: list[str] = []
    if kind in {"all", "providers"}:
        lines = ["providers (credential names):"]
        for row in snapshot["providers"]:
            source = row["env_var"] or row["file_path"] or "source unspecified"
            lines.append(f"  {row['name']} ({row['credential_type']}) <- {source}")
        sections.append("\n".join(lines))
    if kind in {"all", "models"}:
        lines = ["models (use the `name` value in desired.yaml):"]
        for row in snapshot["models"]:
            agents = ",".join(row["agents"]) or "catalog only"
            routes = ",".join(f"{agent}:{route}" for agent, route in row["agent_routes"].items()) or "-"
            lines.append(
                f"  {row['name']} | api={row['internal_name']} | "
                f"catalog_provider={row['catalog_provider']} | routes={routes} | agents={agents}"
            )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def _check_selection(
    *,
    scope: str,
    agent: str,
    provider: str,
    model: str,
    thinking: str,
    providers: Any,
    models: Any,
    check_credentials: bool,
    credential_store: Any,
    issues: list[ValidationIssue],
) -> None:
    if agent not in SUPPORTED_AGENTS:
        issues.append(
            ValidationIssue(scope, f"unknown agent {agent!r}; expected: {', '.join(SUPPORTED_AGENTS)}")
        )
    if provider_def := providers.get(provider):
        if check_credentials and not credential_store.has_credential(provider):
            source = provider_def.env_var or provider_def.file_path or "configured credential source"
            issues.append(ValidationIssue(scope, f"credential is missing for {provider!r} ({source})"))
    else:
        issues.append(
            ValidationIssue(
                scope,
                f"unknown provider {provider!r}; run `uv run python -m benchmark catalog providers`",
            )
        )
    if models.get(model) is None:
        issues.append(
            ValidationIssue(
                scope,
                f"unknown model {model!r}; run `uv run python -m benchmark catalog models`",
            )
        )
    if thinking not in THINKING_PRESETS:
        issues.append(
            ValidationIssue(
                scope,
                f"unsupported thinking {thinking!r}; expected: {', '.join(sorted(THINKING_PRESETS))}",
            )
        )
    if agent == "opencode" and not provider:
        issues.append(ValidationIssue(scope, "OpenCode requires a credential provider"))
    if agent == "opencode" and not model:
        issues.append(ValidationIssue(scope, "OpenCode requires a model"))


def validate_selection(
    *,
    agent: str,
    provider: str,
    model: str,
    thinking: str,
    scope: str = "selection",
    check_credentials: bool = False,
) -> ValidationReport:
    """Validate one resolved agent/provider/model/thinking selection."""
    providers, models = load_catalogs()
    credential_store = None
    if check_credentials:
        from slop_code.agent_runner.credentials import API_KEY_STORE

        credential_store = API_KEY_STORE
    issues: list[ValidationIssue] = []
    _check_selection(
        scope=scope,
        agent=agent,
        provider=provider,
        model=model,
        thinking=thinking,
        providers=providers,
        models=models,
        check_credentials=check_credentials,
        credential_store=credential_store,
        issues=issues,
    )
    return ValidationReport(tuple(issues))


def validate_desired(desired: Any, *, check_credentials: bool = False) -> ValidationReport:
    """Validate names and offline prerequisites before fleet starts a monitor."""
    issues: list[ValidationIssue] = []
    selections = [("defaults", desired.defaults)]
    selections.extend((f"experiment {experiment.id}", experiment) for experiment in desired.experiments)
    for scope, selection in selections:
        issues.extend(
            validate_selection(
                scope=scope,
                agent=selection.agent,
                provider=selection.provider,
                model=selection.model,
                thinking=selection.thinking,
                check_credentials=check_credentials,
            ).issues
        )
    for experiment in desired.experiments:
        if not (PROBLEMS_DIR / experiment.problem).is_dir():
            issues.append(
                ValidationIssue(
                    f"experiment {experiment.id}",
                    f"problem directory not found: {experiment.problem!r}",
                )
            )
        for arm in experiment.arms:
            try:
                get_arm(arm)
            except ValueError:
                target = desired.harness(arm)
                if target.source:
                    issues.append(
                        ValidationIssue(
                            f"experiment {experiment.id}",
                            f"arm {arm!r} is not registered yet; onboarding will be required",
                            level="warning",
                        )
                    )
                else:
                    issues.append(
                        ValidationIssue(
                            f"experiment {experiment.id}",
                            f"unknown arm {arm!r}; add it to benchmark/arms.py or configure harnesses.{arm}.source",
                        )
                    )
    return ValidationReport(tuple(issues))


def report_json(report: ValidationReport) -> str:
    return json.dumps(
        {
            "ok": report.ok,
            "issues": [
                {"scope": issue.scope, "level": issue.level, "message": issue.message}
                for issue in report.issues
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
