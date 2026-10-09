#!/usr/bin/env python3
"""Major do Node é um só por app: `.nvmrc` = `FROM node` = CI = compose de dev.

O ecossistema `docker` do Dependabot sobe o major do `FROM node:` sem tocar no
CI — foi assim que o CI ficou em Node 20 (EOL) com a imagem de prod em 26
(#1634 → #2077). `ignore: semver-major` trocaria a deriva por estagnação muda;
este gate deixa o PR de major vermelho até o `<app>/.nvmrc` subir junto.

App = diretório de 1º nível com `package.json`; o major dele vive em
`<app>/.nvmrc` (um por app porque o Dependabot abre um PR por diretório).
Sítios medidos: todo `FROM` de `Dockerfile*` do repo; todo `actions/setup-node`,
`container` e `services` de `.github/workflows/*.yml`; e `image: node:*` de
`docker-compose*.yml`. Job e serviço se atribuem a um app só por campo de path
(`working-directory`, `cache-dependency-path`, `node-version-file`;
`working_dir`, `build`, `volumes`) — `name:`/`run:` citam outros apps.

Fail-closed — o gate não adivinha o major: `.nvmrc` ausente ou não numérico,
tag sem major (`node:lts`, `node:${V}`), base desconhecida ou ausência de
`FROM node` no Dockerfile de um app, `setup-node` sem versão (usa o Node do
runner), expressão em `node-version`, `node-version-file` que não é
`<app>/.nvmrc` nem `${{ … }}/.nvmrc`, e Node literal que não se atribui a
exatamente um app reprovam. Também reprova job cujo `run:` (fora de linha de
comentário) chama `npm`/`npx`/`node`/`pre-commit` antes de qualquer
`setup-node` e sem `container: node:*` — roda no Node do runner; `pre-commit`
conta porque hook `language: system` chama `node` (probabilidade-parity).

`@types/node` — toda cópia em `<app>/package-lock.json`, aninhada inclusive
(`reference types` mescla os globais) — tem major ≤ `.nvmrc`: types acima do
runtime liberam API que prod não tem. `≤`, não `=`: types atrás e major ímpar
passam (todo major ≥27 é LTS). Declarado no package.json sem cópia no lock
reprova. O major de `@types/node` vem em PR isolado do Dependabot (#2153),
vermelho até o runtime subir: nenhum grupo que carrega major o casa
(`test_dependabot_isola_o_major_de_types_node`).

Mede só o MAJOR: o CI resolve `26` para o último 26.x e a imagem roda o 26.x
do digest — diferença de patch aceita.

Rejeitado (2026-10-08): `engines.node` + `engine-strict` e `devEngines`
(`onFail: error`). O updater npm do Dependabot roda Node 24 com
`npm install --ignore-scripts --package-lock-only` e aborta (EBADENGINE /
EBADDEVENGINES): os PRs npm, inclusive os de segurança do frontend-ops,
parariam em silêncio. `engines` sem strict é só warn. O job sem `setup-node`
fecha pela regra de `run:` acima.

Deferido (2026-10-08; dono: owner do repo): `@types/node` = runtime. `≤` não vê
estagnação (types majors atrás do runtime) nem API removida entre o major dos
types e o do runtime. Retomar no próximo bump de
major do runtime.

Eixos NÃO fechados: dev local fora do compose (nenhum controle de install que
poupe o Dependabot); `.node-version`/`.tool-versions`; Node de imagem que não se
chama `node` fora do Dockerfile de um app; Node chamado dentro de composite
action local, de `workflow_call` ou de script fora de `pre-commit`; o major do
npm; e o prefixo de `${{ … }}/.nvmrc` (o `setup-node` falha sozinho se o
arquivo não existir).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
_PRUNED_DIRS = frozenset(
    {"node_modules", "_scratch", "storage", "data", "inbox", "inbox_processed", "venv"}
)
_FROM_RE = re.compile(r"^\s*FROM\s+(?:--\S+\s+)*(?P<ref>\S+)(?:\s+AS\s+(?P<alias>\S+))?", re.I)
_MAJOR_RE = re.compile(r"^v?(\d+)(?:[.-]|$)")
_COMPOSE_RE = re.compile(r"^(docker-)?compose[^/]*\.ya?ml$")
_EXPRESSION_NVMRC_RE = re.compile(r"^\$\{\{[^}]*\}\}/\.nvmrc$")
_SETUP_NODE = "actions/setup-node@"
_NODE_COMMAND_RE = re.compile(r"(?<![\w./-])(npm|npx|node|pre-commit)(?![\w-])")
_TYPES_NODE = "@types/node"
_DEPENDENCY_FIELDS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
_TYPES_RUNTIME_HINT = (
    "suba o runtime antes, em PR humano (.nvmrc + Dockerfile + compose) — não comite no "
    "branch do Dependabot; o PR dele fica verde no rebase"
)
_TYPES_NESTED_HINT = "fixe a cópia aninhada com `overrides` no package.json"
_BUMP_HINT = (
    "alinhe este sítio — ou, se o major novo é o certo (PR de major do Dependabot), "
    "suba o .nvmrc e os demais sítios do app no mesmo PR"
)


@dataclass(frozen=True)
class NodeMajorDivergence:
    where: str
    found: str
    expected: str

    def format(self) -> str:
        return f"{self.where}: {self.found}; esperado {self.expected}"


@dataclass(frozen=True)
class NodePin:
    where: str
    raw: str
    major: int | None
    apps: frozenset[str]


@dataclass
class NodeParityReport:
    apps: frozenset[str] = frozenset()
    majors: dict[str, int] = field(default_factory=dict)
    pins: list[NodePin] = field(default_factory=list)
    types_node: dict[str, object] = field(default_factory=dict)
    divergences: list[NodeMajorDivergence] = field(default_factory=list)


SiteCollector = Callable[[Path, Path, frozenset[str], NodeParityReport], None]


def node_major(version: str) -> int | None:
    match = _MAJOR_RE.match(version.strip())
    return int(match.group(1)) if match else None


def split_image(ref: str) -> tuple[str, str]:
    """`docker.io/library/node:26-alpine@sha256:…` → (`node`, `26-alpine`)."""
    last = ref.split("@", 1)[0].rsplit("/", 1)[-1]
    repository, _, tag = last.partition(":")
    return repository, tag


def path_apps(values: list[object], apps: frozenset[str]) -> frozenset[str]:
    parts = (re.split(r"[/:\s]+", v) for v in values if isinstance(v, str))
    return frozenset(part for split in parts for part in split) & apps


def walk_repo(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in _PRUNED_DIRS and (d == ".github" or not d.startswith("."))
        )
        yield from (Path(dirpath, name) for name in sorted(filenames))


def discover_apps(root: Path) -> frozenset[str]:
    return frozenset(
        p.parent.name
        for p in root.glob("*/package.json")
        if p.parent.name not in _PRUNED_DIRS and not p.parent.name.startswith(".")
    )


def collect_nvmrc(root: Path, app: str, report: NodeParityReport) -> None:
    nvmrc = root / app / ".nvmrc"
    content = nvmrc.read_text().strip() if nvmrc.is_file() else None
    major = node_major(content or "")
    if major is not None:
        report.majors[app] = major
        return
    found = "arquivo ausente" if content is None else f"conteúdo {content!r}"
    report.divergences.append(
        NodeMajorDivergence(f"{app}/.nvmrc", found, "um major numérico (ex.: `26`)")
    )


def read_json(path: Path) -> dict[str, object] | None:
    return as_dict(json.loads(path.read_text())) if path.is_file() else None


def declares_types_node(manifest: dict[str, object] | None) -> bool:
    return any(_TYPES_NODE in as_dict((manifest or {}).get(f)) for f in _DEPENDENCY_FIELDS)


def installed_types_node(lock: dict[str, object] | None) -> dict[str, object]:
    """Toda cópia do lock — a aninhada também entra no global via `reference types`."""
    packages = as_dict((lock or {}).get("packages"))
    suffix = f"node_modules/{_TYPES_NODE}"
    return {p: as_dict(meta).get("version") for p, meta in packages.items() if p.endswith(suffix)}


def judge_types_node(
    where: str, version: object, app: str, major: int
) -> NodeMajorDivergence | None:
    found = node_major(version) if isinstance(version, str) else None
    if found is not None and found <= major:
        return None
    shown = f"{version!r} sem major numérico" if found is None else f"{version!r} → major {found}"
    nested = not where.endswith(f"#node_modules/{_TYPES_NODE}")
    remedy = _TYPES_NESTED_HINT if nested else _TYPES_RUNTIME_HINT
    return NodeMajorDivergence(
        where,
        f"{_TYPES_NODE} {shown}",
        f"major ≤ {major} ({app}/.nvmrc) — types acima do runtime liberam API que prod não tem; "
        + remedy,
    )


def collect_types_node(root: Path, app: str, report: NodeParityReport) -> None:
    if app not in report.majors:
        return  # .nvmrc inválido já reprovou
    lock_path = f"{app}/package-lock.json"
    copies = installed_types_node(read_json(root / lock_path))
    if not copies and declares_types_node(read_json(root / app / "package.json")):
        found = f"{_TYPES_NODE} declarado em {app}/package.json sem cópia no lock"
        report.divergences.append(NodeMajorDivergence(lock_path, found, "`packages` com a versão"))
    for path, version in sorted(copies.items()):
        report.types_node[f"{lock_path}#{path}"] = version
        divergence = judge_types_node(f"{lock_path}#{path}", version, app, report.majors[app])
        report.divergences.extend([divergence] if divergence else [])


def judge_pin(pin: NodePin, majors: dict[str, int]) -> NodeMajorDivergence | None:
    if pin.major is None:
        return NodeMajorDivergence(
            pin.where, f"{pin.raw!r} sem major numérico", "major explícito (ex.: `node:26-alpine`)"
        )
    if len(pin.apps) != 1:
        owners = sorted(pin.apps) or "nenhum app"
        return NodeMajorDivergence(
            pin.where,
            f"{pin.raw!r} atribuível a {owners}",
            f"exatamente um de {sorted(majors)} — use `node-version-file: <app>/.nvmrc`",
        )
    (app,) = pin.apps
    if app not in majors or pin.major == majors[app]:
        return None  # app sem major válido já reprovou no próprio .nvmrc
    return NodeMajorDivergence(
        pin.where, f"{pin.raw!r} → major {pin.major}", f"{majors[app]} ({app}/.nvmrc); {_BUMP_HINT}"
    )


def dockerfile_froms(path: Path) -> Iterator[tuple[int, str, str | None]]:
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        match = _FROM_RE.match(line)
        if match:
            alias = match["alias"]
            yield lineno, match["ref"], alias.lower() if alias else None


def image_pins(where: str, refs: list[str], owners: frozenset[str]) -> Iterator[NodePin]:
    for ref in refs:
        repository, tag = split_image(ref)
        if repository == "node":
            yield NodePin(where, ref, node_major(tag), owners)


def unknown_bases(
    rel: str, froms: list[tuple[int, str, str | None]]
) -> Iterator[NodeMajorDivergence]:
    stages: set[str] = set()
    for lineno, ref, alias in froms:
        if split_image(ref)[0] != "node" and ref.lower() not in stages:
            yield NodeMajorDivergence(f"{rel}:{lineno}", f"base {ref!r}", "`node:<major>` ou stage")
        stages.update({alias} if alias else set())


def collect_dockerfile(
    root: Path, path: Path, apps: frozenset[str], report: NodeParityReport
) -> None:
    rel = path.relative_to(root).as_posix()
    owner = frozenset({rel.split("/", 1)[0]}) & apps if "/" in rel else frozenset()
    froms = list(dockerfile_froms(path))
    pins = [pin for n, ref, _ in froms for pin in image_pins(f"{rel}:{n}", [ref], owner)]
    report.pins.extend(pins)
    if not owner:
        return
    report.divergences.extend(unknown_bases(rel, froms))
    if not pins:
        report.divergences.append(NodeMajorDivergence(rel, "0 `FROM node:`", "≥1 (imagem de app)"))


def as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def run_directory(node: dict[str, object]) -> object:
    return as_dict(as_dict(node.get("defaults")).get("run")).get("working-directory")


def job_owners(
    workflow: dict[str, object], job: dict[str, object], apps: frozenset[str]
) -> frozenset[str]:
    """Apps do job por `working-directory` e `cache-dependency-path` — nunca por prosa."""
    values = [run_directory(workflow), run_directory(job)]
    for step in job.get("steps") or []:
        step = as_dict(step)
        values += [
            step.get("working-directory"),
            as_dict(step.get("with")).get("cache-dependency-path"),
        ]
    return path_apps(values, apps)


def setup_node_options(job: dict[str, object]) -> Iterator[dict[str, object]]:
    for step in job.get("steps") or []:
        step = as_dict(step)
        if str(step.get("uses", "")).startswith(_SETUP_NODE):
            yield as_dict(step.get("with"))


def judge_version_file(
    where: str, version_file: str, owners: frozenset[str], apps: frozenset[str]
) -> NodeMajorDivergence | None:
    if _EXPRESSION_NVMRC_RE.match(version_file):
        return None
    app, _, name = version_file.partition("/")
    if name == ".nvmrc" and app in apps and (not owners or app in owners):
        return None
    expected = " ou ".join(f"{a}/.nvmrc" for a in sorted(owners & apps) or sorted(apps))
    return NodeMajorDivergence(where, f"node-version-file {version_file!r}", expected)


def setup_node_divergences(
    where: str, version: object, version_file: object, owners: frozenset[str], apps: frozenset[str]
) -> list[NodeMajorDivergence]:
    found: list[NodeMajorDivergence | None] = []
    if version is None and version_file is None:
        found.append(
            NodeMajorDivergence(
                where, "setup-node sem versão (Node do runner)", "node-version-file"
            )
        )
    if version_file is not None:
        found.append(judge_version_file(where, str(version_file), owners, apps))
    if version is not None and "${{" in str(version):
        found.append(
            NodeMajorDivergence(
                where, f"node-version {version!r}", "node-version-file: <app>/.nvmrc"
            )
        )
    return [divergence for divergence in found if divergence is not None]


def collect_setup_node(
    where: str, options: dict[str, object], owners: frozenset[str], report: NodeParityReport
) -> None:
    version, version_file = options.get("node-version"), options.get("node-version-file")
    report.divergences.extend(
        setup_node_divergences(where, version, version_file, owners, report.apps)
    )
    if version is not None and "${{" not in str(version):
        major = node_major(str(version))
        report.pins.append(NodePin(where, f"node-version: {version}", major, owners))


def container_image(job: dict[str, object]) -> object:
    container = job.get("container")
    return as_dict(container).get("image") if isinstance(container, dict) else container


def job_images(job: dict[str, object]) -> Iterator[str]:
    container = container_image(job)
    yield from [container] if isinstance(container, str) else []
    for service in as_dict(job.get("services")).values():
        image = as_dict(service).get("image")
        yield from [image] if isinstance(image, str) else []


def node_command(run: object) -> str | None:
    """`pre-commit` conta: hook `language: system` chama `node`/`npx` (probabilidade-parity)."""
    lines = (line for line in str(run or "").splitlines() if not line.lstrip().startswith("#"))
    match = _NODE_COMMAND_RE.search("\n".join(lines))
    return match.group(1) if match else None


def runner_node_step(job: dict[str, object]) -> tuple[int, str] | None:
    """1º step que chama Node antes de qualquer `setup-node` — roda no Node do runner."""
    for index, step in enumerate(job.get("steps") or [], start=1):
        step = as_dict(step)
        if str(step.get("uses", "")).startswith(_SETUP_NODE):
            return None
        command = node_command(step.get("run"))
        if command is not None:
            return index, command
    return None


def judge_runner_node(where: str, job: dict[str, object]) -> NodeMajorDivergence | None:
    image = container_image(job)
    found = runner_node_step(job)
    if found is None or (isinstance(image, str) and split_image(image)[0] == "node"):
        return None
    index, command = found
    return NodeMajorDivergence(
        where,
        f"step {index} chama `{command}` no Node do runner (sem setup-node antes)",
        "`actions/setup-node` com `node-version-file: <app>/.nvmrc` antes dele "
        "(ou `container: node:<major>`)",
    )


def collect_workflow(
    root: Path, path: Path, apps: frozenset[str], report: NodeParityReport
) -> None:
    rel = path.relative_to(root).as_posix()
    workflow = as_dict(yaml.safe_load(path.read_text()))
    for job_id, job in as_dict(workflow.get("jobs")).items():
        where, job = f"{rel}#{job_id}", as_dict(job)
        owners = job_owners(workflow, job, apps)
        for options in setup_node_options(job):
            collect_setup_node(where, options, owners, report)
        runner_node = judge_runner_node(where, job)
        report.divergences.extend([runner_node] if runner_node else [])
        report.pins.extend(image_pins(where, list(job_images(job)), owners))


def service_owners(service: dict[str, object], apps: frozenset[str]) -> frozenset[str]:
    build = service.get("build")
    volumes = [
        v if isinstance(v, str) else as_dict(v).get("source") for v in service.get("volumes") or []
    ]
    values = [service.get("working_dir"), build, as_dict(build).get("context"), *volumes]
    return path_apps(values, apps)


def collect_compose(root: Path, path: Path, apps: frozenset[str], report: NodeParityReport) -> None:
    rel = path.relative_to(root).as_posix()
    services = as_dict(as_dict(yaml.safe_load(path.read_text())).get("services"))
    for name, service in services.items():
        service = as_dict(service)
        refs = [ref for ref in [service.get("image")] if isinstance(ref, str)]
        report.pins.extend(image_pins(f"{rel}#{name}", refs, service_owners(service, apps)))


def is_workflow(rel: str) -> bool:
    return rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml"))


def site_collector(path: Path, rel: str) -> SiteCollector | None:
    if path.name.startswith("Dockerfile"):
        return collect_dockerfile
    if is_workflow(rel):
        return collect_workflow
    return collect_compose if _COMPOSE_RE.match(path.name) else None


def collect_sites(root: Path, apps: frozenset[str], report: NodeParityReport) -> None:
    for path in walk_repo(root):
        collector = site_collector(path, path.relative_to(root).as_posix())
        if collector is not None:
            collector(root, path, apps, report)


def check_node_parity(root: Path) -> NodeParityReport:
    apps = discover_apps(root)
    report = NodeParityReport(apps=apps)
    if not apps:
        report.divergences.append(
            NodeMajorDivergence(str(root), "nenhum app (`*/package.json`)", "≥1 — root errado?")
        )
    for app in sorted(apps):
        collect_nvmrc(root, app, report)
        collect_types_node(root, app, report)
    collect_sites(root, apps, report)
    judged = (judge_pin(pin, report.majors) for pin in report.pins)
    report.divergences.extend(d for d in judged if d is not None)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO)
    report = check_node_parity(parser.parse_args(argv).root)
    majors = ", ".join(f"{app}={major}" for app, major in sorted(report.majors.items()))
    for divergence in report.divergences:
        print(f"[node-version-parity] {divergence.format()}", file=sys.stderr)
    if report.divergences:
        total = len(report.divergences)
        print(f"node-version-parity: {total} divergência(s) ({majors})", file=sys.stderr)
        return 1
    sites = f"{len(report.pins)} sítios de Node, {len(report.types_node)} {_TYPES_NODE}"
    print(f"node-version-parity: OK ({sites}; {majors})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
