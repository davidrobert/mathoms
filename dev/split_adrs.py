#!/usr/bin/env python3
"""Atomiza docs/DECISIONS.md em docs/adr/NNN-slug.md (ADR-182, F2.A)."""
# Lê o monolito DECISIONS.md, identifica cada bloco `## ADR-NNN — Título`
# (até o próximo `## ADR-` ou EOF, ignorando bloco template em HTML
# comment), extrai metadados via regex (status/date/phase/relates_to/
# supersedes/superseded_by) e gera 1 arquivo por ADR com frontmatter
# completo + body preservado byte-a-byte. Render (slug + frontmatter +
# body) vive em dev/_split_adrs_render.py para manter o arquivo abaixo
# do limite P2 (500 linhas).

from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from pathlib import Path

# Garante que `dev/` esteja no sys.path quando o script é executado direto
# (`python3 dev/split_adrs.py`). Sem isso, o sibling `_split_adrs_render`
# não resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _split_adrs_render import (  # noqa: E402  (import depois de sys.path)
    AdrBlock,
    AdrMeta,
    filename_for,
    render_note,
    title_slug,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS_DEFAULT = REPO_ROOT / "docs" / "DECISIONS.md"
ADR_DIR_DEFAULT = REPO_ROOT / "docs" / "adr"

HEADING_RE = re.compile(r"^## (ADR-(\d{3})(?:-([A-Z]+))?) — (.+)$")
STATUS_LINE_RE = re.compile(
    r"^\*\*Status:\*\*\s*(?:~~)?(?P<status>[A-Za-zÁ-ÿ]+)(?:~~)?" r"(?:\s*\((?P<phase>[^)]+)\))?",
)
DATE_LINE_RE = re.compile(r"\*\*Data:\*\*\s*(\d{4}-\d{2}-\d{2})")
RELATES_LINE_RE = re.compile(
    # Casa header `**Relaciona-se a:** ...` em qualquer posição da linha,
    # incluindo formato inline (`... • **Relaciona-se a:** ADR-X, ADR-Y`).
    r"\*\*(?:Relaciona-se a|Relaciona|Relates to)[^\*]*\*\*[:\s]*(?P<rest>[^*\n]+)",
)
SUPERSEDES_LINE_RE = re.compile(
    # Idem: casa `**Supersedes:** ADR-X` em qualquer posição da linha.
    r"\*\*Supersedes(?:\s+parcial)?(?:mente)?[^\*]*\*\*[:\s]*(?P<rest>[^*\n]+)",
    re.IGNORECASE,
)
SUPERSEDED_BANNER_RE = re.compile(
    # `superseded por/by ADR-Y` ou `Substituído por ADR-Y` (legacy pt-BR).
    # Verbo case-insensitive, mas ADR-NNN case-sensitive — evita capturar
    # slug em url de anchor (`#adr-NNN`) que aparece em links markdown.
    r"(?:[Ss]uperseded|[Ss]ubstitu[ií]d[oa])\s+(?:por|by)"
    r"(?:[ \t]*\n>)?[^\n]{0,80}?\[?(ADR-\d{3}(?:-[A-Z]+)?)",
)
ADR_ID_IN_TEXT_RE = re.compile(r"ADR-(\d{3})(?:-([A-Z]+))?")

DEFAULT_STATUS = "Decidido"
DEFAULT_DATE = "1970-01-01"
ALLOWED_STATUS = {"Decidido", "Proposto", "Roadmap"}


# ----------------------------------------------------------------------
# Parsing de blocos (descarta template em HTML comment)
# ----------------------------------------------------------------------


def _strip_html_comments(text: str) -> str:
    """Substitui conteúdo de comentários HTML por linhas vazias (preserva line numbers)."""

    def _blank(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    return re.sub(r"<!--.*?-->", _blank, text, flags=re.DOTALL)


def _new_block_from_heading(match: re.Match[str], line_no: int) -> AdrBlock:
    """Constrói AdrBlock a partir de um match de HEADING_RE."""
    return AdrBlock(
        id=match.group(1),
        num=match.group(2),
        suffix=match.group(3),
        title=match.group(4).strip(),
        start_line=line_no,
        body_lines=[],
    )


def parse_blocks(content: str) -> list[AdrBlock]:
    """Quebra o markdown em blocos por heading `## ADR-`. Ignora bloco em HTML comment."""
    lines = _strip_html_comments(content).splitlines()
    blocks: list[AdrBlock] = []
    current: AdrBlock | None = None
    for i, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)
        if heading:
            if current is not None:
                blocks.append(current)
            current = _new_block_from_heading(heading, i)
            continue
        if current is not None:
            current.body_lines.append(line)
    if current is not None:
        blocks.append(current)
    return blocks


# ----------------------------------------------------------------------
# Extração de metadados
# ----------------------------------------------------------------------


