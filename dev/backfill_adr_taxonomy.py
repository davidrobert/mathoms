#!/usr/bin/env python3
"""Backfill de taxonomia hierárquica em frontmatter de ADRs em docs/adr/ (Crítica 1 PM review)."""
# Heurística determinística para adicionar tags `area/*`, `methodology/*`, `phase/*`.
# Modos:
#   --dry-run  imprime diff sem aplicar (default seguro).
#   --apply    aplica em docs/adr/.
#   --report   após pass: lista ADRs ainda sem area/* (manual review).
# Regras defensivas: nunca remove tags; pula ADR que já tem area/*; ordem alfabética.

from __future__ import annotations

import argparse
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "docs" / "adr"

# Ordem importa só p/ legibilidade do diff; lookup é set-based.
AREA_KEYWORDS: dict[str, list[str]] = {
    "money": [
        "decimal",
        "money",
        "currency",
        "moeda",
        "moedas",
        "BRL",
        "USD",
        "EUR",
        "valuation",
        "MoneyBRL",
        "MoneyUSD",
        "Decimal(",
    ],
    "auth": [
        "JWT",
        "OAuth",
        "password",
        "session",
        "vault",
        "Fernet",
        "BYOK",
        "auth flow",
        "refresh token",
        "httpOnly cookie",
        "MultiFernet",
    ],
    "persistence": [
        "Alembic",
        "SQLAlchemy",
        "migration",
        "schema",
        "Postgres",
        "SQLite",
        "ORM",
        "FK",
        "ConfigStore",
        "StageConfig",
        "DBArtifactStore",
    ],
    "pipeline": [
        # Descritivos (canônicos pós-F9.2, ADR-093):
        "audit_documents",
        "unlock_documents",
        "route_documents",
        "extract_members",
        "extract_baseline",
        "consolidate_baseline",
        "extract_irpf_full",
        "extract_invoices",
        "extract_statements",
        "extract_with_llm",
        "reconcile_transactions",
        "categorize_transactions",
        "analyze_finances",
        "generate_narratives",
        "validate_cross",
        "review_finances",
        "apply_review",
        # Compat: ADRs pre-F9.2 usam E0..E7
        "E0",
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
        "E7",
        # Genéricos
        "pipeline",
        "stage",
        "ETL",
        "STAGE_REGISTRY",
        "StageSpec",
    ],
    "frontend": [
        "Next.js",
        "Next-intl",
        "React",
        ".tsx",
        "design token",
        "tokens.json",
        "shadcn",
        "Tailwind",
        "Vitest",
        "Recharts",
        "Chart.js",
        "Playwright",
        "Geist",
        "font",
        "Lucide",
        "PWA",
        "responsivo",
        "Intl",
    ],
    "backend": [
        "FastAPI",
        "Celery",
        "endpoint",
        "router",
        "DDD",
        "use case",
        "application layer",
        "Pydantic",
        "domain service",
        "Redis",
        "queue",
        "pub/sub",
        "background thread",
        "monorepo",
    ],
    "llm": [
        "LLM",
        "instructor",
        "structured output",
        "Anthropic",
        "Claude",
        "prompt",
        "ANTHROPIC_API_KEY",
        "LiteLLM",
        "needs_review",
        "LLMCallLog",
    ],
    "security": [
        "LGPD",
        "encryption",
        "hardening",
        "PII",
        "rate limit",
        "CSRF",
        "CORS",
        "prompt injection",
        "secret",
    ],
    "observability": [
        "logging",
        "OpenTelemetry",
        "OTel",
        "metrics",
        "trace",
        "Sentry",
        "structured log",
        "MathomsJsonFormatter",
    ],
    "testing": [
        "Playwright",
        "Vitest",
        "pytest",
        "fixture",
        "golden",
        "snapshot test",
        "MSW",
        "smoke test",
        "E2E",
    ],
    "docs": [
        "vault",
        "Obsidian",
        "MOC",
        "wikilink",
        "frontmatter",
    ],
    "ops": [
        "deploy",
        "CI/CD",
        "runbook",
        "Hetzner",
        "Docker",
        "Traefik",
        "VPS",
        "Coolify",
        "Cloudflare",
    ],
    "report": [
        "relatório",
        "report premium",
        "PDF Playwright",
        "ScoreCard",
        "EXEMPLO_DE_RELATORIO",
        "PrintCSS",
        "report nativo",
        "narrativa",
        "S1.",
        "S2.",
        "S5.",
        "S6.",
    ],
    "methodology": [
        "rules-as-code",
        "domain rule",
        "FORMULAS",
        "methodology_constants",
        "PLANNING_CONTEXT",
    ],
    "multitenancy": [
        "workspace",
        "tenant",
        "multi-tenant",
        "scoping",
        "workspace_id",
    ],
}

