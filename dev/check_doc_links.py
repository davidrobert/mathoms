#!/usr/bin/env python3
"""Valida wikilinks ``[[X]]`` em notas docs/ e detecta órfãs (--check-orphans para falhar)."""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"

# `[[ID]]`, `[[ID|alias]]`, `[[ID#anchor]]`, `[[ID|alias#anchor]]`.
# Captura o ID — parte antes de `|` ou `#`.
WIKILINK_RE = re.compile(r"\[\[([^\]|#\n]+?)(?:\|[^\]\n]+?)?(?:#[^\]\n]+?)?\]\]")

# Diretórios sob `docs/` que não participam do indexador
# (auto-gerados, schemas, arquivo histórico, prompts operacionais).
EXCLUDE_DIRS = {"_MOC/_generated", "_schemas", "archive", "agent_prompts"}

# Notas sob estes diretórios são entrypoints editoriais e nunca contam
# como órfãs (mesmo sem backlink).
ORPHAN_EXEMPT_DIRS = {"_MOC"}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class Note:
    """Nota indexável da vault."""

    path: Path
    id: str | None
    aliases: list[str] = field(default_factory=list)
    type: str | None = None


@dataclass
class WikilinkRef:
    """Ocorrência de um wikilink em uma nota."""

    source: Path
    target_id: str
    line: int
    raw: str


@dataclass
class BrokenLink:
    """Wikilink cujo alvo não foi resolvido."""

    ref: WikilinkRef
    suggestion: str | None


@dataclass(frozen=True)
class MarkdownLinkRef:
    source: Path
    target: str
    line: int
    raw: str


@dataclass(frozen=True)
class BrokenMarkdownLink:
    ref: MarkdownLinkRef


def parse_frontmatter(md_path: Path) -> dict | None:
    """Devolve o YAML frontmatter da nota, ou None se ausente/inválido."""
    text = md_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _is_excluded(rel: Path) -> bool:
    """True se o path relativo cai em algum prefixo excluído."""
    parts = rel.as_posix()
    return any(parts.startswith(prefix) for prefix in EXCLUDE_DIRS)


def _note_from_md(md_path: Path) -> Note | None:
    """Constrói Note do frontmatter; None se não há frontmatter."""
    fm = parse_frontmatter(md_path)
    if fm is None:
        return None
    note_id = fm.get("id")
    aliases = fm.get("aliases") or []
    if not isinstance(aliases, list):
        aliases = [str(aliases)]
    return Note(
        path=md_path,
        id=str(note_id) if note_id is not None else None,
        aliases=[str(a) for a in aliases],
        type=str(fm.get("type")) if fm.get("type") else None,
    )


def collect_notes(docs_root: Path) -> list[Note]:
    """Walk ``docs_root`` indexando notas com frontmatter."""
    notes: list[Note] = []
    if not docs_root.exists():
        return notes
    for md_path in sorted(docs_root.rglob("*.md")):
        rel = md_path.relative_to(docs_root)
        if _is_excluded(rel):
            continue
        note = _note_from_md(md_path)
        if note is not None:
            notes.append(note)
    return notes


def _is_fence_open(line: str) -> str:
    """Devolve o marcador de fence se a linha abre um bloco; '' caso contrário."""
    stripped = line.lstrip()
    if stripped.startswith("```"):
        return "```"
    if stripped.startswith("~~~"):
        return "~~~"
    return ""


def _is_indented_code(line: str) -> bool:
    """True se a linha conta como bloco indentado (4+ espaços ou tab)."""
    return line.startswith("    ") or line.startswith("\t")


def _strip_code_blocks(text: str) -> str:
    """Substitui conteúdo de blocos de código por linhas em branco."""
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in text.splitlines():
        if not in_fence:
            opener = _is_fence_open(line)
            if opener:
                in_fence, fence_marker = True, opener
                out.append("")
                continue
            out.append("" if _is_indented_code(line) else line)
            continue
        if line.lstrip().startswith(fence_marker):
            in_fence = False
        out.append("")
    return "\n".join(out)


