"""Fonte plugável (ADR-278 §37) — discriminated union ``SourceRef`` de domínio PURO
(``pipeline/**`` não importa sqlalchemy): identifica a origem pela chave natural
(``document_id`` ou ``provider|account_id``), não pelo surrogate ``data_source.id``
(detalhe do adapter DB em ``backend/``). Variantes fixadas: ``document`` e ``feed``. O
``SourceAdapter`` é adiado até existir consumidor (Protocol sem implementador = dead code)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union

SourceKind = Literal["document", "feed"]


@dataclass(frozen=True)
class DocumentSource:
    """Origem = documento uploadado. Chave natural: ``document_id``."""

    document_id: str
    kind: Literal["document"] = "document"

    def __post_init__(self) -> None:
        if not self.document_id:
            raise ValueError("DocumentSource.document_id é obrigatório e não-vazio")


@dataclass(frozen=True)
class FeedSource:
    """Origem = feed externo (Open Finance etc). Chave natural: ``provider|account_id``."""

    provider: str
    account_id: str
    sync_id: str
    kind: Literal["feed"] = "feed"

    def __post_init__(self) -> None:
        if not (self.provider and self.account_id and self.sync_id):
            raise ValueError("FeedSource exige provider/account_id/sync_id não-vazios")


SourceRef = Union[DocumentSource, FeedSource]
