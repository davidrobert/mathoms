"""Testes do gate `dev/check_dependabot_major_pauses.py` (ADR-449).

Molde do `test_dependabot_redis_ceiling.py`: o `ignore` do dependabot.yml
espelha um teto que um vizinho impõe, lido do que está instalado (aqui, o
`peerDependencies` gravado no `package-lock.json`). A data entra fixada: o
vencimento por relógio é do hook, no Lint, não do pytest.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
import yaml

from dev import check_dependabot_major_pauses as gate

TODAY = dt.date(2026, 10, 9)
PAUSE = gate.MajorPause(
    "frontend", ("eslint", "@eslint/js"), 10, "eslint", TODAY, dt.date(2026, 11, 30), "#1"
)
REACT_PEER = "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7"


@pytest.mark.parametrize(
    ("spec", "major", "admits"),
    [
        (REACT_PEER, 10, False),
        (REACT_PEER, 9, True),
        (">=4.8.4 <6.1.0", 7, False),
        (">=4.8.4 <6.1.0", 6, True),
        (">= 4.8.4 < 6.1.0", 7, False),
        ("^2.4.9", 3, False),
        ("^3.0.0 || ^8.0.0-0 || ^9.0.0 || ^10.0.0", 10, True),
        ("*", 10, True),
        ("", 10, True),
        (">=8.57.0", 10, True),
        ("9.x", 10, False),
        ("~9.1", 9, True),
        ("~9.1", 10, False),
        ("^0.5.0", 1, False),
        ("<=9", 9, True),
        (">=8 <10", 10, False),
        ("<10.0.0", 9, True),
        (">9", 9, False),
    ],
)
def test_range_npm_admite_major(spec: str, major: int, admits: bool) -> None:
    assert gate.range_admits_major(spec, major) is admits


def test_hyphen_range_reprova_em_vez_de_adivinhar() -> None:
    with pytest.raises(ValueError, match="hyphen"):
        gate.range_admits_major("1.2.3 - 2.0.0", 2)


def _lock(peers: dict[str, dict[str, str]]) -> dict:
    packages = {"": {"name": "app"}}
    for name, peer in peers.items():
        packages[f"node_modules/{name}"] = {"version": "1.0.0", "peerDependencies": peer}
    return {"lockfileVersion": 3, "packages": packages}


def test_bloqueador_e_quem_declara_peer_que_exclui_o_major() -> None:
    lock = _lock({"eslint-plugin-react": {"eslint": REACT_PEER}, "ok": {"eslint": "^9 || ^10"}})
    assert gate.peer_blockers(lock, "eslint", 10) == [
        f"eslint-plugin-react@1.0.0 (peer eslint {REACT_PEER!r})"
    ]


def _repo(tmp_path: Path, ignores: list[dict], peers: dict[str, dict[str, str]]) -> Path:
    (tmp_path / ".github").mkdir()
    (tmp_path / "frontend").mkdir()
    entry = {"package-ecosystem": "npm", "directory": "/frontend", "ignore": ignores}
    config = {"version": 2, "updates": [entry]}
    (tmp_path / ".github" / "dependabot.yml").write_text(yaml.safe_dump(config))
    (tmp_path / "frontend" / "package-lock.json").write_text(json.dumps(_lock(peers)))
    return tmp_path


ESLINT_IGNORES = [
    {"dependency-name": "eslint", "versions": [">=10"]},
    {"dependency-name": "@eslint/js", "versions": [">=10"]},
]
BLOCKED = {"eslint-plugin-react": {"eslint": REACT_PEER}}


def _run(repo: Path, today: dt.date = TODAY) -> int:
    return gate.main(["--repo", str(repo), "--today", today.isoformat()], pauses=(PAUSE,))


def test_pausa_com_peer_bloqueando_passa(tmp_path: Path) -> None:
    assert _run(_repo(tmp_path, ESLINT_IGNORES, BLOCKED)) == 0


def test_gatilho_dispara_quando_o_peer_libera_o_major(tmp_path: Path, capsys) -> None:
    # A mutação real: o Dependabot sobe o plugin para uma versão com peer ^10.
    freed = {"eslint-plugin-react": {"eslint": f"{REACT_PEER} || ^10"}}
    assert _run(_repo(tmp_path, ESLINT_IGNORES, freed)) == 1
    assert "gatilho disparou" in capsys.readouterr().err


def test_gatilho_dispara_quando_o_bloqueador_sai_do_lock(tmp_path: Path, capsys) -> None:
    # A outra saída: a migração troca o eslint-plugin-react pelo @eslint-react.
    assert _run(_repo(tmp_path, ESLINT_IGNORES, {"@eslint-react/x": {"eslint": "*"}})) == 1
    assert "gatilho disparou" in capsys.readouterr().err


def test_prazo_vencido_reprova(tmp_path: Path, capsys) -> None:
    assert _run(_repo(tmp_path, ESLINT_IGNORES, BLOCKED), dt.date(2026, 12, 1)) == 1
    assert "prazo 2026-11-30 vencido" in capsys.readouterr().err


def test_ignore_sem_pausa_registrada_reprova(tmp_path: Path, capsys) -> None:
    extra = [*ESLINT_IGNORES, {"dependency-name": "vite", "versions": [">=8"]}]
    assert _run(_repo(tmp_path, extra, BLOCKED)) == 1
    assert "vite >=8 sem pausa em PAUSES" in capsys.readouterr().err


def test_pausa_sem_ignore_reprova(tmp_path: Path, capsys) -> None:
    assert _run(_repo(tmp_path, ESLINT_IGNORES[:1], BLOCKED)) == 1
    assert "@eslint/js >=10 em PAUSES sem ignore" in capsys.readouterr().err


@pytest.mark.parametrize(
    "rule",
    [
        {"dependency-name": "eslint", "update-types": ["version-update:semver-major"]},
        {"dependency-name": "eslint", "versions": [">=10", "<11"]},
        {"dependency-name": "eslint", "versions": ["10.x"]},
    ],
)
def test_ignore_npm_fora_da_forma_reprova(tmp_path: Path, rule: dict, capsys) -> None:
    assert _run(_repo(tmp_path, [*ESLINT_IGNORES, rule], BLOCKED)) == 1
    assert "fora da forma" in capsys.readouterr().err


def test_repo_real_tem_toda_pausa_registrada_e_bloqueada() -> None:
    assert gate.main(["--today", TODAY.isoformat()]) == 0
