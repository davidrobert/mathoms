"""CenariosConjugeAnalyzer — 3 cenários de IF para trajetória do cônjuge
(Sessão A5c · Fase 8).

Extrai ``analyze_cenarios_conjuge`` (e5_analyze.py:2181) em domain service
puro. Computa aporte mensal e prazo IF em 3 cenários:

1. **Sem Trabalhar** — cônjuge sem renda; aporte reduzido por ``fator_reduzido``.
2. **Com NCLEX** — cônjuge trabalha como RN com ``renda_rn_minima_usd``.
3. **Com NCLEX + Green Card** — ``renda_rn_maxima_usd``.

Modelo de aporte: recupera a fração do aporte habilitada pelo cônjuge
proporcional à renda nova, e adiciona 50% do surplus acima do salário CLT
(cap em 50% do aporte base).

Função pura; todos os parâmetros via :class:`CenariosConjugeConfig` (R9/ISP).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any


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
    """Todos os parâmetros dos 3 cenários, tipados (R9/ISP).

    Sources no legado:
    - ``retorno_real_anual_pct`` ← ``goals.json::independencia_financeira.retorno_real_anual_pct``
    - ``aporte_base`` ← ``goals.json::aportes.meta_aporte_mensal``
    - ``fator_reduzido`` ← ``goals.json::simulacao.aporte_reduzido_fator``
    - ``cambio_usd_brl`` ← ``taxas.json::cambio_usd_brl``
    - ``renda_rn_minima_usd`` / ``renda_rn_maxima_usd`` ← ``goals.json::cenarios_conjuge``
      (fallback: ``mariana_eua`` para compat)
    - ``titular_dob``/``titular_key``/``conjuge_key``/``conjuge_nome`` — family config
    """

    titular_dob: date
    retorno_real_anual_pct: float = 6.0
    aporte_base: float = 0.0
    fator_reduzido: float = 0.66
    cambio_usd_brl: float = 5.80
    renda_rn_minima_usd: float = 4000.0
    renda_rn_maxima_usd: float = 7000.0
    titular_key: str = "david"
    conjuge_key: str = "mariana"
    conjuge_nome: str = "Mariana"
    reference_date: date = _TODAY_FALLBACK
    surplus_share_pct: float = 50.0
    surplus_cap_pct: float = 50.0  # cap em % do aporte_base

    @classmethod
    def from_configs(
        cls,
        *,
        goals: dict | None = None,
        taxas: dict | None = None,
        titular_dob: date,
        titular_key: str = "david",
        conjuge_key: str = "mariana",
        conjuge_nome: str = "Mariana",
        reference_date: date | None = None,
    ) -> "CenariosConjugeConfig":
        g = goals or {}
        if_cfg = g.get("independencia_financeira", {}) or {}
        aportes = g.get("aportes", {}) or {}
        sim = g.get("simulacao", {}) or {}
        mar = g.get("cenarios_conjuge") or g.get("mariana_eua", {}) or {}
        taxas_d = taxas or {}

        return cls(
            titular_dob=titular_dob,
            retorno_real_anual_pct=_safe_float(
                if_cfg.get("retorno_real_anual_pct", 6.0)
            ),
            aporte_base=_safe_float(aportes.get("meta_aporte_mensal", 0)),
            fator_reduzido=_safe_float(sim.get("aporte_reduzido_fator", 0.66)),
            cambio_usd_brl=_safe_float(taxas_d.get("cambio_usd_brl", 5.80)),
            renda_rn_minima_usd=_safe_float(mar.get("renda_rn_minima_usd", 4000)),
            renda_rn_maxima_usd=_safe_float(mar.get("renda_rn_maxima_usd", 7000)),
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
    """Computa 3 cenários de trajetória IF para o cônjuge."""

    _LABELS = ("Sem Trabalhar", "Com NCLEX", "Com NCLEX + Green Card")

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

        # Cenário 1 — Sem trabalhar.
        aporte_s1 = round(cfg.aporte_base * cfg.fator_reduzido, 2)
        prazo_s1 = round(self._compute_prazo(investivel, meta_if, r, aporte_s1), 1)

        aporte_conjuge_fraction = cfg.aporte_base * (1 - cfg.fator_reduzido)

        def _compute_aporte(renda_nova_brl: float) -> tuple[float, float]:
            if salario_conjuge_brl > 0:
                recovery = min(1.0, renda_nova_brl / salario_conjuge_brl)
            else:
                recovery = 1.0 if renda_nova_brl > 0 else 0.0
            base = aporte_s1 + aporte_conjuge_fraction * recovery
            surplus = max(0.0, renda_nova_brl - salario_conjuge_brl)
            extra = min(
                surplus * (cfg.surplus_share_pct / 100.0),
                cfg.aporte_base * (cfg.surplus_cap_pct / 100.0),
            )
            return round(base + extra, 2), recovery

        renda_nclex_brl = cfg.renda_rn_minima_usd * cfg.cambio_usd_brl
        aporte_s2, recovery_nclex = _compute_aporte(renda_nclex_brl)
        prazo_s2 = round(self._compute_prazo(investivel, meta_if, r, aporte_s2), 1)

        renda_gc_brl = cfg.renda_rn_maxima_usd * cfg.cambio_usd_brl
        aporte_s3, recovery_gc = _compute_aporte(renda_gc_brl)
        prazo_s3 = round(self._compute_prazo(investivel, meta_if, r, aporte_s3), 1)

        prazos = (prazo_s1, prazo_s2, prazo_s3)
        aportes = (aporte_s1, aporte_s2, aporte_s3)
        anos_if = tuple(cfg.reference_date.year + int(p) for p in prazos)
        idade_titular = tuple(
            _calculate_age(cfg.titular_dob, cfg.reference_date) + int(p)
            for p in prazos
        )

        cenarios = (
            self._build_cenario(
                0, aportes, prazos, anos_if, idade_titular, resumo=self._resumo_s1(
                    aportes[0], prazos[0], anos_if[0]
                ),
            ),
            self._build_cenario(
                1, aportes, prazos, anos_if, idade_titular, resumo=self._resumo_s2(
                    aportes[1], prazos[1], anos_if[1]
                ),
            ),
            self._build_cenario(
                2, aportes, prazos, anos_if, idade_titular, resumo=self._resumo_s3(
                    aportes[2], prazos[2], anos_if[2]
                ),
            ),
        )

        premissas: dict[str, Any] = {
            "meta_if": meta_if,
            "investivel_atual": investivel,
            "retorno_real_anual_pct": cfg.retorno_real_anual_pct,
            "cambio_usd_brl": cfg.cambio_usd_brl,
            "aporte_base": cfg.aporte_base,
            "fator_reduzido": cfg.fator_reduzido,
            "renda_nclex_usd": cfg.renda_rn_minima_usd,
            "renda_nclex_brl": round(renda_nclex_brl, 2),
            "renda_gc_usd": cfg.renda_rn_maxima_usd,
            "renda_gc_brl": round(renda_gc_brl, 2),
            f"salario_{cfg.conjuge_key}_clt_brl": salario_conjuge_brl,
            "recovery_nclex_pct": round(recovery_nclex * 100, 1),
            "recovery_gc_pct": round(recovery_gc * 100, 1),
        }

        return CenariosConjugeResult(
            cenarios=cenarios,
            premissas=premissas,
            titular_key=cfg.titular_key,
        )

    # -- Helpers --

    def _extract_salario_conjuge(self, fluxo: dict[str, Any]) -> float:
        """Tira a mediana dos valores não-zero do dataset CLT do cônjuge."""
        cfg = self._config
        rmd = (fluxo or {}).get("receita_despesa_mensal_detalhado", {}) or {}
        for ds in rmd.get("receita_datasets", []) or []:
            label = str(ds.get("label", "")).lower()
            if "clt" in label and cfg.conjuge_nome.lower() in label:
                nonzero = [_safe_float(v) for v in ds.get("data", []) if _safe_float(v) > 0]
                if nonzero:
                    s = sorted(nonzero)
                    return s[len(s) // 2]  # mediana aproximada
        return 0.0

    @staticmethod
    def _compute_prazo(
        investivel: float, meta: float, r: float, aporte: float
    ) -> float:
        if investivel >= meta:
            return 0.0
        if r > 0 and aporte > 0:
            numerator = meta + aporte / r
            denominator = investivel + aporte / r
            if denominator > 0 and numerator / denominator > 0:
                n_meses = math.log(numerator / denominator) / math.log(1 + r)
                return max(0.0, n_meses / 12)
        return 999.0

    def _build_cenario(
        self,
        i: int,
        aportes: tuple,
        prazos: tuple,
        anos_if: tuple,
        idades: tuple,
        *,
        resumo: str,
    ) -> CenarioItem:
        return CenarioItem(
            nome=self._LABELS[i],
            aporte_mensal=aportes[i],
            prazo_if_anos=prazos[i],
            ano_if=anos_if[i],
            idade_titular=idades[i],
            resumo=resumo,
        )

    def _resumo_s1(self, aporte: float, prazo: float, ano_if: int) -> str:
        cfg = self._config
        return (
            f"Sem renda da {cfg.conjuge_nome}, aporte cai para R$ {aporte:,.0f}/mês "
            f"({cfg.fator_reduzido:.0%} do base). IF em {prazo:.0f} anos ({ano_if})."
        )

    def _resumo_s2(self, aporte: float, prazo: float, ano_if: int) -> str:
        cfg = self._config
        return (
            f"{cfg.conjuge_nome} como RN (US$ {cfg.renda_rn_minima_usd:,.0f}/mês), "
            f"aporte sobe para R$ {aporte:,.0f}/mês. IF em {prazo:.0f} anos ({ano_if})."
        )

    def _resumo_s3(self, aporte: float, prazo: float, ano_if: int) -> str:
        cfg = self._config
        return (
            f"{cfg.conjuge_nome} como RN sênior/Green Card "
            f"(US$ {cfg.renda_rn_maxima_usd:,.0f}/mês), aporte de R$ {aporte:,.0f}/mês. "
            f"IF em {prazo:.0f} anos ({ano_if})."
        )
