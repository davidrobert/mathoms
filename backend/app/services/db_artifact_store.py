"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.storage.db_artifact_store``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .storage import db_artifact_store as _target

sys.modules[__name__] = _target
