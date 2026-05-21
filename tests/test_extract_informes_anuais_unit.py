"""Unit tests A17 L1 P2 (ADR-238) — stage extract_informes_anuais + helpers."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stages.extract_informes_anuais import (
    _artifact_key_for,
    _build_payload,
    _content_hash,
    _detect_institution_hint,
    _detect_tipo_informe,
    _extract_one,
    _extract_titular_cpf_masked,
    _mask_cpf,
    _redact_filename_pii,
)

# ─────────────────────── tipo_informe detection ───────────────────────────


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("InformePGBL_BrasilPrev_2024.pdf", "previdencia_privada"),
        ("informe_previdencia_2024.pdf", "previdencia_privada"),
        ("Brasilprev_2024_anual.pdf", "previdencia_privada"),
        ("Caixa_Vida_informe_2024.pdf", "previdencia_privada"),
        ("InformeVGBL_Icatu.pdf", "previdencia_privada"),
        ("InformeRendimentosFinanceiros_Itau.pdf", None),  # L3 — não cobre em P1
        ("c6bank_extratoconta_202601.csv", None),
        ("declaracao_irpf_2024.pdf", None),
    ],
)
def test_detect_tipo_informe(filename, expected):
    assert _detect_tipo_informe(filename) == expected


def test_detect_institution_hint():
    assert _detect_institution_hint("InformePGBL_BrasilPrev_2024.pdf") == "brasilprev"
    assert _detect_institution_hint("Caixa_Vida_2024.pdf") == "caixa"
    assert _detect_institution_hint("desconhecido.pdf") == "unknown"


# ─────────────────────── artifact_key composition ─────────────────────────


def test_artifact_key_for_previdencia():
    assert (
        _artifact_key_for("previdencia_privada", "brasilprev", 2024)
        == "previdencia_brasilprev_2024"
    )
    # ano None — não deve crashar
    assert (
        _artifact_key_for("previdencia_privada", "icatu", None)
        == "previdencia_icatu_ano_desconhecido"
    )


# ─────────────────────── PII redaction ────────────────────────────────────


def test_redact_filename_pii_masks_cpf_cnpj():
    assert "12345678900" not in _redact_filename_pii("informe_98765432100_2024.pdf")
    assert "<cpf-redacted>" in _redact_filename_pii("informe_98765432100_2024.pdf")
    assert "<cnpj-redacted>" in _redact_filename_pii("informe_12.345.678/0001-90.pdf")
    assert (
        _redact_filename_pii("InformePGBL_BrasilPrev_2024.pdf") == "InformePGBL_BrasilPrev_2024.pdf"
    )


# ─────────────────────── despacho por tipo_informe ────────────────────────


def test_extract_one_raises_not_implemented_para_tipos_futuros():
    """L2-L4 ainda não implementadas — stage levanta NotImplementedError claro."""

    class _FakeService:
        pass

    class _FakeConfig:
        max_tokens = 4096

    with pytest.raises(NotImplementedError) as exc:
        _extract_one(
            doc=Path("fake.pdf"),
            text="dummy",
            service=_FakeService(),
            config=_FakeConfig(),
            tipo_informe="financeiro_pj",
        )
    assert "financeiro_pj" in str(exc.value)
    assert "L1" in str(exc.value)


# ─────────────────────── payload build + needs_review ─────────────────────


class _FakeOutput:
    """Stub que mimica InformeRendimentosBase.model_dump."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def model_dump(self, mode: str = "json") -> dict:  # noqa: ARG002
        return dict(self._data)


def test_build_payload_force_prompt_version_e_source_artifact_id():
    out = _FakeOutput(
        {
            "ano_base": 2024,
            "tipo_informe": "previdencia_privada",
            "fonte_pagadora_cnpj": "16404287000167",
            "fonte_pagadora_nome": "BrasilPrev",
            "confidence": 0.95,
            "needs_review": False,
            "titular_cpf_masked": None,  # LLM nunca emite CPF
            "prompt_version": "old-version",  # será sobrescrito
        }
    )
    payload = _build_payload(out, "informe-prev-v1.0.0", "Conteúdo sem CPF.", "doc_stem_xyz")
    assert payload["prompt_version"] == "informe-prev-v1.0.0"
    assert payload["source_artifact_id"] == "doc_stem_xyz"
    # confidence ≥ 0.7 → needs_review preserva valor original (False)
    assert payload["needs_review"] is False
    # texto sem CPF → titular_cpf_masked permanece None
    assert payload["titular_cpf_masked"] is None


