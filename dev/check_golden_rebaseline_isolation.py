#!/usr/bin/env python3
"""Rebaseline de golden em commit ISOLADO de código de produção (G-c · F2-DB5); exit 1 = commit misto."""

# Disciplina de rebaseline (DATA_LINEAGE §Guard-rails G-c): um commit que toca
# golden (`tests/fixtures/pipeline_golden/**`, incl. rebaseline_manifest.yaml —
# viajam juntos) E código de produção (`pipeline/**`, `scripts/**`,
# `backend/app/**`) cimentaria o valor novo junto da mudança que o produziu,
# sem diff auditável. Granularidade POR COMMIT (não por PR-diff): é o que
# permite o fluxo legítimo "PR com N commits, 1 deles é o rebaseline isolado".
# Name-only (paths tocados), nunca conteúdo. `config/schemas/**` e `tests/**`
# NÃO contam como produção: mudar contrato+golden no mesmo commit é o próprio
# fluxo de remoção de campo (F2-DB1).
#
# Modos: --staged (pre-commit, diff em cache) | --commit-range BASE..HEAD (local,
# valida cada commit do range isoladamente) | --pr-head-sha SHA (CI: o range são
# os commits da cabeça que a main do merge sintético ainda não tem).

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# O critério, para o PRÓXIMO arquivo se classificar sozinho: é golden de VALOR quando
# o conteúdo é output medido do sistema e o número É a evidência — cimentá-lo junto da
# mudança que o produziu destrói a auditabilidade. NÃO é golden quando o arquivo é
# CATRACA de dívida (`dev/code_style_baseline.json`, `dev/sigilo_terms_baseline.json`,
# `dev/pipeline_log_pii_baseline.json`): ali andar junto do código é o fluxo correto,
# e exigir isolamento só somaria atrito sem ganho de auditoria.
#
# A40.l80 (destrava A40.l90): `backend/tests/snapshots/dogfood_view_model.json` (233
# numéricos, o view-model publicado) estava FORA — o hook rodava verde e cego sobre o
# único golden que a A40.l90 iria rebaselinar. Fechar só esse arquivo seria fechar por
# instância; o conjunto abaixo é o critério aplicado.
#
# `tests/golden_baselines/` (métricas estruturais do parecer com LLM real, ADR-199 T-27)
# entrou pelo mesmo critério quando o rebaseline mensal passou a sair em branch do
# workflow `planner-golden-monthly.yml` — o prefixo protege o commit HUMANO que
# re-semeia junto de mudança no código do parecer.
_GOLDEN_PREFIXES = (
    "tests/fixtures/pipeline_golden/",
    "backend/tests/snapshots/",
    "dev/snapshots/",
    "tests/golden_baselines/",
)
_PRODUCTION_PREFIXES = ("pipeline/", "scripts/", "backend/app/")


def is_golden(path: str) -> bool:
    return path.startswith(_GOLDEN_PREFIXES)


def is_production(path: str) -> bool:
    return path.startswith(_PRODUCTION_PREFIXES)


def violation(paths: list[str]) -> str | None:
    """Retorna descrição da violação se a lista mistura golden + produção."""
    golden = sorted(p for p in paths if is_golden(p))
    production = sorted(p for p in paths if is_production(p))
    if not golden or not production:
        return None
    return (
        f"golden ({', '.join(golden[:3])}{'…' if len(golden) > 3 else ''}) junto de "
        f"produção ({', '.join(production[:3])}{'…' if len(production) > 3 else ''}) — "
        "separe o rebaseline em commit próprio (label golden-rebaseline, G-c)"
    )


def _git_lines(*args: str, cwd: Path | None = None) -> list[str]:
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True, cwd=cwd)
    return [line for line in out.stdout.splitlines() if line.strip()]


def _staged_paths() -> list[str]:
    return _git_lines("diff", "--cached", "--name-only")


def _commit_paths(sha: str) -> list[str]:
    return _git_lines("diff-tree", "--no-commit-id", "--name-only", "-r", sha)


def _merge_em_curso() -> bool:
    """`MERGE_HEAD` existe entre `git merge` e o commit que o conclui."""
    git_dir = Path(
        subprocess.run(
            ["git", "rev-parse", "--git-dir"], capture_output=True, text=True, check=True
        ).stdout.strip()
    )
    return (git_dir / "MERGE_HEAD").exists()


def check_staged() -> list[str]:
    # Merge commit estagia a UNIÃO dos dois lados, então ele acusa o par
    # golden+produção que o outro ramo já isolou corretamente no PR dele — o
    # ofensor não é de quem mergeia, e não há commit que se possa separar. O
    # modo de CI já pula merge (`rev-list --no-merges`); esta é a mesma regra,
    # que faltava no modo `--staged`. O par de QUEM MERGEIA continua vigiado:
    # ele vive nos commits próprios da branch, que o CI varre um a um.
    if _merge_em_curso():
        return []
    msg = violation(_staged_paths())
    return [f"staged: {msg}"] if msg else []


