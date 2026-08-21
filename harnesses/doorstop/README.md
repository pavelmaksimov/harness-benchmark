# doorstop harness (pinned)

- Skill tree: `skill/` → agent skills dir (Codex: `~/.codex/skills/doorstop/`, OpenCode: `~/.config/opencode/skills/doorstop/`)
- Activation: prompt prefix + skill copy hook (`benchmark/skill_hook.py`)
- Tool under test: Doorstop (<https://github.com/doorstop-dev/doorstop>), verified against PyPI 3.2
- Docs root mandated inside the agent workspace: `doorstop-docs/` (+ optional `publish-md/` export)

Re-pin after any change under `skill/`:

```bash
uv run python scripts/pin_harness.py doorstop
```

Then re-run smoke (SMOKE.json is invalidated by content change):

```bash
uv run python -m benchmark smoke --arm doorstop --problem file_backup --checkpoints 2 \
  --agent opencode --provider opencode_auth --model x-preview-f-free --thinking high
```
