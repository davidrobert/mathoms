"""Unit tests Onda 0.5 (ADR-216) — schema InformeAluguelExtract + prompt + filename detector."""

from __future__ import annotations

import json
import re
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.prompts.informe_aluguel import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from pipeline.llm.schemas.informe_aluguel import (
    PROMPT_VERSION,
    IndiceReajuste,
    InformeAluguelExtract,
    InformeAluguelImovel,
    _coerce_decimal,
)


def _build_imovel(**overrides) -> InformeAluguelImovel:
    base = {
        "endereco": "Rua Tasso da Silveira, 61 - Vila Madalena, São Paulo - SP",
        "iptu_municipal": "123.456.789-0",
        "locatario_cnpj": "12345678000190",
        "aluguel_bruto_anual": "25200.00",
        "taxa_administracao_anual": "2520.00",
        "ir_retido_anual": "0",
        "iptu_anual_pago": "4800.00",
        "condominio_anual_pago": "7200.00",
        "aluguel_liquido_anual": "10680.00",
        "meses_locado_no_periodo": 12,
        "indice_reajuste": IndiceReajuste.igpm,
        "data_ultimo_reajuste": "2024-08",
    }
    base.update(overrides)
    return InformeAluguelImovel(**base)


def _build_extract(**overrides) -> InformeAluguelExtract:
    base = {
        "imobiliaria_cnpj": "12345678000190",
        "imobiliaria_nome": "QuintoAndar Servicos Imobiliarios",
        "ano_referencia": 2024,
        "locador_cpf_present": True,
        "imoveis": [_build_imovel()],
        "confidence": 0.95,
    }
    base.update(overrides)
    return InformeAluguelExtract(**base)


# ─────────────────────── _coerce_decimal (ADR-090) ──────────────────────────


def test_coerce_decimal_aceita_string_e_int():
    assert _coerce_decimal("1234.56") == Decimal("1234.56")
    assert _coerce_decimal(1234) == Decimal("1234")
    assert _coerce_decimal(None) is None
    assert _coerce_decimal(Decimal("9.99")) == Decimal("9.99")


def test_coerce_decimal_aceita_float_no_boundary_llm():
    """JSON do LLM não tem Decimal nativo — float chega aqui literal e é coercido
    via ``Decimal(str(v))`` (a conversão prescrita pela ADR-090). Regressão do
    incidente prod 2026-05-18 (run d4f86671): LLM emitiu 7424.71 e 4 retries
    falharam com TypeError antes deste boundary aceitar float."""
    assert _coerce_decimal(7424.71) == Decimal("7424.71")
    assert _coerce_decimal(18543.82) == Decimal("18543.82")
    assert _coerce_decimal(0.0) == Decimal("0")


# ─────────────────────── Schema InformeAluguelImovel ────────────────────────


def test_imovel_happy_path_valida():
    im = _build_imovel()
    assert im.aluguel_bruto_anual == Decimal("25200.00")
    assert im.taxa_administracao_anual == Decimal("2520.00")
    assert im.meses_locado_no_periodo == 12


def test_imovel_aceita_ir_retido_zero_pf_default():
    im = _build_imovel(ir_retido_anual="0")
    assert im.ir_retido_anual == Decimal("0")


def test_imovel_aceita_iptu_e_condominio_null():
    """Imobiliária pode não administrar IPTU/condomínio — None aceitável."""
    im = _build_imovel(iptu_anual_pago=None, condominio_anual_pago=None)
    assert im.iptu_anual_pago is None
    assert im.condominio_anual_pago is None


def test_imovel_rejeita_meses_acima_de_12():
    with pytest.raises(ValueError):
        _build_imovel(meses_locado_no_periodo=13)


def test_imovel_rejeita_meses_negativo():
    with pytest.raises(ValueError):
        _build_imovel(meses_locado_no_periodo=-1)


