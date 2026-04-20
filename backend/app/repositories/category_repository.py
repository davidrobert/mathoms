"""CategoryRepository — CRUD async para o agregado ``Category``.

Encapsula todas as queries sobre ``categories`` + ``category_keywords`` para
que routers e use cases não construam SQL ad-hoc (R13). Toda query inclui
``workspace_id`` no predicado — multi-tenancy é invariante do agregado.

``CategoryKeyword`` é **parte deste agregado** (não tem ciclo de vida fora
de uma ``Category``; cascade delete no schema). Não existe
``CategoryKeywordRepository`` separado — ``replace_keywords`` cobre o caso.

Uso::

    repo = CategoryRepository(session)
    cats = await repo.list_by_workspace(ws_id)
    cat = await repo.get_by_id_with_keywords(ws_id, cat_id)
    cat = await repo.create(ws_id, code="moradia", name="Moradia", ...)
    await repo.replace_keywords(cat, ["aluguel", "condominio"])
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.category import Category, CategoryKeyword


class CategoryRepository:
    """Single Responsibility: persistência do agregado ``Category``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Category — queries
    # -------------------------------------------------------------------

    async def list_by_workspace(self, workspace_id: str) -> list[Category]:
        """Retorna categorias do workspace (com ``keywords`` eager-loaded).

        Ordenação: ``order`` ascendente, empate por ``code`` alfabético —
        mesma ordem usada no router legado.
        """
        result = await self._session.execute(
            select(Category)
            .where(Category.workspace_id == workspace_id)
            .options(selectinload(Category.keywords))
            .order_by(Category.order, Category.code)
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, workspace_id: str, category_id: str
    ) -> Optional[Category]:
        """Retorna categoria por id dentro do workspace (sem keywords)."""
        result = await self._session.execute(
            select(Category).where(
                Category.id == category_id,
                Category.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_keywords(
        self, workspace_id: str, category_id: str
    ) -> Optional[Category]:
        """Retorna categoria com ``keywords`` eager-loaded.

        ``execution_options(populate_existing=True)`` evita que instâncias já
        no identity map da sessão sirvam ``keywords`` stale (caso típico:
        caller acabou de atualizar as keywords e quer reler o agregado com
        estado atual).
        """
        result = await self._session.execute(
            select(Category)
            .where(
                Category.id == category_id,
                Category.workspace_id == workspace_id,
            )
            .options(selectinload(Category.keywords))
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_by_code(
        self, workspace_id: str, code: str
    ) -> Optional[Category]:
        """Retorna categoria por ``code`` dentro do workspace (único no ws)."""
        result = await self._session.execute(
            select(Category).where(
                Category.workspace_id == workspace_id,
                Category.code == code,
            )
        )
        return result.scalar_one_or_none()

    async def code_exists(
        self,
        workspace_id: str,
        code: str,
        *,
        exclude_id: Optional[str] = None,
    ) -> bool:
        """``True`` se já existe categoria com ``code`` no workspace.

        ``exclude_id`` permite validar unicidade em updates (ignora a própria
        categoria que está sendo atualizada).
        """
        stmt = select(Category.id).where(
            Category.workspace_id == workspace_id,
            Category.code == code,
        )
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        result = await self._session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    # -------------------------------------------------------------------
    # Category — commands
    # -------------------------------------------------------------------

    async def create(
        self,
        workspace_id: str,
        *,
        code: str,
        name: str,
        category_type: str,
        monthly_cap: Optional[float] = None,
        order: int = 0,
        keywords: Optional[list[str]] = None,
    ) -> Category:
        """Cria categoria + keywords e retorna instância com ``keywords`` eager.

        Pré-condição: caller já validou unicidade de ``code`` via
        :meth:`code_exists` (ou aceita que o DB constraint quebre).
        """
        cat = Category(
            workspace_id=workspace_id,
            code=code,
            name=name,
            category_type=category_type,
            monthly_cap=monthly_cap,
            order=order,
        )
        self._session.add(cat)
        await self._session.flush()

        for kw_text in keywords or []:
            self._session.add(
                CategoryKeyword(category_id=cat.id, keyword=kw_text)
            )
        await self._session.commit()

        # Refresh com keywords eager para manter invariante (agregado completo).
        result = await self._session.execute(
            select(Category)
            .where(Category.id == cat.id)
            .options(selectinload(Category.keywords))
        )
        return result.scalar_one()

    async def update(
        self,
        category: Category,
        *,
        updates: dict,
        keywords: Optional[list[str]] = None,
    ) -> Category:
        """Aplica ``updates`` em ``category`` (campos escalares) e opcionalmente
        substitui lista de ``keywords``.

        - ``updates`` é um dict já filtrado pelo caller (``exclude_unset``).
          Caller é responsável por validar unicidade de ``code`` se mudar.
        - ``keywords=None`` **não altera** a lista existente.
        - ``keywords=[]`` **apaga** todas as keywords (intencional: replace
          semantics do PUT).
        """
        for field, value in updates.items():
            setattr(category, field, value)

        if keywords is not None:
            await self.replace_keywords(category, keywords)

        await self._session.commit()
        result = await self._session.execute(
            select(Category)
            .where(Category.id == category.id)
            .options(selectinload(Category.keywords))
        )
        return result.scalar_one()

    async def delete(self, category: Category) -> None:
        """Remove a categoria e suas keywords.

        Apaga keywords explicitamente antes da categoria — não depende de
        ``ondelete='CASCADE'`` (inativo em SQLite de testes) nem de
        ``cascade='all, delete-orphan'`` (exige keywords eager).
        """
        await self._session.execute(
            sql_delete(CategoryKeyword).where(
                CategoryKeyword.category_id == category.id
            )
        )
        await self._session.delete(category)
        await self._session.commit()

    async def delete_all_in_workspace(self, workspace_id: str) -> int:
        """Remove todas as categorias de um workspace. Usado em import/replace.

        Keywords são deletadas antes via SQL bulk para evitar N queries. Não
        faz commit — deixa a cargo do caller (padrão do
        ``_import_categorization`` que chama delete + create em uma só txn).
        """
        cats = (
            (
                await self._session.execute(
                    select(Category).where(
                        Category.workspace_id == workspace_id
                    )
                )
            )
            .scalars()
            .all()
        )
        count = 0
        for cat in cats:
            await self._session.execute(
                sql_delete(CategoryKeyword).where(
                    CategoryKeyword.category_id == cat.id
                )
            )
            await self._session.delete(cat)
            count += 1
        await self._session.flush()
        return count

    # -------------------------------------------------------------------
    # Keywords — sub-entidade do agregado
    # -------------------------------------------------------------------

    async def replace_keywords(
        self, category: Category, keywords: list[str]
    ) -> None:
        """Substitui todas as keywords da categoria pelo conteúdo de ``keywords``.

        Usado em PUT /categories/{id} quando caller quer semântica de replace
        total. Não faz commit — o caller (``update``) decide o boundary.
        """
        await self._session.execute(
            sql_delete(CategoryKeyword).where(
                CategoryKeyword.category_id == category.id
            )
        )
        await self._session.flush()
        for kw_text in keywords:
            self._session.add(
                CategoryKeyword(category_id=category.id, keyword=kw_text)
            )
