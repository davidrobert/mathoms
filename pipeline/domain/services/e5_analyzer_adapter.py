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

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from pipeline.artifact_store import ArtifactStore
from pipeline.domain.types.config import FiscalParameters
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
from pipeline.domain.services.financial_score_calculator import (
    FinancialScoreCalculator,
    FinancialScoreConfig,
)
from pipeline.domain.services.fluxo_caixa_enricher import (
    FluxoCaixaEnriched,
    FluxoCaixaEnricher,
    FluxoEnricherConfig,
)
from pipeline.domain.services.if_projector import (
    IFProjection,
    IFProjector,
    IFProjectorConfig,
)
from pipeline.domain.services.investimentos_classes_analyzer import (
    InvestimentosClassesAnalysis,
    InvestimentosClassesAnalyzer,
    InvestimentosClassesConfig,
)
from pipeline.domain.services.orcamento_calculator import (
    OrcamentoProspectivo,
    OrcamentoProspectivoCalculator,
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
    PrevidenciaAnalysis,
    PrevidenciaAnalyzer,
    PrevidenciaConfig,
)
from pipeline.domain.services.ratios_calculator import (
    FinancialRatios,
    RatiosCalculator,
)
from pipeline.domain.services.reserva_emergencia_calculator import (
    EmergencyReserveCalculator,
    ReservaEmergenciaConfig,
)

# =============================================================================
# Stage keys
# =============================================================================


