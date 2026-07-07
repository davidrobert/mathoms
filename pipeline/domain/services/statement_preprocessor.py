"""Pre-processadores de extratos E2 (Fase 6 foundation · Sessão A1).

Extrai duas responsabilidades de ``scripts/reconcile_transactions.py::load_and_group_e2_extracts``
(linhas 655-795) em domain services puros, testáveis sem I/O:

- ``StatementPeriodNormalizer``: garante que o campo ``periodo`` seja um dict
  ``{inicio, fim}``. Cobre três casos:
    1. ``periodo`` já é ``{inicio, fim}`` → nada a fazer.
    2. ``periodo`` é string (``YYYYMM`` ou ``YYYY-MM-DD``) → expande para dict.
    3. Fatura sem ``periodo`` → sintetiza com chain de fallbacks
       (``data_vencimento`` → tx dates) e ajusta ``inicio`` para o min de
       ``transacoes[].data`` se anterior ao sintetizado.

- ``AnachronicTransactionDropper`` (guard #4 do legado) vive em
  ``pipeline/domain/services/anachronic_guard.py`` desde A28.l8 (P2 ≤500).

O normalizer opera sobre o **dict** legado E2 (não ``BankStatement``) porque a
sintese de período é pré-requisito para ``BankStatement.from_e2_dict``
(que exige ``periodo_inicio``/``periodo_fim`` ou ``periodo``). O caller faz a
conversão depois de normalizar.

Warnings retornados são dataclasses frozen estruturadas — nunca strings.
Serialização para o formato legado (``log_progress(...)``) fica no shell.
"""

from __future__ import annotations

import copy
from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode

# Re-export de back-compat — consumidores históricos importam o guard daqui.
from pipeline.domain.services.anachronic_guard import (
    AnachronicFilterResult as AnachronicFilterResult,
)
from pipeline.domain.services.anachronic_guard import (
    AnachronicGuardConfig as AnachronicGuardConfig,
)
from pipeline.domain.services.anachronic_guard import (
    AnachronicTransactionDropper as AnachronicTransactionDropper,
)
from pipeline.domain.services.anachronic_guard import (
    AnachronicTransactionWarning as AnachronicTransactionWarning,
)

# =============================================================================
# Reasons (enum-like — mantém warnings type-safe)
# =============================================================================


class PeriodDerivationReason:
    """Motivos pelos quais um periodo foi sintetizado/normalizado."""

    PERIODO_STRING_YYYYMM = "periodo_string_yyyymm"
    PERIODO_STRING_DATE = "periodo_string_date"
    PERIODO_STRING_INVALID = "periodo_string_invalid"
    PERIODO_UNEXPECTED_TYPE = "periodo_unexpected_type"
    PERIODO_YEAR_IMPLAUSIBLE = "periodo_year_implausible"
    FATURA_DERIVED_FROM_DATA_VENCIMENTO = "fatura_derived_from_data_vencimento"
    FATURA_INICIO_ADJUSTED_TO_TX = "fatura_inicio_adjusted_to_tx"
    FATURA_DERIVED_FROM_TX_DATES = "fatura_derived_from_tx_dates"
    FATURA_NO_PERIODO_NO_DATA_VENCIMENTO_NO_TXNS = "fatura_no_periodo_no_data_vencimento_no_txns"


# =============================================================================
# Plausibilidade de período (A28.l8)
# =============================================================================

# Sentinel oficial de "período desconhecido" — propaga E0→E2→E3 e é tratado
# downstream; nunca deve ser confundido com ano-fantasma (1899/2100 vindos de
# clamp de ``safe_date`` ou string bruta de parser).
PERIOD_SENTINEL = "999999"
PLAUSIBLE_YEAR_MIN = 2015
PLAUSIBLE_YEAR_MAX = 2035


def _year_implausible(value: str | None) -> bool:
    """True se os 4 primeiros dígitos formam ano fora de [2015, 2035]."""
    if not value:
        return False
    head = str(value).strip()[:4]
    if len(head) < 4 or not head.isdigit():
        return False
    return not (PLAUSIBLE_YEAR_MIN <= int(head) <= PLAUSIBLE_YEAR_MAX)


def _implausible_periodo_value(*values: str | None) -> str | None:
    """Primeiro valor de período com ano-fantasma; sentinel oficial é passthrough."""
    for v in values:
        if v and str(v).strip().startswith(PERIOD_SENTINEL):
            continue
        if _year_implausible(v):
            return str(v)
    return None


def _implausible_warning(offending: str, source: str | None) -> "PeriodDerivationWarning":
    return _string_warning(
        PeriodDerivationReason.PERIODO_YEAR_IMPLAUSIBLE, offending, "", "", source
    )