def _wikilinks_from_text(text: str) -> list[str]:
    """Extrai cada `ADR-NNN(-X)?` mencionado e devolve `[[ADR-NNN]]` único."""
    seen: list[str] = []
    for m in ADR_ID_IN_TEXT_RE.finditer(text):
        adr_id = f"ADR-{m.group(1)}"
        if m.group(2):
            adr_id = f"{adr_id}-{m.group(2)}"
        wikilink = f"[[{adr_id}]]"
        if wikilink not in seen:
            seen.append(wikilink)
    return seen


def _dedupe(items: list[str]) -> list[str]:
    """Preserva ordem de primeira ocorrência."""
    seen: OrderedDict[str, None] = OrderedDict()
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


def _extract_status_and_phase(line: str) -> tuple[str, str | None]:
    """Lê `**Status:** Decidido (F8.4)` → ('Decidido', 'F8.4')."""
    m = STATUS_LINE_RE.match(line)
    if not m:
        return DEFAULT_STATUS, None
    status = m.group("status")
    phase = m.group("phase")
    if status not in ALLOWED_STATUS:
        return DEFAULT_STATUS, phase
    return status, phase


def _extract_first_date(line: str) -> str | None:
    """Devolve a primeira data ISO encontrada em `**Data:** YYYY-MM-DD`."""
    m = DATE_LINE_RE.search(line)
    return m.group(1) if m else None


def _extract_status_line_meta(body: str) -> tuple[str | None, str | None, str | None]:
    """Procura a linha `**Status:**` no body. Retorna (status, phase, date)."""
    for line in body.splitlines():
        if STATUS_LINE_RE.match(line):
            status, phase = _extract_status_and_phase(line)
            date = _extract_first_date(line)
            return status, phase, date
    return None, None, None


def _extract_explicit_date(body: str) -> str | None:
    """Procura `**Data:** YYYY-MM-DD` em qualquer linha do body."""
    for line in body.splitlines():
        date = _extract_first_date(line)
        if date is not None:
            return date
    return None


def _extract_relates_to(body: str) -> list[str]:
    """Coleta wikilinks de qualquer ocorrência `**Relaciona-se a:** ...` no body."""
    out: list[str] = []
    for m in RELATES_LINE_RE.finditer(body):
        out.extend(_wikilinks_from_text(m.group("rest")))
    return _dedupe(out)


def _extract_supersedes(body: str) -> list[str]:
    """Coleta wikilinks de qualquer `**Supersedes(es) ...** ADR-X` (inline ou heading)."""
    out: list[str] = []
    for m in SUPERSEDES_LINE_RE.finditer(body):
        out.extend(_wikilinks_from_text(m.group("rest")))
    return _dedupe(out)


def _extract_superseded_by(body: str) -> list[str]:
    """Coleta wikilinks de banners `superseded por ADR-Y` ou `Substituído por ADR-Y`."""
    out: list[str] = []
    for m in SUPERSEDED_BANNER_RE.finditer(body):
        out.append(f"[[{m.group(1)}]]")
    return _dedupe(out)


def _resolve_status_and_date(
    block_id: str,
    body: str,
) -> tuple[str, str | None, str, list[str]]:
    """Devolve (status, phase, date, warnings) aplicando defaults com warning."""
    status, phase, date_from_status = _extract_status_line_meta(body)
    warnings: list[str] = []
    if status is None:
        warnings.append(f"{block_id}: linha `**Status:**` ausente — usando default")
        status = DEFAULT_STATUS
    date = date_from_status or _extract_explicit_date(body)
    if date is None:
        warnings.append(f"{block_id}: campo `**Data:**` ausente — usando placeholder")
        date = DEFAULT_DATE
    return status, phase, date, warnings


def extract_meta(block: AdrBlock) -> AdrMeta:
    """Constrói AdrMeta consolidando regex sobre o body completo."""
    body = "\n".join(block.body_lines)
    status, phase, date, warnings = _resolve_status_and_date(block.id, body)
    return AdrMeta(
        status=status,
        phase=phase,
        date=date,
        relates_to=_extract_relates_to(body),
        supersedes=_extract_supersedes(body),
        superseded_by=_extract_superseded_by(body),
        warnings=warnings,
    )


# ----------------------------------------------------------------------
# Resolver de filename (colisões)
# ----------------------------------------------------------------------


def _candidate_filename(block: AdrBlock) -> tuple[str, str, list[str]]:
    """Devolve (slug, filename, warnings) para o bloco — sem checar colisão."""
    slug = title_slug(block.title)
    warnings: list[str] = []
    if not slug:
        slug = "untitled"
        warnings.append(f"{block.id}: slug vazio — usando 'untitled'")
    return slug, filename_for(block, slug), warnings


