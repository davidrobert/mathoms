"""Identidade v2 de ``TransactionOverride`` (ADR-282) — unifica o hash do subsistema
de override/learning com o ``natural_key`` v2 do pipeline (``compute_natural_key``),
aposentando o terceiro hash ``generate_transaction_hash`` (D6 da A23.l3). Adapters D3
([[ADR-278]]) só mapeiam nomes; normalização vive no hasher. Slice 1 cobre o caminho
limpo (``ClassifiedTransaction`` carrega ``tipo`` → ``direction`` correto em
fatura-estorno); o adapter de ``TransactionItem`` (read-path) entra na slice 2."""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.domain.services._tx_identity import (
    HashInputs,
    build_hash_inputs,
    compute_natural_key,
)
from pipeline.domain.services.transaction_classifier import ClassifiedTransaction


@dataclass(frozen=True)
class OverrideIdentity:
    """Hash v2 + snapshot dos inputs — linha de override auto-suficiente (ADR-282)."""

    natural_key_hash: str
    hash_version: int
    tx_data: str
    tx_banco: str
    tx_titular: str
    tx_tipo_conta: str
    tx_valor_cents: int
    tx_moeda: str
    tx_direction: str
    tx_descricao: str

    def as_columns(self) -> dict:
        """Mapeia para as colunas v2 de ``transaction_overrides`` (ADR-282 M1)."""
        return {
            "natural_key_hash": self.natural_key_hash,
            "hash_version": self.hash_version,
            "tx_data": self.tx_data,
            "tx_banco": self.tx_banco,
            "tx_titular": self.tx_titular,
            "tx_tipo_conta": self.tx_tipo_conta,
            "tx_valor_cents": self.tx_valor_cents,
            "tx_moeda": self.tx_moeda,
            "tx_direction": self.tx_direction,
            "tx_descricao": self.tx_descricao,
        }


def _identity_from_inputs(inputs: HashInputs) -> OverrideIdentity:
    nk = compute_natural_key(inputs)
    return OverrideIdentity(
        natural_key_hash=nk.hash,
        hash_version=nk.hash_version,
        tx_data=inputs.data,
        tx_banco=inputs.banco,
        tx_titular=inputs.titular,
        tx_tipo_conta=inputs.tipo_conta,
        tx_valor_cents=inputs.valor_cents,
        tx_moeda=inputs.moeda,
        tx_direction=inputs.direction,
        tx_descricao=inputs.descricao,
    )


def inputs_from_classified_tx(tx: ClassifiedTransaction) -> HashInputs:
    """Adapter D3 — ``ClassifiedTransaction`` (linha E4) → ``HashInputs``."""
    return build_hash_inputs(
        data=tx.data,
        banco=tx.banco,
        titular=tx.titular,
        tipo_conta=tx.tipo_conta,
        valor=tx.valor,
        moeda=tx.moeda,
        descricao=tx.descricao,
        tipo=tx.tipo,
    )


def identity_from_classified_tx(tx: ClassifiedTransaction) -> OverrideIdentity:
    """Hash v2 + snapshot de uma linha E4 classificada (caminho do learning loop)."""
    return _identity_from_inputs(inputs_from_classified_tx(tx))
