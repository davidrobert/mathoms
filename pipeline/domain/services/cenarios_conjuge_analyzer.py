"""CenariosConjugeAnalyzer — cenário de estresse "Sem renda do cônjuge" (ADR-167)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

_TODAY_FALLBACK = date(2026, 4, 19)


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

    Sources no legado:
    - ``retorno_real_anual_pct`` ← ``goals.json::independencia_financeira.retorno_real_anual_pct``
    - ``aporte_base`` ← ``goals.json::aportes.meta_aporte_mensal``
    - ``fator_reduzido`` ← ``goals.json::simulacao.aporte_reduzido_fator``
    - ``titular_dob``/``titular_key``/``conjuge_key``/``conjuge_nome`` — family config
    """

    titular_dob: date
    retorno_real_anual_pct: float = 6.0
    aporte_base: float = 0.0
    fator_reduzido: float = 0.66
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
        sim = g.get("simulacao", {}) or {}

        return cls(
            titular_dob=titular_dob,
            retorno_real_anual_pct=_safe_float(if_cfg.get("retorno_real_anual_pct", 6.0)),
            aporte_base=_safe_float(aportes.get("meta_aporte_mensal", 0)),
            fator_reduzido=_safe_float(sim.get("aporte_reduzido_fator", 0.66)),
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
    prazo_if_anos: float
    ano_if: int
    idade_titular: int
    resumo: str

    def to_dict(self, titular_key: str = "david") -> dict:
        return {
            "nome": self.nome,
            "aporte_mensal": round(self.aporte_mensal, 2),
            "prazo_if_anos": self.prazo_if_anos,
            "ano_if": self.ano_if,
            f"idade_{titular_key}": self.idade_titular,
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
            f"idade_{self.titular_key}_if": [c.idade_titular for c in self.cenarios],
            "premissas": dict(self.premissas),
            "cenarios": [c.to_dict(self.titular_key) for c in self.cenarios],
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
        investivel = _safe_float((patrimonio or {}).get("investivel", 0))
        r = (1 + cfg.retorno_real_anual_pct / 100.0) ** (1 / 12) - 1

        salario_conjuge_brl = self._extract_salario_conjuge(fluxo)

        aporte = round(cfg.aporte_base * cfg.fator_reduzido, 2)
        prazo = round(self._compute_prazo(investivel, meta_if, r, aporte), 1)
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
            f"salario_{cfg.conjuge_key}_clt_brl": salario_conjuge_brl,
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
    def _compute_prazo(investivel: float, meta: float, r: float, aporte: float) -> float:
        if investivel >= meta:
            return 0.0
        if r > 0 and aporte > 0:
            numerator = meta + aporte / r
            denominator = investivel + aporte / r
            if denominator > 0 and numerator / denominator > 0:
                n_meses = math.log(numerator / denominator) / math.log(1 + r)
                return max(0.0, n_meses / 12)
        # Sentinela legada: 999 (int) preservado para paridade dos goldens.
        return 999

    def _resumo(self, aporte: float, prazo: float, ano_if: int) -> str:
        cfg = self._config
        return (
            f"Sem renda do cônjuge, aporte cai para R$ {aporte:,.0f}/mês "
            f"({cfg.fator_reduzido:.0%} do base). IF em {prazo:.0f} anos ({ano_if})."
        )


# =============================================================================
# Eligibility gate (ADR-167)
# =============================================================================


def should_render_conjuge_scenarios(
    *,
    family_members: Mapping[str, Any],
    fluxo: Mapping[str, Any],
    goals: Mapping[str, Any],
) -> bool:
    """Decide se o cenário 'cônjuge sem trabalhar' é elegível para o workspace (ADR-167).

    Regra Cerbasi/Perini: meta IF presente E ≥2 membros com renda recorrente E
    renda do cônjuge ≥15% da renda familiar total. Solteiro / 1 renda / casal
    sem meta IF / casal 95/5 → False (sem o que stressar / impacto < ruído).
    """
    if _safe_float((goals or {}).get("if_meta", 0)) <= 0:
        return False

    membros = (family_members or {}).get("membros", {}) or {}
    titular_key = (family_members or {}).get("titular", "") or ""
    conjuge_key = next(
        (k for k, v in membros.items() if isinstance(v, dict) and v.get("papel") == "conjuge"),
        "",
    )
    if not titular_key or not conjuge_key:
        return False

    rmd = (fluxo or {}).get("receita_despesa_mensal_detalhado", {}) or {}
    datasets = rmd.get("receita_datasets", []) or []

    def _sum_label(role_name: str) -> float:
        total = 0.0
        for ds in datasets:
            label = str(ds.get("label", "")).lower()
            if role_name and role_name in label:
                total += sum(_safe_float(v) for v in ds.get("data", []) if _safe_float(v) > 0)
        return total

    titular_nome = (membros.get(titular_key, {}) or {}).get("nome_curto", titular_key).lower()
    conjuge_nome = (membros.get(conjuge_key, {}) or {}).get("nome_curto", conjuge_key).lower()

    renda_titular = _sum_label(titular_nome)
    renda_conjuge = _sum_label(conjuge_nome)
    renda_familiar = renda_titular + renda_conjuge

    if renda_titular <= 0 or renda_conjuge <= 0 or renda_familiar <= 0:
        return False

    return (renda_conjuge / renda_familiar) >= 0.15
