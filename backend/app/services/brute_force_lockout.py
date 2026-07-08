"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.security.brute_force_lockout``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .security import brute_force_lockout as _target

sys.modules[__name__] = _target
