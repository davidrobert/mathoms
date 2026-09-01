#!/usr/bin/env python3
"""Ledger de conservação E2→E3→E4 em cents — núcleo puro da skill ledger-certify (ADR-343/302).

Funções puras (testáveis sem DB): recebem os artefatos E2/E3/E4 como dicts e
computam as igualdades de conservação em **int cents** (tol-zero, ADR-090) +
detectam dupla-contagem de investimento (ADR-271) + atribuem o veredito (5
estados fail-closed da rubrica). Reusa `dev.golden_diff.to_cents` (não reimplementa
aritmética de cents).

**Conservação é o piso, não o teto:** os piores erros são sum-preserving. Este
módulo cobre a **camada A** (conservação objetiva por transição de stage) + o
detector de dupla-contagem (**camada B**, o check que falha num cenário
sum-preserving). A camada B de fronteira de categoria (natureza/consumo) é
julgamento de domínio delegado ao financial-planner, não codificável aqui.
"""

from __future__ import annotations

import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.golden_diff import to_cents

# Detector cross-grupo (camada B, ADR-354 · A40.l1) — implementado nos módulos irmãos
# ``dev.ledger_cross_group`` (detecção) e ``dev.ledger_cross_group_render`` (render) para
# manter os arquivos sob o teto de 500 linhas, e re-exportado aqui porque este é o ponto
# de entrada documentado do ledger.
from dev.ledger_cross_group import (  # noqa: F401
    EXPLAINED_DIVERGENCE,
    CrossGroupCollision,
    CrossGroupSummary,
    cross_group_coverage,
    cross_group_double_count,
    cross_group_explained,
    cross_group_numerator,
    cross_group_summary,
    cross_group_unkeyable,
    validate_explained,
)
from dev.ledger_cross_group_render import fmt_cross_group  # noqa: F401

# Re-export por BINDING: este módulo é o ponto de entrada documentado do ledger, e os
# call-sites (harness, rubrica, testes) importam daqui. Chamada qualificada tornaria
# inertes os `monkeypatch` que apontam para este namespace — lição do #1915 (A42.l14).
from dev.ledger_e2e3 import (  # noqa: F401,E402
    declared_removed_count,
    e2_to_e3,
)
from dev.ledger_verdicts import (  # noqa: F401,E402
    COBERTO_SEM_VALOR,
    CONSERVADO,
    DEDUP_LEGITIMO,
    NAO_VERIFICAVEL,
    PERDA_SILENCIOSA,
    ConservationResult,
)

# ─────────────────────────── E3 → E4 ───────────────────────────
#
# O que esta perna NÃO discrimina ([[ADR-426]] §Consequências): erro de SINAL já
# presente no E3 e propagado fielmente pelo E4. Na forma dominante do dado, a tx não
# declara `tipo` e a direção É derivada do sinal (`_normalize_tipo`) — não existe
# segunda declaração independente para discordar dele. Quando `tipo` existe, o
# classificador aplica `abs(valor)` na despesa e a discordância atravessa sem rastro.
# Isso é fidelidade do E3 — perna E2→E3 e `parse-certify` —, não conservação desta
# transição. Medido em [[A42.l18]]: inverter o sinal de N débitos deixa Δ=0.


def _bucket_value_ok(bucket: dict) -> bool:
    """Σ totais_por_categoria == total_geral (cents)."""
    total = to_cents(bucket.get("total_geral", 0))
    parts = sum(to_cents(v) for v in bucket.get("totais_por_categoria", {}).values())
    return total == parts


def _classifier_skips(e3_artifacts: list[dict]) -> int:
    """Canal de exclusão E3→E4 declarado: tx survivor do E3 que o
    ``TransactionClassifier`` pula ANTES de classificar — mirror fiel dos dois
    ``continue`` de ``_classify_account_audit`` (tx não-dict + linha
    ``info_fiscal_anual``, ADR-242: informe fiscal anual não entra no fluxo mensal).
    Reusa o predicado canônico ``is_info_fiscal_anual`` como fonte única (não um
    literal duplicado no harness), simétrico ao ``_skips_reconcile`` da perna E2→E3
    (ADR-347). Sem este termo, o gap E3→E4 vira falso ``perda-silenciosa`` (P0);
    resíduo NÃO coberto por este canal permanece perda (anti-silêncio ADR-342)."""
    from pipeline.domain.services.llm_category_hint import is_info_fiscal_anual

    def _skip(tx: object) -> bool:  # espelha os dois `continue` de _classify_account_audit
        return not isinstance(tx, dict) or is_info_fiscal_anual(tx.get("categoria_sugerida"))

    return sum(
        _skip(tx)
        for art in e3_artifacts
        if isinstance(art, dict)  # paridade com load_reconciled_accounts (fail-safe)
        for tx in (art.get("transacoes") or [])
    )


