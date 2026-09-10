from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_pricing(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid pricing file: {path}")
    return data


# Adapters whose usage counters are disjoint (see vendor SCB agent adapters):
# OpenCode reports fresh input, cache reads, output and reasoning as separate counters
# (agents/opencode/agent.py), while the Codex and pi adapters store prompt tokens already
# including cache reads (agents/pi/agent.py: input += cacheRead; agents/gemini/agent.py
# does the same) and OpenAI-style output tokens already including reasoning.
DISJOINT_COUNTER_AGENTS = frozenset({"opencode"})


def prompt_tokens(
    *,
    agent: str | None,
    input_tokens: float | None,
    cache_read_tokens: float | None,
) -> float | None:
    """Prompt tokens on one scale across adapters: cached reads folded into input.

    Returns None when the input count itself is unknown.
    """
    if input_tokens is None:
        return None
    if agent in DISJOINT_COUNTER_AGENTS:
        return input_tokens + (cache_read_tokens or 0)
    return input_tokens


def completion_tokens(
    *,
    agent: str | None,
    output_tokens: float | None,
    reasoning_tokens: float | None,
) -> float | None:
    """Completion tokens on one scale across adapters: reasoning folded into output."""
    if output_tokens is None:
        return None
    if agent in DISJOINT_COUNTER_AGENTS:
        return output_tokens + (reasoning_tokens or 0)
    return output_tokens


def normalized_cost_usd(
    *,
    model: str,
    pricing: dict[str, Any],
    input_tokens: int | None,
    output_tokens: int | None,
    cache_read_tokens: int | None,
    cache_write_tokens: int | None,
    reasoning_tokens: int | None,
) -> float | None:
    """Recompute cost from token usage and pinned pricing table.

    Missing mandatory token fields => None (never invent values).
    """
    models = pricing.get("models") or {}
    rates = models.get(model)
    if not isinstance(rates, dict):
        return None
    if input_tokens is None or output_tokens is None:
        return None

    cache_read = cache_read_tokens or 0
    cache_write = cache_write_tokens or 0
    reasoning = reasoning_tokens or 0
    input_includes_cache = bool(rates.get("input_includes_cache", True))
    reasoning_in_output = bool(rates.get("reasoning_in_output", True))
    uncached_input = (
        max(int(input_tokens) - int(cache_read), 0)
        if input_includes_cache
        else int(input_tokens)
    )

    cost = 0.0
    cost += uncached_input / 1_000_000 * float(rates.get("input") or 0)
    cost += int(output_tokens) / 1_000_000 * float(rates.get("output") or 0)
    cost += int(cache_read) / 1_000_000 * float(rates.get("cache_read") or 0)
    cost += int(cache_write) / 1_000_000 * float(rates.get("cache_write") or 0)
    if not reasoning_in_output:
        cost += reasoning / 1_000_000 * float(rates.get("reasoning") or 0)
    return cost
