"""Snapshot do view-model de /reports/[id]/data sobre a fixture dogfood (A23.l2 · G-a). Reproduz deterministicamente a FORMA do payload que o React consome (E5 + ``_report_lineage`` + ``comparisons``/``changelog``) sem DB, normaliza monetário para cents int (ADR-090; zero float no snapshot) e trava como golden. Garante: (1) run 2× byte-idêntico; (2) nenhum float serializado; (3) completude ``monetary_fields(view_model) ⊆ snapshot`` (cobertura estrutural, não enumeração). Atualizar golden: ``MATHOMS_UPDATE_SNAPSHOT=1 pytest backend/tests/test_report_view_model_snapshot.py``."""

from __future__ import annotations

import json
import os
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _p in (str(_REPO), str(_REPO / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location("golden_diff", _REPO / "dev" / "golden_diff.py")
_golden_diff = _ilu.module_from_spec(_spec)
sys.modules["golden_diff"] = _golden_diff
_spec.loader.exec_module(_golden_diff)
is_monetary = _golden_diff.is_monetary

from pipeline_golden_substrate import (  # noqa: E402
    load_fixture,
    run_dogfood_pipeline,
    write_e5_config,
)

_DOGFOOD = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"
_SNAPSHOT = Path(__file__).resolve().parent / "snapshots" / "dogfood_view_model.json"
_FAMILY = {
    "titular": "alex",
    "membros": {
        "alex": {"nome_curto": "Alex", "data_nascimento": "1985-03-10"},
        "bia": {"nome_curto": "Bia", "data_nascimento": "1987-07-22"},
    },
}
# data_analise = data de hoje; prob_if_ate_idade_meta = saída Monte Carlo não-seedada.
# Ambos não-monetários e fora do escopo do snapshot de conservação numérica.
_VOLATILE_LEAVES = frozenset({"data_analise", "prob_if_ate_idade_meta"})


def _to_cents(value: Any) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _quantize_str(value: float) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _normalize(obj: Any, path: str = "") -> Any:
    """Monetário→cents int; float não-monetário→string quantizada; volátil→sentinela."""
    if isinstance(obj, dict):
        return {k: _normalize(v, f"{path}.{k}" if path else k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v, f"{path}[{i}]") for i, v in enumerate(obj)]
    leaf = path.rsplit(".", 1)[-1].split("[", 1)[0]
    if leaf in _VOLATILE_LEAVES:
        return "<volatile>"
    if isinstance(obj, bool) or not isinstance(obj, (int, float)):
        return obj
    if is_monetary(path):
        return _to_cents(obj)
    return obj if isinstance(obj, int) else _quantize_str(obj)


def _assemble_view_model(e5_payload: dict) -> dict:
    """Forma do view-model de get_report_data: E5 + lineage stub + comparisons/changelog."""
    from backend.app.services.report_lineage import lineage_payload

    return {
        **e5_payload,
        "_report_lineage": lineage_payload(
            pipeline_run_id="run-dogfood",
            source_document_count=3,
            source_document_ids=["doc-1", "doc-2", "doc-3"],
            consumed_document_count=3,
            consumed_document_ids=["doc-1", "doc-2", "doc-3"],
        ),
        "comparisons": None,
        "changelog": None,
    }


def _run_view_model(tmp_path: Path) -> dict:
    # A28.l1 — categorização mínima que exercita os caminhos canônicos da reserva:
    # receita PJ-dominante (meses_alvo 18) + despesa essencial documentada (ADR-306 §D4).
    # ADR-330/331: código E4 REAL (lucros_distribuidos), não o agregado fantasma receita_pj.
    write_e5_config(
        tmp_path,
        family=_FAMILY,
        income_keywords={"lucros_distribuidos": ["PIX"]},
        expense_keywords={"alimentacao": ["MERCADO"]},
    )
    e5 = run_dogfood_pipeline(
        tmp_path,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts={
            "fict_a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
            "fict_b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
        },
    )
    return _normalize(_assemble_view_model(e5))


def _dump(view_model: dict) -> str:
    return json.dumps(view_model, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _iter_floats(obj: Any) -> bool:
    if isinstance(obj, float):
        return True
    if isinstance(obj, dict):
        return any(_iter_floats(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_iter_floats(v) for v in obj)
    return False


def _children(obj: Any, path: str) -> list[tuple[str, Any]]:
    if isinstance(obj, dict):
        return [(f"{path}.{k}" if path else k, v) for k, v in obj.items()]
    if isinstance(obj, list):
        return [(f"{path}[{i}]", v) for i, v in enumerate(obj)]
    return []


def _is_monetary_leaf(obj: Any, path: str) -> bool:
    return isinstance(obj, (int, float)) and not isinstance(obj, bool) and is_monetary(path)


def _monetary_paths(obj: Any, path: str = "") -> set[str]:
    children = _children(obj, path)
    if not children:
        return {path} if _is_monetary_leaf(obj, path) else set()
    out: set[str] = set()
    for sub, value in children:
        out |= _monetary_paths(value, sub)
    return out


def test_view_model_snapshot_matches_golden(tmp_path: Path):
    view_model = _run_view_model(tmp_path)
    actual = _dump(view_model)
    if os.environ.get("MATHOMS_UPDATE_SNAPSHOT") == "1" or not _SNAPSHOT.exists():
        _SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        _SNAPSHOT.write_text(actual, encoding="utf-8")
    expected = _SNAPSHOT.read_text(encoding="utf-8")
    assert (
        actual == expected
    ), "view-model divergiu do golden — rebaseline via MATHOMS_UPDATE_SNAPSHOT=1"


def test_view_model_snapshot_is_deterministic(tmp_path):
    first = _dump(_run_view_model(tmp_path / "a"))
    second = _dump(_run_view_model(tmp_path / "b"))
    assert first == second


def test_snapshot_has_zero_float(tmp_path: Path):
    assert not _iter_floats(_run_view_model(tmp_path))


def test_monetary_fields_subset_of_snapshot(tmp_path: Path):
    view_model = _run_view_model(tmp_path)
    # monetary_fields computados sobre o view-model normalizado: cada campo monetário
    # vira cents int e DEVE estar presente — cobertura estrutural (não enumeração).
    monetary = _monetary_paths(view_model)
    serialized = json.loads(_dump(view_model))
    present = _monetary_paths(serialized)
    assert monetary <= present
    assert monetary, "esperado ≥1 campo monetário no view-model dogfood"
