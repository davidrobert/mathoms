"""Prova por mutação do gate ADR-390 D4."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "dev"))

from check_conversao_me_funnel import main, offenders  # noqa: E402


def test_orphan_multiply_fails(tmp_path: Path) -> None:
    producer = tmp_path / "pipeline" / "domain" / "services" / "fake_caixa.py"
    producer.parent.mkdir(parents=True)
    producer.write_text("def convert(saldo, cambio_usd):\n    return saldo * cambio_usd\n")
    assert main(["--root", str(tmp_path / "pipeline")]) == 1
    assert any("fake_caixa.py" in item for item in offenders((tmp_path / "pipeline",)))


def test_conversor_file_is_exempt(tmp_path: Path) -> None:
    sink = tmp_path / "pipeline" / "conversao_me.py"
    sink.parent.mkdir(parents=True)
    sink.write_text("def convert_me_brl(amount, quote):\n    return amount * quote.rate\n")
    other = tmp_path / "pipeline" / "ok.py"
    other.write_text("def add(a, b):\n    return a + b\n")
    assert main(["--root", str(tmp_path / "pipeline")]) == 0
