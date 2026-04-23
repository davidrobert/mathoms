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
    e7_dir: Path = field(init=False)
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

    #: ArtifactStore injetável (ADR-083). Se ``None``, ``get_artifact_store()``
    #: devolve um :class:`DiskArtifactStore` apontando para ``self.root``.
    #: Stages devem usar ``ctx.get_artifact_store()`` em vez de acessar este
    #: campo diretamente, para manter a resolução lazy.
    artifact_store: Optional["ArtifactStore"] = field(default=None, repr=False)

    #: ADR-119 — mediana de duração (ms) por stage, calculada dos últimos runs
    #: bem-sucedidos do workspace. Populado pelo orchestrator (Celery task);
    #: vazio em CLI/testes. Stages emitem via ``emit_item_progress(...,
    #: estimated_duration_ms=ctx.stage_duration_estimates.get(stage))`` no
    #: primeiro evento da stage.
    stage_duration_estimates: Dict[str, int] = field(default_factory=dict, repr=False)

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
        self.e7_dir = self.processed_dir / "E7_review"
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

        Default: :class:`DiskArtifactStore` apontando para ``self.root``.
        Web/Celery: injetar um :class:`DBArtifactStore` via ``for_tenant`` ou
        pós-construção, antes de chamar os stages.

        Idempotente: a primeira chamada sem store pré-injetado cria um
        :class:`DiskArtifactStore` e o memoriza em ``self.artifact_store``.
        """
        if self.artifact_store is None:
            from pipeline.artifact_store import DiskArtifactStore

            self.artifact_store = DiskArtifactStore(self.root)
        return self.artifact_store

    def ensure_dirs(self) -> None:
        """Cria diretórios de output se não existirem."""
        for d in (
            self.processed_dir,
            self.e2_dir,
            self.e3_dir,
            self.e4_dir,
            self.e5_dir,
            self.e7_dir,
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
    ) -> WorkspaceContext:
        """Contexto para tenant web com config do banco de dados.

        Args:
            tenant_root: Root directory for this tenant's data.
            config: Dict overrides for pipeline config files.
            config_dir: External config directory (e.g. global project config/).
                        If None, defaults to tenant_root/config/.
            pipeline_run_id: Active pipeline run id — enables live ``stage_activity`` events.
            artifact_store: ``ArtifactStore`` pré-construído (ADR-083). ``None``
                faz ``get_artifact_store()`` instanciar um ``DiskArtifactStore``
                lazy na primeira chamada.
        """
        return cls(
            root=tenant_root,
            _config_dir_override=config_dir,
            config_overrides=config,
            pipeline_run_id=pipeline_run_id,
            artifact_store=artifact_store,
        )