def _string_warning(
    reason: str, raw: str, inicio: str, fim: str, source: str | None
) -> "PeriodDerivationWarning":
    return PeriodDerivationWarning(
        source=source, reason=reason, derived_inicio=inicio, derived_fim=fim, raw_value=raw
    )


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

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason | None:
        """Projeta (ADR-272) para ReviewReason; só período implausível vira reason."""
        if self.reason != PeriodDerivationReason.PERIODO_YEAR_IMPLAUSIBLE:
            return None
        return ReviewReason(
            code=ReviewReasonCode.dedup_sentinel_period,
            stage=stage,
            artifact_key=artifact_key,
            document_id=document_id,
            offending_value=self.raw_value or f"{self.derived_inicio}..{self.derived_fim}",
            expected=(
                f"ano de periodo em [{PLAUSIBLE_YEAR_MIN}, {PLAUSIBLE_YEAR_MAX}] "
                f"ou sentinel {PERIOD_SENTINEL}"
            ),
            message="periodo implausivel na normalizacao E3; documento requer revisao",
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


# =============================================================================
# StatementPeriodNormalizer
# =============================================================================


# Conjunto de tipos de fatura aceitos para sintetizar período (mantém paridade
# com ``reconcile_transactions.should_skip_extract`` — outras "fatura*" são skip antes
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
            offending = _implausible_periodo_value(out["periodo_inicio"], out["periodo_fim"])
            if offending is not None:
                return self._implausible_result(out, offending, source_name, warnings)
            return NormalizationResult(out, skip=False, warnings=())

        periodo = out.get("periodo")

        # Caso 1: periodo já é dict → propaga para campos planos se ausentes.
        if isinstance(periodo, dict):
            offending = _implausible_periodo_value(periodo.get("inicio"), periodo.get("fim"))
            if offending is not None:
                return self._implausible_result(out, offending, source_name, warnings)
            self._propagate_to_flat_fields(out, periodo)
            return NormalizationResult(out, skip=False, warnings=())

        # Caso 2: periodo é string → expande.
        if isinstance(periodo, str):
            warning, expanded = self._expand_periodo_string(periodo, source_name)
            if warning is not None:
                warnings.append(warning)
            implausible = (
                warning is not None
                and warning.reason == PeriodDerivationReason.PERIODO_YEAR_IMPLAUSIBLE
            )
            if implausible:
                return NormalizationResult(out, skip=True, warnings=tuple(warnings))
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

        # Guardrail A28.l8: síntese herda datas clampadas por ``safe_date``
        # (ex.: c6bank faturacarbon → 2100-xx via FATURA_DERIVED_FROM_TX_DATES).
        offending = _implausible_periodo_value(
            synth_periodo.get("inicio"), synth_periodo.get("fim")
        )
        if offending is not None:
            return self._implausible_result(out, offending, source_name, warnings)

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

    def _implausible_result(
        self,
        out: dict[str, Any],
        offending: str,
        source: str | None,
        warnings: list[PeriodDerivationWarning],
    ) -> NormalizationResult:
        """Período com ano-fantasma nunca vira artefato silencioso (A28.l8)."""
        warnings.append(_implausible_warning(offending, source))
        return NormalizationResult(out, skip=True, warnings=tuple(warnings))

    def _expand_periodo_string(
        self, raw: str, source: str | None
    ) -> tuple[PeriodDerivationWarning | None, dict[str, str]]:
        s = raw.strip()
        if len(s) == 6 and s.isdigit():
            yyyymm = self._expand_yyyymm(raw, s, source)
            if yyyymm is not None:
                return yyyymm

        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return self._expand_iso_date(raw, s, source)

        invalid = _string_warning(
            PeriodDerivationReason.PERIODO_STRING_INVALID, raw, "", "", source
        )
        return invalid, {"inicio": "", "fim": ""}

    @staticmethod
    def _expand_yyyymm(
        raw: str, s: str, source: str | None
    ) -> tuple[PeriodDerivationWarning, dict[str, str]] | None:
        """Expande YYYYMM; None se mês inválido (sentinel 999999 cai em INVALID)."""
        y, m = int(s[:4]), int(s[4:6])
        if not (1 <= m <= 12):
            return None
        if not (PLAUSIBLE_YEAR_MIN <= y <= PLAUSIBLE_YEAR_MAX):
            return _implausible_warning(raw, source), {"inicio": "", "fim": ""}
        last = monthrange(y, m)[1]
        expanded = {"inicio": f"{y}-{m:02d}-01", "fim": f"{y}-{m:02d}-{last:02d}"}
        reason = PeriodDerivationReason.PERIODO_STRING_YYYYMM
        return _string_warning(reason, raw, expanded["inicio"], expanded["fim"], source), expanded

    @staticmethod
    def _expand_iso_date(
        raw: str, s: str, source: str | None
    ) -> tuple[PeriodDerivationWarning, dict[str, str]]:
        d = s[:10]
        if _year_implausible(d):
            return _implausible_warning(raw, source), {"inicio": "", "fim": ""}
        warning = _string_warning(PeriodDerivationReason.PERIODO_STRING_DATE, raw, d, d, source)
        return warning, {"inicio": d, "fim": d}

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
