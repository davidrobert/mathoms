#!/usr/bin/env python3
"""Sincroniza .codex/agents/*.toml a partir de .claude/agents/*.md."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - suporte a Python 3.9 local.
    tomllib = None

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
CODEX_AGENTS_DIR = REPO_ROOT / ".codex" / "agents"

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FIELD_RE = re.compile(r"^([A-Za-z_]+):\s*(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class CodexAgent:
    name: str
    description: str
    developer_instructions: str
    source_path: Path


def _rel_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_source_agent(path: Path) -> CodexAgent | None:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        print(f"warn: {_rel_path(path)} sem frontmatter valido; pulando", file=sys.stderr)
        return None
    fields = {m.group(1): m.group(2).strip() for m in FIELD_RE.finditer(match.group(1))}
    if "name" not in fields or "description" not in fields:
        print(f"warn: {_rel_path(path)} sem name/description; pulando", file=sys.stderr)
        return None
    return CodexAgent(
        name=fields["name"],
        description=fields["description"],
        developer_instructions=text[match.end() :].rstrip(),
        source_path=path,
    )


def discover_source_agents(agents_dir: Path = CLAUDE_AGENTS_DIR) -> list[CodexAgent]:
    agents: list[CodexAgent] = []
    for path in sorted(agents_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        agent = _parse_source_agent(path)
        if agent is not None:
            agents.append(agent)
    return agents


def _toml_basic_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_literal_multiline(value: str) -> str:
    if "'''" in value:
        raise ValueError("developer_instructions nao pode conter tres aspas simples")
    return "'''\n" + value.rstrip() + "\n'''"


def render_codex_agent(agent: CodexAgent) -> str:
    source = _rel_path(agent.source_path)
    lines = [
        "# Auto-gerado por dev/sync_codex_agents.py.",
        f"# Fonte: {source}. Edite o .md fonte, nao este TOML.",
        f"name = {_toml_basic_string(agent.name)}",
        f"description = {_toml_basic_string(agent.description)}",
        "developer_instructions = " + _toml_literal_multiline(agent.developer_instructions),
        "",
    ]
    rendered = "\n".join(lines)
    if tomllib is not None:
        tomllib.loads(rendered)
    return rendered


def expected_codex_files(
    agents: list[CodexAgent], codex_agents_dir: Path = CODEX_AGENTS_DIR
) -> dict[Path, str]:
    return {codex_agents_dir / f"{agent.name}.toml": render_codex_agent(agent) for agent in agents}


def _existing_codex_files(codex_agents_dir: Path) -> set[Path]:
    return set(codex_agents_dir.glob("*.toml")) if codex_agents_dir.exists() else set()


def sync_codex_agents(claude_agents_dir: Path, codex_agents_dir: Path) -> int:
    codex_agents_dir.mkdir(parents=True, exist_ok=True)
    expected = expected_codex_files(discover_source_agents(claude_agents_dir), codex_agents_dir)
    changed = 0
    for path, content in expected.items():
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            changed += 1
    for stale_path in sorted(_existing_codex_files(codex_agents_dir) - set(expected)):
        stale_path.unlink()
        changed += 1
    print(f"OK: .codex/agents sincronizado ({len(expected)} agentes, {changed} mudancas)")
    return 0


def check_codex_agents(claude_agents_dir: Path, codex_agents_dir: Path) -> int:
    expected = expected_codex_files(discover_source_agents(claude_agents_dir), codex_agents_dir)
    existing = _existing_codex_files(codex_agents_dir)
    stale = [
        path
        for path, content in expected.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    extra = sorted(existing - set(expected))
    if not stale and not extra:
        print("OK: .codex/agents sincronizado com .claude/agents")
        return 0
    for path in stale + extra:
        print(f"fora de sync: {_rel_path(path)}", file=sys.stderr)
    print("Rode `python3 dev/sync_codex_agents.py` e commite o diff.", file=sys.stderr)
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="falha se .codex/agents divergir")
    parser.add_argument("--claude-agents-dir", type=Path, default=CLAUDE_AGENTS_DIR)
    parser.add_argument("--codex-agents-dir", type=Path, default=CODEX_AGENTS_DIR)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.check:
        return check_codex_agents(args.claude_agents_dir, args.codex_agents_dir)
    return sync_codex_agents(args.claude_agents_dir, args.codex_agents_dir)


if __name__ == "__main__":
    sys.exit(main())