def test_imovel_rejeita_endereco_curto():
    with pytest.raises(ValueError):
        _build_imovel(endereco="SP")


def test_imovel_aceita_float_no_boundary_llm():
    """Wire JSON do LLM emite number → Python float; o validator coerce via
    ``Decimal(str(v))`` na borda (ADR-090). Regressão prod 2026-05-18."""
    im = InformeAluguelImovel(
        endereco="Rua Test, 100",
        aluguel_bruto_anual=25200.50,  # float do LLM — aceito no boundary
        taxa_administracao_anual=2520.00,
        ir_retido_anual=0.0,
        aluguel_liquido_anual=22680.50,
        meses_locado_no_periodo=12,
    )
    assert im.aluguel_bruto_anual == Decimal("25200.5")
    assert im.taxa_administracao_anual == Decimal("2520")
    assert im.aluguel_liquido_anual == Decimal("22680.5")


def test_imovel_indice_reajuste_default_nao_informado():
    im = _build_imovel()
    im_sem = InformeAluguelImovel(
        endereco="Rua Test, 100",
        aluguel_bruto_anual="1000",
        taxa_administracao_anual="100",
        ir_retido_anual="0",
        aluguel_liquido_anual="900",
        meses_locado_no_periodo=12,
    )
    assert im_sem.indice_reajuste == IndiceReajuste.nao_informado


def test_imovel_data_reajuste_aceita_yyyy_mm_e_yyyy_mm_dd():
    im1 = _build_imovel(data_ultimo_reajuste="2024-08")
    im2 = _build_imovel(data_ultimo_reajuste="2024-08-15")
    assert im1.data_ultimo_reajuste == "2024-08"
    assert im2.data_ultimo_reajuste == "2024-08-15"


def test_imovel_data_reajuste_rejeita_formato_invalido():
    with pytest.raises(ValueError):
        _build_imovel(data_ultimo_reajuste="agosto/2024")


def test_imovel_rejeita_additional_properties():
    """Sub-models são strict — campo extra deve ser rejeitado."""
    with pytest.raises(ValueError):
        InformeAluguelImovel(
            endereco="Rua Test, 100",
            aluguel_bruto_anual="1000",
            taxa_administracao_anual="100",
            ir_retido_anual="0",
            aluguel_liquido_anual="900",
            meses_locado_no_periodo=12,
            campo_inventado="x",  # deve falhar com extra='forbid'
        )


def test_extract_aceita_payload_llm_com_numbers_regressao_prod_2026_05_18():
    """Regressão prod 2026-05-18 (run d4f86671 / workspace 5@5.com): o LLM
    QuintoAndar emitiu JSON com number (não string) em campos monetários e o
    schema rejeitou via TypeError, falhando 4 retries. Este teste simula o
    payload exato (parseado via ``json.loads``, que produz ``float`` para
    number literals) e confirma que o schema agora aceita."""
    raw_json = """
    {
      "imobiliaria_cnpj": "12345678000190",
      "imobiliaria_nome": "QuintoAndar Servicos Imobiliarios",
      "ano_referencia": 2024,
      "locador_cpf_present": true,
      "imoveis": [
        {
          "endereco": "Rua Tasso da Silveira, 61 - Vila Madalena, SP",
          "iptu_municipal": "123.456.789-0",
          "locatario_cnpj": "12345678000190",
          "aluguel_bruto_anual": 7424.71,
          "taxa_administracao_anual": 742.47,
          "ir_retido_anual": 0,
          "iptu_anual_pago": null,
          "condominio_anual_pago": null,
          "aluguel_liquido_anual": 6682.24,
          "meses_locado_no_periodo": 12,
          "indice_reajuste": "IGPM",
          "data_ultimo_reajuste": "2024-08"
        }
      ],
      "confidence": 0.95
    }
    """
    parsed = json.loads(raw_json)
    assert isinstance(parsed["imoveis"][0]["aluguel_bruto_anual"], float)
    ext = InformeAluguelExtract(**parsed)
    assert ext.imoveis[0].aluguel_bruto_anual == Decimal("7424.71")
    assert ext.imoveis[0].aluguel_liquido_anual == Decimal("6682.24")


