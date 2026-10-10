"""E2 descobre documentos no diretório do tenant do run, não no do 1º run do processo.

Regressão: ``scripts/extract_bank_documents.py`` importava ``DATA_DIR`` por nome de
``scripts.e2.common``. O 1º import do processo acontece dentro do 1º run e congelava
o diretório daquele tenant; o filho Celery que rodasse depois o E2 de outro
workspace lia — e gravava como seus — os documentos do primeiro.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import pipeline.stages.extract_invoices as extract_invoices
import pipeline.stages.extract_statements as extract_statements
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext


@pytest.fixture
def _restaura_config_e2():
    import scripts.e2.common as e2_common

    base_dir = e2_common.BASE_DIR
    yield
    e2_common._init_config(base_dir)


def _tenant(root: Path, filename: str) -> WorkspaceContext:
    statements_dir = root / "data" / "financial_statements"
    statements_dir.mkdir(parents=True)
    (statements_dir / filename).write_text("conteudo sintetico\n", encoding="utf-8")
    return WorkspaceContext(root=root, artifact_store=InMemoryArtifactStore())


@pytest.mark.usefixtures("_restaura_config_e2")
@pytest.mark.parametrize(
    ("stage_module", "stage", "doc_type"),
    [
        (extract_statements, "extract_statements", "extratoconta"),
        (extract_invoices, "extract_invoices", "faturacartao"),
    ],
)
def test_segundo_tenant_no_mesmo_processo_le_so_os_proprios_documentos(
    tmp_path, stage_module, stage, doc_type
):
    # Banco sem parser: o E2 grava o stub de escalação na chave do stem (ADR-342),
    # então a chave prova QUAL arquivo foi descoberto sem depender de layout.
    ctx_a = _tenant(tmp_path / "ws_a", f"bancosintetico_{doc_type}_202601-0_original.csv")
    ctx_b = _tenant(tmp_path / "ws_b", f"bancosintetico_{doc_type}_202602-0_original.csv")

    for ctx in (ctx_a, ctx_b):
        stage_module.run(ctx)

    store_a, store_b = ctx_a.get_artifact_store(), ctx_b.get_artifact_store()
    assert store_a.list_keys(stage) == [f"bancosintetico_{doc_type}_202601"]
    assert store_b.list_keys(stage) == [f"bancosintetico_{doc_type}_202602"]
    stub_b = store_b.read(stage, f"bancosintetico_{doc_type}_202602")
    assert stub_b["arquivo_origem"] == f"bancosintetico_{doc_type}_202602-0_original.csv"
