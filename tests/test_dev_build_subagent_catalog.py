"""Testes para dev/build_subagent_catalog.py (W6-T04)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).parent.parent / "dev" / "build_subagent_catalog.py"
_SPEC = importlib.util.spec_from_file_location("build_subagent_catalog", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
build = importlib.util.module_from_spec(_SPEC)
# Registra antes de exec_module: @dataclass introspecta sys.modules[__module__].
sys.modules["build_subagent_catalog"] = build
_SPEC.loader.exec_module(build)


# ----------------------------------------------------------------------
# parse_frontmatter
# ----------------------------------------------------------------------


def test_parse_frontmatter_extrai_campos_basicos():
    text = (
        "---\n"
        "name: foo-bar\n"
        "description: Descrição longa que vira tudo em uma linha.\n"
        "tools: Read, Grep\n"
        "model: opus\n"
        "---\n\n# Papel\n"
    )
    fm = build.parse_frontmatter(text)
    assert fm == {
        "name": "foo-bar",
        "description": "Descrição longa que vira tudo em uma linha.",
        "tools": "Read, Grep",
        "model": "opus",
    }


def test_parse_frontmatter_sem_marcador_retorna_none():
    assert build.parse_frontmatter("# Sem frontmatter\n") is None


def test_parse_frontmatter_template_html_comment_retorna_none():
    text = "<!-- TEMPLATE -->\n---\nname: foo\n---\n"
    assert build.parse_frontmatter(text) is None


# ----------------------------------------------------------------------
# split_description
# ----------------------------------------------------------------------


def test_split_description_extrai_role_trigger_not_for():
    desc = "Especialista X. Use para decisões de Y. NÃO invoque para bugs de Z."
    role, trigger, not_for = build.split_description(desc)
    assert role == "Especialista X."
    assert trigger == "Use para decisões de Y."
    assert not_for == "NÃO invoque para bugs de Z."


def test_split_description_preserva_abreviacoes_db_vs_blob():
    desc = (
        "Engenheiro de Dados. "
        "Use para decidir onde dado vive (DB vs. blob vs. cache). "
        "NÃO invoque para UI."
    )
    role, trigger, not_for = build.split_description(desc)
    # "vs." NÃO deve quebrar a frase do trigger
    assert "DB vs. blob vs. cache" in trigger
    assert role == "Engenheiro de Dados."
    assert not_for == "NÃO invoque para UI."


def test_split_description_sem_trigger_e_sem_not_for():
    desc = "Apenas papel sem trigger."
    role, trigger, not_for = build.split_description(desc)
    assert role == "Apenas papel sem trigger."
    assert trigger == ""
    assert not_for == ""


def test_split_description_invoque_ao_tambem_funciona():
    desc = "Designer X. Invoque ao revisar tela. NÃO invoque para backend."
    role, trigger, not_for = build.split_description(desc)
    assert trigger == "Invoque ao revisar tela."
    assert not_for == "NÃO invoque para backend."


# ----------------------------------------------------------------------
# discover_agents
# ----------------------------------------------------------------------


def _write_agent(dirpath: Path, slug: str, description: str) -> Path:
    path = dirpath / f"{slug}.md"
    path.write_text(
        f"---\n"
        f"name: {slug}\n"
        f"description: {description}\n"
        f"tools: Read\n"
        f"model: opus\n"
        f"---\n\n# Papel\n",
        encoding="utf-8",
    )
    return path


def test_discover_agents_ignora_underscore_prefix(tmp_path: Path):
    _write_agent(tmp_path, "foo", "Foo. Use para X. NÃO invoque para Y.")
    # Arquivo com prefix `_` é ignorado (template auxiliar)
    (tmp_path / "_TEMPLATE.md").write_text(
        "<!-- template -->\n---\nname: tmpl\ndescription: nope.\n---\n",
        encoding="utf-8",
    )
    agents = build.discover_agents(tmp_path)
    slugs = [a.slug for a in agents]
    assert slugs == ["foo"]


def test_discover_agents_ordena_por_slug(tmp_path: Path):
    _write_agent(tmp_path, "zebra", "Z. Use para Z. NÃO invoque para Z.")
    _write_agent(tmp_path, "alpha", "A. Use para A. NÃO invoque para A.")
    _write_agent(tmp_path, "mike", "M. Use para M. NÃO invoque para M.")
    agents = build.discover_agents(tmp_path)
    assert [a.slug for a in agents] == ["alpha", "mike", "zebra"]


def test_discover_agents_pula_arquivo_sem_frontmatter(tmp_path: Path, capsys):
    _write_agent(tmp_path, "good", "Good. Use para X. NÃO invoque para Y.")
    (tmp_path / "broken.md").write_text("# Sem frontmatter\n", encoding="utf-8")
    agents = build.discover_agents(tmp_path)
    assert [a.slug for a in agents] == ["good"]
    captured = capsys.readouterr()
    assert "broken.md" in captured.err


# ----------------------------------------------------------------------
# render_catalog + inject (round-trip + idempotência)
# ----------------------------------------------------------------------


def test_render_catalog_produz_marcadores_e_entradas(tmp_path: Path):
    _write_agent(tmp_path, "foo", "Foo. Use para X. NÃO invoque para Y.")
    agents = build.discover_agents(tmp_path)
    out = build.render_catalog(agents)
    assert build.BEGIN_MARK in out
    assert build.END_MARK in out
    assert "**[foo]" in out
    assert "Foo." in out
    assert "Use para X." in out
    assert "NÃO invoque para Y." in out


def test_render_catalog_sem_agentes_emite_placeholder():
    out = build.render_catalog([])
    assert build.BEGIN_MARK in out
    assert build.END_MARK in out
    assert "Nenhum subagente registrado" in out


def test_inject_falha_sem_marcadores_no_arquivo():
    content = "# CLAUDE.md\nSem marcadores aqui.\n"
    with pytest.raises(SystemExit, match="marcações"):
        build.inject(content, "fake catalog")


def test_inject_substitui_bloco_entre_marcadores():
    content = f"# Top\n\nantes\n\n{build.BEGIN_MARK}\n\nlixo antigo\n\n{build.END_MARK}\n\ndepois\n"
    catalog = f"{build.BEGIN_MARK}\n\nNOVO CONTEÚDO\n\n{build.END_MARK}"
    out = build.inject(content, catalog)
    assert "NOVO CONTEÚDO" in out
    assert "lixo antigo" not in out
    assert "antes" in out and "depois" in out


def test_round_trip_idempotente(tmp_path: Path):
    """Rodar inject duas vezes não muda o arquivo (gate de pre-commit fica estável)."""
    _write_agent(tmp_path, "alpha", "A. Use para A. NÃO invoque para A.")
    agents = build.discover_agents(tmp_path)
    catalog = build.render_catalog(agents)

    base = f"# CLAUDE.md\nintro\n\n{build.BEGIN_MARK}\n{build.END_MARK}\n\noutro\n"
    once = build.inject(base, catalog)
    twice = build.inject(once, catalog)
    assert once == twice
