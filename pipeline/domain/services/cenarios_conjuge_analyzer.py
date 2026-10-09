"""CenariosConjugeAnalyzer — cenário de estresse "Sem renda do cônjuge" (ADR-167)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from pipeline.domain.services.if_projector import default_if_absent, solve_prazo_anos
from pipeline.domain.services.methodology_constants import (
    APORTE_REDUZIDO_FATOR_CONJUGE,
)
from pipeline.domain.services.narrativas.format_helpers import fmt_currency

_TODAY_FALLBACK = date(2026, 4, 19)

# Default float exposto por ergonomia (dataclass field exige imutável simples).
# Decimal canônico vive em ``methodology_constants`` (ADR-177).
_APORTE_REDUZIDO_FATOR_DEFAULT: float = float(APORTE_REDUZIDO_FATOR_CONJUGE)


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return 0.0


def _calculate_age(dob: date, reference_date: date) -> int:
    age = reference_date.year - dob.year
    if (reference_date.month, reference_date.day) < (dob.month, dob.day):
        age -= 1
    return age


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class CenariosConjugeConfig:
    """Parâmetros do cenário de estresse, tipados (R9/ISP).

    Sources:
    - ``retorno_real_anual_pct`` ← ``goals.json::independencia_financeira.retorno_real_anual_pct``
    - ``aporte_base`` ← ``goals.json::aportes.meta_aporte_mensal``
    - ``fator_reduzido`` ← rules-as-code (``APORTE_REDUZIDO_FATOR_CONJUGE``,
      ADR-177); override por argumento aceito para testes.
    - ``titular_dob``/``titular_key``/``conjuge_key``/``conjuge_nome`` — family config
    """

    titular_dob: date
    retorno_real_anual_pct: float = 6.0
    aporte_base: float = 0.0
    fator_reduzido: float = _APORTE_REDUZIDO_FATOR_DEFAULT
    titular_key: str = "titular"
    conjuge_key: str = "conjuge"
    conjuge_nome: str = "Cônjuge"
    reference_date: date = _TODAY_FALLBACK

    @classmethod
    def from_configs(
        cls,
        *,
        goals: dict | None = None,
        titular_dob: date,
        titular_key: str = "titular",
        conjuge_key: str = "conjuge",
        conjuge_nome: str = "Cônjuge",
        reference_date: date | None = None,
    ) -> "CenariosConjugeConfig":
        """Constrói config (ADR-167; pós-A8.4 PR2 sem dependência de USD/cambio)."""
        g = goals or {}
        if_cfg = g.get("independencia_financeira", {}) or {}
        aportes = g.get("aportes", {}) or {}

        return cls(
            titular_dob=titular_dob,
            retorno_real_anual_pct=default_if_absent(if_cfg.get("retorno_real_anual_pct"), 6.0),
            aporte_base=_safe_float(aportes.get("meta_aporte_mensal", 0)),
            fator_reduzido=_APORTE_REDUZIDO_FATOR_DEFAULT,
            titular_key=titular_key,
            conjuge_key=conjuge_key,
            conjuge_nome=conjuge_nome,
            reference_date=reference_date or _TODAY_FALLBACK,
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class CenarioItem:
    nome: str
    aporte_mensal: float
    # `None` = prazo não projetável com as premissas do cenário. Era a sentinela
    # 999, que propagava para ano_if=3025 e idade_titular=1040 (mesmo defeito de
    # IFProjector._solve_prazo).
    prazo_if_anos: float | None
    ano_if: int | None
    idade_titular: int | None
    resumo: str

    def to_dict(self) -> dict:
        return {
            "nome": self.nome,
            "aporte_mensal": round(self.aporte_mensal, 2),
            "prazo_if_anos": self.prazo_if_anos,
            "ano_if": self.ano_if,
            "idade_titular": self.idade_titular,  # ADR-338: role-keyed
            "resumo": self.resumo,
        }


@dataclass(frozen=True)
class CenariosConjugeResult:
    cenarios: tuple[CenarioItem, ...]
    premissas: dict[str, Any]
    titular_key: str = "david"

    def to_legacy_dict(self) -> dict:
        labels = [c.nome for c in self.cenarios]
        return {
            "labels": labels,
            "aportes": [round(c.aporte_mensal, 2) for c in self.cenarios],
            "prazos_if": [c.prazo_if_anos for c in self.cenarios],
            "anos_if": [c.ano_if for c in self.cenarios],
            "idade_titular_if": [c.idade_titular for c in self.cenarios],  # ADR-338: role-keyed
            "premissas": dict(self.premissas),
            "cenarios": [c.to_dict() for c in self.cenarios],
        }


# =============================================================================
# Service
# =============================================================================


class CenariosConjugeAnalyzer:
    """Computa o cenário de estresse 'Sem renda do cônjuge' (ADR-167)."""

    _LABEL = "Sem renda do cônjuge"

    def __init__(self, config: CenariosConjugeConfig) -> None:
        self._config = config

    def analyze(
        self,
        *,
        patrimonio: dict[str, Any],
        goals: dict[str, Any],
        fluxo: dict[str, Any],
    ) -> CenariosConjugeResult:
        cfg = self._config

        meta_if = _safe_float((goals or {}).get("if_meta", 0))
        # ADR-142 + ADR-215 §6: cenários conjuge usam `investivel_efetivo`.
        investivel = _safe_float((patrimonio or {}).get("investivel_efetivo", 0))
        r = (1 + cfg.retorno_real_anual_pct / 100.0) ** (1 / 12) - 1

        salario_conjuge_brl = self._extract_salario_conjuge(fluxo)

        aporte = round(cfg.aporte_base * cfg.fator_reduzido, 2)
        prazo_bruto = self._compute_prazo(investivel, meta_if, r, aporte)
        prazo = None if prazo_bruto is None else round(prazo_bruto, 1)
        ano_if: int | None = None
        idade_titular: int | None = None
        if prazo is not None:
            ano_if = cfg.reference_date.year + int(prazo)
            idade_titular = _calculate_age(cfg.titular_dob, cfg.reference_date) + int(prazo)

        cenario = CenarioItem(
            nome=self._LABEL,
            aporte_mensal=aporte,
            prazo_if_anos=prazo,
            ano_if=ano_if,
            idade_titular=idade_titular,
            resumo=self._resumo(aporte, prazo, ano_if),
        )

        premissas: dict[str, Any] = {
            "meta_if": meta_if,
            "investivel_atual": investivel,
            "retorno_real_anual_pct": cfg.retorno_real_anual_pct,
            "aporte_base": cfg.aporte_base,
            "fator_reduzido": cfg.fator_reduzido,
            "salario_conjuge_clt_brl": salario_conjuge_brl,  # ADR-338: role-keyed
        }

        return CenariosConjugeResult(
            cenarios=(cenario,),
            premissas=premissas,
            titular_key=cfg.titular_key,
        )

    # -- Helpers --

    def _extract_salario_conjuge(self, fluxo: dict[str, Any]) -> float:
        """Mediana dos valores não-zero do dataset CLT do cônjuge."""
        cfg = self._config
        rmd = (fluxo or {}).get("receita_despesa_mensal_detalhado", {}) or {}
        for ds in rmd.get("receita_datasets", []) or []:
            label = str(ds.get("label", "")).lower()
            if "clt" in label and cfg.conjuge_nome.lower() in label:
                nonzero = [_safe_float(v) for v in ds.get("data", []) if _safe_float(v) > 0]
                if nonzero:
                    s = sorted(nonzero)
                    return s[len(s) // 2]
        return 0.0

    @staticmethod
    def _compute_prazo(investivel: float, meta: float, r: float, aporte: float) -> float | None:
        """``None`` fora do ramo fechado — era a sentinela 999 (ver CenarioItem)."""
        # Delega ao domínio (ADR-373): era uma 2ª cópia da mesma fórmula, e um ramo
        # preenchido só de um lado faria S7 e o Apêndice C discordarem sobre a
        # mesma família.
        return solve_prazo_anos(investivel=investivel, if_meta=meta, r=r, aporte_mensal=aporte)

    def _resumo(self, aporte: float, prazo: float | None, ano_if: int | None) -> str:
        # A37.l14 (PD-11): f"{v:,.0f}" produzia milhar US ("R$ 13,200");
        # fmt_currency é o formatador BR canônico das narrativas.
        cfg = self._config
        head = (
            f"Sem renda do cônjuge, aporte cai para {fmt_currency(aporte)}/mês "
            f"({cfg.fator_reduzido:.0%} do base)."
        )
        if prazo is None:
            return f"{head} Prazo até a IF não projetável com as premissas deste cenário."
        return f"{head} IF em {prazo:.0f} anos ({ano_if})."


# =============================================================================
# Elegibilidade (ADR-167 §Emenda 2026-10-09)
# =============================================================================


class VereditoCenarioConjuge(str, Enum):
    elegivel = "elegivel"
    sem_conjuge_cadastrado = "sem_conjuge_cadastrado"
    sem_meta_if = "sem_meta_if"


# Os critérios de renda da ADR (≥2 rendas, cônjuge ≥15%) ficam de fora até existir
# renda por membro com dono: o label de receita não carrega o membro.
def veredito_cenario_conjuge(*, conjuge_key: str, if_meta: float) -> VereditoCenarioConjuge:
    """Decide se o cenário 'Sem renda do cônjuge' entra no payload E5 (ADR-167)."""
    if not conjuge_key:
        return VereditoCenarioConjuge.sem_conjuge_cadastrado
    if if_meta <= 0:
        return VereditoCenarioConjuge.sem_meta_if
    return VereditoCenarioConjuge.elegivel
