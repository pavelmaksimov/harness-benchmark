# supermemory harness (pinned)

- Skills: `skills/supermemory-*`
- Home extras: `home/supermemory/*.js` → `~/.codex/supermemory/`
- Runtime config: benchmark hook installs `~/.codex/supermemory.json` from the host
  (`~/.codex/supermemory.json`, else `SUPERMEMORY_CODEX_API_KEY` / local `api_key` file)
  with `baseUrl=http://127.0.0.1:6767` (local supermemory-server, local embeddings).
- Docker: `configs/environments/docker-python3.12-uv-hostnet.yaml` (`network: host`)
  so the agent container can reach host `:6767`.

Prerequisite: local server up (`systemctl --user start supermemory` or
`~/.local/share/supermemory/start.sh`) listening on `127.0.0.1:6767`.
