"""Tests — labels PJ no `TransactionClassifier` ([[ADR-236]] §D2)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.transaction_classifier import (  # noqa: E402
    PJ_LABELS,
    ClassifierConfig,
    FolhaPJProxyUnavailable,
    TransactionClassifier,
)

# =============================================================================
# Helpers
# =============================================================================


_DEFAULT_PJ_MAPPING = {
    "ARVO": "Arvo (David - PJ)",
    "BRANDLOVERS": "BrandLovers (David - PJ)",
    "CNRY": "CNRY (David - PJ)",
}


def _config_with_pj() -> ClassifierConfig:
    return ClassifierConfig.from_configs(
        categorization={
            "expense_keywords": {"mercado": ["mercado"]},
            "income_keywords": {"receita_clt": ["KIWIFY"], "receita_pj": []},
            "pj_source_mapping": _DEFAULT_PJ_MAPPING,
            "clt_source_mapping": {"KIWIFY": "Kiwify (CLT)"},
        }
    )


def _config_without_pj_mapping() -> ClassifierConfig:
    """Workspace sem PJ cadastrada — pj_source_mapping vazio."""
    return ClassifierConfig.from_configs(
        categorization={
            "expense_keywords": {"mercado": ["mercado"]},
            "income_keywords": {},
            "pj_source_mapping": {},
        }
    )


def _account(*, banco: str = "Itaú", tipo_conta: str = "extratoconta") -> dict:
    return {
        "banco": banco,
        "tipo_conta": tipo_conta,
        "moeda": "BRL",
        "titular": "David Robert",
        "transacoes": [],
    }


def _tx(descricao: str, valor: float, *, tipo: str | None = None) -> dict:
    out: dict = {"data": "2026-01-15", "descricao": descricao, "valor": valor}
    if tipo is not None:
        out["tipo"] = tipo
    return out


# =============================================================================
# 1. pro_labore — crédito PJ-side + keyword PRO-LABORE
# =============================================================================


def test_pro_labore_label_assigned_when_pj_side_and_keyword_present():
    classifier = TransactionClassifier(_config_with_pj())
    acc = _account()
    acc["transacoes"] = [_tx("ARVO PRO-LABORE JANEIRO", 8000.00, tipo="credito")]

    results = classifier.classify_account(acc)

    assert len(results) == 1
    tx = results[0]
    assert tx.kind == "receita"
    assert tx.categoria == "pro_labore"
    assert tx.categoria in PJ_LABELS
    assert tx.origem == "Arvo (David - PJ)"


def test_pro_labore_keyword_variants_all_matched():
    """3 variantes de "pro-labore" todas batem."""
    classifier = TransactionClassifier(_config_with_pj())
    for variant in ("PRO-LABORE", "PROLABORE", "PRO LABORE"):
        acc = _account()
        acc["transacoes"] = [_tx(f"ARVO {variant} REF 01/26", 8000.00, tipo="credito")]
        results = classifier.classify_account(acc)
        assert results[0].categoria == "pro_labore", f"variant {variant!r} não bateu"


def test_pro_labore_requires_pj_side_proxy():
    """Keyword pro-labore SEM pj_source_mapping → não atribui pro_labore."""
    classifier = TransactionClassifier(_config_without_pj_mapping())
    acc = _account()
    acc["transacoes"] = [_tx("EMPRESA XPTO PRO-LABORE", 8000.00, tipo="credito")]

    results = classifier.classify_account(acc)

    assert results[0].categoria != "pro_labore"
    # Cai no fallback de receita (sem PJ mapping → outras_receitas).
    assert results[0].kind == "receita"


# =============================================================================
# 2. lucros_distribuidos — crédito PJ-side que NÃO casou pro_labore
# =============================================================================


def test_lucros_distribuidos_label_assigned_when_pj_side_and_no_prolabore():
    classifier = TransactionClassifier(_config_with_pj())
    acc = _account()
    acc["transacoes"] = [_tx("BRANDLOVERS DISTRIBUICAO MENSAL", 25000.00, tipo="credito")]

    results = classifier.classify_account(acc)

    assert results[0].kind == "receita"
    assert results[0].categoria == "lucros_distribuidos"


def test_lucros_distribuidos_loses_to_pro_labore_when_both_keywords_present():
    """Pró-labore tem precedência — descrição com ambos cai em pro_labore."""
    classifier = TransactionClassifier(_config_with_pj())
    acc = _account()
    acc["transacoes"] = [_tx("CNRY PRO-LABORE + COMPLEMENTO LUCROS", 12000.00, tipo="credito")]

    results = classifier.classify_account(acc)

    assert results[0].categoria == "pro_labore"


# =============================================================================
# 3. das_simples — débito + keyword DAS (word-bounded)
# =============================================================================


def test_das_simples_label_assigned_on_debit_with_anchored_keyword():
    classifier = TransactionClassifier(_config_with_pj())
    acc = _account()
    acc["transacoes"] = [_tx("DARF/DAS SIMPLES NACIONAL", -1500.00, tipo="debito")]

    results = classifier.classify_account(acc)

    assert results[0].kind == "despesa"
    assert results[0].categoria == "das_simples"


def test_das_simples_no_false_positive_on_substring():
    """``ADASA`` (saneamento DF) não deve casar DAS — word-boundary."""
    classifier = TransactionClassifier(_config_with_pj())
    acc = _account()
    acc["transacoes"] = [_tx("ADASA CONTA SANEAMENTO", -180.00, tipo="debito")]

    results = classifier.classify_account(acc)

    assert results[0].categoria != "das_simples"


def test_das_simples_does_not_require_pj_proxy():
    """DAS é tributo PJ por natureza — não precisa pj_source_mapping populado."""
    classifier = TransactionClassifier(_config_without_pj_mapping())
    acc = _account()
    acc["transacoes"] = [_tx("DARF DAS MEI 03/26", -65.00, tipo="debito")]

    results = classifier.classify_account(acc)

    assert results[0].categoria == "das_simples"


# =============================================================================
# 4. folha_pj — débito + keyword folha + proxy habilitado (run_ctx)
# =============================================================================


def test_folha_pj_label_assigned_when_proxy_enabled():
    """Workspace com pj_source_mapping + receita PJ observada → folha_pj atribui."""
    classifier = TransactionClassifier(_config_with_pj())
    acc = _account()
    acc["transacoes"] = [
        # receita PJ que ativa has_pj_income
        _tx("ARVO PRO-LABORE", 8000.00, tipo="credito"),
        # candidato folha_pj
        _tx("SALARIO FUNCIONARIO XPTO", -3500.00, tipo="debito"),
    ]

    results = classifier.classify_account(acc)

    folha_pj = [r for r in results if r.categoria == "folha_pj"]
    assert len(folha_pj) == 1
    assert folha_pj[0].kind == "despesa"


def test_folha_pj_emits_warning_when_no_pj_source_mapping():
    """Workspace sem pj_source_mapping → folha_pj NÃO atribui + warning emitido."""
    classifier = TransactionClassifier(_config_without_pj_mapping())
    acc = _account()
    acc["transacoes"] = [
        _tx("SALARIO MARIA FUNCIONARIA", -3500.00, tipo="debito"),
        _tx("FOLHA DE PAGAMENTO 02/26", -7000.00, tipo="debito"),
    ]

    transactions, warnings = classifier.classify_all_with_warnings([acc])

    folha_pj = [t for t in transactions if t.categoria == "folha_pj"]
    assert folha_pj == []
    assert len(warnings) == 1
    w = warnings[0]
    assert isinstance(w, FolhaPJProxyUnavailable)
    assert w.reason == "no_pj_source_mapping"
    assert w.candidatas_count == 2
    assert "SALARIO" in w.sample_descricao
    # format() é human-readable e não vaza valor monetário
    formatted = w.format()
    assert "folha_pj proxy desabilitado" in formatted
    assert "3500" not in formatted and "7000" not in formatted


def test_folha_pj_emits_warning_when_pj_mapping_populated_but_no_pj_income_observed():
    """Workspace com pj_source_mapping populado, mas sem receita PJ observada
    no run → reason="no_pj_income_observed".
    """
    classifier = TransactionClassifier(_config_with_pj())
    acc = _account()
    acc["transacoes"] = [_tx("SALARIO FUNCIONARIO", -3500.00, tipo="debito")]

    transactions, warnings = classifier.classify_all_with_warnings([acc])

    folha_pj = [t for t in transactions if t.categoria == "folha_pj"]
    assert folha_pj == []
    assert len(warnings) == 1
    assert warnings[0].reason == "no_pj_income_observed"


def test_no_warning_when_no_folha_pj_candidates():
    """Ausência genuína de folha PJ — sem candidatas → sem warning."""
    classifier = TransactionClassifier(_config_without_pj_mapping())
    acc = _account()
    acc["transacoes"] = [_tx("Mercado Vila Mariana", -250.00, tipo="debito")]

    transactions, warnings = classifier.classify_all_with_warnings([acc])

    assert warnings == []


# =============================================================================
# 5. iss — débito + keyword ISS (word-bounded)
# =============================================================================


def test_iss_label_assigned_on_debit_with_anchored_keyword():
    classifier = TransactionClassifier(_config_with_pj())
    acc = _account()
    acc["transacoes"] = [_tx("PREFEITURA SP ISS 03/26", -450.00, tipo="debito")]

    results = classifier.classify_account(acc)

    assert results[0].kind == "despesa"
    assert results[0].categoria == "iss"


def test_iss_no_false_positive_on_substring():
    """ "DEMISSAO" / "MISSAO" contém ISS — não deve casar."""
    classifier = TransactionClassifier(_config_with_pj())
    acc = _account()
    acc["transacoes"] = [_tx("DEMISSAO VOLUNTARIA TAXA", -300.00, tipo="debito")]

    results = classifier.classify_account(acc)

    assert results[0].categoria != "iss"


# =============================================================================
# Integração: classify_all_with_warnings em workspace multi-account
# =============================================================================


def test_classify_all_with_warnings_aggregates_across_accounts():
    """Pre-pass do has_pj_income é run-level (todos os accounts)."""
    classifier = TransactionClassifier(_config_with_pj())
    acc_pj = _account(banco="Bradesco PJ", tipo_conta="extratoconta")
    acc_pj["transacoes"] = [_tx("ARVO PRO-LABORE", 8000.00, tipo="credito")]
    acc_pf = _account(banco="Itaú PF", tipo_conta="extratoconta")
    acc_pf["transacoes"] = [_tx("SALARIO JOAO FUNCIONARIO", -3500.00, tipo="debito")]

    transactions, warnings = classifier.classify_all_with_warnings([acc_pj, acc_pf])

    # has_pj_income foi detectado em acc_pj → folha_pj em acc_pf é atribuída
    folha_pj = [t for t in transactions if t.categoria == "folha_pj"]
    assert len(folha_pj) == 1
    assert warnings == []


def test_pj_labels_set_contains_expected_5_keys():
    """Sanity: PJ_LABELS é o conjunto fechado da API pública."""
    assert PJ_LABELS == frozenset(
        {"pro_labore", "lucros_distribuidos", "das_simples", "folha_pj", "iss"}
    )
