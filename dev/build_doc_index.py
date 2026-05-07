#!/usr/bin/env python3
"""Regenera índices materializados em docs/_MOC/_generated/ a partir do frontmatter das notas."""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
GENERATED_DIR = DOCS / "_MOC" / "_generated"

# Diretórios da vault que NÃO devem ser indexados.
# Inclui o próprio output do codegen (evita auto-referência) e legados que
# permanecem como Markdown plano durante a transição (Fases 2-5 do plano).
SKIP_DIRS: frozenset[str] = frozenset(
    {
        "_MOC",
        "_schemas",
        "archive",
        "agent_prompts",
        "audits",
        "runbooks",
        "api",
    }
)

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SPRINT_DIR_RE = re.compile(r"^([A-Z])(\d+)$")

HEADER_LINES: tuple[str, str] = (
    "> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.",
    "> Para regenerar: `python3 dev/build_doc_index.py --inline`.",
)


@dataclass(frozen=True)
class Note:
    """Nota da vault com frontmatter parseado e tipado."""

    path: Path
    id: str
    type: str
    status: str
    title: str
    sprint: str | None = None
    plan: str | None = None
    tags: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)


def parse_frontmatter(md_path: Path) -> dict[str, Any] | None:
    """Extrai bloco YAML entre `---` no topo do arquivo. None se ausente ou inválido."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"warn: falha ao ler {md_path}: {exc}", file=sys.stderr)
        return None
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        print(f"warn: frontmatter YAML inválido em {md_path}: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        return None
    return data


def _to_note(md_path: Path, fm: dict[str, Any]) -> Note | None:
    """Converte frontmatter dict em Note. None se faltar campo essencial `type`."""
    type_ = fm.get("type")
    if not isinstance(type_, str) or not type_.strip():
        return None
    tags = fm.get("tags") or []
    tags_tuple = tuple(str(t) for t in tags) if isinstance(tags, list) else ()
    sprint = fm.get("sprint")
    plan = fm.get("plan")
    return Note(
        path=md_path,
        id=str(fm.get("id", "")),
        type=type_,
        status=str(fm.get("status", "")),
        title=str(fm.get("title", "")),
        sprint=str(sprint) if sprint is not None else None,
        plan=str(plan) if plan is not None else None,
        tags=tags_tuple,
        raw=fm,
    )


def _is_skipped(md_path: Path, docs_root: Path) -> bool:
    """True se o arquivo está em diretório legado/gerado que não deve ser indexado."""
    try:
        rel_parts = md_path.relative_to(docs_root).parts
    except ValueError:
        return True
    return bool(rel_parts) and rel_parts[0] in SKIP_DIRS


def collect_notes(docs_root: Path) -> list[Note]:
    """Walk docs/ procurando *.md com frontmatter; pula diretórios em SKIP_DIRS."""
    notes: list[Note] = []
    for md_path in sorted(docs_root.rglob("*.md")):
        if _is_skipped(md_path, docs_root):
            continue
        fm = parse_frontmatter(md_path)
        if fm is None:
            continue
        note = _to_note(md_path, fm)
        if note is not None:
            notes.append(note)
    return notes


def _rel_path(note: Note) -> str:
    """Path relativo a docs/ com forward slashes (estável cross-OS)."""
    return note.path.relative_to(DOCS).as_posix()


def _header(title: str) -> list[str]:
    """Bloco de cabeçalho padrão (header de aviso + título h1)."""
    return [HEADER_LINES[0], HEADER_LINES[1], "", f"# {title}", ""]


def _join(lines: list[str]) -> str:
    """Junta linhas com `\n` e garante trailing newline único."""
    return "\n".join(lines).rstrip() + "\n"


def build_index_md(notes: list[Note]) -> str:
    """Gera INDEX.md — 1 linha por nota em tabela markdown."""
    lines = _header("Índice geral da vault")
    if not notes:
        lines.append("_Nenhuma nota com frontmatter indexada ainda._")
        return _join(lines)
    lines.append("| id | type | status | sprint | título | path |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for note in sorted(notes, key=lambda n: (n.type, n.id, _rel_path(n))):
        sprint = note.sprint or ""
        lines.append(
            f"| {note.id} | {note.type} | {note.status} | {sprint} "
            f"| {note.title} | `{_rel_path(note)}` |"
        )
    return _join(lines)


# Renderers vivem em _<name>_renderer.py para manter este módulo <500 linhas
# (guideline CLAUDE.md). F2.F deletará dev/build_adr_toc.py.
try:
    from _adr_index_renderer import (  # noqa: E402
        _load_adr_categories,
        category_for_adr,
        render_adr_index,
    )
    from _changelog_recent_renderer import render_changelog_recent  # noqa: E402
    from _plan_progress_renderer import render_plan_progress  # noqa: E402
    from _sprint_current_renderer import render_sprint_current  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover
    from dev._adr_index_renderer import (  # noqa: E402
        _load_adr_categories,
        category_for_adr,
        render_adr_index,
    )
    from dev._changelog_recent_renderer import render_changelog_recent  # noqa: E402
    from dev._plan_progress_renderer import render_plan_progress  # noqa: E402
    from dev._sprint_current_renderer import render_sprint_current  # noqa: E402


def build_adr_index_md(notes: list[Note]) -> str:
    """Gera ADR_INDEX.md — ADRs agrupadas por categoria + status com sumário."""
    adrs = [n for n in notes if n.type == "adr"]
    return _join(render_adr_index(adrs, _header))


def _available_sprint_dirs(docs_root: Path) -> set[str]:
    """Conjunto de diretórios `docs/sprint/<X>/` que casam com SPRINT_DIR_RE."""
    sprint_root = docs_root / "sprint"
    if not sprint_root.is_dir():
        return set()
    return {
        child.name
        for child in sprint_root.iterdir()
        if child.is_dir() and SPRINT_DIR_RE.match(child.name)
    }


def build_sprint_current_md(notes: list[Note]) -> str:
    """Gera SPRINT_CURRENT.md — lanes ready/open/in_progress da sprint corrente."""
    lanes = [n for n in notes if n.type == "lane"]
    available = _available_sprint_dirs(DOCS)
    return _join(render_sprint_current(lanes, available, _header))


def build_changelog_recent_md(notes: list[Note]) -> str:
    """Gera CHANGELOG_RECENT.md — entries dos últimos 14 dias agregados por dia."""
    entries = [n for n in notes if n.type == "changelog-entry"]
    return _join(render_changelog_recent(entries, _header))


def build_roadmap_md(notes: list[Note]) -> str:
    """Gera ROADMAP.md — referência leve para `docs/reference/PHASES.md` (fonte estável)."""
    lines = _header("Roadmap F0-F11")
    lines.append("Tabela completa em [`docs/reference/PHASES.md`](../../reference/PHASES.md).")
    lines.append("")
    lines.append(
        "Sprint corrente em [`SPRINT_CURRENT.md`](SPRINT_CURRENT.md); planos abertos em "
        "[`PLAN_PROGRESS.md`](PLAN_PROGRESS.md)."
    )
    return _join(lines)


def build_plan_progress_md(notes: list[Note]) -> str:
    """Gera PLAN_PROGRESS.md — sub-agrupa plans por status + lista lanes por plano."""
    plans = [n for n in notes if n.type == "plan"]
    lanes = [n for n in notes if n.type == "lane"]
    return _join(render_plan_progress(plans, lanes, _header))


def regenerate_all(docs_root: Path) -> dict[str, str]:
    """Retorna `{filename: content}` para os 6 arquivos materializados."""
    notes = collect_notes(docs_root)
    return {
        "INDEX.md": build_index_md(notes),
        "ADR_INDEX.md": build_adr_index_md(notes),
        "SPRINT_CURRENT.md": build_sprint_current_md(notes),
        "CHANGELOG_RECENT.md": build_changelog_recent_md(notes),
        "ROADMAP.md": build_roadmap_md(notes),
        "PLAN_PROGRESS.md": build_plan_progress_md(notes),
    }


def write_files(target_dir: Path, content_by_name: dict[str, str]) -> list[str]:
    """Escreve arquivos no disco; retorna lista dos que mudaram."""
    target_dir.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []
    for name, content in content_by_name.items():
        path = target_dir / name
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing != content:
            path.write_text(content, encoding="utf-8")
            changed.append(name)
    return changed


def _file_drift(name: str, content: str) -> tuple[str, str] | None:
    """Compara um arquivo gerado vs disco. Retorna `(name, diff)` se difere, senão None."""
    path = GENERATED_DIR / name
    if not path.exists():
        return name, f"(ausente — esperado {len(content)} bytes)"
    actual = path.read_text(encoding="utf-8")
    if actual == content:
        return None
    diff = "".join(
        difflib.unified_diff(
            actual.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/docs/_MOC/_generated/{name}",
            tofile=f"b/docs/_MOC/_generated/{name}",
            n=2,
        )
    )
    return name, diff


def check_drift(docs_root: Path) -> tuple[bool, list[tuple[str, str]]]:
    """Compara disco vs regenerado. Retorna `(has_drift, [(filename, diff), ...])`."""
    expected = regenerate_all(docs_root)
    drifted = [d for d in (_file_drift(n, c) for n, c in expected.items()) if d is not None]
    return bool(drifted), drifted


def _print_drift(drifted: list[tuple[str, str]]) -> None:
    """Imprime mensagem de erro + diffs em stderr."""
    print(
        "✗ docs/_MOC/_generated/ fora de sync. Rode "
        "`python3 dev/build_doc_index.py --inline` e commite o diff.",
        file=sys.stderr,
    )
    for name, diff in drifted:
        print(f"\n--- drift em {name} ---", file=sys.stderr)
        print(diff or "(diff vazio)", file=sys.stderr)


def _run_check() -> int:
    if not GENERATED_DIR.exists():
        print(
            f"erro: {GENERATED_DIR.relative_to(REPO_ROOT)} não existe. "
            "Rode `python3 dev/build_doc_index.py --inline` primeiro.",
            file=sys.stderr,
        )
        return 1
    has_drift, drifted = check_drift(DOCS)
    if not has_drift:
        print("✓ docs/_MOC/_generated/ sincronizado com a vault.")
        return 0
    _print_drift(drifted)
    return 1


def _run_inline() -> int:
    expected = regenerate_all(DOCS)
    changed = write_files(GENERATED_DIR, expected)
    if changed:
        print(f"✓ regenerado: {', '.join(changed)}")
    else:
        print("✓ docs/_MOC/_generated/ já sincronizado (nenhuma mudança).")
    return 0


def _build_sprint_current_in_memory(notes: list[Note]) -> str:
    """Variant de build_sprint_current_md sem IO de disco (usada por smoke tests)."""
    lanes = [n for n in notes if n.type == "lane"]
    return _join(render_sprint_current(lanes, set(), _header))


def _build_changelog_recent_with_today(entries: list[Note], today) -> str:
    """Variant injetável de today (usada por smoke tests para janela determinística)."""
    return _join(render_changelog_recent(entries, _header, today_fn=lambda: today))


def _run_self_test() -> int:
    """Roda smoke tests inline (definidos em _test_build_doc_index_smoke.py)."""
    try:
        from _test_build_doc_index_smoke import run_smoke_tests
    except ModuleNotFoundError:  # pragma: no cover
        from dev._test_build_doc_index_smoke import run_smoke_tests
    return run_smoke_tests(
        note_cls=Note,
        build_fn=build_adr_index_md,
        load_fn=_load_adr_categories,
        category_fn=category_for_adr,
        plan_build_fn=build_plan_progress_md,
        sprint_build_fn=_build_sprint_current_in_memory,
        changelog_build_fn=_build_changelog_recent_with_today,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Define a CLI com flags `--check`, `--inline` e `--self-test` mutuamente exclusivas."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 se _MOC/_generated/ está fora de sync",
    )
    parser.add_argument(
        "--inline",
        action="store_true",
        help="regenera in-place sobrescrevendo os 6 arquivos",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="roda smoke tests inline da categorização de ADRs",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    flags_set = sum(int(f) for f in (args.check, args.inline, args.self_test))
    if flags_set > 1:
        print("erro: --check, --inline e --self-test são mutuamente exclusivas.", file=sys.stderr)
        return 2
    if args.check:
        return _run_check()
    if args.inline:
        return _run_inline()
    if args.self_test:
        return _run_self_test()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
