"""
WorkspaceContext — abstração central de paths e configuração do pipeline.

Fornece paths e configs injetáveis para cada etapa. Permite:
- CLI: WorkspaceContext.default() → usa layout atual do projeto
- Web: WorkspaceContext.for_tenant(root, config) → multi-tenant
- Testes: WorkspaceContext(root=tmp_dir, config_overrides={...}) → isolado
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from pipeline.artifact_store import ArtifactStore
    from pipeline.llm.call_hooks import LLMCallHooks
    from pipeline.llm.institution_catalog import InstitutionCatalogProvider
    from pipeline.llm.metrics import LLMMetricsEmitter
    from pipeline.llm.response_cache import LLMResponseCache
    from pipeline.ports import (
        ConfigStore,
        EconomicAssumptionsResolver,
        PropertyIdentityResolver,
        PropertyOverridesResolver,
        PropertySupersessionWriter,
    )


@dataclass
class WorkspaceContext:
    """Contexto de execução do pipeline: paths e configuração injetáveis."""

    root: Path

    # Optional config_dir override — when tenant root doesn't contain config/,
    # point to the global project config/ instead.
    _config_dir_override: Optional[Path] = field(default=None, repr=False)

    # Paths derivados (calculados no __post_init__)
    config_dir: Path = field(init=False)
    data_dir: Path = field(init=False)
    processed_dir: Path = field(init=False)
    e2_dir: Path = field(init=False)
    e3_dir: Path = field(init=False)
    e4_dir: Path = field(init=False)
    e5_dir: Path = field(init=False)
    output_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)
    members_dir: Path = field(init=False)
    inbox_dir: Path = field(init=False)
    scratch_dir: Path = field(init=False)

    config_overrides: Optional[Dict[str, Any]] = field(default=None, repr=False)

    #: When set (web/Celery run), stages may emit fine-grained ``stage_activity`` WS events.
    pipeline_run_id: Optional[str] = field(default=None, repr=False)

    #: Incremental mode — E0/E2 stages only process new (unprocessed) documents.
    #: E3→E7 always run full over all existing extracts.
    incremental: bool = False
    #: Stored paths of new documents (relative to tenant root). Used by E0/E2 to filter.
    incremental_doc_paths: List[str] = field(default_factory=list)

    #: ArtifactStore injetável (ADR-083 · ADR-212 PR3b). Obrigatório em runtime:
    #: ``get_artifact_store()`` raise ``RuntimeError`` se ``None``. Backend Celery
    #: passa ``DBArtifactStore``; testes passam ``InMemoryArtifactStore``.
    #: ``Optional`` aqui permite construção em duas fases (instanciar + injetar)
    #: — mas qualquer chamada a ``get_artifact_store()`` exige store presente.
    artifact_store: Optional["ArtifactStore"] = field(default=None, repr=False)

    #: Workspace identifier — required for ``ConfigStore`` reads (ADR-134).
    #: ``None`` em CLI/testes locais; backend Celery preenche em ``for_tenant``.
    workspace_id: Optional[str] = field(default=None, repr=False)

    #: ``ConfigStore`` injetável (ADR-134, Sprint A7.1). ``None`` → stages caem no
    #: fallback de disco via ``load_config()``. Backend popula com
    #: :class:`DBConfigStore` em :func:`pipeline_task._setup_run_context`.
    config_store: Optional["ConfigStore"] = field(default=None, repr=False)

    #: ``PropertyIdentityResolver`` injetável (ADR-215, P2). Permite ao
    #: consolidador E1.5c emitir `property_id` UUID estável cross-IRPFs.
    #: ``None`` → consolidador pula a etapa (compat com testes/CLI legados).
    property_identity_resolver: Optional["PropertyIdentityResolver"] = field(
        default=None, repr=False
    )

    #: ``PropertySupersessionWriter`` injetável (ADR-324). Permite ao
    #: consolidador E1.5c reconciliar no DB a supersessão das perdedoras do
    #: dedup ADR-246/265. ``None`` → step 3b não poda (compat testes/CLI).
    property_supersession_writer: Optional["PropertySupersessionWriter"] = field(
        default=None, repr=False
    )

    #: ``EconomicAssumptionsResolver`` injetável (ADR-219, wave 2). Permite ao
    #: E5 snapshotar premissas econômicas vigentes no payload (auditoria
    #: fiduciária). ``None`` → E5 emite ``premissas_economicas`` ausente
    #: (UI degrada — compat com testes/CLI legados).
    economic_assumptions_resolver: Optional["EconomicAssumptionsResolver"] = field(
        default=None, repr=False
    )

    #: ``PropertyOverridesResolver`` injetável (ADR-215 §1). Permite ao E5
    #: ler `workspace_property_overrides` e injetar
    #: `PatrimonioConfig.property_classification_overrides` — fonte ÚNICA do
    #: lazy split (`PatrimonioCalculator._split_imoveis`) pós-sunset do
    #: fallback `residencia_keyword`. ``None`` → calculator/analyzers usam
    #: dict vazio (todos os imóveis caem em cat_2 — esperado para workspace
    #: sem classificação via UI ainda).
    property_overrides_resolver: Optional["PropertyOverridesResolver"] = field(
        default=None, repr=False
    )

    #: ADR-222 — toggle per-workspace controlando se cat_2 (imóveis de renda)
    #: entra em ``investivel_efetivo`` (invariante ADR-142). Default ``True``
    #: preserva comportamento do legado ``config/pipeline.json:14`` para
    #: workspaces/CLI sem injeção explícita. Backend popula com o valor real
    #: lido de ``workspaces.imoveis_no_if`` em ``_setup_run_context``.
    imoveis_no_if: bool = field(default=True)

    #: ADR-173 — hooks de FinOps no choke-point LLM (budget hard-stop +
    #: ``LLMCallLog``). Backend injeta ``LLMBudgetService`` em
    #: ``_setup_run_context``; ``None`` em CLI/testes → sem cap, sem log.
    llm_call_hooks: Optional["LLMCallHooks"] = field(default=None, repr=False)

    #: ADR-307 — cache de resposta LLM opt-in (Redis via backend); ``None``
    #: em CLI/testes → todo lookup é miss, sem write.
    llm_response_cache: Optional["LLMResponseCache"] = field(default=None, repr=False)

    #: A33.l7 (ADR-110) — métricas OTLP ``mathoms.llm.*`` no choke-point.
    #: Backend injeta ``OtelLLMMetrics`` apenas quando ``OTEL_EXPORTER_OTLP_ENDPOINT``
    #: existe; ``None`` (CLI/testes/opt-out) → zero overhead.
    llm_metrics_emitter: Optional["LLMMetricsEmitter"] = field(default=None, repr=False)

    #: A33.l8 (ADR-137) — catálogo de instituições para injection nos user
    #: prompts LLM (``e1_members``, ``e2_llm``, ``apolice``). Backend injeta
    #: ``DBInstitutionCatalogProvider`` em ``run_context_factory``; ``None``
    #: em CLI/testes → bloco de fallback documentado (sem lista hardcoded).
    institution_catalog_provider: Optional["InstitutionCatalogProvider"] = field(
        default=None, repr=False
    )

    #: ADR-119 — mediana de duração (ms) por stage, calculada dos últimos runs
    #: bem-sucedidos do workspace. Populado pelo orchestrator (Celery task);
    #: vazio em CLI/testes. Stages emitem via ``emit_item_progress(...,
    #: estimated_duration_ms=ctx.stage_duration_estimates.get(stage))`` no
    #: primeiro evento da stage.
    stage_duration_estimates: Dict[str, int] = field(default_factory=dict, repr=False)

    #: ADR-323 — circuit-breaker run-scoped do executor HTTP (F2 cutover Go).
    #: Vira ``True`` no primeiro stage que ``FallbackPipelineClient`` degrada
    #: para InProcess (shell down / 5xx); os stages seguintes vão direto ao
    #: InProcess sem re-sondar o Go. Estado por-run (nunca no singleton do
    #: client) — preserva statelessness ADR-111 §1.b.
    shell_degraded: bool = field(default=False, repr=False)

    def __post_init__(self):
        self.root = Path(self.root).resolve()
        if self._config_dir_override is not None:
            self.config_dir = Path(self._config_dir_override).resolve()
        else:
            self.config_dir = self.root / "config"
        self.data_dir = self.root / "data"
        self.processed_dir = self.root / "processed"
        self.e2_dir = self.processed_dir / "E2_extracts"
        self.e3_dir = self.processed_dir / "E3_reconciled"
        self.e4_dir = self.processed_dir / "E4_unified"
        self.e5_dir = self.processed_dir / "E5_analysis"
        self.output_dir = self.root / "output"
        self.logs_dir = self.root / "logs"
        self.members_dir = self.root / "members"
        self.inbox_dir = self.root / "inbox"
        self.scratch_dir = self.root / "_scratch"

    def load_config(self, name: str, *, required: bool = False) -> dict:
        """Carrega config por nome. Prioriza override (dict/DB), fallback p/ disco.

        Args:
            name: Nome do arquivo de config (ex: "pipeline.json", "family_members.json")
            required: Se True, raises FileNotFoundError quando não encontrado.

        Returns:
            Dict com a configuração. {} se não encontrado e não required.
        """
        if self.config_overrides and name in self.config_overrides:
            return self.config_overrides[name]

        path = self.config_dir / name
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Config não encontrado: {path}")
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            if required:
                raise
            return {}

    def get_artifact_store(self) -> "ArtifactStore":
        """Retorna o ``ArtifactStore`` ativo para esta run.

        ADR-212 PR3b: ``artifact_store`` deve ser injetado explicitamente
        (Web/Celery via ``DBArtifactStore``; testes via
        ``InMemoryArtifactStore``). Lazy-default de ``DiskArtifactStore``
        foi removido — caminho disco deixou de existir.
        """
        if self.artifact_store is None:
            raise RuntimeError(
                "WorkspaceContext.artifact_store não foi injetado. "
                "Backend Celery deve passar DBArtifactStore; testes devem "
                "passar InMemoryArtifactStore. ADR-212 PR3b removeu o "
                "default implícito de DiskArtifactStore."
            )
        return self.artifact_store

    def ensure_dirs(self) -> None:
        """Cria diretórios de output se não existirem."""
        for d in (
            self.processed_dir,
            self.e2_dir,
            self.e3_dir,
            self.e4_dir,
            self.e5_dir,
            self.processed_dir / "E7_review",
            self.output_dir,
            self.logs_dir,
            self.scratch_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    # -- Factory methods --

    @classmethod
    def default(cls) -> WorkspaceContext:
        """Contexto padrão: raiz do projeto atual (retrocompatível com CLI)."""
        project_dir = Path(__file__).resolve().parent.parent
        return cls(root=project_dir)

    @classmethod
    def for_tenant(
        cls,
        tenant_root: Path,
        config: Optional[Dict[str, Any]] = None,
        config_dir: Optional[Path] = None,
        pipeline_run_id: Optional[str] = None,
        artifact_store: Optional["ArtifactStore"] = None,
        workspace_id: Optional[str] = None,
        config_store: Optional["ConfigStore"] = None,
        property_identity_resolver: Optional["PropertyIdentityResolver"] = None,
        property_supersession_writer: Optional["PropertySupersessionWriter"] = None,
        economic_assumptions_resolver: Optional["EconomicAssumptionsResolver"] = None,
        property_overrides_resolver: Optional["PropertyOverridesResolver"] = None,
        imoveis_no_if: bool = True,
        institution_catalog_provider: Optional["InstitutionCatalogProvider"] = None,
    ) -> WorkspaceContext:
        """Contexto para tenant web com config do banco de dados.

        Args:
            tenant_root: Root directory for this tenant's data.
            config: Dict overrides for pipeline config files.
            config_dir: External config directory (e.g. global project config/).
                        If None, defaults to tenant_root/config/.
            pipeline_run_id: Active pipeline run id — enables live ``stage_activity`` events.
            artifact_store: ``ArtifactStore`` pré-construído (ADR-083 · ADR-212).
                Obrigatório quando os stages forem executados — ``get_artifact_store()``
                raise ``RuntimeError`` se ``None``.
            workspace_id: ID do workspace — necessário para leitura via ``config_store``
                (ADR-134, A7.1).
            config_store: ``ConfigStore`` pré-construído (ADR-134). ``None`` faz
                stages caírem no fallback ``ctx.load_config()`` (disco/overrides).
        """
        return cls(
            root=tenant_root,
            _config_dir_override=config_dir,
            config_overrides=config,
            pipeline_run_id=pipeline_run_id,
            artifact_store=artifact_store,
            workspace_id=workspace_id,
            config_store=config_store,
            property_identity_resolver=property_identity_resolver,
            property_supersession_writer=property_supersession_writer,
            economic_assumptions_resolver=economic_assumptions_resolver,
            property_overrides_resolver=property_overrides_resolver,
            imoveis_no_if=imoveis_no_if,
            institution_catalog_provider=institution_catalog_provider,
        )