# ─────────────────────── Schema InformeAluguelExtract ───────────────────────


def test_extract_happy_path_valida():
    ext = _build_extract()
    assert ext.imobiliaria_cnpj == "12345678000190"
    assert ext.ano_referencia == 2024
    assert len(ext.imoveis) == 1
    assert ext.confidence == 0.95


def test_extract_normaliza_cnpj_com_mascara():
    """Máscara é normalizada deterministicamente no validator (ADR-288) —
    antes era hard-fail e a coerção dependia só de instrução de prompt."""
    ext = _build_extract(imobiliaria_cnpj="12.345.678/0001-90")
    assert ext.imobiliaria_cnpj == "12345678000190"


def test_extract_cnpj_ilegivel_vira_none_regressao_prod_2026_06_11():
    """Regressão prod 2026-06-11 (workspace 5@5.com): informe QuintoAndar sem
    CNPJ legível no texto extraído → LLM emitiu ``<UNKNOWN>``, o campo required
    com pattern estrito queimou 4 retries (124s) e o informe foi perdido.
    Pós-ADR-288 (lição ADR-238): sentinel/garbage degrada para None na 1ª
    validação — zero retries, documento preservado."""
    for sentinel in ("<UNKNOWN>", "", "N/A", "nao informado", "123"):
        ext = _build_extract(imobiliaria_cnpj=sentinel)
        assert ext.imobiliaria_cnpj is None, f"sentinel {sentinel!r} deveria virar None"
    ext = _build_extract(imobiliaria_cnpj=None)
    assert ext.imobiliaria_cnpj is None


def test_extract_locador_cpf_present_flag_only():
    """ADR-259 §2 (A20.l15): o VALOR do CPF nunca entra no schema — só o flag."""
    ext = _build_extract()
    assert ext.locador_cpf_present is True
    assert not hasattr(ext, "locador_cpf")


def test_imovel_normaliza_locatario_cnpj_com_mascara():
    imovel = _build_imovel(locatario_cnpj="12.345.678/0001-90")
    assert imovel.locatario_cnpj == "12345678000190"


def test_imovel_locatario_cnpj_ilegivel_vira_none():
    imovel = _build_imovel(locatario_cnpj="<UNKNOWN>")
    assert imovel.locatario_cnpj is None


def test_extract_rejeita_ano_fora_da_faixa():
    with pytest.raises(ValueError):
        _build_extract(ano_referencia=1999)
    with pytest.raises(ValueError):
        _build_extract(ano_referencia=2101)


def test_extract_rejeita_confidence_fora_de_0_1():
    with pytest.raises(ValueError):
        _build_extract(confidence=1.5)
    with pytest.raises(ValueError):
        _build_extract(confidence=-0.1)


def test_extract_aceita_lista_de_imoveis_vazia():
    """Imobiliária pode emitir informe sem imóveis (revisão humana — confidence baixa esperada)."""
    ext = _build_extract(imoveis=[], confidence=0.3)
    assert ext.imoveis == []


def test_extract_aceita_multiplos_imoveis():
    im1 = _build_imovel(endereco="Imovel 1, SP", iptu_municipal="111")
    im2 = _build_imovel(endereco="Imovel 2, SP", iptu_municipal="222")
    ext = _build_extract(imoveis=[im1, im2])
    assert len(ext.imoveis) == 2
    enderecos = {i.endereco for i in ext.imoveis}
    assert enderecos == {"Imovel 1, SP", "Imovel 2, SP"}


