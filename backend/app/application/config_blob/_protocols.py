"""Protocols consumidos pelos use cases de ``config_blob``.

``ConfigBlobRepositoryProtocol`` é **paramétrico** — mesmo repo atende os
3 modelos isomórficos (Pipeline, Institution, ReportLayout). Conceitualmente
um repo por agregado, mas as 3 rows compartilham shape (``config_json`` opaco)
e ciclo de vida (upsert 1:1 por workspace), logo o SQLAlchemy real
(``backend.app.repositories.config_blob_repository``) é um único módulo —
este Protocol espelha essa decisão.

``GlobalDefaultsLoaderProtocol`` isola os reads de ``config/*.json|.yaml``
(side-effect de filesystem) para que use cases não dependam do disco em
teste. Fake default carrega ``{}`` ou shape testável.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol

from backend.app.models.config_blob import (
    InstitutionConfig,
    PipelineConfig,
    ReportLayout,
)

ConfigBlobModel = PipelineConfig | InstitutionConfig | ReportLayout


class ConfigBlobRepositoryProtocol(Protocol):
    async def get_config_json(
        self, workspace_id: str, model_class: type[ConfigBlobModel]
    ) -> Optional[dict[str, Any]]: ...

    async def upsert(
        self,
        workspace_id: str,
        model_class: type[ConfigBlobModel],
        config_json: dict[str, Any],
    ) -> ConfigBlobModel: ...


class GlobalDefaultsLoaderProtocol(Protocol):
    """Lê defaults globais (``config/pipeline.json`` etc.).

    Implementado em produção por funções em
    ``backend.app.services.config_defaults`` via wrapper; em teste, por
    fake que devolve dict fixo.
    """

    def load_json(self, name: str) -> dict[str, Any]: ...

    def load_yaml(self, name: str) -> dict[str, Any]: ...
