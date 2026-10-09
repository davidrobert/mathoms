"""Cada trilha opentelemetry-* (1.x, 0.Xb0) tem UMA sentinela no Dependabot pip.

Grupos pip nunca agruparam neste repo: sem `ignore`, cada release otel abria um
PR de piso por membro, todos vermelhos no lockfile-sync. O resto da família é
`ignore` só de version update (os três `update-types`), para que security update
continue abrindo. Membro novo no .in sem decisão aqui vira 2ª sentinela e reprova.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml
from packaging.utils import canonicalize_name

_REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cls", _REPO / "dev" / "check_lockfile_sync.py")
assert _spec and _spec.loader
cls = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cls)

DEPENDABOT_YML = _REPO / ".github" / "dependabot.yml"
VERSION_UPDATE_TYPES = {
    "version-update:semver-major",
    "version-update:semver-minor",
    "version-update:semver-patch",
}


def _otel_tracks() -> dict[str, set[str]]:
    declared = [r for f in cls.IN_FILES for r in cls.declared_requirements(f)]
    tracks: dict[str, set[str]] = {}
    for name, floor in cls.otel_floors(declared).items():
        assert floor is not None, f"{name} sem piso `>=` no .in"
        tracks.setdefault(cls.otel_track(floor), set()).add(name)
    return tracks


def _version_only_ignores(entry: dict) -> set[str]:
    return {
        canonicalize_name(rule["dependency-name"])
        for rule in entry.get("ignore", [])
        if set(rule.get("update-types", [])) == VERSION_UPDATE_TYPES and "versions" not in rule
    }


def _pip_entries() -> list[dict]:
    config = yaml.safe_load(DEPENDABOT_YML.read_text(encoding="utf-8"))
    return [e for e in config["updates"] if e["package-ecosystem"] == "pip"]


def test_uma_entrada_pip_so() -> None:
    assert [e["directory"] for e in _pip_entries()] == ["/"]


def test_cada_trilha_otel_tem_uma_sentinela_e_o_resto_ignorado() -> None:
    tracks = _otel_tracks()
    assert set(tracks) == {"1.x", "0.Xb0"}, f"trilhas otel no .in: {tracks}"
    for entry in _pip_entries():
        ignored = {n for n in _version_only_ignores(entry) if n.startswith("opentelemetry-")}
        assert ignored <= set().union(*tracks.values()), f"ignore otel sem dep no .in: {ignored}"
        sentinels = {track: names - ignored for track, names in tracks.items()}
        assert all(
            len(names) == 1 for names in sentinels.values()
        ), f"esperada 1 sentinela por trilha em {entry['directory']}, got {sentinels}"
