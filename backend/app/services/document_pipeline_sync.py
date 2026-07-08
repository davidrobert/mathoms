"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.pipeline.document_pipeline_sync``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .pipeline import document_pipeline_sync as _target

sys.modules[__name__] = _target
