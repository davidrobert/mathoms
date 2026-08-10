"""Coerência nav ↔ seção no report_layout (A40.l7 · RV3-04)."""
# `enabled: false` com entrada de nav viva entregava âncora morta em 100% dos
# relatórios — e o título da seção desligada chegava ao cliente pelo drawer
# mobile. O gate vive DENTRO do codegen (falha antes de emitir), porque gerado
# que já contém o defeito não é gate.

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_DIR = REPO_ROOT / "dev"
SECTION_TITLES_TS = (
    REPO_ROOT / "frontend" / "src" / "components" / "report" / "utils" / "sectionTitles.ts"
)

if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))


@pytest.fixture(scope="module")
def layout() -> dict:
    import codegen_report_layout

    return codegen_report_layout.load_yaml()


def _nav_links(lay: dict) -> list[dict]:
    return [lnk for groups in lay["navigation"].values() for g in groups for lnk in g["links"]]


def test_live_layout_passes(layout: dict) -> None:
    """A vault viva satisfaz o gate — a entrada morta de S_PROTECAO saiu."""
    import report_layout_nav_targets as gate

    gate.validate_nav_targets(layout)


def test_link_para_secao_desabilitada_falha(layout: dict) -> None:
    """Reproduz RV3-04 exatamente: seção `enabled: false` com link de nav vivo."""
    import report_layout_nav_targets as gate

    mutated = copy.deepcopy(layout)
    target = next(s for s in mutated["estrategico"]["sections"] if s.get("enabled", True))
    target["enabled"] = False
    with pytest.raises(gate.NavTargetError, match=target["id"]):
        gate.validate_nav_targets(mutated)


def test_link_para_id_inexistente_falha(layout: dict) -> None:
    """Âncora para id que não é seção, apêndice nem seção do shell."""
    import report_layout_nav_targets as gate

    mutated = copy.deepcopy(layout)
    mutated["navigation"]["estrategico"][0]["links"].append({"section_id": "S_NAO_EXISTE"})
    with pytest.raises(gate.NavTargetError, match="S_NAO_EXISTE"):
        gate.validate_nav_targets(mutated)


def test_secao_habilitada_sem_link_falha(layout: dict) -> None:
    """Direção inversa do assert bidirecional: seção renderizada fora do índice."""
    import report_layout_nav_targets as gate

    mutated = copy.deepcopy(layout)
    groups = mutated["navigation"]["estrategico"]
    removed = groups[0]["links"].pop()
    with pytest.raises(gate.NavTargetError, match=removed["section_id"]):
        gate.validate_nav_targets(mutated)


def test_secao_do_shell_nao_dispara(layout: dict) -> None:
    """Controle anti-overfire: `V0` existe no DOM sem entrada no YAML."""
    # A polaridade importa: filtrar por "ausente das sections" em vez de
    # "desligado explicitamente" apagaria V0 do índice.
    import report_layout_nav_targets as gate

    assert "V0" in {lnk["section_id"] for lnk in _nav_links(layout)}
    ids, _disabled = gate.declared_sections(layout)
    assert "V0" not in ids, "V0 passou a ser seção YAML; revise SHELL_RENDERED_SECTIONS"
    gate.validate_nav_targets(layout)


def test_shell_rendered_sections_em_paridade_com_o_tsx() -> None:
    """A constante Python espelha SHELL_SECTION_TITLES — senão o allowlist apodrece."""
    import report_layout_nav_targets as gate

    block = re.search(
        r"const SHELL_SECTION_TITLES: Record<string, string> = \{(.*?)\};",
        SECTION_TITLES_TS.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    assert block, "SHELL_SECTION_TITLES não encontrado — o parser precisa de ajuste"
    tsx_ids = set(re.findall(r"^\s*(\w+):", block.group(1), re.MULTILINE))
    assert tsx_ids == set(gate.SHELL_RENDERED_SECTIONS)
