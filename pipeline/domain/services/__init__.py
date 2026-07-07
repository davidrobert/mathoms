"""Domain services — lógica pura de negócio, sem I/O."""

from pipeline.domain.services.account_grouper import (
    AccountGrouper,
    AccountGrouperConfig,
    AccountKey,
)
from pipeline.domain.services.baseline_normalizer import (
    BaselineNormalizer,
    NormalizedBaseline,
)
from pipeline.domain.services.baseline_validator import (
    BaselineAccountSaldo,
    BaselineDiffWarning,
    BaselineValidator,
    BaselineValidatorConfig,
)
from pipeline.domain.services.calculators import (
    CashFlowAggregator,
    CashFlowReport,
    EmergencyReserveCalculator,
    EmergencyReserveConfig,
    EmergencyReserveReport,
    FinancialScoreCalculator,
    MonthlyFlow,
    PatrimonioCalculator,
    PatrimonioConfig,
    PatrimonioReport,
    ScoreConfig,
)
from pipeline.domain.services.cash_flow_builder import (
    CashFlow,
    CashFlowBuilder,
    DespesasUnified,
    FluxoMensal,
    ReceitasUnified,
)
from pipeline.domain.services.categorization_service import (
    RULE_HARD_CAP,
    RULE_SOFT_CAP,
    CategorizationRules,
    CategorizationRulesV2,
    CategorizationService,
    LearnedRule,
)
from pipeline.domain.services.cenarios_conjuge_analyzer import (
    CenarioItem,
    CenariosConjugeAnalyzer,
    CenariosConjugeConfig,
    CenariosConjugeResult,
)
from pipeline.domain.services.consumo_consciente_calculator import (
    ConsumoConsciente,
    ConsumoConscienteCalculator,
    ConsumoConscienteConfig,
    GastoPontualItem,
)
from pipeline.domain.services.diagnostico_comportamental_analyzer import (
    DiagnosticoComportamentalAnalyzer,
    DiagnosticoComportamentalConfig,
    DiagnosticoItem,
)
from pipeline.domain.services.e3_reconciler_adapter import (
    E3ReconcilerAdapter,
    ReconciliationStoreResult,
)
from pipeline.domain.services.e4_categorizer_adapter import (
    CategorizationResult,
    E4CategorizerAdapter,
)
from pipeline.domain.services.e5_analyzer_adapter import (
    E5AnalysisResult,
    E5AnalyzerAdapter,
)
from pipeline.domain.services.e5_member_resolver import (
    E5MemberResolver,
    MemberResolverConfig,
    ResolvedMembers,
)
from pipeline.domain.services.endividamento_analyzer import (
    DividaItem,
    EndividamentoAnalysis,
    EndividamentoAnalyzer,
)
from pipeline.domain.services.equilibrio_cerbasi_analyzer import (
    ClassificacaoFaixa,
    EquilibrioCerbasi,
    EquilibrioCerbasiAnalyzer,
    EquilibrioCerbasiConfig,
)
from pipeline.domain.services.fluxo_caixa_enricher import (
    FluxoCaixaEnriched,
    FluxoCaixaEnricher,
    FluxoEnricherConfig,
    Janela12m,
)
from pipeline.domain.services.if_projector import (
    IFProjection,
    IFProjector,
    IFProjectorConfig,
    extract_if_meta_from_text,
    extract_if_trs_from_text,
    extract_renda_passiva_from_text,
)
from pipeline.domain.services.income_origin_resolver import (
    IncomeOriginConfig,
    IncomeOriginResolver,
)
from pipeline.domain.services.instituicoes_por_membro_analyzer import (
    InstituicoesPorMembroAnalyzer,
    InstituicoesPorMembroConfig,
    InstituicoesPorMembroResult,
    MembroInstituicoes,
)
from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferConfig,
    InternalTransferDetector,
)
from pipeline.domain.services.investimentos_classes_analyzer import (
    ClasseAtivo,
    InvestimentosClassesAnalysis,
    InvestimentosClassesAnalyzer,
    InvestimentosClassesConfig,
)
from pipeline.domain.services.investments_consolidator import (
    ConsolidatedInvestments,
    InvestmentsConsolidator,
    InvestmentsConsolidatorConfig,
)
from pipeline.domain.services.keyword_matcher import (
    KeywordMatcher,
    find_longest_matching_keyword,
)
from pipeline.domain.services.member_analyzer import (
    MemberAnalyzer,
    MemberPatrimonio,
)
from pipeline.domain.services.orcamento_calculator import (
    OrcamentoProspectivo,
    OrcamentoProspectivoCalculator,
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
    IRPFBracket,
    PrevidenciaAnalysis,
    PrevidenciaAnalyzer,
    PrevidenciaConfig,
)
from pipeline.domain.services.ratios_calculator import (
    FinancialRatios,
    RatiosCalculator,
)
from pipeline.domain.services.reconciliation_service import (
    ReconciliationConfig,
    ReconciliationService,
)
from pipeline.domain.services.reconciliation_validators import (
    ContinuityAccountKey,
    FaturaExcludedFromSaldoChain,
    SaldoContinuityConfig,
    SaldoContinuityResult,
    SaldoContinuityValidator,
    SaldoGapWarning,
    TemporalGapConfig,
    TemporalGapDetector,
    TemporalGapWarning,
)
from pipeline.domain.services.statement_preprocessor import (
    AnachronicFilterResult,
    AnachronicGuardConfig,
    AnachronicTransactionDropper,
    AnachronicTransactionWarning,
    NormalizationResult,
    PeriodDerivationReason,
    PeriodDerivationWarning,
    StatementPeriodNormalizer,
)
from pipeline.domain.services.top_ativos_analyzer import (
    TopAtivo,
    TopAtivosAnalyzer,
    TopAtivosConfig,
    TopAtivosResult,
)
from pipeline.domain.services.transaction_classifier import (
    ClassifiedTransaction,
    ClassifierConfig,
    TransactionClassifier,
)

