"""A18 L1 P4 (ADR-239) — stage extract_comprovantes_bens helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stages.extract_comprovantes_bens import (
    _artifact_key_for,
    _build_payload,
    _content_hash,
    _detect_tipo_comprovante,
    _extract_one,
    _extract_titular_cpf_masked,
    _mask_cpf,
    _redact_placa,
)


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("crlv_2026_yamaha.pdf", "crlv"),
        ("CRLV-e_Toro_2026.pdf", "crlv"),
        ("licenciamento_2026.pdf", "crlv"),
        ("renavam_98765432100.pdf", "crlv"),
        ("denatran_certificado.pdf", "crlv"),
        ("informe_brasilprev_2024.pdf", None),
        # A18 L2: apolice agora casa (era None em L1).
        ("apolice_tokio_marine.pdf", "apolice"),
        ("extrato_c6_202601.pdf", None),
    ],
)
def test_detect_tipo_comprovante(filename, expected):
    assert _detect_tipo_comprovante(filename) == expected


def test_artifact_key_for_crlv():
    assert _artifact_key_for("crlv", "ABC1D23", 2026) == "crlv_ABC1D23_2026"
    assert _artifact_key_for("crlv", "XYZ9A87", None) == "crlv_XYZ9A87_ano_desconhecido"


def test_redact_placa():
    assert _redact_placa("ABC1D23") == "ABC***3"
    assert _redact_placa("") == "***"
    assert _redact_placa("AB") == "***"


def test_mask_cpf_idempotente():
    assert _mask_cpf("11111111111") == "***.111.111-**"
    assert _mask_cpf("000.000.000-00") == "***.000.000-**"
    assert _mask_cpf("invalido") == ""


def test_extract_titular_cpf_masked_do_texto():
    """LGPD: Python pós-LLM mascara CPF do texto bruto do CRLV."""
    text = "Proprietário: Fulano\nCPF: 000.000.000-00\nPlaca ABC1D23"
    assert _extract_titular_cpf_masked(text) == "***.000.000-**"
    # Raw também
    assert _extract_titular_cpf_masked("CPF 11111111111") == "***.111.111-**"
    # Sem CPF → None. Nota: RENAVAM 11 dígitos colide com regex CPF; o stage
    # depende do LLM SEMPRE retornar `proprietario_cpf_masked=null` (instrução
    # SYSTEM_PROMPT D8), e o Python só mascara quando o texto traz "CPF" explícito
    # próximo. Em texto puro com apenas RENAVAM, false positive aceito porque o
    # caller (stage runner) já valida placa válida + LLM marca needs_review se
    # confidence baixa.
    assert _extract_titular_cpf_masked("Placa ABC1D23 sem dados pessoais") is None


def test_content_hash_determinista(tmp_path: Path):
    f = tmp_path / "crlv.pdf"
    f.write_bytes(b"%PDF-fake-crlv-content")
    h1 = _content_hash(f)
    h2 = _content_hash(f)
    assert h1 == h2 and len(h1) == 64


def test_extract_one_raises_not_implemented_para_outros_tipos():
    """A18 V2: rgi/iptu (imóveis) ainda não cobertos → NotImplementedError claro."""

    class _FakeService:
        pass

    class _FakeConfig:
        max_tokens = 4096

    with pytest.raises(NotImplementedError) as exc:
        _extract_one(
            doc=Path("rgi_2026.pdf"),
            text="dummy",
            service=_FakeService(),
            config=_FakeConfig(),
            tipo_comprovante="rgi_imovel",
        )
    assert "rgi_imovel" in str(exc.value)
    assert "V2" in str(exc.value)


class _FakeOutput:
    def __init__(self, data: dict) -> None:
        self._data = data

    def model_dump(self, mode: str = "json") -> dict:  # noqa: ARG002
        return dict(self._data)


def test_build_payload_forca_prompt_version_e_mascara_cpf():
    out = _FakeOutput(
        {
            "placa": "ABC1D23",
            "renavam": "12345678900",
            "marca": "Yamaha",
            "modelo": "NMAX",
            "ano_modelo": 2024,
            "ano_fabricacao": 2024,
            "exercicio": 2026,
            "categoria": "particular",
            "confidence": 0.95,
            "prompt_version": "old-version",
        }
    )
    texto_com_cpf = "Proprietário: Fulano\nCPF: 000.000.000-00"
    payload = _build_payload(out, "crlv-v1.0.0", texto_com_cpf, "doc_stem")
    assert payload["prompt_version"] == "crlv-v1.0.0"
    assert payload["source_artifact_id"] == "doc_stem"
    assert payload["proprietario_cpf_masked"] == "***.000.000-**"


def test_build_payload_needs_review_confidence_baixo():
    out = _FakeOutput({"placa": "ABC1D23", "confidence": 0.65})
    payload = _build_payload(out, "crlv-v1.0.0", "texto sem cpf", "stem")
    assert payload["needs_review"] is True


# ─────────────────────── STAGE_REGISTRY + suffix sync ─────────────────────


def test_stage_registered_and_suffixed():
    from pipeline.artifact_store import _STAGE_TO_SUFFIX
    from pipeline.stage_spec import FULL_ORDER, STAGE_REGISTRY, STAGE_RENAME_MAP

    assert "extract_comprovantes_bens" in STAGE_REGISTRY
    assert STAGE_REGISTRY["extract_comprovantes_bens"].is_llm is True
    assert STAGE_REGISTRY["extract_comprovantes_bens"].tier == "premium"
    assert "extract_comprovantes_bens" in FULL_ORDER
    # Aparece após extract_informes_anuais (mesma família de extract de upload)
    pos_inf = FULL_ORDER.index("extract_informes_anuais")
    pos_comp = FULL_ORDER.index("extract_comprovantes_bens")
    assert pos_comp == pos_inf + 1
    assert _STAGE_TO_SUFFIX["extract_comprovantes_bens"] == "-2_comprovante_bem.json"
    assert _STAGE_TO_SUFFIX["E2-comprovante-bem"] == "-2_comprovante_bem.json"
    assert STAGE_RENAME_MAP["E2-comprovante-bem"] == "extract_comprovantes_bens"


def test_stage_runner_registered():
    from pipeline.orchestrator import _STAGE_RUNNERS

    assert "extract_comprovantes_bens" in _STAGE_RUNNERS
    module, attr = _STAGE_RUNNERS["extract_comprovantes_bens"]
    assert module == "pipeline.stages.extract_comprovantes_bens"
    assert attr == "run"
