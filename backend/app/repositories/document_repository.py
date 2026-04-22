"""DocumentRepository — CRUD async para o agregado ``Document``.

Encapsula todas as queries sobre ``documents`` para que o router e os use
cases não construam SQL ad-hoc (R13). Toda query inclui ``workspace_id``
no predicado — multi-tenancy é invariante do agregado.

R14 (ADR-101): repo **não faz commit** — caller é dono do boundary
transacional. Isso é essencial no upload, onde cada arquivo entra num
``begin_nested()`` e a unique-index race contra
``ux_documents_workspace_content_hash`` precisa que o caller decida se
fecha savepoint ou rollback.

Uso::

    repo = DocumentRepository(session)
    docs = await repo.list(ws_id, statuses=[DocumentStatus.ready])
    doc = await repo.get_by_id(ws_id, doc_id)
    existing = await repo.find_fuzzy_duplicate_id(
        ws_id, doc_type=DocumentType.bank_statement, bank_code="itau",
        period="202601", exclude_id=doc.id,
    )
    await repo.add(new_doc)
    await session.commit()   # caller commita

Escopo do slice A6e.5: o repo cobre **apenas queries do router de
documentos**. ``document_processor.py``, ``document_pipeline_sync.py`` e
``tasks/pipeline_task.py`` ainda acessam ``Document`` diretamente — sua
migração é escopo de slices futuros (use-case layer R15).
"""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document, DocumentStatus, DocumentType


class DocumentRepository:
    """Single Responsibility: persistência do agregado ``Document``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def list(
        self,
        workspace_id: str,
        *,
        statuses: Optional[Iterable[DocumentStatus]] = None,
        doc_type: Optional[DocumentType] = None,
    ) -> list[Document]:
        """Lista documentos do workspace, opcionalmente filtrados.

        - ``statuses=None`` não filtra; lista com 1 elemento vira ``==``,
          lista com >1 vira ``IN``. Sem elementos → query vazia (retorna
          ``[]`` sem bater no DB).
        - ``doc_type`` aceita enum ou ``None``.
        - Ordenação: ``uploaded_at DESC`` — paridade com o router legado.
        """
        stmt = select(Document).where(Document.workspace_id == workspace_id)

        if statuses is not None:
            seq = list(statuses)
            if not seq:
                return []
            if len(seq) == 1:
                stmt = stmt.where(Document.status == seq[0])
            else:
                stmt = stmt.where(Document.status.in_(seq))

        if doc_type is not None:
            stmt = stmt.where(Document.doc_type == doc_type)

        stmt = stmt.order_by(Document.uploaded_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, workspace_id: str, document_id: str) -> Optional[Document]:
        """Retorna documento por id dentro do workspace (ou ``None``)."""
        result = await self._session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_content_hash(self, workspace_id: str, content_hash: str) -> Optional[Document]:
        """Retorna documento com o hash exato no workspace (ou ``None``).

        Usado para dedupe exato — o ``ux_documents_workspace_content_hash``
        já bloqueia INSERTs duplicados; esse método é útil em use cases
        que querem **detectar sem inserir** (ex.: pré-checagem antes de
        gastar LLM).
        """
        result = await self._session.execute(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.content_hash == content_hash,
            )
        )
        return result.scalar_one_or_none()

    async def find_fuzzy_duplicate_id(
        self,
        workspace_id: str,
        *,
        doc_type: DocumentType,
        bank_code: str,
        period: str,
        exclude_id: Optional[str] = None,
    ) -> Optional[str]:
        """Retorna o id de outro documento no ws com mesmo triplo (ou ``None``).

        Fuzzy dedupe = mesmo ``(doc_type, bank_code, period)`` mas hash
        diferente. O caller decide se marca ``possible_duplicate_of_id``
        + ``needs_review=True`` — o repo só informa a existência.

        ``exclude_id`` ignora um id específico (normalmente o próprio doc
        recém-criado). Pré-condição: ``doc_type``, ``bank_code`` e
        ``period`` são todos não-vazios — caller deve filtrar ``other``
        e ``None`` antes de invocar (regra de negócio, não do repo).
        """
        stmt = (
            select(Document.id)
            .where(
                Document.workspace_id == workspace_id,
                Document.doc_type == doc_type,
                Document.bank_code == bank_code,
                Document.period == period,
            )
            .limit(1)
        )
        if exclude_id is not None:
            stmt = stmt.where(Document.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_non_error(self, workspace_id: str) -> list[Document]:
        """Lista todos os documentos do workspace em estado ≠ ``error``.

        Usado pelo ``rebuild_fuzzy_duplicate_pointers`` após reclassify
        em lote — docs em erro não participam da detecção fuzzy.
        """
        result = await self._session.execute(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.status != DocumentStatus.error,
            )
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Commands — nenhum faz commit (ADR-101 R14)
    # -------------------------------------------------------------------

    async def add(self, document: Document, *, flush: bool = True) -> Document:
        """Registra ``document`` na sessão; retorna a instância.

        ``flush=True`` (default) emite o ``INSERT`` agora para que:
        - o ``id`` fique disponível antes do commit (uploads em lote
          precisam do id para fuzzy-dedupe cross-referencial);
        - o ``IntegrityError`` da unique index apareça aqui — o caller
          pode capturar e dar rollback no savepoint em vez de descobrir
          só no commit final.

        Caller é sempre responsável pelo ``session.commit()``.
        """
        self._session.add(document)
        if flush:
            await self._session.flush()
        return document

    async def delete(self, document: Document) -> None:
        """Remove ``document`` da sessão (ORM delete, sem commit).

        A remoção do arquivo em disco é responsabilidade do caller
        (``StorageService``) — repo só fala DB.
        """
        await self._session.delete(document)
