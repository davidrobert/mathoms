"""LC-03 (certificação ledger-certify r2) — o "drop de 1 tx" E3→E4 é o skip
**intencional** de linha info-fiscal-anual (ADR-242), NÃO perda silenciosa.

A r2 mediu `Σ transacoes_total(E3)=5724` vs `tx_total(_lineage)=5723`. Este teste
localiza a causa: `TransactionClassifier` exclui do fluxo de caixa mensal as linhas
marcadas `categoria_sugerida == INFO_FISCAL_ANUAL` (`transaction_classifier.py`
`_classify_account_audit`, ADR-242) — comportamento correto (evita double-count e
distorção de KPIs). Follow-up de conservação (família LC-01): o E4 deve **declarar**
esse skip (`intake_skipped` no `_lineage`) para que `e3_total == classified + skips`
feche — hoje o skip é silencioso e a ledger-certify o vê como perda."""

from __future__ import annotations

from pipeline.domain.services.llm_category_hint import INFO_FISCAL_ANUAL
from pipeline.domain.services.transaction_classifier import (
    ClassifierConfig,
    TransactionClassifier,
)


def _account(txns: list[dict]) -> dict:
    return {
        "banco": "itau",
        "tipo_conta": "extratoconta",
        "titular": "titular",
        "moeda": "BRL",
        "transacoes": txns,
    }


def _classifier() -> TransactionClassifier:
    return TransactionClassifier(ClassifierConfig.from_configs(categorization={}, family={}))


def test_info_fiscal_anual_linha_excluida_do_fluxo_e3_para_e4():
    clf = _classifier()
    normal = {"data": "2026-01-05", "descricao": "MERCADO", "valor": -100.0}
    fiscal = {
        "data": "2026-01-31",
        "descricao": "INFORME IR RENDIMENTOS",
        "valor": 50000.0,
        "categoria_sugerida": INFO_FISCAL_ANUAL,
    }
    # 2 tx no E3 → 1 classificada no E4: a linha info-fiscal-anual é o "drop de 1".
    assert len(clf.classify_all([_account([normal, fiscal])])) == 1
    # Isolando: só a fiscal → 0 (é ela que sai); só a normal → 1 (permanece).
    assert len(clf.classify_all([_account([fiscal])])) == 0
    assert len(clf.classify_all([_account([normal])])) == 1
