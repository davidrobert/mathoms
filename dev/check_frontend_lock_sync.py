#!/usr/bin/env python3
"""Gate de pre-commit: `<app>/package-lock.json` passa no `npm ci` do npm que o `FROM node` do app traz.

App = diretório de 1º nível com `package.json` versionado (a definição do gate
node-version-parity). Todo app tem `package-lock.json` e um `Dockerfile` cujos
`FROM node:` concordam num major; o lock é validado por
`npx -y npm@<versão exata> ci --dry-run --ignore-scripts`, com a versão que
`NPM_BY_NODE_MAJOR` dá para esse major. Incidente de origem: 2026-04-25
(cb0ff11), lock fora de sync quebrou `npm ci` no CI por ~5h.

npm fixo não serve, porque npm 10 e npm 11 divergem nesse comando. Medido em
2026-10-09 com 10.8.2, 10.9.9 e 11.19.0, nas imagens node:20-alpine e
node:26-alpine:
- optional de plataforma ausente do lock (`@next/swc-linux-x64-musl` e outros,
  12/12 remoções): npm 10 aceita e npm 11 recusa. O hook antigo (`npm@10`) dava
  verde, e o `npm ci` do build de prod quebrava (node:26-alpine traz npm 11).
- peerOptional ausente (o lock do cb0ff11): npm 10 recusa e npm 11 aceita. Era
  falso positivo contra um lock que todo consumidor aceita, Dependabot incluso:
  o updater roda npm 11.19.0.

Fail-closed: reprova app sem lock ou sem Dockerfile, `FROM node` ausente, com
`$`, sem major ou com major divergente entre stages, e major fora do mapa. Sem
`npx`, reprova em CI (`CI=true`) e só avisa no ambiente local.

`--verify-image <app>` é um step dos jobs do app no CI, que têm Docker. Ele roda
`npm -v` na imagem exata do FROM e reprova se o major diferir do mapa. Assim um
bump de digest dentro da linha do Node que traga npm de outro major não passa
calado.

Rejeitado (2026-10-08/09): `engines` + `engine-strict`, `devEngines`
(`onFail: error`) e `packageManager`. O updater do Dependabot (Node 24, Corepack
lê `packageManager`) avalia esses campos antes de existir PR. Os dois primeiros
abortam com EBADENGINE ou EBADDEVENGINES, e os PRs npm param em silêncio. Este
gate falha no PR, à vista.

Eixo aberto: o minor do npm dentro do major. O mapa pina a versão exata para o
Lint ser determinístico; o `--verify-image` só avisa quando o minor diverge.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = "dev/check_frontend_lock_sync.py"

# npm do `node:<major>-alpine` pinado nos Dockerfiles, medido com
# `docker run --rm --entrypoint npm <ref do FROM> -v` (2026-10-09). Node major
# novo: meça e adicione a linha; o `--verify-image` confere o major no CI.
NPM_BY_NODE_MAJOR: dict[int, str] = {26: "11.19.0"}

_FROM_RE = re.compile(r"^\s*FROM\s+(?:--\S+\s+)*(?P<ref>\S+)", re.IGNORECASE)
_NODE_IMAGE_RE = re.compile(r"^(?:(?:docker\.io/)?library/)?node(?P<rest>[:@].*)?$")
_MAJOR_RE = re.compile(r"^:v?(\d+)(?:[.-]|@|$)")
_LOCK_DESYNC_MARKERS = ("can only install packages when", "from lock file", "does not satisfy")
# O EUSAGE imprime o motivo e depois ~15 linhas de uso do `npm ci`; o corte pela
# cauda mostrava só o uso e escondeu o `Missing:` do #2187 (msw 3).
_NPM_USAGE_START = "Clean install a project"
_NPM_EXCERPT_MAX = 60
_PEER_FIX = (
    "o major novo exige um peer que um vizinho não aceita: pause o major no "
    ".github/dependabot.yml (`ignore` com data e gatilho) ou suba o vizinho junto — "
    "`--force`/`--legacy-peer-deps` só esconde o conflito"
)
_NPM_TIMEOUT_S = 300

NpmRunner = Callable[[Path, str], "subprocess.CompletedProcess[str]"]
DockerRunner = Callable[[str], "subprocess.CompletedProcess[str]"]


@dataclass(frozen=True)
class LockGateFailure:
    app: str
    cause: str
    detail: str
    fix: str

    def format(self) -> str:
        return f"🛑 [{self.cause}] {self.app}: {self.detail}\n   Correção: {self.fix}"


class LockGateError(Exception):
    def __init__(self, failure: LockGateFailure) -> None:
        super().__init__(failure.format())
        self.failure = failure


@dataclass(frozen=True)
class AppTarget:
    app: str
    node_major: int
    npm_version: str
    image_refs: tuple[str, ...]


def apps_from_tracked(paths: list[str]) -> list[str]:
    """Apps = diretórios de 1º nível com `package.json` no índice."""
    parts = (Path(p).parts for p in paths)
    return sorted({p[0] for p in parts if len(p) == 2 and p[1] == "package.json"})


def tracked_files(repo: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=True
    )
    return result.stdout.splitlines()


def node_image_refs(app: str, dockerfile: str) -> tuple[str, ...]:
    matches = (_FROM_RE.match(line) for line in dockerfile.splitlines())
    refs = tuple(m.group("ref") for m in matches if m)
    unresolved = [r for r in refs if "$" in r]
    if unresolved:
        raise _dockerfile_error(app, f"FROM com variável não resolvível: {unresolved}")
    node_refs = tuple(r for r in refs if _NODE_IMAGE_RE.match(r))
    if not node_refs:
        raise _dockerfile_error(
            app, f"nenhum `FROM node:` em {app}/Dockerfile (FROMs: {list(refs)})"
        )
    return node_refs


def node_major(app: str, refs: tuple[str, ...]) -> int:
    majors = {_major_of(app, ref) for ref in refs}
    if len(majors) != 1:
        raise _dockerfile_error(
            app, f"stages com majors divergentes {sorted(majors)}: {list(refs)}"
        )
    return majors.pop()


def _major_of(app: str, ref: str) -> int:
    match = _NODE_IMAGE_RE.match(ref)
    rest = (match.group("rest") if match else None) or ""
    major = _MAJOR_RE.match(rest)
    if major is None:
        raise _dockerfile_error(app, f"tag sem major numérico: {ref!r} (esperado node:<N>-…)")
    return int(major.group(1))


def _dockerfile_error(app: str, detail: str) -> LockGateError:
    fix = f"pine `FROM node:<major>-alpine@sha256:…` literal em todo stage de {app}/Dockerfile"
    return LockGateError(LockGateFailure(app, "dockerfile", detail, fix))


def npm_version_for(app: str, major: int) -> str:
    if major in NPM_BY_NODE_MAJOR:
        return NPM_BY_NODE_MAJOR[major]
    detail = (
        f"Node {major} (FROM de {app}/Dockerfile) fora de NPM_BY_NODE_MAJOR={NPM_BY_NODE_MAJOR}"
    )
    fix = (
        f"meça `docker run --rm --entrypoint npm <ref do FROM> -v` e adicione "
        f'`{major}: "<versão>",` em NPM_BY_NODE_MAJOR ({SCRIPT})'
    )
    raise LockGateError(LockGateFailure(app, "mapa", detail, fix))


def resolve_target(repo: Path, app: str, tracked: set[str]) -> AppTarget:
    for required in ("package-lock.json", "Dockerfile"):
        if f"{app}/{required}" not in tracked:
            detail = f"{app}/package.json versionado sem {app}/{required}"
            fix = f"versione {app}/{required} — o lock só tem consumidor conhecido pelo FROM do Dockerfile"
            raise LockGateError(LockGateFailure(app, "app", detail, fix))
    refs = node_image_refs(app, (repo / app / "Dockerfile").read_text(encoding="utf-8"))
    major = node_major(app, refs)
    return AppTarget(app, major, npm_version_for(app, major), tuple(dict.fromkeys(refs)))


def run_npm_ci_dry_run(app_dir: Path, npm_version: str) -> subprocess.CompletedProcess[str]:
    cmd = ["npx", "-y", f"npm@{npm_version}", "ci", "--dry-run", "--ignore-scripts"]
    try:
        return subprocess.run(
            cmd, cwd=app_dir, capture_output=True, text=True, timeout=_NPM_TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"timeout de {_NPM_TIMEOUT_S}s")


def check_lock(repo: Path, target: AppTarget, runner: NpmRunner) -> LockGateFailure | None:
    result = runner(repo / target.app, target.npm_version)
    if result.returncode == 0:
        return None
    output = (result.stderr or "") + (result.stdout or "")
    return _npm_failure(target, output)


def npm_error_excerpt(output: str) -> str:
    """Cabeça do erro do npm, sem o bloco de uso: o motivo vem antes dele."""
    lines = [ln for ln in output.splitlines() if ln.strip() not in ("", "npm error", "npm ERR!")]
    end = next((i for i, ln in enumerate(lines) if _NPM_USAGE_START in ln), len(lines))
    kept = [ln for ln in lines[:end] if "complete log of this run" not in ln]
    hidden = len(kept) - _NPM_EXCERPT_MAX
    shown = kept[:_NPM_EXCERPT_MAX] + ([f"… (+{hidden} linhas)"] if hidden > 0 else [])
    return "\n".join(f"     {line}" for line in shown)


def _npm_failure(target: AppTarget, output: str) -> LockGateFailure:
    npm = f"npm@{target.npm_version}"
    excerpt = npm_error_excerpt(output)
    if "ERESOLVE" in output:
        detail = f"conflito de peer (ERESOLVE) no {npm}\n{excerpt}"
        return LockGateFailure(target.app, "peer", detail, _PEER_FIX)
    if any(marker in output for marker in _LOCK_DESYNC_MARKERS):
        return _lock_desync_failure(target, npm, excerpt)
    detail = (
        f"`npx {npm} ci --dry-run` falhou sem ser por lock (rede, registry, Node local)\n{excerpt}"
    )
    fix = f"rode o comando à mão; o {npm} exige Node ^20.17 || >=22.9 no PATH"
    return LockGateFailure(target.app, "ambiente", detail, fix)


def _lock_desync_failure(target: AppTarget, npm: str, excerpt: str) -> LockGateFailure:
    detail = f"package-lock.json dessincronizado de package.json para o {npm} (FROM node:{target.node_major})"
    fix = (
        f"cd {target.app} && npx -y {npm} install --package-lock-only --ignore-scripts"
        f" && git add package-lock.json  (incidente cb0ff11, 2026-04-25)"
    )
    return LockGateFailure(target.app, "lock", f"{detail}\n{excerpt}", fix)


def run_image_npm_version(ref: str) -> subprocess.CompletedProcess[str]:
    cmd = ["docker", "run", "--rm", "--entrypoint", "npm", ref, "-v"]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=_NPM_TIMEOUT_S)


def verify_image(target: AppTarget, docker: DockerRunner) -> list[LockGateFailure]:
    failures = []
    for ref in target.image_refs:
        result = docker(ref)
        found = result.stdout.strip()
        if result.returncode != 0 or not found:
            detail = f"`docker run {ref} npm -v` falhou: {result.stderr.strip()[-300:]}"
            failures.append(
                LockGateFailure(target.app, "ambiente", detail, "confira o Docker do job")
            )
            continue
        failures.extend(_compare_image_npm(target, ref, found))
    return failures


def _compare_image_npm(target: AppTarget, ref: str, found: str) -> list[LockGateFailure]:
    expected = target.npm_version
    if found.split(".")[0] != expected.split(".")[0]:
        detail = f"{ref} traz npm {found}; NPM_BY_NODE_MAJOR[{target.node_major}] = {expected!r}"
        fix = f'NPM_BY_NODE_MAJOR[{target.node_major}] = "{found}" em {SCRIPT}'
        return [LockGateFailure(target.app, "imagem", detail, fix)]
    if found != expected:
        print(
            f"::warning::{target.app}: {ref} traz npm {found}, o mapa pina {expected} (minor é eixo aberto)"
        )
    return []


def _npx_missing(env: Mapping[str, str]) -> int:
    if env.get("CI", "").lower() in ("1", "true"):
        print("🛑 npx ausente no PATH em CI: o lock-sync não checou nada.", file=sys.stderr)
        return 1
    print("⚠️  npx ausente: lock-sync pulado (no CI ele reprova).", file=sys.stderr)
    return 0


def _report(failures: list[LockGateFailure]) -> int:
    for failure in failures:
        print(failure.format(), file=sys.stderr)
    return 1 if failures else 0


def _resolve_all(
    repo: Path, apps: list[str] | None
) -> tuple[list[AppTarget], list[LockGateFailure]]:
    tracked = tracked_files(repo)
    targets, failures = [], []
    for app in apps or apps_from_tracked(tracked):
        try:
            targets.append(resolve_target(repo, app, set(tracked)))
        except LockGateError as err:
            failures.append(err.failure)
    return targets, failures


def main(
    argv: list[str] | None = None,
    *,
    npm_runner: NpmRunner = run_npm_ci_dry_run,
    docker_runner: DockerRunner = run_image_npm_version,
    which: Callable[[str], str | None] = shutil.which,
    env: Mapping[str, str] = os.environ,
) -> int:
    args = _parse_args(argv)
    targets, failures = _resolve_all(args.repo, args.verify_image)
    if args.verify_image:
        return _report(failures + [f for t in targets for f in verify_image(t, docker_runner)])
    if which("npx") is None:
        return _report(failures) or _npx_missing(env)
    lock_failures = (check_lock(args.repo, t, npm_runner) for t in targets)
    return _report(failures + [f for f in lock_failures if f])


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument(
        "--verify-image",
        nargs="+",
        metavar="APP",
        help="compara o major do npm da imagem do FROM com NPM_BY_NODE_MAJOR (requer Docker)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
