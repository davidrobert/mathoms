"""PrevidenciaAnalyzer — otimização PGBL a partir de receita PJ (Sessão A5b).

Extrai ``analyze_previdencia_pgbl`` (e5_analyze.py:1632) em domain service
puro. Calcula potencial de dedução PGBL via receita PJ (anualizada) com base
em ``FiscalParameters`` (ADR-135 — fonte: tabela ``fiscal_parameters``) ou
``parametros_fiscais.json`` legacy (até A7.5).

Função pura. Recebe ``PrevidenciaConfig`` tipada (R9/ISP) e dicts de entrada
(``fluxo``). Não toca disco.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from pipeline.domain.services.brl_prose import fmt_brl_prosa
from pipeline.domain.services.irpf_analyzer import CapacidadePgbl, PgblStatus
from pipeline.domain.services.irpf_faixa_marginal import resolve_faixa_marginal
from pipeline.domain.services.pgbl_economia_ir import economia_diferencial
from pipeline.domain.services.pgbl_motivos import (
    CAMPOS_MOTIVO_PGBL,
    FRAGMENTO_CANONICO_MOTIVO,
    PRECEDENCIA_MOTIVO_PGBL,
    MotivoAusenciaPgbl,
    _com_motivo_de_economia_nula,
    _motivos_por_campo,
    _prescreve,
    motivo_dominante,
)
from pipeline.domain.services.pgbl_notas import (
    _NOTA_BASE_FAMILIAR,
    _NOTA_DIFERIMENTO,
    _NOTA_IRPFM,
    _NOTA_NO_TETO,
    _NOTA_PROXY_ANO_CORRENTE,
    _NOTA_REGIME_INCOMPLETO,
    _NOTA_SEM_CAPACIDADE,
    _NOTA_SEM_RENDA,
    _NOTA_SEM_TABELA,
    _NOTA_SIMPLIFICADO,
    _nota_do_motivo,
)
from pipeline.domain.types.config import FiscalParameters, IRPFBracket, RedutorIRPF


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
    # ADR-389 D4 + A40.l64: completude do regime é DADO da row, para o consumidor
    # recusar lendo-a em vez de `if year >= 2026`. O caminho legado (`from_fiscal`,
    # dict pré-A7.2b) não conhece a coluna e presume completo — presumir incompleto
    # ali reteria a prescrição de todo workspace legado sem defeito medido.
    regime_completo: bool = True
    componentes_ausentes: tuple[str, ...] = ()
    ano_fiscal: int | None = None
    # ADR-414 D4. VO zerado (default) = ano sem redutor — o caminho legado nunca
    # o conhece, e AC <= 2025 também não tem.
    redutor: RedutorIRPF = field(default_factory=RedutorIRPF)
    irpfm_limiar_brl_cents: int = 0
    # Sem row do ano: recusa, nunca fallback silencioso ([[A40.l79]]).
    tabela_ausente: bool = False

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
            # ADR-389 D2: a base da DAA é a tabela ANUAL — a mensal serve o IRRF
            # na fonte e é consumida pela cascata da S8 ([[A40.l37]]).
            irpf_faixas=fiscal.ir_brackets_anual.faixas,
            redutor=fiscal.redutor_anual,
            irpfm_limiar_brl_cents=fiscal.irpfm_limiar_brl_cents,
            tabela_ausente=fiscal.tabela_ausente,
            regime_completo=fiscal.regime_completo,
            componentes_ausentes=fiscal.componentes_ausentes,
            ano_fiscal=fiscal.year,
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class CapacidadePgblIRPF:
    """Capacidade PGBL do titular lida do IRPF (ADR-277/395)."""

    capacidade: CapacidadePgbl
    # BRUTO: indexa o redutor da Lei 15.270/2025 (ADR-414 D1) e é o que os 12% do
    # teto PGBL usam. NÃO indexa a tabela progressiva.
    renda_tributavel_anual: Decimal
    ano_base: int
    fonte: str
    # BASE de cálculo DECLARADA (`imposto_apurado.base_calculo_brl` somado no ano):
    # é ela que indexa a tabela e a alíquota marginal. OBRIGATÓRIA: o campo é
    # `required` no schema e16, então declaração que parseia sempre a tem — e o `cap`
    # só existe se alguma parseou. Optional aqui seria ramo que não dispara, e cair
    # no bruto é o defeito que a ADR-414 fecha.
    base_calculo_anual: Decimal
    # Limite SUPERIOR do `REND` do IRPFM: o maior bruto entre as declarações do
    # ano (tributável + isentos + exclusiva). Superior porque as exclusões do
    # art. 16-A só REDUZEM — logo, abaixo do piso o mínimo certamente não vincula.
    rend_upper_anual: Decimal = Decimal("0")
    # Quantas declarações compõem a base do ano. > 1 ⇒ a base é SOMA familiar, e
    # a progressividade não é aditiva (`IR(a+b) > IR(a)+IR(b)`) ⇒ a economia sai
    # superestimada. Enquanto a apuração por declaração não existir ([[ADR-414]]
    # §Limitação), o número é retido em vez de publicado com viés conhecido.
    declaracoes_no_ano: int = 1
    nota_degradacao: str | None = None  # ADR-305 D3: existe ano mais recente não usado

    @property
    def pgbl_status(self) -> PgblStatus:
        return self.capacidade.status


# `Decimal` em memória, `float` no wire: `to_legacy_dict` É a fronteira de
# serialização do payload E5 (ADR-090 §consequências).
def _cents(valor: Decimal) -> int:
    return int(valor * 100)


def _round_ou_ausente(valor: Decimal | None) -> float | None:
    return None if valor is None else float(round(valor, 2))


# Os campos prescritivos nascem AUSENTES, não zerados (ADR-375 D4). `R$ 0` como
# "aporte sugerido" continua sendo conselho, e um default numérico faz o card
# voltar a publicar assim que alguém mudar o `def` — gate de call-site não
# protege o default.
@dataclass(frozen=True)
class CamposGateados:
    """Os 5 campos que um motivo de ausência pode suprimir (ADR-402)."""

    limite_pgbl_anual: Decimal | None
    capacidade_restante_anual: Decimal | None
    aporte_mensal: Decimal | None
    aliquota_marginal: float | None  # percentage, não money
    economia_ir_anual: Decimal | None


@dataclass(frozen=True)
class PrevidenciaAnalysis:
    # `limite_pgbl_anual` carrega o TETO (12% × base tributável das declarações
    # completas), não a capacidade restante — o nome sempre disse teto e o valor
    # era outro (ADR-402). O restante mora em `capacidade_restante_anual`, onde
    # `0` é legítimo: significa teto consumido, e não "não existe teto".
    status: str  # "Calculado" | "N/D"
    nota: str
    renda_tributavel_anual: Decimal | None = None
    limite_pgbl_anual: Decimal | None = None
    capacidade_restante_anual: Decimal | None = None
    aporte_mensal: Decimal | None = None
    aliquota_marginal: float | None = None  # percentage, não money
    economia_ir_anual: Decimal | None = None
    fonte_recomendacao: str | None = None  # "irpf_capacidade" (ADR-277/375)
    ano_base: int | None = None  # ADR-305 D4: ano-base fiscal do cálculo
    nota_degradacao: str | None = None  # ADR-305 D3
    pgbl_status: PgblStatus | None = None
    pgbl_aportado_anual: Decimal | None = None
    excedente_nao_dedutivel_anual: Decimal | None = None
    motivo_ausencia: dict[str, MotivoAusenciaPgbl | None] = field(
        default_factory=lambda: dict.fromkeys(CAMPOS_MOTIVO_PGBL)
    )

    def to_legacy_dict(self) -> dict:
        return {
            "status": self.status,
            "nota": self.nota,
            "renda_tributavel_anual": _round_ou_ausente(self.renda_tributavel_anual),
            "limite_pgbl_anual": _round_ou_ausente(self.limite_pgbl_anual),
            "capacidade_restante_anual": _round_ou_ausente(self.capacidade_restante_anual),
            "aporte_mensal": _round_ou_ausente(self.aporte_mensal),
            "aliquota_marginal": self.aliquota_marginal,
            "economia_ir_anual": _round_ou_ausente(self.economia_ir_anual),
            "fonte_recomendacao": self.fonte_recomendacao,
            "ano_base": self.ano_base,
            "nota_degradacao": self.nota_degradacao,
            "pgbl_status": self.pgbl_status.value if self.pgbl_status else None,
            "pgbl_aportado_anual": _round_ou_ausente(self.pgbl_aportado_anual),
            "excedente_nao_dedutivel_anual": _round_ou_ausente(self.excedente_nao_dedutivel_anual),
            "motivo_ausencia": self._motivo_ausencia_wire(),
        }

    def _motivo_ausencia_wire(self) -> dict[str, str | None]:
        return {
            campo: (motivo.value if motivo else None)
            for campo, motivo in self.motivo_ausencia.items()
        }


# =============================================================================
# Service
# =============================================================================


_DEFAULT_NUM_MONTHS = 12


# Nomeia o insumo que falta, não a nossa incapacidade — e a ausência é ausência,
# não zero: `R$ 0` num campo chamado "aporte sugerido" continua sendo conselho.
def _sem_capacidade_declarada() -> PrevidenciaAnalysis:
    return PrevidenciaAnalysis(
        status="N/D",
        nota=_NOTA_SEM_CAPACIDADE,
        motivo_ausencia=dict.fromkeys(CAMPOS_MOTIVO_PGBL, MotivoAusenciaPgbl.sem_irpf_processado),
    )


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

    def _motivos(self, cap: CapacidadePgblIRPF) -> dict[str, MotivoAusenciaPgbl | None]:
        return _motivos_por_campo(
            cap,
            self._config.regime_completo,
            self._irpfm_vincula(cap),
            self._config.tabela_ausente,
        )

    def _analyze_via_irpf(self, cap: CapacidadePgblIRPF) -> PrevidenciaAnalysis:
        motivos = self._motivos(cap)
        economia = self._economia(cap, motivos)
        motivos = _com_motivo_de_economia_nula(motivos, economia, cap.capacidade.restante)
        return PrevidenciaAnalysis(
            status="Calculado",
            nota=_nota_do_motivo(motivo_dominante(motivos), cap, self._config),
            renda_tributavel_anual=cap.renda_tributavel_anual,
            fonte_recomendacao="irpf_capacidade",
            ano_base=cap.ano_base,
            nota_degradacao=cap.nota_degradacao,
            pgbl_status=cap.pgbl_status,
            pgbl_aportado_anual=cap.capacidade.aportado,
            excedente_nao_dedutivel_anual=cap.capacidade.excedente_nao_dedutivel,
            motivo_ausencia=motivos,
            **asdict(self._campos_gateados(cap, motivos, economia)),
        )

    # Um campo com motivo é ausência, sempre — nunca número menor (ADR-375 D4).
    # `aliquota_marginal` é bicondicional com a economia: marginal sem economia
    # publicável é ruído citável, que convida o leitor a reconstruir a prescrição
    # que o motivo acabou de suprimir.
    def _campos_gateados(
        self,
        cap: CapacidadePgblIRPF,
        motivos: dict[str, MotivoAusenciaPgbl | None],
        economia: Decimal | None,
    ) -> "CamposGateados":
        restante = cap.capacidade.restante
        # A marginal é bicondicional com o APORTE, não com a economia: é o aporte
        # que ela permite reconstruir (alíquota × aporte). Retido o aporte, a
        # marginal sai junto; publicado (inclusive o zero de `no_teto`), ela fica.
        return CamposGateados(
            limite_pgbl_anual=None if motivos["teto"] else cap.capacidade.teto,
            capacidade_restante_anual=None if motivos["restante"] else restante,
            aporte_mensal=None if motivos["aporte"] else restante / Decimal("12"),
            aliquota_marginal=None if motivos["aporte"] else self._aliquota(cap),
            economia_ir_anual=economia,
        )

    # Reter prescrição não é apagar fato: a capacidade de 12% vem do IRPF e não
    # depende do regime do ano corrente. O que sai são os dois campos que a
    # ADR-375 D4 nomeia — "prescrever PGBL" (aporte) e "publicar economia de IR".
    # Limiar `0` = ano sem IRPFM (AC <= 2025) ⇒ nunca vincula. A vigência vem do
    # DADO da row, nunca de `if year >= 2026` ([[ADR-414]] D5).
    def _irpfm_vincula(self, cap: CapacidadePgblIRPF) -> bool:
        limiar = self._config.irpfm_limiar_brl_cents
        return limiar > 0 and _cents(cap.rend_upper_anual) >= limiar

    def _economia(
        self, cap: CapacidadePgblIRPF, motivos: dict[str, MotivoAusenciaPgbl | None]
    ) -> Decimal | None:
        if motivos["economia"] or cap.capacidade.restante is None:
            return None
        if not self._config.irpf_faixas:
            # Mesma política de `_aliquota_para`: sem tabela não há diferencial a
            # calcular, e a degradação é do chamador. O produto é o que o caminho
            # legado (dict pré-A7.2b) sempre publicou.
            return cap.capacidade.restante * Decimal(str(self._aliquota(cap))) / Decimal("100")
        # ADR-414 D2: a tabela indexa a BASE declarada, nunca o bruto.
        return economia_diferencial(
            cap.base_calculo_anual,
            cap.capacidade.restante,
            self._config.irpf_faixas,
            bruto_anual=cap.renda_tributavel_anual,
            redutor=self._config.redutor,
        )

    # ADR-414 D1: a faixa marginal é da BASE, não do bruto — o D6 da ADR-375 sempre
    # falou de base (`base_calculo_anual_brl_cents`); era o call-site que divergia.
    def _aliquota(self, cap: CapacidadePgblIRPF) -> float:
        return self._aliquota_para(_cents(cap.base_calculo_anual))

    def _aliquota_para(self, base_calculo_anual_brl_cents: int) -> float:
        """Alíquota marginal; sem tabela configurada, degrada para o fallback declarado."""
        # A degradação por ausência de tabela é política do chamador, não da regra:
        # o service recusa tabela vazia porque resolver faixa sem faixas é erro de
        # config. Publicar prescrição sobre esse fallback é o que a ADR-375 D4 fecha.
        faixas = self._config.irpf_faixas
        if not faixas:
            return self._config.aliquota_fallback
        return float(resolve_faixa_marginal(base_calculo_anual_brl_cents, faixas))
