"""O `ignore` de redis no dependabot.yml espelha o teto que o kombu[redis] impõe.

Sem o `ignore`, o updater pip pergunta se `redis==<último>` resolve; com o teto
do kombu a resposta é não, e o pip 26 do updater não consegue provar isso — o
job sai `failure` (08-31 → 10-09). Com um `ignore` maior que o teto, a mesma
pergunta volta; com um `ignore` sem teto, o redis para de subir em silêncio.
"""

from __future__ import annotations

from importlib.metadata import requires
from pathlib import Path

import pytest
import yaml
from packaging.requirements import Requirement

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPENDABOT_YML = REPO_ROOT / ".github" / "dependabot.yml"


def redis_ceiling_from_kombu(kombu_requires: list[str]) -> str | None:
    for raw in kombu_requires:
        req = Requirement(raw)
        if req.name != "redis" or not (req.marker and req.marker.evaluate({"extra": "redis"})):
            continue
        ceilings = [spec.version for spec in req.specifier if spec.operator == "<"]
        assert len(ceilings) <= 1, f"expected ≤1 '<' bound on redis, got {req.specifier!s}"
        return ceilings[0] if ceilings else None
    raise AssertionError(f"kombu sem redis no extra 'redis': {kombu_requires!r}")


def redis_ignores_by_pip_entry(config: dict) -> dict[str, list[str]]:
    return {
        entry["directory"]: [
            version
            for rule in entry.get("ignore", [])
            if rule.get("dependency-name") == "redis"
            for version in rule.get("versions", [])
        ]
        for entry in config["updates"]
        if entry["package-ecosystem"] == "pip"
    }


@pytest.mark.parametrize(
    ("kombu_requires", "expected"),
    [
        (['redis!=4.5.5,!=5.0.2,<6.5,>=4.5.2; extra == "redis"'], "6.5"),
        (['redis>=4.5.2; extra == "redis"'], None),
        (['redis<5; extra == "other"', 'redis<7,>=4.5.2; extra == "redis"'], "7"),
    ],
)
def test_teto_do_redis_lido_do_extra_redis_do_kombu(
    kombu_requires: list[str], expected: str | None
) -> None:
    assert redis_ceiling_from_kombu(kombu_requires) == expected


def test_ignore_de_redis_acompanha_o_teto_do_kombu_instalado() -> None:
    ceiling = redis_ceiling_from_kombu(requires("kombu") or [])
    expected = [f">={ceiling}"] if ceiling else []
    config = yaml.safe_load(DEPENDABOT_YML.read_text(encoding="utf-8"))
    ignores = redis_ignores_by_pip_entry(config)
    assert ignores, f"nenhuma entrada pip em {DEPENDABOT_YML}"
    assert ignores == {directory: expected for directory in ignores}, (
        f"kombu instalado limita redis a <{ceiling}; o ignore de redis em cada "
        f"entrada pip deve ser {expected} (vazio = kombu sem teto, apague o ignore)"
    )
