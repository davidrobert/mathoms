"""Corpus golden E2 × schema strict — pré-condição do flip warn→strict (ADR-284)."""

# Cada writer E2 vivo roda de verdade sobre input sintético e o artefato
# resultante (pós stamp_natural_key, espelho exato do write-path de produção
# em run_with_store/extract_with_llm) é validado com strict forçado contra o
# schema do SEU stage: e2_extract.schema.json (parsers determinísticos) ou
# e2_llm_artifact.schema.json (writer E2-llm — vocabulário próprio, A24.l7).
# Três buckets, enumeração exaustiva garantida por
# test_corpus_cobre_todos_os_parsers:
#   PASS_CASES — output valida em strict hoje.
#   KNOWN_DRIFT_CASES — writer vivo cujo output viola o schema do stage;
#     paths exatos pinados; flip do schema bloqueado enquanto não esvazia
#     (runbook schema_validation_strict_flip §1). Esvaziado em A24.l7.
#   INPUT_GAPS — parser sem input sintético viável. Esvaziado em A24.l7
#     (layouts de fatura no gerador + XLS binário via xlwt dev-dep).

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Tuple

import pytest

from pipeline.domain.services.e2_natural_key import stamp_natural_key
from scripts.e2.registry import route_to_parser
from scripts.pipeline_common import validate_dict

pytest.importorskip("pdfplumber")

_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _pin_repo_config_dir():
    """Gate anti-vacuidade (A32.l2): ``e0_route._init_config`` reponta
    ``CONFIG_DIR`` global sem desfazer — sem o pin, ``pipeline.json``/schemas
    somem e ``validate_dict`` degrada para no-op silencioso na suíte completa.
    O reset de ``_schema_registry`` força rebuild do Registry contra o dir
    pinado (cache global construído sob CONFIG_DIR poluído quebraria $ref).
    """
    import scripts.pipeline_common as pc

    pc._init_config(_REPO_ROOT)
    pc._schema_registry = None
    yield


_SAMPLE_TX = [
    {"date": "2026-04-05", "description": "Mercado Sintetico", "amount": -250.50},
    {"date": "2026-04-01", "description": "Pagto Folha", "amount": 12500.00},
]
# Crédito >6 dígitos raw não dispara o ramo de crédito do parse_bradesco —
# mesma ressalva de tests/test_e2_synthetic_pdf_parsers.py::_BRADESCO_TX.
_BRADESCO_TX = [
    {"date": "2026-04-05", "description": "Mercado Sintetico", "amount": -250.50},
    {"date": "2026-04-10", "description": "Pagto Folha", "amount": 1250.00},
]


def _pdf_builder(
    bank: str, transactions=None, kind: str = "extrato"
) -> Callable[[Path, str], Path]:
    def _build(tmp_path: Path, filename: str) -> Path:
        from tests.fixtures.pdf_generator import generate_statement

        path = tmp_path / filename
        path.write_bytes(
            generate_statement(
                bank,  # type: ignore[arg-type]
                kind,  # type: ignore[arg-type]
                period="2026-04",
                transactions=transactions or _SAMPLE_TX,
                account_holder="Titular Golden",
            )
        )
        return path

    return _build


_FATURA_TX = [
    {"date": "2026-04-05", "description": "MERCADO SINTETICO", "amount": 250.50},
    {"date": "2026-04-12", "description": "RESTAURANTE SINTETICO", "amount": 90.00},
]

# Fatura Itaú (cartão): nacional + internacional (US$) + IOF sem data — exercita
# o balde `lancamentos_atuais` (nacional+internacional+IOF) do parse_itau_fatura.
_ITAU_FATURA_TX = [
    {"date": "2026-04-05", "description": "MERCADO GOLDEN", "amount": 250.50},
    {"date": "2026-04-19", "description": "CLOUD GOLDEN", "amount": 80.00, "usd": 15.00},
    {"description": "Repasse de IOF", "amount": 2.80, "kind": "iof"},
]