def _survivor_value_cents(e3_artifacts: list[dict]) -> int:
    """Σ |valor| (cents) das tx E3 NÃO-puladas pelo classificador. Usa ``valor``
    (não ``amount``) p/ paridade com ``_coerce_valor`` do classificador — o lado
    ``classified`` soma o mesmo campo, evitando drift amount↔valor no check de valor."""
    from pipeline.domain.services.llm_category_hint import is_info_fiscal_anual

    def _keep(tx: object) -> bool:
        return isinstance(tx, dict) and not is_info_fiscal_anual(tx.get("categoria_sugerida"))

    return sum(
        abs(to_cents(tx.get("valor", 0)))
        for art in e3_artifacts
        if isinstance(art, dict)
        for tx in (art.get("transacoes") or [])
        if _keep(tx)
    )


@dataclass(frozen=True)
class _E3E4Signals:
    """Sinais de conferência declarados pelo E4 em ``despesas._lineage.signals``.
    Os dois de cents são ``None`` quando o produtor não os declara (artefato
    pré-[[ADR-426]]) — ausência é "não medido", nunca "mediu e deu zero"."""

    tx_total: int
    dedup_collapsed: int
    dedup_collapsed_cents: int | None
    transferencias_cents: int | None


def _opt_int(raw: object) -> int | None:
    """``None`` quando o sinal não foi declarado; int quando foi (inclusive ``"0"``)."""
    return int(raw) if isinstance(raw, str) and raw.lstrip("-").isdigit() else None


def _e3e4_signals(despesas: dict) -> _E3E4Signals:
    sig = despesas.get("_lineage", {}).get("signals", {})
    return _E3E4Signals(
        int(sig.get("tx_total", 0)),
        int(sig.get("dedup_collapsed", 0)),
        _opt_int(sig.get("dedup_collapsed_cents")),
        _opt_int(sig.get("transferencias_cents")),
    )


def _e3e4_value_out(despesas: dict, receitas: dict, sig: _E3E4Signals) -> int | None:
    """Σ do DESTINO em cents — os dois baldes serializados + as transferências (sem
    balde próprio) + o valor que o dedup do E4 removeu. Produtor diferente do lado de
    origem: é a soma que o relatório mostra, não uma re-soma da mesma lista. ``None``
    quando o produtor não declara os dois termos ⇒ eixo-valor não medido."""
    if sig.dedup_collapsed_cents is None or sig.transferencias_cents is None:
        return None
    return (
        to_cents(despesas.get("total_geral", 0))
        + to_cents(receitas.get("total_geral", 0))
        + sig.transferencias_cents
        + sig.dedup_collapsed_cents
    )


def _e3e4_destino(despesas: dict, receitas: dict, transferencias_count: int, dedup: int) -> int:
    return (
        receitas.get("total_transacoes", 0)
        + despesas.get("total_transacoes", 0)
        + transferencias_count
        + dedup
    )


def e3_to_e4(
    e3_artifacts: list[dict],
    despesas: dict,
    receitas: dict,
    transferencias_count: int,
) -> ConservationResult:
    """Conservação E3→E4: count fecha, baldes fecham, e o VALOR sobrevivente E3 ==
    Σ do destino declarado (baldes + transferências + removido pelo dedup)."""
    excluded = _classifier_skips(e3_artifacts)
    survivors = sum(a.get("transacoes_total", 0) for a in e3_artifacts) - excluded
    value_in = _survivor_value_cents(e3_artifacts)
    sig = _e3e4_signals(despesas)
    destino = _e3e4_destino(despesas, receitas, transferencias_count, sig.dedup_collapsed)
    buckets_ok = _bucket_value_ok(despesas) and _bucket_value_ok(receitas)
    value_out = _e3e4_value_out(despesas, receitas, sig)
    v, d = _e3e4_count_verdict(survivors, excluded, sig.tx_total, destino, buckets_ok)
    v, d = _value_downgrade(v, d, value_in, value_out)
    return ConservationResult(
        "E3->E4", sig.tx_total, destino, value_in, value_out, sig.dedup_collapsed, v, d
    )


def _e3e4_checks(survivors: int, excluded: int, tx_total: int, destino: int, buckets_ok: bool):
    return [
        (
            survivors != tx_total,
            PERDA_SILENCIOSA,
            f"survivors {survivors} (excl. {excluded} info_fiscal/não-dict) != tx_total "
            f"{tx_total} (dropou)",
        ),
        (tx_total != destino, PERDA_SILENCIOSA, f"tx_total {tx_total} != destino {destino}"),
        (not buckets_ok, PERDA_SILENCIOSA, "Σ categorias != total_geral num balde"),
    ]


