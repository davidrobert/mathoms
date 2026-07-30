"""Partes puras do harness de captura de render (skill `report-review`).

O I/O de browser não é mockado — não vale o custo. O que se testa aqui é o que
quebra em silêncio: a guarda de localhost, o scrub do token e o manifesto.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude"
    / "skills"
    / "pipeline-review"
    / "scripts"
    / "capture_report_render.py"
)

_spec = importlib.util.spec_from_file_location("capture_report_render", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


@pytest.mark.parametrize("url", ["http://localhost:3000", "http://127.0.0.1:3000"])
def test_assert_local_aceita_localhost(url):
    mod._assert_local(url)


@pytest.mark.parametrize(
    "url",
    ["https://app.mathoms.ai", "https://app.staging.mathoms.ai", "http://192.168.1.10:3000"],
)
def test_assert_local_recusa_remoto(url):
    """O risco não é RAM local — é competir com o tráfego de PDF de verdade."""
    with pytest.raises(SystemExit):
        mod._assert_local(url)


def test_scrub_remove_token():
    sujo = "GET /x failed: Authorization: Bearer eyJhbGciOi.JIUzI1NiJ9.abc-_123"
    limpo = mod._scrub(sujo)
    assert "eyJhbGciOi" not in limpo
    assert "Bearer <scrubbed>" in limpo


def test_scrub_preserva_o_resto():
    assert mod._scrub("erro comum sem credencial") == "erro comum sem credencial"


def test_manifest_tem_provenance_e_nao_vaza_id_inteiro():
    ctx = {
        "sha": "abc1234",
        "workspace_id": "1b9f2cf5-6a19-4d2a-af7a-79d739ddeff6",
        "report_id": "7a7e9333-1111-2222-3333-444455556666",
        "run_id": "573a54a7-dc0c-4859-ab7c-469662f35f95",
    }
    md = mod.build_manifest(ctx, [{"surface": "screen", "elapsed_s": 4.2}], "http://localhost:3000")
    assert "abc1234" in md
    assert "1b9f2cf5" in md and ctx["workspace_id"] not in md
    assert "| screen | 4.2 |" in md
    assert "off-git" in md


def test_manifest_aceita_run_ausente():
    ctx = {"sha": "abc1234", "workspace_id": "w" * 36, "report_id": "r" * 36, "run_id": None}
    assert "—" in mod.build_manifest(ctx, [], "http://localhost:3000")