def _itau_fatura_builder(tmp_path: Path, filename: str) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    from tests.fixtures.pdf.itau import draw_itau_fatura

    path = tmp_path / filename
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    draw_itau_fatura(c, w, h, h - 2 * cm, "2026-04", _ITAU_FATURA_TX)
    c.save()
    return path


def _xls_builder(generator_name: str) -> Callable[[Path, str], Path]:
    def _build(tmp_path: Path, filename: str) -> Path:
        from tests.fixtures.pdf import xls as xls_mod

        generate = getattr(xls_mod, generator_name)
        path = tmp_path / filename
        path.write_bytes(generate("2026-04", _SAMPLE_TX, account_holder="Titular Golden"))
        return path

    return _build


def _text_builder(content: str) -> Callable[[Path, str], Path]:
    def _build(tmp_path: Path, filename: str) -> Path:
        path = tmp_path / filename
        path.write_text(content, encoding="utf-8")
        return path

    return _build


def _lines_pdf_builder(lines: list) -> Callable[[Path, str], Path]:
    """PDF sintético a partir de linhas fixas (A38.l12 — CDB PDF)."""

    def _build(tmp_path: Path, filename: str) -> Path:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas

        path = tmp_path / filename
        c = canvas.Canvas(str(path), pagesize=A4)
        _, height = A4
        y = height - 2 * cm
        c.setFont("Helvetica", 9)
        for line in lines:
            c.drawString(2 * cm, y, line)
            y -= 0.5 * cm
        c.save()
        return path

    return _build


_ITAU_CDB_PDF_LINES = [
    "Extrato de movimentação mensal - CDB-DI",
    "Período: 01/07/2026 à 22/07/2026",
    "30/06/2026 SALDO ANTERIOR 100.000,00",
    "22/07/2026 SALDO FINAL 124.940,17",
]
_SANT_CDB_PDF_LINES = [
    "DETALHES DO INVESTIMENTO",
    "CDB Valor total (R$) : 143.248,51 Valores Referentes a : 22/07/2026",
    "CDB DI SANTANDER Valor Total : R$ 143.248,51 Disponível para Resgate : R$ 138.304,04",
    "Você possui 1 contrato neste investimento",
]
# Posição acionária Itaú (A39.l9): a qtd Total é o int antes do ticker;
# `Preferencial778` cola Tipo+Livres (espelha o layout real sem espaços).
_ITAU_POSICAO_LINES = [
    "Posição Acionária",
    "Empresa Custódia Código papel",
    "Tipo Livres Bloqueadas Total",
    "BRASKEM S.A. 300 0 300 BRKM5",
    "TOTAL 300 0 300",
    "ITAUSA S.A. Preferencial778 0 778 ITSA4",
    "TOTAL 778 0 778",
]


def _rico_carteira_builder(tmp_path: Path, filename: str) -> Path:
    from tests.fixtures.pdf.rico import generate_rico_carteira_xlsx

    path = tmp_path / filename
    path.write_bytes(generate_rico_carteira_xlsx())
    return path


_C6_EXTRATO_PJ_CSV = """EXTRATO DE CONTA CORRENTE C6 BANK

Agência: 1 / Conta: 12345678
Extrato gerado em 30/04/2026 - as 10:00:00

Extrato de 01/04/2026 a 30/04/2026

Data Lançamento,Data Contábil,Título,Descrição,Entrada,Saída,Saldo
05/04/2026,05/04/2026,Pix enviado,Mercado Sintetico,,250.50,1000.00
10/04/2026,10/04/2026,Pix recebido,Pagto Folha,1250.00,,2250.50
"""

