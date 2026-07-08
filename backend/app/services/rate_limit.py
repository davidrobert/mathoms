"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.security.rate_limit``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .security import rate_limit as _target

sys.modules[__name__] = _target
