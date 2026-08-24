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
    # ADR-389 D4 + A40.l64: completude do regime é DADO da row, para o consumidor
    # recusar lendo-a em vez de `if year >= 2026`. O caminho legado (`from_fiscal`,
    # dict pré-A7.2b) não conhece a coluna e presume completo — presumir incompleto
    # ali reteria a prescrição de todo workspace legado sem defeito medido.
    regime_completo: bool = True
    componentes_ausentes: tuple[str, ...] = ()
    ano_fiscal: int | None = None

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
            regime_completo=fiscal.regime_completo,
            componentes_ausentes=fiscal.componentes_ausentes,
            ano_fiscal=fiscal.year,
        )


# =============================================================================
# Result
# =============================================================================


# `nota_degradacao` NÃO serve a este papel: tem dono semântico (ADR-305 D3 —
# "existe ano-base mais recente não usado") e coocorre com estes motivos.
class MotivoAusenciaPgbl(str, Enum):
    """Por que um campo do card PGBL nasce ausente (ADR-402). Enum fechado."""

    sem_irpf_processado = "sem_irpf_processado"
    modelo_simplificado = "modelo_simplificado"
    sem_renda_tributavel = "sem_renda_tributavel"
    regime_fiscal_incompleto = "regime_fiscal_incompleto"


# Precedência declarada: o primeiro que se aplica é o dominante e CALA os demais.
# Sem ela, o r7 publicou uma nota que casava `_NOTA_REGIME_INCOMPLETO` E
# `_NOTA_SIMPLIFICADO` — duas explicações mutuamente exclusivas no mesmo texto.
PRECEDENCIA_MOTIVO_PGBL: tuple[MotivoAusenciaPgbl, ...] = (
    MotivoAusenciaPgbl.sem_irpf_processado,
    MotivoAusenciaPgbl.modelo_simplificado,
    MotivoAusenciaPgbl.sem_renda_tributavel,
    MotivoAusenciaPgbl.regime_fiscal_incompleto,
)

# Os quatro campos que podem nascer ausentes, na ordem em que o card os lê.
CAMPOS_MOTIVO_PGBL: tuple[str, ...] = ("teto", "restante", "aporte", "economia")

# Fonte única do par (motivo, texto): a nota e os campos derivam AMBOS do VO, e
# este mapa é o que permite ao gate assertar coocorrência em vez de inspecionar.
FRAGMENTO_CANONICO_MOTIVO: dict[MotivoAusenciaPgbl, str] = {
    MotivoAusenciaPgbl.sem_irpf_processado: "Não há IRPF processado",
    MotivoAusenciaPgbl.modelo_simplificado: "modelo simplificado",
    MotivoAusenciaPgbl.sem_renda_tributavel: "Sem renda tributável",
    MotivoAusenciaPgbl.regime_fiscal_incompleto: "não se aplica ao ano-calendário",
}


def motivo_dominante(
    motivos: dict[str, MotivoAusenciaPgbl | None],
) -> MotivoAusenciaPgbl | None:
    """O motivo de maior precedência presente — quem decide a nota."""
    presentes = {m for m in motivos.values() if m is not None}
    for motivo in PRECEDENCIA_MOTIVO_PGBL:
        if motivo in presentes:
            return motivo
    return None


# Carrega o VO inteiro, não o escalar: `teto` e `restante` são grandezas
# distintas, e o campo publicado com nome de teto precisa do teto.
@dataclass(frozen=True)
class CapacidadePgblIRPF:
    """Capacidade PGBL do titular lida do IRPF (ADR-277/395)."""

    capacidade: CapacidadePgbl
    renda_tributavel_anual: Decimal
    ano_base: int
    fonte: str
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

_NOTA_SEM_CAPACIDADE = (
    "Não há IRPF processado para medir o seu espaço dedutível de PGBL. O limite de "
    "12% incide sobre a renda tributável declarada na pessoa física — pró-labore e "
    "demais rendimentos tributáveis —, e lucros distribuídos não entram nessa base. "
    "Processe a declaração mais recente para que este número apareça."
)


