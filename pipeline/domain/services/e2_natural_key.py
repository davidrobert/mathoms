"""Estampa K4 ``natural_key`` + ``direction`` + ``amount`` no write-path comum de E2
(ADR-278 B4 passo 1 + B5) — NÃO em ``to_e2_dict`` (só roda no round-trip E3). Cobre
vocabulário determinístico (banco/titular/tipo_conta) e LLM (instituicao/membro/
tipo_documento) por fallback; emite ``natural_key`` só com discriminantes presentes
(senão ``null`` classe-c, nunca hash degenerado). F1 **emite + mede**, não consome:
E4 segue v1 (D4) e os leitores seguem ``valor`` (cutover ``valor``→``amount`` é A24)."""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.domain.services._tx_identity import (
    _coerce_signed,
    _has_discriminants,
    build_hash_inputs,
    compute_natural_key,
    derive_direction,
    to_amount_string,
)


@dataclass(frozen=True)
class NaturalKeyStats:
    """Cobertura de estampagem — denominador/numerador do gate do passo 2."""

    tx_total: int
    with_key: int
    null_key: int


def _first(*values: str | None) -> str | None:
    for v in values:
        if v:
            return v
    return None


def _tx_key(tx: dict, *, banco, titular, tipo_conta, moeda, eligible: bool) -> dict | None:
    valor = tx.get("valor")
    if not (eligible and valor is not None):
        return None
    inputs = build_hash_inputs(
        data=tx.get("data"),
        banco=banco,
        titular=titular,
        tipo_conta=tipo_conta,
        valor=valor,
        moeda=moeda,
        descricao=tx.get("descricao"),
        tipo=tx.get("tipo"),
    )
    return compute_natural_key(inputs).to_dict()


def _stamp_tx(tx: dict, *, banco, titular, tipo_conta, moeda, eligible: bool) -> bool:
    # tipo_lancamento é categórico (NÃO é direction) → derive só de tipo+sinal.
    tx["direction"] = derive_direction(
        tipo=tx.get("tipo"), valor=_coerce_signed(tx.get("valor")), tipo_conta=tipo_conta
    )
    # ADR-278 B5: amount decimal-string aditivo (omite quando valor ausente/não-numérico).
    amount = to_amount_string(tx.get("valor"))
    if amount is not None:
        tx["amount"] = amount
    key = _tx_key(
        tx, banco=banco, titular=titular, tipo_conta=tipo_conta, moeda=moeda, eligible=eligible
    )
    tx["natural_key"] = key
    return bool(key)


def stamp_natural_key(result: dict) -> NaturalKeyStats:
    """Popula ``transacoes[].natural_key`` + ``direction`` + ``amount`` in-place; retorna cobertura."""
    banco = _first(result.get("banco"), result.get("instituicao"), result.get("institution"))
    titular = _first(result.get("titular"), result.get("documento_titular"), result.get("membro"))
    tipo_conta = _first(result.get("tipo_conta"), result.get("tipo"), result.get("tipo_documento"))
    moeda = result.get("moeda")
    txs = result.get("transacoes") or []
    eligible = _has_discriminants(banco, titular, tipo_conta)
    with_key = sum(
        _stamp_tx(
            tx, banco=banco, titular=titular, tipo_conta=tipo_conta, moeda=moeda, eligible=eligible
        )
        for tx in txs
    )
    return NaturalKeyStats(tx_total=len(txs), with_key=with_key, null_key=len(txs) - with_key)
