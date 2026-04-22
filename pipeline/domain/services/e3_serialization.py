"""Serialização para o formato E3 legado (Sessão A2 da Fase 6).

O ``BankStatement`` é o value object canônico do domínio, mas o output do E3
em disco/DB segue o schema histórico definido em
``config/schemas/e3_reconciled.schema.json`` (campos ``banco``, ``tipo_conta``,
``periodo_cobertura``, ``fontes``, ``transacoes_total``,
``transacoes_duplicadas_removidas``...).

Este módulo concentra essa conversão **fora** de ``BankStatement`` para manter
o domain model limpo e independente do formato de saída legado. O
``main_with_store`` em ``scripts/e3_reconcile.py`` consome estas funções.

Funções puras, sem I/O — testáveis com fixtures de uma linha.
"""

from __future__ import annotations

from typing import Any, Iterable

from pipeline.domain.models.bank import BankCanonicalizer
from pipeline.domain.models.document import BankStatement


def _money_to_float(money) -> float | None:
    """Converte ``Money | None`` para ``float``; ``None`` permanece ``None``."""
    if money is None:
        return None
    return float(money.amount)


def _canonicalize_bank(institution: str, canonicalizer: BankCanonicalizer | None) -> str:
    """Resolve o banco para forma canônica usada em filenames legados.

    - Com ``canonicalizer``: aplica ``canonicalize`` (lowercase, sem acentos,
      mapeado para o código de ``institutions.json`` quando houver match).
    - Sem ``canonicalizer``: fallback simples ``lower().replace(" ", "")``
      (paridade com ``e3_reconcile.generate_output_filename``).
    """
    if canonicalizer is not None:
        return canonicalizer.canonicalize(institution)
    return (institution or "").lower().replace(" ", "")


def serialize_to_e3_legacy_format(
    statement: BankStatement,
    *,
    sources: Iterable[str],
    duplicates_removed: int = 0,
    titular: str | None = None,
) -> dict[str, Any]:
    """Converte ``BankStatement`` reconciliado para o dict E3 legado.

    Args:
        statement: extrato já reconciliado (pós-merge cross-file).
        sources: nomes de arquivo originais que contribuíram para o extrato
            (campo ``fontes`` do schema E3).
        duplicates_removed: contagem de transações descartadas durante o
            dedup cross-file (campo ``transacoes_duplicadas_removidas``).
        titular: opcional — se ``None``, usa ``statement.member_key``.

    Returns:
        Dict aderente a ``config/schemas/e3_reconciled.schema.json``.
    """
    saldo_inicial = _money_to_float(statement.opening_balance)
    saldo_final = _money_to_float(statement.closing_balance)
    saldo_inicial_unknown = saldo_inicial is None
    saldo_final_unknown = saldo_final is None
    if saldo_inicial is None:
        saldo_inicial = 0.0
    if saldo_final is None:
        saldo_final = 0.0

    transacoes = []
    for tx in statement.transactions:
        item: dict[str, Any] = {
            "data": tx.date.isoformat(),
            "descricao": tx.description,
            "valor": float(tx.amount.amount),
        }
        if tx.category:
            item["categoria"] = tx.category
        if tx.member_key:
            item["membro"] = tx.member_key
        if tx.source_document:
            item["arquivo_origem"] = tx.source_document
        transacoes.append(item)

    return {
        "banco": statement.institution,
        "tipo_conta": statement.account_type or "extrato",
        "titular": titular if titular is not None else statement.member_key,
        "moeda": statement.currency.upper(),
        "periodo_cobertura": {
            "inicio": statement.period_start.isoformat(),
            "fim": statement.period_end.isoformat(),
        },
        "saldo_inicial": saldo_inicial,
        "saldo_inicial_unknown": saldo_inicial_unknown,
        "saldo_final": saldo_final,
        "saldo_final_unknown": saldo_final_unknown,
        "fontes": list(sources),
        "transacoes_total": len(transacoes),
        "transacoes_duplicadas_removidas": int(duplicates_removed),
        "transacoes": transacoes,
    }


def generate_legacy_filename(
    statement: BankStatement,
    *,
    canonicalizer: BankCanonicalizer | None = None,
) -> str:
    """Gera o nome de arquivo E3 legado para um ``BankStatement``.

    Formato (paridade com ``e3_reconcile.generate_output_filename``):
        - Faturas (``account_type.startswith("fatura")``):
          ``{banco}_{tipo_conta}_{YYYYMM}_{YYYYMM}-3_reconciled.json``
          (sem moeda)
        - Demais: ``{banco}_{tipo_conta}_{MOEDA}_{YYYYMM}_{YYYYMM}-3_reconciled.json``

    A normalização de banco usa ``BankCanonicalizer`` quando disponível,
    com fallback ``lower().replace(" ", "")``.
    """
    banco = _canonicalize_bank(statement.institution, canonicalizer)
    tipo_conta = (statement.account_type or "extrato").lower()
    moeda = statement.currency.upper()
    inicio_ym = statement.period_start.strftime("%Y%m")
    fim_ym = statement.period_end.strftime("%Y%m")

    if tipo_conta.startswith("fatura"):
        return f"{banco}_{tipo_conta}_{inicio_ym}_{fim_ym}-3_reconciled.json"
    return f"{banco}_{tipo_conta}_{moeda}_{inicio_ym}_{fim_ym}-3_reconciled.json"


def generate_legacy_artifact_key(
    statement: BankStatement,
    *,
    canonicalizer: BankCanonicalizer | None = None,
) -> str:
    """Versão sem o sufixo ``-3_reconciled.json`` para usar como
    ``ArtifactStore`` key (o store anexa o sufixo via ``stage_suffix``).
    """
    return generate_legacy_filename(statement, canonicalizer=canonicalizer).removesuffix(
        "-3_reconciled.json"
    )
