"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.documents.document_duplicates``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .documents import document_duplicates as _target

sys.modules[__name__] = _target
