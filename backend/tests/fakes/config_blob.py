"""Fakes in-memory de ``ConfigBlobRepository`` e do defaults loader.

Implementam os Protocols declarados em
``backend.app.application.config_blob._protocols`` via duck typing.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.app.models.config_blob import (
    InstitutionConfig,
    PipelineConfig,
    ReportLayout,
)


class FakeConfigBlobRepository:
    def __init__(self) -> None:
        # chave: (workspace_id, model_class.__name__)
        self._blobs: dict[tuple[str, str], dict[str, Any]] = {}

    async def get_config_json(
        self, workspace_id: str, model_class: type
    ) -> Optional[dict[str, Any]]:
        return self._blobs.get((workspace_id, model_class.__name__))

    async def upsert(
        self,
        workspace_id: str,
        model_class: type,
        config_json: dict[str, Any],
    ) -> Any:
        self._blobs[(workspace_id, model_class.__name__)] = config_json
        # Retorna uma instância do model (como o repo real) — atributo
        # ``config_json`` é o que os use cases leem.
        return model_class(workspace_id=workspace_id, config_json=config_json)


class FakeGlobalDefaultsLoader:
    """Devolve dicts fixos (configuráveis no construtor) em vez de tocar
    o disco — satisfaz ``GlobalDefaultsLoaderProtocol``.
    """

    def __init__(
        self,
        *,
        json_defaults: Optional[dict[str, dict[str, Any]]] = None,
        yaml_defaults: Optional[dict[str, dict[str, Any]]] = None,
    ) -> None:
        self._json = json_defaults or {}
        self._yaml = yaml_defaults or {}

    def load_json(self, name: str) -> dict[str, Any]:
        return self._json.get(name, {})

    def load_yaml(self, name: str) -> dict[str, Any]:
        return self._yaml.get(name, {})


__all__ = [
    "FakeConfigBlobRepository",
    "FakeGlobalDefaultsLoader",
    "InstitutionConfig",
    "PipelineConfig",
    "ReportLayout",
]
