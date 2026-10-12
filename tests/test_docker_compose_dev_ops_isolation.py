"""Só o `api-ops` do compose de dev monta `/admin/*`, e só na rede interna (ADR-116)."""

# O api do cliente nunca liga `MATHOMS_INTERNAL_OPS_UI_ENABLED`; o console
# interno fala com um processo dedicado, sem porta publicada no host.

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_DEV = REPO_ROOT / "docker-compose.dev.yml"
FRONTEND_OPS_DOCKERFILE = REPO_ROOT / "frontend-ops" / "Dockerfile"
OPS_API_BASE = "http://api-ops:8000"
# Sem default: `:-` vazio cai no guard do entrypoint; `:?` quebraria o compose
# inteiro, porque o Compose interpola todo service antes de filtrar o profile.
SECRET_WITHOUT_DEFAULT = re.compile(r"^\$\{MATHOMS_INTERNAL_OPS_SESSION_SECRET(:-)?\}$")
REQUIRED_VARIABLE = re.compile(r"\$\{[A-Za-z0-9_]+:?\?[^}]*\}")


def _services() -> dict[str, dict]:
    return yaml.safe_load(COMPOSE_DEV.read_text(encoding="utf-8"))["services"]


def _string_values(node: object) -> list[str]:
    if isinstance(node, dict):
        return [s for value in node.values() for s in _string_values(value)]
    if isinstance(node, list):
        return [s for item in node for s in _string_values(item)]
    return [node] if isinstance(node, str) else []


def _environment(spec: dict) -> dict[str, str]:
    env = spec.get("environment") or {}
    if isinstance(env, list):
        return dict(item.split("=", 1) for item in env)
    return {key: str(value) for key, value in env.items()}


def test_only_api_ops_enables_internal_ops_ui() -> None:
    enabled = [
        name
        for name, spec in _services().items()
        if _environment(spec).get("MATHOMS_INTERNAL_OPS_UI_ENABLED", "").lower() in {"1", "true"}
    ]
    assert enabled == ["api-ops"], f"expected só api-ops com /admin montado, got {enabled!r}"


def test_api_ops_is_profiled_and_unpublished() -> None:
    spec = _services()["api-ops"]
    assert spec.get("profiles") == [
        "ops"
    ], f"expected profiles ['ops'], got {spec.get('profiles')!r}"
    assert "ports" not in spec, f"expected api-ops sem ports:, got {spec['ports']!r}"


def test_api_ops_session_secret_has_no_default() -> None:
    value = _environment(_services()["api-ops"])["MATHOMS_INTERNAL_OPS_SESSION_SECRET"]
    assert SECRET_WITHOUT_DEFAULT.match(value), f"expected secret sem default, got {value!r}"


def test_compose_dev_has_no_required_variable() -> None:
    assert REQUIRED_VARIABLE.search("${X:?msg}") and REQUIRED_VARIABLE.search("${X?msg}")
    compose = yaml.safe_load(COMPOSE_DEV.read_text(encoding="utf-8"))
    required = [v for v in _string_values(compose) if REQUIRED_VARIABLE.search(v)]
    assert not required, f"expected nenhum ${{VAR:?}} (quebra todo profile), got {required!r}"


def test_api_ops_build_matches_worker_sharing_its_tag() -> None:
    services = _services()
    api_ops, worker = services["api-ops"], services["worker"]
    assert api_ops["image"] == worker["image"], f"got {api_ops['image']!r} vs {worker['image']!r}"
    assert api_ops["build"] == worker["build"], f"got {api_ops['build']!r} vs {worker['build']!r}"


def test_api_ops_healthcheck_probes_admin_mount() -> None:
    probe = " ".join(_services()["api-ops"]["healthcheck"]["test"])
    assert "localhost:8000/admin/" in probe and "401" in probe, f"got {probe!r}"


def test_frontend_ops_proxies_admin_to_api_ops_by_default() -> None:
    build_arg = _services()["frontend-ops"]["build"]["args"]["INTERNAL_OPS_API_BASE"]
    assert build_arg.endswith(
        f":-{OPS_API_BASE}}}"
    ), f"expected default {OPS_API_BASE}, got {build_arg!r}"
    dockerfile = FRONTEND_OPS_DOCKERFILE.read_text(encoding="utf-8")
    assert f"ARG INTERNAL_OPS_API_BASE={OPS_API_BASE}\n" in dockerfile
