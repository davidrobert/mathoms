"""A37.l11 (PD-05) — resolver de canonicalização de seguradora no boundary E2→domínio."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.seguradora_resolver import (  # noqa: E402
    canonicalize_apolice_seguradora,
    fallback_seguradora_display,
    normalize_seguradora_code,
    resolve_seguradora,
)

_CATALOGO = {"porto": "Porto Seguro", "tokiomarine": "Tokio Marine"}


# ─────────────────────── normalização ─────────────────────────────────────


def test_normalize_lowercase_sem_acentos_sem_separadores():
    assert normalize_seguradora_code("Pôrto Seguro S.A.") == "portoseguros" + "a"
    assert normalize_seguradora_code("  TOKIO-MARINE ") == "tokiomarine"
    assert normalize_seguradora_code("") == ""
    assert normalize_seguradora_code("   ") == ""


# ─────────────────────── match por code (caminho feliz) ───────────────────


def test_match_por_code_exato():
    res = resolve_seguradora("porto", _CATALOGO)
    assert (res.code, res.display_name, res.in_catalog) == ("porto", "Porto Seguro", True)
    assert res.ambiguous is False


def test_match_por_code_tolera_caixa_e_espacos():
    res = resolve_seguradora(" PORTO ", _CATALOGO)
    assert res.code == "porto"
    assert res.in_catalog is True


# ─────────────────────── fallback pelo nome normalizado ───────────────────


def test_variante_do_nome_resolve_para_code_canonico():
    """Evidência 2026-07-20: LLM emitiu `portoseguro` — casa "Porto Seguro"."""
    res = resolve_seguradora("portoseguro", _CATALOGO)
    assert (res.code, res.display_name, res.in_catalog) == ("porto", "Porto Seguro", True)


def test_nome_com_espacos_e_acentos_resolve():
    res = resolve_seguradora("Pôrto Seguro", _CATALOGO)
    assert res.code == "porto"
    assert res.in_catalog is True


# ─────────────────────── fora do catálogo → flag SOFT ─────────────────────


def test_code_desconhecido_normaliza_com_flag_soft_sem_ambiguidade():
    """Critério de aceite: fora do catálogo → flag soft (in_catalog=False),
    NUNCA ambiguidade (que é o único gatilho de needs_review no stage)."""
    res = resolve_seguradora("Segurex S.A.", _CATALOGO)
    assert res.code == "segurexsa"
    assert res.in_catalog is False
    assert res.ambiguous is False
    assert res.display_name == "Segurex S.a."


def test_vazio_retorna_resolucao_vazia():
    res = resolve_seguradora("", _CATALOGO)
    assert res.code == ""
    assert res.in_catalog is False


def test_catalogo_vazio_degrada_para_normalizacao_pura():
    res = resolve_seguradora("Porto Seguro", {})
    assert res.code == "portoseguro"
    assert res.in_catalog is False


# ─────────────────────── ambiguidade real → needs_review ──────────────────


def test_ambiguidade_real_marca_ambiguous():
    """2 entries do catálogo com o mesmo nome normalizado — único caso que
    justifica needs_review (catálogo esparso; over-fire degradaria proteção)."""
    catalogo = {"porto": "Porto Seguro", "portoseg": "Porto-Seguro"}
    res = resolve_seguradora("portoseguro", catalogo)
    assert res.ambiguous is True
    assert res.in_catalog is False


# ─────────────────────── canonicalize_apolice_seguradora ──────────────────


def test_canonicalize_copia_e_adiciona_display_name():
    apolice = {"apolice_numero": "X1", "seguradora": "portoseguro"}
    out = canonicalize_apolice_seguradora(apolice, _CATALOGO)
    assert out["seguradora"] == "porto"
    assert out["seguradora_nome"] == "Porto Seguro"
    assert "_seguradora_fora_catalogo" not in out
    assert apolice["seguradora"] == "portoseguro"  # input imutado


def test_canonicalize_fora_catalogo_marca_chave_interna():
    out = canonicalize_apolice_seguradora({"seguradora": "segurex"}, _CATALOGO)
    assert out["seguradora"] == "segurex"
    assert out["_seguradora_fora_catalogo"] is True


def test_fallback_display_capitaliza_palavras():
    assert fallback_seguradora_display("segurex nacional") == "Segurex Nacional"
    assert fallback_seguradora_display("") == ""
