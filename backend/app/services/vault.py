"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.security.vault``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .security import vault as _target

sys.modules[__name__] = _target
