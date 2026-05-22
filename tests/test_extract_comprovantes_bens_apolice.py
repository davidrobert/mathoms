"""A18 L2 P3 (ADR-239 D6 + D8) — stage dispatch apolice + cascata Haiku→Sonnet."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stages.extract_comprovantes_bens import (
    _apolice_artifact_key,
    _build_apolice_payload,
    _cascade_needed,
    _detect_tipo_comprovante,
    _extract_one,
)

# ─────────────────────── filename → tipo (apolice) ────────────────────────


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("apolice_porto_2026.pdf", "apolice"),
        ("apolice_seguro_tokio.pdf", "apolice"),
        ("seguro_porto_combinada.pdf", "apolice"),
        # CRLV continua casando crlv (não regride L1)
        ("crlv_2026_yamaha.pdf", "crlv"),
        ("CRLV-e_Toro.pdf", "crlv"),
        # Outros não casam
        ("informe_brasilprev.pdf", None),
        ("extrato_c6_202601.pdf", None),
    ],
)
def test_detect_tipo_comprovante_apolice(filename, expected):
    assert _detect_tipo_comprovante(filename) == expected


# ─────────────────────── cascade gate (ADR-239 D6) ─────────────────────────


def test_cascade_disparado_quando_multi_bem():
    """len(bens_segurados) > 1 → cascade (caso V1 obrigatório: Porto combinada)."""
    payload = {
        "bens_segurados": [
            {"tipo": "veiculo"},
            {"tipo": "imovel"},
        ],
        "confidence": 0.95,
    }
    assert _cascade_needed(payload, "texto qualquer") is True


def test_cascade_disparado_quando_confidence_baixo():
    """confidence < 0.7 → cascade (Haiku admite incerteza, Sonnet refina)."""
    payload = {"bens_segurados": [{"tipo": "veiculo"}], "confidence": 0.65}
    assert _cascade_needed(payload, "texto") is True


def test_cascade_disparado_quando_string_combinada_detectada():
    """Strings textuais ('combinada', 'residencial+auto') disparam cascade mesmo com 1 bem."""
    payload = {"bens_segurados": [{"tipo": "veiculo"}], "confidence": 0.95}
    assert _cascade_needed(payload, "Apolice Porto Protecao Combinada") is True
    assert _cascade_needed(payload, "produto residencial + auto") is True


def test_cascade_nao_disparado_quando_apolice_simples():
    """Single-bem + confidence alto + sem strings → fica em Haiku."""
    payload = {"bens_segurados": [{"tipo": "veiculo"}], "confidence": 0.95}
    assert _cascade_needed(payload, "apolice simples Tokio Marine") is False


def test_cascade_nao_disparado_para_zero_bens():
    """0 bens → gate len>1 False; mas confidence baixo dispara."""
    p_zero_high = {"bens_segurados": [], "confidence": 0.95}
    assert _cascade_needed(p_zero_high, "texto") is False
    p_zero_low = {"bens_segurados": [], "confidence": 0.5}
    assert _cascade_needed(p_zero_low, "texto") is True


# ─────────────────────── artifact key apólice ─────────────────────────────


def test_apolice_artifact_key_combina_numero_e_ano_vigencia():
    """Key = ``apolice_<numero_sanitized>_<vigencia_ano>`` (ADR-239 D7 temporal)."""
    payload = {"apolice_numero": "AUTO-TM-20260301-A1", "vigencia_inicio": "2026-03-01"}
    assert _apolice_artifact_key(payload) == "apolice_AUTO-TM-20260301-A1_2026"


def test_apolice_artifact_key_sanitiza_caracteres_especiais():
    """Caracteres não [A-Za-z0-9\\-] viram underscore (filename-safe)."""
    payload = {"apolice_numero": "AB/123#XY", "vigencia_inicio": "2026-04-10"}
    assert _apolice_artifact_key(payload) == "apolice_AB_123_XY_2026"


def test_apolice_artifact_key_fallback_sem_numero():
    payload = {"apolice_numero": "", "vigencia_inicio": "2026-01-01"}
    assert _apolice_artifact_key(payload) == "apolice_sem_numero_2026"


def test_apolice_artifact_key_fallback_sem_vigencia():
    payload = {"apolice_numero": "X1"}
    assert _apolice_artifact_key(payload) == "apolice_X1_ano_desconhecido"


# ─────────────────────── build_apolice_payload + LGPD ────────────────────


class _FakeApoliceOutput:
    def __init__(self, data: dict) -> None:
        self._data = data

    def model_dump(self, mode: str = "json") -> dict:  # noqa: ARG002
        return dict(self._data)


def _minimal_apolice_dict() -> dict:
    return {
        "apolice_numero": "ABC-1",
        "seguradora": "porto",
        "vigencia_inicio": "2026-03-01",
        "vigencia_fim": "2027-03-01",
        "premio_total_brl": "1000.00",
        "forma_pagamento": "cartao",
        "confidence": 0.9,
        "bens_segurados": [{"tipo": "veiculo"}],
        "prompt_version": "old-version",
    }


def test_build_apolice_payload_forca_prompt_version_e_cascade_flag():
    out = _FakeApoliceOutput(_minimal_apolice_dict())
    payload = _build_apolice_payload(
        out, "apolice-v1.0.0", "texto sem cpf", "doc_stem", cascade_triggered=True
    )
    assert payload["prompt_version"] == "apolice-v1.0.0"
    assert payload["source_artifact_id"] == "doc_stem"
    assert payload["cascade_triggered"] is True


def test_build_apolice_payload_mascara_cpf_em_python_pos_llm():
    """LGPD ADR-231 D8: Python mascara CPF do texto; LLM nunca retorna CPF."""
    out = _FakeApoliceOutput(_minimal_apolice_dict())
    texto = "Segurado: Fulano\nCPF: 000.000.000-00\nPagador: Cônjuge"
    payload = _build_apolice_payload(out, "apolice-v1.0.0", texto, "stem", cascade_triggered=False)
    assert payload["pagador_cpf_masked"] == "***.000.000-**"
    assert payload["segurado_cpf_masked"] == "***.000.000-**"


def test_build_apolice_payload_needs_review_confidence_baixo():
    data = _minimal_apolice_dict()
    data["confidence"] = 0.5
    out = _FakeApoliceOutput(data)
    payload = _build_apolice_payload(out, "apolice-v1.0.0", "x", "s", cascade_triggered=False)
    assert payload["needs_review"] is True


def test_build_apolice_payload_zera_sinistro_indenizacao_v1():
    """Placeholder V1 sempre null (ADR-239 D8 Risco 1)."""
    data = _minimal_apolice_dict()
    data["sinistro_indenizacao_recebida_brl"] = "10000.00"  # LLM erra: deveria ser null
    out = _FakeApoliceOutput(data)
    payload = _build_apolice_payload(out, "apolice-v1.0.0", "x", "s", cascade_triggered=False)
    assert payload["sinistro_indenizacao_recebida_brl"] is None


# ─────────────────────── _extract_one despacho ────────────────────────────


def test_extract_one_raises_para_outros_tipos():
    """rgi/iptu/etc continuam NotImplementedError (V2)."""
    with pytest.raises(NotImplementedError) as exc:
        _extract_one(
            doc=Path("rgi.pdf"),
            text="dummy",
            llm=object(),
            config=object(),
            tipo_comprovante="rgi_imovel",
        )
    assert "rgi_imovel" in str(exc.value)
    assert "V2" in str(exc.value)
