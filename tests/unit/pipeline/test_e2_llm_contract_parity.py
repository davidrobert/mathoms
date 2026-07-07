"""Golden de paridade estrutural writer E2-llm ↔ schema ↔ readers E3 (A32.l2).

O writer LLM (``_output_to_e2_json``) e os readers E3 (``should_skip``/``key``/
``from_e2_dict``) divergiram de vocabulário por ~6 semanas sem sinal
(``tipo_documento`` vs ``tipo``) — cdbdetalhes/investimentosposicao nunca eram
pulados e entravam na reconciliação (P1/P3 do dogfood 2026-07-07). Este golden
fecha a CLASSE do bug: é DERIVADO do schema (campos ``required``) e do código
dos readers (chains de ``d.get()`` extraídas por AST), não de listas
hardcoded — quebra sozinho quando qualquer lado evoluir.
"""

from __future__ import annotations

import ast
import inspect
import json
import sys
import textwrap
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.models.document import BankStatement  # noqa: E402
from pipeline.domain.services.account_grouper import (  # noqa: E402
    AccountGrouper,
    AccountKey,
)
from pipeline.domain.services.e3_reconciler_adapter import (  # noqa: E402
    E3ReconcilerAdapter,
)
from pipeline.domain.services.reconciliation_service import (  # noqa: E402
    ReconciliationConfig,
)
from pipeline.domain.services.statement_preprocessor import (  # noqa: E402
    StatementPeriodNormalizer,
)
from pipeline.llm.schemas.e2_llm_extract import (  # noqa: E402
    ExtractedInvestment,
    ExtractedTransaction,
    LLMExtractOutput,
)
from pipeline.stages.extract_with_llm import _output_to_e2_json  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS_DIR = REPO_ROOT / "config" / "schemas"


# =============================================================================
# Fixture sintética (PII-zero) — espelha o write-path de produção
# =============================================================================


def _default_tx() -> ExtractedTransaction:
    return ExtractedTransaction(
        date="2026-04-05",
        description="PIX SINTETICO",
        amount=-100.0,
        category_hint="alimentacao",
        balance_after=900.0,
    )


def _llm_output(
    document_type: str = "extrato",
    period: str | None = "202604",
    transactions: list[ExtractedTransaction] | None = None,
    investments: list[ExtractedInvestment] | None = None,
) -> LLMExtractOutput:
    return LLMExtractOutput(
        source_file=f"bancosintetico_{document_type}_202604.pdf",
        institution="bancosintetico",
        document_type=document_type,
        period=period,
        member_key="titular_sintetico",
        currency="BRL",
        transactions=transactions if transactions is not None else [_default_tx()],
        investments=list(investments or []),
        confidence=0.9,
        notes="fixture sintetica",
    )


def _writer_artifact(**kwargs) -> dict:
    return _output_to_e2_json(_llm_output(**kwargs))


def _aplicacao_tx(tx_date: str, amount: float) -> ExtractedTransaction:
    return ExtractedTransaction(date=tx_date, description="APLICACAO CDB SINTETICO", amount=amount)


def _cdb_position_output(document_type: str) -> LLMExtractOutput:
    """Posição de investimento com datas de aplicação antigas lidas como tx (P3)."""
    investment = ExtractedInvestment(
        type="cdb",
        institution="bancosintetico",
        description="CDB DI SINTETICO",
        value_brl=3000.0,
        applied_date="2023-01-10",
    )
    return _llm_output(
        document_type=document_type,
        period="202606",
        transactions=[_aplicacao_tx("2023-01-10", -1000.0), _aplicacao_tx("2024-02-20", -2000.0)],
        investments=[investment],
    )


# =============================================================================
# Golden (a) — required dos schemas ⊆ keys emitidas pelo writer
# =============================================================================


def _schema_required(schema_name: str) -> set[str]:
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text(encoding="utf-8"))
    return set(schema["required"])


@pytest.mark.parametrize("schema_name", ["e2_extract.schema.json", "e2_llm_artifact.schema.json"])
def test_writer_emite_todos_required_do_schema(schema_name: str) -> None:
    """Campo required novo no schema exige emissão no writer (derivado, não lista)."""
    missing = _schema_required(schema_name) - _writer_artifact().keys()
    assert not missing, (
        f"_output_to_e2_json não emite campos required de {schema_name}: "
        f"{sorted(missing)} — readers E3 e validação strict dependem deles"
    )