def resolve_filenames(blocks: list[AdrBlock]) -> tuple[dict[str, str], list[str]]:
    """Mapeia block.id → filename, resolvendo colisões com sufixo `-2`, `-3`."""
    used: set[str] = set()
    out: dict[str, str] = {}
    warnings: list[str] = []
    counter: dict[str, int] = defaultdict(int)
    for block in blocks:
        slug, candidate, slug_warnings = _candidate_filename(block)
        warnings.extend(slug_warnings)
        if candidate in used:
            counter[candidate] += 1
            new_slug = f"{slug}-{counter[candidate] + 1}"
            candidate = filename_for(block, new_slug)
            warnings.append(f"{block.id}: colisão de slug, usando `{candidate}`")
        used.add(candidate)
        out[block.id] = candidate
    return out, warnings


# ----------------------------------------------------------------------
# Detecção de duplicatas no source
# ----------------------------------------------------------------------


def detect_duplicate_ids(blocks: list[AdrBlock]) -> list[str]:
    """Retorna lista de ids duplicados encontrados no source."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for block in blocks:
        if block.id in seen:
            duplicates.append(block.id)
        seen.add(block.id)
    return duplicates


# ----------------------------------------------------------------------
# Stats + escrita
# ----------------------------------------------------------------------


@dataclass
class SplitStats:
    """Estatísticas do split (para o reporte final)."""

    total: int
    proposto: int
    roadmap: int
    with_phase: int
    with_supersedes: int
    with_superseded_by: int


def _compute_stats(blocks: list[AdrBlock], metas: dict[str, AdrMeta]) -> SplitStats:
    """Agrega contadores que entram no reporte de F2.A."""
    return SplitStats(
        total=len(blocks),
        proposto=sum(1 for b in blocks if metas[b.id].status == "Proposto"),
        roadmap=sum(1 for b in blocks if metas[b.id].status == "Roadmap"),
        with_phase=sum(1 for b in blocks if metas[b.id].phase),
        with_supersedes=sum(1 for b in blocks if metas[b.id].supersedes),
        with_superseded_by=sum(1 for b in blocks if metas[b.id].superseded_by),
    )


def _write_notes(
    blocks: list[AdrBlock],
    metas: dict[str, AdrMeta],
    filenames: dict[str, str],
    out_dir: Path,
) -> list[str]:
    """Escreve cada nota em `out_dir/<filename>`. Retorna mensagens de progresso."""
    out_dir.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    for block in blocks:
        target = out_dir / filenames[block.id]
        content = render_note(block, metas[block.id])
        existed = target.exists()
        target.write_text(content, encoding="utf-8")
        marker = " (sobrescrito)" if existed else ""
        messages.append(f"  {filenames[block.id]}  ({content.count(chr(10)) + 1} linhas){marker}")
    return messages


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    """Constrói o parser CLI."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input",
        type=Path,
        default=DECISIONS_DEFAULT,
        help=f"Source markdown (default: {DECISIONS_DEFAULT.relative_to(REPO_ROOT)})",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ADR_DIR_DEFAULT,
        help=f"Diretório destino (default: {ADR_DIR_DEFAULT.relative_to(REPO_ROOT)})",
    )
    return p


def _print_warnings(warnings: list[str]) -> None:
    """Imprime warnings em stderr."""
    for w in warnings:
        print(f"warn: {w}", file=sys.stderr)


def _print_summary(stats: SplitStats, out_dir: Path) -> None:
    """Reporta totais ao final."""
    rel = out_dir.relative_to(REPO_ROOT) if out_dir.is_absolute() else out_dir
    print(f"OK {stats.total} arquivos gerados em {rel}/")
    print(
        f"  Proposto={stats.proposto} Roadmap={stats.roadmap} "
        f"com_phase={stats.with_phase} "
        f"supersedes={stats.with_supersedes} superseded_by={stats.with_superseded_by}"
    )


def _print_progress(messages: list[str]) -> None:
    """Imprime as primeiras/últimas 5 linhas de progresso (modo conciso)."""
    for m in messages[:5]:
        print(m)
    if len(messages) > 10:
        print(f"  ... ({len(messages) - 10} arquivos omitidos do log) ...")
    for m in messages[-5:]:
        print(m)


def main() -> int:
    """Orquestra split: parse → meta → filename → write → summary."""
    args = _build_argparser().parse_args()
    content = args.input.read_text(encoding="utf-8")
    blocks = parse_blocks(content)
    print(f"lendo {args.input.relative_to(REPO_ROOT)} ({content.count(chr(10))} linhas)...")
    print(f"{len(blocks)} ADRs identificadas (ADR-{blocks[0].num} .. ADR-{blocks[-1].num}).")
    duplicates = detect_duplicate_ids(blocks)
    if duplicates:
        print(f"erro: ids duplicados no source: {duplicates}", file=sys.stderr)
        return 1
    metas = {b.id: extract_meta(b) for b in blocks}
    all_warnings = [w for b in blocks for w in metas[b.id].warnings]
    filenames, fname_warnings = resolve_filenames(blocks)
    all_warnings.extend(fname_warnings)
    print(f"gerando {args.out_dir.relative_to(REPO_ROOT)}/...")
    _print_progress(_write_notes(blocks, metas, filenames, args.out_dir))
    _print_warnings(all_warnings)
    _print_summary(_compute_stats(blocks, metas), args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
