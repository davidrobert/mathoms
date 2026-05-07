#!/usr/bin/env python3
"""Migra docs/<SLUG>_PLAN.md → docs/plan/<SLUG>/_README.md com frontmatter (ADR-182, F3.B)."""
# Para cada plano em PLAN_SPECS: cria docs/plan/<SLUG>/, move via `git mv`
# e injeta frontmatter conforme docs/_schemas/note-plan.schema.json.
# Preserva conteúdo byte-equivalente após o frontmatter (apenas remove
# bloco YAML pré-existente quando incompatível com o schema canônico).
#
# Idempotente: se o destino já existe, o plano correspondente é pulado.

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
PLAN_DIR = DOCS / "plan"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class PlanSpec:
    """Especificação de migração de 1 plano legado para a vault Obsidian-friendly."""

    legacy_filename: str  # ex.: "DOC_REORG_PLAN.md"
    slug_upper: str  # ex.: "DOC_REORG"
    plan_id: str  # ex.: "PLAN-doc-reorg"
    title: str  # H1 humano (extraído do plano original)
    status: str  # in_progress | paused
    created_at: str  # ISO date
    sprint_origem: str | None
    sprint_atual: str | None
    sprints_envolvidas: list[str]
    paused_at: str | None
    pause_reason: str | None
    adrs_canonical: list[str]  # wikilinks `[[ADR-NNN]]`
    extra_tags: list[str] = field(default_factory=list)


# Data de referência para `last_review` (sessão F3.B).
LAST_REVIEW = "2026-05-07"


PLAN_SPECS: list[PlanSpec] = [
    PlanSpec(
        legacy_filename="CENARIOS_ESTRESSE_PLAN.md",
        slug_upper="CENARIOS_ESTRESSE",
        plan_id="PLAN-cenarios-estresse",
        title="Cenários de Estresse — plano canônico",
        status="in_progress",
        created_at="2026-05-06",
        sprint_origem="A8",
        sprint_atual="A11",
        sprints_envolvidas=["A8", "A11"],
        paused_at=None,
        pause_reason=None,
        adrs_canonical=[],
    ),
    PlanSpec(
        legacy_filename="DOC_REORG_PLAN.md",
        slug_upper="DOC_REORG",
        plan_id="PLAN-doc-reorg",
        title="Reorganização da documentação operacional como vault Obsidian-friendly",
        status="in_progress",
        created_at="2026-05-07",
        sprint_origem="A11",
        sprint_atual="A11",
        sprints_envolvidas=["A11"],
        paused_at=None,
        pause_reason=None,
        adrs_canonical=["[[ADR-182]]"],
    ),
    PlanSpec(
        legacy_filename="I18N_PLAN.md",
        slug_upper="I18N",
        plan_id="PLAN-i18n",
        title="Internacionalização (i18n)",
        status="paused",
        created_at="2026-04-25",
        sprint_origem=None,
        sprint_atual=None,
        sprints_envolvidas=[],
        paused_at="2026-04-26",
        pause_reason="Aguarda definição de produto sobre locales prioritários (F12 do roadmap).",
        adrs_canonical=["[[ADR-130]]"],
    ),
    PlanSpec(
        legacy_filename="P1_STRUCTURAL_PLAN.md",
        slug_upper="P1_STRUCTURAL",
        plan_id="PLAN-p1-structural",
        title="P1 — Plano estrutural (motor canônico + pipeline offline)",
        status="paused",
        created_at="2026-04-17",
        sprint_origem=None,
        sprint_atual=None,
        sprints_envolvidas=[],
        paused_at="2026-05-06",
        pause_reason="Substituído por PLAN-platform-review (revisão multi-agente 2026-05-06).",
        adrs_canonical=[],
    ),
    PlanSpec(
        legacy_filename="PLATFORM_REVIEW_PLAN.md",
        slug_upper="PLATFORM_REVIEW",
        plan_id="PLAN-platform-review",
        title="Platform Review Plan — 2026-05-06",
        status="in_progress",
        created_at="2026-05-06",
        sprint_origem="A11",
        sprint_atual="A11",
        sprints_envolvidas=["A11"],
        paused_at=None,
        pause_reason=None,
        adrs_canonical=[],
    ),
    PlanSpec(
        legacy_filename="REPORT_PREMIUM_PLAN.md",
        slug_upper="REPORT_PREMIUM",
        plan_id="PLAN-report-premium",
        title="Elevar `/reports/[id]` ao nível do `EXEMPLO_DE_RELATORIO.html`",
        status="in_progress",
        created_at="2026-04-23",
        sprint_origem=None,
        sprint_atual=None,
        sprints_envolvidas=[],
        paused_at=None,
        pause_reason=None,
        adrs_canonical=["[[ADR-117]]", "[[ADR-129]]"],
    ),
]