# =============================================================================
# Golden (b) — chains de leitura dos readers, derivadas por AST
# =============================================================================


def _str_constant(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _read_key(node: ast.AST, param: str) -> str | None:
    """Key lida se ``node`` é ``<param>.get("lit", ...)`` ou ``<param>["lit"]``."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == param
        and node.args
    ):
        return _str_constant(node.args[0])
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        return _str_constant(node.slice) if node.value.id == param else None
    return None


def _collect_chains(node: ast.AST, param: str, chains: set[frozenset[str]]) -> None:
    """Agrupa reads por expressão de fallback (``a or b`` / ternário) em chains."""
    if isinstance(node, (ast.BoolOp, ast.IfExp)):
        keys = {k for sub in ast.walk(node) if (k := _read_key(sub, param))}
        if keys:
            chains.add(frozenset(keys))
            return
    key = _read_key(node, param)
    if key is not None:
        chains.add(frozenset({key}))
    for child in ast.iter_child_nodes(node):
        _collect_chains(child, param, chains)


def _reader_chains(func, param: str) -> set[frozenset[str]]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    chains: set[frozenset[str]] = set()
    _collect_chains(tree, param, chains)
    assert chains, f"nenhum read de dict extraído de {func.__qualname__} — AST mudou?"
    return chains


# Chains que o writer LLM contratualmente NÃO preenche: LLMExtractOutput não
# modela saldos, número de conta nem notas top-level; `conta` é fallback
# aninhado de moeda (writer sempre emite `moeda`).
# Exemption stale (chain sumiu do reader OU writer passou a cobrir) FALHA o
# teste — mesma disciplina de KNOWN_DRIFT_CASES do corpus strict (ADR-284).
_LLM_WRITER_OPTIONAL_CHAINS: dict[str, set[frozenset[str]]] = {
    "from_e2_dict": {
        frozenset({"saldo_inicial", "opening_balance"}),
        frozenset({"saldo_final", "closing_balance"}),
        frozenset({"numero_conta", "account_number"}),
        frozenset({"numero_conta_norm"}),
        frozenset({"notas", "notes"}),
    },
    "should_skip": set(),
    "key": {frozenset({"conta"})},
}


def _assert_chain_parity(
    reader_name: str, chains: set[frozenset[str]], artifact_keys: set[str]
) -> None:
    exempt = _LLM_WRITER_OPTIONAL_CHAINS[reader_name]
    unsatisfied = {chain for chain in chains if not chain & artifact_keys}
    missing = unsatisfied - exempt
    assert not missing, (
        f"{reader_name} lê chains que o writer E2-llm não emite: "
        f"{sorted(sorted(c) for c in missing)} — emita no writer ou declare em "
        f"_LLM_WRITER_OPTIONAL_CHAINS com justificativa"
    )
    stale = exempt - unsatisfied
    assert not stale, (
        f"exemptions stale para {reader_name}: {sorted(sorted(c) for c in stale)} "
        f"— chain sumiu do reader ou writer passou a emitir; remova a exemption"
    )


def test_chains_do_from_e2_dict_cobertas_pelo_writer() -> None:
    """from_e2_dict recebe o artifact pós-normalizer (flatten de periodo) — paridade contra essas keys."""
    normalized = StatementPeriodNormalizer().normalize(_writer_artifact(), "golden").data
    chains = _reader_chains(BankStatement.from_e2_dict.__func__, "d")
    _assert_chain_parity("from_e2_dict", chains, set(normalized.keys()))


def test_chains_do_should_skip_cobertas_pelo_writer() -> None:
    chains = _reader_chains(AccountGrouper.should_skip, "data")
    _assert_chain_parity("should_skip", chains, set(_writer_artifact().keys()))


def test_chains_do_key_cobertas_pelo_writer() -> None:
    chains = _reader_chains(AccountGrouper.key, "data")
    _assert_chain_parity("key", chains, set(_writer_artifact().keys()))


# =============================================================================
# Golden funcional — parse nunca cai em fallback vazio
# =============================================================================


def test_parse_do_artifact_llm_nao_cai_em_fallback_vazio() -> None:
    artifact = _writer_artifact()
    grouper = AccountGrouper()
    assert grouper.should_skip(artifact) is False
    assert grouper.key(artifact) == AccountKey("bancosintetico", "extrato", "BRL")

    result = StatementPeriodNormalizer().normalize(artifact, source_name="golden")
    assert result.skip is False
    stmt = BankStatement.from_e2_dict(result.data)
    assert stmt.institution == "bancosintetico"
    assert stmt.account_type == "extrato"
    assert stmt.currency == "BRL"
    assert (stmt.period_start, stmt.period_end) == (date(2026, 4, 1), date(2026, 4, 30))


def test_membro_extraido_via_llm_chega_ao_bank_statement() -> None:
    """Regressão do gap A32.l2: writer emite `membro`, reader perdia a atribuição."""
    artifact = _writer_artifact()
    assert artifact["membro"] == "titular_sintetico"

    normalized = StatementPeriodNormalizer().normalize(artifact, source_name="golden").data
    stmt = BankStatement.from_e2_dict(normalized)
    assert stmt.member_key == "titular_sintetico"


def test_documento_titular_tem_precedencia_sobre_membro() -> None:
    """E2 determinístico (documento_titular) vence o vocabulário LLM (membro)."""
    artifact = _writer_artifact()
    artifact["documento_titular"] = "titular_deterministico"

    normalized = StatementPeriodNormalizer().normalize(artifact, source_name="golden").data
    assert BankStatement.from_e2_dict(normalized).member_key == "titular_deterministico"


# =============================================================================
# Regressão P1/P3 — skip-list volta a valer para artifacts E2-llm
# =============================================================================


@pytest.mark.parametrize("skip_type", ["cdbdetalhes", "investimentosposicao"])
def test_artifact_llm_de_posicao_e_pulado_pela_reconciliacao(skip_type: str) -> None:
    """Fixture LLM com tipo_documento na skip-list nunca entra no E3 (A32 P1)."""
    store = InMemoryArtifactStore()
    artifact = _output_to_e2_json(_cdb_position_output(skip_type))
    store.seed("extract_with_llm", f"bancosintetico_{skip_type}_202606", artifact)

    adapter = E3ReconcilerAdapter(ReconciliationConfig())
    statements, _, anachronic, skipped = adapter.load_bank_statements_with_warnings(store)

    assert statements == []
    assert skipped == 1
    assert anachronic == []


@pytest.mark.parametrize("skip_type", ["cdbdetalhes", "investimentosposicao"])
def test_artifact_llm_antigo_sem_tipo_e_pulado_via_fallback(skip_type: str) -> None:
    """Artifacts de mai/jun (pré-A32.l2) só têm tipo_documento — fallback dos readers cobre sem re-extração."""
    stale = _output_to_e2_json(_cdb_position_output(skip_type))
    del stale["tipo"]
    store = InMemoryArtifactStore()
    store.seed("extract_with_llm", f"bancosintetico_{skip_type}_202606", stale)

    adapter = E3ReconcilerAdapter(ReconciliationConfig())
    statements, _, anachronic, skipped = adapter.load_bank_statements_with_warnings(store)

    assert statements == []
    assert skipped == 1
    assert anachronic == []


def test_p3_anachronic_nao_dispara_sobre_posicao_de_cdb() -> None:
    """P3 do dogfood: doc pulado nem chega ao anachronic guard — zero warning."""
    store = InMemoryArtifactStore()
    store.seed(
        "extract_with_llm",
        "bancosintetico_cdbdetalhes_202606",
        _output_to_e2_json(_cdb_position_output("cdbdetalhes")),
    )
    store.seed(
        "extract_with_llm",
        "bancosintetico_extrato_202604",
        _writer_artifact(),
    )

    adapter = E3ReconcilerAdapter(ReconciliationConfig())
    statements, _, anachronic, skipped = adapter.load_bank_statements_with_warnings(store)

    assert anachronic == [], "anachronic guard rodou sobre posição que devia ser pulada"
    assert skipped == 1
    assert [s.account_type for s in statements] == ["extrato"]


def test_artifact_llm_antigo_de_extrato_reconcilia_com_identidade_completa() -> None:
    """Extrato antigo (sem `tipo`) ganha account_type via fallback tipo_documento."""
    stale = _writer_artifact()
    del stale["tipo"]

    grouper = AccountGrouper()
    assert grouper.should_skip(stale) is False
    assert grouper.key(stale) == AccountKey("bancosintetico", "extrato", "BRL")

    normalized = StatementPeriodNormalizer().normalize(stale, source_name="stale").data
    assert BankStatement.from_e2_dict(normalized).account_type == "extrato"
