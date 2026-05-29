#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hook pre-commit (A20.L2 · ADR-249): base externa em Dockerfile/compose sem @sha256 falha o commit."""

# Pin por digest do índice multi-arch garante reprodutibilidade dev↔CI↔prod
# (P0.5). Recebe paths via argv (pre-commit, só staged); sem argv escaneia
# todos os Dockerfiles + composes via `git ls-files`. Isenta: FROM de stage
# interno (ref a `AS <stage>`), `scratch`, `image:` de build local
# (`mathoms-*`), e `FROM ${ARG}` cujo ARG default já tenha `@sha256:`.

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FROM_RE = re.compile(r"^\s*FROM\s+(?P<ref>\S+)(?:\s+AS\s+(?P<alias>\S+))?", re.IGNORECASE)
ARG_RE = re.compile(r"^\s*ARG\s+(?P<name>\w+)=(?P<value>\S+)", re.IGNORECASE)
ARG_REF_RE = re.compile(r"\$\{?(?P<name>\w+)\}?")
IMAGE_RE = re.compile(r"^\s*image:\s*[\"']?(?P<ref>[^\"'\s]+)", re.IGNORECASE)

LOCAL_IMAGE_PREFIXES = ("mathoms-", "mathoms_")
SHA_PIN = "@sha256:"


def _is_dockerfile(path: Path) -> bool:
    return path.name == "Dockerfile" or path.name.startswith("Dockerfile.")


def _is_compose(path: Path) -> bool:
    return path.name.startswith("docker-compose") and path.suffix in (".yml", ".yaml")


def _record_from(ref: str, lineno: int, from_refs: list, base_args: dict) -> None:
    if not ref.startswith("$"):
        from_refs.append((lineno, ref))
        return
    arg_ref = ARG_REF_RE.search(ref)
    if arg_ref:
        base_args.setdefault(arg_ref["name"], lineno)


def _parse_dockerfile(lines: list[str]):
    arg_defaults: dict[str, str] = {}
    stages: set[str] = set()
    from_refs: list[tuple[int, str]] = []
    base_args: dict[str, int] = {}
    for n, raw in enumerate(lines, start=1):
        m_arg = ARG_RE.match(raw)
        if m_arg:
            arg_defaults[m_arg["name"]] = m_arg["value"]
            continue
        m = FROM_RE.match(raw)
        if not m:
            continue
        if m["alias"]:
            stages.add(m["alias"])
        _record_from(m["ref"], n, from_refs, base_args)
    return arg_defaults, stages, from_refs, base_args


def _check_from_refs(path: Path, from_refs: list, stages: set) -> list[str]:
    errors: list[str] = []
    for lineno, ref in from_refs:
        if ref == "scratch" or ref in stages:
            continue
        if SHA_PIN not in ref:
            errors.append(f"{path}:{lineno}: FROM '{ref}' sem @sha256: (pine por digest)")
    return errors


def _arg_error(path: Path, arg_name: str, lineno: int, value: str | None) -> str | None:
    if value is None:
        return f"{path}:{lineno}: FROM usa ${{{arg_name}}} mas o ARG não tem default"
    if SHA_PIN not in value:
        return f"{path}: ARG {arg_name}={value} (usado em FROM linha {lineno}) sem @sha256:"
    return None


def _check_base_args(path: Path, base_args: dict, arg_defaults: dict) -> list[str]:
    errors: list[str] = []
    for arg_name, lineno in base_args.items():
        msg = _arg_error(path, arg_name, lineno, arg_defaults.get(arg_name))
        if msg:
            errors.append(msg)
    return errors


def _check_dockerfile(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    arg_defaults, stages, from_refs, base_args = _parse_dockerfile(lines)
    errors = _check_from_refs(path, from_refs, stages)
    errors.extend(_check_base_args(path, base_args, arg_defaults))
    return errors


def _check_compose(path: Path) -> list[str]:
    errors: list[str] = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = IMAGE_RE.match(raw)
        if not m:
            continue
        ref = m["ref"]
        if ref.startswith(LOCAL_IMAGE_PREFIXES) or ref.startswith("$"):
            continue
        if SHA_PIN not in ref:
            errors.append(f"{path}:{n}: image '{ref}' sem @sha256: (pine por digest)")
    return errors


def _targets(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(p) for p in argv]
    out = subprocess.run(
        ["git", "ls-files", "Dockerfile", "**/Dockerfile", "Dockerfile.*", "docker-compose*.yml"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [Path(p) for p in out]


def _check_path(path: Path) -> list[str]:
    if _is_dockerfile(path):
        return _check_dockerfile(path)
    if _is_compose(path):
        return _check_compose(path)
    return []


def _report(errors: list[str]) -> None:
    print("Imagens base sem pin @sha256: (A20.L2 · ADR-249):", file=sys.stderr)
    for e in errors:
        print(f"  ✗ {e}", file=sys.stderr)
    print(
        "\nColete o digest do índice multi-arch:\n"
        "  docker buildx imagetools inspect <img>:<tag> --format '{{.Manifest.Digest}}'\n"
        "e use FROM <img>:<tag>@sha256:<digest>.",
        file=sys.stderr,
    )


def main(argv: list[str]) -> int:
    errors: list[str] = []
    for path in _targets(argv):
        if path.exists() and "_archive/" not in str(path):
            errors.extend(_check_path(path))
    if errors:
        _report(errors)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
