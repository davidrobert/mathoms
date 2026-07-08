"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.pipeline.retry_config``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .pipeline import retry_config as _target

sys.modules[__name__] = _target