_C6_CARBON_CSV = (
    "Data de Compra;Nome no Cartão;Final do Cartão;Categoria;Descrição;Parcela;"
    "Valor (em US$);Cotação (em R$);Valor (em R$)\n"
    "05/04/2026;TITULAR GOLDEN;1234;Mercado;MERCADO SINTETICO;Única;0;0;250.50\n"
    "08/04/2026;TITULAR GOLDEN;1234;Viagem;HOTEL INTL;2/3;100.00;5.10;510.00\n"
    "15/04/2026;TITULAR GOLDEN;1234;Pagamento;Inclusao de Pagamento;Única;0;0;-760.50\n"
)

_PAOACUCAR_CSV = """data,lançamento,valor
2026-04-05,RESTAURANTE SINTETICO 1/3,150.00
2026-04-12,PAGAMENTO EFETUADO,-150.00
"""

_SANTANDER_FATURA_CSV = """data,lancamento,valor
2026-04-05,LOJA SINTETICA,100.00
2026-04-12,PAGAMENTO EFETUADO,-100.00
"""

_ITAU_CDB_HTML = """<html><body><table>
<tr><td>Extrato de movimentação mensal - CDB/RDB</td></tr>
<tr><td></td><td>Nome:</td><td>Titular Golden</td></tr>
<tr><td></td><td>Agência:</td><td>0001</td><td>Conta:</td><td>12345-6</td></tr>
<tr><td></td><td>Período:</td><td>01/04/2026 a 30/04/2026</td></tr>
<tr><td></td><td>SALDO ANTERIOR</td><td>100.000,00</td></tr>
<tr><td>1234567890123</td><td>05/05/2027</td><td>05/05/2025</td><td>100.000,00</td>
<td>100,00</td><td>100.000,00</td><td>101.000,00</td><td>1.000,00</td></tr>
<tr><td></td><td>SALDO FINAL</td><td>101.000,00</td></tr>
<tr><td>Total:</td><td>100.000,00</td><td>0,00</td><td>0,00</td><td>0,00</td>
<td>1.000,00</td><td>101.000,00</td><td>150,00</td><td>100.850,00</td></tr>
</table></body></html>"""


def _santander_cdb_xlsx_builder(tmp_path: Path, filename: str) -> Path:
    import openpyxl

    wb = openpyxl.Workbook()
    sh = wb.active
    sh.append(["CDB", "Valor Total: R$101.000,00", "Valores Referentes a: 30/04/2026"])
    sh.append(
        ["CDB DI SANTANDER", "Valor Total: R$101.000,00", "Disponível para Resgate: R$101.000,00"]
    )
    # Linha de posição (op 15+ dígitos): Σ posições == total ⇒ checksum fecha
    # (ADR-342 §Emenda 2026-07-23). Sem ela, 0 posições + total ⇒ escala.
    sh.append(["000000000000001", "R$101.000,00", "R$101.000,00"])
    path = tmp_path / filename
    wb.save(path)
    return path


