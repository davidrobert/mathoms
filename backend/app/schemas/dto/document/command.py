"""Command DTOs (inputs de write) do agregado ``Document``.

Um *command* é a representação de uma **intenção** do caller (criar,
atualizar, apagar). Upload é um caso especial (multipart ``UploadFile``),
então aqui ficam só os comandos estruturados — PATCH de classificação
e os flags booleanos de endpoints batch.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.app.models.document import DocumentType


class DocumentUpdateCommand(BaseModel):
    """Correção manual de classificação pelo usuário (``PATCH /documents/{id}``).

    Todos os campos são opcionais — atualiza apenas os enviados (semântica
    PATCH). Envie ``null`` explícito para limpar um campo escalar.
    ``bank_code`` e ``period`` vazios (string de espaços) viram ``None``
    automaticamente — paridade com o comportamento legado.
    """

    doc_type: Optional[DocumentType] = Field(default=None)
    bank_code: Optional[str] = Field(default=None, max_length=50)
    period: Optional[str] = Field(default=None, max_length=50)

    @field_validator("bank_code", "period", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v