_E4_RECEITAS_KEY = "receitas"
_E4_DESPESAS_KEY = "despesas"
_E4_FLUXO_KEY = "fluxo_mensal_detalhado"
_E4_PATRIMONIO_KEY = "patrimonio"
_E4_INVESTIMENTOS_KEY = "investimentos"


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
    pontos_fortes: tuple[PontoForteItem, ...]
    pontos_urgentes: tuple[PontoUrgenteItem, ...]


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
        investment_banks: frozenset[str] | None = None,
        member_resolver: E5MemberResolver | None = None,
        fluxo_enricher: FluxoCaixaEnricher | None = None,
        if_projector: IFProjector | None = None,
        ratios_calculator: RatiosCalculator | None = None,
        orcamento_calculator: OrcamentoProspectivoCalculator | None = None,
        endividamento_analyzer: EndividamentoAnalyzer | None = None,
        previdencia_analyzer: PrevidenciaAnalyzer | None = None,
        investimentos_classes_analyzer: InvestimentosClassesAnalyzer | None = None,
        consumo_calculator: ConsumoConscienteCalculator | None = None,
        equilibrio_analyzer: EquilibrioCerbasiAnalyzer | None = None,
        cenarios_analyzer: CenariosConjugeAnalyzer | None = None,
        diagnostico_analyzer: DiagnosticoComportamentalAnalyzer | None = None,
        pontos_fortes_analyzer: PontosFortesAnalyzer | None = None,
        pontos_urgentes_analyzer: PontosUrgentesAnalyzer | None = None,
    ) -> None:
        self._identity = member_identity or MemberIdentity(
            titular_key="david",
            conjuge_key="mariana",
            titular_nome="David",
            conjuge_nome="Mariana",
        )
        self._patrimonio = patrimonio_calculator or PatrimonioCalculator(
            PatrimonioConfig(members=self._identity, residencia_keyword="")
        )
        self._reserva = reserva_calculator or EmergencyReserveCalculator(
            ReservaEmergenciaConfig(members=self._identity)
        )
        self._score = score_calculator or FinancialScoreCalculator(FinancialScoreConfig.default())
        self._taxas = taxas or {}
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
        self._ratios = ratios_calculator or RatiosCalculator()
        self._orcamento = orcamento_calculator or OrcamentoProspectivoCalculator()
        self._endividamento = endividamento_analyzer or EndividamentoAnalyzer()
        self._previdencia = previdencia_analyzer or PrevidenciaAnalyzer()
        self._inv_classes = investimentos_classes_analyzer or InvestimentosClassesAnalyzer()
        self._consumo = consumo_calculator or ConsumoConscienteCalculator()
        self._equilibrio = equilibrio_analyzer or EquilibrioCerbasiAnalyzer()
        self._cenarios = cenarios_analyzer
        self._diagnostico = diagnostico_analyzer or DiagnosticoComportamentalAnalyzer()
        self._pontos_fortes = pontos_fortes_analyzer or PontosFortesAnalyzer()
        self._pontos_urgentes = pontos_urgentes_analyzer or PontosUrgentesAnalyzer()

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
    ) -> "E5AnalyzerAdapter":
        """Constrói o adapter com todas as configs + services instanciados.

        ``titular_dob`` é obrigatório para ``IFProjector`` e
        ``CenariosConjugeAnalyzer`` — quando ``None``, esses dois services
        são desabilitados (o resultado terá ``if_projection=None`` e
        ``cenarios_conjuge=None``).

        ``taxas`` fornece câmbios USD/EUR para valoração de caixa em ME.
        ``institutions`` lista bancos de investimento (skip em caixa).

        A7.2b: ``fiscal_parameters`` (typed) tem prioridade sobre ``fiscal``
        (dict legacy). ``cambio_usd_brl`` (Decimal) tem prioridade sobre
        ``taxas["cambio_usd_brl"]``. Quando ambos None, usa fallback do JSON
        legado via ``FileConfigStore`` bridge.
        """
        member_cfg = MemberResolverConfig.from_family(family)
        identity = cls._build_identity(family, member_cfg)
        patrimonio_cfg = PatrimonioConfig(
            members=identity,
            residencia_keyword=cls._extract_residencia_keyword(family, member_cfg),
        )
        reserva_cfg = ReservaEmergenciaConfig.from_scoring_json(scoring or {}, identity)
        score_cfg = FinancialScoreConfig.from_scoring_json(scoring or {})
        investment_banks = cls._load_investment_banks(institutions)

        if_projector: IFProjector | None = None
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
            except ValueError:
                if_projector = None

        cenarios_analyzer: CenariosConjugeAnalyzer | None = None
        if titular_dob is not None:
            # Paridade com legado: quando family_members.json não declara
            # cônjuge, ``conjuge_key``/``conjuge_nome`` ficam vazios — o que
            # reflete nas chaves ``salario__clt_brl`` etc. Não impomos
            # default ``"mariana"`` aqui para preservar o output do legado.
            cenarios_cfg = CenariosConjugeConfig.from_configs(
                goals=goals,
                taxas=taxas,
                titular_dob=titular_dob,
                titular_key=member_cfg.titular_key,
                conjuge_key=member_cfg.conjuge_key,
                conjuge_nome=(member_cfg.conjuge_key or "").title(),
                reference_date=reference_date,
                cambio_usd_brl=cambio_usd_brl,
            )
            cenarios_analyzer = CenariosConjugeAnalyzer(cenarios_cfg)

        return cls(
            member_identity=identity,
            patrimonio_calculator=PatrimonioCalculator(patrimonio_cfg),
            reserva_calculator=EmergencyReserveCalculator(reserva_cfg),
            score_calculator=FinancialScoreCalculator(score_cfg),
            taxas=taxas,
            investment_banks=investment_banks,
            member_resolver=E5MemberResolver(member_cfg),
            fluxo_enricher=FluxoCaixaEnricher(
                FluxoEnricherConfig.from_categorization(categorization)
            ),
            if_projector=if_projector,
            endividamento_analyzer=EndividamentoAnalyzer(),
            previdencia_analyzer=PrevidenciaAnalyzer(
                PrevidenciaConfig.from_fiscal_parameters(fiscal_parameters)
                if fiscal_parameters is not None
                else PrevidenciaConfig.from_fiscal(fiscal)
            ),
            investimentos_classes_analyzer=InvestimentosClassesAnalyzer(
                InvestimentosClassesConfig.from_configs(scoring=scoring)
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
        receitas = store.read("E4", _E4_RECEITAS_KEY) or {}
        despesas = store.read("E4", _E4_DESPESAS_KEY) or {}
        fluxo_mensal = store.read("E4", _E4_FLUXO_KEY) or {}
        patrimonio_raw = store.read("E4", _E4_PATRIMONIO_KEY) or {}
        investimentos_raw = store.read("E4", _E4_INVESTIMENTOS_KEY) or {}

        # 2. Resolve membros do baseline.
        members = self._member_resolver.resolve(patrimonio_raw)

        # 3. Enriquece fluxo.
        fluxo_enriched = self._fluxo_enricher.enrich(
            receitas=receitas, despesas=despesas, fluxo_mensal=fluxo_mensal
        )
        fluxo_legacy = fluxo_enriched.to_legacy_dict()

        # 4. Caixa E3 (shell: lê tudo que está em E3 via store).
        caixa_total, caixa_detalhes = self._load_caixa_from_e3(store)

        # 5. Patrimônio completo (paridade com ``analyze_patrimonio`` legacy).
        patrimonio_full = self._patrimonio.calculate(
            PatrimonioInputs(
                baseline=patrimonio_raw,
                investimentos_atuais=investimentos_raw,
                caixa_total_brl=caixa_total,
                caixa_detalhes=caixa_detalhes,
            )
        )

        # 6. Ratios (consome ``bruto``/``dividas``/``investivel`` do dict full).
        ratios_result = self._ratios.calculate(fluxo_legacy, patrimonio_full)
        ratios_dict = ratios_result.to_legacy_dict()

        # 7. IF projection (se config disponível).
        if_projection: IFProjection | None = None
        if self._if_projector is not None:
            if_projection = self._if_projector.project(
                investivel=float(patrimonio_full.get("investivel", 0))
            )

        # 8. Reserva emergência (paridade com ``analyze_reserva_emergencia``).
        reserva = self._reserva.calculate(fluxo=fluxo_legacy, patrimonio=patrimonio_full)

        # 9. Score (paridade com ``calculate_score``).
        score_goals = {"if_pct": if_projection.if_pct if if_projection else 0.0}
        score = self._score.calculate(
            ratios=ratios_dict,
            patrimonio=patrimonio_full,
            goals=score_goals,
            fluxo=fluxo_legacy,
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

        # 12. Previdência.
        previdencia = self._previdencia.analyze(fluxo_legacy)

        # 13. Investimentos por classe.
        bens_list = [
            (members.titular_data.get("bens") or members.titular_data),
            (members.conjuge_data.get("bens") or members.conjuge_data),
        ]
        investimentos_classes = self._inv_classes.analyze(bens_list)

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

        # 17. Diagnósticos comportamentais.
        diagnosticos = self._diagnostico.analyze(fluxo_legacy, ratios_dict)

        # 18. Pontos fortes + urgentes (agora com score/reserva REAIS).
        #     Paridade com legado: ``analyze_pontos_fortes`` lê
        #     ``goals["progresso_pct"]`` mas ``analyze_goals`` emite
        #     ``if_pct`` (não ``progresso_pct``), então na prática o check
        #     sempre usa fallback ``0``. Espelhamos esse comportamento
        #     passando ``goals={}`` até que o analyzer novo aceite ``if_pct``.
        pontos_fortes = self._pontos_fortes.analyze(
            score=score,
            ratios=ratios_dict,
            patrimonio=patrimonio_full,
            fluxo=fluxo_legacy,
            reserva=reserva,
            goals={},
        )
        pontos_urgentes = self._pontos_urgentes.analyze(ratios_dict, reserva, patrimonio_full)

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
            consumo_consciente=consumo,
            equilibrio_cerbasi=equilibrio,
            cenarios_conjuge=cenarios,
            diagnosticos=tuple(diagnosticos),
            pontos_fortes=tuple(pontos_fortes),
            pontos_urgentes=tuple(pontos_urgentes),
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
    def _extract_residencia_keyword(family: dict | None, member_cfg: MemberResolverConfig) -> str:
        """Keyword para identificar residência principal na composição."""
        fam = family or {}
        membros = fam.get("membros", {}) or {}
        if isinstance(membros, dict):
            return (
                membros.get(member_cfg.titular_key, {}).get("residencia_principal_keyword", "")
                or ""
            ).lower()
        return ""

    @staticmethod
    def _load_investment_banks(institutions: dict | None) -> frozenset[str]:
        """Carrega lista de bancos de investimento de ``institutions.json``."""
        if institutions:
            banks = institutions.get("investment_banks", []) or []
            if banks:
                return frozenset(b.lower() for b in banks if isinstance(b, str))
        return frozenset({"btg pactual", "rico", "picpay", "binance", "xp"})

    # -- Helper de I/O (shell) --

    def _load_caixa_from_e3(self, store: ArtifactStore) -> tuple[float, list[CaixaDetalhe]]:
        """Carrega saldos de caixa + moeda estrangeira de todos os E3 artifacts.

        Classificação (paridade com ``_load_caixa_from_e3_saldos`` legado):
            - Conta corrente BRL → ``caixa``
            - Moeda estrangeira (USD/EUR) → ``moeda_estrangeira`` (→ BRL via taxas)
            - Poupança / PJ / corretora / fatura → skip
            - Banco de investimento → skip

        Sem keys em E3 (ou store sem list_keys) → (0.0, []).
        """
        keys = list(store.list_keys("E3")) if hasattr(store, "list_keys") else []
        if not keys:
            return 0.0, []

        cambio_usd = safe_float(self._taxas.get("cambio_usd_brl", 5.80), default=5.80)
        cambio_eur = safe_float(self._taxas.get("cambio_eur_brl", 6.35), default=6.35)

        latest_per_account: dict[tuple[str, str, str, str], tuple[str, dict]] = {}

        for key in keys:
            data = store.read("E3", key) or {}
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
        detalhes: list[CaixaDetalhe] = []
        for _, data in sorted(latest_per_account.values(), key=lambda x: x[0]):
            tipo_conta = (data.get("tipo_conta") or "").lower()
            moeda = (data.get("moeda") or "BRL").upper()
            saldo = safe_float(data.get("saldo_final"))

            if moeda == "USD":
                valor_brl = saldo * cambio_usd
            elif moeda == "EUR":
                valor_brl = saldo * cambio_eur
            else:
                valor_brl = saldo

            categoria = "moeda_estrangeira" if moeda != "BRL" else "caixa"
            total_brl += valor_brl
            detalhes.append(
                CaixaDetalhe(
                    conta=f"{data.get('banco', '?')} ({tipo_conta})",
                    moeda=moeda,
                    saldo_original=saldo,
                    valor_brl=valor_brl,
                    tipo=categoria,
                )
            )

        return round(total_brl, 2), detalhes
