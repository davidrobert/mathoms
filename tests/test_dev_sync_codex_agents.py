"""Testes para dev/sync_codex_agents.py."""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

_MODULE_PATH = Path(__file__).parent.parent / "dev" / "sync_codex_agents.py"
_SPEC = importlib.util.spec_from_file_location("sync_codex_agents", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
sync = importlib.util.module_from_spec(_SPEC)
sys.modules["sync_codex_agents"] = sync
_SPEC.loader.exec_module(sync)


def _write_agent(dirpath: Path, slug: str, body: str = "# Papel\n\nCorpo.") -> Path:
    path = dirpath / f"{slug}.md"
    path.write_text(
        "---\n"
        f"name: {slug}\n"
        f"description: Especialista {slug}. Use para X. NAO invoque para Y.\n"
        "tools: Read\n"
        "model: opus\n"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    return path


def test_discover_source_agents_ignora_template(tmp_path: Path):
    _write_agent(tmp_path, "foo")
    _write_agent(tmp_path, "_TEMPLATE")
    agents = sync.discover_source_agents(tmp_path)
    assert [agent.name for agent in agents] == ["foo"]


def test_render_codex_agent_gera_toml_valido(tmp_path: Path):
    source = _write_agent(tmp_path, "foo")
    agent = sync.discover_source_agents(tmp_path)[0]
    rendered = sync.render_codex_agent(agent)
    parsed = tomllib.loads(rendered)
    assert parsed["name"] == "foo"
    assert parsed["description"].startswith("Especialista foo.")
    assert "# Papel" in parsed["developer_instructions"]
    assert str(source) in rendered


def test_sync_codex_agents_cria_todos_e_remove_extra(tmp_path: Path):
    claude_dir = tmp_path / "claude"
    codex_dir = tmp_path / "codex"
    claude_dir.mkdir()
    codex_dir.mkdir()
    _write_agent(claude_dir, "alpha")
    _write_agent(claude_dir, "beta")
    (codex_dir / "stale.toml").write_text("name = 'stale'\n", encoding="utf-8")

    assert sync.sync_codex_agents(claude_dir, codex_dir) == 0

    assert sorted(path.name for path in codex_dir.glob("*.toml")) == [
        "alpha.toml",
        "beta.toml",
    ]


def test_check_codex_agents_detecta_drift(tmp_path: Path):
    claude_dir = tmp_path / "claude"
    codex_dir = tmp_path / "codex"
    claude_dir.mkdir()
    _write_agent(claude_dir, "alpha")

    assert sync.sync_codex_agents(claude_dir, codex_dir) == 0
    (codex_dir / "alpha.toml").write_text("name = 'alpha'\n", encoding="utf-8")

    assert sync.check_codex_agents(claude_dir, codex_dir) == 1