__all__ = [
    "ReconciliationConfig",
    "ReconciliationService",
    "ContinuityAccountKey",
    "FaturaExcludedFromSaldoChain",
    "SaldoContinuityConfig",
    "SaldoContinuityResult",
    "SaldoContinuityValidator",
    "SaldoGapWarning",
    "TemporalGapConfig",
    "TemporalGapDetector",
    "TemporalGapWarning",
    "BaselineAccountSaldo",
    "BaselineDiffWarning",
    "BaselineValidator",
    "BaselineValidatorConfig",
    "E3ReconcilerAdapter",
    "ReconciliationStoreResult",
    "AccountGrouper",
    "AccountGrouperConfig",
    "AccountKey",
    "AnachronicFilterResult",
    "AnachronicGuardConfig",
    "AnachronicTransactionDropper",
    "AnachronicTransactionWarning",
    "NormalizationResult",
    "PeriodDerivationReason",
    "PeriodDerivationWarning",
    "StatementPeriodNormalizer",
    "CategorizationRules",
    "CategorizationRulesV2",
    "CategorizationService",
    "LearnedRule",
    "RULE_HARD_CAP",
    "RULE_SOFT_CAP",
    "IncomeOriginConfig",
    "IncomeOriginResolver",
    "InternalTransferConfig",
    "InternalTransferDetector",
    "MemberAnalyzer",
    "MemberPatrimonio",
    "KeywordMatcher",
    "find_longest_matching_keyword",
    "ClassifiedTransaction",
    "ClassifierConfig",
    "TransactionClassifier",
    "CashFlow",
    "CashFlowBuilder",
    "DespesasUnified",
    "FluxoMensal",
    "ReceitasUnified",
    "BaselineNormalizer",
    "NormalizedBaseline",
    "ConsolidatedInvestments",
    "InvestmentsConsolidator",
    "InvestmentsConsolidatorConfig",
    "CategorizationResult",
    "E4CategorizerAdapter",
    "IFProjection",
    "IFProjector",
    "IFProjectorConfig",
    "extract_if_meta_from_text",
    "extract_if_trs_from_text",
    "extract_renda_passiva_from_text",
    "FinancialRatios",
    "RatiosCalculator",
    "OrcamentoProspectivo",
    "OrcamentoProspectivoCalculator",
    "DividaItem",
    "EndividamentoAnalysis",
    "EndividamentoAnalyzer",
    "IRPFBracket",
    "PrevidenciaAnalysis",
    "PrevidenciaAnalyzer",
    "PrevidenciaConfig",
    "ClasseAtivo",
    "InstituicoesPorMembroAnalyzer",
    "InstituicoesPorMembroConfig",
    "InstituicoesPorMembroResult",
    "InvestimentosClassesAnalysis",
    "InvestimentosClassesAnalyzer",
    "InvestimentosClassesConfig",
    "MembroInstituicoes",
    "TopAtivo",
    "TopAtivosAnalyzer",
    "TopAtivosConfig",
    "TopAtivosResult",
    "ConsumoConsciente",
    "ConsumoConscienteCalculator",
    "ConsumoConscienteConfig",
    "GastoPontualItem",
    "DiagnosticoComportamentalAnalyzer",
    "DiagnosticoComportamentalConfig",
    "DiagnosticoItem",
    "PontoUrgenteItem",
    "PontosUrgentesAnalyzer",
    "PontosUrgentesConfig",
    "ClassificacaoFaixa",
    "EquilibrioCerbasi",
    "EquilibrioCerbasiAnalyzer",
    "EquilibrioCerbasiConfig",
    "PontoForteItem",
    "PontosFortesAnalyzer",
    "PontosFortesConfig",
    "E5MemberResolver",
    "MemberResolverConfig",
    "ResolvedMembers",
    "FluxoCaixaEnriched",
    "FluxoCaixaEnricher",
    "FluxoEnricherConfig",
    "Janela12m",
    "CenarioItem",
    "CenariosConjugeAnalyzer",
    "CenariosConjugeConfig",
    "CenariosConjugeResult",
    "E5AnalysisResult",
    "E5AnalyzerAdapter",
    "CashFlowAggregator",
    "CashFlowReport",
    "EmergencyReserveCalculator",
    "EmergencyReserveConfig",
    "EmergencyReserveReport",
    "FinancialScoreCalculator",
    "MonthlyFlow",
    "PatrimonioCalculator",
    "PatrimonioConfig",
    "PatrimonioReport",
    "ScoreConfig",
]