METHODOLOGY_KEYWORDS: dict[str, list[str]] = {
    "perini": ["Perini", "Bruno Perini", "Viver de Renda", "TRS"],
    "cerbasi": ["Cerbasi", "Gustavo Cerbasi", "Equilíbrio Financeiro"],
    "auvp": ["AUVP", "Raul Sena"],
}

PHASE_RE = re.compile(r"\((?:Sprint\s+)?([AF]\d+(?:[a-z]\d?)?(?:\.\d+[a-z]?)?)\)")
SAMPLE_SEED = 42
SAMPLE_SIZE = 20

TITLE_WEIGHT = 5
BODY_WEIGHT = 1
SCORE_THRESHOLD = 3
MAX_AREAS_PER_ADR = 3

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class AdrFile:
    """ADR parseado: path + frontmatter + body raw + raw original."""

    path: Path
    fm: dict
    body: str
    raw: str


def parse_adr(path: Path) -> AdrFile | None:
    """Parse ADR file; None se sem frontmatter."""
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return None
    fm_block = match.group(1)
    fm = yaml.safe_load(fm_block) or {}
    if not isinstance(fm, dict):
        return None
    body = raw[match.end() :]
    return AdrFile(path=path, fm=fm, body=body, raw=raw)


def _has_area(tags: list[str]) -> bool:
    return any(t.startswith("area/") for t in tags)


def _count_hits(text: str, keyword: str) -> int:
    return text.lower().count(keyword.lower())


def _score_areas(title: str, body: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for area, keywords in AREA_KEYWORDS.items():
        score = 0
        for kw in keywords:
            score += _count_hits(title, kw) * TITLE_WEIGHT
            score += _count_hits(body, kw) * BODY_WEIGHT
        if score > 0:
            scores[area] = score
    return scores


def detect_areas(title: str, body: str) -> set[str]:
    """Top-N áreas com score ≥ threshold."""
    scores = _score_areas(title, body)
    above = {a: s for a, s in scores.items() if s >= SCORE_THRESHOLD}
    top = sorted(above.items(), key=lambda x: -x[1])[:MAX_AREAS_PER_ADR]
    return {a for a, _ in top}


def detect_methodologies(title: str, body: str) -> set[str]:
    """Methodology raramente >1 por ADR; threshold ≥1 hit."""
    text_lower = (title + "\n" + body).lower()
    found = set()
    for m, keywords in METHODOLOGY_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            found.add(m)
    return found


def detect_phase(text: str) -> str | None:
    match = PHASE_RE.search(text)
    return match.group(1) if match else None


def slug_for_tag(category: str, value: str) -> str:
    """Garante value casa pattern [a-z0-9][a-z0-9-]*."""
    s = value.lower().replace(".", "-").replace("_", "-").replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    return f"{category}/{s}"


@dataclass(frozen=True)
class Proposal:
    skipped: bool
    reason: str = ""
    new_tags: tuple[str, ...] = ()
    areas: tuple[str, ...] = ()


def _collect_new_tags(areas: set[str], methodologies: set[str], phase: str | None) -> set[str]:
    tags: set[str] = {slug_for_tag("area", a) for a in areas}
    tags |= {slug_for_tag("methodology", m) for m in methodologies}
    if phase:
        tags.add(slug_for_tag("phase", phase))
    return tags


def build_proposal(adr: AdrFile) -> Proposal:
    """Decide quais tags adicionar; preserva ADRs já taxonomizadas."""
    existing_tags: list[str] = adr.fm.get("tags") or []
    if _has_area(existing_tags):
        return Proposal(skipped=True, reason="already has area/* tag")
    title = adr.fm.get("title", "")
    body = adr.body
    areas = detect_areas(title, body)
    methodologies = detect_methodologies(title, body)
    phase_detected = None if adr.fm.get("phase") else detect_phase(title + "\n" + body)
    new_tags = _collect_new_tags(areas, methodologies, phase_detected)
    return Proposal(skipped=False, new_tags=tuple(sorted(new_tags)), areas=tuple(sorted(areas)))


def _is_tags_list_item(line: str) -> bool:
    return line.startswith("  -") or line.startswith("    -")


def _skip_tags_list(lines: list[str], start: int) -> int:
    i = start
    while i < len(lines) and _is_tags_list_item(lines[i]):
        i += 1
    return i


def _emit_tags_block(out: list[str], new_tags_full: list[str]) -> None:
    out.append("tags:")
    out.extend(f"  - {tag}" for tag in new_tags_full)


def _replace_tags_in_yaml(fm_block: str, new_tags_full: list[str]) -> str:
    """Reescreve campo tags no bloco YAML preservando outros campos."""
    lines = fm_block.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].lstrip()
        if stripped in ("tags:", "tags: []"):
            _emit_tags_block(out, new_tags_full)
            i = _skip_tags_list(lines, i + 1)
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def apply_proposal(adr: AdrFile, proposal: Proposal) -> str:
    """Retorna conteúdo novo do ADR com tags atualizadas."""
    if proposal.skipped or not proposal.new_tags:
        return adr.raw
    existing_tags: list[str] = adr.fm.get("tags") or []
    merged = sorted(set(existing_tags) | set(proposal.new_tags))
    match = FRONTMATTER_RE.match(adr.raw)
    if match is None:
        return adr.raw
    fm_block = match.group(1)
    new_block = _replace_tags_in_yaml(fm_block, merged)
    return f"---\n{new_block}\n---\n{adr.body}"


