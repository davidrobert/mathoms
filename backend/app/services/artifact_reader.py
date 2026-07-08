"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.storage.artifact_reader``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .storage import artifact_reader as _target

sys.modules[__name__] = _target
