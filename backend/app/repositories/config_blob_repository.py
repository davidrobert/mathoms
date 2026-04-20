"""ConfigBlobRepository — CRUD async para os 3 blobs de config por workspace.

Os três modelos (``PipelineConfig``, ``InstitutionConfig``, ``ReportLayout``)
são **estruturalmente idênticos**: ``id`` + ``workspace_id`` (unique) +
``config_json`` (dict opaco) + ``updated_at``. Este repositório é
**genérico** — recebe a classe do modelo como parâmetro e encapsula o
padrão comum:

- Upsert por ``workspace_id`` (há no máximo uma linha por workspace de
  cada tipo, garantido pelo ``unique=True`` do schema).
- Leitura com fallback para o disco (``config/pipeline.json``,
  ``institutions.json``, ``report_layout.yaml``) delegada ao caller — o
  repositório NÃO conhece defaults do disco, isso é responsabilidade do
  use case (manter SRP / ISP).
- Nenhum commit dentro do repo — caller é dono do boundary transacional.
  Isso permite compor import de múltiplos blobs numa só transação (como
  faz ``POST /config/import``).

R13 (ADR-101): toda query inclui ``workspace_id`` no predicado — multi-
tenancy é invariante.

Uso::

    repo = ConfigBlobRepository(session)
    cfg = await repo.get(workspace_id, PipelineConfig)
    if cfg is None:
        ...  # caller decide se carrega default do disco
    await repo.upsert(workspace_id, PipelineConfig, {"llm": {...}})
    await session.commit()   # caller commita
"""

from __future__ import annotations

from typing import Any, Optional, TypeVar, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.config_blob import (
    InstitutionConfig,
    PipelineConfig,
    ReportLayout,
)

# Os 3 modelos têm a mesma shape — mas não herdam de um protocolo comum.
# Usar Union explícito é mais honesto que um TypeVar genérico sem bound.
ConfigBlobModel = Union[PipelineConfig, InstitutionConfig, ReportLayout]
_T = TypeVar("_T", PipelineConfig, InstitutionConfig, ReportLayout)


class ConfigBlobRepository:
    """Single Responsibility: persistência dos 3 blobs de config do workspace.

    Não é um repositório "por agregado" no sentido estrito — é um repo
    **paramétrico** que atende 3 tabelas isomórficas. A alternativa de 3
    repositórios separados duplicaria ~30 linhas de código sem ganho
    semântico: os 3 blobs são "overrides" da config global e não têm
    comportamento próprio.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, workspace_id: str, model_class: type[_T]
    ) -> Optional[_T]:
        """Retorna a row de config para o workspace, ou ``None`` se não existir.

        Retornar ``None`` é o sinal para o caller carregar o default do
        disco (``_load_global_json`` / ``_load_global_yaml``). O repo não
        toca o filesystem.
        """
        result = await self._session.execute(
            select(model_class).where(model_class.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def get_config_json(
        self, workspace_id: str, model_class: type[_T]
    ) -> Optional[dict[str, Any]]:
        """Atalho de leitura: retorna direto o ``config_json`` ou ``None``.

        Útil para o helper de export que só precisa do dict, não da
        instância ORM.
        """
        cfg = await self.get(workspace_id, model_class)
        return cfg.config_json if cfg else None

    async def upsert(
        self,
        workspace_id: str,
        model_class: type[_T],
        config_json: dict[str, Any],
    ) -> _T:
        """Cria ou atualiza o blob para o workspace e retorna a instância.

        **Não faz commit** — caller é responsável. Semântica de
        ``upsert``: substitui o ``config_json`` inteiro (não faz merge).
        Se quiser merge, caller faz o merge antes de chamar aqui.

        Faz ``flush`` para que o id fique disponível se for uma criação
        (útil para o caller que quer logar / testar).
        """
        cfg = await self.get(workspace_id, model_class)
        if cfg is not None:
            cfg.config_json = config_json
        else:
            cfg = model_class(workspace_id=workspace_id, config_json=config_json)
            self._session.add(cfg)
        await self._session.flush()
        return cfg

    async def delete(
        self, workspace_id: str, model_class: type[_T]
    ) -> bool:
        """Remove o blob do workspace (idempotente).

        Retorna ``True`` se algo foi apagado, ``False`` se não havia blob
        para esse workspace. Não faz commit.
        """
        cfg = await self.get(workspace_id, model_class)
        if cfg is None:
            return False
        await self._session.delete(cfg)
        await self._session.flush()
        return True
