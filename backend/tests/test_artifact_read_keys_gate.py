"""O gate de chave lida↔emitida precisa reprovar o bug que o originou."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "dev" / "check_artifact_read_keys.py"


def _gate_module():
    spec = importlib.util.spec_from_file_location("check_artifact_read_keys", GATE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _erros(codigo: str, tmp_path: Path) -> list[str]:
    gate = _gate_module()
    alvo = tmp_path / "modulo_sob_teste.py"
    alvo.write_text(codigo, encoding="utf-8")
    monkeyed = gate.REPO_ROOT
    try:
        gate.REPO_ROOT = tmp_path
        return gate._analisa(alvo, gate._schema_por_stage())
    finally:
        gate.REPO_ROOT = monkeyed


_LEITOR_CORRETO = """
from backend.app.services.security.crypto import read_artifact_content

ARTIFACT_CONTRACT = ("analyze_finances",)


def f(artifact):
    payload = read_artifact_content(artifact.content_json) or {}
    return payload.get("patrimonio"), payload["investimentos"]
"""

_LEITOR_DO_BUG = _LEITOR_CORRETO.replace('"patrimonio"', '"patrimonio_full"')

_SEM_CONTRATO = _LEITOR_CORRETO.replace('ARTIFACT_CONTRACT = ("analyze_finances",)', "")

_ENXERTO = """
from backend.app.services.security.crypto import read_artifact_content

ARTIFACT_CONTRACT = ("analyze_finances",)


def f(artifact):
    payload = dict(read_artifact_content(artifact.content_json))
    payload["_report_lineage"] = {}
    return payload
"""


def test_reprova_a_chave_ficticia_que_originou_o_gate(tmp_path):
    erros = _erros(_LEITOR_DO_BUG, tmp_path)
    assert any("patrimonio_full" in e for e in erros), erros


def test_aprova_as_chaves_que_o_produtor_emite(tmp_path):
    assert _erros(_LEITOR_CORRETO, tmp_path) == []


def test_falha_fechado_sem_contrato_declarado(tmp_path):
    erros = _erros(_SEM_CONTRATO, tmp_path)
    assert any("ARTIFACT_CONTRACT" in e for e in erros), erros


def test_enxerto_do_backend_nao_e_violacao(tmp_path):
    # Escrever chave nova no payload é legítimo; só a LEITURA precisa existir no schema.
    assert _erros(_ENXERTO, tmp_path) == []


def test_todo_leitor_de_application_declara_contrato():
    """O repo inteiro passa — se um módulo novo ler artefato, este teste acusa."""
    gate = _gate_module()
    erros: list[str] = []
    mapa = gate._schema_por_stage()
    for path in sorted(gate.SCAN_DIR.rglob("*.py")):
        erros.extend(gate._analisa(path, mapa))
    assert erros == [], "\n".join(erros)


def test_contratos_declarados_citam_stage_conhecido():
    gate = _gate_module()
    mapa = gate._schema_por_stage()
    declarados = 0
    for path in sorted(gate.SCAN_DIR.rglob("*.py")):
        stages = gate._contrato_declarado(ast.parse(path.read_text(encoding="utf-8")))
        if not stages:
            continue
        declarados += 1
        assert all(s in mapa for s in stages), f"{path}: stage fora de SCHEMA_BY_STAGE"
    assert declarados >= 5, "esperado ao menos os 5 leitores conhecidos de application/"
