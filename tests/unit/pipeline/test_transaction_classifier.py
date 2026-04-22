"""Tests — ``TransactionClassifier`` (Sessão A4a · Fase 7 foundation).

Cobre paridade com ``process_transactions`` (``e4_categorize.py:589-730``).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.income_origin_resolver import IncomeOriginConfig  # noqa: E402
from pipeline.domain.services.internal_transfer_detector import (  # noqa: E402
    InternalTransferConfig,
)
from pipeline.domain.services.transaction_classifier import (  # noqa: E402
    ClassifiedTransaction,
    ClassifierConfig,
    TransactionClassifier,
)

# =============================================================================
# Helpers
# =============================================================================


def _account(
    *,
    banco: str = "Itaú",
    tipo_conta: str = "extratoconta",
    moeda: str = "BRL",
    titular: str = "david",
    transacoes: list[dict] | None = None,
) -> dict:
    return {
        "banco": banco,
        "tipo_conta": tipo_conta,
        "moeda": moeda,
        "titular": titular,
        "transacoes": list(transacoes or []),
    }


def _tx(
    data: str,
    descricao: str,
    valor: float,
    *,
    tipo: str | None = None,
) -> dict:
    out: dict = {"data": data, "descricao": descricao, "valor": valor}
    if tipo is not None:
        out["tipo"] = tipo
    return out


def _default_config(**overrides) -> ClassifierConfig:
    """Config mínimo para testes — keywords simples, sem transferências."""
    return ClassifierConfig.from_configs(
        categorization={
            "expense_keywords": overrides.get(
                "expense_kw", {"mercado": ["mercado"], "uber": ["uber"]}
            ),
            "income_keywords": overrides.get("income_kw", {"receita_clt": ["salario"]}),
            "internal_transfer_patterns": overrides.get("transfer_patterns", []),
            "clt_source_mapping": overrides.get("clt", {"empregador": "Empregador Principal"}),
            "pj_source_mapping": overrides.get("pj", {}),
        },
        family=overrides.get("family", {}),
    )


# =============================================================================
# Config from_configs
# =============================================================================


class TestConfig:
    def test_from_configs_combines_pix_patterns_from_family(self):
        cat = {
            "expense_keywords": {},
            "income_keywords": {},
            "internal_transfer_patterns": ["X"],
            "clt_source_mapping": {},
            "pj_source_mapping": {},
        }
        fam = {
            "transferencias_internas": {
                "patterns_pix": ["Y"],
                "recipients": ["Recipient"],
                "patterns_bank_specific": {"c6": ["Pagamento"]},
                "patterns_global": ["PIX SAQUE"],
            }
        }
        cfg = ClassifierConfig.from_configs(categorization=cat, family=fam)

        # Patterns internos = concat(cat.internal_transfer_patterns, family.patterns_pix)
        assert "X" in cfg.transfer_config.internal_patterns
        assert "Y" in cfg.transfer_config.internal_patterns
        assert "Recipient" in cfg.transfer_config.internal_recipients
        assert cfg.transfer_config.bank_specific_patterns["c6"] == ("Pagamento",)
        assert "PIX SAQUE" in cfg.transfer_config.global_transfer_patterns

    def test_defaults_when_empty(self):
        cfg = ClassifierConfig.from_configs()
        assert cfg.expense_keywords == {}
        assert cfg.income_keywords == {}


# =============================================================================
# Crédito → receita
# =============================================================================


class TestCreditClassification:
    def test_credito_matches_income_keyword(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        acc = _account(transacoes=[_tx("2026-01-05", "SALARIO EMPREGADOR", 5000, tipo="credito")])
        results = classifier.classify_account(acc)

        assert len(results) == 1
        r = results[0]
        assert r.kind == "receita"
        assert r.categoria == "receita_clt"
        assert r.origem == "Empregador Principal"
        assert r.valor == 5000.0

    def test_credito_without_keyword_falls_back_to_outras_receitas(self):
        cfg = _default_config(income_kw={"receita_clt": ["salario"]})
        classifier = TransactionClassifier(cfg)

        acc = _account(transacoes=[_tx("2026-01-05", "RECEBIDO ALGUEM", 200, tipo="credito")])
        results = classifier.classify_account(acc)

        assert results[0].categoria == "outras_receitas"
        assert results[0].origem == "Outras Receitas"

    def test_tipo_credit_accented_is_normalized(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        acc = _account(transacoes=[_tx("2026-01-05", "SALARIO", 5000, tipo="crédito")])
        results = classifier.classify_account(acc)

        assert results[0].kind == "receita"

    def test_credit_inferred_by_positive_value_when_tipo_absent(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        acc = _account(transacoes=[{"data": "2026-01-05", "descricao": "SALARIO", "valor": 5000}])
        results = classifier.classify_account(acc)

        assert results[0].kind == "receita"


# =============================================================================
# Débito → despesa
# =============================================================================


class TestDebitClassification:
    def test_debito_matches_expense_keyword(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        acc = _account(transacoes=[_tx("2026-01-05", "MERCADO PAO", -100, tipo="debito")])
        results = classifier.classify_account(acc)

        assert len(results) == 1
        d = results[0]
        assert d.kind == "despesa"
        assert d.categoria == "mercado"
        # Valor positivo mesmo que input era negativo.
        assert d.valor == 100.0

    def test_debit_without_keyword_falls_back_to_nao_identificado(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        acc = _account(transacoes=[_tx("2026-01-05", "Algo desconhecido", -50, tipo="debito")])
        results = classifier.classify_account(acc)

        assert results[0].categoria == "nao_identificado"

    def test_debit_inferred_by_negative_value(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        acc = _account(transacoes=[{"data": "2026-01-05", "descricao": "UBER", "valor": -30}])
        results = classifier.classify_account(acc)

        assert results[0].kind == "despesa"
        assert results[0].categoria == "uber"


# =============================================================================
# Transferência interna
# =============================================================================


class TestInternalTransfer:
    def test_internal_transfer_detected_early(self):
        cfg = _default_config(transfer_patterns=["TRANSF MARIANA"])
        classifier = TransactionClassifier(cfg)

        acc = _account(transacoes=[_tx("2026-01-05", "PIX TRANSF MARIANA", -1000, tipo="debito")])
        results = classifier.classify_account(acc)

        assert results[0].kind == "transferencia"
        assert results[0].categoria is None

    def test_internal_transfer_on_credit(self):
        cfg = _default_config(transfer_patterns=["TRANSF DAVID"])
        classifier = TransactionClassifier(cfg)

        acc = _account(transacoes=[_tx("2026-01-05", "PIX TRANSF DAVID", 1000, tipo="credito")])
        results = classifier.classify_account(acc)

        assert results[0].kind == "transferencia"


# =============================================================================
# Fatura
# =============================================================================


class TestFatura:
    def test_fatura_without_tipo_positive_value_is_despesa(self):
        """Faturas: valor positivo sem tipo = compra (despesa)."""
        cfg = _default_config(expense_kw={"uber": ["uber"]})
        classifier = TransactionClassifier(cfg)

        acc = _account(
            tipo_conta="faturacarbon",
            transacoes=[{"data": "2026-01-05", "descricao": "UBER", "valor": 30}],
        )
        results = classifier.classify_account(acc)

        assert results[0].kind == "despesa"
        assert results[0].valor == 30.0

    def test_fatura_with_negative_value_is_credito_estorno(self):
        """Faturas: valor negativo sem tipo = estorno (crédito)."""
        cfg = _default_config(income_kw={"outras_receitas": ["estorno"]})
        classifier = TransactionClassifier(cfg)

        acc = _account(
            tipo_conta="faturacarbon",
            transacoes=[{"data": "2026-01-05", "descricao": "ESTORNO X", "valor": -30}],
        )
        results = classifier.classify_account(acc)

        assert results[0].kind == "receita"


# =============================================================================
# Integração multi-conta
# =============================================================================


class TestClassifyAll:
    def test_processes_multiple_accounts(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        a = _account(transacoes=[_tx("2026-01-05", "MERCADO", -100, tipo="debito")])
        b = _account(
            banco="Nubank",
            transacoes=[_tx("2026-01-06", "UBER", -30, tipo="debito")],
        )

        results = classifier.classify_all([a, b])

        assert len(results) == 2
        bancos = {r.banco for r in results}
        assert bancos == {"Itaú", "Nubank"}


# =============================================================================
# Valor coercion
# =============================================================================


class TestValorCoercion:
    def test_valor_string_brazilian_format(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        acc = _account(
            transacoes=[
                {"data": "2026-01-05", "descricao": "UBER", "valor": "1.234,56", "tipo": "debito"}
            ]
        )
        results = classifier.classify_account(acc)

        assert results[0].valor == 1234.56

    def test_valor_invalid_defaults_to_zero(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        acc = _account(
            transacoes=[
                {"data": "2026-01-05", "descricao": "UBER", "valor": "nonsense", "tipo": "debito"}
            ]
        )
        results = classifier.classify_account(acc)

        assert results[0].valor == 0.0


# =============================================================================
# to_legacy_dict
# =============================================================================


class TestLegacyDict:
    def test_receita_dict_has_origem_and_categoria(self):
        tx = ClassifiedTransaction(
            kind="receita",
            data="2026-01-05",
            descricao="SALARIO",
            valor=5000.0,
            banco="Itaú",
            moeda="BRL",
            tipo_conta="extratoconta",
            titular="david",
            tipo="credito",
            categoria="receita_clt",
            origem="X",
        )
        d = tx.to_legacy_dict()
        assert d["categoria"] == "receita_clt"
        assert d["origem"] == "X"
        assert "tipo" not in d

    def test_despesa_dict_no_origem(self):
        tx = ClassifiedTransaction(
            kind="despesa",
            data="2026-01-05",
            descricao="MERCADO",
            valor=100.0,
            banco="Itaú",
            moeda="BRL",
            tipo_conta="extratoconta",
            titular="david",
            tipo="debito",
            categoria="mercado",
        )
        d = tx.to_legacy_dict()
        assert d["categoria"] == "mercado"
        assert "origem" not in d

    def test_transferencia_dict_has_tipo(self):
        tx = ClassifiedTransaction(
            kind="transferencia",
            data="2026-01-05",
            descricao="PIX MARIANA",
            valor=1000.0,
            banco="Itaú",
            moeda="BRL",
            tipo_conta="extratoconta",
            titular="david",
            tipo="debito",
        )
        d = tx.to_legacy_dict()
        assert d["tipo"] == "debito"
        assert "categoria" not in d
        assert "origem" not in d


# =============================================================================
# Defensive: entradas malformadas
# =============================================================================


class TestDefensive:
    def test_empty_account_returns_empty_list(self):
        cfg = _default_config()
        assert TransactionClassifier(cfg).classify_account({}) == []

    def test_account_without_transacoes_key(self):
        cfg = _default_config()
        assert TransactionClassifier(cfg).classify_account({"banco": "X"}) == []

    def test_skips_non_dict_transaction(self):
        cfg = _default_config()
        classifier = TransactionClassifier(cfg)

        acc = _account(
            transacoes=[
                None,
                "string",
                {"data": "2026-01-05", "descricao": "MERCADO", "valor": -100, "tipo": "debito"},
            ]
        )
        results = classifier.classify_account(acc)
        assert len(results) == 1
