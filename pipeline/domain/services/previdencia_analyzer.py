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
from pipeline.domain.services.irpf_faixa_marginal import resolve_faixa_marginal
from pipeline.domain.types.config import FiscalParameters, IRPFBracket


def _to_cents(reais: float) -> int:
    return int(round(reais * 100))


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
                    upper_brl_cents=_to_cents(_safe_float(limite)) if limite is not None else None,
                    aliquota_pct=Decimal(str(_safe_float(faixa.get("aliquota_pct", 0)))),
                    deducao_brl_cents=0,
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
        # Passa-through: a conversão anterior para reais-float perdia a faixa cujo
        # teto é 0 (`if b.upper_brl_cents` é falsy em zero), promovendo-a a terminal.
        lp_pct = float(fiscal.lucro_presumido_aliquota * Decimal("100"))
        return cls(
            lucro_presumido_pct=lp_pct or 32.0,
            pgbl_limite_pct=12.0,
            irpf_faixas=fiscal.ir_brackets,
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


# `Decimal` em memória, `float` no wire: `to_legacy_dict` É a fronteira de
# serialização do payload E5 (ADR-090 §consequências).
def _round_ou_ausente(valor: Decimal | None) -> float | None:
    return None if valor is None else float(round(valor, 2))


# Os campos prescritivos nascem AUSENTES, não zerados (ADR-375 D4). `R$ 0` como
# "aporte sugerido" continua sendo conselho, e um default numérico faz o card
# voltar a publicar assim que alguém mudar o `def` — gate de call-site não
# protege o default.
@dataclass(frozen=True)
class PrevidenciaAnalysis:
    status: str  # "Calculado" | "N/D"
    nota: str
    renda_tributavel_anual: Decimal | None = None
    limite_pgbl_anual: Decimal | None = None
    aporte_mensal: Decimal | None = None
    aliquota_marginal: float | None = None  # percentage, não money
    economia_ir_anual: Decimal | None = None
    fonte_recomendacao: str | None = None  # "irpf_capacidade" (ADR-277/375)
    ano_base: int | None = None  # ADR-305 D4: ano-base fiscal do cálculo
    nota_degradacao: str | None = None  # ADR-305 D3

    def to_legacy_dict(self) -> dict:
        return {
            "status": self.status,
            "nota": self.nota,
            "renda_tributavel_anual": _round_ou_ausente(self.renda_tributavel_anual),
            "limite_pgbl_anual": _round_ou_ausente(self.limite_pgbl_anual),
            "aporte_mensal": _round_ou_ausente(self.aporte_mensal),
            "aliquota_marginal": self.aliquota_marginal,
            "economia_ir_anual": _round_ou_ausente(self.economia_ir_anual),
            "fonte_recomendacao": self.fonte_recomendacao,
            "ano_base": self.ano_base,
            "nota_degradacao": self.nota_degradacao,
        }


# =============================================================================
# Service
# =============================================================================


_DEFAULT_NUM_MONTHS = 12

_NOTA_SEM_CAPACIDADE = (
    "Não há IRPF processado para medir o seu espaço dedutível de PGBL. O limite de "
    "12% incide sobre a renda tributável declarada na pessoa física — pró-labore e "
    "demais rendimentos tributáveis —, e lucros distribuídos não entram nessa base. "
    "Processe a declaração mais recente para que este número apareça."
)


# Nomeia o insumo que falta, não a nossa incapacidade — e a ausência é ausência,
# não zero: `R$ 0` num campo chamado "aporte sugerido" continua sendo conselho.
def _sem_capacidade_declarada() -> PrevidenciaAnalysis:
    return PrevidenciaAnalysis(status="N/D", nota=_NOTA_SEM_CAPACIDADE)


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
        """Espaço PGBL a partir da capacidade declarada no IRPF; sem ela, ausência."""
        if capacidade_irpf is None:
            return _sem_capacidade_declarada()
        return self._analyze_via_irpf(capacidade_irpf)

    def _analyze_via_irpf(self, cap: CapacidadePgblIRPF) -> PrevidenciaAnalysis:
        restante = max(Decimal("0"), cap.restante_anual)
        aliquota = self._aliquota_para(int(cap.renda_tributavel_anual * 100))
        return PrevidenciaAnalysis(
            status="Calculado",
            nota=_nota_capacidade_irpf(cap, float(restante)),
            renda_tributavel_anual=cap.renda_tributavel_anual,
            limite_pgbl_anual=restante,
            aporte_mensal=restante / Decimal("12"),
            aliquota_marginal=aliquota,
            economia_ir_anual=restante * Decimal(str(aliquota)) / Decimal("100"),
            fonte_recomendacao="irpf_capacidade",
            ano_base=cap.ano_base,
            nota_degradacao=cap.nota_degradacao,
        )

    def _aliquota_para(self, base_calculo_anual_brl_cents: int) -> float:
        """Alíquota marginal; sem tabela configurada, degrada para o fallback declarado."""
        # A degradação por ausência de tabela é política do chamador, não da regra:
        # o service recusa tabela vazia porque resolver faixa sem faixas é erro de
        # config. Publicar prescrição sobre esse fallback é o que a ADR-375 D4 fecha.
        faixas = self._config.irpf_faixas
        if not faixas:
            return self._config.aliquota_fallback
        return float(resolve_faixa_marginal(base_calculo_anual_brl_cents, faixas))
