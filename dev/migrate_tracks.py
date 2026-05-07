#!/usr/bin/env python3
"""Migra docs/agent_prompts/track_*.md para docs/sprint/<X>/tracks/<slug>.md (ADR-182, F3.A).

Walk em docs/agent_prompts/track_*.md (62 arquivos). Para cada track:
  1. Infere sprint do filename (regex de prefixo).
  2. Calcula slug do filename novo (remove prefixo `track_`, troca `_` por `-`).
  3. Move arquivo via `git mv` para docs/sprint/<sprint>/tracks/<slug>.md.
  4. Injeta frontmatter (schema docs/_schemas/note-track.schema.json) no topo.

Status default: `consumed` (lanes em sprints A6-A10 são consumidos; F3.E
ajusta lanes ainda em progresso na sprint corrente para `ready`).

Cross-sprint tracks sem prefixo (`track_onda_*`, `track_irpf_*`,
`track_pipeline_*`, `track_real_estate_*`, `track_report_*`,
`track_platform_*`) caem em A11 (sprint atual).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "docs" / "agent_prompts"
SPRINT_BASE = ROOT / "docs" / "sprint"

# Regras de inferência por prefixo do filename (depois de remover `track_`).
# Ordem importa: mais específico primeiro.
SPRINT_PREFIX_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^a(\d+)[a-z]?\d*[a-z]?_"), "A_DIGITS"),  # a6e3, a7_0, a8, a10
    (re.compile(r"^f(\d+)[a-z]?_"), "F_DIGITS"),  # f7f, f9_0, f9_2a
    (re.compile(r"^w(\d+)t\d+_"), "W_DIGITS"),  # w5t01, w6t05
]

# Sprint default para tracks sem prefixo claro (cross-sprint, sprint atual).
DEFAULT_SPRINT = "A11"

# Tracks sem prefixo que caem no DEFAULT_SPRINT.
UNPREFIXED_PREFIXES = (
    "onda_",
    "pipeline_",
    "irpf_",
    "real_estate_",
    "report_",
    "platform_",
)


@dataclass(frozen=True)
class TrackMapping:
    """Mapeamento source → destination de uma migração de track."""

    source: Path
    sprint: str
    slug: str
    track_id: str
    title: str
    destination: Path


def infer_sprint(stem_after_track: str) -> str:
    """Devolve sprint inferida do stem (sem prefixo `track_`).

    Ex.: 'a6e3_use_cases' → 'A6'; 'a7_0_config_store' → 'A7';
    'w5t01_a11y' → 'W5'; 'f9_2a_pipeline' → 'F9'; 'onda_1_x' → 'A11'.
    """
    # Tenta padrão A<digits>...
    m = re.match(r"^a(\d+)", stem_after_track)
    if m:
        return f"A{m.group(1)}"
    # Padrão F<digits>...
    m = re.match(r"^f(\d+)", stem_after_track)
    if m:
        return f"F{m.group(1)}"
    # Padrão W<digits>t<num>...
    m = re.match(r"^w(\d+)t\d+", stem_after_track)
    if m:
        return f"W{m.group(1)}"
    # Sem prefixo claro: cai no default (sprint atual).
    if any(stem_after_track.startswith(p) for p in UNPREFIXED_PREFIXES):
        return DEFAULT_SPRINT
    # Fallback raw.
    return DEFAULT_SPRINT


def compute_slug(stem_after_track: str) -> str:
    """Converte 'a6e3_use_cases' → 'a6e3-use-cases'."""
    return stem_after_track.replace("_", "-")


def extract_h1(md_path: Path) -> str | None:
    """Extrai primeiro H1 do arquivo (linha começando com `# `)."""
    try:
        for line in md_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
    except (OSError, UnicodeDecodeError):
        return None
    return None


def derive_title(h1: str | None, slug: str) -> str:
    """Devolve title — H1 se existe, caso contrário derivado do slug."""
    if h1:
        return h1
    # Fallback: capitaliza tokens do slug.
    return " ".join(token.capitalize() for token in slug.split("-"))


def build_frontmatter(mapping: TrackMapping) -> str:
    """Renderiza bloco YAML conforme docs/_schemas/note-track.schema.json."""
    sprint_tag = mapping.sprint.lower()
    # YAML title pode conter caracteres especiais — quote sempre por segurança.
    title_quoted = mapping.title.replace('"', '\\"')
    return (
        "---\n"
        f"id: {mapping.track_id}\n"
        "type: track\n"
        f'title: "{title_quoted}"\n'
        f"sprint: {mapping.sprint}\n"
        "status: consumed\n"
        "created_at: null\n"
        "consumed_at: null\n"
        "agent_role: null\n"
        "tags:\n"
        "  - type/track\n"
        f"  - sprint/{sprint_tag}\n"
        "  - status/consumed\n"
        "---\n\n"
    )


def discover_tracks() -> list[Path]:
    """Lista docs/agent_prompts/track_*.md (não recursivo, exclui archive/)."""
    return sorted(SOURCE_DIR.glob("track_*.md"))


def plan_migration(sources: list[Path]) -> list[TrackMapping]:
    """Constrói TrackMapping para cada arquivo source."""
    mappings: list[TrackMapping] = []
    for src in sources:
        stem = src.stem  # 'track_a6e3_use_cases'
        if not stem.startswith("track_"):
            raise ValueError(f"arquivo inesperado (sem prefixo `track_`): {src.name}")
        stem_after = stem[len("track_") :]
        sprint = infer_sprint(stem_after)
        slug = compute_slug(stem_after)
        track_id = f"TRACK-{slug}"
        h1 = extract_h1(src)
        title = derive_title(h1, slug)
        dest = SPRINT_BASE / sprint / "tracks" / f"{slug}.md"
        mappings.append(
            TrackMapping(
                source=src,
                sprint=sprint,
                slug=slug,
                track_id=track_id,
                title=title,
                destination=dest,
            )
        )
    return mappings


def ensure_dest_dirs(mappings: list[TrackMapping]) -> None:
    """Cria docs/sprint/<X>/tracks/ para cada sprint distinta."""
    sprints = {m.sprint for m in mappings}
    for sprint in sorted(sprints):
        (SPRINT_BASE / sprint / "tracks").mkdir(parents=True, exist_ok=True)


def git_mv(source: Path, dest: Path) -> None:
    """Roda `git mv source dest` preservando history."""
    cmd = ["git", "mv", str(source.relative_to(ROOT)), str(dest.relative_to(ROOT))]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"git mv falhou: {' '.join(cmd)}\n"
            f"  stdout: {result.stdout}\n"
            f"  stderr: {result.stderr}"
        )


def inject_frontmatter(dest: Path, frontmatter: str) -> None:
    """Adiciona frontmatter no topo do arquivo destino, preservando o body."""
    body = dest.read_text(encoding="utf-8")
    if body.startswith("---"):
        raise RuntimeError(
            f"{dest} já tem frontmatter — abortando para não duplicar.\n"
            f"  primeiras linhas:\n{body[:200]!r}"
        )
    dest.write_text(frontmatter + body, encoding="utf-8")


def execute(mappings: list[TrackMapping], *, dry_run: bool) -> None:
    """Executa migração: ensure dirs, git mv, inject frontmatter."""
    if dry_run:
        for m in mappings:
            print(
                f"DRY: {m.source.relative_to(ROOT)} → {m.destination.relative_to(ROOT)} "
                f"(id={m.track_id}, sprint={m.sprint})"
            )
        return
    ensure_dest_dirs(mappings)
    for m in mappings:
        git_mv(m.source, m.destination)
        inject_frontmatter(m.destination, build_frontmatter(m))


def print_summary(mappings: list[TrackMapping]) -> None:
    """Imprime tabela agregada por sprint para revisão / commit message."""
    by_sprint: dict[str, list[str]] = {}
    for m in mappings:
        by_sprint.setdefault(m.sprint, []).append(m.slug)
    print()
    print("Mapping de sprint:")
    for sprint in sorted(by_sprint):
        slugs = sorted(by_sprint[sprint])
        print(f"  {sprint}: {len(slugs)} tracks")
        for slug in slugs:
            print(f"    - {slug}")
    print()
    print(f"Total: {len(mappings)} tracks migrados.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="apenas imprime mapping; não executa git mv nem escreve",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = discover_tracks()
    if not sources:
        print(f"erro: nenhum track_*.md encontrado em {SOURCE_DIR}", file=sys.stderr)
        return 1
    mappings = plan_migration(sources)
    execute(mappings, dry_run=args.dry_run)
    print_summary(mappings)
    if args.dry_run:
        print("(dry-run — nada foi alterado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
