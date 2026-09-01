"""Atribuição de titularidade de uma posição — quem é o dono, e por qual evidência."""

# Extraído de `investments_consolidator` na A40.l96 ([[ADR-430]] §3): a pergunta
# "de quem é esta posição" é concern próprio, e o consolidador tinha 3 camadas de
# decisão inline no meio do laço de dedup.

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pipeline.domain.services.member_name_resolver import MemberNameResolver

if TYPE_CHECKING:  # import tardio em runtime para evitar ciclo
    from pipeline.domain.services.account_resolver import AccountResolver

AtribuicaoFonte = Literal["declarada", "conta_casada", "banco_unico", "indeterminada", "sem_dono"]
"""De onde veio o `membro` de uma posição ([[ADR-430]] §3)."""

# Sem isto, fechado o wiring E1→E4 o `banco_unico` sustenta quase toda a
# atribuição e o relatório afirmaria titularidade INFERIDA com o peso visual da
# DECLARADA — regressão sob [[ADR-394]] (fato ≠ hint).
_FONTE_POR_CONFIANCA: dict[str, AtribuicaoFonte] = {
    "strict": "conta_casada",
    "fallback_bank": "banco_unico",
}


def canonicalizar_membro(bruto: str, resolver: MemberNameResolver | None) -> str:
    """Chave curta do E1 → chave canônica do workspace ([[ADR-243]])."""
    # Não casar aqui é o defeito D3 da A40.l96: `papel_da_chave('david')` contra
    # `titular_key='david_robert_...'` devolve `sem_dono`. Sem match, preserva o
    # bruto — a telemetria do resolver já registra unknown/ambiguous.
    if not bruto or resolver is None:
        return bruto
    return resolver.resolve(bruto).canonical_key or bruto


def atribuir_por_conta(
    data: dict,
    inst_key: str,
    *,
    account_resolver: "AccountResolver",
    name_resolver: MemberNameResolver | None,
) -> tuple[str, AtribuicaoFonte]:
    """Titularidade a partir de (instituição, número de conta) — com a origem."""
    acc_num = data.get("numero_conta") or data.get("account_number")
    res = account_resolver.resolve(inst_key, acc_num)
    # ADR-226 §Emenda 2026-08-31: eixo de TITULARIDADE. O de conta responde
    # outra pergunta e não deve contaminar a atribuição patrimonial.
    if res.member_confidence == "ambiguous":
        # Sentinela da ADR-346 §4b — load-bearing, ver ADR-430 §3 Correção.
        return "needs_review", "indeterminada"
    if not res.member_key:
        return "", "sem_dono"
    fonte = _FONTE_POR_CONFIANCA.get(res.member_confidence, "banco_unico")
    return canonicalizar_membro(res.member_key, name_resolver), fonte


def soma_inferida(investimentos_atuais: dict | None) -> float:
    """Valor das posições cujo dono veio de INFERÊNCIA, não de declaração."""
    # Leitor de `atribuicao_fonte` ([[ADR-430]] §3). `conta_casada` casa por
    # número de conta declarado e conta como fato; `banco_unico` deduz do banco
    # ter um dono só, e é hint. Sem este leitor o campo nasceria morto.
    dados = (investimentos_atuais or {}).get("dados") or []
    return round(
        sum(
            float(p.get("valor_atual") or 0.0)
            for p in dados
            if isinstance(p, dict) and p.get("atribuicao_fonte") == "banco_unico"
        ),
        2,
    )
