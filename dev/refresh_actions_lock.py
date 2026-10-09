#!/usr/bin/env python3
"""Regenera `.github/actions.lock.yml` lendo o action.yml de cada ref em uso via `gh api` — o único ponto com rede do gate de inputs (ADR-320 §Emenda 2026-10-09). Tudo-ou-nada: qualquer falha aborta antes de escrever, e sem ref faltando não abre rede."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.check_action_inputs import (  # noqa: E402
    LOCK_PATH,
    Lock,
    LockEntry,
    check_all,
    collect_step_uses,
    load_lock,
    remote_uses,
    render_lock,
    report,
)

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
INPUT_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
MANIFEST_NAMES = ("action.yml", "action.yaml")
MAX_MANIFEST_BYTES = 512 * 1024
GH_TIMEOUT_S = 20
# Tag anotada aponta para objeto tag; mais de 3 saltos até o commit é patológico.
MAX_TAG_HOPS = 3

# (path da API, resposta crua?) → corpo, ou None em 404. Qualquer outra falha levanta.
GhApi = Callable[[str, bool], str | None]


class RefreshError(Exception):
    """Falha que aborta o refresh inteiro; o lock no disco fica intocado."""


def gh_api(path: str, raw: bool = False) -> str | None:
    accept = ["-H", "Accept: application/vnd.github.raw"] if raw else []
    try:
        proc = subprocess.run(
            ["gh", "api", *accept, path], capture_output=True, text=True, timeout=GH_TIMEOUT_S
        )
    except subprocess.TimeoutExpired as exc:
        raise RefreshError(f"gh api {path}: sem resposta em {GH_TIMEOUT_S}s") from exc
    if proc.returncode == 0:
        return proc.stdout
    if "HTTP 404" in proc.stderr:
        return None
    first_line = (proc.stderr.strip().splitlines() or [""])[0][:160]
    raise RefreshError(f"gh api {path}: rc={proc.returncode} {first_line}")


def split_uses(uses: str) -> tuple[str, str, str]:
    """`owner/repo[/subpath]@ref` → (`owner/repo`, `subpath`, `ref`)."""
    spec, ref = uses.split("@", 1)
    owner, repo, *subpath = spec.split("/")
    return f"{owner}/{repo}", "/".join(subpath), ref


def is_sha_ref(uses: str) -> bool:
    return bool(SHA_RE.match(split_uses(uses)[2]))


def _json_object(api: GhApi, path: str) -> dict | None:
    body = api(path, False)
    return None if body is None else json.loads(body)["object"]


def resolve_tag_sha(api: GhApi, repo: str, ref: str) -> str:
    """Só tag ou SHA de 40 hex: lock de branch (`@main`) é falso por construção, o ref anda sem PR."""
    obj = _json_object(api, f"repos/{repo}/git/ref/tags/{quote(ref, safe='')}")
    for _ in range(MAX_TAG_HOPS):
        if obj is None:
            raise RefreshError(f"{repo}@{ref}: não é tag nem SHA de 40 hex")
        if obj["type"] == "commit":
            return obj["sha"]
        obj = _json_object(api, f"repos/{repo}/git/tags/{obj['sha']}")
    raise RefreshError(f"{repo}@{ref}: tag anotada com mais de {MAX_TAG_HOPS} saltos")


def fetch_manifest(api: GhApi, repo: str, subpath: str, sha: str) -> str:
    for name in MANIFEST_NAMES:
        path = "/".join(part for part in (subpath, name) if part)
        body = api(f"repos/{repo}/contents/{quote(path)}?ref={sha}", True)
        if body is not None:
            return body
    raise RefreshError(f"{repo}@{sha}: sem {' nem '.join(MANIFEST_NAMES)} em {subpath or '/'}")


def _manifest_inputs(manifest: dict, uses: str) -> dict:
    inputs = manifest.get("inputs") or {}
    if not isinstance(inputs, dict):
        raise RefreshError(f"{uses}: `inputs` deveria ser mapping, veio {type(inputs).__name__}")
    bad = [name for name in inputs if not INPUT_NAME_RE.match(str(name))]
    if bad:
        raise RefreshError(f"{uses}: nome de input fora de {INPUT_NAME_RE.pattern}: {bad!r}")
    return inputs


def parse_manifest(text: str, uses: str, resolved_sha: str | None) -> LockEntry:
    """Copia só nomes e `runs.using`, nunca texto livre (`description`) do repo de terceiro."""
    if len(text.encode()) > MAX_MANIFEST_BYTES:
        raise RefreshError(f"{uses}: action.yml com mais de {MAX_MANIFEST_BYTES} bytes")
    manifest = yaml.safe_load(text)
    runs = manifest.get("runs") if isinstance(manifest, dict) else None
    if not isinstance(runs, dict) or not isinstance(runs.get("using"), str):
        raise RefreshError(f"{uses}: action.yml sem `runs.using` string")
    inputs = _manifest_inputs(manifest, uses)
    deprecated = [
        n for n, spec in inputs.items() if isinstance(spec, dict) and spec.get("deprecationMessage")
    ]
    return LockEntry(runs["using"], tuple(sorted(inputs)), tuple(sorted(deprecated)), resolved_sha)


def build_entry(api: GhApi, uses: str) -> LockEntry:
    repo, subpath, ref = split_uses(uses)
    tag_sha = None if SHA_RE.match(ref) else resolve_tag_sha(api, repo, ref)
    return parse_manifest(fetch_manifest(api, repo, subpath, tag_sha or ref), uses, tag_sha)


def refresh_lock(in_use: list[str], lock: Lock, api: GhApi) -> Lock:
    """Sem ref faltando, só poda (offline). Com rede já aberta, relê também as tags, que andam sem PR."""
    missing = [uses for uses in in_use if uses not in lock]
    if not missing:
        return {uses: lock[uses] for uses in in_use}
    to_fetch = sorted(set(missing) | {uses for uses in in_use if not is_sha_ref(uses)})
    fetched = {uses: build_entry(api, uses) for uses in to_fetch}
    return {uses: fetched.get(uses) or lock[uses] for uses in in_use}


def write_atomically(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def main(argv: list[str] | None = None, api: GhApi = gh_api, lock_path: Path = LOCK_PATH) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    sites = collect_step_uses()
    try:
        lock = refresh_lock(remote_uses(sites), load_lock(lock_path), api)
    except RefreshError as exc:
        print(f"✗ refresh abortado, {lock_path.name} intocado: {exc}")
        return 2
    write_atomically(lock_path, render_lock(lock))
    print(f"{lock_path.name}: {len(lock)} ref(s).")
    return report(check_all(sites, lock))


if __name__ == "__main__":
    sys.exit(main())
