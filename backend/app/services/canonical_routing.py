"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.documents.canonical_routing``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .documents import canonical_routing as _target

sys.modules[__name__] = _target
