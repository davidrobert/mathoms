"""Use cases do agregado ``Category`` (ADR-101 R15).

Endpoints REST de ``/workspaces/{id}/config/categories`` delegam aqui.
Erros de domínio são traduzidos para HTTP no router (por handlers globais
em ``main.py``).
"""

from backend.app.application.category.create_category import create_category
from backend.app.application.category.delete_category import delete_category
from backend.app.application.category.list_categories import list_categories
from backend.app.application.category.update_category import update_category

__all__ = [
    "create_category",
    "delete_category",
    "list_categories",
    "update_category",
]
