import pytest

from benchmark.cost import normalized_cost_usd


def test_normalized_cost_supports_disjoint_opencode_usage() -> None:
    pricing = {
        "models": {
            "model": {
                "input": 0.15,
                "output": 0.50,
                "cache_read": 0.015,
                "cache_write": 0.0,
                "reasoning": 0.50,
                "input_includes_cache": False,
                "reasoning_in_output": False,
            }
        }
    }

    cost = normalized_cost_usd(
        model="model",
        pricing=pricing,
        input_tokens=1_000_000,
        output_tokens=3_000_000,
        cache_read_tokens=2_000_000,
        cache_write_tokens=0,
        reasoning_tokens=4_000_000,
    )

    assert cost == pytest.approx(3.68)


def test_normalized_cost_preserves_inclusive_provider_defaults() -> None:
    pricing = {
        "models": {
            "model": {
                "input": 1.0,
                "output": 10.0,
                "cache_read": 0.1,
                "cache_write": 0.0,
                "reasoning": 10.0,
            }
        }
    }

    cost = normalized_cost_usd(
        model="model",
        pricing=pricing,
        input_tokens=1_000_000,
        output_tokens=300_000,
        cache_read_tokens=200_000,
        cache_write_tokens=0,
        reasoning_tokens=100_000,
    )

    assert cost == pytest.approx(3.82)
