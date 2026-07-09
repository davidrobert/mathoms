"""Testes do gate de sigilo metodológico estendido (A34.l5 · ADR-319).

Cobrem as duas superfícies com semânticas distintas: user-facing legada
(case-sensitive, strip de comentários, §13.4) e superset público
(case-insensitive, sem strip — repo público não tem "atribuição interna").
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).parent.parent / "dev" / "check_sigilo_terms.py"
_SPEC = importlib.util.spec_from_file_location("check_sigilo_terms", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
sigilo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sigilo)


# ─── Roteamento de superfícies ──────────────────────────────────────────


def test_user_facing_rules_intactas() -> None:
    assert sigilo.is_user_facing("frontend/src/app/(app)/page.tsx")
    assert sigilo.is_user_facing("frontend/src/components/report/Card.tsx")
    assert sigilo.is_user_facing("docs/_marketing/landing.md")
    assert not sigilo.is_user_facing("docs/adr/183-landing-positioning-pillars-2026.md")


def test_public_superset_cobre_paths_do_flip() -> None:
    assert sigilo.is_public_superset("docs/adr/199-parecer-planejador.md")
    assert sigilo.is_public_superset("docs/sprint/A11/lanes/qualquer.md")
    assert sigilo.is_public_superset("config/prompts/parecer_planejador.yaml")
    assert sigilo.is_public_superset("backend/alembic/versions/xyz_seed.py")
    assert sigilo.is_public_superset("README.md")
    assert sigilo.is_public_superset("frontend/README.md")


def test_public_superset_nao_cobre_codigo_interno() -> None:
    assert not sigilo.is_public_superset("pipeline/llm/prompts/apolice.py")
    assert not sigilo.is_public_superset("frontend/src/components/X.tsx")
    assert not sigilo.is_public_superset("node_modules/pkg/README.md")


# ─── Semântica do superset público ──────────────────────────────────────


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_public_case_insensitive(tmp_path: Path) -> None:
    p = _write(tmp_path, "doc.md", "metodologia cerbasi em minúsculas\n")
    hits = sigilo.check_file_public(p)
    assert [(h[0], h[1].lower()) for h in hits] == [(1, "cerbasi")]


def test_public_sem_strip_de_comentarios(tmp_path: Path) -> None:
    # Comentário HTML seria ignorado na surface legada; no superset público
    # docstring/comment também é publicado → hit.
    p = _write(tmp_path, "doc.md", "<!-- estratégia AUVP aqui -->\n")
    assert len(sigilo.check_file_public(p)) == 1


def test_public_termos_compostos(tmp_path: Path) -> None:
    p = _write(tmp_path, "doc.md", "curso Viver de Renda\nmétodo do Raul Sena\n")
    assert len(sigilo.check_file_public(p)) == 2


def test_public_sem_termo_passa(tmp_path: Path) -> None:
    p = _write(tmp_path, "doc.md", "metodologia consagrada de planejamento patrimonial\n")
    assert sigilo.check_file_public(p) == []


# ─── Allowlist e baseline ───────────────────────────────────────────────


def test_allowlist_permanente_minima() -> None:
    # Só os docs que DEFINEM a política — entrada nova exige justificativa.
    assert sigilo.PUBLIC_ALLOWLIST == frozenset(
        {
            "docs/adr/183-landing-positioning-pillars-2026.md",
            "docs/reference/COPY_GUIDELINES.md",
        }
    )


def test_baseline_existe_e_contem_os_bloqueadores() -> None:
    baseline = sigilo._load_public_baseline()
    assert "config/prompts/parecer_planejador.yaml" in baseline
    assert "config/prompts/section_summaries.yaml" in baseline
    assert all(isinstance(p, str) for p in baseline)


def test_baseline_nao_contem_allowlist() -> None:
    # Path allowlistado nunca deveria estar também no baseline (redundância
    # mascararia a remoção indevida da allowlist).
    baseline = sigilo._load_public_baseline()
    assert not (baseline & sigilo.PUBLIC_ALLOWLIST)
