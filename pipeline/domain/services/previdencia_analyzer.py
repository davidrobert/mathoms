"""PrevidenciaAnalyzer — otimização PGBL a partir de receita PJ (Sessão A5b).

Extrai ``analyze_previdencia_pgbl`` (e5_analyze.py:1632) em domain service
puro. Calcula potencial de dedução PGBL via receita PJ (anualizada) com base
em ``FiscalParameters`` (ADR-135 — fonte: tabela ``fiscal_parameters``) ou
``parametros_fiscais.json`` legacy (até A7.5).

Função pura. Recebe ``PrevidenciaConfig`` tipada (R9/ISP) e dicts de entrada
(``fluxo``). Não toca disco.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pipeline.domain.services.irpf_analyzer import PgblStatus
from pipeline.domain.types.config import FiscalParameters


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

    @classmethod
    def from_fiscal_parameters(cls, fiscal: FiscalParameters) -> "PrevidenciaConfig":
        """Constrói config a partir de :class:`FiscalParameters` (ADR-135 · A7.2b)."""
        faixas = tuple(
            IRPFBracket(
                limite_anual=(b.upper_brl_cents / 100.0) if b.upper_brl_cents else None,
                aliquota_pct=float(b.aliquota_pct),
            )
            for b in fiscal.ir_brackets
        )
        lp_pct = float(fiscal.lucro_presumido_aliquota * Decimal("100"))
        return cls(
            lucro_presumido_pct=lp_pct or 32.0,
            pgbl_limite_pct=12.0,
            irpf_faixas=faixas,
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class CapacidadePgblIRPF:
    """Capacidade PGBL dedutível restante do titular, lida do IRPF (ADR-277)."""

    restante_anual: Decimal  # Σ(tributável×12% − já_aportado), clamp ≥0 (ADR-189)
    renda_tributavel_anual: Decimal
    ano_base: int
    fonte: str
    nota_degradacao: str | None = None  # ADR-305 D3: existe ano mais recente não usado
    pgbl_status: PgblStatus | None = None  # RV2-03: ramifica a nota (simplificado ≠ teto)


@dataclass(frozen=True)
class PrevidenciaAnalysis:
    status: str  # "Calculado" | "N/D"
    nota: str
    renda_tributavel_anual: float
    limite_pgbl_anual: float
    aporte_mensal: float
    aliquota_marginal: float
    economia_ir_anual: float
    fonte_recomendacao: str = "proxy_receita_pj"  # | "irpf_capacidade" (ADR-277)
    ano_base: int | None = None  # ADR-305 D4: ano-base fiscal do cálculo (None no proxy)
    nota_degradacao: str | None = None  # ADR-305 D3

    def to_legacy_dict(self) -> dict:
        return {
            "status": self.status,
            "nota": self.nota,
            "renda_tributavel_anual": round(self.renda_tributavel_anual, 2),
            "limite_pgbl_anual": round(self.limite_pgbl_anual, 2),
            "aporte_mensal": round(self.aporte_mensal, 2),
            "aliquota_marginal": self.aliquota_marginal,
            "economia_ir_anual": round(self.economia_ir_anual, 2),
            "fonte_recomendacao": self.fonte_recomendacao,
            "ano_base": self.ano_base,
            "nota_degradacao": self.nota_degradacao,
        }


# =============================================================================
# Service
# =============================================================================


_DEFAULT_NUM_MONTHS = 12

# ADR-305 D3 (co-design financial-planner): a capacidade lida do IRPF é
# retrospectiva — o número recomenda o ano-calendário CORRENTE via proxy.
_NOTA_PROXY_ANO_CORRENTE = (
    "O espaço dedutível de 12% aplica-se ao ano-calendário corrente — aportes até "
    "31/12 deduzem na próxima declaração; se a renda tributável atual diferir do "
    "ano-base, o espaço real muda proporcionalmente."
)


# RV2-03 (co-design financial-planner): a nota ramifica por PgblStatus, não por
# restante>0. modelo_simplificado (dedução desabilitada pelo modelo) e no_teto
# (teto de 12% consumido) colapsavam ambos em "teto atingido" — factualmente falso
# no simplificado e invertia o conselho. Sem fabricar 12% hipotético (limite/aporte
# ficam 0 — só a prosa cita a hipótese). Conformidade a ADR-305 D3.
_NOTA_DIFERIMENTO = (
    "Lembre que o PGBL difere o IR — o resgate é tributado; o benefício depende da alíquota futura."
)
_NOTA_SIMPLIFICADO = (
    "Declaração no modelo simplificado no ano-base {ano}: o desconto padrão "
    "substitui as deduções legais, então o PGBL não gera economia de IR neste "
    "modelo — o teto de 12% não foi consumido. Migrar para o modelo completo só "
    "compensa se a soma das deduções legais (incluindo até 12% da renda tributável "
    "em PGBL) superar o desconto simplificado, e a dedução de 12% pressupõe "
    "contribuição a regime oficial de previdência. Avalie com seu contador — a "
    "opção de modelo é feita a cada declaração e vale para o ano-calendário corrente."
)
_NOTA_SEM_RENDA = (
    "Sem renda tributável no ano-base {ano}: sem base de cálculo, o PGBL não gera "
    "dedução de IR no momento. O benefício reaparece se houver renda tributável "
    "(ex.: pró-labore ou PJ tributada); reavalie se a situação mudar."
)
_NOTA_NO_TETO = (
    "Teto de 12% da renda tributável já atingido no ano-base {ano} — aportes "
    "adicionais em PGBL não trazem dedução extra neste ano."
)


def _nota_capacidade_irpf(cap: CapacidadePgblIRPF, restante: float) -> str:
    """Nota de capacidade PGBL ramificada por PgblStatus (RV2-03 · ADR-305 D3)."""
    ano = cap.ano_base
    if cap.pgbl_status == PgblStatus.modelo_simplificado:
        return _NOTA_SIMPLIFICADO.format(ano=ano)
    if cap.pgbl_status == PgblStatus.sem_renda_tributavel:
        return _NOTA_SEM_RENDA.format(ano=ano)
    if cap.pgbl_status == PgblStatus.no_teto or (cap.pgbl_status is None and restante <= 0):
        return f"{_NOTA_NO_TETO.format(ano=ano)} {_NOTA_PROXY_ANO_CORRENTE}"
    capacidade = (
        f"Capacidade PGBL restante do IRPF {ano}: R$ {restante:,.0f} (já descontado o aportado)."
    )
    return f"{capacidade} {_NOTA_DIFERIMENTO} {_NOTA_PROXY_ANO_CORRENTE}"


class PrevidenciaAnalyzer:
    """Calcula otimização PGBL a partir de receita PJ anualizada."""

    def __init__(self, config: PrevidenciaConfig | None = None) -> None:
        self._config = config or PrevidenciaConfig()

    def analyze(
        self,
        fluxo: dict[str, Any],
        capacidade_irpf: CapacidadePgblIRPF | None = None,
    ) -> PrevidenciaAnalysis:
        """Recomenda aporte PGBL. Com IRPF do titular, ancora na capacidade
        restante (já líquida do aportado, INV-PREV-3); sem IRPF, usa o proxy
        de receita PJ (ADR-277)."""
        if capacidade_irpf is not None:
            return self._analyze_via_irpf(capacidade_irpf)
        return self._analyze_via_proxy(fluxo)

    def _analyze_via_irpf(self, cap: CapacidadePgblIRPF) -> PrevidenciaAnalysis:
        restante = max(0.0, float(cap.restante_anual))
        renda_trib = float(cap.renda_tributavel_anual)
        aliquota = self._resolve_aliquota(renda_trib)
        return PrevidenciaAnalysis(
            status="Calculado",
            nota=_nota_capacidade_irpf(cap, restante),
            renda_tributavel_anual=renda_trib,
            limite_pgbl_anual=restante,
            aporte_mensal=restante / 12.0,
            aliquota_marginal=aliquota,
            economia_ir_anual=restante * (aliquota / 100.0),
            fonte_recomendacao="irpf_capacidade",
            ano_base=cap.ano_base,
            nota_degradacao=cap.nota_degradacao,
        )

    def _analyze_via_proxy(self, fluxo: dict) -> PrevidenciaAnalysis:
        # ADR-330: renda PJ vem do bloco canônico receita_por_natureza (fallback proxy;
        # o path canônico é _analyze_via_irpf com renda tributável).
        receita_pj = _safe_float(fluxo.get("receita_por_natureza", {}).get("receita_pj", 0))
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
