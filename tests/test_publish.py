from __future__ import annotations

from benchmark.publish import _latest_cells


def test_latest_cells_keeps_same_model_for_different_adapters() -> None:
    payloads = [
        {
            "date": "2026-08-21T10:00:00Z",
            "experiment_id": "codex-exp",
            "problem": "file_backup",
            "agent": "codex",
            "provider": "codex_auth",
            "model": "same-model",
            "arms": {"baseline": {}},
            "n_baseline": 3,
        },
        {
            "date": "2026-08-21T09:00:00Z",
            "experiment_id": "opencode-exp",
            "problem": "file_backup",
            "agent": "opencode",
            "provider": "opencode_auth",
            "model": "same-model",
            "arms": {"baseline": {}},
            "n_baseline": 3,
        },
    ]

    cells = _latest_cells(payloads)

    assert {(cell["agent"], cell["provider"]) for cell in cells} == {
        ("codex", "codex_auth"),
        ("opencode", "opencode_auth"),
    }
