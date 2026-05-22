"""E4 categorizer adapter (Sessão A4a — Fase 7 foundation).

Orquestra os domain services do E4 sobre um :class:`ArtifactStore`, preparando
o terreno para o ``main_with_store`` do E4 (Sessão A4b). Escopo atual:

- Lê extratos E3 (`list_keys("E3")`).
- Classifica transações via :class:`TransactionClassifier` (A4a).
- Agrega em ``ReceitasUnified``/``DespesasUnified``/``FluxoMensal`` via
  :class:`CashFlowBuilder` (A4a).
- Lê baseline E1.5c se presente e aplica :class:`BaselineNormalizer` (A4a)
  para formato canônico.
- Lê posições E2 de investimento (glob equivalente em `list_keys`) e consolida
  via :class:`InvestmentsConsolidator` (A4a).

**Não** escreve em ``E4`` ainda — apenas retorna um
:class:`CategorizationResult` tipado. A serialização para o formato E4 legado
(7 artefatos) e a integração com `main_with_store` ficam para A4b.

Zero I/O além do ``store.read``/``list_keys``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from pipeline.artifact_store import ArtifactStore
from pipeline.domain.services.baseline_normalizer import (
    BaselineNormalizer,
    NormalizedBaseline,
)
from pipeline.domain.services.cash_flow_builder import CashFlow, CashFlowBuilder

_dedup_logger = logging.getLogger("mathoms.pipeline.dedup")
from pipeline.domain.services.categorization_service import CategorizationRulesV2
from pipeline.domain.services.investments_consolidator import (
    ConsolidatedInvestments,
    InvestmentsConsolidator,
)
from pipeline.domain.services.transaction_classifier import (
    ClassifiedTransaction,
    ClassifierConfig,
    TransactionClassifier,
)

# =============================================================================
# Config do adapter
# =============================================================================


# Input stages para posições E2. No DiskArtifactStore, todos apontam para
# ``E2_extracts/``; o adapter deduplica por key.
_E2_INPUT_STAGES: tuple[str, ...] = ("E2-extratos", "E2-faturas", "E2-llm")

# Stage do baseline consolidado (E1.5c) — key convencionada.
_BASELINE_STAGE = "E1.5c"
_BASELINE_KEY = "baseline_patrimonial"

# Tipos de extract E2 que representam posição de investimento (paridade com
# ``build_investimentos_unified``: *investimentosposicao*, *carteira*,
# *cdbresumo*).
_INVESTMENT_POSITION_TYPES = (
    "investimentosposicao",
    "carteirarendafixa",
    "cdbresumo",
)


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class CategorizationResult:
    """Saída do ``E4CategorizerAdapter.categorize_via_store``.

    Tudo tipado; o serializer legado (A4b) consumirá estes campos para
    produzir os 7 artefatos E4 em disco/DB.
    """

    classified: tuple[ClassifiedTransaction, ...]
    cash_flow: CashFlow
    baseline: NormalizedBaseline
    investments: ConsolidatedInvestments
    accounts_loaded: int
    skipped_accounts: int = 0


# =============================================================================
# Adapter
# =============================================================================


class E4CategorizerAdapter:
    """Orquestra E3 → classify → aggregate sobre ``ArtifactStore``.

    Cada dependência é injetável (R9/ISP). Defaults são seguros: testes que
    não têm baseline ou posições E2 obtêm estruturas vazias mas consistentes.
    """

    def __init__(
        self,
        classifier: TransactionClassifier,
        *,
        cash_flow_builder: CashFlowBuilder | None = None,
        baseline_normalizer: BaselineNormalizer | None = None,
        investments_consolidator: InvestmentsConsolidator | None = None,
    ) -> None:
        self._classifier = classifier
        self._cash_flow_builder = cash_flow_builder or CashFlowBuilder()
        self._baseline_normalizer = baseline_normalizer or BaselineNormalizer()
        self._investments_consolidator = investments_consolidator or InvestmentsConsolidator()

    # -- Factory (conveniência p/ main_with_store na Sessão A4b) --

    @classmethod
    def from_configs(
        cls,
        *,
        categorization: dict | None = None,
        family: dict | None = None,
        learned_rules_v2: CategorizationRulesV2 | None = None,
    ) -> "E4CategorizerAdapter":
        """Constrói o adapter a partir dos dicts de config.

        ``learned_rules_v2`` (ADR-186 §D5 · A12.P2): regras workspace-aprendidas
        — injetar quando ``ctx.workspace_id`` está disponível (via adapter
        ``backend/app/services/categorization_rules_adapter.py``). Default
        ``None`` preserva paridade legado (workspaces sem regras).
        """
        from dataclasses import replace

        from pipeline.domain.services.investments_consolidator import (
            InvestmentsConsolidatorConfig,
        )

        classifier_cfg = ClassifierConfig.from_configs(
            categorization=categorization,
            family=family,
        )
        if learned_rules_v2 is not None:
            classifier_cfg = replace(classifier_cfg, learned_rules_v2=learned_rules_v2)
        inv_cfg = InvestmentsConsolidatorConfig.from_family(family=family)
        return cls(
            classifier=TransactionClassifier(classifier_cfg),
            investments_consolidator=InvestmentsConsolidator(inv_cfg),
        )

    # -- Loading --

    def load_reconciled_accounts(self, store: ArtifactStore) -> list[dict]:
        """Lê todos os extratos E3 reconciliados do store."""
        out: list[dict] = []
        for key in store.list_keys("E3"):
            data = store.read("E3", key)
            if isinstance(data, dict) and data.get("transacoes"):
                out.append(data)
        return out

    def load_baseline(self, store: ArtifactStore) -> dict | None:
        """Lê baseline E1.5c do store; ``None`` se ausente."""
        return store.read(_BASELINE_STAGE, _BASELINE_KEY)

    def load_investment_positions(
        self, store: ArtifactStore, *, input_stages: Iterable[str] | None = None
    ) -> list[dict]:
        """Lê artefatos E2 que representam posições de investimento.

        Filtra por ``tipo`` conhecido (equivalente ao glob do legado sobre
        nomes de arquivo). Deduplica por key entre stages que mapeiam para
        o mesmo diretório (Disk).
        """
        stages = tuple(input_stages) if input_stages else _E2_INPUT_STAGES
        seen_keys: set[str] = set()
        out: list[dict] = []
        for stage in stages:
            for key in store.list_keys(stage):
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                data = store.read(stage, key)
                if not isinstance(data, dict):
                    continue
                tipo = str(data.get("tipo") or "").lower()
                tipo_documento = str(data.get("tipo_documento") or "").lower()
                # ADR-244: informes de rendimentos (snapshot 31/12 do banco)
                # também contêm posições de investimento (ex.: CDB Itaú no
                # informe IR, R$ 290k descartados antes desta lane). Sem isto,
                # `total_por_membro` em E5 só capturava `investment_report`
                # (Binance/PJ) e ignorava o snapshot fiscal anual dos bancos.
                has_investimentos = bool(data.get("investimentos"))
                is_investment_doc = (
                    tipo_documento in ("investment_report", "informe_rendimentos")
                    and has_investimentos
                )
                if tipo not in _INVESTMENT_POSITION_TYPES and not is_investment_doc:
                    continue
                # Injeta source name para o consolidador.
                from pipeline.artifact_store import stage_suffix

                try:
                    source = key + stage_suffix(stage)
                except KeyError:
                    source = key
                out.append({**data, "_source": source})
        return out

    # -- Orquestração --

    def categorize_via_store(self, store: ArtifactStore) -> CategorizationResult:
        """Pipeline E4 end-to-end em memória:

        1. Lê todos os E3.
        2. Classifica transações.
        3. Agrega via ``CashFlowBuilder``.
        4. Lê + normaliza baseline.
        5. Lê + consolida posições de investimento.

        Returns:
            :class:`CategorizationResult` tipado. A escrita em ``E4`` fica
            para o ``main_with_store`` (Sessão A4b) quando o serializer
            legado existir.
        """
        accounts = self.load_reconciled_accounts(store)
        classified = self._classifier.classify_all(accounts)
        cash_flow = self._cash_flow_builder.build(classified)

        # ADR-248 — telemetria estruturada do dedup cross-document. Sem PII
        # (não logamos descrição nem valor exato; só counts + sample hashes).
        if cash_flow.dedup_report.collapsed_count > 0:
            _dedup_logger.info(
                "mathoms.pipeline.dedup.cross_document",
                extra={
                    "stage": "categorize_transactions",
                    "workspace_id": getattr(store, "workspace_id", None),
                    "pipeline_run_id": getattr(store, "pipeline_run_id", None),
                    **cash_flow.dedup_report.to_log_dict(),
                },
            )

        baseline_raw = self.load_baseline(store)
        baseline_normalized = self._baseline_normalizer.normalize(baseline_raw)

        positions = self.load_investment_positions(store)
        investments = self._investments_consolidator.consolidate(positions)

        return CategorizationResult(
            classified=tuple(classified),
            cash_flow=cash_flow,
            baseline=baseline_normalized,
            investments=investments,
            accounts_loaded=len(accounts),
        )
