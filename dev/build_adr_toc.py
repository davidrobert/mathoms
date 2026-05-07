#!/usr/bin/env python3
"""Gera o sumário (Índice por categoria) de docs/DECISIONS.md (idempotente)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS = REPO_ROOT / "docs" / "DECISIONS.md"

HEADING_RE = re.compile(r"^## (ADR-([0-9]+(?:-[A-Z]+)?)) — (.+)$", re.MULTILINE)
TOC_START = "<!-- ADR-TOC-START -->"
TOC_END = "<!-- ADR-TOC-END -->"


def github_slug(heading_text: str) -> str:
    """Algoritmo do GitHub Slugger (espelhado de dev/check_adr_anchors.py)."""
    s = heading_text.lower()
    s = re.sub(r"[^\w\- ]+", "", s, flags=re.UNICODE)
    s = s.replace(" ", "-")
    return s


# Categorias por palavra-chave (primeiro match ganha) + faixa numérica fallback.
# Ordem dentro do dicionário é a ordem de seções no ToC final.
CATEGORIES: list[tuple[str, list[str], list[range]]] = [
    # (Nome da categoria, palavras-chave no título (lowercase), faixas numéricas)
    ("Fundação", ["sqlalchemy", "filesystem", "jwt", "vps", "monorepo", "wrap"], [range(1, 14)]),
    (
        "Persistência",
        ["alembic", "postgresql", "sqlite", "docker volume", "fernet"],
        [range(38, 42)],
    ),
    (
        "Pipeline",
        [
            "threading",
            "vault",
            "e0-route",
            "sync session",
            "config_dir",
            "storage_root",
            "cancelamento",
            "content-first",
            "classificação de documentos",
        ],
        [range(14, 20), range(30, 31), range(75, 76), range(79, 80), range(81, 82)],
    ),
    (
        "Config (materialização legada)",
        ["materializar config", "configs editáveis", "fallback seletivo", "import/export"],
        [range(20, 24)],
    ),
    ("LLM", ["litellm", "byok", "instructor", "retry", "e7 full scope"], [range(24, 29)]),
    ("Task Queue", ["celery", "websocket", "redis para queue", "cancel stage"], [range(29, 33)]),
    (
        "Frontend / Design",
        [
            "react components",
            "dashboard completo",
            "media print",
            "recharts",
            "design system antes",
            "shadcn",
            "tailwind",
            "geist fonts",
            "lucide",
            "intl nativo",
            "migração incremental",
        ],
        [range(33, 55)],
    ),
    (
        "Produto",
        ["transaction explorer", "data lineage", "responsivo", "category override"],
        [range(44, 48)],
    ),
    (
        "Produção & Infra (F7)",
        [
            "fernet app-level",
            "billing",
            "traefik",
            "coverage target",
            "rolling restart",
            "jwt 15min",
            "vps cx32",
            "cve scan",
            "fernet dual key",
            "telemetria",
            "subdomínios mathomsai",
        ],
        [range(7, 8), range(40, 42), range(55, 62), range(108, 109)],
    ),
    (
        "Testing",
        [
            "frontend testing em fase",
            "hardening fintech",
            "backend hardening",
            "test infrastructure",
            "msw sync",
            "premium llm e2e",
            "playwright workspace",
        ],
        [range(62, 72)],
    ),
    ("Operations", ["sub-fase 7e", "auth flows completos"], [range(65, 67)]),
    ("UX / Linguagem", ["códigos internos do pipeline"], [range(68, 69)]),
    ("Multi-tenancy (F8)", ["multi-tenancy"], [range(72, 73)]),
    (
        "Goals & Tasks (F8)",
        [
            "goals como entidade",
            "tasks como entidade",
            "cutover cli",
            "pipeline-adapter como contrato",
        ],
        [range(73, 78)],
    ),
    (
        "Design System & Render (F9 / Report Premium)",
        [
            "design tokens unificados",
            "render nativo react",
            "design tokens",
        ],
        [range(76, 79), range(121, 130)],
    ),
    (
        "Pipeline DDD/SOLID + Infra+Domínio (Sprint A6)",
        [
            "pipelineartifact",
            "artifactstore",
            "content-addressed",
            "eliminar materialização",
            "materializationbridge",
            "stagespec",
            "stageconfig",
            "pipelinedomain",
            "decimal",
            "pydantic para domain",
            "renomear scripts",
            "rename completo",
            "report single-active",
            "lgpd",
            "observabilidade de cutover",
            "extract-then-refactor",
            "caminho b",
            "reuse de analyze",
            "a6d commitment",
            "princípios r12-r17",
            "princípios r18-r20",
            "teste manual",
            "e15c",
            "llm stages escrevem",
            "opt-in db artifacts",
            "remoção de materializationbridge",
            "auth portability",
            "stateless-rigoroso",
            "pipeline-as-service",
            "convenções go",
            "skeleton go",
            "domain events",
            "f7f-local",
            "flip do default",
            "livestep",
            "readers db-first",
        ],
        [range(82, 121)],
    ),
    ("Internacionalização (F12)", ["internacionalização"], [range(130, 131)]),
    (
        "Report Premium (F-pós, ondas v1/v2)",
        [
            "scripts/e6_render",
            "ssr standalone",
            "descontinuação completa",
            "report referencia",
            "lifecycle scoping",
            "transferencias_internas",
            "ui de edição",
            "snapshotchangelogbuilder",
            "section_summaries",
            "finalização migração recharts",
            "supervisão cto",
        ],
        [range(122, 130), range(131, 134), range(139, 140), range(144, 145), range(148, 149)],
    ),
    (
        "Sprint A7 — Rules-as-Code & Cutover",
        [
            "configstore",
            "versionamento temporal de séries fiscais",
            "decision aggregate",
            "catalog + override resolver",
            "docs/methodology",
            "rules-as-code",
            "7 categorias canonical",
            "source hierarchy",
            "milhas",
        ],
        [range(134, 138), range(143, 148)],
    ),
    (
        "Decisões metodológicas pós-auditoria (Roadmap v2)",
        [
            "goal if schema v2",
            "goal alocação-alvo schema v2",
            "toggle `imoveis_no_if`",
            "imoveis_no_if",
        ],
        [range(140, 143)],
    ),
    (
        "Sprint A10 — `goals.json` cutover final",
        [
            "rules-as-code consolidation goals.json",
            "risk aggregate workspace-scoped",
            "decision aggregate — extensão de schema",
            "goals.json cutover final via stageconfig",
            "goals.json removido de `_archive/`",
        ],
        [range(177, 182)],
    ),
]


# Overrides por número quando a heurística pega mal (ordem de cima vence).
# Mantém o script idempotente sem complicar demais a regra geral.
OVERRIDES: dict[int, str] = {
    7: "Produção & Infra (F7)",  # ADR-007 Fernet criptografia (não Fundação)
    40: "Produção & Infra (F7)",  # Billing
    41: "Produção & Infra (F7)",  # Traefik
    57: "Produção & Infra (F7)",  # JWT 15min/refresh 7d
    58: "Produção & Infra (F7)",  # VPS CX32
    60: "Produção & Infra (F7)",  # Fernet dual key
    65: "Operations",  # 7E operational readiness
    66: "Operations",  # Auth flows beta blockers
    68: "UX / Linguagem",  # códigos internos não vazam
    76: "Design System & Render (F9 / Report Premium)",
    77: "Goals & Tasks (F8)",
    78: "Design System & Render (F9 / Report Premium)",
    80: "Pipeline",  # incremental extraction
    106: "Pipeline DDD/SOLID + Infra+Domínio (Sprint A6)",
    109: "Pipeline DDD/SOLID + Infra+Domínio (Sprint A6)",  # auth portability A6f.5a
    116: "Produção & Infra (F7)",  # F7F-Local
    138: "Sprint A7 — Rules-as-Code & Cutover",  # supervisão CTO Sprint A7
    139: "Frontend / Design",
    144: "Report Premium (F-pós, ondas v1/v2)",
    148: "Report Premium (F-pós, ondas v1/v2)",
    177: "Sprint A10 — `goals.json` cutover final",  # rules-as-code consolidation
    178: "Sprint A10 — `goals.json` cutover final",  # Risk aggregate
    179: "Sprint A10 — `goals.json` cutover final",  # Decision schema extension
    180: "Sprint A10 — `goals.json` cutover final",  # StageConfig bundle cutover
    181: "Sprint A10 — `goals.json` cutover final",  # cleanup _archive + forbidden_paths
    # Override força "Outras" porque keyword "vault" pegaria categoria "Pipeline"
    # (ADR-015 "vault por workspace"). Quando cluster docs/vault crescer, criar
    # categoria própria via CATEGORIES (OVERRIDES sozinho não cria categoria nova).
    182: "Outras",  # ADR-182 vault de documentação operacional Obsidian-friendly
}


def categorize(adr_id: str, num: int, title: str) -> str:
    if num in OVERRIDES:
        return OVERRIDES[num]
    title_lower = title.lower()
    for cat, keywords, ranges in CATEGORIES:
        if _matches_keyword(keywords, title_lower) or _matches_range(ranges, num):
            return cat
    return "Outras"


def _matches_keyword(keywords: list[str], title_lower: str) -> bool:
    return any(kw in title_lower for kw in keywords)


def _matches_range(ranges: list[range], num: int) -> bool:
    return any(num in r for r in ranges)


def build_toc(content: str) -> str:
    """Retorna o ToC em markdown."""
    matches = list(HEADING_RE.finditer(content))
    if not matches:
        return ""

    by_category: dict[str, list[tuple[str, str, str]]] = {}
    for m in matches:
        adr_id = m.group(1)
        try:
            num = int(re.match(r"(\d+)", m.group(2)).group(1))
        except (AttributeError, ValueError):
            num = 0
        title = m.group(3).strip()
        cat = categorize(adr_id, num, title)
        full_heading = f"{adr_id} — {title}"
        slug = github_slug(full_heading)
        by_category.setdefault(cat, []).append((adr_id, title, slug))

    # Ordenar entradas dentro de cada categoria por id numérico
    def adr_sort_key(entry: tuple[str, str, str]) -> tuple[int, str]:
        m = re.match(r"ADR-(\d+)(?:-([A-Z]+))?", entry[0])
        if not m:
            return (0, "")
        return (int(m.group(1)), m.group(2) or "")

    for cat in by_category:
        by_category[cat].sort(key=adr_sort_key)

    # Ordem de saída: a ordem de CATEGORIES + "Outras" no fim
    ordered_cats = [c[0] for c in CATEGORIES]
    if "Outras" in by_category:
        ordered_cats.append("Outras")

    lines: list[str] = ["## Índice por categoria", ""]
    for cat in ordered_cats:
        if cat not in by_category:
            continue
        lines.append(f"**{cat}:**")
        # Cada ADR em formato compacto `[D{num}](#slug)` separado por espaço
        compact = []
        for adr_id, title, slug in by_category[cat]:
            short_id = adr_id.replace("ADR-0", "D").replace("ADR-", "D")
            compact.append(f"[{short_id}](#{slug})")
        lines.append(" ".join(compact))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def inject(content: str, new_toc: str) -> str:
    """Substitui o bloco entre TOC_START/TOC_END pelo ToC novo."""
    pattern = re.compile(
        re.escape(TOC_START) + r".*?" + re.escape(TOC_END),
        re.DOTALL,
    )
    replacement = f"{TOC_START}\n\n{new_toc}\n{TOC_END}"
    if not pattern.search(content):
        raise SystemExit(
            f"erro: marcações {TOC_START!r} / {TOC_END!r} não encontradas em "
            f"{DECISIONS.relative_to(REPO_ROOT)}. Insira-as manualmente onde "
            f"o ToC deve aparecer antes de rodar com --inline."
        )
    return pattern.sub(replacement, content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--file",
        type=Path,
        default=DECISIONS,
        help="Caminho do markdown (default: docs/DECISIONS.md)",
    )
    parser.add_argument("--inline", action="store_true", help="Injetar ToC no arquivo")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 se ToC atual diferir do gerado (para CI/pre-commit)",
    )
    args = parser.parse_args()

    content = args.file.read_text(encoding="utf-8")
    new_toc = build_toc(content)

    if args.check:
        try:
            new_content = inject(content, new_toc)
        except SystemExit as e:
            print(e, file=sys.stderr)
            return 1
        if new_content != content:
            print(
                "✗ ToC desatualizado. Rode `python3 dev/build_adr_toc.py --inline` "
                "e commite o diff.",
                file=sys.stderr,
            )
            return 1
        print("✓ ToC sincronizado")
        return 0

    if args.inline:
        new_content = inject(content, new_toc)
        if new_content != content:
            args.file.write_text(new_content, encoding="utf-8")
            print(f"✓ ToC reescrito em {args.file}")
        else:
            print("✓ ToC já sincronizado (nenhuma mudança)")
        return 0

    print(new_toc, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