def check_commit_range(commit_range: str) -> list[str]:
    errors: list[str] = []
    for sha in _git_lines("rev-list", "--no-merges", commit_range):
        msg = violation(_commit_paths(sha))
        if msg:
            errors.append(f"{sha[:10]}: {msg}")
    return errors


class MergeSinteticoInesperado(RuntimeError):
    """HEAD não é o merge sintético do evento com histórico completo — a faixa não existe."""


_SHA = re.compile(r"[0-9a-f]{40}")


def _exige_sha(flag: str, valor: str) -> None:
    if not _SHA.fullmatch(valor):
        raise MergeSinteticoInesperado(f"{flag} deve ser SHA de 40 hex, got {valor!r}")


def _pais_do_merge(merge_sha: str, cwd: Path | None) -> list[str]:
    """Os dois pais do merge do evento; cada desvio do formato tem causa própria."""
    head, *pais = _git_lines("rev-list", "--parents", "-n", "1", "HEAD", cwd=cwd)[0].split()
    if head != merge_sha:
        raise MergeSinteticoInesperado(
            f"HEAD {head[:10]} não é o merge do evento {merge_sha[:10]}: o checkout mudou"
        )
    if not pais:
        raise MergeSinteticoInesperado(
            f"merge {head[:10]} sem pais no clone: o histórico dele não foi buscado — "
            "o fetch precisa ancorar no GITHUB_SHA"
        )
    if len(pais) != 2:
        raise MergeSinteticoInesperado(
            f"HEAD {head[:10]} tem {len(pais)} pai(s), esperado 2 (main, cabeça)"
        )
    return pais


# Em `pull_request` o checkout é o merge sintético: pai 1 = a main contra a qual o
# GitHub montou o merge, pai 2 = a cabeça. `base.sha` NÃO serve de base: é o merge-base
# do último push, e `base.sha..HEAD` arrastava a main desde então — o squash de
# rebaseline alheio reprovava todo PR atrás dela (#2065, run 37868572346). O pai 2 é
# conferido porque, com os pais trocados, a faixa INVERTE e acusa os squashes da main.
def base_do_merge_sintetico(pr_head_sha: str, merge_sha: str, cwd: Path | None = None) -> str:
    """Pai 1 do merge sintético do PR: a main que o merge já contém."""
    _exige_sha("--pr-head-sha", pr_head_sha)
    _exige_sha("--merge-sha", merge_sha)
    ponta_da_main, cabeca = _pais_do_merge(merge_sha, cwd)
    if cabeca != pr_head_sha:
        raise MergeSinteticoInesperado(
            f"pai 2 {cabeca[:10]} não é a cabeça {pr_head_sha[:10]}: com os pais trocados "
            "a faixa inverte"
        )
    _exige_faixa_completa(ponta_da_main, cabeca, cwd)
    return ponta_da_main


# Merge-base encontrado NÃO prova a faixa: com a branch atualizada por merge da main
# (o trem), o merge-base sai certo e o clone raso ainda deixa squash antigo da main
# fora do alcance do pai 1 — a faixa media 50 commits contra 4 reais (sre-devops,
# 2026-10-09). Com a main linear, faixa truncada sempre contém commit sem pai.
def _exige_faixa_completa(ponta_da_main: str, cabeca: str, cwd: Path | None) -> None:
    faixa = f"{ponta_da_main}..{cabeca}"
    for linha in _git_lines("rev-list", "--parents", faixa, cwd=cwd):
        if " " not in linha:
            raise MergeSinteticoInesperado(
                f"a faixa {ponta_da_main[:10]}..{cabeca[:10]} cruza o limite do clone raso em "
                f"{linha[:10]}: o histórico não alcança a base do PR"
            )


def check_pull_request(pr_head_sha: str, merge_sha: str) -> list[str]:
    base = base_do_merge_sintetico(pr_head_sha, merge_sha)
    return check_commit_range(f"{base}..{pr_head_sha}")


def _errors_for(args: argparse.Namespace) -> list[str]:
    if args.pr_head_sha:
        return check_pull_request(args.pr_head_sha, args.merge_sha)
    if args.commit_range:
        return check_commit_range(args.commit_range)
    return check_staged()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--commit-range", default=None, help="BASE..HEAD (local); default: staged")
    modo.add_argument("--pr-head-sha", default=None, help="CI: `pull_request.head.sha`")
    parser.add_argument("--merge-sha", default=None, help="CI: `GITHUB_SHA`, o merge sintético")
    args = parser.parse_args(argv)
    if bool(args.pr_head_sha) != bool(args.merge_sha):
        parser.error("--pr-head-sha e --merge-sha andam juntos")

    try:
        errors = _errors_for(args)
    except MergeSinteticoInesperado as exc:
        print(f"check_golden_rebaseline_isolation: {exc}", file=sys.stderr)
        return 2
    for line in errors:
        print(f"check_golden_rebaseline_isolation: {line}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