# (filename, builder) por função de parser registrada em scripts/e2/registry.
PASS_CASES: Dict[str, Tuple[str, Callable[[Path, str], Path]]] = {
    "bankofamerica.parse_bankofamerica": (
        "bankofamerica_extratoconta_202604_golden.pdf",
        _pdf_builder("bankofamerica"),
    ),
    "bradesco.parse_bradesco": (
        "bradesco_extratoconta_202604_golden.pdf",
        _pdf_builder("bradesco", _BRADESCO_TX),
    ),
    "btg.parse_btg": ("btgpactual_extratoconta_202604_golden.pdf", _pdf_builder("btgpactual")),
    "c6bank.parse_c6bank": ("c6bank_extratoconta_202604_golden.pdf", _pdf_builder("c6bank")),
    "c6bank.parse_c6bank_csv": (
        "c6bank_extratocontapj_202604.csv",
        _text_builder(_C6_EXTRATO_PJ_CSV),
    ),
    "c6bank.parse_c6_carbon_csv": ("c6bank_faturacarbon_202604.csv", _text_builder(_C6_CARBON_CSV)),
    "caixa.parse_caixa": ("caixa_extratoconta_202604_golden.pdf", _pdf_builder("caixa")),
    "itau.parse_itau": ("itau_extratoconta_202604_golden.pdf", _pdf_builder("itau")),
    "itau.parse_itau_paoacucar_csv": (
        "itau_faturapaoacucar_fatura-20260410.csv",
        _text_builder(_PAOACUCAR_CSV),
    ),
    "picpay.parse_picpay": ("picpay_extratoconta_202604_golden.pdf", _pdf_builder("picpay")),
    "quintoandar.parse_quintoandar": (
        "quintoandar_faturaaluguelapt01_202604.pdf",
        _pdf_builder("quintoandar"),
    ),
    "rico.parse_rico": ("rico_extratoconta_202604_golden.pdf", _pdf_builder("rico")),
    "santander.parse_santander_conta": (
        "santander_extratoconta_202604_golden.pdf",
        _pdf_builder("santander"),
    ),
    "santander.parse_santander_fatura_csv": (
        "santander_faturaunique_202604.csv",
        _text_builder(_SANTANDER_FATURA_CSV),
    ),
    "wise.parse_wise": ("wise_extratoconta_202604_golden.pdf", _pdf_builder("wise")),
    # cdbresumo: emitem `banco` aditivo ao lado de `instituicao` desde A24.l7
    # (valor idêntico — E4 lê `instituicao or banco`; sem transacoes, sem E3).
    "itau.parse_itau_cdb_html_xls": ("itau_cdbresumo_202604.xls", _text_builder(_ITAU_CDB_HTML)),
    "santander.parse_santander_cdb_xlsx": (
        "santander_cdbresumo_202604.xlsx",
        _santander_cdb_xlsx_builder,
    ),
    # CDB posição em PDF (A38.l12) — mesmo shape cdbresumo dos parsers xls/xlsx.
    "itau.parse_itau_cdb_pdf": (
        "itau_cdbresumo_202604.pdf",
        _lines_pdf_builder(_ITAU_CDB_PDF_LINES),
    ),
    "santander.parse_santander_cdb_pdf": (
        "santander_cdbresumo_202604.pdf",
        _lines_pdf_builder(_SANT_CDB_PDF_LINES),
    ),
    # Faturas PDF com layout sintético dedicado (A24.l7 passo 3 — ex-INPUT_GAPS).
    "c6bank.parse_c6_carbon": (
        "c6bank_faturacarbon_202604.pdf",
        _pdf_builder("c6bank", _FATURA_TX, kind="fatura"),
    ),
    "itau.parse_itau_paoacucar": (
        "itau_faturapaoacucar_202604.pdf",
        _pdf_builder("itau", _FATURA_TX, kind="fatura"),
    ),
    "santander.parse_santander_unique": (
        "santander_faturaunique_202604.pdf",
        _pdf_builder("santander", _FATURA_TX, kind="fatura"),
    ),
    "itau.parse_itau_fatura": ("itau_fatura_202604.pdf", _itau_fatura_builder),
    # Posição de renda variável (A39.l9): custódia acionária Itaú (só-quantidade)
    # + carteira Rico (valorada por classe).
    "itau.parse_itau_investimentosposicao": (
        "itau_investimentosposicao_202604.pdf",
        _lines_pdf_builder(_ITAU_POSICAO_LINES),
    ),
    "rico.parse_rico_carteira": (
        "rico_investimentosposicao_202604.xlsx",
        _rico_carteira_builder,
    ),
    # XLS binário gerado com xlwt (dev-dep, A24.l7 passo 3 — ex-INPUT_GAPS).
    "itau.parse_itau_xls": (
        "itau_extratocontapersonnalite_202604.xls",
        _xls_builder("generate_itau_xls"),
    ),
    "santander.parse_santander_xls": (
        "santander_extratoconta_202604.xls",
        _xls_builder("generate_santander_xls"),
    ),
}

