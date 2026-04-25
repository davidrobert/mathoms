"""Golden de execução E3: tenant mínimo + E2 fixture → E3 → assert + schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_E2_FIXTURE = (
    _REPO / "tests" / "fixtures" / "pipeline_golden" / "e2" / "minimal-extrato-2_extract.json"
)


@pytest.fixture
def e3_tenant_minimal(tmp_path: Path) -> Path:
    """Workspace com config mínima e um extract E2 compatível com E3."""
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    (cfg / "pipeline.json").write_text(
        '{"reconciliation": {"skip_types": [], "skip_files": []}}',
        encoding="utf-8",
    )
    (cfg / "family_members.json").write_text("{}", encoding="utf-8")
    (cfg / "institutions.json").write_text('{"banco_canonical": {}}', encoding="utf-8")

    e2_dir = tmp_path / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True)

    data = json.loads(_E2_FIXTURE.read_text(encoding="utf-8"))
    data["saldo_inicial"] = 0.0
    data["saldo_final"] = 100.0
    (e2_dir / "golden-minimal-2_extract.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return tmp_path


def test_e3_execution_produces_reconciled_json(e3_tenant_minimal: Path):
    """Roda e3_reconcile.main_with_store em tenant isolado."""
    from pipeline.context import WorkspaceContext
    from scripts.e3_reconcile import main_with_store

    ctx = WorkspaceContext(root=e3_tenant_minimal)
    main_with_store(ctx)

    e3_dir = e3_tenant_minimal / "processed" / "E3_reconciled"
    outputs = sorted(e3_dir.glob("*-3_reconciled.json"))
    assert len(outputs) == 1, f"expected one E3 file, got {[p.name for p in outputs]}"

    payload = json.loads(outputs[0].read_text(encoding="utf-8"))
    assert payload["banco"] == "itau"
    assert payload["tipo_conta"] == "extratoconta"
    assert payload["moeda"] == "BRL"
    assert payload["transacoes_total"] == 1
    assert payload["transacoes_duplicadas_removidas"] == 0
    assert len(payload["transacoes"]) == 1
    assert payload["transacoes"][0]["valor"] == 100.0

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_REPO / "config" / "schemas" / "e3_reconciled.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, schema)

    from scripts.pipeline_common import validate_artifact

    assert validate_artifact(outputs[0], "e3_reconciled.schema.json") is True
