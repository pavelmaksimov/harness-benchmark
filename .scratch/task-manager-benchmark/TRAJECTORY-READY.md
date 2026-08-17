# Task Manager trajectory readiness (agent launch)

Date: 2026-08-17  
Policy: option 1 — benchmark = checkpoint prompts + evaluation tests only.

## What is ready

| Piece | Status |
|-------|--------|
| Briefs `checkpoint_1.md` … `checkpoint_15.md` | present |
| Tests `tests/test_checkpoint_N.py` (15 files) | present |
| Markers | unmarked = Core; `@pytest.mark.functionality` / `@pytest.mark.error` used on every CP |
| `include_prior_tests: true` | CP2–CP15 in `config.yaml` |
| Arm `pass_policy` | `all-core-cases` (baseline, ponytail, other arms) — no SCB runner change |
| Offline gate | `uv run python -m benchmark validate-problem --problem task_manager` **passes** |
| Deps | `test_dependencies` in `config.yaml`; sync via `scripts/sync_task_manager_problem.sh` |
| Metrics excludes | `EXCLUDE_DIR_NAMES` unchanged; `tests` and `snapshot` not excluded |
| Default problem | `file_backup` untouched |

Agents are graded at run time. There is **no** cumulative reference app for CP2+. Only `solutions/checkpoint_1/` remains for optional offline CP1 sanity.

## Deferred until Docker images exist

- Live Codex-in-Docker smoke: `benchmark smoke --arm … --problem task_manager`
- Full multi-run science: `run-all --problem task_manager --runs 3 --jobs …`

Do not treat a single local/offline check as the experiment result. See issue 18 notes.