def test_build_payload_marks_needs_review_quando_confidence_baixo():
    out = _FakeOutput(
        {
            "ano_base": 2024,
            "tipo_informe": "previdencia_privada",
            "confidence": 0.65,  # < 0.7 → needs_review auto
        }
    )
    payload = _build_payload(out, "informe-prev-v1.0.0", "texto", "stem")
    assert payload["needs_review"] is True


def test_build_payload_extrai_e_mascara_cpf_em_python():
    """Gate financial-planner Q8: LLM nunca mascarara CPF — feito em Python pós-extração."""
    # CPF placeholder seguro (não-real, fora do padrão mod-11) — apenas para regex test.
    out = _FakeOutput({"ano_base": 2024, "tipo_informe": "previdencia_privada", "confidence": 0.95})
    texto_com_cpf_formatado = "Titular: João Silva\nCPF: 000.000.000-00"
    payload = _build_payload(out, "informe-prev-v1.0.0", texto_com_cpf_formatado, "stem")
    assert payload["titular_cpf_masked"] == "***.000.000-**"
    # CPF raw também é detectado
    texto_com_cpf_raw = "11111111111 - placeholder"
    payload2 = _build_payload(out, "informe-prev-v1.0.0", texto_com_cpf_raw, "stem")
    assert payload2["titular_cpf_masked"] == "***.111.111-**"


def test_mask_cpf_idempotente():
    """``_mask_cpf`` aceita CPF formatado ou raw e devolve sempre máscara parcial."""
    assert _mask_cpf("00000000000") == "***.000.000-**"
    assert _mask_cpf("000.000.000-00") == "***.000.000-**"
    assert _mask_cpf("invalido") == ""


def test_content_hash_determinista(tmp_path: Path):
    """Hash idempotente entre chamadas — base da cache key estável (gate data-engineer Q4)."""
    f = tmp_path / "informe.pdf"
    f.write_bytes(b"%PDF-fake-content-for-test\x00\x01\x02")
    h1 = _content_hash(f)
    h2 = _content_hash(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex
    # Re-criar com mesmo nome mas conteúdo distinto → hash distinto
    f.write_bytes(b"%PDF-fake-other-content")
    assert _content_hash(f) != h1


# ─────────────────────── STAGE_REGISTRY + suffix sync ─────────────────────


def test_stage_registered_and_suffixed():
    from pipeline.artifact_store import _STAGE_TO_SUFFIX
    from pipeline.stage_spec import FULL_ORDER, STAGE_REGISTRY, STAGE_RENAME_MAP

    assert "extract_informes_anuais" in STAGE_REGISTRY
    assert STAGE_REGISTRY["extract_informes_anuais"].is_llm is True
    assert STAGE_REGISTRY["extract_informes_anuais"].tier == "premium"
    assert "extract_informes_anuais" in FULL_ORDER
    pos_alug = FULL_ORDER.index("extract_informe_aluguel")
    pos_anual = FULL_ORDER.index("extract_informes_anuais")
    assert pos_anual == pos_alug + 1
    assert _STAGE_TO_SUFFIX["extract_informes_anuais"] == "-2_informe_anual.json"
    # Alias legacy mantido por invariante test_values_cover_registry_plus_virtual
    # (paridade com E6-parecer / E1.6 — stages F9.2+ descritivos têm reverso
    # para CLI/HTTP).
    assert STAGE_RENAME_MAP["E2-informe-anual"] == "extract_informes_anuais"
    assert _STAGE_TO_SUFFIX["E2-informe-anual"] == "-2_informe_anual.json"


def test_stage_runner_registered():
    """`_assert_runners_cover_registry` em pipeline/orchestrator.py protege contra divergência."""
    from pipeline.orchestrator import _STAGE_RUNNERS

    assert "extract_informes_anuais" in _STAGE_RUNNERS
    module, attr = _STAGE_RUNNERS["extract_informes_anuais"]
    assert module == "pipeline.stages.extract_informes_anuais"
    assert attr == "run"
