"""Shim de import (ADR-285 · A33.l9): movido para ``app.services.pipeline.stage_duration_estimator``.

Removido no codemod final da lane — não adicione código aqui.
"""

import sys

from .pipeline import stage_duration_estimator as _target

sys.modules[__name__] = _target
