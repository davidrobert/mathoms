"""Parity — E5 / E5.N respeitam ``ctx.config_overrides`` (A7.1 · ADR-134)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.context import WorkspaceContext  # noqa: E402

_OVERRIDE_FAMILY = {
    "titular": "david",
    "membros": {
        "david": {"nome_curto": "David", "data_nascimento": "1990-01-15", "papel": "titular"},
        "ana": {"nome_curto": "Ana", "papel": "conjuge"},
    },
}

_OVERRIDE_CATEGORIZATION = {
    "expense_keywords": {},
    "income_keywords": {"renda": ["PIX"]},
    "one_time_income_keywords": ["fgts"],
    "one_time_income_categories": ["receita_fgts"],
    "clt_source_mapping": {"src1": "label1"},
}


def _seed_disk_decoy(tmp_path: Path, *, with_fiscal: bool = False) -> None:
    """Disco intencionalmente diferente — overrides devem vencer."""
    cfg = tmp_path / "config"
    cfg.mkdir(exist_ok=True)
    (cfg / "family_members.json").write_text('{"titular":"DISK"}', encoding="utf-8")
    (cfg / "categorization.json").write_text("{}", encoding="utf-8")
    if with_fiscal:
        (cfg / "parametros_fiscais.json").write_text("{}", encoding="utf-8")


def _ctx_with_overrides(tmp_path: Path) -> WorkspaceContext:
    return WorkspaceContext(
        root=tmp_path,
        config_overrides={
            "family_members.json": _OVERRIDE_FAMILY,
            "categorization.json": _OVERRIDE_CATEGORIZATION,
        },
    )


def test_e5_init_config_prefers_overrides_over_disk(tmp_path: Path) -> None:
    import scripts.e5_analyze as e5

    _seed_disk_decoy(tmp_path)
    e5._init_config(tmp_path, ctx=_ctx_with_overrides(tmp_path))
    assert e5._TITULAR_KEY == "david"
    assert e5._CONJUGE_KEY == "ana"
    assert e5.FAMILY_CONFIG == _OVERRIDE_FAMILY
    assert "fgts" in e5.ONE_TIME_INCOME_KEYWORDS


def test_e5_init_config_falls_back_to_disk_when_no_ctx(tmp_path: Path) -> None:
    import json

    import scripts.e5_analyze as e5

    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "family_members.json").write_text(json.dumps(_OVERRIDE_FAMILY), encoding="utf-8")
    (cfg / "categorization.json").write_text(json.dumps(_OVERRIDE_CATEGORIZATION), encoding="utf-8")
    e5._init_config(tmp_path, ctx=None)
    assert e5._TITULAR_KEY == "david"


def test_e5n_init_config_prefers_overrides_over_disk(tmp_path: Path) -> None:
    import scripts.e5n_narrativas as e5n

    _seed_disk_decoy(tmp_path, with_fiscal=True)
    e5n._init_config(tmp_path, ctx=_ctx_with_overrides(tmp_path))
    assert e5n._TITULAR_KEY == "david"
    assert e5n.FAMILY == _OVERRIDE_FAMILY
    assert e5n._CATEGORIZATION == _OVERRIDE_CATEGORIZATION
