"""StageConfig — configuração imutável passada por parâmetro (ADR-088).

Substitui a reinicialização de globals (``scripts/pipeline_common._init_config``)
por um objeto **imutável** construído a partir do ``WorkspaceContext``. Pydantic
``ConfigDict(frozen=True)`` garante que a instância é thread-safe e pode ser
compartilhada entre múltiplos workers sem risco de mutação acidental.

Filosofia (R11):

    | Objeto               | Padrão                | Motivo                     |
    |----------------------|-----------------------|----------------------------|
    | Campos primitivos    | ``@dataclass(frozen)``| Imutabilidade real         |
    | Campos dict/list     | Pydantic frozen       | Pydantic deep-copia        |

``StageConfig`` tem campos ``dict`` → Pydantic frozen.
``Money``, ``Transaction`` etc. (Fase 5) tem campos primitivos → dataclass frozen.

Fail-fast (M3): configs **obrigatórios** faltando levantam ``ConfigError``.
``or {}`` é usado apenas para configs opcionais (``goals``, ``scoring``,
``fiscal``), onde ausência é aceitável.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Optional

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext
    from pipeline.ports import ConfigStore


class ConfigError(RuntimeError):
    """Raised quando um config obrigatório está ausente ou malformado."""


class StageConfig(BaseModel):
    """Configuração imutável passada por parâmetro.

    Thread-safe: instância pode ser compartilhada entre múltiplos workers sem
    risco de mutação acidental. Pydantic ``frozen=True`` garante imutabilidade
    real — atribuição direta ou ``model.field = ...`` levantam
    ``ValidationError``.

    Construção: usar :meth:`from_context` com um ``WorkspaceContext`` real ou
    :meth:`empty` para testes de domínio que não precisam de config.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    family_members: dict = {}
    pipeline: dict = {}
    institutions: dict = {}
    categorization: dict = {}
    goals: dict = {}
    scoring: dict = {}
    fiscal: dict = {}
    # ConfigStore boundary (ADR-134, Sprint A7.0) — A7.1 popula em
    # backend/app/services/pipeline_adapter.py com DBConfigStore. Default
    # None preserva compat: chamadas antigas continuam usando _init_config /
    # materialize_config até A7.5.
    config_store: Optional["ConfigStore"] = None

    # Configs cuja ausência levanta ``ConfigError`` em ``from_context``.
    REQUIRED: ClassVar[frozenset[str]] = frozenset(
        {
            "family_members",
            "pipeline",
            "institutions",
            "categorization",
        }
    )

    @classmethod
    def from_context(cls, ctx: "WorkspaceContext") -> "StageConfig":
        """Constrói ``StageConfig`` a partir de um ``WorkspaceContext``.

        Campos obrigatórios (:attr:`REQUIRED`) ausentes → ``ConfigError``.
        Campos opcionais ausentes → ``{}``.
        """

        def _load(name: str, *, required: bool) -> dict:
            data = ctx.load_config(f"{name}.json")
            if not data and required:
                # Tenta reler com ``required=True`` para distinguir ausência
                # total (FileNotFoundError) de conteúdo vazio.
                raise ConfigError(
                    f"Config obrigatório ausente: '{name}.json' não encontrado "
                    f"em {ctx.config_dir} (nem em config_overrides)"
                )
            return data or {}

        return cls(
            family_members=_load("family_members", required=True),
            pipeline=_load("pipeline", required=True),
            institutions=_load("institutions", required=True),
            categorization=_load("categorization", required=True),
            goals=_load("goals", required=False),
            scoring=_load("scoring", required=False),
            fiscal=_load("parametros_fiscais", required=False),
        )

    @classmethod
    def empty(cls) -> "StageConfig":
        """Instância com todos os configs vazios — para testes unitários."""
        return cls()