def test_extract_prompt_version_default_e_versionado():
    ext = _build_extract()
    assert ext.prompt_version == PROMPT_VERSION
    # Semver puro pós-A20.l15 (errata ADR-233 §Migration).
    assert re.fullmatch(r"\d+\.\d+\.\d+", PROMPT_VERSION)


def test_extract_serializa_para_json_com_decimais_string():
    """ADR-090 wire: Decimal serializa como string decimal no JSON."""
    ext = _build_extract()
    payload = ext.model_dump(mode="json")
    imovel0 = payload["imoveis"][0]
    # Pydantic v2 com mode='json' serializa Decimal como string
    assert isinstance(imovel0["aluguel_bruto_anual"], str)
    assert imovel0["aluguel_bruto_anual"] == "25200.00"


# ─────────────────────── JSON Schema (DBArtifactStore ADR-212) ──────────────


def _canonical_validator():
    """Validator do schema canônico (ADR-212 hook pós-write) — skip sem jsonschema."""
    schema_path = (
        Path(__file__).resolve().parent.parent
        / "config"
        / "schemas"
        / "informe_aluguel.schema.json"
    )
    assert schema_path.exists(), "schema canônico precisa existir para validação ADR-212"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema = pytest.importorskip(
        "jsonschema", reason="jsonschema não disponível neste ambiente — gate roda em CI"
    )
    return jsonschema.Draft202012Validator(schema)


def test_payload_passa_no_json_schema_canonico():
    """Payload de InformeAluguelExtract deve validar contra
    ``config/schemas/informe_aluguel.schema.json`` (ADR-212 hook pós-write)."""
    payload = _build_extract().model_dump(mode="json")
    _canonical_validator().validate(payload)


def test_payload_cnpj_null_passa_no_json_schema_canonico():
    """ADR-288: payload com ``imobiliaria_cnpj=null`` (ilegível no documento)
    valida no schema do hook pós-write; pattern segue rejeitando string inválida."""
    validator = _canonical_validator()
    from jsonschema import ValidationError

    payload = _build_extract(imobiliaria_cnpj="<UNKNOWN>").model_dump(mode="json")
    assert payload["imobiliaria_cnpj"] is None
    validator.validate(payload)

    with pytest.raises(ValidationError):
        validator.validate(dict(payload, imobiliaria_cnpj="123"))


# ─────────────────────── Prompt format ──────────────────────────────────────


def test_system_prompt_referencia_rules_metodologicas():
    """SYSTEM_PROMPT deve cobrir aluguel bruto, taxa adm, IR retido condicional, IPTU/condomínio opcionais."""
    assert "aluguel" in SYSTEM_PROMPT.lower()
    assert "taxa de administra" in SYSTEM_PROMPT.lower()
    assert "ir retido" in SYSTEM_PROMPT.lower()
    assert "iptu" in SYSTEM_PROMPT.lower()
    assert "condomínio" in SYSTEM_PROMPT.lower()
    # ADR-090 / convenção numérica: valores monetários como string decimal
    # (entre aspas) — alinha com pattern e16_irpf_full e evita o bug prod
    # 2026-05-18 onde LLM emitia number e _coerce_decimal rejeitava.
    assert '"1234.56"' in SYSTEM_PROMPT


def test_system_prompt_proibe_placeholder_em_identificadores_adr288():
    """ADR-288: contrato positivo — CNPJ/CPF ausente/ilegível → null, nunca
    placeholder (proíbe a categoria, não enumera sentinels)."""
    sp = SYSTEM_PROMPT.lower()
    assert "placeholder" in sp
    assert "`null`" in SYSTEM_PROMPT
    assert "informação válida" in SYSTEM_PROMPT


def test_system_prompt_sigilo_metodologico_adr207():
    """Sigilo §13 COPY_GUIDELINES — não mencionar Perini/Cerbasi/AUVP no output."""
    sp = SYSTEM_PROMPT.lower()
    assert "perini" not in sp or "não mencionar" in sp or "nao mencionar" in sp
    # Verifica explicitação do sigilo
    assert (
        "sigilo" in sp
        or "não mencionar" in sp.replace("ã", "a")
        or "nao mencionar" in sp.replace("ã", "a")
    )


