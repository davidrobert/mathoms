"""
Config Loader unificado — substitui as 6+ implementações de _load_json_config.

Usa WorkspaceContext quando disponível, fallback para leitura direta do disco.
Cache por contexto para evitar re-leituras desnecessárias.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


_disk_cache: Dict[str, dict] = {}


def load_config(
    name: str,
    *,
    ctx: Optional[WorkspaceContext] = None,
    config_dir: Optional[Path] = None,
    required: bool = False,
) -> dict:
    """Carrega config JSON por nome.

    Prioridade:
        1. ctx.load_config(name) se ctx fornecido (suporta overrides do DB)
        2. config_dir / name se config_dir fornecido
        3. Fallback: disco via PROJECT_DIR/config/ (retrocompat)

    Args:
        name: Nome do arquivo (ex: "pipeline.json")
        ctx: WorkspaceContext opcional
        config_dir: Path direto para diretório de config
        required: Se True, raises em vez de retornar {}

    Returns:
        Dict com a configuração.
    """
    if ctx is not None:
        return ctx.load_config(name, required=required)

    if config_dir is not None:
        return _load_from_disk(config_dir / name, required=required)

    project_dir = Path(__file__).resolve().parent.parent
    return _load_from_disk(project_dir / "config" / name, required=required)


def _load_from_disk(path: Path, *, required: bool = False) -> dict:
    """Carrega JSON do disco com cache."""
    cache_key = str(path)
    if cache_key in _disk_cache:
        return _disk_cache[cache_key]

    if not path.exists():
        if required:
            raise FileNotFoundError(f"Config não encontrado: {path}")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _disk_cache[cache_key] = data
        return data
    except (json.JSONDecodeError, OSError) as exc:
        if required:
            raise
        from pipeline.observability import get_logger

        get_logger("config_loader").warning(
            "config load failed",
            extra={"file": path.name, "error": str(exc)},
        )
        return {}


def clear_cache() -> None:
    """Limpa o cache de configs. Útil para testes e re-inicialização."""
    _disk_cache.clear()


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Lê um JSON qualquer do disco. Retorna None em caso de erro."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def write_json(path: Path, data: Dict[str, Any], *, indent: int = 2) -> bool:
    """Escreve JSON formatado. Retorna True se bem-sucedido."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except (OSError, TypeError):
        return False