def _bucket_for(prop: Proposal) -> str:
    if prop.skipped:
        return "skipped"
    return "no_area" if not prop.new_tags else "proposed"


def render_diff_summary(parsed: list[AdrFile]) -> tuple[list, list, list]:
    """Roda build_proposal + categoriza em 3 buckets."""
    skipped: list = []
    no_area: list = []
    proposed: list = []
    bucket_target = {"skipped": skipped, "no_area": no_area}
    for adr in parsed:
        prop = build_proposal(adr)
        bucket = _bucket_for(prop)
        if bucket == "proposed":
            proposed.append((adr, prop))
        else:
            bucket_target[bucket].append(adr)
    return skipped, no_area, proposed


def cmd_dry_run(parsed: list[AdrFile]) -> int:
    skipped, no_area, proposed = render_diff_summary(parsed)
    print(f"== Análise de {len(parsed)} ADRs ==\n")
    print(f"  ✓ {len(proposed)} ADRs ganham tags")
    print(f"  · {len(skipped)} ADRs já têm area/* (preservadas)")
    print(f"  ⚠ {len(no_area)} ADRs sem keyword detectada\n")
    print(f"== Sample {SAMPLE_SIZE} ADRs com proposta (seed={SAMPLE_SEED}) ==\n")
    rng = random.Random(SAMPLE_SEED)
    sample = rng.sample(proposed, min(SAMPLE_SIZE, len(proposed)))
    for adr, prop in sample:
        title = adr.fm.get("title", "")[:80]
        print(f"{adr.path.name}")
        print(f"  title: {title}")
        print(f"  + tags: {list(prop.new_tags)}\n")
    return 0


def cmd_apply(parsed: list[AdrFile]) -> int:
    skipped, no_area, proposed = render_diff_summary(parsed)
    written = 0
    for adr, prop in proposed:
        new_content = apply_proposal(adr, prop)
        if new_content != adr.raw:
            adr.path.write_text(new_content, encoding="utf-8")
            written += 1
    print(f"✓ {written} ADRs atualizadas; {len(skipped)} preservadas; {len(no_area)} sem area.")
    return 0


def cmd_report(parsed: list[AdrFile]) -> int:
    """Lista ADRs sem area/* — para review manual."""
    no_area_now = []
    for adr in parsed:
        tags: list[str] = adr.fm.get("tags") or []
        if not _has_area(tags):
            no_area_now.append(adr)
    print(f"== ADRs sem area/* ({len(no_area_now)}) ==\n")
    for adr in no_area_now:
        title = adr.fm.get("title", "")[:80]
        print(f"  {adr.path.name}")
        print(f"    {title}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--report", action="store_true")
    args = ap.parse_args()

    files = sorted(ADR_DIR.glob("*.md"))
    parsed = [a for a in (parse_adr(p) for p in files) if a is not None]

    if args.dry_run:
        return cmd_dry_run(parsed)
    if args.apply:
        return cmd_apply(parsed)
    if args.report:
        return cmd_report(parsed)
    return 1  # unreachable


if __name__ == "__main__":
    sys.exit(main())
