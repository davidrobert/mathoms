"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.pipeline.pipeline_client``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .pipeline import pipeline_client as _target

sys.modules[__name__] = _target
