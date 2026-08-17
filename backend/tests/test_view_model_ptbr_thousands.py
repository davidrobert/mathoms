"""A40.l51 C2 — view-model entregue não usa milhar US (`R$ 2,000`)."""

from __future__ import annotations

import json
import re
from pathlib import Path

_SNAPSHOT = Path(__file__).resolve().parent / "snapshots" / "dogfood_view_model.json"
_US_THOUSANDS = re.compile(r"R\$\s*\d+,\d{3}")


def _children(current: object) -> list[object]:
    if isinstance(current, dict):
        return list(current.values())
    if isinstance(current, list):
        return list(current)
    return []


def _strings(obj: object):
    stack: list[object] = [obj]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            yield current
            continue
        stack.extend(_children(current))


def test_dogfood_snapshot_has_no_us_thousands() -> None:
    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    offenders = [text for text in _strings(data) if _US_THOUSANDS.search(text)]
    assert offenders == []
