# benjamin-plus-skill benchmark arm

Pinned from [`JetBrains/benjamin-plus-skill`](https://github.com/JetBrains/benjamin-plus-skill)
at commit `532771be5687566b12a9f62e17fbe7ad3591518c`.

- `skill/SKILL.md` is the upstream `RULESET.md`.
- `AGENTS.md` is the upstream `injected-instruction.md` for OpenCode.
- Re-pin with `uv run python scripts/pin_harness.py benjamin-plus-skill`.
- Run the required CP1 smoke with `uv run python -m benchmark smoke --arm benjamin-plus-skill --problem file_backup`.
