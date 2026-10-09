"""Testes do gate ``dev/check_engine_hide_parameters.py``.

O gate tem de reprovar cada forma de construir engine sem o flag e aprovar a forma
com ele; o scan real fecha o repo de hoje, e enxerga os construtores de produção.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _REPO_ROOT / "dev" / "check_engine_hide_parameters.py"
_SPEC = importlib.util.spec_from_file_location("check_engine_hide_parameters", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)


def _violacoes(src: str) -> list[str]:
    return gate.violations_in_source(src, "sintetico.py")[0]


@pytest.mark.parametrize(
    "src",
    [
        "engine = create_engine(url)",
        "engine = create_engine(url, hide_parameters=False)",
        "engine = create_async_engine(url, echo=True)",
        "import sqlalchemy as sa\nengine = sa.create_engine(url)",
        "Session = sessionmaker(bind=create_engine(url, future=True))",
        "engine = async_engine_from_config(cfg, prefix='sqlalchemy.')",
        "engine = engine_from_config(cfg)",
        "engine = create_engine(url, **opts)",
        "engine = create_engine(url, hide_parameters=flag)",
    ],
)
def test_reprova_construtor_sem_o_literal_true(src):
    assert len(_violacoes(src)) == 1


@pytest.mark.parametrize(
    "src",
    [
        "engine = create_engine(url, hide_parameters=True)",
        "engine = create_async_engine(url, future=True, hide_parameters=True)",
        "engine = sa.create_engine(url, hide_parameters=True, **opts)",
        "engine = async_engine_from_config(cfg, prefix='x.', hide_parameters=True)",
    ],
)
def test_aprova_construtor_com_o_literal_true(src):
    assert _violacoes(src) == []


def test_parse_quebrado_reprova_em_vez_de_pular():
    assert _violacoes("def f(:\n") != []


def test_construtor_dentro_de_string_nao_e_chamada():
    # Snippet executado em container (dev/smoke_pipeline_service_container.py) é dado.
    assert _violacoes('SNIPPET = """engine = create_engine(url)"""') == []


def test_diretorio_tests_fica_fora_do_scan():
    assert gate._is_test_path("pipeline-service/tests/conftest.py")
    assert gate._is_test_path("backend/tests/test_x.py")
    assert not gate._is_test_path("backend/app/core/database.py")
    assert not gate._is_test_path("dev/tests_helper.py")


def test_repo_de_hoje_passa_e_o_scan_enxerga_os_construtores():
    violacoes, total = gate.collect_violations()
    assert violacoes == []
    # database.py ×2 + alembic + scripts de operador em dev/ — zero seria leitura vazia.
    assert total >= 3


def test_ancora_sem_construtor_visto_reprova():
    assert gate._anchor_violations({"backend/app/core/database.py": 2}) != []
    assert gate._anchor_violations(dict.fromkeys(gate._ANCHORS, 1)) == []
