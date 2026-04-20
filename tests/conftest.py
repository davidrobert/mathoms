"""Pytest hooks for tests/ — must load before tests import ``scripts.*``."""

import os
from pathlib import Path

# pipeline_common requires MATHOMS_WORKSPACE_ROOT (strict); default to repo root for suite.
_REPO_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MATHOMS_WORKSPACE_ROOT", str(_REPO_ROOT))