# Nomeia o insumo que falta, não a nossa incapacidade — e a ausência é ausência,
# não zero: `R$ 0` num campo chamado "aporte sugerido" continua sendo conselho.
def _sem_capacidade_declarada() -> PrevidenciaAnalysis:
    return PrevidenciaAnalysis(
        status="N/D",
        nota=_NOTA_SEM_CAPACIDADE,
        motivo_ausencia=dict.fromkeys(CAMPOS_MOTIVO_PGBL, MotivoAusenciaPgbl.sem_irpf_processado),
    )


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


# A40.l64 — a row de AC2026 nasce `regime_completo=False` porque a tabela
# progressiva deixou de descrever sozinha o imposto devido. Os dois componentes
# que faltam são independentes do aporte, então a diferencial por faixa
# superestima: quem tem tributável anual até R$ 60k já paga zero depois do
# redutor, e acima de R$ 600k o mínimo reabsorve o que a dedução economiza.
_COMPONENTE_LABEL = {
    "redutor_lei_15270": "o redutor da Lei 15.270/2025",
    "irpfm": "o imposto mínimo sobre altas rendas (IRPFM)",
}


def _lista_componentes(componentes: tuple[str, ...]) -> str:
    """Rótulos legíveis em português; termo desconhecido sai verbatim, não sumido."""
    rotulos = [_COMPONENTE_LABEL.get(c, c) for c in componentes]
    if not rotulos:
        return "componentes do regime vigente"
    if len(rotulos) == 1:
        return rotulos[0]
    return f"{', '.join(rotulos[:-1])} e {rotulos[-1]}"


_NOTA_REGIME_INCOMPLETO = (
    "A estimativa de economia de IR não se aplica ao ano-calendário {ano}: a tabela "
    "progressiva deixou de descrever sozinha o imposto devido, e ainda falta modelar "
    "{componentes}. Nenhum deles se move com o aporte, então calcular a economia pela "
    "diferença de faixa superestimaria o benefício — e para renda tributável de até "
    "R$ 60 mil no ano, em que o imposto já fica zerado, publicaria uma economia "
    "inexistente. O seu espaço dedutível de 12% continua válido e está declarado acima; "
    "a estimativa volta quando o regime estiver completo."
)


def _nota_regime_incompleto(config: "PrevidenciaConfig") -> str:
    ano = config.ano_fiscal or "corrente"
    return _NOTA_REGIME_INCOMPLETO.format(
        ano=ano, componentes=_lista_componentes(config.componentes_ausentes)
    )


# Direção da derivação (ADR-402): nota e campos derivam AMBOS do VO. A nota
# nunca é escrita ao lado do campo, e o campo nunca é lido a partir da nota —
# `null` não carrega a razão de ser `null`, então "nota derivada do campo" é
# inexequível. O motivo dominante é o pivô comum.
def _motivos_por_campo(
    cap: CapacidadePgblIRPF, regime_completo: bool
) -> dict[str, MotivoAusenciaPgbl | None]:
    """Aplica a precedência aos 4 campos. Fonte única do que é ausência e por quê."""
    if cap.pgbl_status == PgblStatus.modelo_simplificado:
        return dict.fromkeys(CAMPOS_MOTIVO_PGBL, MotivoAusenciaPgbl.modelo_simplificado)
    # `teto is None` sem status simplificado significa que nenhuma declaração
    # COMPLETA tem base tributável — a dedução de 12% não tem sobre o que incidir.
    if cap.pgbl_status == PgblStatus.sem_renda_tributavel or cap.capacidade.teto is None:
        return dict.fromkeys(CAMPOS_MOTIVO_PGBL, MotivoAusenciaPgbl.sem_renda_tributavel)
    if not regime_completo:
        # Anula prescrição (ADR-375 D4) e PRESERVA o fato: o espaço de 12% vem do
        # IRPF e não depende da completude do regime do ano corrente.
        return {
            "teto": None,
            "restante": None,
            "aporte": MotivoAusenciaPgbl.regime_fiscal_incompleto,
            "economia": MotivoAusenciaPgbl.regime_fiscal_incompleto,
        }
    return dict.fromkeys(CAMPOS_MOTIVO_PGBL, None)