def test_user_prompt_template_aceita_placeholders_documentados():
    """USER_PROMPT_TEMPLATE precisa de filename, institution, ano_referencia, document_text."""
    formatted = USER_PROMPT_TEMPLATE.format(
        filename="quintoandar_informerendimentosaluguel_2024.pdf",
        institution="QuintoAndar",
        ano_referencia=2024,
        document_text="(corpo do PDF)",
    )
    assert "quintoandar_informerendimentosaluguel_2024.pdf" in formatted
    assert "QuintoAndar" in formatted
    assert "2024" in formatted
    assert "(corpo do PDF)" in formatted


def test_user_prompt_lista_campos_imovel_obrigatorios():
    """USER_PROMPT_TEMPLATE deve enumerar campos por imóvel para reduzir alucinação."""
    sp = USER_PROMPT_TEMPLATE.lower()
    for campo in (
        "endereco",
        "aluguel_bruto_anual",
        "taxa_administracao_anual",
        "ir_retido_anual",
        "aluguel_liquido_anual",
        "meses_locado_no_periodo",
    ):
        assert campo in sp, f"campo {campo!r} ausente do USER_PROMPT_TEMPLATE"


# ─────────────────────── Filename detector + artifact_key helper ────────────


def test_filename_pattern_detecta_informe_quintoandar():
    """Regex de detecção (espelhado de scripts/route_documents.py:112)."""
    pattern = re.compile(r"informe.*rendimento.*aluguel", re.I)
    assert pattern.search("quintoandar_informerendimentosaluguel_2024-0_original.pdf")
    assert pattern.search("loft_informeRendimentosAluguel_2024.pdf")
    assert pattern.search("INFORME-DE-RENDIMENTOS-ALUGUEL-2024.PDF")
    assert not pattern.search("irpfdeclaracao_2024_titular.pdf")
    assert not pattern.search("c6bank_extratoconta_202401.csv")


def test_artifact_key_strip_original_suffix():
    """Stem para artifact_key — strip de ``-0_original`` (paridade com E1.6)."""
    from pipeline.stages.extract_informe_aluguel import _artifact_key_for

    p1 = Path("quintoandar_informerendimentosaluguel_2024-0_original.pdf")
    assert _artifact_key_for(p1) == "quintoandar_informerendimentosaluguel_2024"

    p2 = Path("loft_informe_2024.pdf")
    assert _artifact_key_for(p2) == "loft_informe_2024"


def test_redact_filename_pii_mascara_cpf_e_cnpj():
    """PII — CPF/CNPJ não devem vazar em logs estruturados."""
    from pipeline.stages.extract_informe_aluguel import _redact_filename_pii

    assert "<cpf-redacted>" in _redact_filename_pii("informe_12345678900_2024.pdf")
    assert "<cpf-redacted>" in _redact_filename_pii("informe_123.456.789-00_2024.pdf")
    assert "<cnpj-redacted>" in _redact_filename_pii("informe_12.345.678/0001-90_2024.pdf")
    # Não-CPF preservado
    assert _redact_filename_pii("informe_2024.pdf") == "informe_2024.pdf"


# ─────────────────────── SCHEMA_BY_STAGE registry ───────────────────────────


def test_schema_by_stage_registra_informe_aluguel():
    """ADR-212: stage 'E2-informe-aluguel' deve mapear para schema JSON canônico."""
    from backend.app.services.storage.db_artifact_store import SCHEMA_BY_STAGE

    assert SCHEMA_BY_STAGE.get("E2-informe-aluguel") == "informe_aluguel.schema.json"
    assert SCHEMA_BY_STAGE.get("extract_informe_aluguel") == "informe_aluguel.schema.json"
