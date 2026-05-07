#!/usr/bin/env python3
"""Auto-gera o catálogo de subagentes em CLAUDE.md a partir de .claude/agents/*.md (W6-T04)."""

# Cada agente tem frontmatter YAML com `name`, `description`, `tools`, `model`.
# Extraímos (slug, role, trigger, not_for) e emitimos um bloco markdown entre
# `<!-- BEGIN auto-gen subagent catalog -->` e `<!-- END auto-gen subagent catalog -->`
# em CLAUDE.md. Arquivos com prefixo `_` (ex.: `_TEMPLATE.md`) são ignorados.
#
# Uso:
#   python3 dev/build_subagent_catalog.py            # imprime no stdout
#   python3 dev/build_subagent_catalog.py --inline   # injeta em CLAUDE.md
#   python3 dev/build_subagent_catalog.py --check    # exit 1 se desatualizado

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

BEGIN_MARK = "<!-- BEGIN auto-gen subagent catalog -->"
END_MARK = "<!-- END auto-gen subagent catalog -->"

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FIELD_RE = re.compile(r"^([A-Za-z_]+):\s*(.+?)\s*$", re.MULTILINE)
TRIGGER_RE = re.compile(r"\b(Use\s+(?:para|ao)|Invoque\s+(?:ao|antes|para))\b[^.]*\.")
NOT_FOR_RE = re.compile(r"\bN[ÃA]O\s+invoque[^.]*\.")

# Abreviações com ponto que NÃO terminam frase. Substituímos por marcador
# antes de quebrar em sentenças e revertemos depois.
ABBREVIATIONS = ("vs.", "ex.", "etc.", "i.e.", "e.g.", "p.ex.")
ABBREV_MARKER = "\x00"


@dataclass(frozen=True)
class Agent:
    slug: str
    role: str
    trigger: str
    not_for: str
    path: Path


def _mask_abbrev(text: str) -> str:
    out = text
    for abbr in ABBREVIATIONS:
        out = out.replace(abbr, abbr.replace(".", ABBREV_MARKER))
    return out


def _unmask_abbrev(text: str) -> str:
    return text.replace(ABBREV_MARKER, ".")


def _rel_or_name(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Extrai pares chave→valor do frontmatter YAML; None se ausente."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return {fm.group(1): fm.group(2).strip() for fm in FIELD_RE.finditer(m.group(1))}


def _split_role(desc_head: str, trig_match: re.Match[str] | None) -> str:
    if trig_match:
        return _unmask_abbrev(desc_head[: trig_match.start()].strip()).rstrip(".") + "."
    first = re.match(r"[^.]*\.", desc_head)
    return _unmask_abbrev(first.group(0).strip() if first else desc_head.strip())


def split_description(desc: str) -> tuple[str, str, str]:
    """Quebra description em (role, trigger, not_for) preservando abreviações comuns."""
    masked = _mask_abbrev(desc)
    not_match = NOT_FOR_RE.search(masked)
    not_for = _unmask_abbrev(not_match.group(0).strip()) if not_match else ""
    desc_head = masked[: not_match.start()].rstrip() if not_match else masked
    trig_match = TRIGGER_RE.search(desc_head)
    trigger = _unmask_abbrev(trig_match.group(0).strip()) if trig_match else ""
    role = _split_role(desc_head, trig_match)
    return role, trigger, not_for


def _load_agent(path: Path) -> Agent | None:
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if not fm or "name" not in fm or "description" not in fm:
        print(f"warn: {_rel_or_name(path)} sem frontmatter válido — pulando", file=sys.stderr)
        return None
    role, trigger, not_for = split_description(fm["description"])
    return Agent(slug=fm["name"], role=role, trigger=trigger, not_for=not_for, path=path)


def discover_agents(agents_dir: Path = AGENTS_DIR) -> list[Agent]:
    """Carrega todos os agentes em agents_dir, ignorando arquivos com prefixo `_`."""
    agents: list[Agent] = []
    for path in sorted(agents_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        agent = _load_agent(path)
        if agent is not None:
            agents.append(agent)
    return agents


def _render_agent_entry(agent: Agent) -> list[str]:
    lines = [f"- **[{agent.slug}]({_rel_or_name(agent.path)})** — {agent.role}"]
    if agent.trigger:
        lines.append(f"  {agent.trigger}")
    if agent.not_for:
        lines.append(f"  {agent.not_for}")
    return lines


_HEADER_LINES = (
    "<!-- Esta lista é auto-gerada por dev/build_subagent_catalog.py. -->",
    "<!-- Para editar, modifique .claude/agents/<slug>.md (frontmatter `description`) e rode: -->",
    "<!--   python3 dev/build_subagent_catalog.py --inline -->",
)


def render_catalog(agents: list[Agent]) -> str:
    """Renderiza o bloco markdown entre BEGIN_MARK e END_MARK."""
    if not agents:
        return f"{BEGIN_MARK}\n\n_Nenhum subagente registrado._\n\n{END_MARK}"
    lines: list[str] = [BEGIN_MARK, "", *_HEADER_LINES, ""]
    for agent in agents:
        lines.extend(_render_agent_entry(agent))
    lines.extend(["", END_MARK])
    return "\n".join(lines)


def inject(content: str, catalog: str) -> str:
    """Substitui o bloco entre BEGIN_MARK/END_MARK pelo catálogo novo."""
    pattern = re.compile(re.escape(BEGIN_MARK) + r".*?" + re.escape(END_MARK), re.DOTALL)
    if not pattern.search(content):
        raise SystemExit(
            f"erro: marcações {BEGIN_MARK!r} / {END_MARK!r} não encontradas em "
            f"{CLAUDE_MD.relative_to(REPO_ROOT)}. Insira-as manualmente onde "
            f"o catálogo deve aparecer antes de rodar com --inline."
        )
    return pattern.sub(catalog, content)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--file", type=Path, default=CLAUDE_MD, help="Caminho do CLAUDE.md")
    p.add_argument("--agents-dir", type=Path, default=AGENTS_DIR, help="Diretório de agentes")
    p.add_argument("--inline", action="store_true", help="Injetar catálogo no arquivo")
    p.add_argument("--check", action="store_true", help="Exit 1 se desatualizado (CI)")
    return p


def _run_check(args: argparse.Namespace, catalog: str) -> int:
    content = args.file.read_text(encoding="utf-8")
    new_content = inject(content, catalog)
    if new_content != content:
        print(
            "✗ Catálogo de subagentes desatualizado. Rode "
            "`python3 dev/build_subagent_catalog.py --inline` e commite o diff.",
            file=sys.stderr,
        )
        return 1
    print("✓ Catálogo de subagentes sincronizado")
    return 0


def _run_inline(args: argparse.Namespace, catalog: str) -> int:
    content = args.file.read_text(encoding="utf-8")
    new_content = inject(content, catalog)
    if new_content != content:
        args.file.write_text(new_content, encoding="utf-8")
        print(f"✓ Catálogo reescrito em {_rel_or_name(args.file)}")
    else:
        print("✓ Catálogo já sincronizado (nenhuma mudança)")
    return 0


def main() -> int:
    args = _build_parser().parse_args()
    catalog = render_catalog(discover_agents(args.agents_dir))
    if args.check:
        try:
            return _run_check(args, catalog)
        except SystemExit as e:
            print(e, file=sys.stderr)
            return 1
    if args.inline:
        return _run_inline(args, catalog)
    print(catalog)
    return 0


if __name__ == "__main__":
    sys.exit(main())
