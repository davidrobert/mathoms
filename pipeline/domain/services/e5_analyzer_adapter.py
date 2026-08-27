"""E5AnalyzerAdapter — orquestra a análise financeira do E5 sobre ``ArtifactStore``
(Sessão A5c · Fase 8 foundation).

Compõe os domain services extraídos em A1/A3c/A5a/A5b/A5c:

- :func:`resolve_members` ([[ADR-410]] D1) — produtor único de titular/cônjuge.
- :class:`MemberAnalyzer` (A3c) — patrimônio por membro (helpers).
- :class:`PatrimonioCalculator` (A1) — patrimônio consolidado.
- :class:`EmergencyReserveCalculator` (A1) — reserva emergência.
- :class:`FinancialScoreCalculator` (A1) — score.
- :class:`CashFlowAggregator` (A1) — fluxo base.
- :class:`FluxoCaixaEnricher` (A5c) — fluxo enriquecido.
- :class:`IFProjector` (A5a) — projeção IF.
- :class:`RatiosCalculator` (A5a) — ratios.
- :class:`OrcamentoProspectivoCalculator` (A5a) — orçamento.
- :class:`EndividamentoAnalyzer` (A5b) — endividamento.
- :class:`PrevidenciaAnalyzer` (A5b) — PGBL.
- :class:`InvestimentosClassesAnalyzer` (A5b) — classes de ativo.
- :class:`ConsumoConscienteCalculator` (A5b) — gastos pontuais.
- :class:`DiagnosticoComportamentalAnalyzer` (A5c) — diagnósticos.
- :class:`PontosFortesAnalyzer` (A5c) — pontos fortes.
- :class:`PontosUrgentesAnalyzer` (A5c) — ações urgentes.
- :class:`EquilibrioCerbasiAnalyzer` (A5c) — equilíbrio presente/futuro.
- :class:`CenariosConjugeAnalyzer` (A5c) — cenários de trajetória.

**Escopo desta foundation**: o adapter fornece uma API unificada para o
``main_with_store`` de A5d — **não escreve em E5 ainda**. Retorna um
:class:`E5AnalysisResult` com todos os sub-resultados tipados.

Services que exigem config externa (``IFProjector``, ``PrevidenciaAnalyzer``,
etc.) recebem a config na factory :meth:`from_configs`; services sem config
externa (``RatiosCalculator``, ``OrcamentoProspectivoCalculator``...) são
instanciados com defaults.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from pipeline.artifact_store import ArtifactStore
from pipeline.domain.protection_bundle import ProtectionBundle
from pipeline.domain.services.carteira_por_papel import build_carteira_por_papel
from pipeline.domain.services.cenarios_conjuge_analyzer import (
    CenariosConjugeAnalyzer,
    CenariosConjugeConfig,
    CenariosConjugeResult,
)
from pipeline.domain.services.composicao_familiar import build_composicao_familiar
from pipeline.domain.services.consumo_consciente_calculator import (
    ConsumoConsciente,
    ConsumoConscienteCalculator,
    ConsumoConscienteConfig,
)
from pipeline.domain.services.conversao_me import (
    ConversaoMeBrl,
    HardcodedFxDefault,
    apply_fx,
    identity_already_brl,
    resolve_fx_input,
    warn_hardcoded,
)
from pipeline.domain.services.diagnostico_comportamental_analyzer import (
    DiagnosticoComportamentalAnalyzer,
    DiagnosticoComportamentalConfig,
    DiagnosticoItem,
)
from pipeline.domain.services.e5_lineage import build_e5_lineage
from pipeline.domain.services.endividamento_analyzer import (
    EndividamentoAnalysis,
    EndividamentoAnalyzer,
)
from pipeline.domain.services.equilibrio_cerbasi_analyzer import (
    EquilibrioCerbasi,
    EquilibrioCerbasiAnalyzer,
    EquilibrioCerbasiConfig,
)
from pipeline.domain.services.exposicao_cambial_analyzer import (
    ExposicaoCambialResult,
    compute_exposicao_cambial,
)
from pipeline.domain.services.financial_score_calculator import (
    FinancialScoreCalculator,
    FinancialScoreConfig,
)
from pipeline.domain.services.fiscal_source import (
    FiscalSource,
    InformeProventosSummary,
    ProventosRendaAnual,
)
from pipeline.domain.services.fluxo_caixa_enricher import (
    FluxoCaixaEnriched,
    FluxoCaixaEnricher,
    FluxoEnricherConfig,
)
from pipeline.domain.services.fonte_precedencia_arbiter import (
    arbitrar_frescor,
    fontes_de_irpf,
    fontes_de_posicoes_atuais,
)
from pipeline.domain.services.if_monte_carlo import (
    IFMonteCarloConfig,
    MonteCarloIFResult,
    PrazoDeclarado,
    run_monte_carlo_if,
)
from pipeline.domain.services.if_projector import (
    IFProjection,
    IFProjector,
    IFProjectorConfig,
)
from pipeline.domain.services.informe_extrato_override import (
    ExtratoPosicao,
    apply_informe_override,
)
from pipeline.domain.services.instituicoes_por_membro_analyzer import (
    InstituicoesPorMembroAnalyzer,
    InstituicoesPorMembroConfig,
    InstituicoesPorMembroResult,
)
from pipeline.domain.services.investimentos_classes_analyzer import (
    InvestimentosClassesAnalysis,
    InvestimentosClassesAnalyzer,
    InvestimentosClassesConfig,
)
from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer, partition_irpf_payloads
from pipeline.domain.services.irpf_completude import resolve_ano_base_fiscal
from pipeline.domain.services.orcamento_calculator import (
    OrcamentoProspectivo,
    OrcamentoProspectivoCalculator,
)
from pipeline.domain.services.passive_income_calculator import (
    DistribuicaoPJSignal,
    PassiveIncomeCalculator,
    PassiveIncomeConfig,
    PassiveIncomeResult,
)
from pipeline.domain.services.patrimonio_calculator import PatrimonioCalculator
from pipeline.domain.services.patrimonio_resolvers import resolve_members
from pipeline.domain.services.patrimonio_types import (
    CaixaContaExcluida,
    CaixaDetalhe,
    MemberIdentity,
    MembrosResolvidos,
    PatrimonioConfig,
    PatrimonioInputs,
    normalize_data_referencia,
    safe_float,
)
from pipeline.domain.services.pontos_fortes_analyzer import (
    PontoForteItem,
    PontosFortesAnalyzer,
    PontosFortesConfig,
)
from pipeline.domain.services.pontos_urgentes_analyzer import (
    PontosUrgentesAnalyzer,
    PontosUrgentesConfig,
    PontoUrgenteItem,
)
from pipeline.domain.services.previdencia_analyzer import (
    CapacidadePgblIRPF,
    PrevidenciaAnalysis,
    PrevidenciaAnalyzer,
    PrevidenciaConfig,
)
from pipeline.domain.services.protecao_analyzer import FamilyMemberSnapshot
from pipeline.domain.services.protecao_wiring import (
    ProtecaoSources,
    compute_protecao_via_store,
    family_snapshots_from_config,
)
from pipeline.domain.services.ratios_calculator import (
    FinancialRatios,
    RatiosCalculator,
    RentabilidadeConfig,
)
from pipeline.domain.services.reserva_emergencia_calculator import (
    EmergencyReserveCalculator,
    ReservaEmergenciaConfig,
)
from pipeline.domain.services.reserva_liquidez import FallbackIrpfPorPapel
from pipeline.domain.services.top_ativos_analyzer import (
    TopAtivosAnalyzer,
    TopAtivosConfig,
    TopAtivosResult,
)
from pipeline.domain.types.config import FiscalParameters

# =============================================================================
# Stage keys
# =============================================================================


_E4_RECEITAS_KEY = "receitas"
_E4_DESPESAS_KEY = "despesas"
_E4_FLUXO_KEY = "fluxo_mensal_detalhado"
_E4_PATRIMONIO_KEY = "patrimonio"
_E4_INVESTIMENTOS_KEY = "investimentos"
_IRPF_FULL_STAGE = "extract_irpf_full"

_logger = logging.getLogger("mathoms.pipeline.e5")


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class E5AnalysisResult:
    """Output agregado do ``E5AnalyzerAdapter.analyze_via_store``.

    Contém todos os sub-resultados tipados. O serializer legado (A5d)
    consome este objeto para produzir ``analise_financeira-5_analysis.json``.
    """

    # Inputs resolvidos.
    members: MembrosResolvidos
    receitas: dict[str, Any]
    despesas: dict[str, Any]
    fluxo_mensal_raw: dict[str, Any]
    patrimonio_raw: dict[str, Any]
    investimentos_raw: dict[str, Any]

    # Fluxo enriquecido (A5c).
    fluxo_enriched: FluxoCaixaEnriched

    # Patrimônio / Reserva / Score (A6d.3.3 — full-fidelity dicts com paridade
    # ao legado ``analyze_patrimonio`` / ``analyze_reserva_emergencia`` /
    # ``calculate_score``). Chaves dinâmicas baseadas em ``MemberIdentity``.
    patrimonio_full: dict[str, Any]
    reserva: dict[str, Any]
    score: dict[str, Any]

    # Análises.
    if_projection: IFProjection | None
    ratios: FinancialRatios
    orcamento: OrcamentoProspectivo
    endividamento: EndividamentoAnalysis
    previdencia: PrevidenciaAnalysis
    investimentos_classes: InvestimentosClassesAnalysis
    consumo_consciente: ConsumoConsciente
    equilibrio_cerbasi: EquilibrioCerbasi
    cenarios_conjuge: CenariosConjugeResult | None
    diagnosticos: tuple[DiagnosticoItem, ...]
    diagnostico_confianca: dict[str, str | float]
    pontos_fortes: tuple[PontoForteItem, ...]
    pontos_urgentes: tuple[PontoUrgenteItem, ...]
    # A8.3 — TRS efetiva + carteira de renda (None quando workspace sem IRPF
    # extract_irpf_full artifact; status `"sem_irpf"` ou `"gerador_zero"`
    # quando IRPF presente mas inputs insuficientes — UI do S7 trata cada
    # caso com empty state específico).
    passive_income: PassiveIncomeResult | None = None
    # N3 — Monte Carlo IF com cone P10/P50/P90 (None quando if_projection é None).
    monte_carlo_if: MonteCarloIFResult | None = None
    # Top 15 ativos individuais (companion de investimentos_classes). None
    # quando o analyzer não foi injetado (paridade legacy).
    top_ativos: TopAtivosResult | None = None
    # Instituições agrupadas por membro + total de imóveis. Companion de
    # investimentos_classes; substitui leitura legacy de E4 disk artifacts.
    instituicoes_por_membro: InstituicoesPorMembroResult | None = None
    # Bloco G plan RESIDENCIA_E_USO: agregação de patrimônio com lastro em
    # moeda estrangeira (caixa USD/EUR + ativos classificados "Internacional"
    # por ADR-193). Consumido pelo Card "Exposição Cambial" no relatório.
    exposicao_cambial: ExposicaoCambialResult | None = None
    # ADR-279 (A24.l5/l6): bloco ``_lineage`` field-level (patrimônio +
    # reserva + despesa total + total investido), anexado ao output em
    # ``e5_serialization.build_e5_output``.
    lineage: dict[str, Any] | None = None
    # A17 L4 (ADR-238 §L4): yield-on-cost por (ticker, ano_base) dos informes
    # proventos_acoes lidos de ``extract_informes_anuais``. None quando o
    # workspace não tem informes de proventos.
    proventos_por_ativo: tuple[InformeProventosSummary, ...] | None = None
    # A28.l6 (ADR-240 D8): payload ``protecao_patrimonial`` — apólices de
    # ``extract_comprovantes_bens`` alimentam ``compute_protecao``. Sempre
    # presente (workspace sem apólice = KPIs zerados + gap qualitativo,
    # cenário G6-b).
    protecao_patrimonial: dict[str, Any] | None = None
    # PE-3 (r7): cadastro civil do domicílio (papel + faixa etária em
    # ``faixa_ref``). Par do lado fiscal ``irpf_kpis.dependentes`` — sem ele o
    # parecer emitia os dois fatos da mesma família sem reconciliar. ``None``
    # quando o workspace não declara membros.
    composicao_familiar: dict[str, Any] | None = None


# =============================================================================
# Adapter
# =============================================================================


class E5AnalyzerAdapter:
    """Orquestra análise financeira E5 sobre ``ArtifactStore``.

    **Não escreve** em ``E5`` — apenas lê E4 artifacts, compõe os services
    e retorna :class:`E5AnalysisResult`. Escrita fica para ``main_with_store``
    em A5d, que acopla um ``e5_serialization``.

    Todas as dependências são injetáveis (R9/ISP); defaults são seguros.
    Services que exigem config externa obrigatória (``IFProjector``,
    ``CenariosConjugeAnalyzer``) são opcionais — quando ``None``, a análise
    correspondente no resultado vira ``None``.
    """

    def __init__(
        self,
        *,
        member_identity: MemberIdentity | None = None,
        patrimonio_calculator: PatrimonioCalculator | None = None,
        reserva_calculator: EmergencyReserveCalculator | None = None,
        score_calculator: FinancialScoreCalculator | None = None,
        taxas: dict | None = None,
        cambio_usd_brl: Decimal | float | None = None,
        cambio_eur_brl: Decimal | float | None = None,
        cambio_observed_at: dict[str, str] | None = None,
        fluxo_enricher: FluxoCaixaEnricher | None = None,
        if_projector: IFProjector | None = None,
        if_projector_config: IFProjectorConfig | None = None,
        ratios_calculator: RatiosCalculator | None = None,
        orcamento_calculator: OrcamentoProspectivoCalculator | None = None,
        endividamento_analyzer: EndividamentoAnalyzer | None = None,
        previdencia_analyzer: PrevidenciaAnalyzer | None = None,
        investimentos_classes_analyzer: InvestimentosClassesAnalyzer | None = None,
        top_ativos_analyzer: TopAtivosAnalyzer | None = None,
        instituicoes_analyzer: InstituicoesPorMembroAnalyzer | None = None,
        consumo_calculator: ConsumoConscienteCalculator | None = None,
        equilibrio_analyzer: EquilibrioCerbasiAnalyzer | None = None,
        cenarios_analyzer: CenariosConjugeAnalyzer | None = None,
        diagnostico_analyzer: DiagnosticoComportamentalAnalyzer | None = None,
        pontos_fortes_analyzer: PontosFortesAnalyzer | None = None,
        pontos_urgentes_analyzer: PontosUrgentesAnalyzer | None = None,
        passive_income_calculator: PassiveIncomeCalculator | None = None,
        family_snapshots: tuple[FamilyMemberSnapshot, ...] = (),
        family_config: dict | None = None,
        reference_date: date | None = None,
        seguradoras_catalog: Mapping[str, str] | None = None,
        protection_bundle: ProtectionBundle | None = None,
        cnpj_raiz_to_code: Mapping[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._identity = member_identity or MemberIdentity(
            titular_key="david",
            conjuge_key="mariana",
            titular_nome="David",
            conjuge_nome="Mariana",
        )
        self._patrimonio = patrimonio_calculator or PatrimonioCalculator(
            PatrimonioConfig(members=self._identity)
        )
        self._reserva = reserva_calculator or EmergencyReserveCalculator(
            ReservaEmergenciaConfig(members=self._identity)
        )
        self._score = score_calculator or FinancialScoreCalculator(FinancialScoreConfig.default())
        self._taxas = taxas or {}
        self._cambio_usd_brl = float(cambio_usd_brl) if cambio_usd_brl is not None else None
        self._cambio_eur_brl = float(cambio_eur_brl) if cambio_eur_brl is not None else None
        # ADR-390 D2 — data da row de cotação usada, não a data do lookup.
        self._cambio_observed_at = dict(cambio_observed_at or {})
        # ADR-384 — resolvedor de identidade institucional (raiz de 8 dígitos →
        # code do catálogo); vazio degrada para o token de nome no matcher.
        self._cnpj_raiz_to_code = dict(cnpj_raiz_to_code or {})
        self._fluxo_enricher = fluxo_enricher or FluxoCaixaEnricher()
        self._if_projector = if_projector
        self._if_projector_config = if_projector_config
        self._ratios = ratios_calculator or RatiosCalculator()
        self._orcamento = orcamento_calculator or OrcamentoProspectivoCalculator()
        self._endividamento = endividamento_analyzer or EndividamentoAnalyzer()
        self._previdencia = previdencia_analyzer or PrevidenciaAnalyzer()
        self._inv_classes = investimentos_classes_analyzer or InvestimentosClassesAnalyzer()
        self._top_ativos = top_ativos_analyzer or TopAtivosAnalyzer()
        self._instituicoes = instituicoes_analyzer or InstituicoesPorMembroAnalyzer()
        self._consumo = consumo_calculator or ConsumoConscienteCalculator()
        self._equilibrio = equilibrio_analyzer or EquilibrioCerbasiAnalyzer()
        self._cenarios = cenarios_analyzer
        self._diagnostico = diagnostico_analyzer or DiagnosticoComportamentalAnalyzer()
        self._pontos_fortes = pontos_fortes_analyzer or PontosFortesAnalyzer()
        self._pontos_urgentes = pontos_urgentes_analyzer or PontosUrgentesAnalyzer()
        self._passive_income = passive_income_calculator or PassiveIncomeCalculator(
            PassiveIncomeConfig()
        )
        self._family_snapshots = family_snapshots
        # PE-3: as faixas etárias são recortadas em 31/12 do ano-base fiscal, que
        # só se resolve com o store em mãos — daí reter a config e não só os
        # snapshots, cujas idades já foram fixadas em ``reference_date``.
        self._family_config = family_config
        self._reference_date = reference_date or date.today()
        # A37.l11 — canonicalização de seguradora no bloco de proteção.
        self._seguradoras_catalog = dict(seguradoras_catalog or {})
        # ADR-240 §Emenda 2026-08-08 — apólices cadastradas decidem ausência de
        # cobertura junto com as extraídas. `None` degrada para só-documento.
        self._protection_bundle = protection_bundle

    # -- Factory --

    @classmethod
    def from_configs(
        cls,
        *,
        categorization: dict | None = None,
        family: dict | None = None,
        scoring: dict | None = None,
        goals: dict | None = None,
        fiscal: dict | None = None,
        taxas: dict | None = None,
        titular_dob: date | None = None,
        conjuge_dob: date | None = None,
        reference_date: date | None = None,
        fiscal_parameters: FiscalParameters | None = None,
        cambio_usd_brl: Decimal | float | None = None,
        cambio_eur_brl: Decimal | float | None = None,
        cambio_observed_at: dict[str, str] | None = None,
        property_classification_overrides: dict[str, str] | None = None,
        imoveis_no_if: bool = True,
        seguradoras_catalog: Mapping[str, str] | None = None,
        protection_bundle: ProtectionBundle | None = None,
        cnpj_raiz_to_code: Mapping[str, tuple[str, ...]] | None = None,
    ) -> "E5AnalyzerAdapter":
        """Constrói o adapter com todas as configs + services instanciados.

        ``titular_dob`` é obrigatório para ``IFProjector`` e
        ``CenariosConjugeAnalyzer`` — quando ``None``, esses dois services
        são desabilitados (o resultado terá ``if_projection=None`` e
        ``cenarios_conjuge=None``).

        ``taxas`` fornece câmbios USD/EUR para valoração de caixa em ME.

        A7.2b: ``fiscal_parameters`` (typed) tem prioridade sobre ``fiscal``
        (dict legacy). ``cambio_usd_brl`` / ``cambio_eur_brl`` (Decimal)
        têm prioridade sobre ``taxas["cambio_usd_brl"]`` / ``taxas["cambio_eur_brl"]``.
        Quando ambos None, USD/EUR usam HardcodedFxDefault nomeado
        (ADR-390 D3) — pos-A7.5, sem fallback de disco.
        """
        identity = MemberIdentity.from_family(family)
        # ADR-215 §1: classificação user-driven em `workspace_property_overrides`
        # (gravado via UI P5 / endpoint P4) é fonte ÚNICA. Adapter extrai o
        # subset `residencia_principal` em `residencia_property_ids` para os
        # analyzers downstream (top_ativos, classes, instituicoes, members)
        # que precisam apenas saber "qual imóvel é a residência".
        overrides = property_classification_overrides or {}
        residencia_property_ids = frozenset(
            pid for pid, cls_ in overrides.items() if cls_ == "residencia_principal"
        )
        patrimonio_cfg = PatrimonioConfig(
            members=identity,
            property_classification_overrides=overrides,
            include_real_estate_in_if=imoveis_no_if,
        )
        reserva_cfg = ReservaEmergenciaConfig.from_scoring_json(scoring or {}, identity)
        score_cfg = FinancialScoreConfig.from_scoring_json(scoring or {})

        if_projector: IFProjector | None = None
        if_projector_config_built: IFProjectorConfig | None = None
        if titular_dob is not None and goals:
            try:
                if_cfg = IFProjectorConfig.from_configs(
                    goals=goals,
                    titular_dob=titular_dob,
                    conjuge_dob=conjuge_dob,
                    reference_date=reference_date,
                    titular_key=identity.titular_key,
                    conjuge_key=identity.conjuge_key,
                )
                if_projector = IFProjector(if_cfg)
                if_projector_config_built = if_cfg
            except ValueError:
                if_projector = None

        cenarios_analyzer: CenariosConjugeAnalyzer | None = None
        if titular_dob is not None:
            # Paridade com legado: quando family_members.json não declara
            # cônjuge, ``conjuge_key``/``conjuge_nome`` ficam vazios — o que
            # reflete nas chaves ``salario__clt_brl`` etc. Não impomos
            # default ``"mariana"`` aqui para preservar o output do legado.
            # ADR-167 (A8.4 PR2): analyzer simplificado — sem dependência de
            # USD/cambio. ``taxas``/``cambio_usd_brl`` deixam de fluir aqui.
            cenarios_cfg = CenariosConjugeConfig.from_configs(
                goals=goals,
                titular_dob=titular_dob,
                titular_key=identity.titular_key,
                conjuge_key=identity.conjuge_key,
                conjuge_nome=(identity.conjuge_key or "").title(),
                reference_date=reference_date,
            )
            cenarios_analyzer = CenariosConjugeAnalyzer(cenarios_cfg)

        return cls(
            member_identity=identity,
            patrimonio_calculator=PatrimonioCalculator(patrimonio_cfg),
            reserva_calculator=EmergencyReserveCalculator(reserva_cfg),
            score_calculator=FinancialScoreCalculator(score_cfg),
            taxas=taxas,
            cambio_usd_brl=cambio_usd_brl,
            cambio_eur_brl=cambio_eur_brl,
            cambio_observed_at=cambio_observed_at,
            fluxo_enricher=FluxoCaixaEnricher(
                FluxoEnricherConfig.from_configs(categorization=categorization, scoring=scoring)
            ),
            if_projector=if_projector,
            if_projector_config=if_projector_config_built,
            endividamento_analyzer=EndividamentoAnalyzer(),
            previdencia_analyzer=PrevidenciaAnalyzer(
                PrevidenciaConfig.from_fiscal_parameters(fiscal_parameters)
                if fiscal_parameters is not None
                else PrevidenciaConfig.from_fiscal(fiscal)
            ),
            investimentos_classes_analyzer=InvestimentosClassesAnalyzer(
                InvestimentosClassesConfig.from_configs(
                    scoring=scoring, residencia_property_ids=residencia_property_ids
                )
            ),
            top_ativos_analyzer=TopAtivosAnalyzer(
                TopAtivosConfig.from_configs(
                    scoring=scoring, residencia_property_ids=residencia_property_ids
                )
            ),
            instituicoes_analyzer=InstituicoesPorMembroAnalyzer(
                InstituicoesPorMembroConfig.from_configs(
                    residencia_property_ids=residencia_property_ids
                )
            ),
            consumo_calculator=ConsumoConscienteCalculator(
                ConsumoConscienteConfig.from_configs(scoring=scoring, goals=goals)
            ),
            equilibrio_analyzer=EquilibrioCerbasiAnalyzer(
                EquilibrioCerbasiConfig.from_scoring(scoring)
            ),
            cenarios_analyzer=cenarios_analyzer,
            diagnostico_analyzer=DiagnosticoComportamentalAnalyzer(
                DiagnosticoComportamentalConfig.from_scoring(scoring)
            ),
            pontos_fortes_analyzer=PontosFortesAnalyzer(PontosFortesConfig.from_scoring(scoring)),
            pontos_urgentes_analyzer=PontosUrgentesAnalyzer(
                PontosUrgentesConfig.from_scoring(scoring)
            ),
            passive_income_calculator=PassiveIncomeCalculator(PassiveIncomeConfig()),
            family_snapshots=family_snapshots_from_config(family, reference_date or date.today()),
            family_config=family,
            reference_date=reference_date,
            seguradoras_catalog=seguradoras_catalog,
            protection_bundle=protection_bundle,
            cnpj_raiz_to_code=cnpj_raiz_to_code,
        )

    # -- API --

    def analyze_via_store(self, store: ArtifactStore) -> E5AnalysisResult:
        """Lê E4+E3 do store, compõe análises e retorna ``E5AnalysisResult``.

        **Não escreve em E5.** Escrita fica para ``main_with_store`` (A5d).

        Diferente da foundation A5c, esta versão (A6d.3.3) usa os três
        calculadores puros (``PatrimonioCalculator``, ``EmergencyReserveCalculator``,
        ``FinancialScoreCalculator``) — zero placeholders.
        """
        # 1. Inputs do E4.
        receitas = store.read("categorize_transactions", _E4_RECEITAS_KEY) or {}
        despesas = store.read("categorize_transactions", _E4_DESPESAS_KEY) or {}
        fluxo_mensal = store.read("categorize_transactions", _E4_FLUXO_KEY) or {}
        patrimonio_raw = store.read("categorize_transactions", _E4_PATRIMONIO_KEY) or {}
        investimentos_raw = store.read("categorize_transactions", _E4_INVESTIMENTOS_KEY) or {}
        # Produtor único do eixo B ([[ADR-412]] §D3): particiona uma vez e é
        # injetado; nenhum consumidor resolve titularidade por dentro.
        carteira = build_carteira_por_papel(
            investimentos_raw,
            titular_key=self._identity.titular_key,
            conjuge_key=self._identity.conjuge_key,
        )

        # 2. Resolve membros do baseline — produtor único ([[ADR-410]] D1).
        members = resolve_members(patrimonio_raw, self._identity)
        titular_data, conjuge_data = members.as_tuple()

        # 3. Enriquece fluxo. `data_corte` vem do `reference_date` do run (nunca de
        #    `date.today()` no ponto de uso): transação posterior sai dos agregados
        #    realizados e vira `fluxo_caixa.provisionado`.
        fluxo_enriched = self._fluxo_enricher.enrich(
            receitas=receitas,
            despesas=despesas,
            fluxo_mensal=fluxo_mensal,
            data_corte=self._reference_date,
        )
        fluxo_legacy = fluxo_enriched.to_legacy_dict()

        # 4. Caixa E3 (shell: lê tudo que está em E3 via store).
        # ADR-245: fallback baseline IRPF quando não há extrato USD/EUR em E3.
        caixa_total, caixa_detalhes, caixa_exclusoes = self._load_caixa_from_e3(
            store, baseline=patrimonio_raw
        )

        # 5. Patrimônio completo (paridade com ``analyze_patrimonio`` legacy).
        patrimonio_full = self._patrimonio.calculate(
            PatrimonioInputs(
                baseline=patrimonio_raw,
                members=members,
                investimentos_atuais=investimentos_raw,
                carteira=carteira,
                caixa_total_brl=caixa_total,
                caixa_detalhes=caixa_detalhes,
            )
        )
        # ADR-376 §4 — exclusões de caixa com razão tipada, visíveis no payload.
        patrimonio_full["caixa_exclusoes"] = [exc.to_dict() for exc in caixa_exclusoes]
        # ADR-383 §5 — árbitro de frescor em fase OBSERVACIONAL: emite veredito
        # e contradições SEM alterar nenhum valor consumido pelo PL. O flip
        # (PR-b da A40.l41) só ocorre após medir o efeito no dogfood real.
        patrimonio_full["frescor_fontes"] = self._veredito_frescor(
            patrimonio_raw, investimentos_raw
        )

        # 6a. IRPF + passive income (carteira de renda + TRS efetiva · A8.3).
        # A33.l4: informes anuais carregados 1× — alimentam os buckets
        # dividendos/jcp (D4 bucket-fill) e o per-ativo de S3.
        irpf_analyzer = _try_load_irpf_analyzer(store)
        fiscal_informes = FiscalSource.from_informes(_try_load_informes(store))
        passive_income = self._compute_passive_income(
            irpf_analyzer,
            patrimonio_full,
            investimentos_raw,
            fluxo_legacy,
            proventos=fiscal_informes.proventos_renda_por_ano(),
        )

        # 6b. Ratios (consome ``bruto``/``dividas``/``investivel`` do dict full).
        ratios_result = self._ratios.calculate(
            fluxo_legacy,
            patrimonio_full,
            passive_income=passive_income,
            irpf=irpf_analyzer,
        )
        ratios_dict = ratios_result.to_legacy_dict()

        # 7. IF projection — ADR-142 + ADR-215 §6 enforce: usa
        # ``investivel_efetivo`` (cat_3+4+5+6 + cat_2 geradores se toggle).
        if_projection: IFProjection | None = None
        if self._if_projector is not None:
            if_projection = self._if_projector.project(
                investivel=float(patrimonio_full.get("investivel_efetivo", 0)),
                renda_passiva_fora_do_investivel_mensal=_renda_passiva_fora_do_investivel(
                    patrimonio_full, passive_income
                ),
            )

        # 7b. Monte Carlo IF — cone de cenários (N3).
        monte_carlo_if: MonteCarloIFResult | None = None
        if if_projection is not None and self._if_projector_config is not None:
            _cfg = self._if_projector_config
            _investivel = float(patrimonio_full.get("investivel_efetivo", 0))
            _mc_cfg = IFMonteCarloConfig(
                patrimonio_investivel=Decimal(str(max(0.0, _investivel))),
                meta_if=Decimal(str(max(0.0, _cfg.if_meta))),
                retorno_real_esperado=_cfg.retorno_real_anual_pct / 100.0,
                aporte_mensal=Decimal(str(max(0.0, _cfg.aporte_mensal))),
            )
            monte_carlo_if = run_monte_carlo_if(
                _mc_cfg,
                ano_base=self._reference_date.year,
                prazo_declarado=_prazo_declarado_do_goal(_cfg),
            )

        # 8. Reserva emergência (FORMULAS.md §Reserva · A28.l1) — item-level
        #    para o filtro de liquidez (posições atuais > IRPF bens).
        reserva = self._reserva.calculate(
            fluxo=fluxo_legacy,
            patrimonio=patrimonio_full,
            carteira=carteira,
            # O eixo B não substitui o IRPF: no dogfood o balde do cônjuge vem
            # inteiramente daqui, e tratar a carteira como resposta completa o
            # zeraria — com a identidade de conservação fechando mesmo assim.
            fallback_irpf=FallbackIrpfPorPapel(
                titular=titular_data,
                conjuge=conjuge_data if self._identity.conjuge_key else None,
            ),
        )

        # 9. Score (paridade com ``calculate_score``) — cobertura_despesas lê
        #    a reserva canônica (FORMULAS.md §Reserva · A28.l1).
        score_goals = {"if_pct": if_projection.if_pct if if_projection else 0.0}
        score = self._score.calculate(
            ratios=ratios_dict,
            patrimonio=patrimonio_full,
            goals=score_goals,
            fluxo=fluxo_legacy,
            reserva=reserva,
        )

        # 10. Orcamento prospectivo.
        num_months = len(fluxo_legacy.get("receita_despesa_mensal_detalhado", {}).get("labels", []))
        orcamento = self._orcamento.calculate(
            fluxo_legacy.get("despesas_por_categoria", {}),
            num_months=num_months,
        )

        # 11. Endividamento — item é a DÍVIDA do baseline (ADR-301/ADR-401), não
        #     "um membro que tem dívida". `endiv_members` só alimenta o fallback
        #     de baseline sem itemização; o nome de exibição sai em `membro`,
        #     campo tipado, nunca embutido na descrição.
        endiv_members = [
            {"nome": self._identity.titular_nome, "data": titular_data},
            {"nome": self._identity.conjuge_nome, "data": conjuge_data},
        ]
        endividamento = self._endividamento.analyze(
            patrimonio_full,
            endiv_members,
            dividas_baseline=(patrimonio_raw or {}).get("dividas"),
            ano_ref=None,
            identity=self._identity,
        )

        # 12. Previdência — ancora na capacidade PGBL restante do IRPF do
        #     titular quando há declaração (ADR-277, INV-PREV-3); sem IRPF,
        #     o analyzer cai no proxy de receita PJ.
        capacidade_pgbl = _build_capacidade_pgbl(irpf_analyzer)
        previdencia = self._previdencia.analyze(fluxo_legacy, capacidade_irpf=capacidade_pgbl)

        # 13. Investimentos por classe + Top 15 ativos + instituições por membro.
        #     Usa nomes de exibição (titular_nome/conjuge_nome) — paridade com
        #     endividamento (linhas 552-554). O campo ``membro`` no JSON sai
        #     como "David"/"Mariana" (de ``family_members.nome_curto``), não
        #     como o key cru "david_robert_..." — relatório consome direto.
        titular_bens = titular_data.get("bens") or titular_data
        conjuge_bens = conjuge_data.get("bens") or conjuge_data
        bens_list = [titular_bens, conjuge_bens]
        bens_por_membro = [
            (self._identity.titular_nome, titular_bens),
            (self._identity.conjuge_nome, conjuge_bens),
        ]
        investimentos_classes = self._inv_classes.analyze(bens_list)
        top_ativos = self._top_ativos.analyze(bens_por_membro)
        instituicoes = self._instituicoes.analyze(bens_por_membro)

        # 14. Consumo consciente.
        consumo = self._consumo.calculate(fluxo_legacy, despesas)

        # 15. Equilibrio Cerbasi.
        equilibrio = self._equilibrio.analyze(fluxo_legacy)

        # 16. Cenarios conjuge (se disponível).
        cenarios: CenariosConjugeResult | None = None
        if self._cenarios is not None and if_projection is not None:
            cenarios = self._cenarios.analyze(
                patrimonio=patrimonio_full,
                goals={"if_meta": if_projection.if_meta},
                fluxo=fluxo_legacy,
            )

        # 17. Diagnósticos comportamentais + confiança por cobertura (ADR-353).
        diagnosticos = self._diagnostico.analyze(fluxo_legacy, ratios_dict)
        diagnostico_confianca = self._diagnostico.confianca(fluxo_legacy)

        # 18. Pontos fortes + urgentes (agora com score/reserva REAIS).
        #     FP-002: passamos `goals={"if_pct": ...}` para o analyzer
        #     ativar o ponto forte "Caminho para Independência Financeira"
        #     (cobertura ≥ 20%). Anteriormente passava `{}` por paridade
        #     com legado bug — analyzer agora aceita `if_pct` (alias
        #     defensivo cobre `progresso_pct` também).
        pontos_fortes_goals = {"if_pct": if_projection.if_pct} if if_projection is not None else {}
        pontos_fortes = self._pontos_fortes.analyze(
            score=score,
            ratios=ratios_dict,
            patrimonio=patrimonio_full,
            fluxo=fluxo_legacy,
            reserva=reserva,
            goals=pontos_fortes_goals,
        )
        # 18b. Proteção patrimonial (A28.l6 — ativa ADR-240): apólices do stage
        #      ``extract_comprovantes_bens`` → ``compute_protecao``. O payload
        #      condiciona o item de seguro em pontos_urgentes ("nenhuma apólice
        #      identificada" só quando não há apólice vigente alguma).
        protecao = compute_protecao_via_store(
            store,
            ProtecaoSources(
                irpf_analyzer=irpf_analyzer,
                patrimonio_full=patrimonio_full,
                fluxo_legacy=fluxo_legacy,
                fluxo_mensal_raw=fluxo_mensal,
            ),
            family_snapshots=self._family_snapshots,
            reference_date=self._reference_date,
            seguradoras_catalog=self._seguradoras_catalog,
            protection_bundle=self._protection_bundle,
        )
        pontos_urgentes = self._pontos_urgentes.analyze(
            ratios_dict, reserva, patrimonio_full, protecao=protecao
        )

        # Bloco G — exposição cambial: caixa em moeda estrangeira + ativos
        # com lastro internacional (ADR-193 bucket "Internacional"). Denominador
        # é `investivel_financeiro` ou fallback para `investivel` legacy se
        # rodando pré-ADR-142 runtime.
        _investivel_denom = float(
            patrimonio_full.get("investivel_financeiro") or patrimonio_full.get("investivel") or 0
        )
        exposicao_cambial = compute_exposicao_cambial(
            caixa_detalhes=patrimonio_full.get("caixa_detalhes") or [],
            investimentos_atuais=investimentos_raw,
            investivel_financeiro=_investivel_denom,
        )

        return E5AnalysisResult(
            members=members,
            receitas=receitas,
            despesas=despesas,
            fluxo_mensal_raw=fluxo_mensal,
            patrimonio_raw=patrimonio_raw,
            investimentos_raw=investimentos_raw,
            fluxo_enriched=fluxo_enriched,
            patrimonio_full=patrimonio_full,
            reserva=reserva,
            score=score,
            if_projection=if_projection,
            ratios=ratios_result,
            orcamento=orcamento,
            endividamento=endividamento,
            previdencia=previdencia,
            investimentos_classes=investimentos_classes,
            top_ativos=top_ativos,
            instituicoes_por_membro=instituicoes,
            consumo_consciente=consumo,
            equilibrio_cerbasi=equilibrio,
            cenarios_conjuge=cenarios,
            diagnosticos=tuple(diagnosticos),
            diagnostico_confianca=diagnostico_confianca,
            pontos_fortes=tuple(pontos_fortes),
            pontos_urgentes=tuple(pontos_urgentes),
            passive_income=passive_income,
            monte_carlo_if=monte_carlo_if,
            proventos_por_ativo=tuple(fiscal_informes.proventos_summaries()) or None,
            exposicao_cambial=exposicao_cambial,
            protecao_patrimonial=protecao,
            composicao_familiar=self._composicao_familiar(irpf_analyzer),
            lineage=build_e5_lineage(
                patrimonio_report=patrimonio_full,
                reserva=reserva,
                fluxo_legacy=fluxo_legacy,
                investimentos_legacy=investimentos_classes.to_legacy_dict(),
                endividamento_legacy=endividamento.to_legacy_dict(),
                despesas_e4=despesas,
                identity=self._identity,
            ),
        )

    # -- Helpers de wiring --

    def _composicao_familiar(self, irpf: IRPFAnalyzer | None) -> dict[str, Any] | None:
        """Cadastro civil recortado em 31/12 do ano-base fiscal (PE-3)."""
        ref = _faixa_ref_fiscal(irpf, self._reference_date)
        snapshots = family_snapshots_from_config(self._family_config, ref)
        return build_composicao_familiar(snapshots, faixa_ref=ref.isoformat())

    def _compute_passive_income(
        self,
        irpf_analyzer: IRPFAnalyzer | None,
        patrimonio_full: dict,
        investimentos_raw: dict,
        fluxo_legacy: dict,
        *,
        proventos: tuple[ProventosRendaAnual, ...] = (),
    ) -> PassiveIncomeResult:
        """Wraps ``PassiveIncomeCalculator.calculate`` extraindo despesa do fluxo."""
        despesa = Decimal(str(fluxo_legacy.get("janela_12m", {}).get("despesa_mensal_media") or 0))
        return self._passive_income.calculate(
            irpf=irpf_analyzer,
            patrimonio=patrimonio_full,
            investimentos_atuais=investimentos_raw,
            reference_date=self._reference_date,
            despesa_mensal_media_brl=despesa,
            proventos=proventos,
            distribuicao_pj_signal=_distribuicao_pj_signal_from_fluxo(fluxo_legacy),
        )

    # ADR-383 (A40.l41) — fase observacional: o pool atual declarado é sempre
    # ``posicoes_atuais`` porque é o que `_compute_investimentos` prefere hoje
    # (fallback IRPF só quando o total do membro é zero).
    def _veredito_frescor(self, patrimonio_raw: dict, investimentos_raw: dict) -> dict:
        e4 = fontes_de_posicoes_atuais(investimentos_raw, membro_default=self._identity.titular_key)
        irpf = fontes_de_irpf(patrimonio_raw.get("investimentos_consolidados") or [])
        atual = {(f.instituicao, f.membro): "posicoes_atuais" for f in e4}
        veredito = arbitrar_frescor(
            e4 + irpf,
            data_alvo=self._reference_date.isoformat(),
            pool_atual_por_celula=atual,
        )
        for contradicao in veredito.contradicoes:
            _logger.warning(
                "mathoms.pipeline.e5.frescor_contradicao",
                extra={"contradicao": contradicao.to_dict()},
            )
        return veredito.to_payload()

    # -- Helper de I/O (shell) --

    def _load_caixa_from_e3(
        self,
        store: ArtifactStore,
        *,
        baseline: dict | None = None,
    ) -> tuple[float, list[CaixaDetalhe], list[CaixaContaExcluida]]:
        """Carrega saldos de caixa + moeda estrangeira de todos os E3 artifacts.

        Classificação (ADR-376 — caixa canônico, sem denylist de instituição):
            - Conta corrente BRL → ``caixa``
            - Moeda estrangeira (USD/EUR) → ``moeda_estrangeira`` (→ BRL via taxas)
            - Fatura → não é conta (skip categórico)
            - Poupança / PJ / saldo desconhecido → fora do caixa com razão
              tipada (``CaixaContaExcluida``, 1 por conta) — nada some em silêncio

        Cambio (ADR-390): typed ``self._cambio_usd_brl`` /
        ``self._cambio_eur_brl`` têm prioridade sobre ``self._taxas``. Sem
        os dois, USD/EUR usam ``HardcodedFxDefault`` nomeado + WARNING.

        ADR-245 — fallback baseline IRPF: quando nenhum extrato em USD/EUR
        está em E3, agrega items de moeda estrangeira de
        ``baseline.investimentos_consolidados`` (depósitos em ME, contas
        offshore). Trade-off conhecido: o item segue em
        ``investimentos_consolidados`` no patrimonio_calculator — se algum
        membro cair em fallback IRPF puro (``titular_val == 0``), pode
        haver double-count. Cobertura cirúrgica do caso comum.

        Sem keys em E3 (ou store sem list_keys) → fallback baseline apenas.
        """
        keys = (
            list(store.list_keys("reconcile_transactions")) if hasattr(store, "list_keys") else []
        )
        latest_per_account: dict[tuple[str, str, str, str], tuple[str, dict]] = {}
        excluidas_por_conta: dict[tuple[str, str, str, str], CaixaContaExcluida] = {}

        for key in keys:
            data = store.read("reconcile_transactions", key) or {}
            tipo_conta = (data.get("tipo_conta") or "").lower()
            banco = (data.get("banco") or "").lower()
            moeda = (data.get("moeda") or "BRL").upper()
            saldo_raw = data.get("saldo_final")
            titular = (data.get("titular") or "").lower()
            account_key = (banco, tipo_conta, moeda, titular)

            if "fatura" in tipo_conta:
                continue
            motivo = _motivo_exclusao_caixa(tipo_conta, saldo_raw, data)
            if motivo is not None:
                excluidas_por_conta.setdefault(
                    account_key,
                    CaixaContaExcluida(
                        banco=banco, tipo_conta=tipo_conta, moeda=moeda, motivo=motivo
                    ),
                )
                continue

            period_end = (data.get("periodo_cobertura") or {}).get("fim") or ""
            tiebreak = (period_end, key)
            prev = latest_per_account.get(account_key)
            if prev is None or tiebreak > prev[0]:
                latest_per_account[account_key] = (tiebreak, data)

        # Conta com artifact de saldo desconhecido mas outro com saldo válido
        # entra no caixa — a exclusão só vale se a conta ficou de fora mesmo.
        excluidas = [
            exc for k, exc in sorted(excluidas_por_conta.items()) if k not in latest_per_account
        ]

        total_brl = 0.0
        posicoes: list[ExtratoPosicao] = []
        has_foreign_in_e3 = False
        hardcoded_counts: dict[str, int] = {}
        for _, data in sorted(latest_per_account.values(), key=lambda x: x[0]):
            tipo_conta = (data.get("tipo_conta") or "").lower()
            moeda = (data.get("moeda") or "BRL").upper()
            saldo = safe_float(data.get("saldo_final"))
            conv, hardcoded = self._converter_extrato(saldo, moeda)
            if hardcoded is not None:
                hardcoded_counts[hardcoded.pair] = hardcoded_counts.get(hardcoded.pair, 0) + 1
            if moeda != "BRL":
                has_foreign_in_e3 = True
            if conv.valor_brl is not None:
                total_brl += float(conv.valor_brl)
            period_end = (data.get("periodo_cobertura") or {}).get("fim") or ""
            data_ref, precisao = normalize_data_referencia(period_end)
            posicoes.append(
                ExtratoPosicao(
                    detalhe=_detalhe_from_conv(
                        data, tipo_conta, moeda, saldo, conv, data_ref, precisao
                    ),
                    banco=(data.get("banco") or "").lower(),
                    period_end=period_end,
                )
            )
        for par, n_linhas in hardcoded_counts.items():
            warn_hardcoded(par, n_linhas)

        # ADR-238 D5 (A33.l2) — informe 31/12 vence extrato D+1: substitui o
        # saldo do extrato da virada de ano pelo do informe (fonte fiscal
        # certificada) e anota divergência relevante nos entries do baseline.
        override = apply_informe_override(
            posicoes,
            (baseline or {}).get("informe_pf_saldos_31_12") or [],
            cnpj_raiz_to_code=self._cnpj_raiz_to_code,
        )
        detalhes = override.detalhes
        total_brl += float(override.ajuste_total_brl)

        # ADR-245: fallback baseline IRPF para moeda estrangeira.
        if not has_foreign_in_e3 and baseline:
            me_total, me_detalhes = _extract_me_caixa_from_baseline(baseline)
            total_brl += me_total
            detalhes.extend(me_detalhes)

        return round(total_brl, 2), detalhes, excluidas

    def _converter_extrato(
        self, saldo, moeda: str
    ) -> tuple[ConversaoMeBrl, HardcodedFxDefault | None]:
        resolved = resolve_fx_input(
            moeda,
            typed_usd=self._cambio_usd_brl,
            typed_eur=self._cambio_eur_brl,
            taxas=self._taxas,
            observed_at=self._cambio_observed_at,
        )
        hardcoded = resolved if isinstance(resolved, HardcodedFxDefault) else None
        return apply_fx(saldo, moeda, resolved), hardcoded


def _detalhe_from_conv(
    data: dict, tipo_conta: str, moeda: str, saldo, conv: ConversaoMeBrl, data_ref, precisao: str
) -> CaixaDetalhe:
    valor = float(conv.valor_brl) if conv.valor_brl is not None else 0.0
    tipo = "moeda_estrangeira" if moeda != "BRL" else "caixa"
    return CaixaDetalhe(
        conta=f"{data.get('banco', '?')} ({tipo_conta})",
        moeda=moeda,
        saldo_original=saldo,
        valor_brl=valor,
        tipo=tipo,
        data_referencia=data_ref,
        data_referencia_precisao=precisao,
        conversao=conv,
    )


def _motivo_exclusao_caixa(tipo_conta: str, saldo_raw, data: dict) -> str | None:
    """Razão tipada de exclusão do caixa corrente (ADR-376 §4); ``None`` = elegível."""
    if "poupan" in tipo_conta:
        return "poupanca"
    if "pj" in tipo_conta:
        return "conta_pj"
    if saldo_raw is None or data.get("saldo_final_unknown", False):
        return "saldo_desconhecido"
    return None


# =============================================================================
# Helpers — fallback baseline IRPF para moeda estrangeira (ADR-245)
# =============================================================================


# Keywords reconhecidas em descrições do baseline IRPF que indicam caixa em ME.
# Baseado em rótulos canônicos do informe IR brasileiro: códigos 02
# ("Depósito em moeda...") e 99 ("Outros bens em moeda estrangeira").
_ME_KEYWORDS_USD: tuple[str, ...] = (
    "dolar",
    "u$",
    "us$",
    "usd",
)
_ME_KEYWORDS_EUR: tuple[str, ...] = (
    "euro",
    "eur",
)
_ME_KEYWORDS_GENERIC: tuple[str, ...] = (
    "moeda estrangeira",
    "deposito em moeda nacional decorrente de moeda",
    "moeda nacional decorrente",
)


# ADR-369 D2 — o alvo do Monte Carlo é o prazo que a FAMÍLIA declarou, ancorado
# em ano absoluto. Antes o adapter passava `if_projection.idade_titular_if`, a
# saída do projetor determinístico, e a métrica publicada media P(o modelo bater
# a data que ele mesmo imprimiu). Um teste por AST trava a expressão deste
# kwarg: asserção sobre o valor deixaria um refactor reintroduzir a derivação
# com o teste verde.
def _prazo_declarado_do_goal(cfg: IFProjectorConfig) -> PrazoDeclarado | None:
    """``None`` quando ninguém declarou prazo — o MC emite ausência com motivo."""
    if cfg.prazo_declarado_pendente or cfg.prazo_declarado_anos is None:
        return None
    if not cfg.prazo_declarado_em:
        return None
    return PrazoDeclarado(
        anos=cfg.prazo_declarado_anos,
        ano_alvo=int(cfg.prazo_declarado_em[:4]) + cfg.prazo_declarado_anos,
        declarado_em=cfg.prazo_declarado_em,
    )


def _distribuicao_pj_signal_from_fluxo(fluxo_legacy: dict) -> DistribuicaoPJSignal | None:
    # ADR-336: usa por_fonte["lucros_distribuidos"] (categoria — isolado, NÃO o agregado
    # receita_pj, que vazaria pró-labore) + janela_meses (janela cheia do fluxo).
    lucros = (fluxo_legacy.get("por_fonte", {}) or {}).get("lucros_distribuidos")
    if lucros is None:
        return None
    return DistribuicaoPJSignal(
        lucros_distribuidos_brl=Decimal(str(lucros)),
        janela_meses=int(fluxo_legacy.get("janela_meses") or 12),
    )


def _extract_me_caixa_from_baseline(baseline: dict) -> tuple[float, list[CaixaDetalhe]]:
    """Extrai items de moeda estrangeira de ``baseline.investimentos_consolidados``.

    O IRPF brasileiro classifica depósitos em ME sob código 02 (mesmo grupo
    de "Aplicação de renda fixa"). Sem extrato bancário reconciliado,
    esses items são a única fonte de saldo ME — esta função aceita o
    trade-off de leve duplicação com ``_investimentos_from_irpf`` (em
    cenários raros de fallback IRPF puro) em troca de visibilidade do
    saldo ME no card "Caixa e Moeda Estrangeira" (ADR-245 §Limitações).

    Valor IRPF já está em BRL. ``moeda`` é BRL (unidade de
    ``saldo_original``); keyword "dólar" não autoriza gravar BRL como USD
    (ADR-245 L3 emendada · ADR-390).
    """
    inv_list = baseline.get("investimentos_consolidados", []) or []
    if not isinstance(inv_list, list):
        return 0.0, []

    total_brl = 0.0
    detalhes: list[CaixaDetalhe] = []
    for item in inv_list:
        if not isinstance(item, dict):
            continue
        descricao = str(item.get("descricao", "") or "").lower()
        if not any(kw in descricao for kw in _ME_KEYWORDS_GENERIC) and not (
            any(kw in descricao for kw in _ME_KEYWORDS_USD)
            or any(kw in descricao for kw in _ME_KEYWORDS_EUR)
        ):
            continue

        valor = _resolve_valor_31_12(item)
        if valor <= 0:
            continue

        conv = identity_already_brl(valor)
        total_brl += valor
        detalhes.append(
            CaixaDetalhe(
                conta=f"IRPF: {(item.get('descricao') or '')[:80]}",
                moeda="BRL",
                saldo_original=valor,
                valor_brl=valor,
                tipo="moeda_estrangeira_irpf",
                fonte="baseline_irpf",
                conversao=conv,
            )
        )
    return total_brl, detalhes


def _resolve_valor_31_12(item: dict) -> float:
    """Lê valor agregado mais recente de ``valores_31_12`` ou ``valor``."""
    vals = item.get("valores_31_12") if isinstance(item, dict) else None
    if isinstance(vals, dict) and vals:
        latest_year = max(vals.keys())
        return safe_float(vals.get(latest_year, 0))
    return safe_float(item.get("valor", 0))


# [[ADR-418]] §D2 — o termo que a meta desconta: renda passiva de ativo que o
# numerador NÃO conta. Hoje o único eixo de exclusão é ``imoveis_no_if``; eixo novo
# entra AQUI, e eixo que não passe por aqui reabre a dupla-penalidade.
def _renda_passiva_fora_do_investivel(
    patrimonio_full: dict, passive_income: PassiveIncomeResult | None
) -> float:
    """Aluguel observado quando cat_2 está fora de ``investivel_efetivo``; senão ``0``."""
    if passive_income is None or passive_income.status != "ok":
        return 0.0
    if bool(patrimonio_full.get("imoveis_no_if", True)):
        return 0.0
    alugueis_anual = passive_income.renda_passiva_por_fonte_brl.get("alugueis")
    return float(alugueis_anual or 0) / 12.0


# =============================================================================
# Helpers de wiring A8.3 (IRPF + PassiveIncomeCalculator)
# =============================================================================


def _read_irpf_payloads_with_keys(
    store: ArtifactStore,
) -> tuple[list[dict], list[str]]:
    """Lê payloads E1.6 + retorna ``artifact_key`` de cada um (tie-break do dedup)."""
    try:
        keys = list(store.list_keys(_IRPF_FULL_STAGE))
    except Exception:
        return [], []
    pairs = [(k, store.read(_IRPF_FULL_STAGE, k)) for k in keys]
    filtered = [(k, p) for k, p in pairs if p]
    payloads, payload_keys, skipped = partition_irpf_payloads(
        [p for _, p in filtered], [k for k, _ in filtered]
    )
    for key, reason in skipped:
        _logger.warning("irpf_payload_skipped", extra={"artifact_key": key, "reason": reason})
    return payloads, payload_keys


def _try_load_informes(store: ArtifactStore) -> tuple[dict, ...]:
    """Payloads de ``extract_informes_anuais`` (graceful: store sem informes → ())."""
    if not hasattr(store, "list_keys"):
        return ()
    try:
        keys = list(store.list_keys("extract_informes_anuais"))
        return tuple(p for p in (store.read("extract_informes_anuais", k) for k in keys) if p)
    except Exception:
        return ()


def _try_load_proventos_summaries(
    store: ArtifactStore,
) -> tuple[InformeProventosSummary, ...] | None:
    """Yield por ativo dos informes proventos_acoes (A17 L4; graceful sem informes)."""
    summaries = FiscalSource.from_informes(_try_load_informes(store)).proventos_summaries()
    return tuple(summaries) or None


def _try_load_irpf_analyzer(store: ArtifactStore) -> IRPFAnalyzer | None:
    """Lê ``extract_irpf_full`` opcionalmente — paridade com ``_e5_load_irpf_kpis``.

    Dedup aplicado automaticamente em ``IRPFAnalyzer.from_payloads``; tie-break
    do dedup usa ``artifact_key`` (lexicográfico). Tie-break por ``created_at``
    fica para A-condicional (precisa extender ``ArtifactStore`` protocol).
    """
    payloads, tie_break_keys = _read_irpf_payloads_with_keys(store)
    if not payloads:
        return None
    try:
        analyzer = IRPFAnalyzer.from_payloads(payloads, tie_break_keys=tie_break_keys)
    except Exception:
        return None
    return analyzer if analyzer.anos_base_disponiveis() else None


def _faixa_ref_fiscal(irpf: IRPFAnalyzer | None, reference_date: date) -> date:
    """31/12 do ano-calendário do IRPF sob reconciliação (mesmo ``resolve_ano_base_fiscal``
    de ``irpf_kpis.ano_base_default``, ADR-305). Sem IRPF não há ano a reconciliar:
    cai no último ano-calendário fechado, um relógio no passado — nunca à frente
    da realidade, que é a direção que fabricaria menor onde já há maior."""
    resolved = resolve_ano_base_fiscal(irpf.estados_completude()) if irpf is not None else None
    ano = resolved.ano if resolved is not None else reference_date.year - 1
    return date(ano, 12, 31)


# VO inteiro (ADR-402): teto, aportado, restante e status saem da mesma leitura.
# A base é DECLARADA e somada no ano ([[ADR-414]] D2), nunca derivada do bruto.
def _build_capacidade_pgbl(irpf: IRPFAnalyzer | None) -> CapacidadePgblIRPF | None:
    """Capacidade PGBL do ano-base fiscal único (ADR-266/277/305/375). ``None`` quando
    não há IRPF ou ano-base resolvível → analyzer devolve ausência declarada."""
    if irpf is None:
        return None
    resolved = resolve_ano_base_fiscal(irpf.estados_completude())
    if resolved is None:
        return None
    return CapacidadePgblIRPF(
        capacidade=irpf.pgbl_capacidade_dedutivel(resolved.ano),
        renda_tributavel_anual=irpf.rendimentos_tributaveis(resolved.ano),
        base_calculo_anual=irpf.base_calculo_anual(resolved.ano),
        rend_upper_anual=irpf.maior_renda_total_declarante(resolved.ano),
        declaracoes_no_ano=len(irpf.declarations_for_year(resolved.ano)),
        ano_base=resolved.ano,
        fonte="irpf_pgbl_capacidade",
        nota_degradacao=resolved.nota_degradacao,
    )


# A40.l47 — ``_passive_income_config_from_goals`` foi removida aqui: existia só para
# mapear ``goals.trs_pct`` em ``PassiveIncomeConfig.trs_meta_pct``, campo que ninguém
# lia. ``goals.trs_pct`` é **taxa de saque** (goal.if.v2 §inputs, wizard passo 2,
# ``if_meta = renda × 12 ÷ trs_pct``) e não pode virar alvo de rentabilidade — a
# promoção é o defeito que a [[ADR-191]] §emenda 2026-08-14 corrige.
