#!/usr/bin/env python3
"""Verifica que filename de cada nota em docs/ casa com `id:` do frontmatter (ADR-182, F1.E)."""
# Strict para adr/lane (245 notas em F2/F4); best-effort com --strict-warnings
# para plan/track/changelog-entry/domain-rule. Exclui _MOC/_generated, _schemas,
# archive, agent_prompts.

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"

# Diretórios excluídos da varredura (gerados, schemas, históricos, prompts).
EXCLUDED_DIRS = (
    DOCS / "_MOC" / "_generated",
    DOCS / "_schemas",
    DOCS / "archive",
    DOCS / "agent_prompts",
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# IDs por tipo (espelha tabela §4.1 do DOC_REORG_PLAN.md).
ADR_ID_RE = re.compile(r"^ADR-(\d{3})(?:-([A-Z]+))?$")
LANE_ID_RE = re.compile(r"^([A-Z]\d+(?:\.\d+[a-z]?)*)$")
PLAN_ID_RE = re.compile(r"^PLAN-([a-z0-9-]+)$")
TRACK_ID_RE = re.compile(r"^TRACK-([a-z0-9-]+)$")
CHG_ID_RE = re.compile(r"^CHG-(\d{4}-\d{2}-\d{2})-([A-Z0-9-]+)$")
RULE_ID_RE = re.compile(r"^RULE-([a-z0-9-]+)$")


# ----------------------------------------------------------------------
# Frontmatter parsing
# ----------------------------------------------------------------------


def parse_frontmatter(md_path: Path) -> dict | None:
    """Extrai o dict YAML do frontmatter ou retorna None se a nota não tem."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


# ----------------------------------------------------------------------
# Validação rigorosa por tipo
# ----------------------------------------------------------------------

SLUG_BODY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _check_adr(note_id: str, stem: str) -> str | None:
    """Valida ADR. Retorna None se ok, ou descrição do esperado."""
    m = ADR_ID_RE.match(note_id)
    if not m:
        return f"id ADR fora do formato canônico (esperado `ADR-NNN` ou `ADR-NNN-X`): {note_id!r}"
    num, suffix = m.group(1), m.group(2)
    expected_prefix = f"{num}-" if not suffix else f"{num}-{suffix.lower()}-"
    expected_pattern = f"{expected_prefix}<slug-lowercase>.md"
    if not stem.startswith(expected_prefix):
        return f"filename esperado `{expected_pattern}`"
    slug = stem[len(expected_prefix) :]
    if not slug or not SLUG_BODY_RE.match(slug):
        return f"slug do filename inválido (esperado lowercase com hífens): {slug!r}"
    return None


def _check_lane(note_id: str, stem: str) -> str | None:
    """Valida lane. Aceita `A10.2`, `A10.2a`, `A10.2.1` etc."""
    if not LANE_ID_RE.match(note_id):
        return (
            f"id de lane fora do formato canônico (esperado `<sprint>.<num>[<letra>]`): {note_id!r}"
        )
    expected_prefix = note_id.replace(".", "-") + "-"
    expected_pattern = f"{expected_prefix}<slug-lowercase>.md"
    if not stem.startswith(expected_prefix):
        return f"filename esperado `{expected_pattern}`"
    slug = stem[len(expected_prefix) :]
    if not slug or not SLUG_BODY_RE.match(slug):
        return f"slug do filename inválido (esperado lowercase com hífens): {slug!r}"
    return None


# ----------------------------------------------------------------------
# Validação best-effort por tipo (warning)
# ----------------------------------------------------------------------


def _check_plan(note_id: str, md_path: Path) -> str | None:
    """Plan: filename é `_README.md` num dir cujo nome casa com `<UPPER_SLUG>`."""
    m = PLAN_ID_RE.match(note_id)
    if not m:
        return f"id PLAN fora do formato canônico (esperado `PLAN-<slug>`): {note_id!r}"
    if md_path.name != "_README.md":
        return f"plan deveria ser `_README.md` num diretório próprio (id={note_id})"
    expected_dir = m.group(1).upper().replace("-", "_")
    actual_dir = md_path.parent.name
    if actual_dir.upper().replace("-", "_") != expected_dir:
        return f"diretório do plano esperado `{expected_dir}/`, encontrado `{actual_dir}/` (id={note_id})"
    return None


def _check_track(note_id: str, stem: str) -> str | None:
    """Track: stem deve conter o slug (sem prefixo `track-`)."""
    m = TRACK_ID_RE.match(note_id)
    if not m:
        return f"id TRACK fora do formato canônico (esperado `TRACK-<slug>`): {note_id!r}"
    slug = m.group(1)
    if stem.lower() != slug:
        return (
            f"filename esperado `{slug}.md` (slug do id sem prefixo `TRACK-`), "
            f"encontrado `{stem}.md`"
        )
    return None


def _check_changelog(note_id: str, stem: str) -> str | None:
    """Changelog entry: stem é `id` ou `id-lowercase`. v1 aceita ambos."""
    if not CHG_ID_RE.match(note_id):
        return (
            f"id de changelog fora do formato canônico "
            f"(esperado `CHG-YYYY-MM-DD-<scope>`): {note_id!r}"
        )
    if stem != note_id and stem != note_id.lower():
        return f"filename esperado `{note_id}.md` ou `{note_id.lower()}.md`, encontrado `{stem}.md`"
    return None


def _check_domain_rule(note_id: str, stem: str) -> str | None:
    """Domain rule: stem é `slug` (sem prefixo `RULE-`) ou `id-lowercase`."""
    m = RULE_ID_RE.match(note_id)
    if not m:
        return f"id RULE fora do formato canônico (esperado `RULE-<slug>`): {note_id!r}"
    slug = m.group(1)
    if stem != slug and stem != note_id.lower():
        return f"filename esperado `{slug}.md` ou `{note_id.lower()}.md`, encontrado `{stem}.md`"
    return None


# ----------------------------------------------------------------------
# Despacho por tipo
# ----------------------------------------------------------------------

# Tipos com validação rigorosa (falha hard).
STRICT_TYPES = {"adr", "lane"}

# Tipos com validação best-effort (warning, não falha em v1).
LENIENT_TYPES = {"plan", "track", "changelog-entry", "domain-rule"}


def check_note(md_path: Path, fm: dict) -> tuple[str | None, str | None]:
    """Valida nota; retorna (erro_hard, warning_lenient) — ambos podem ser None."""
    # Notas sem id E sem type são legado pré-migração; este gate ignora
    # (validate_frontmatter.py é o responsável por exigir frontmatter completo).
    note_id = fm.get("id")
    note_type = fm.get("type")
    if not note_id and not note_type:
        return (None, None)
    if not note_id or not isinstance(note_id, str):
        return (f"frontmatter sem `id:` ou id inválido: {note_id!r}", None)
    if not note_type or not isinstance(note_type, str):
        return (f"frontmatter sem `type:` ou type inválido: {note_type!r}", None)

    stem = md_path.stem

    if note_type == "adr":
        err = _check_adr(note_id, stem)
        return (err, None)
    if note_type == "lane":
        err = _check_lane(note_id, stem)
        return (err, None)
    if note_type == "plan":
        return (None, _check_plan(note_id, md_path))
    if note_type == "track":
        return (None, _check_track(note_id, stem))
    if note_type == "changelog-entry":
        return (None, _check_changelog(note_id, stem))
    if note_type == "domain-rule":
        return (None, _check_domain_rule(note_id, stem))

    # Tipo desconhecido — não bloqueia (gate `validate_frontmatter.py` cobre).
    return (None, None)


# ----------------------------------------------------------------------
# Coleta
# ----------------------------------------------------------------------


def _is_excluded(path: Path) -> bool:
    for excluded in EXCLUDED_DIRS:
        try:
            path.relative_to(excluded)
            return True
        except ValueError:
            continue
    return False


def collect_md_files(root: Path) -> list[Path]:
    """Lista todos os `.md` em `root`, exceto os diretórios excluídos."""
    if not root.exists():
        return []
    out: list[Path] = []
    for md in sorted(root.rglob("*.md")):
        if _is_excluded(md):
            continue
        out.append(md)
    return out


def _resolve_input_paths(args_paths: list[str]) -> list[Path]:
    """Traduz argumentos CLI em lista de `.md` a checar."""
    if not args_paths:
        return collect_md_files(DOCS)
    out: list[Path] = []
    for raw in args_paths:
        p = Path(raw).resolve()
        if p.is_dir():
            out.extend(collect_md_files(p))
        elif p.suffix == ".md" and not _is_excluded(p):
            out.append(p)
    return out


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def _format_error(md_path: Path, fm: dict, err: str) -> str:
    rel = md_path.relative_to(REPO_ROOT) if md_path.is_absolute() else md_path
    note_id = fm.get("id", "<sem id>")
    return (
        f"✗ {rel}\n"
        f"  id no frontmatter: {note_id}\n"
        f"  problema: {err}\n"
        f"  filename atual: {md_path.name}"
    )


def _format_warning(md_path: Path, fm: dict, warn: str) -> str:
    rel = md_path.relative_to(REPO_ROOT) if md_path.is_absolute() else md_path
    note_id = fm.get("id", "<sem id>")
    return f"! {rel} (id={note_id}): {warn}"


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="Arquivos .md ou diretórios. Default: docs/.")
    ap.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Promove warnings (plan/track/changelog/domain-rule) a erro.",
    )
    return ap


def _scan_notes(md_files: list[Path]) -> tuple[list[str], list[str], int]:
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0
    for md in md_files:
        fm = parse_frontmatter(md)
        if fm is None or (not fm.get("id") and not fm.get("type")):
            continue
        checked += 1
        err, warn = check_note(md, fm)
        if err:
            errors.append(_format_error(md, fm, err))
        if warn:
            warnings.append(_format_warning(md, fm, warn))
    return errors, warnings, checked


def main() -> int:
    args = _build_argparser().parse_args()
    md_files = _resolve_input_paths(args.paths)
    errors, warnings, checked = _scan_notes(md_files)
    for w in warnings:
        print(w, file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    if args.strict_warnings:
        errors.extend(warnings)
    if errors:
        print(f"\n✗ {len(errors)} divergência(s) em {checked} nota(s).", file=sys.stderr)
        return 1
    if checked == 0:
        return 0
    print(f"✓ {checked} nota(s) validada(s). Filenames batem com IDs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
