# _core/integrations

Neutral, harness-agnostic definitions of external connectors (MCP servers). Define each connector
**once** in `servers.json`; project it into a specific harness's native config with the generator.
This is what lets the workspace grow network/MCP workflows (a mailbox reader, a credentialed
line-of-business connector) without locking to one harness.

## Generate a harness config
```
python _core/scripts/gen-harness-config.py codex     # ~/.codex/config.toml section (TOML)
python _core/scripts/gen-harness-config.py claude     # .mcp.json
python _core/scripts/gen-harness-config.py vscode     # .vscode/mcp.json
python _core/scripts/gen-harness-config.py all        # all three
```
Output goes to stdout — review, then merge into the target file. Only `enabled` servers are emitted
unless you pass `--include-disabled`.

## Rules
- One source of truth: edit `servers.json`, never hand-edit a harness config as the master.
- Secrets stay in `.env` and are referenced as `${ENV:KEY}` — never inline a secret here (this file
  is committed). `${WORKSPACE}` is a placeholder for the absolute workspace path on the target machine.
- The generated `.mcp.json` / `.vscode/mcp.json` are harness-specific and machine-specific — keep them
  out of version control if they contain absolute paths (see `.gitignore`).