def _strip_existing_frontmatter(text: str) -> str:
    """Remove bloco `---...---` no topo se houver. Idempotente."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text
    return text[match.end() :]


def _format_yaml_list(items: list[str]) -> str:
    """Renderiza lista YAML inline. Empty → `[]`."""
    if not items:
        return "[]"
    return "[" + ", ".join(items) + "]"


def _format_yaml_str_list(items: list[str]) -> str:
    """Renderiza lista de strings com aspas duplas — necessário p/ wikilinks `[[X]]`.

    YAML inline interpreta `[[X]]` como lista aninhada `[['X']]`. Aspas
    forçam interpretação literal: `["[[ADR-182]]"]` → `['[[ADR-182]]']`.
    """
    if not items:
        return "[]"
    quoted = [f'"{item}"' for item in items]
    return "[" + ", ".join(quoted) + "]"


def _format_optional(value: str | None) -> str:
    """Renderiza scalar opcional: None → `null`, str → o valor."""
    return "null" if value is None else str(value)


def _quote_if_needed(value: str) -> str:
    """Aplica aspas simples ao título se contém chars que confundem YAML."""
    if any(ch in value for ch in (":", "#", "`", "[", "]", "{", "}", "&", "*", "?")):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    return value


def build_frontmatter(spec: PlanSpec) -> str:
    """Constrói o bloco YAML frontmatter conforme note-plan.schema.json."""
    status_tag = f"status/{spec.status.replace('_', '-')}"
    tags: list[str] = ["type/plan", status_tag, *spec.extra_tags]

    lines: list[str] = ["---"]
    lines.append(f"id: {spec.plan_id}")
    lines.append("type: plan")
    lines.append(f"title: {_quote_if_needed(spec.title)}")
    lines.append(f"status: {spec.status}")
    lines.append(f"created_at: {spec.created_at}")
    lines.append(f"last_review: {LAST_REVIEW}")
    lines.append(f"sprint_origem: {_format_optional(spec.sprint_origem)}")
    lines.append(f"sprint_atual: {_format_optional(spec.sprint_atual)}")
    lines.append(f"sprints_envolvidas: {_format_yaml_list(spec.sprints_envolvidas)}")
    lines.append(f"paused_at: {_format_optional(spec.paused_at)}")
    pause_reason_render = (
        "null" if spec.pause_reason is None else _quote_if_needed(spec.pause_reason)
    )
    lines.append(f"pause_reason: {pause_reason_render}")
    lines.append(f"adrs_canonical: {_format_yaml_str_list(spec.adrs_canonical)}")
    lines.append("tags:")
    for tag in tags:
        lines.append(f"  - {tag}")
    lines.append("---")
    lines.append("")  # linha em branco entre frontmatter e body
    return "\n".join(lines) + "\n"


def _run_git(*args: str, dry_run: bool = False) -> None:
    """Executa comando git no repo. Em dry-run, apenas imprime."""
    cmd = ["git", "-C", str(REPO_ROOT), *args]
    if dry_run:
        print(f"  [dry-run] {' '.join(cmd)}")
        return
    subprocess.run(cmd, check=True)


def migrate_one(spec: PlanSpec, *, dry_run: bool) -> str:
    """Migra 1 plano. Retorna mensagem de status humana."""
    legacy = DOCS / spec.legacy_filename
    target_dir = PLAN_DIR / spec.slug_upper
    target = target_dir / "_README.md"

    if target.exists():
        return f"  ✓ {spec.plan_id}: já migrado em {target.relative_to(REPO_ROOT)}"

    if not legacy.exists():
        raise FileNotFoundError(
            f"plano legado ausente: {legacy.relative_to(REPO_ROOT)} (spec={spec.plan_id})"
        )

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    # `git mv` preserva history. Tem que rodar antes de editar conteúdo.
    rel_legacy = legacy.relative_to(REPO_ROOT)
    rel_target = target.relative_to(REPO_ROOT)
    _run_git("mv", str(rel_legacy), str(rel_target), dry_run=dry_run)

    if dry_run:
        return f"  [dry-run] {spec.plan_id}: {rel_legacy} → {rel_target} (frontmatter pendente)"

    # Lê o conteúdo já no destino, descarta frontmatter pré-existente
    # (ex.: PLATFORM_REVIEW_PLAN.md tinha YAML custom não-schema-compliant)
    # e injeta o frontmatter canônico.
    body = target.read_text(encoding="utf-8")
    body_clean = _strip_existing_frontmatter(body)
    frontmatter = build_frontmatter(spec)
    target.write_text(frontmatter + body_clean, encoding="utf-8")

    return f"  ✓ {spec.plan_id}: {rel_legacy} → {rel_target}"


def _validate_specs() -> None:
    """Sanity check: status `paused` exige paused_at + pause_reason."""
    for spec in PLAN_SPECS:
        if spec.status == "paused":
            if not spec.paused_at or not spec.pause_reason:
                raise ValueError(
                    f"{spec.plan_id}: status=paused requer paused_at e pause_reason "
                    f"(paused_at={spec.paused_at!r}, pause_reason={spec.pause_reason!r})"
                )
        # Validação simples do formato date.
        try:
            date.fromisoformat(spec.created_at)
        except ValueError as exc:
            raise ValueError(f"{spec.plan_id}: created_at inválido — {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="imprime ações sem executar git mv nem reescrita",
    )
    args = parser.parse_args()

    _validate_specs()

    print(f"Migrando {len(PLAN_SPECS)} plano(s) → docs/plan/<SLUG>/_README.md")
    if args.dry_run:
        print("(dry-run)")

    for spec in PLAN_SPECS:
        msg = migrate_one(spec, dry_run=args.dry_run)
        print(msg)

    print("\nFeito.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
