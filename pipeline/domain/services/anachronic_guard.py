"""Guard anachronic de transações E2→E3 (extraído de ``statement_preprocessor``).

``AnachronicTransactionDropper`` remove transações com ``data >`` N dias antes
de ``periodo.inicio`` (default 180). Equivalente ao guard #4 do legado
(e3_reconcile.py:772-795) que descarta registros pré-período (tipicamente
posições de investimento mal-classificadas como extratos).

Warnings retornados são dataclasses frozen estruturadas — nunca strings.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class AnachronicGuardConfig:
    """Janela máxima entre ``periodo.inicio`` e ``transacoes[].data`` antes que
    a transação seja considerada anachronic e descartada.

    Default 180 dias (6 meses), idêntico ao legado.
    """

    max_days_before_periodo_inicio: int = 180


@dataclass(frozen=True)
class AnachronicTransactionWarning:
    """Notifica transações descartadas por estarem >N dias antes do período."""

    source: str | None
    periodo_inicio: str
    cutoff: str
    dropped_count: int
    sample_dates: tuple[str, ...] = field(default_factory=tuple)

    def format(self) -> str:
        sample = ",".join(self.sample_dates[:3])
        return (
            f"anachronic-drop src={self.source or '?'} "
            f"periodo_inicio={self.periodo_inicio} cutoff={self.cutoff} "
            f"dropped={self.dropped_count} sample=[{sample}]"
        )


@dataclass(frozen=True)
class AnachronicFilterResult:
    """Saída de ``AnachronicTransactionDropper.filter``.

    - ``data``: cópia do dict com ``transacoes`` filtradas.
    - ``warning``: ``None`` se nada foi descartado.
    """

    data: dict[str, Any]
    warning: AnachronicTransactionWarning | None


class AnachronicTransactionDropper:
    """Remove transações com ``data <`` ``periodo.inicio - max_days_before``.

    O legado loga e descarta esses registros (e3_reconcile.py:772-795). Aqui
    fazemos o mesmo, mas retornando warning estruturado e sem mutar o input.

    Não opera se ``periodo.inicio`` está vazio/ausente — nesse caso, retorna
    o dict inalterado e nenhum warning.
    """

    def __init__(self, config: AnachronicGuardConfig | None = None) -> None:
        self._config = config or AnachronicGuardConfig()

    def filter(
        self,
        data: dict[str, Any],
        source_name: str | None = None,
    ) -> AnachronicFilterResult:
        out = copy.deepcopy(data)
        # Aceita formato dict (`periodo: {inicio, fim}`) usado pelo legado
        # ``e3_reconcile`` E formato plano (`periodo_inicio`) do schema E2.
        periodo_inicio = (out.get("periodo") or {}).get("inicio") or out.get("periodo_inicio") or ""
        periodo_inicio = str(periodo_inicio)[:10]
        if not periodo_inicio:
            return AnachronicFilterResult(out, warning=None)

        try:
            dt_inicio = datetime.strptime(periodo_inicio, "%Y-%m-%d")
        except ValueError:
            return AnachronicFilterResult(out, warning=None)

        cutoff = dt_inicio - timedelta(days=self._config.max_days_before_periodo_inicio)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        txns = out.get("transacoes") or []
        if not txns:
            return AnachronicFilterResult(out, warning=None)

        kept, dropped = self._partition_by_cutoff(txns, cutoff_str)
        if not dropped:
            return AnachronicFilterResult(out, warning=None)

        out["transacoes"] = kept
        warning = AnachronicTransactionWarning(
            source=source_name,
            periodo_inicio=periodo_inicio,
            cutoff=cutoff_str,
            dropped_count=len(dropped),
            sample_dates=tuple(sorted(set(dropped))[:3]),
        )
        return AnachronicFilterResult(out, warning=warning)

    @staticmethod
    def _partition_by_cutoff(
        txns: list[dict[str, Any]], cutoff_str: str
    ) -> tuple[list[dict[str, Any]], list[str]]:
        kept: list[dict[str, Any]] = []
        dropped: list[str] = []
        for tx in txns:
            tx_date = str(tx.get("data") or "")[:10]
            if tx_date and tx_date < cutoff_str:
                dropped.append(tx_date)
            else:
                kept.append(tx)
        return kept, dropped