# Writers vivos cujo output viola o schema do seu stage HOJE — paths pinados;
# flip do schema correspondente bloqueado até o bucket esvaziar. Esvaziado em
# A24.l7: cdbresumo promovidos a PASS (banco aditivo); writer E2-llm ganhou
# contrato dedicado e2_llm_artifact.schema.json (ver test_llm_writer_*).
KNOWN_DRIFT_CASES: Dict[str, Tuple[str, Callable[[Path, str], Path], set]] = {}

# Parser registrado sem input sintético viável (runbook §1 — débito da
# pré-condição do flip). Esvaziado em A24.l7 passo 3: faturas PDF ganharam
# layout dedicado no gerador tests/fixtures/pdf/ e os XLS binários são
# gerados via xlwt (dev-dep em requirements-dev.txt).
INPUT_GAPS: Dict[str, str] = {}


def _registered_parser_funcs() -> set[str]:
    import scripts.e2.registry as registry

    registry._load_all_parsers() if hasattr(registry, "_load_all_parsers") else None
    return {f"{fn.__module__.split('.')[-1]}.{fn.__name__}" for _, fn in registry._ALL_PARSERS}


def _parse_and_stamp(tmp_path: Path, case_key: str, filename: str, builder) -> dict:
    path = builder(tmp_path, filename)
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None, f"sem parser para {filename!r}"
    routed = f"{parser_fn.__module__.split('.')[-1]}.{parser_fn.__name__}"
    assert routed == case_key, f"filename {filename!r} roteou para {routed}, esperado {case_key}"
    result = parser_fn(path, filename)
    assert isinstance(result, dict) and not result.get("requires_llm_fallback"), (
        f"{case_key}: parser não produziu resultado determinístico: "
        f"{result.get('notas') if isinstance(result, dict) else result!r}"
    )
    stamp_natural_key(result)
    return result


def test_corpus_cobre_todos_os_parsers():
    """Parser novo em scripts/e2/banks/ exige decisão de corpus (ADR-284)."""
    enumerated = set(PASS_CASES) | set(KNOWN_DRIFT_CASES) | set(INPUT_GAPS)
    registered = _registered_parser_funcs()
    assert enumerated == registered, (
        f"corpus dessincronizado do registry — faltam: {sorted(registered - enumerated)}; "
        f"sobram: {sorted(enumerated - registered)}"
    )


