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
    """Workspace com config mínima.

    ADR-212 PR3b: E2 não é mais escrito em disco — fixture retorna apenas
    o tmp_path com config; o E2 input é seeded no store em-memória pelo
    próprio teste (``store.seed(...)``).
    """
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    (cfg / "pipeline.json").write_text(
        '{"reconciliation": {"skip_types": [], "skip_files": []}}',
        encoding="utf-8",
    )
    (cfg / "family_members.json").write_text("{}", encoding="utf-8")
    (cfg / "institutions.json").write_text('{"banco_canonical": {}}', encoding="utf-8")
    return tmp_path


def _e2_minimal_payload() -> dict:
    """Carrega fixture E2 + ajusta saldos para casar com gold standard E3."""
    data = json.loads(_E2_FIXTURE.read_text(encoding="utf-8"))
    data["saldo_inicial"] = 0.0
    data["saldo_final"] = 100.0
    return data


def test_e3_execution_produces_reconciled_json(e3_tenant_minimal: Path):
    """Roda reconcile_transactions.main_with_store em tenant isolado.

    ADR-212 PR3b: ``WorkspaceContext`` requer ``artifact_store`` explícito.
    E3 ainda lê E2 de disco via ``load_and_group_e2_extracts`` (fixture
    escreve em ``processed/E2_extracts/``); escreve E3 via store
    (``InMemoryArtifactStore`` aqui). Assertions consultam o store.
    """
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.context import WorkspaceContext
    from scripts.reconcile_transactions import main_with_store

    store = InMemoryArtifactStore()
    store.seed("E2-extratos", "golden-minimal", _e2_minimal_payload())
    ctx = WorkspaceContext(root=e3_tenant_minimal, artifact_store=store)
    main_with_store(ctx)

    e3_keys = store.list_keys("E3")
    assert len(e3_keys) == 1, f"expected one E3 key, got {e3_keys}"

    payload = store.read("E3", e3_keys[0])
    assert payload is not None
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

    from scripts.pipeline_common import validate_dict

    assert validate_dict(payload, "e3_reconciled.schema.json") is True