def _value_downgrade(verdict: str, detail: str, value_in: int, value_out: int | None):
    """WARN-first: count-conservado com VALOR não-provado cai para
    ``coberto-sem-verificação`` — nunca afirma ``conservado`` sobre valor não-provável,
    nunca sobe a PERDA por valor (evita falso-P0 por convenção de sinal/amount).
    ``value_out is None`` (produtor não declara) é ``coberto``, não ``conservado``:
    antes da declaração o eixo-valor era uma identidade e passava sempre."""
    if verdict != CONSERVADO:
        return verdict, detail
    if value_out is None:
        return COBERTO_SEM_VALOR, "count fecha; destino E3→E4 sem valor declarado"
    if value_in == value_out:
        return verdict, detail
    return (
        COBERTO_SEM_VALOR,
        f"count fecha; valor E3→E4 não-provado (Δ={value_in - value_out} cents)",
    )


def _e3e4_count_verdict(survivors: int, excluded: int, tx_total: int, destino: int, ok: bool):
    checks = _e3e4_checks(survivors, excluded, tx_total, destino, ok)
    default = (CONSERVADO, f"count e baldes fecham (excl. {excluded} info_fiscal/não-dict)")
    return next(((vv, dd) for cond, vv, dd in checks if cond), default)


# ─────────────────── dedup de investimento (camada B, P0) ───────────────────


def _norm(text: str) -> str:
    """Normaliza texto para chave de identidade de posição (ADR-271)."""
    stripped = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join(stripped.lower().split())


def _pos_descriptor(pos: dict) -> str:
    """Descritor estável e time-invariante de uma posição: ticker quando houver,
    senão nome+vencimento. É o que separa DOIS produtos distintos de UMA mesma
    posição re-snapshotada — a descrição sozinha vem vazia neste corpus, e keyar só
    por (tipo|instituição) funde produtos distintos do mesmo snapshot (LC-06)."""
    ticker = _norm(pos.get("ticker_norm") or pos.get("ticker") or pos.get("codigo") or "")
    if ticker:
        return ticker
    nome = _norm(pos.get("nome") or pos.get("descricao") or pos.get("name") or "")
    venc = _norm(pos.get("vencimento") or "")
    return f"{nome}@{venc}" if venc else nome


def _pos_value_cents(pos: dict) -> int:
    for k in ("valor_atual", "valor_total", "current_value", "valor_brl", "valor"):
        raw = pos.get(k)
        if raw not in (None, ""):
            return to_cents(raw)
    return 0


def _pos_data_ref(pos: dict) -> str:
    return _norm(pos.get("data_referencia") or pos.get("data_posicao") or pos.get("periodo") or "")


def _pos_identity(pos: dict) -> tuple[str, str, str]:
    """Identidade de posição SEM membro nem tempo. Membro fora da chave de propósito:
    o vetor real (snapshot stale via escape membro-vazio) exige que a identidade não
    dependa de atribuição de membro (frágil, ADR-287); o tempo entra à parte."""
    return (_norm(pos.get("tipo", "")), _norm(pos.get("instituicao", "")), _pos_descriptor(pos))


def _identity_label(identity: tuple[str, str, str], reason: str) -> str:
    tipo, inst, desc = identity
    return f"{tipo}|{inst}|{desc or '<sem-descrição>'} [{reason}]"


def _exact_dups(positions: list[dict]) -> set[tuple[str, str, str]]:
    """Identidades cuja linha COMPLETA (identidade + data_ref + valor + membro)
    aparece 2×: duplicata literal dentro de um snapshot."""
    seen: dict[tuple, int] = {}
    for pos in positions:
        full = _pos_identity(pos) + (
            _pos_data_ref(pos),
            _pos_value_cents(pos),
            _norm(pos.get("membro", "")),
        )
        seen[full] = seen.get(full, 0) + 1
    return {full[:3] for full, n in seen.items() if n > 1}


def _cross_period(positions: list[dict]) -> set[tuple[str, str, str]]:
    """Identidades presentes em ≥2 ``data_referencia`` distintas: somar dois
    snapshots da MESMA posição infla o patrimônio (o vetor real — ex.: binance
    stale). Só conta ``data_ref`` não-vazia (fail-safe: sem data não afirma nada)."""
    refs: dict[tuple[str, str, str], set[str]] = {}
    for pos in positions:
        dr = _pos_data_ref(pos)
        if dr:
            refs.setdefault(_pos_identity(pos), set()).add(dr)
    return {ident for ident, drs in refs.items() if len(drs) > 1}


def investment_double_count(investimentos: dict) -> list[str]:
    """Posições dupla-contadas (ADR-271) — falha num cenário sum-preserving. Dois
    vetores: duplicata literal num snapshot + mesma posição em ≥2 ``data_referencia``.
    NÃO alerta em N produtos distintos do mesmo tipo/instituição no mesmo snapshot
    (valor/descritor diferentes ⇒ somar é correto) — o falso-positivo do LC-06."""
    positions = [p for p in investimentos.get("dados", []) if isinstance(p, dict)]
    hits: dict[tuple[str, str, str], str] = {}
    for ident in _exact_dups(positions):
        hits[ident] = "duplicata-exata"
    for ident in _cross_period(positions):
        hits.setdefault(ident, "snapshot-stale-cross-período")
    return [_identity_label(ident, reason) for ident, reason in hits.items()]
