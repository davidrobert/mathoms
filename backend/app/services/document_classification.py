"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.documents.document_classification``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .documents import document_classification as _target

sys.modules[__name__] = _target
