"""Mapper ORM → DTO para o agregado ``Document``.

O mapper **não** recebe ``AsyncSession``. Recebe a instância ORM já
hidratada — isso torna o mapper testável sem DB.

Regra dos enums: ``Document.doc_type`` e ``Document.status`` são
``sqlalchemy.Enum`` — no identity map vêm sempre como instâncias do enum
Python. O DTO é declarado em cima dos mesmos enums, então ``model_validate``
aceita a instância diretamente. Não precisamos de ``.value``.
"""

from __future__ import annotations

from backend.app.models.document import Document
from backend.app.schemas.dto.document.response import DocumentResponse


def document_to_response(document: Document) -> DocumentResponse:
    """Converte ORM ``Document`` → DTO de resposta.

    Equivalente a ``DocumentResponse.model_validate(document)`` — por
    ter ``from_attributes=True`` no config, o Pydantic lê cada atributo
    do ORM. Usar a função nomeada é preferível por três motivos:

    1. Simétrico aos outros agregados A6e (category, family_member,
       config_blob).
    2. Único ponto para futuras divergências DTO ↔ ORM (ex.: formatar
       ``classification_meta`` ou embutir ``stored_path`` relativo).
    3. Testável isoladamente sem instanciar um Pydantic validator.
    """
    return DocumentResponse.model_validate(document)
