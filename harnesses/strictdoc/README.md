# strictdoc harness (pinned)

- Skill tree: `skill/` → agent skills dir (Codex: `~/.codex/skills/strictdoc/`, OpenCode: `~/.config/opencode/skills/strictdoc/`)
- Activation: prompt prefix + skill copy hook (`benchmark/skill_hook.py`)
- Tool under test: StrictDoc (<https://github.com/strictdoc-project/strictdoc>), verified against PyPI 0.28.1
- Docs root mandated inside the agent workspace: `strictdoc-docs/` (sources + `sdoc-export/`)

Re-pin after any change under `skill/`:

```bash
uv run python scripts/pin_harness.py strictdoc
```

Then re-run smoke (SMOKE.json is invalidated by content change):

```bash
uv run python -m benchmark smoke --arm strictdoc --problem file_backup --checkpoints 2 \
  --agent opencode --provider opencode_auth --model x-preview-f-free --thinking high
```
