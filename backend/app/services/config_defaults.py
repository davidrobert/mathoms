"""Helpers para ler defaults globais de ``config/`` (fallback quando o
workspace ainda não tem persistência no DB).

Compartilhado entre ``config.py``, ``family_members.py`` e ``categories.py``
— evita duplicar o loader por router (A6e.3).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from backend.app.core.config import settings


def _global_config_dir() -> Path:
    return settings.PIPELINE_ROOT / "config"


def load_global_json(name: str) -> dict[str, Any]:
    """Lê ``config/<name>`` (JSON); dict vazio se ausente."""
    path = _global_config_dir() / name
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_global_yaml(name: str) -> dict[str, Any]:
    """Lê ``config/<name>`` (YAML); dict vazio se ausente ou vazio."""
    path = _global_config_dir() / name
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ConfigDefaultsLoader:
    """Adapter que implementa ``GlobalDefaultsLoaderProtocol`` (A6e.3b).

    Envolve ``load_global_json``/``load_global_yaml`` nos nomes esperados
    pelo Protocol (``load_json``/``load_yaml``) — evita renomear os
    module-level helpers (múltiplos call-sites fora deste pacote).
    """

    @staticmethod
    def load_json(name: str) -> dict[str, Any]:
        return load_global_json(name)

    @staticmethod
    def load_yaml(name: str) -> dict[str, Any]:
        return load_global_yaml(name)
