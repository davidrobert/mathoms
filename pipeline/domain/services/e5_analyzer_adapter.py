"""E5AnalyzerAdapter — orquestra a análise financeira do E5 sobre ``ArtifactStore``
(Sessão A5c · Fase 8 foundation).

Compõe os domain services extraídos em A1/A3c/A5a/A5b/A5c:

- :class:`E5MemberResolver` (A5c) — resolve titular/cônjuge do baseline.
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
from pipeline.domain.services.cenarios_conjuge_analyzer import (
    CenariosConjugeAnalyzer,
    CenariosConjugeConfig,
    CenariosConjugeResult,
)
from pipeline.domain.services.consumo_consciente_calculator import (
    ConsumoConsciente,
    ConsumoConscienteCalculator,
    ConsumoConscienteConfig,
)
from pipeline.domain.services.diagnostico_comportamental_analyzer import (
    DiagnosticoComportamentalAnalyzer,
    DiagnosticoComportamentalConfig,
    DiagnosticoItem,
)
from pipeline.domain.services.e5_lineage import build_e5_lineage
from pipeline.domain.services.e5_member_resolver import (
    E5MemberResolver,
    MemberResolverConfig,
    ResolvedMembers,
)
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
from pipeline.domain.services.patrimonio_types import (
    CaixaDetalhe,
    MemberIdentity,
    PatrimonioConfig,
    PatrimonioInputs,
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
)
from pipeline.domain.services.reserva_emergencia_calculator import (
    EmergencyReserveCalculator,
    ReservaEmergenciaConfig,
)
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
    members: ResolvedMembers
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
        investment_banks: frozenset[str] | None = None,
        member_resolver: E5MemberResolver | None = None,
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
        reference_date: date | None = None,
        seguradoras_catalog: Mapping[str, str] | None = None,
        protection_bundle: ProtectionBundle | None = None,
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
        self._investment_banks = investment_banks or frozenset(
            {
                "btg pactual",
                "rico",
                "picpay",
                "binance",
                "xp",
            }
        )
        self._member_resolver = member_resolver or E5MemberResolver()
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
        institutions: dict | None = None,
        titular_dob: date | None = None,
        conjuge_dob: date | None = None,
        reference_date: date | None = None,
        fiscal_parameters: FiscalParameters | None = None,
        cambio_usd_brl: Decimal | float | None = None,
        cambio_eur_brl: Decimal | float | None = None,
        property_classification_overrides: dict[str, str] | None = None,
        imoveis_no_if: bool = True,
        seguradoras_catalog: Mapping[str, str] | None = None,
        protection_bundle: ProtectionBundle | None = None,
    ) -> "E5AnalyzerAdapter":
        """Constrói o adapter com todas as configs + services instanciados.

        ``titular_dob`` é obrigatório para ``IFProjector`` e
        ``CenariosConjugeAnalyzer`` — quando ``None``, esses dois services
        são desabilitados (o resultado terá ``if_projection=None`` e
        ``cenarios_conjuge=None``).

        ``taxas`` fornece câmbios USD/EUR para valoração de caixa em ME.
        ``institutions`` lista bancos de investimento (skip em caixa).

        A7.2b: ``fiscal_parameters`` (typed) tem prioridade sobre ``fiscal``
        (dict legacy). ``cambio_usd_brl`` / ``cambio_eur_brl`` (Decimal)
        têm prioridade sobre ``taxas["cambio_usd_brl"]`` / ``taxas["cambio_eur_brl"]``.
        Quando ambos None, usa default codificado (5.80/6.35) — pos-A7.5,
        sem fallback de disco.
        """
        member_cfg = MemberResolverConfig.from_family(family)
        identity = cls._build_identity(family, member_cfg)
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
        investment_banks = cls._load_investment_banks(institutions)

        if_projector: IFProjector | None = None
        if_projector_config_built: IFProjectorConfig | None = None
        if titular_dob is not None and goals:
            try:
                if_cfg = IFProjectorConfig.from_configs(
                    goals=goals,
                    titular_dob=titular_dob,
                    conjuge_dob=conjuge_dob,
                    reference_date=reference_date,
                    titular_key=member_cfg.titular_key,
                    conjuge_key=member_cfg.conjuge_key,
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
                titular_key=member_cfg.titular_key,
                conjuge_key=member_cfg.conjuge_key,
                conjuge_nome=(member_cfg.conjuge_key or "").title(),
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
            investment_banks=investment_banks,
            member_resolver=E5MemberResolver(member_cfg),
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
            passive_income_calculator=PassiveIncomeCalculator(
                _passive_income_config_from_goals(goals)
            ),
            family_snapshots=family_snapshots_from_config(family, reference_date or date.today()),
            reference_date=reference_date,
            seguradoras_catalog=seguradoras_catalog,
            protection_bundle=protection_bundle,
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

        # 2. Resolve membros do baseline.
        members = self._member_resolver.resolve(patrimonio_raw)

        # 3. Enriquece fluxo.
        fluxo_enriched = self._fluxo_enricher.enrich(
            receitas=receitas, despesas=despesas, fluxo_mensal=fluxo_mensal
        )
        fluxo_legacy = fluxo_enriched.to_legacy_dict()

        # 4. Caixa E3 (shell: lê tudo que está em E3 via store).
        # ADR-245: fallback baseline IRPF quando não há extrato USD/EUR em E3.
        caixa_total, caixa_detalhes = self._load_caixa_from_e3(store, baseline=patrimonio_raw)

        # 5. Patrimônio completo (paridade com ``analyze_patrimonio`` legacy).
        patrimonio_full = self._patrimonio.calculate(
            PatrimonioInputs(
                baseline=patrimonio_raw,
                investimentos_atuais=investimentos_raw,
                caixa_total_brl=caixa_total,
                caixa_detalhes=caixa_detalhes,
            )
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
                investivel=float(patrimonio_full.get("investivel_efetivo", 0))
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
            investimentos_atuais=investimentos_raw,
            bens_por_membro={
                self._identity.titular_key: members.titular_data,
                **(
                    {self._identity.conjuge_key: members.conjuge_data}
                    if self._identity.conjuge_key
                    else {}
                ),
            },
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

        # 11. Endividamento — usa nomes de exibição (titular_nome/conjuge_nome)
        #     para paridade com legado ``analyze_endividamento`` que formata
        #     "Financiamento imobiliário (David)" (capitalizado).
        endiv_members = [
            {"nome": self._identity.titular_nome, "data": members.titular_data},
            {"nome": self._identity.conjuge_nome, "data": members.conjuge_data},
        ]
        endividamento = self._endividamento.analyze(patrimonio_full, endiv_members)

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
        titular_bens = members.titular_data.get("bens") or members.titular_data
        conjuge_bens = members.conjuge_data.get("bens") or members.conjuge_data
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

    # -- Helpers de config --

    @staticmethod
    def _build_identity(family: dict | None, member_cfg: MemberResolverConfig) -> MemberIdentity:
        """Extrai nomes de exibição (nome_curto) do ``family_members.json``."""
        fam = family or {}
        membros = fam.get("membros", {}) or {}
        titular_key = member_cfg.titular_key
        conjuge_key = member_cfg.conjuge_key
        titular_nome = (
            membros.get(titular_key, {}).get("nome_curto", titular_key.title())
            if isinstance(membros, dict)
            else titular_key.title()
        )
        conjuge_nome = (
            membros.get(conjuge_key, {}).get("nome_curto", conjuge_key.title())
            if isinstance(membros, dict) and conjuge_key
            else (conjuge_key.title() if conjuge_key else "")
        )
        return MemberIdentity(
            titular_key=titular_key,
            conjuge_key=conjuge_key,
            titular_nome=titular_nome,
            conjuge_nome=conjuge_nome,
        )

    @staticmethod
    def _load_investment_banks(institutions: dict | None) -> frozenset[str]:
        """Carrega lista de bancos de investimento de ``institutions.json``."""
        if institutions:
            banks = institutions.get("investment_banks", []) or []
            if banks:
                return frozenset(b.lower() for b in banks if isinstance(b, str))
        return frozenset({"btg pactual", "rico", "picpay", "binance", "xp"})

    # -- Helper de I/O (shell) --

    def _load_caixa_from_e3(
        self,
        store: ArtifactStore,
        *,
        baseline: dict | None = None,
    ) -> tuple[float, list[CaixaDetalhe]]:
        """Carrega saldos de caixa + moeda estrangeira de todos os E3 artifacts.

        Classificação (paridade com ``_load_caixa_from_e3_saldos`` legado):
            - Conta corrente BRL → ``caixa``
            - Moeda estrangeira (USD/EUR) → ``moeda_estrangeira`` (→ BRL via taxas)
            - Poupança / PJ / corretora / fatura → skip
            - Banco de investimento → skip

        Cambio resolution (A7.5): typed ``self._cambio_usd_brl`` /
        ``self._cambio_eur_brl`` (resolvidos via ``ConfigStore.get_market_rate``)
        têm prioridade sobre ``self._taxas`` dict legacy. Default final: 5.80/6.35.

        ADR-245 — fallback baseline IRPF: quando nenhum extrato em USD/EUR
        está em E3, agrega items de moeda estrangeira de
        ``baseline.investimentos_consolidados`` (depósitos em ME, contas
        offshore). Trade-off conhecido: o item segue em
        ``investimentos_consolidados`` no patrimonio_calculator — se algum
        membro cair em fallback IRPF puro (``titular_val == 0``), pode
        haver double-count. Cobertura cirúrgica do caso comum.

        Sem keys em E3 (ou store sem list_keys) → fallback baseline apenas.
        """
        cambio_usd = (
            self._cambio_usd_brl
            if self._cambio_usd_brl is not None
            else safe_float(self._taxas.get("cambio_usd_brl", 5.80), default=5.80)
        )
        cambio_eur = (
            self._cambio_eur_brl
            if self._cambio_eur_brl is not None
            else safe_float(self._taxas.get("cambio_eur_brl", 6.35), default=6.35)
        )

        keys = (
            list(store.list_keys("reconcile_transactions")) if hasattr(store, "list_keys") else []
        )
        latest_per_account: dict[tuple[str, str, str, str], tuple[str, dict]] = {}

        for key in keys:
            data = store.read("reconcile_transactions", key) or {}
            tipo_conta = (data.get("tipo_conta") or "").lower()
            banco = (data.get("banco") or "").lower()
            moeda = (data.get("moeda") or "BRL").upper()
            saldo_raw = data.get("saldo_final")

            if saldo_raw is None or data.get("saldo_final_unknown", False):
                continue
            if "fatura" in tipo_conta or "poupan" in tipo_conta or "pj" in tipo_conta:
                continue
            if banco in self._investment_banks:
                continue

            titular = (data.get("titular") or "").lower()
            account_key = (banco, tipo_conta, moeda, titular)
            period_end = (data.get("periodo_cobertura") or {}).get("fim") or ""
            tiebreak = (period_end, key)
            prev = latest_per_account.get(account_key)
            if prev is None or tiebreak > prev[0]:
                latest_per_account[account_key] = (tiebreak, data)

        total_brl = 0.0
        posicoes: list[ExtratoPosicao] = []
        has_foreign_in_e3 = False
        for _, data in sorted(latest_per_account.values(), key=lambda x: x[0]):
            tipo_conta = (data.get("tipo_conta") or "").lower()
            moeda = (data.get("moeda") or "BRL").upper()
            saldo = safe_float(data.get("saldo_final"))

            if moeda == "USD":
                valor_brl = saldo * cambio_usd
                has_foreign_in_e3 = True
            elif moeda == "EUR":
                valor_brl = saldo * cambio_eur
                has_foreign_in_e3 = True
            else:
                valor_brl = saldo

            categoria = "moeda_estrangeira" if moeda != "BRL" else "caixa"
            total_brl += valor_brl
            posicoes.append(
                ExtratoPosicao(
                    detalhe=CaixaDetalhe(
                        conta=f"{data.get('banco', '?')} ({tipo_conta})",
                        moeda=moeda,
                        saldo_original=saldo,
                        valor_brl=valor_brl,
                        tipo=categoria,
                    ),
                    banco=(data.get("banco") or "").lower(),
                    period_end=(data.get("periodo_cobertura") or {}).get("fim") or "",
                )
            )

        # ADR-238 D5 (A33.l2) — informe 31/12 vence extrato D+1: substitui o
        # saldo do extrato da virada de ano pelo do informe (fonte fiscal
        # certificada) e anota divergência relevante nos entries do baseline.
        override = apply_informe_override(
            posicoes, (baseline or {}).get("informe_pf_saldos_31_12") or []
        )
        detalhes = override.detalhes
        total_brl += float(override.ajuste_total_brl)

        # ADR-245: fallback baseline IRPF para moeda estrangeira.
        if not has_foreign_in_e3 and baseline:
            me_total, me_detalhes = _extract_me_caixa_from_baseline(baseline)
            total_brl += me_total
            detalhes.extend(me_detalhes)

        return round(total_brl, 2), detalhes


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


def _moeda_from_descricao(descricao_lower: str) -> str:
    """Inferir moeda a partir de palavras-chave em descrição do baseline IRPF."""
    if any(kw in descricao_lower for kw in _ME_KEYWORDS_USD):
        return "USD"
    if any(kw in descricao_lower for kw in _ME_KEYWORDS_EUR):
        return "EUR"
    return "USD"  # default conservador — IRPF mais comum em USD


def _extract_me_caixa_from_baseline(baseline: dict) -> tuple[float, list[CaixaDetalhe]]:
    """Extrai items de moeda estrangeira de ``baseline.investimentos_consolidados``.

    O IRPF brasileiro classifica depósitos em ME sob código 02 (mesmo grupo
    de "Aplicação de renda fixa"). Sem extrato bancário reconciliado,
    esses items são a única fonte de saldo ME — esta função aceita o
    trade-off de leve duplicação com ``_investimentos_from_irpf`` (em
    cenários raros de fallback IRPF puro) em troca de visibilidade do
    saldo ME no card "Caixa e Moeda Estrangeira" (ADR-245 §Limitações).

    Valor IRPF já está em BRL (declaração consolida a R$ à taxa
    de fechamento do ano-base) — não re-converte.
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

        moeda = _moeda_from_descricao(descricao)
        total_brl += valor
        detalhes.append(
            CaixaDetalhe(
                conta=f"IRPF: {(item.get('descricao') or '')[:80]}",
                moeda=moeda,
                saldo_original=valor,  # IRPF já é BRL — sem cambio reverso.
                valor_brl=valor,
                tipo="moeda_estrangeira_irpf",
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


def _build_capacidade_pgbl(irpf: IRPFAnalyzer | None) -> CapacidadePgblIRPF | None:
    """Capacidade PGBL do ano-base fiscal único (ADR-266/277/305). ``None`` quando
    não há IRPF ou ano-base resolvível → analyzer usa o proxy de receita PJ."""
    if irpf is None:
        return None
    resolved = resolve_ano_base_fiscal(irpf.estados_completude())
    if resolved is None:
        return None
    return CapacidadePgblIRPF(
        restante_anual=irpf.pgbl_capacidade_dedutivel(resolved.ano),
        renda_tributavel_anual=irpf.rendimentos_tributaveis(resolved.ano),
        ano_base=resolved.ano,
        fonte="irpf_pgbl_capacidade",
        nota_degradacao=resolved.nota_degradacao,
        pgbl_status=irpf.pgbl_status(resolved.ano),  # RV2-03: ramifica a nota por estado
    )


def _passive_income_config_from_goals(goals: dict | None) -> PassiveIncomeConfig:
    """Constrói ``PassiveIncomeConfig`` lendo ``trs_pct`` de ``independencia_financeira``."""
    if_block = (goals or {}).get("independencia_financeira") or {}
    trs_pct_raw = if_block.get("trs_pct")
    if trs_pct_raw is None:
        return PassiveIncomeConfig()
    try:
        return PassiveIncomeConfig(trs_meta_pct=Decimal(str(trs_pct_raw)))
    except Exception:
        return PassiveIncomeConfig()
