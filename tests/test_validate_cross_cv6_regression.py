"""Regressão CV6 (A36.l3): `_cv6_if_progress` deve ler `investivel_efetivo` (fonte do `if_pct`, `analyze_finances.py:1197`), não a chave morta `patrimonio.investivel` — que dava 0 e reprovava CV6 em 100% dos runs."""

from __future__ import annotations

from scripts.validate_cross import _cv6_if_progress


def _e5(*, if_meta: float, if_pct: float, investivel_efetivo=None, investivel=None) -> dict:
    pat: dict = {}
    if investivel_efetivo is not None:
        pat["investivel_efetivo"] = investivel_efetivo
    if investivel is not None:  # a chave morta — não deve ser lida
        pat["investivel"] = investivel
    return {"goals": {"if_meta": if_meta, "if_pct": if_pct}, "patrimonio": pat}


def test_cv6_passa_quando_investivel_efetivo_bate_com_if_pct() -> None:
    """500/1000 = 50%; if_pct reportado 50 → CV6 passa (antes do fix, falhava)."""
    res = _cv6_if_progress(_e5(if_meta=1000.0, if_pct=50.0, investivel_efetivo=500.0))
    assert res is not None
    assert res.check_id == "CV6"
    assert res.passed is True


def test_cv6_ignora_a_chave_morta_investivel() -> None:
    """Só `investivel` (sem `investivel_efetivo`) → lê 0 → reprova; prova que o fix não lê a chave morta (senão 500 bateria com if_pct 50 e passaria)."""
    res = _cv6_if_progress(_e5(if_meta=1000.0, if_pct=50.0, investivel=500.0))
    assert res is not None
    assert res.passed is False


def test_cv6_reprova_em_divergencia_real() -> None:
    """Investível efetivo 200/1000 = 20%, mas if_pct reportado 50 → diverge → reprova."""
    res = _cv6_if_progress(_e5(if_meta=1000.0, if_pct=50.0, investivel_efetivo=200.0))
    assert res is not None
    assert res.passed is False


def test_cv6_skip_sem_meta() -> None:
    """`if_meta <= 0` → check não aplicável (None), sem divisão por zero."""
    assert _cv6_if_progress(_e5(if_meta=0.0, if_pct=0.0, investivel_efetivo=100.0)) is None
