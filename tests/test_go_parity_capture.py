"""Testes dos helpers puros de ``dev/go_parity_capture.py`` (F2 GO_SHELL).

A captura em si (Redis pub/sub) é integração e não roda aqui — só a detecção de
evento terminal e o decode defensivo.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dev.go_parity_capture import _decode, _is_terminal  # noqa: E402


def test_is_terminal_recognises_terminal_events():
    assert _is_terminal({"event": "run_completed"}) is True
    assert _is_terminal({"event": "run_failed"}) is True
    assert _is_terminal({"event": "run_cancelled"}) is True


def test_is_terminal_false_for_stage_events():
    assert _is_terminal({"event": "stage_started"}) is False
    assert _is_terminal({}) is False


def test_decode_parses_json_and_swallows_garbage():
    assert _decode('{"event": "run_started"}') == {"event": "run_started"}
    assert _decode("not json") is None
    assert _decode(None) is None
