"""Gate de .github/labeler.yml: glob negativo sob `any-glob-to-*` casa em todo PR."""

from __future__ import annotations

import yaml

from dev.check_labeler_config import DEFAULT_CONFIG, scan_config

BROKEN = """\
'area:docs':
  - changed-files:
      - any-glob-to-any-file:
          - 'docs/**'
          - '!**/CHANGELOG.md'
"""

CORRECT = """\
'area:docs':
  - changed-files:
      - any-glob-to-any-file:
          - 'docs/**'
      - all-globs-to-all-files:
          - '!**/CHANGELOG.md'
"""


def test_detecta_negativo_sob_any() -> None:
    violations = scan_config(yaml.safe_load(BROKEN))
    assert [(v.label, v.glob) for v in violations] == [("area:docs", "!**/CHANGELOG.md")]


def test_aceita_negativo_sob_all_globs_to_all_files() -> None:
    assert scan_config(yaml.safe_load(CORRECT)) == []


def test_config_real_esta_limpa() -> None:
    parsed = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    violations = scan_config(parsed)
    assert violations == [], [v.format() for v in violations]
