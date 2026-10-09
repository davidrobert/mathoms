"""Dependabot pip: uma entrada só, e UMA sentinela por trilha opentelemetry-*.

A entrada `/` cobre os dois .in; a `/backend` duplicava os PRs dela (2026-10-09).
Grupos pip nunca agruparam neste repo: sem `ignore`, cada release otel abria um
PR de piso por membro, e a família é acoplada por `==`. O resto da família é
`ignore` só de version update (os três `update-types`), para que security update
continue abrindo. Membro novo no .in sem decisão aqui vira 2ª sentinela e reprova.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPENDABOT_YML = REPO_ROOT / ".github" / "dependabot.yml"
IN_FILES = (REPO_ROOT / "requirements.in", REPO_ROOT / "backend" / "requirements.in")
VERSION_UPDATE_TYPES = {
    "version-update:semver-major",
    "version-update:semver-minor",
    "version-update:semver-patch",
}


def _otel_requirements() -> list[Requirement]:
    lines = (raw.split("#", 1)[0].strip() for f in IN_FILES for raw in f.read_text().splitlines())
    reqs = [Requirement(line) for line in lines if line and not line.startswith("-")]
    return [r for r in reqs if canonicalize_name(r.name).startswith("opentelemetry-")]


def _track(req: Requirement) -> str:
    floors = [spec.version for spec in req.specifier if spec.operator == ">="]
    assert len(floors) == 1, f"{req.name}: esperado um piso `>=`, got {req.specifier!s}"
    return "0.Xb" if Version(floors[0]).major == 0 else "1.x"


def _otel_tracks() -> dict[str, set[str]]:
    tracks: dict[str, set[str]] = {}
    for req in _otel_requirements():
        tracks.setdefault(_track(req), set()).add(canonicalize_name(req.name))
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
    assert set(tracks) == {"1.x", "0.Xb"}, f"trilhas otel no .in: {tracks}"
    otel = set().union(*tracks.values())
    for entry in _pip_entries():
        ignored = {n for n in _version_only_ignores(entry) if n.startswith("opentelemetry-")}
        assert ignored <= otel, f"ignore otel sem dep no .in: {sorted(ignored - otel)}"
        sentinels = {track: names - ignored for track, names in tracks.items()}
        assert all(
            len(names) == 1 for names in sentinels.values()
        ), f"esperada 1 sentinela por trilha em {entry['directory']}, got {sentinels}"
