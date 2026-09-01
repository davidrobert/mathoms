#!/usr/bin/env python3
"""Perna E2→E3 do ledger — a identidade de TRÊS produtores (artefatos E2, artefatos E3,
log de execução do E3). Extraída de ``dev.ledger_conservation`` na A42.l3, quando o
núcleo cruzou as 500 linhas ao ganhar o resíduo computado; lá ficam a E3→E4 e o
vocabulário compartilhado. Funções puras — sem I/O, sem DB.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.golden_diff import to_cents
from dev.ledger_verdicts import (
    COBERTO_SEM_VALOR,
    CONSERVADO,
    PERDA_SILENCIOSA,
    ConservationResult,
)

# Doc-types que carregam posição/informe (não transação bancária): passam pelo
# reconciliador mas não produzem tx reconciliada — não podem inflar o denominador
# E2→E3 (LC-07). Espelha a distinção do E4 (``e4_categorizer_adapter``:
# ``tipo_documento in ("investment_report", "informe_rendimentos")``). Os tipos já
# normalizados (``investimentosposicao``, ``informerendimentos``…) saem via
# ``AccountGrouper.should_skip``; este set cobre as formas LLM com underscore.
_NON_TX_DOC_TYPES = frozenset({"investment_report", "informe_rendimentos"})


def _tx_cents(tx: dict) -> int:
    """Cents de uma transação. O pipeline move ``valor`` (float); ``amount``
    (decimal-string, ADR-278) é preferido quando presente por precisão."""
    raw = tx.get("amount")
    if raw in (None, ""):
        raw = tx.get("valor", 0)
    return to_cents(raw)


def _sum_cents(txns: list[dict]) -> int:
    return sum(_tx_cents(t) for t in txns)


def _skips_reconcile(artifact: dict) -> bool:
    """True se o reconciliador não produziria tx a partir deste artefato E2 — tipo
    pulado (``AccountGrouper.should_skip``: IRPF, posição, informe, fatura não-
    suportada) ou doc-type de posição/informe (``_NON_TX_DOC_TYPES``). Filtra o
    denominador E2→E3 para não contar tx que nunca entram no reconcile (LC-07)."""
    from pipeline.domain.services.account_grouper import AccountGrouper

    if not isinstance(artifact, dict):
        return True
    doc_type = str(artifact.get("tipo") or artifact.get("tipo_documento") or "").strip()
    if doc_type in _NON_TX_DOC_TYPES:
        return True
    return AccountGrouper().should_skip(artifact)


# Público desde A42.l20: o drift de `ledger_certify_core` precisa do MESMO normalizador
# que a conservação usa. Reimplementar a escolha canal-vs-legado num segundo módulo foi
# exatamente o defeito que aquela lane pagou.
def declared_removed_count(artifact: dict) -> int:
    """Remoções declaradas do artefato — partição completa quando ``remocoes`` existe."""
    # `transacoes_duplicadas_removidas` é SÓ cross-file (O4 do co-design A40.l2):
    # canal novo em `remocoes` não entrava no count_out e o check de COUNT disparava
    # antes de qualquer check de valor. Fallback preserva artefato antigo.
    remocoes = artifact.get("remocoes")
    if isinstance(remocoes, dict) and remocoes:
        return sum(int(r.get("count", 0)) for r in remocoes.values() if isinstance(r, dict))
    return int(artifact.get("transacoes_duplicadas_removidas", 0))


def _declared_dedup_cents(e3_artifacts: list[dict]) -> int:
    """Σ ``valor_cents`` declarado nos canais de remoção (``remocoes``, ADR-347
    §Dec-6). Prova a conservação de VALOR E2→E3 quando fecha contra o valor removido
    (val_in − val_out); antes da serialização por canal, era 0 ⇒ valor não-provável."""
    return sum(
        int(r.get("valor_cents", 0))
        for a in e3_artifacts
        if isinstance(a, dict)
        for r in (a.get("remocoes") or {}).values()
        if isinstance(r, dict)
    )


def _terms(e2_artifacts: list[dict], e3_artifacts: list[dict], exclusoes_run) -> _E2E3Terms:
    """Termos de contagem. O denominador exclui artefatos não-reconciliáveis
    (posição/informe/IRPF): suas tx nunca entram no reconcile (LC-07)."""
    reconcilable = [a for a in e2_artifacts if not _skips_reconcile(a)]
    count_in = sum(len(a.get("transacoes") or []) for a in reconcilable)
    survivors = sum(a.get("transacoes_total", 0) for a in e3_artifacts)
    dups = sum(declared_removed_count(a) for a in e3_artifacts)
    semeado = sum(len(a.get("transacoes") or []) for a in e2_artifacts)
    return _E2E3Terms(count_in, survivors + dups, dups, semeado, exclusoes_run)


def e2_to_e3(
    e2_artifacts: list[dict], e3_artifacts: list[dict], *, exclusoes_run: int | None = None
) -> ConservationResult:
    """Conservação E2→E3 (workspace-wide), ancorada no resíduo dos TRÊS produtores.
    ``exclusoes_run`` é o terceiro termo — statements excluídos inteiros no load, cujo
    count ``e3_load_report.StatementExclusion`` declara pertencer ao ledger run-level
    (não há artefato E3 para eles). ``None`` ⇒ resíduo não computável, nunca "deu zero"."""
    reconcilable = [a for a in e2_artifacts if not _skips_reconcile(a)]
    e2_tx = [t for a in reconcilable for t in a.get("transacoes", [])]
    e3_tx = [t for a in e3_artifacts for t in a.get("transacoes", [])]
    return _e2e3_verdict(
        _terms(e2_artifacts, e3_artifacts, exclusoes_run),
        _sum_cents(e2_tx),
        _sum_cents(e3_tx),
        _declared_dedup_cents(e3_artifacts),
    )


@dataclass(frozen=True)
class _E2E3Terms:
    """Os termos de contagem da identidade E2→E3, com os três produtores separados."""

    count_in: int  # artefatos E2 (reconciliáveis)
    count_out: int  # artefatos E3: sobreviventes + remoções declaradas
    dups: int
    semeado: int  # artefatos E2, ANTES do filtro de reconciliabilidade
    exclusoes_run: int | None  # log de execução do E3 (statements excluídos no load)

    @property
    def residuo(self) -> int | None:
        if self.exclusoes_run is None:
            return None
        return self.count_in - self.count_out - self.exclusoes_run


def _e2e3_result(t: _E2E3Terms, val_in, val_out, veredito) -> ConservationResult:
    v, d = veredito
    return ConservationResult(
        "E2->E3",
        t.count_in,
        t.count_out,
        val_in,
        val_out,
        t.dups,
        v,
        d,
        semeado=t.semeado,
        exclusoes_run=t.exclusoes_run,
        residuo=t.residuo,
    )


def _e2e3_verdict(t: _E2E3Terms, val_in: int, val_out: int, declared: int) -> ConservationResult:
    """Veredito E2→E3 fail-closed, ancorado no RESÍDUO computado — a versão anterior
    adjetivava o gap ("sub-declaração") sem computá-lo e sem o termo de exclusões
    run-level, o que invertia o sinal quando as exclusões EXCEDIAM o gap (item 8)."""
    value_ok = t.dups > 0 and (val_in - val_out) == declared
    checks = _e2e3_checks(t, val_in, val_out, declared, value_ok)
    default = (
        CONSERVADO,
        f"resíduo 0 ({_ident(t)})" + ("; dedup declarado fecha" if t.dups else ""),
    )
    return _e2e3_result(t, val_in, val_out, next(((v, d) for c, v, d in checks if c), default))


def _ident(t: _E2E3Terms) -> str:
    """A identidade impressa por extenso — o gap deixa de ser adjetivo e vira conta."""
    return f"in {t.count_in} − out {t.count_out} − {t.exclusoes_run} excl. run-level"


def _e2e3_checks(t: _E2E3Terms, val_in, val_out, declared, value_ok) -> list:
    """Checks do veredito E2→E3, na ORDEM que importa (count antes de valor)."""
    r = t.residuo
    if r is None:
        # Guard ANTES da lista: ela é construída avidamente, e formatar `-r` com `r`
        # ausente estoura. "Não computável" precede todo veredito de contagem.
        return [
            (
                True,
                COBERTO_SEM_VALOR,
                f"resíduo não computável: exclusões run-level não informadas "
                f"(in {t.count_in}, out {t.count_out}) — não é 'e deu zero'",
            )
        ]
    return _checks_de_contagem(t, r) + _checks_de_valor(t, val_in, val_out, declared, value_ok)


# LC-07 (#1063) decidiu a severidade de `r > 0 com dups`: sub-declaração, não perda
# provada — a row foi colapsada e mal-contada, não sumiu. O item 8 da A42.l3 mudou só a
# GLOSA (o resíduo vem computado); re-escalar seria reinscrever critério já refutado.
def _checks_de_contagem(t: _E2E3Terms, r: int) -> list:
    """Vereditos pelo SINAL do resíduo."""
    return [
        (
            r < 0,
            PERDA_SILENCIOSA,
            f"SOBRE-declaração de {-r}: as exclusões declaradas EXCEDEM o gap "
            f"({_ident(t)}) — mesma row declarada em >1 canal, ou canal contado 2x",
        ),
        (
            r > 0 and t.dups == 0,
            PERDA_SILENCIOSA,
            f"resíduo {r} sem dedup declarado: rows entraram no reconcile e não estão "
            f"em artefato nem em canal ({_ident(t)})",
        ),
        (
            r > 0,
            COBERTO_SEM_VALOR,
            f"sub-declaração de dedup: resíduo {r} com dups={t.dups} ({_ident(t)})",
        ),
    ]


def _checks_de_valor(t: _E2E3Terms, val_in, val_out, declared, value_ok) -> list:
    return [
        (
            t.dups > 0 and not value_ok,
            COBERTO_SEM_VALOR,
            f"dups>0; valor removido {val_in - val_out} != declarado {declared}",
        ),
        (
            val_out != val_in and t.dups == 0,
            PERDA_SILENCIOSA,
            "Σ valor diverge sem dedup (dups=0)",
        ),
    ]