@pytest.mark.parametrize("case_key", sorted(PASS_CASES))
def test_parser_output_valida_em_strict(case_key: str, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    filename, builder = PASS_CASES[case_key]
    result = _parse_and_stamp(tmp_path, case_key, filename, builder)
    # cdbresumo emite posicoes (posições de investimento), não transacoes.
    parsed_rows = result.get("transacoes") or result.get("itens") or result.get("posicoes")
    assert parsed_rows or result.get("saldo_atual") is not None, f"{case_key}: parse vazio"
    assert validate_dict(result, "e2_extract.schema.json", source=f"corpus/{case_key}") is True


def _observed_drift_paths(caplog) -> set:
    return {
        r.validation_path
        for r in caplog.records
        if r.name == "mathoms.pipeline.schema_validation" and hasattr(r, "validation_path")
    }


def _capture_warn_telemetry(monkeypatch, caplog):
    import logging

    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
    caplog.set_level(logging.WARNING, logger="mathoms.pipeline.schema_validation")


def _llm_tx_with_optional_fields():
    from pipeline.llm.schemas.e2_llm_extract import ExtractedTransaction

    return ExtractedTransaction(
        date="2026-04-05",
        description="PIX SINTETICO",
        amount=-100.0,
        category_hint="alimentacao",
        balance_after=900.0,
    )


def _synthetic_llm_extract_artifact() -> dict:
    """Espelha o write-path E2-llm: LLMExtractOutput → _output_to_e2_json → stamp."""
    from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
    from pipeline.stages.extract_with_llm import _output_to_e2_json

    output = LLMExtractOutput(
        source_file="banco_desconhecido_202604.pdf",
        institution="bancodesconhecido",
        document_type="extrato",
        period="202604",
        currency="BRL",
        transactions=[_llm_tx_with_optional_fields()],
        confidence=0.9,
    )
    e2_json = _output_to_e2_json(output)
    e2_json["prompt_version"] = "corpus"
    stamp_natural_key(e2_json)
    return e2_json


@pytest.mark.parametrize("case_key", sorted(KNOWN_DRIFT_CASES))
def test_known_drift_pinado(case_key: str, tmp_path: Path, monkeypatch, caplog):
    """Warn passa, strict rejeita, paths exatos pinados — se o drift sumiu, promova o case para PASS_CASES."""
    _capture_warn_telemetry(monkeypatch, caplog)
    filename, builder, expected_paths = KNOWN_DRIFT_CASES[case_key]
    result = _parse_and_stamp(tmp_path, case_key, filename, builder)
    assert validate_dict(result, "e2_extract.schema.json", source=f"corpus/{case_key}") is True
    observed = _observed_drift_paths(caplog)
    assert observed == expected_paths, f"{case_key}: drift mudou — observado {sorted(observed)}"
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    assert validate_dict(result, "e2_extract.schema.json", source=f"corpus/{case_key}") is False


def test_strict_gate_nao_e_noop(monkeypatch):
    """Canário anti-vacuidade (A32.l2): strict rejeita doc vazio — se CONFIG_DIR
    estivesse poluído, validate_dict retornaria True para qualquer input e o
    corpus inteiro passaria vazio."""
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    assert validate_dict({}, "e2_extract.schema.json", source="corpus/canary") is False


def test_llm_writer_valida_em_strict_no_contrato_dedicado(monkeypatch):
    """Writer E2-llm valida em strict contra e2_llm_artifact.schema.json (A24.l7) — required canonical-only (banco/tipo/moeda) pós-ADR-312; legados são opcionais para rows antigas."""
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    e2_json = _synthetic_llm_extract_artifact()
    assert validate_dict(e2_json, "e2_llm_artifact.schema.json", source="corpus/e2-llm") is True


def test_llm_writer_valida_em_strict_no_contrato_do_reader(monkeypatch):
    """A32.l2: o artifact E2-llm entra no E3 pelo mesmo caminho dos parsers
    determinísticos — satisfaz também e2_extract.schema.json (banco/tipo/moeda
    required, o vocabulário que os readers leem), não só o contrato dedicado."""
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    e2_json = _synthetic_llm_extract_artifact()
    assert validate_dict(e2_json, "e2_extract.schema.json", source="corpus/e2-llm") is True


def test_llm_artifact_ref_compartilhado_resolve_e_fecha_transacao(monkeypatch, caplog):
    """Prova que o $ref cross-file (e2_llm_artifact → e2_extract#/$defs/transacao) RESOLVE — $ref unresolvable degrada p/ WARN silencioso em modo warn e um typo de $id deixaria o gate verde até o flip strict."""
    # Campo desconhecido na transação DEVE produzir drift de
    # additionalProperties no path da transação (só acontece se o $ref
    # resolveu no contrato fechado) e rejeitar em strict.
    _capture_warn_telemetry(monkeypatch, caplog)
    e2_json = _synthetic_llm_extract_artifact()
    e2_json["transacoes"][0]["campo_fantasma"] = "x"
    assert validate_dict(e2_json, "e2_llm_artifact.schema.json", source="corpus/e2-llm") is True
    assert "unresolvable" not in caplog.text.lower()
    drift = [
        r
        for r in caplog.records
        if r.name == "mathoms.pipeline.schema_validation" and hasattr(r, "validation_path")
    ]
    assert {r.validation_path for r in drift} == {"$.transacoes[].campo_fantasma"}
    assert {r.validator_keyword for r in drift} == {"additionalProperties"}
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    assert validate_dict(e2_json, "e2_llm_artifact.schema.json", source="corpus/e2-llm") is False
