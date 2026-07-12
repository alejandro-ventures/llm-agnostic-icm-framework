#!/usr/bin/env python3
"""Project the neutral MCP registry (_core/integrations/servers.json) into a harness's
native config. The repo stays harness-agnostic; each harness gets a generated adapter.
Stdlib only. See PORTABILITY.md.

  python _core/scripts/gen-harness-config.py codex    # -> ~/.codex/config.toml section (TOML)
  python _core/scripts/gen-harness-config.py claude    # -> .mcp.json (JSON)
  python _core/scripts/gen-harness-config.py vscode    # -> .vscode/mcp.json (JSON)
  python _core/scripts/gen-harness-config.py all       # all three, to stdout

Prints to stdout (review, then merge into the target file). Secrets are referenced by
${ENV:KEY} and are NOT resolved here — each harness reads them from the environment / .env.
By default only `enabled` servers are emitted; pass --include-disabled to see all.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "integrations" / "servers.json"


def load_servers(include_disabled: bool):
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return [s for s in data.get("servers", []) if include_disabled or s.get("enabled")]


def _toml_str(s: str) -> str:
    return json.dumps(s)  # JSON string escaping is valid for TOML basic strings


def emit_codex(servers) -> str:
    out = ["# ~/.codex/config.toml  -- merge these sections"]
    for s in servers:
        out.append(f"\n[mcp_servers.{s['name']}]")
        out.append(f"command = {_toml_str(s['command'])}")
        out.append("args = [" + ", ".join(_toml_str(a) for a in s.get("args", [])) + "]")
        if s.get("env"):
            out.append(f"\n[mcp_servers.{s['name']}.env]")
            for k, v in s["env"].items():
                out.append(f"{k} = {_toml_str(v)}")
    return "\n".join(out) + "\n"


def _json_block(servers, top_key, with_type):
    body = {}
    for s in servers:
        entry = {"command": s["command"], "args": s.get("args", [])}
        if with_type:
            entry = {"type": s.get("transport", "stdio"), **entry}
        if s.get("env"):
            entry["env"] = s["env"]
        body[s["name"]] = entry
    return json.dumps({top_key: body}, indent=2, ensure_ascii=False) + "\n"


def emit_claude(servers) -> str:
    return "// .mcp.json  (project root)\n" + _json_block(servers, "mcpServers", with_type=False)


def emit_vscode(servers) -> str:
    return "// .vscode/mcp.json\n" + _json_block(servers, "servers", with_type=True)


EMITTERS = {"codex": emit_codex, "claude": emit_claude, "vscode": emit_vscode}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("harness", choices=[*EMITTERS, "all"])
    p.add_argument("--include-disabled", action="store_true")
    a = p.parse_args(argv)
    servers = load_servers(a.include_disabled)
    if not servers:
        print("# no enabled servers in the registry (use --include-disabled to see all)")
        return 0
    targets = list(EMITTERS) if a.harness == "all" else [a.harness]
    for i, h in enumerate(targets):
        if i:
            print("\n" + "=" * 60)
        print(EMITTERS[h](servers), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