def _strip_html_comments(text: str) -> str:
    """Apaga conteúdo de comentários HTML preservando linhas."""

    def _blank(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    return re.sub(r"<!--.*?-->", _blank, text, flags=re.DOTALL)


def _strip_inline_code(text: str) -> str:
    """Apaga conteúdo de código inline (entre backticks) preservando linhas."""
    # Regex: 1+ backticks abrindo, conteúdo sem o mesmo número de backticks, fechando.
    # Simples para o caso comum de single-backtick (que cobre `[[X]]` em prosa).
    return re.sub(r"`[^`\n]+`", lambda m: " " * len(m.group(0)), text)


def _strip_frontmatter_preserving_lines(text: str) -> str:
    """Remove conteúdo do frontmatter mas preserva número de linhas."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text
    blanks = "\n" * match.group(0).count("\n")
    return blanks + text[match.end() :]


def _refs_from_line(source: Path, line: str, lineno: int) -> list[WikilinkRef]:
    """Extrai todos os wikilinks de uma única linha."""
    refs: list[WikilinkRef] = []
    for match in WIKILINK_RE.finditer(line):
        target = match.group(1).strip()
        if not target:
            continue
        refs.append(WikilinkRef(source=source, target_id=target, line=lineno, raw=match.group(0)))
    return refs


def extract_wikilinks(md_path: Path) -> list[WikilinkRef]:
    """Extrai wikilinks da nota, ignorando código (block + inline) e comentários HTML."""
    raw = md_path.read_text(encoding="utf-8")
    text = _strip_frontmatter_preserving_lines(raw)
    text = _strip_html_comments(text)
    text = _strip_code_blocks(text)
    text = _strip_inline_code(text)
    refs: list[WikilinkRef] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        refs.extend(_refs_from_line(md_path, line, lineno))
    return refs


MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]\n]+)\]\(([^)\n]+)\)")
URI_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def _strip_markdown_target(target: str) -> str:
    clean = target.strip().strip("<>")
    clean = clean.split("#", 1)[0]
    clean = clean.split("?", 1)[0]
    return clean.strip()


def _is_relative_markdown_target(target: str) -> bool:
    if not target or target.startswith("#"):
        return False
    if URI_SCHEME_RE.match(target) or target.startswith("/"):
        return False
    return True


def _markdown_refs_from_line(source: Path, line: str, lineno: int) -> list[MarkdownLinkRef]:
    refs: list[MarkdownLinkRef] = []
    for match in MARKDOWN_LINK_RE.finditer(line):
        target = _strip_markdown_target(match.group(2))
        if not _is_relative_markdown_target(target):
            continue
        refs.append(MarkdownLinkRef(source=source, target=target, line=lineno, raw=match.group(0)))
    return refs


def extract_markdown_links(md_path: Path) -> list[MarkdownLinkRef]:
    raw = md_path.read_text(encoding="utf-8")
    text = _strip_frontmatter_preserving_lines(raw)
    text = _strip_html_comments(text)
    text = _strip_code_blocks(text)
    text = _strip_inline_code(text)
    refs: list[MarkdownLinkRef] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        refs.extend(_markdown_refs_from_line(md_path, line, lineno))
    return refs


def collect_markdown_files(docs_root: Path) -> list[Path]:
    files: list[Path] = []
    if not docs_root.exists():
        return files
    for md_path in sorted(docs_root.rglob("*.md")):
        rel = md_path.relative_to(docs_root)
        if _is_excluded(rel):
            continue
        files.append(md_path)
    return files


def find_broken_markdown_links(refs: list[MarkdownLinkRef]) -> list[BrokenMarkdownLink]:
    broken: list[BrokenMarkdownLink] = []
    for ref in refs:
        resolved = (ref.source.parent / ref.target).resolve()
        if resolved.exists():
            continue
        broken.append(BrokenMarkdownLink(ref=ref))
    return broken


def _index_ids(notes: list[Note]) -> tuple[dict[str, Note], list[str]]:
    """Mapeia ``id`` → nota; reporta colisão hard."""
    index: dict[str, Note] = {}
    messages: list[str] = []
    for note in notes:
        if note.id is None:
            continue
        existing = index.get(note.id)
        if existing is not None and existing.path != note.path:
            messages.append(
                f"ERRO: id duplicado '{note.id}' em {_rel(existing.path)} e {_rel(note.path)}"
            )
            continue
        index[note.id] = note
    return index, messages


def _index_aliases(notes: list[Note], index: dict[str, Note]) -> list[str]:
    """Adiciona aliases ao index; reporta duplicação como WARN."""
    messages: list[str] = []
    for note in notes:
        for alias in note.aliases:
            existing = index.get(alias)
            if existing is None:
                index[alias] = note
                continue
            if existing.path == note.path:
                continue
            messages.append(
                f"WARN: alias '{alias}' compartilhado por {_rel(existing.path)} e {_rel(note.path)}"
            )
    return messages


def build_id_index(notes: list[Note]) -> tuple[dict[str, Note], list[str]]:
    """Mapeia ``id``/``aliases`` → nota; devolve (index, mensagens)."""
    index, id_msgs = _index_ids(notes)
    alias_msgs = _index_aliases(notes, index)
    return index, id_msgs + alias_msgs


def find_broken(refs: list[WikilinkRef], index: dict[str, Note]) -> list[BrokenLink]:
    """Lista refs cujo target não está no index, com sugestão."""
    broken: list[BrokenLink] = []
    keys = list(index.keys())
    for ref in refs:
        if ref.target_id in index:
            continue
        matches = difflib.get_close_matches(ref.target_id, keys, n=2, cutoff=0.6)
        suggestion = ", ".join(matches) if matches else None
        broken.append(BrokenLink(ref=ref, suggestion=suggestion))
    return broken


def _is_orphan_exempt(note: Note, docs_root: Path) -> bool:
    """True se a nota está em diretório editorial (ex.: ``docs/_MOC/``)."""
    try:
        rel = note.path.relative_to(docs_root).as_posix()
    except ValueError:
        rel = note.path.as_posix()
    return any(rel.startswith(prefix) for prefix in ORPHAN_EXEMPT_DIRS)


def find_orphans(notes: list[Note], all_refs: list[WikilinkRef], docs_root: Path) -> list[Note]:
    """Notas sem backlink, exceto entrypoints editoriais (``docs/_MOC/``)."""
    referenced = {ref.target_id for ref in all_refs}
    orphans: list[Note] = []
    for note in notes:
        if note.id is None:
            continue
        if _is_orphan_exempt(note, docs_root):
            continue
        labels = {note.id, *note.aliases}
        if labels & referenced:
            continue
        orphans.append(note)
    return orphans


def _rel(path: Path) -> str:
    """Path relativo ao repo root, com fallback absoluto."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _filter_notes(notes: list[Note], paths: list[Path]) -> list[Note]:
    """Filtra notas por paths explícitos (CLI args)."""
    if not paths:
        return notes
    targets = {p.resolve() for p in paths}
    return [n for n in notes if n.path.resolve() in targets]


def _print_broken(broken: list[BrokenLink]) -> None:
    """Imprime broken links no formato esperado."""
    for item in broken:
        print(f"X {_rel(item.ref.source)}:{item.ref.line}")
        print(f"  wikilink: {item.ref.raw}")
        print("  alvo nao encontrado.")
        if item.suggestion:
            print(f"  sugestao: {item.suggestion}")


def _print_orphans(orphans: list[Note]) -> None:
    """Imprime notas órfãs como warning."""
    for note in orphans:
        label = note.id or "(sem id)"
        print(f"! orfa: {_rel(note.path)} ({label})")
        print("   nenhuma outra nota referencia esta.")


def _print_broken_markdown(broken: list[BrokenMarkdownLink]) -> None:
    for item in broken:
        print(f"M {_rel(item.ref.source)}:{item.ref.line}")
        print(f"  markdown: {item.ref.raw}")
        print(f"  path alvo nao encontrado: {item.ref.target}")


def _build_argparser() -> argparse.ArgumentParser:
    """Constrói o parser de CLI."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="*", type=Path, help="Notas específicas (default: docs/).")
    p.add_argument("--check-orphans", action="store_true", help="Falha (exit 1) se houver órfãs.")
    p.add_argument(
        "--report-markdown-links",
        action="store_true",
        help="Reporta markdown links relativos quebrados sem falhar.",
    )
    p.add_argument(
        "--check-markdown-links",
        action="store_true",
        help="Falha se markdown links relativos estiverem quebrados.",
    )
    p.add_argument("--docs-root", type=Path, default=DOCS, help="Override da raiz da vault.")
    return p


def _print_summary(
    notes: list[Note],
    target_refs: list[WikilinkRef],
    broken: list[BrokenLink],
    orphans: list[Note],
    fail: bool,
) -> None:
    """Imprime linha-resumo final."""
    indexable = sum(1 for n in notes if n.id is not None)
    summary = (
        f"{len(notes)} notas, {len(target_refs)} wikilinks, "
        f"{len(broken)} broken, {len(orphans)} orfas (de {indexable} indexaveis)."
    )
    print(f"{'X' if fail else 'OK'} {summary}")


def _collect_all_refs(notes: list[Note]) -> list[WikilinkRef]:
    """Junta wikilinks de todas as notas indexadas."""
    refs: list[WikilinkRef] = []
    for note in notes:
        refs.extend(extract_wikilinks(note.path))
    return refs


def _refs_for_targets(all_refs: list[WikilinkRef], targets: list[Note]) -> list[WikilinkRef]:
    """Filtra wikilinks cuja origem está no conjunto de notas alvo."""
    target_paths = {n.path for n in targets}
    return [r for r in all_refs if r.source in target_paths]


def _target_markdown_files(args: argparse.Namespace) -> list[Path]:
    if args.paths:
        return [path.resolve() for path in args.paths if path.suffix == ".md" and path.is_file()]
    return collect_markdown_files(args.docs_root)


def _collect_markdown_refs(files: list[Path]) -> list[MarkdownLinkRef]:
    refs: list[MarkdownLinkRef] = []
    for path in files:
        refs.extend(extract_markdown_links(path))
    return refs


def _maybe_report_markdown_links(args: argparse.Namespace) -> list[BrokenMarkdownLink]:
    if not (args.report_markdown_links or args.check_markdown_links):
        return []
    broken = find_broken_markdown_links(_collect_markdown_refs(_target_markdown_files(args)))
    _print_broken_markdown(broken)
    print(f"Markdown links relativos quebrados: {len(broken)}")
    return broken


def _run_validation(args: argparse.Namespace) -> int:
    """Pipeline: coleta → index → broken/órfãs → exit code."""
    notes = collect_notes(args.docs_root)
    if not notes:
        print("0 notas indexadas (vault vazia ou pré-Fase 2).")
        return 0
    index, msgs = build_id_index(notes)
    for msg in msgs:
        print(msg)
    targets = _filter_notes(notes, args.paths)
    all_refs = _collect_all_refs(notes)
    target_refs = _refs_for_targets(all_refs, targets)
    broken = find_broken(target_refs, index)
    markdown_broken = _maybe_report_markdown_links(args)
    orphans = find_orphans(targets, all_refs, args.docs_root)
    _print_broken(broken)
    _print_orphans(orphans)
    has_collision = any(m.startswith("ERRO:") for m in msgs)
    fail = bool(
        has_collision
        or broken
        or (args.check_orphans and orphans)
        or (args.check_markdown_links and markdown_broken)
    )
    _print_summary(notes, target_refs, broken, orphans, fail)
    return 1 if fail else 0


def main() -> int:
    """Entrada CLI — devolve exit code (0 ok, 1 broken/orphan/colisão)."""
    args = _build_argparser().parse_args()
    return _run_validation(args)


if __name__ == "__main__":
    sys.exit(main())
