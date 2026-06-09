"""K4 natural_key v2 — paridade, determinismo, anti-drift e estampagem (ADR-278 B3/B4)."""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal, localcontext

import pytest

from pipeline.domain.services._tx_identity import (
    build_hash_inputs,
    compute_natural_key,
    compute_transaction_hash,
    decimal_cents,
    derive_direction,
    to_amount_string,
)
from pipeline.domain.services.e2_natural_key import stamp_natural_key
from pipeline.domain.services.transaction_classifier import _normalize_tipo

V1_FROZEN = "9589a7cf5f36990a"
V2_FROZEN = "09dd2534bd04b023"


def _nk(**kw) -> str:
    return compute_natural_key(build_hash_inputs(**kw)).hash


V2_FROZEN_575 = _nk(
    data="2026-01-01",
    banco="C6",
    titular="ana",
    tipo_conta="corrente",
    valor=0.575,
    moeda="BRL",
    descricao="pix",
    tipo=None,
)


def _base(**over) -> dict:
    base = dict(
        data="2026-01-01",
        banco="C6",
        titular="ana",
        tipo_conta="corrente",
        descricao="pix",
        moeda="BRL",
        valor=100.0,
    )
    base.update(over)
    return base


class TestParity:
    def test_a_shape_independence(self):
        # Mesma tx por shapes diferentes (float/str/Decimal) → mesmo hash.
        assert (
            _nk(**_base(valor=1234.56))
            == _nk(**_base(valor="1234.56"))
            == _nk(**_base(valor=Decimal("1234.56")))
        )

    def test_b_decimal_edge_no_drift(self):
        # 0.575 float ↔ Decimal → 58 cents idêntico (corrige int(round(0.575*100))==57).
        assert decimal_cents(0.575) == decimal_cents(Decimal("0.575")) == 58
        assert _nk(**_base(valor=0.575)) == _nk(**_base(valor=Decimal("0.575")))

    def test_c_moeda_direction_discriminate(self):
        entrada = _nk(**_base(valor=100.0))
        saida = _nk(**_base(valor=-100.0))
        usd = _nk(**_base(valor=100.0, moeda="USD"))
        assert entrada != saida
        assert entrada != usd
        assert saida != usd

    def test_emit_recompute_parity_vocabularies(self):
        # Mesma tx lógica por dois "vocabulários" de origem → mesmo HashInputs → mesmo hash.
        c = dict(
            data="2026-02-10",
            banco="Itau",
            titular="João",
            tipo_conta="corrente",
            descricao="TED",
            moeda="BRL",
        )
        assert _nk(**c, valor=Decimal("500.00"), tipo=None) == _nk(**c, valor=500.0, tipo="credito")

    def test_emit_recompute_parity_fatura_estorno(self):
        # Fatura estorno: valor<0 (sem tipo) ↔ tipo="credito" → mesmo direction → mesmo hash.
        c = dict(
            data="2026-03-01",
            banco="C6",
            titular="ana",
            tipo_conta="faturaunique",
            descricao="estorno",
            moeda="BRL",
        )
        assert _nk(**c, valor=-50.0, tipo=None) == _nk(**c, valor=Decimal("50.00"), tipo="credito")


class TestFrozenAndVersion:
    def test_v1_frozen(self):
        # Contrato com hashes históricos no DB — NÃO pode mudar (ADR-278 D1).
        h = compute_transaction_hash(
            data="2026-01-01",
            banco="C6 Bank",
            titular="Ana",
            tipo_conta="corrente",
            valor=1234.56,
            descricao="PIX recebido",
        )
        assert h == V1_FROZEN

    def test_v2_frozen(self):
        # v2 estável desde o nascimento (cents int no núcleo) — nunca rebaselinar.
        inp = build_hash_inputs(
            data="2026-01-01",
            banco="C6 Bank",
            titular="Ana",
            tipo_conta="corrente",
            valor=1234.56,
            moeda="BRL",
            descricao="PIX recebido",
            tipo=None,
        )
        nk = compute_natural_key(inp)
        assert nk.hash == V2_FROZEN
        assert nk.hash_version == 2

    def test_v2_sign_distinguishes_direction(self):
        # Substitui test_abs_value_collapses_sign (v1): em v2 entrada != saída.
        assert _nk(**_base(valor=100.0)) != _nk(**_base(valor=-100.0))

    def test_v1_still_collapses_sign(self):
        # v1 (shim) preserva o comportamento legado abs() para compat de DB.
        kw = dict(data="2026-01-01", banco="X", titular="y", tipo_conta="z", descricao="abc")
        assert compute_transaction_hash(valor=100.0, **kw) == compute_transaction_hash(
            valor=-100.0, **kw
        )


class TestDeterminism:
    def test_deterministic_under_rounding_context(self):
        # Rounding inline (ROUND_HALF_UP) vence o getcontext() mutável (ADR-111).
        with localcontext() as ctx:
            ctx.rounding = ROUND_DOWN
            assert decimal_cents(0.575) == 58
            assert _nk(**_base(valor=0.575)) == V2_FROZEN_575

    def test_run_twice_identical(self):
        assert _nk(**_base()) == _nk(**_base())