def _nota_capacidade_irpf(cap: CapacidadePgblIRPF, restante: Decimal | None) -> str:
    """Fato medido (sem motivo dominante de ausência total): teto vivo ou consumido."""
    ano = cap.ano_base
    if cap.pgbl_status == PgblStatus.no_teto or not restante or restante <= 0:
        return f"{_NOTA_NO_TETO.format(ano=ano)} {_NOTA_PROXY_ANO_CORRENTE}"
    capacidade = (
        f"Capacidade PGBL restante do IRPF {ano}: {fmt_brl_prosa(restante)} "
        "(já descontado o aportado)."
    )
    return f"{capacidade} {_NOTA_DIFERIMENTO} {_NOTA_PROXY_ANO_CORRENTE}"


def _nota_do_motivo(
    dominante: MotivoAusenciaPgbl | None,
    cap: CapacidadePgblIRPF,
    config: "PrevidenciaConfig",
) -> str:
    """Uma nota, um motivo. A precedência já calou os demais."""
    ano = cap.ano_base
    if dominante == MotivoAusenciaPgbl.modelo_simplificado:
        return _NOTA_SIMPLIFICADO.format(ano=ano)
    if dominante == MotivoAusenciaPgbl.sem_renda_tributavel:
        return _NOTA_SEM_RENDA.format(ano=ano)
    fato = _nota_capacidade_irpf(cap, cap.capacidade.restante)
    if dominante == MotivoAusenciaPgbl.regime_fiscal_incompleto:
        return f"{_nota_regime_incompleto(config)} {fato}"
    return fato


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
        motivos = _motivos_por_campo(cap, self._config.regime_completo)
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
            **asdict(self._campos_gateados(cap, motivos)),
        )

    # Um campo com motivo é ausência, sempre — nunca número menor (ADR-375 D4).
    # `aliquota_marginal` é bicondicional com a economia: marginal sem economia
    # publicável é ruído citável, que convida o leitor a reconstruir a prescrição
    # que o motivo acabou de suprimir.
    def _campos_gateados(
        self, cap: CapacidadePgblIRPF, motivos: dict[str, MotivoAusenciaPgbl | None]
    ) -> "CamposGateados":
        restante = cap.capacidade.restante
        economia = self._economia(cap, motivos)
        return CamposGateados(
            limite_pgbl_anual=None if motivos["teto"] else cap.capacidade.teto,
            capacidade_restante_anual=None if motivos["restante"] else restante,
            aporte_mensal=None if motivos["aporte"] else restante / Decimal("12"),
            aliquota_marginal=None if economia is None else self._aliquota(cap),
            economia_ir_anual=economia,
        )

    # Reter prescrição não é apagar fato: a capacidade de 12% vem do IRPF e não
    # depende do regime do ano corrente. O que sai são os dois campos que a
    # ADR-375 D4 nomeia — "prescrever PGBL" (aporte) e "publicar economia de IR".
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
        return economia_diferencial(
            cap.renda_tributavel_anual, cap.capacidade.restante, self._config.irpf_faixas
        )

    def _aliquota(self, cap: CapacidadePgblIRPF) -> float:
        return self._aliquota_para(_cents(cap.renda_tributavel_anual))

    def _aliquota_para(self, base_calculo_anual_brl_cents: int) -> float:
        """Alíquota marginal; sem tabela configurada, degrada para o fallback declarado."""
        # A degradação por ausência de tabela é política do chamador, não da regra:
        # o service recusa tabela vazia porque resolver faixa sem faixas é erro de
        # config. Publicar prescrição sobre esse fallback é o que a ADR-375 D4 fecha.
        faixas = self._config.irpf_faixas
        if not faixas:
            return self._config.aliquota_fallback
        return float(resolve_faixa_marginal(base_calculo_anual_brl_cents, faixas))
