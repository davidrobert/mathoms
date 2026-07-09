"""Paridade da fonte única das 7 classes AUVP (ADR-141 §Emenda item 11).

O espelho backend (`ALOCACAO_V2_CLASSES`) e o schema v2 têm de concordar nos
`id` (ordem + conjunto). A fonte frontend equivalente
(`frontend/src/lib/alocacaoClasses.ts`) trava contra o mesmo schema em
`frontend/tests/lib/alocacaoClasses.test.ts` — o schema é a âncora comum.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.dto.goal import ALOCACAO_V2_CLASS_FIELDS, ALOCACAO_V2_CLASSES

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _REPO_ROOT / "config" / "schemas" / "goal.alocacao_alvo.v2.schema.json"

_VALID_FAMILIES = {"renda_fixa", "renda_variavel", "imobiliario", "liquidez"}


def _schema_input_keys() -> list[str]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return list(schema["properties"]["inputs"]["required"])


def test_class_ids_match_schema_order_and_set():
    ids = [c.id for c in ALOCACAO_V2_CLASSES]
    assert ids == _schema_input_keys()


def test_class_fields_derived_from_classes():
    assert ALOCACAO_V2_CLASS_FIELDS == tuple(c.id for c in ALOCACAO_V2_CLASSES)


def test_ids_are_unique():
    ids = [c.id for c in ALOCACAO_V2_CLASSES]
    assert len(set(ids)) == len(ids)


def test_labels_are_non_empty():
    for c in ALOCACAO_V2_CLASSES:
        assert c.label.strip()
        assert c.label_full.strip()


def test_families_are_valid():
    for c in ALOCACAO_V2_CLASSES:
        assert c.family in _VALID_FAMILIES
