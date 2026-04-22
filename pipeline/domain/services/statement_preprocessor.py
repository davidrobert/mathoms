"""Pre-processadores de extratos E2 (Fase 6 foundation · Sessão A1).

Extrai duas responsabilidades de ``scripts/e3_reconcile.py::load_and_group_e2_extracts``
(linhas 655-795) em domain services puros, testáveis sem I/O:

- ``StatementPeriodNormalizer``: garante que o campo ``periodo`` seja um dict
  ``{inicio, fim}``. Cobre três casos:
    1. ``periodo`` já é ``{inicio, fim}`` → nada a fazer.
    2. ``periodo`` é string (``YYYYMM`` ou ``YYYY-MM-DD``) → expande para dict.
    3. Fatura sem ``periodo`` → sintetiza com chain de fallbacks
       (``data_vencimento`` → tx dates) e ajusta ``inicio`` para o min de
       ``transacoes[].data`` se anterior ao sintetizado.

- ``AnachronicTransactionDropper``: remove transações com ``data >`` N dias
  antes de ``periodo.inicio`` (default 180). Equivalente ao guard #4 do legado
  (e3_reconcile.py:772-795) que descarta registros pré-período (tipicamente
  posições de investimento mal-classificadas como extratos).

Ambos operam sobre o **dict** legado E2 (não ``BankStatement``) porque a
sintese de período é pré-requisito para ``BankStatement.from_e2_dict``
(que exige ``periodo_inicio``/``periodo_fim`` ou ``periodo``). O caller faz a
conversão depois de normalizar.

Warnings retornados são dataclasses frozen estruturadas — nunca strings.
Serialização para o formato legado (``log_progress(...)``) fica no shell.
"""

from __future__ import annotations

import copy
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

# =============================================================================
# Reasons (enum-like — mantém warnings type-safe)
# =============================================================================


class PeriodDerivationReason:
    """Motivos pelos quais um periodo foi sintetizado/normalizado."""

    PERIODO_STRING_YYYYMM = "periodo_string_yyyymm"
    PERIODO_STRING_DATE = "periodo_string_date"
    PERIODO_STRING_INVALID = "periodo_string_invalid"
    PERIODO_UNEXPECTED_TYPE = "periodo_unexpected_type"
    FATURA_DERIVED_FROM_DATA_VENCIMENTO = "fatura_derived_from_data_vencimento"
    FATURA_INICIO_ADJUSTED_TO_TX = "fatura_inicio_adjusted_to_tx"
    FATURA_DERIVED_FROM_TX_DATES = "fatura_derived_from_tx_dates"
    FATURA_NO_PERIODO_NO_DATA_VENCIMENTO_NO_TXNS = "fatura_no_periodo_no_data_vencimento_no_txns"


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class AnachronicGuardConfig:
    """Janela máxima entre ``periodo.inicio`` e ``transacoes[].data`` antes que
    a transação seja considerada anachronic e descartada.

    Default 180 dias (6 meses), idêntico ao legado.
    """

    max_days_before_periodo_inicio: int = 180


# =============================================================================
# Warnings estruturados
# =============================================================================


@dataclass(frozen=True)
class PeriodDerivationWarning:
    """Notifica que o ``periodo`` precisou ser sintetizado/normalizado."""

    source: str | None
    reason: str
    derived_inicio: str | None = None
    derived_fim: str | None = None
    raw_value: str | None = None  # forma original (string original do periodo, etc)

    def format(self) -> str:
        parts = [f"period derivation [{self.reason}]"]
        if self.source:
            parts.append(f"src={self.source}")
        if self.derived_inicio or self.derived_fim:
            parts.append(f"derived={self.derived_inicio or '?'}..{self.derived_fim or '?'}")
        if self.raw_value:
            parts.append(f"raw={self.raw_value!r}")
        return " ".join(parts)


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


# =============================================================================
# Result containers
# =============================================================================


@dataclass(frozen=True)
class NormalizationResult:
    """Saída de ``StatementPeriodNormalizer.normalize``.

    - ``data``: cópia (deep) do dict de entrada com ``periodo`` normalizado e,
      em faturas, ``saldo_inicial``/``saldo_final`` derivados se ausentes.
    - ``skip``: ``True`` quando não foi possível derivar período (caller deve
      pular o extrato — equivale aos ``log_progress("E3.1", "Skipping ...")``
      do legado).
    - ``warnings``: lista estruturada (pode ser vazia).
    """

    data: dict[str, Any]
    skip: bool
    warnings: tuple[PeriodDerivationWarning, ...]


@dataclass(frozen=True)
class AnachronicFilterResult:
    """Saída de ``AnachronicTransactionDropper.filter``.

    - ``data``: cópia do dict com ``transacoes`` filtradas.
    - ``warning``: ``None`` se nada foi descartado.
    """

    data: dict[str, Any]
    warning: AnachronicTransactionWarning | None


