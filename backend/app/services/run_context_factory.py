"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.pipeline.run_context_factory``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .pipeline import run_context_factory as _target

sys.modules[__name__] = _target