class TestDeriveDirectionAntiDrift:
    @pytest.mark.parametrize("valor", [100.0, -100.0, 0.0, 0.575, -0.01])
    @pytest.mark.parametrize("tipo_conta", ["corrente", "poupanca", "faturaunique", "faturagold"])
    def test_matches_normalize_tipo(self, valor, tipo_conta):
        # derive_direction (sign branch) deve espelhar _normalize_tipo (E4) — anti-drift.
        norm = _normalize_tipo(None, valor, tipo_conta)
        expected = "credit" if norm == "credito" else "debit"  # None/debito → debit
        assert derive_direction(tipo=None, valor=valor, tipo_conta=tipo_conta) == expected

    def test_tipo_wins_over_sign(self):
        # tipo explícito vence o sinal (não inverte em fatura).
        assert derive_direction(tipo="credito", valor=-100.0, tipo_conta="corrente") == "credit"
        assert derive_direction(tipo="débito", valor=100.0, tipo_conta="corrente") == "debit"


class TestStamp:
    def test_deterministic_producer_emits_key(self):
        result = {
            "banco": "C6",
            "tipo": "corrente",
            "moeda": "BRL",
            "titular": "ana",
            "tipo_conta": "corrente",
            "transacoes": [
                {"data": "2026-01-01", "descricao": "pix", "valor": 100.0},
                {"data": "2026-01-02", "descricao": "saque", "valor": -50.0},
            ],
        }
        stats = stamp_natural_key(result)
        assert stats.tx_total == 2 and stats.with_key == 2 and stats.null_key == 0
        txs = result["transacoes"]
        assert txs[0]["natural_key"]["hash_version"] == 2
        assert txs[0]["direction"] == "credit" and txs[1]["direction"] == "debit"
        assert txs[0]["natural_key"]["hash"] != txs[1]["natural_key"]["hash"]

    def test_fatura_without_titular_emits_null(self):
        # Classe-c: titular ausente → natural_key=null (nunca hash degenerado).
        result = {
            "banco": "C6",
            "tipo": "faturaunique",
            "moeda": "BRL",
            "titular": None,
            "transacoes": [{"data": "2026-01-01", "descricao": "loja", "valor": 99.9}],
        }
        stats = stamp_natural_key(result)
        assert stats.with_key == 0 and stats.null_key == 1
        assert result["transacoes"][0]["natural_key"] is None
        # direction ainda é emitido (não depende de discriminante).
        assert result["transacoes"][0]["direction"] == "debit"

    def test_llm_vocabulary_resolved_by_fallback(self):
        # LLM usa instituicao/membro/tipo_documento — costura resolve por fallback.
        result = {
            "instituicao": "Nubank",
            "tipo_documento": "extratoconta",
            "moeda": "BRL",
            "membro": "ana",
            "transacoes": [{"data": "2026-01-01", "descricao": "pix", "valor": 100.0}],
        }
        stats = stamp_natural_key(result)
        assert stats.with_key == 1
        assert result["transacoes"][0]["natural_key"]["hash_version"] == 2

    def test_empty_transacoes(self):
        stats = stamp_natural_key({"banco": "C6", "titular": "ana", "tipo_conta": "corrente"})
        assert stats.tx_total == 0 and stats.with_key == 0


class TestAmountString:
    """``to_amount_string`` — espelho decimal canônico de ``valor`` (ADR-278 B5)."""

    def test_float_mirror(self):
        assert to_amount_string(1234.56) == "1234.56"

    def test_signed_preserved(self):
        assert to_amount_string(-50.0) == "-50.0"

    def test_no_scientific_notation_large(self):
        # repr(float) grande vira E+ no Decimal; format("f") força ponto-fixo.
        out = to_amount_string(1e16)
        assert "E" not in out and "e" not in out
        assert Decimal(out) == Decimal("1E+16")

    def test_edge_575_preserves_third_digit(self):
        # Não quantiza: 3ª casa de borda preservada (paridade com decimal_cents).
        assert to_amount_string(0.575) == "0.575"
        assert decimal_cents(to_amount_string(0.575)) == decimal_cents(0.575)

    def test_decimal_and_str_shapes(self):
        assert to_amount_string(Decimal("100.00")) == "100.00"
        assert to_amount_string("100.5") == "100.5"

    def test_none_and_nonnumeric_return_none(self):
        # valor ausente ou BR-string ("1.234,56") → None (stamp omite a chave).
        assert to_amount_string(None) is None
        assert to_amount_string("1.234,56") is None


class TestStampAmount:
    """``amount`` estampado ao lado de ``valor`` no write-path comum (ADR-278 B5)."""

    def test_amount_mirrors_valor_at_cents(self):
        result = {
            "banco": "C6",
            "moeda": "BRL",
            "titular": "ana",
            "tipo_conta": "corrente",
            "transacoes": [
                {"data": "2026-01-01", "descricao": "pix", "valor": 100.0},
                {"data": "2026-01-02", "descricao": "saque", "valor": -50.5},
            ],
        }
        stamp_natural_key(result)
        txs = result["transacoes"]
        for tx in txs:
            assert decimal_cents(tx["amount"]) == decimal_cents(tx["valor"])
            assert Decimal(tx["amount"]) == Decimal(str(tx["valor"]))
        assert txs[0]["amount"] == "100.0" and txs[1]["amount"] == "-50.5"

    def test_amount_omitted_when_valor_absent(self):
        result = {
            "banco": "C6",
            "moeda": "BRL",
            "titular": "ana",
            "tipo_conta": "corrente",
            "transacoes": [{"data": "2026-01-01", "descricao": "sem valor"}],
        }
        stamp_natural_key(result)
        assert "amount" not in result["transacoes"][0]
