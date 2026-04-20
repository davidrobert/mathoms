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
from typing import Any

from pipeline.artifact_store import ArtifactStore
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
from pipeline.domain.services.fluxo_caixa_enricher import (
    FluxoCaixaEnricher,
    FluxoCaixaEnriched,
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
from pipeline.domain.services.pontos_fortes_analyzer import (
    PontoForteItem,
    PontosFortesAnalyzer,
    PontosFortesConfig,
)
from pipeline.domain.services.pontos_urgentes_analyzer import (
    PontoUrgenteItem,
    PontosUrgentesAnalyzer,
    PontosUrgentesConfig,
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
        self._member_resolver = member_resolver or E5MemberResolver()
        self._fluxo_enricher = fluxo_enricher or FluxoCaixaEnricher()
        self._if_projector = if_projector
        self._ratios = ratios_calculator or RatiosCalculator()
        self._orcamento = orcamento_calculator or OrcamentoProspectivoCalculator()
        self._endividamento = endividamento_analyzer or EndividamentoAnalyzer()
        self._previdencia = previdencia_analyzer or PrevidenciaAnalyzer()
        self._inv_classes = (
            investimentos_classes_analyzer or InvestimentosClassesAnalyzer()
        )
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
        titular_dob: date | None = None,
        conjuge_dob: date | None = None,
        reference_date: date | None = None,
    ) -> "E5AnalyzerAdapter":
        """Constrói o adapter com todas as configs + services instanciados.

        ``titular_dob`` é obrigatório para ``IFProjector`` e
        ``CenariosConjugeAnalyzer`` — quando ``None``, esses dois services
        são desabilitados (o resultado terá ``if_projection=None`` e
        ``cenarios_conjuge=None``).
        """
        member_cfg = MemberResolverConfig.from_family(family)

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
            cenarios_cfg = CenariosConjugeConfig.from_configs(
                goals=goals,
                taxas=taxas,
                titular_dob=titular_dob,
                titular_key=member_cfg.titular_key,
                conjuge_key=member_cfg.conjuge_key or "mariana",
                conjuge_nome=(member_cfg.conjuge_key or "mariana").title(),
                reference_date=reference_date,
            )
            cenarios_analyzer = CenariosConjugeAnalyzer(cenarios_cfg)

        return cls(
            member_resolver=E5MemberResolver(member_cfg),
            fluxo_enricher=FluxoCaixaEnricher(
                FluxoEnricherConfig.from_categorization(categorization)
            ),
            if_projector=if_projector,
            endividamento_analyzer=EndividamentoAnalyzer(),
            previdencia_analyzer=PrevidenciaAnalyzer(
                PrevidenciaConfig.from_fiscal(fiscal)
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
            pontos_fortes_analyzer=PontosFortesAnalyzer(
                PontosFortesConfig.from_scoring(scoring)
            ),
            pontos_urgentes_analyzer=PontosUrgentesAnalyzer(
                PontosUrgentesConfig.from_scoring(scoring)
            ),
        )

    # -- API --

    def analyze_via_store(self, store: ArtifactStore) -> E5AnalysisResult:
        """Lê E4 do store, compõe análises e retorna ``E5AnalysisResult``.

        **Não escreve em E5.** Escrita fica para ``main_with_store`` (A5d).
        """
        # 1. Inputs do E4.
        receitas = store.read("E4", _E4_RECEITAS_KEY) or {}
        despesas = store.read("E4", _E4_DESPESAS_KEY) or {}
        fluxo_mensal = store.read("E4", _E4_FLUXO_KEY) or {}
        patrimonio_raw = store.read("E4", _E4_PATRIMONIO_KEY) or {}
        investimentos_raw = store.read("E4", _E4_INVESTIMENTOS_KEY) or {}

        # 2. Resolve membros do baseline (patrimonio já é o baseline
        # normalizado pelo `BaselineNormalizer`).
        members = self._member_resolver.resolve(patrimonio_raw)

        # 3. Enriquece fluxo (adiciona janela_12m, chart datasets, etc.).
        fluxo_enriched = self._fluxo_enricher.enrich(
            receitas=receitas, despesas=despesas, fluxo_mensal=fluxo_mensal
        )
        fluxo_legacy = fluxo_enriched.to_legacy_dict()

        # 4. Patrimônio para ratios — usa numbers no top-level do baseline
        # (paridade com legado: `patrimonio["bruto"] / "dividas" / "investivel"`).
        patrimonio_top = self._extract_patrimonio_for_ratios(
            patrimonio_raw, investimentos_raw
        )

        # 5. Ratios.
        ratios_result = self._ratios.calculate(fluxo_legacy, patrimonio_top)
        ratios_dict = ratios_result.to_legacy_dict()

        # 6. IF projection (se config disponível).
        if_projection: IFProjection | None = None
        if self._if_projector is not None:
            if_projection = self._if_projector.project(
                investivel=float(patrimonio_top.get("investivel", 0))
            )

        # 7. Orcamento prospectivo.
        num_months = len(fluxo_legacy.get("receita_despesa_mensal_detalhado", {}).get("labels", []))
        orcamento = self._orcamento.calculate(
            fluxo_legacy.get("despesas_por_categoria", {}),
            num_months=num_months,
        )

        # 8. Endividamento (precisa de members list).
        endiv_members = [
            {"nome": members.titular_key, "data": members.titular_data},
            {"nome": members.conjuge_key, "data": members.conjuge_data},
        ]
        endividamento = self._endividamento.analyze(patrimonio_top, endiv_members)

        # 9. Previdência (receita PJ).
        previdencia = self._previdencia.analyze(fluxo_legacy)

        # 10. Investimentos por classe (usa bens dos dois membros).
        bens_list = [
            (members.titular_data.get("bens") or members.titular_data),
            (members.conjuge_data.get("bens") or members.conjuge_data),
        ]
        investimentos_classes = self._inv_classes.analyze(bens_list)

        # 11. Consumo consciente.
        consumo = self._consumo.calculate(fluxo_legacy, despesas)

        # 12. Equilibrio Cerbasi.
        equilibrio = self._equilibrio.analyze(fluxo_legacy)

        # 13. Cenarios conjuge (se disponível).
        cenarios: CenariosConjugeResult | None = None
        if self._cenarios is not None and if_projection is not None:
            cenarios = self._cenarios.analyze(
                patrimonio=patrimonio_top,
                goals={"if_meta": if_projection.if_meta},
                fluxo=fluxo_legacy,
            )

        # 14. Diagnósticos comportamentais.
        diagnosticos = self._diagnostico.analyze(fluxo_legacy, ratios_dict)

        # 15. Pontos fortes + urgentes.
        score_placeholder: dict[str, Any] = {"classificacao": "", "valor": 0}
        reserva_placeholder: dict[str, Any] = {"cobertura_meses": 0}

        pontos_fortes = self._pontos_fortes.analyze(
            score=score_placeholder,
            ratios=ratios_dict,
            patrimonio=patrimonio_top,
            fluxo=fluxo_legacy,
            reserva=reserva_placeholder,
            goals={"progresso_pct": (if_projection.if_pct if if_projection else 0)},
        )
        pontos_urgentes = self._pontos_urgentes.analyze(
            ratios_dict, reserva_placeholder, patrimonio_top
        )

        return E5AnalysisResult(
            members=members,
            receitas=receitas,
            despesas=despesas,
            fluxo_mensal_raw=fluxo_mensal,
            patrimonio_raw=patrimonio_raw,
            investimentos_raw=investimentos_raw,
            fluxo_enriched=fluxo_enriched,
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

    # -- Helpers --

    @staticmethod
    def _extract_patrimonio_for_ratios(
        patrimonio_raw: dict, investimentos_raw: dict
    ) -> dict[str, Any]:
        """Extrai ``bruto``/``dividas``/``investivel`` do baseline + investimentos.

        Versão simplificada — no legado `analyze_patrimonio` computa muitos
        campos adicionais. Aqui capturamos apenas o essencial para ratios.
        O serializer E5 completo (A5d) invoca `PatrimonioCalculator` para
        produzir o dict completo.
        """
        pat_ano = (patrimonio_raw or {}).get("patrimonio_por_ano", {}) or {}
        if pat_ano:
            anos = sorted(pat_ano.keys())
            ano_data = pat_ano.get(anos[-1], {}) or {} if anos else {}
            bruto = float(ano_data.get("total_bens", 0) or 0)
            dividas = float(ano_data.get("total_dividas", 0) or 0)
        else:
            bruto = 0.0
            dividas = 0.0

        total_investimentos = float((investimentos_raw or {}).get("total_geral", 0) or 0)
        investivel = bruto - dividas  # aproximação (sem residência/veículos).
        if total_investimentos > 0:
            investivel = max(investivel, total_investimentos)

        return {
            "bruto": bruto,
            "dividas": dividas,
            "investivel": max(0.0, investivel),
        }
