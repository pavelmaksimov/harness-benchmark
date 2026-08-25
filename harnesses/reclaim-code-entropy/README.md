# reclaim-code-entropy harness (pinned)

- Skill tree: `skill/` → agent skills dir (Codex: `~/.codex/skills/reclaim-code-entropy/`, OpenCode: `~/.config/opencode/skills/reclaim-code-entropy/`)
- Activation: prompt prefix + skill copy hook (`benchmark/skill_hook.py`)
- Source: [`Yevanchen/reclaim-code-entropy`](https://github.com/Yevanchen/reclaim-code-entropy) at commit `9e6482e45814076b9710b55c8dcbb064ba4b7977`
- Workflow: evidence-backed entropy audit and safe simplification; no extra workspace artifact root is mandated

The arm keeps the upstream skill payload unchanged. It makes the skill active
for every checkpoint while the prompt keeps the agent focused on delivering a
working solution and preserving unrelated changes.

This arm is wired and pinned but has no `SMOKE.json` yet. Run the CP1 smoke
before any full experiment, then triage its snapshot and commit the generated
marker.

Re-pin after any change under `skill/`:

```bash
uv run python scripts/pin_harness.py reclaim-code-entropy
```

Then re-run the smoke because `SMOKE.json` is invalidated by a content change:

```bash
uv run python -m benchmark smoke --arm reclaim-code-entropy --problem file_backup
```
