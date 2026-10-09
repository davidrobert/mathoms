"""Gate lock ⊨ .in (ADR-254): a versão pinada no lock satisfaz o specifier do .in.

Até 2026-10-09 o gate só conferia presença de nome, e o PR do Dependabot que
sobe o piso sem regenerar o lock passava verde (#1637: `opentelemetry-api>=1.44.0`
com o lock em 1.42.1).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cls", _REPO / "dev" / "check_lockfile_sync.py")
assert _spec and _spec.loader
cls = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cls)

_LOCK = """\
opentelemetry-api==1.42.1 \\
    --hash=sha256:aaaa
    # via -r backend/requirements.in
opentelemetry-instrumentation-fastapi==0.65b0 \\
    --hash=sha256:bbbb
uvicorn==0.48.0 \\
    --hash=sha256:cccc
"""


def _violations(tmp_path: Path, in_text: str) -> list[str]:
    in_file = tmp_path / "requirements.in"
    lock_file = tmp_path / "requirements.lock"
    in_file.write_text(in_text, encoding="utf-8")
    lock_file.write_text(_LOCK, encoding="utf-8")
    return cls.lock_violations(cls.declared_requirements(in_file), cls.locked_versions(lock_file))


def test_repo_real_passa_sob_o_gate() -> None:
    pins = cls.locked_versions(cls.LOCK_FILE)
    assert all(cls.lock_violations(cls.declared_requirements(f), pins) == [] for f in cls.IN_FILES)


def test_piso_acima_do_lock_reprova(tmp_path: Path) -> None:
    assert _violations(tmp_path, "opentelemetry-api>=1.44.0\n") == [
        "opentelemetry-api: o lock pina 1.42.1, o .in pede >=1.44.0"
    ]


def test_dep_ausente_do_lock_reprova(tmp_path: Path) -> None:
    assert _violations(tmp_path, "httpx>=0.27\n") == ["httpx: ausente do lock"]


@pytest.mark.parametrize(
    ("in_text", "expected_ok"),
    [
        ("opentelemetry-instrumentation-fastapi>=0.65b0\n", True),
        ("opentelemetry-instrumentation-fastapi>=0.66b0\n", False),
        ("opentelemetry-instrumentation-fastapi>=0.50b0\n", True),
    ],
)
def test_piso_prerelease_compara_com_o_pin(tmp_path: Path, in_text: str, expected_ok: bool) -> None:
    assert (_violations(tmp_path, in_text) == []) is expected_ok


def test_extra_comentario_e_flag_nao_viram_dependencia(tmp_path: Path) -> None:
    in_text = "# cabeçalho\n-c constraints.txt\nuvicorn[standard]>=0.30  # inline >=9\n"
    assert _violations(tmp_path, in_text) == []


def test_nome_normalizado_pep503(tmp_path: Path) -> None:
    assert _violations(tmp_path, "OpenTelemetry_API>=1.30\n") == []


def test_linha_invalida_aborta_com_a_linha(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="linha inválida 'fastapi>>0.1'"):
        _violations(tmp_path, "fastapi>>0.1\n")


def _otel(*lines: str) -> list[str]:
    return cls.otel_floor_violations([cls.Requirement(line) for line in lines])


def test_repo_real_tem_familia_otel_alinhada() -> None:
    declared = [r for f in cls.IN_FILES for r in cls.declared_requirements(f)]
    assert cls.otel_floor_violations(declared) == []


def test_familia_otel_alinhada_passa() -> None:
    assert (
        _otel(
            "opentelemetry-api>=1.44.0",
            "opentelemetry-sdk>=1.44",
            "opentelemetry-instrumentation-fastapi>=0.65b0",
            "opentelemetry-instrumentation-celery>=0.65b0",
        )
        == []
    )


def test_membro_contrib_sozinho_reprova() -> None:
    (violation,) = _otel(
        "opentelemetry-api>=1.44.0",
        "opentelemetry-instrumentation-fastapi>=0.66b0",
        "opentelemetry-instrumentation-celery>=0.65b0",
    )
    assert violation.startswith("opentelemetry-* 0.Xb0: pisos distintos")
    assert "'opentelemetry-instrumentation-fastapi': '0.66b0'" in violation


def test_membro_core_sozinho_reprova() -> None:
    (violation,) = _otel("opentelemetry-api>=1.44.0", "opentelemetry-sdk>=1.30")
    assert violation.startswith("opentelemetry-* 1.x: pisos distintos")


def test_membro_otel_sem_piso_reprova() -> None:
    assert _otel("opentelemetry-api", "opentelemetry-sdk>=1.44.0") == [
        "opentelemetry-api: esperado um único piso `>=`"
    ]


def test_familia_fora_do_prefixo_nao_entra() -> None:
    assert _otel("opentelemetry-api>=1.44.0", "otel-lookalike>=0.1") == []