# =============================================================================
# StatementPeriodNormalizer
# =============================================================================


# Conjunto de tipos de fatura aceitos para sintetizar período (mantém paridade
# com ``e3_reconcile.should_skip_extract`` — outras "fatura*" são skip antes
# de chegar ao normalizer).
_DEFAULT_FATURA_PREFIX = "fatura"


class StatementPeriodNormalizer:
    """Garante ``data['periodo']`` como dict ``{inicio, fim}``.

    Service stateless — todos os métodos são determinísticos sobre o dict de
    entrada. Não muta o input (faz ``deepcopy``).

    Uso típico:

        normalizer = StatementPeriodNormalizer()
        result = normalizer.normalize(raw_e2_dict, source_name="fatura.json")
        if result.skip:
            continue  # caller pula este extrato
        data = result.data  # já com periodo dict
        for w in result.warnings:
            logger.info(w.format())
    """

    def normalize(
        self,
        data: dict[str, Any],
        source_name: str | None = None,
    ) -> NormalizationResult:
        out = copy.deepcopy(data)
        warnings: list[PeriodDerivationWarning] = []

        # Caso 0: schema oficial usa ``periodo_inicio``/``periodo_fim`` (campos
        # planos do JSON Schema E2). Quando ambos estão presentes, o dict já
        # está pronto para ``BankStatement.from_e2_dict`` — nada a fazer.
        if out.get("periodo_inicio") and out.get("periodo_fim"):
            return NormalizationResult(out, skip=False, warnings=())

        periodo = out.get("periodo")

        # Caso 1: periodo já é dict → propaga para campos planos se ausentes.
        if isinstance(periodo, dict):
            self._propagate_to_flat_fields(out, periodo)
            return NormalizationResult(out, skip=False, warnings=())

        # Caso 2: periodo é string → expande.
        if isinstance(periodo, str):
            warning, expanded = self._expand_periodo_string(periodo, source_name)
            if warning is not None:
                warnings.append(warning)
            out["periodo"] = expanded
            self._propagate_to_flat_fields(out, expanded)
            return NormalizationResult(out, skip=False, warnings=tuple(warnings))

        # Caso 3: periodo ausente.
        # Para extratos não-fatura, o legado pula (caller decide). Replicamos:
        # apenas faturas sintetizam.
        tipo = (out.get("tipo") or "").strip()
        if not tipo.startswith(_DEFAULT_FATURA_PREFIX):
            # Sem periodo e não é fatura → skip (caller logará).
            return NormalizationResult(out, skip=True, warnings=())

        # Tenta sintetizar a partir de data_vencimento + tx dates.
        synth_warnings, synth_periodo, synth_skip = self._synthesize_fatura_periodo(
            out, source_name
        )
        warnings.extend(synth_warnings)

        if synth_skip:
            return NormalizationResult(out, skip=True, warnings=tuple(warnings))

        out["periodo"] = synth_periodo
        self._propagate_to_flat_fields(out, synth_periodo)

        # Se sintetizou de data_vencimento, propaga saldos como o legado faz.
        if "saldo_inicial" not in out:
            out["saldo_inicial"] = out.get("saldo_anterior") or 0
        if "saldo_final" not in out:
            out["saldo_final"] = out.get("saldo_atual") or 0

        return NormalizationResult(out, skip=False, warnings=tuple(warnings))

    @staticmethod
    def _propagate_to_flat_fields(out: dict[str, Any], periodo: dict[str, str]) -> None:
        """Garante que ``periodo_inicio``/``periodo_fim`` existam como campos
        planos — formato esperado por ``BankStatement.from_e2_dict``. Não
        sobrescreve valores já presentes.
        """
        if "periodo_inicio" not in out and periodo.get("inicio"):
            out["periodo_inicio"] = periodo["inicio"]
        if "periodo_fim" not in out and periodo.get("fim"):
            out["periodo_fim"] = periodo["fim"]

    # -- helpers --

    def _expand_periodo_string(
        self, raw: str, source: str | None
    ) -> tuple[PeriodDerivationWarning | None, dict[str, str]]:
        s = raw.strip()
        if len(s) == 6 and s.isdigit():
            y, m = int(s[:4]), int(s[4:6])
            if 1 <= m <= 12:
                last = monthrange(y, m)[1]
                expanded = {
                    "inicio": f"{y}-{m:02d}-01",
                    "fim": f"{y}-{m:02d}-{last:02d}",
                }
                return (
                    PeriodDerivationWarning(
                        source=source,
                        reason=PeriodDerivationReason.PERIODO_STRING_YYYYMM,
                        derived_inicio=expanded["inicio"],
                        derived_fim=expanded["fim"],
                        raw_value=raw,
                    ),
                    expanded,
                )

        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            d = s[:10]
            expanded = {"inicio": d, "fim": d}
            return (
                PeriodDerivationWarning(
                    source=source,
                    reason=PeriodDerivationReason.PERIODO_STRING_DATE,
                    derived_inicio=d,
                    derived_fim=d,
                    raw_value=raw,
                ),
                expanded,
            )

        empty = {"inicio": "", "fim": ""}
        return (
            PeriodDerivationWarning(
                source=source,
                reason=PeriodDerivationReason.PERIODO_STRING_INVALID,
                derived_inicio="",
                derived_fim="",
                raw_value=raw,
            ),
            empty,
        )

    def _synthesize_fatura_periodo(
        self,
        data: dict[str, Any],
        source: str | None,
    ) -> tuple[list[PeriodDerivationWarning], dict[str, str], bool]:
        """Aplica a chain de fallbacks de ``e3_reconcile.py::665-770``.

        Returns: (warnings, periodo_sintetizado, skip). Se ``skip``, ``periodo``
        é vazio e o caller deve pular o extrato.
        """
        warnings: list[PeriodDerivationWarning] = []
        venc_raw = (data.get("data_vencimento") or "").strip()
        txns = data.get("transacoes") or []
        tx_dates = sorted((str(t.get("data") or "")[:10] for t in txns if t.get("data")))

        # Caso 3a: sem data_vencimento.
        if not venc_raw:
            if not tx_dates:
                warnings.append(
                    PeriodDerivationWarning(
                        source=source,
                        reason=PeriodDerivationReason.FATURA_NO_PERIODO_NO_DATA_VENCIMENTO_NO_TXNS,
                    )
                )
                return warnings, {"inicio": "", "fim": ""}, True
            # Deriva de min/max das tx.
            periodo = {"inicio": tx_dates[0], "fim": tx_dates[-1]}
            warnings.append(
                PeriodDerivationWarning(
                    source=source,
                    reason=PeriodDerivationReason.FATURA_DERIVED_FROM_TX_DATES,
                    derived_inicio=periodo["inicio"],
                    derived_fim=periodo["fim"],
                )
            )
            return warnings, periodo, False

        # Caso 3b: tem data_vencimento — tenta parsear.
        try:
            dt_venc = datetime.strptime(venc_raw, "%Y-%m-%d")
        except ValueError:
            # Fallback final: tx dates se houver.
            if tx_dates:
                periodo = {"inicio": tx_dates[0], "fim": tx_dates[-1]}
                warnings.append(
                    PeriodDerivationWarning(
                        source=source,
                        reason=PeriodDerivationReason.FATURA_DERIVED_FROM_TX_DATES,
                        derived_inicio=periodo["inicio"],
                        derived_fim=periodo["fim"],
                        raw_value=venc_raw,
                    )
                )
                return warnings, periodo, False
            # Sem tx e venc inválido → skip.
            warnings.append(
                PeriodDerivationWarning(
                    source=source,
                    reason=PeriodDerivationReason.FATURA_NO_PERIODO_NO_DATA_VENCIMENTO_NO_TXNS,
                    raw_value=venc_raw,
                )
            )
            return warnings, {"inicio": "", "fim": ""}, True

        # Sintetiza de venc-30d até venc.
        dt_start = dt_venc - timedelta(days=30)
        synth_inicio = dt_start.strftime("%Y-%m-%d")
        synth_fim = venc_raw
        warnings.append(
            PeriodDerivationWarning(
                source=source,
                reason=PeriodDerivationReason.FATURA_DERIVED_FROM_DATA_VENCIMENTO,
                derived_inicio=synth_inicio,
                derived_fim=synth_fim,
                raw_value=venc_raw,
            )
        )

        # Ajusta inicio para min(tx_dates) se anterior — legado fix #4.
        if tx_dates and tx_dates[0] < synth_inicio:
            warnings.append(
                PeriodDerivationWarning(
                    source=source,
                    reason=PeriodDerivationReason.FATURA_INICIO_ADJUSTED_TO_TX,
                    derived_inicio=tx_dates[0],
                    derived_fim=synth_fim,
                    raw_value=synth_inicio,
                )
            )
            synth_inicio = tx_dates[0]

        return warnings, {"inicio": synth_inicio, "fim": synth_fim}, False


# =============================================================================
# AnachronicTransactionDropper
# =============================================================================


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

        kept: list[dict[str, Any]] = []
        dropped: list[str] = []
        for tx in txns:
            tx_date = str(tx.get("data") or "")[:10]
            if tx_date and tx_date < cutoff_str:
                dropped.append(tx_date)
            else:
                kept.append(tx)

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
