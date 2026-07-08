"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.security.protection_pii``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .security import protection_pii as _target

sys.modules[__name__] = _target
