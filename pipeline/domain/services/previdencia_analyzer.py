"""PrevidenciaAnalyzer — otimização PGBL a partir de receita PJ (Sessão A5b).

Extrai ``analyze_previdencia_pgbl`` (e5_analyze.py:1632) em domain service
puro. Calcula potencial de dedução PGBL via receita PJ (anualizada) com base
em ``parametros_fiscais.json`` (lucro presumido, limite PGBL, tabela IRPF).

Função pura. Recebe ``PrevidenciaConfig`` tipada (R9/ISP) e dicts de entrada
(``fluxo``). Não toca disco.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(",", "."))
        except ValueError:
            return 0.0
    return 0.0


# =============================================================================
# Config (R9/ISP)
# =============================================================================


@dataclass(frozen=True)
class IRPFBracket:
    """Faixa da tabela progressiva IRPF.

    ``limite_anual`` ``None`` representa a última faixa (sem teto).
    """

    limite_anual: float | None
    aliquota_pct: float


@dataclass(frozen=True)
class PrevidenciaConfig:
    """Parâmetros fiscais para cálculo PGBL.

    Sources no legado (parametros_fiscais.json):
    - ``lucro_presumido_pct`` ← ``lucro_presumido.percentual_servicos_pct`` (default 32%)
    - ``pgbl_limite_pct`` ← ``pgbl.limite_deducao_pct`` (default 12%)
    - ``irpf_faixas`` ← ``irpf_tabela_progressiva.faixas``
    - ``aliquota_fallback`` ← default 7,5% quando não há faixas configuradas
    """

    lucro_presumido_pct: float = 32.0
    pgbl_limite_pct: float = 12.0
    irpf_faixas: tuple[IRPFBracket, ...] = ()
    aliquota_fallback: float = 7.5

    @classmethod
    def from_fiscal(cls, fiscal: dict | None = None) -> "PrevidenciaConfig":
        f = fiscal or {}
        lp = f.get("lucro_presumido", {}) or {}
        pgbl = f.get("pgbl", {}) or {}
        irpf = f.get("irpf_tabela_progressiva", {}) or {}
        faixas_raw = irpf.get("faixas") or []
        faixas: list[IRPFBracket] = []
        for faixa in faixas_raw:
            if not isinstance(faixa, dict):
                continue
            limite = faixa.get("limite_anual")
            faixas.append(
                IRPFBracket(
                    limite_anual=_safe_float(limite) if limite is not None else None,
                    aliquota_pct=_safe_float(faixa.get("aliquota_pct", 0)),
                )
            )
        return cls(
            lucro_presumido_pct=_safe_float(lp.get("percentual_servicos_pct", 32.0)),
            pgbl_limite_pct=_safe_float(pgbl.get("limite_deducao_pct", 12.0)),
            irpf_faixas=tuple(faixas),
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class PrevidenciaAnalysis:
    status: str  # "Calculado" | "N/D"
    nota: str
    renda_tributavel_anual: float
    limite_pgbl_anual: float
    aporte_mensal: float
    aliquota_marginal: float
    economia_ir_anual: float

    def to_legacy_dict(self) -> dict:
        return {
            "status": self.status,
            "nota": self.nota,
            "renda_tributavel_anual": round(self.renda_tributavel_anual, 2),
            "limite_pgbl_anual": round(self.limite_pgbl_anual, 2),
            "aporte_mensal": round(self.aporte_mensal, 2),
            "aliquota_marginal": self.aliquota_marginal,
            "economia_ir_anual": round(self.economia_ir_anual, 2),
        }


# =============================================================================
# Service
# =============================================================================


_DEFAULT_NUM_MONTHS = 12


class PrevidenciaAnalyzer:
    """Calcula otimização PGBL a partir de receita PJ anualizada."""

    def __init__(self, config: PrevidenciaConfig | None = None) -> None:
        self._config = config or PrevidenciaConfig()

    def analyze(self, fluxo: dict[str, Any]) -> PrevidenciaAnalysis:
        receita_pj = _safe_float(fluxo.get("por_fonte", {}).get("receita_pj", 0))
        num_months = len(
            (fluxo.get("receita_despesa_mensal_detalhado", {}) or {}).get("labels", []) or []
        )
        if num_months == 0:
            num_months = _DEFAULT_NUM_MONTHS

        receita_pj_anual = receita_pj * (12 / num_months) if num_months > 0 else 0

        cfg = self._config
        lp_factor = cfg.lucro_presumido_pct / 100.0
        pgbl_factor = cfg.pgbl_limite_pct / 100.0

        renda_tributavel = receita_pj_anual * lp_factor

        if renda_tributavel <= 0:
            return PrevidenciaAnalysis(
                status="N/D",
                nota="Sem receita PJ identificada para cálculo de PGBL.",
                renda_tributavel_anual=0.0,
                limite_pgbl_anual=0.0,
                aporte_mensal=0.0,
                aliquota_marginal=0.0,
                economia_ir_anual=0.0,
            )

        limite_pgbl = renda_tributavel * pgbl_factor

        aliquota_marginal = self._resolve_aliquota(renda_tributavel)
        economia_ir = limite_pgbl * (aliquota_marginal / 100.0)

        lp_pct_display = int(cfg.lucro_presumido_pct)
        return PrevidenciaAnalysis(
            status="Calculado",
            nota=(
                f"Base: receita PJ anualizada R$ {receita_pj_anual:,.0f}, "
                f"lucro presumido {lp_pct_display}%."
            ),
            renda_tributavel_anual=renda_tributavel,
            limite_pgbl_anual=limite_pgbl,
            aporte_mensal=limite_pgbl / 12.0,
            aliquota_marginal=aliquota_marginal,
            economia_ir_anual=economia_ir,
        )

    def _resolve_aliquota(self, renda_tributavel: float) -> float:
        """Busca a alíquota marginal correspondente à renda anual.

        Paridade com legado (linha 1671-1678): começa com a 1ª faixa, itera;
        se renda > limite_anual, avança; a última faixa (``limite_anual=None``)
        é selecionada automaticamente.
        """
        faixas = self._config.irpf_faixas
        if not faixas:
            return self._config.aliquota_fallback

        aliquota = faixas[0].aliquota_pct
        for faixa in faixas:
            if faixa.limite_anual is not None and renda_tributavel > faixa.limite_anual:
                aliquota = faixa.aliquota_pct
            elif faixa.limite_anual is None:
                aliquota = faixa.aliquota_pct
        return aliquota
