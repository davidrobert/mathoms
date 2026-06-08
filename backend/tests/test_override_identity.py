"""Identidade v2 de override (ADR-282 slice 1): o adapter ``ClassifiedTransaction``
→ ``natural_key`` v2 casa o hash do dedup, distingue direction, é imune ao drift de
sufixo PIX (o bug ADR-255 que orfaniza categorização manual) e produz uma linha
auto-suficiente (re-hasheável só do snapshot, sem replay de E4)."""

from __future__ import annotations

from backend.app.services.override_identity import (
    identity_from_classified_tx,
    inputs_from_classified_tx,
)
from pipeline.domain.services._tx_identity import (
    HashInputs,
    build_hash_inputs,
    compute_natural_key,
)
from pipeline.domain.services.transaction_classifier import ClassifiedTransaction


def _tx(**over) -> ClassifiedTransaction:
    base = dict(
        kind="despesa",
        data="2026-03-15",
        descricao="PAGAMENTO LOJA",
        valor=50.0,
        banco="c6bank",
        moeda="BRL",
        tipo_conta="conta_corrente",
        titular="Test User",
        tipo="debito",
        categoria="Lazer",
    )
    base.update(over)
    return ClassifiedTransaction(**base)


def test_identity_equals_dedup_natural_key_v2() -> None:
    """A invariante central: a identidade do override == natural_key v2 da MESMA linha."""
    tx = _tx()
    identity = identity_from_classified_tx(tx)
    dedup = compute_natural_key(
        build_hash_inputs(
            data=tx.data,
            banco=tx.banco,
            titular=tx.titular,
            tipo_conta=tx.tipo_conta,
            valor=tx.valor,
            moeda=tx.moeda,
            descricao=tx.descricao,
            tipo=tx.tipo,
        )
    )
    assert identity.natural_key_hash == dedup.hash
    assert identity.hash_version == 2


def test_direction_distinguishes_credit_from_debit() -> None:
    """Mesma magnitude, direction oposta → hashes distintos (v2 corrige o abs do v1)."""
    debit = identity_from_classified_tx(_tx(tipo="debito"))
    credit = identity_from_classified_tx(_tx(kind="receita", tipo="credito", origem="salario"))
    assert debit.tx_direction == "debit"
    assert credit.tx_direction == "credit"
    assert debit.natural_key_hash != credit.natural_key_hash


def test_fatura_estorno_direction_follows_tipo_not_sign() -> None:
    """Fatura com valor<0 + tipo=credito (estorno) → direction credit (D2/ADR-278)."""
    estorno = identity_from_classified_tx(
        _tx(kind="receita", valor=-120.0, tipo="credito", tipo_conta="fatura_cartao")
    )
    assert estorno.tx_direction == "credit"


def test_pix_suffix_drift_does_not_change_hash() -> None:
    """C6 re-extraído com sufixo de roteamento → MESMO hash (não orfaniza override)."""
    plain = identity_from_classified_tx(_tx(descricao="PAGAMENTO LOJA"))
    suffixed = identity_from_classified_tx(_tx(descricao="PAGAMENTO LOJA — TRANSF ENVIADA PIX"))
    assert plain.natural_key_hash == suffixed.natural_key_hash


def test_no_tipo_conta_collision_across_accounts() -> None:
    """Mesma data/desc/valor em contas distintas → hashes distintos (v1 colidia)."""
    corrente = identity_from_classified_tx(_tx(tipo_conta="conta_corrente"))
    poupanca = identity_from_classified_tx(_tx(tipo_conta="conta_poupanca"))
    assert corrente.natural_key_hash != poupanca.natural_key_hash


def test_snapshot_is_self_sufficient_for_rehash() -> None:
    """Invariante ADR-282: re-hashear só do snapshot reproduz o hash (sem replay E4)."""
    identity = identity_from_classified_tx(_tx())
    rehashed = compute_natural_key(
        HashInputs(
            data=identity.tx_data,
            banco=identity.tx_banco,
            titular=identity.tx_titular,
            tipo_conta=identity.tx_tipo_conta,
            valor_cents=identity.tx_valor_cents,
            moeda=identity.tx_moeda,
            direction=identity.tx_direction,
            descricao=identity.tx_descricao,
        )
    )
    assert rehashed.hash == identity.natural_key_hash


def test_adapter_returns_raw_inputs_not_normalized() -> None:
    """Snapshot guarda valor cru (lineage humano-legível); normalização vive no hasher."""
    inputs = inputs_from_classified_tx(_tx(descricao="PAGAMENTO LOJA — TRANSF ENVIADA PIX"))
    assert inputs.descricao == "PAGAMENTO LOJA — TRANSF ENVIADA PIX"
    assert inputs.valor_cents == 5000
