#!/usr/bin/env python3
"""W2-T05 · ADR-233 — gate: exige bump de PROMPT_VERSION quando prompt LLM muda."""

# Como funciona — heurística intencionalmente simples (sem AST quebradiço):
#   - Para cada arquivo monitorado com PROMPT_VERSION, compara com origin/main:<path>.
#   - Arquivo novo / idêntico / bumpado → OK. Conteúdo diferente sem bump → falha.
#   - Valida formato canônico: regex CANONICAL_VERSION_RE (semver puro OU
#     <slug>-v<semver> legado).
# False positive aceito (refactor whitespace força bump) — preferível a false
# negative (mudança real sem bump invalida cache LLM em produção).
# Bypass de emergência: MATHOMS_SKIP_PROMPT_VERSION_CHECK=1.
# Uso: pre-commit via pass_filenames; CI smoke roda sem argv (varre tudo).
#
# Duas famílias de arquivo, um invariante (A40.l93 · achado N2 do fecho da A40.l89):
#   - `.py` em PROMPT_DIRS com `PROMPT_VERSION` — auto-discovery pela constante.
#   - `.yaml` em config/prompts/ com `version:` — DECLARADO, nunca descoberto (ver
#     YAML_VERSIONADO). O `version:` do manifest do parecer vira `manifest_version`,
#     que entra na chave do cache Redis com TTL de 7 dias: editar sem bump servia
#     parecer gerado sob o manifest anterior por uma semana, e nada cobrava.

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PROMPT_DIRS = (Path("pipeline/llm/prompts"), Path("pipeline/llm/schemas"))
PROMPT_YAML_DIR = Path("config/prompts")

# Critério de admissão: a `version:` entra em chave de cache que **não** hasheia o
# texto do prompt. Não é "mora em config/prompts/" — o cache genérico de resposta
# ([[ADR-307]]) hasheia system+user renderizados e se auto-invalida, então prompt
# que passa só por ele não precisa desta rota. Glob aqui produziria garantia falsa:
# o leitor assumiria cobertura onde não há cache a proteger.
YAML_VERSIONADO: dict[Path, str] = {
    PROMPT_YAML_DIR / "parecer_planejador.yaml": "manifest_version na chave do parecer (TTL 7d)",
    PROMPT_YAML_DIR
    / "section_summaries.yaml": "prompt_version na chave da narrativa de seção (TTL 24h)",
    PROMPT_YAML_DIR / "lineage_debug.yaml": "version estratifica a telemetria do eval de lineage",
}

# O outro lado da IGUALDADE DE CONJUNTO com o diretório. YAML novo que não esteja em
# nenhum dos dois reprova pedindo a declaração — allowlist que só cresce falha aberta
# (mesma razão escrita no `_RESOLUCAO_DIVIDA_DECLARADA`). Motivo por entrada: denylist
# sem motivo é o próximo doc falso.
YAML_SEM_CACHE_VERSIONADO: dict[Path, str] = {
    PROMPT_YAML_DIR / "chart_conclusions.yaml": "templates determinísticos; `version:` sem leitor",
    PROMPT_YAML_DIR / "e15_secoes_rfb_2024.yaml": "catálogo de seções do E1.5c, não é prompt",
    PROMPT_YAML_DIR
    / "e16_codigos_rfb_2024.yaml": "tabela RFB; o prompt versionado é pipeline/llm/schemas/e16_irpf_full.py",
}

# Captura ``PROMPT_VERSION = "X"`` (single ou double quote) no início da linha.
PROMPT_VERSION_RE = re.compile(
    r'^\s*PROMPT_VERSION\s*=\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)

# Ancorado em coluna 0, SEM o `^\s*` do padrão acima. A tolerância de indentação
# faria a chave de um bloco aninhado passar por `version:` de topo — colar o padrão
# da branch Python aqui seria a mesma classe de defeito que esta extensão fecha.
# Precondição medida em 2026-08-28: nos 6 YAMLs, toda ocorrência em coluna 0 é a
# chave de máquina. Bloco escalar com conteúdo em coluna 0 casaria prosa — e com o
# check de formato ligado isso falha ALTO (prosa não é semver), não em silêncio.
YAML_VERSION_RE = re.compile(r'^version:[ \t]*["\']?([^"\'\s#]+)', re.MULTILINE)

# Formato canônico (errata ADR-233 §Migration, A20.l12): semver puro ESTRITO.
# A tolerância <slug>-v<semver> foi removida — todos os prompts migraram.
CANONICAL_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

UPSTREAM_REF = os.environ.get("MATHOMS_PROMPT_VERSION_BASE", "origin/main")


def _run_git(args: list[str]) -> tuple[int, str]:
    """Roda git, retorna (returncode, stdout). stderr suprimido."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout


def _extract_version(content: str, path: Path | None = None) -> str | None:
    """Valor da primeira versão declarada — `PROMPT_VERSION` no .py, `version:` no YAML."""
    regex = YAML_VERSION_RE if path is not None and path.suffix == ".yaml" else PROMPT_VERSION_RE
    m = regex.search(content)
    return m.group(1) if m else None


def _read_local(path: Path) -> str | None:
    """Lê arquivo do working tree. None se não existir."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _read_upstream(path: Path) -> str | None:
    """Lê ``{UPSTREAM_REF}:<path>``. None quando o arquivo é novo nessa ref."""
    rc, out = _run_git(["show", f"{UPSTREAM_REF}:{path.as_posix()}"])
    if rc != 0:
        return None
    return out


# `_read_upstream` devolvia `None` para DOIS casos — arquivo novo e ref inexistente —
# e `_check_bump` tratava os dois como OK. Ref que não resolve desligava o gate inteiro
# em silêncio: todo arquivo vira "novo", nenhum bump é cobrado. Hoje o único consumidor
# é o pre-commit local (não há job de CI para este hook), onde `origin/main` costuma
# existir — mas a condição é ambiente, não invariante, e ampliar a cobertura de um
# instrumento que pode estar desligado é o defeito que a A40.l93 fecha nos outros três.
def _upstream_ref_error() -> str | None:
    """Devolve mensagem se ``UPSTREAM_REF`` não resolve para um commit."""
    rc, _ = _run_git(["rev-parse", "--verify", "--quiet", f"{UPSTREAM_REF}^{{commit}}"])
    if rc == 0:
        return None
    return (
        f"ref de comparação {UPSTREAM_REF!r} não resolve para um commit — o gate não "
        f"consegue saber o que mudou e falharia ABERTO. Rode `git fetch origin`, ou "
        f"aponte MATHOMS_PROMPT_VERSION_BASE para uma ref local (ex.: HEAD)."
    )


def _is_prompt_module(path: Path) -> bool:
    """True se ``path`` declara ``PROMPT_VERSION = "..."`` no nível do módulo."""
    content = _read_local(path)
    return bool(content and PROMPT_VERSION_RE.search(content))


def _discover_prompts() -> list[Path]:
    """.py em PROMPT_DIRS que declaram PROMPT_VERSION + os YAMLs declarados."""
    found: list[Path] = []
    for d in PROMPT_DIRS:
        if not d.exists():
            continue
        found.extend(f for f in sorted(d.glob("*.py")) if _is_prompt_module(f))
    found.extend(f for f in sorted(YAML_VERSIONADO) if f.exists())
    return found


# Igualdade de CONJUNTO com o diretório, não `⊆`: YAML novo em config/prompts/ que
# ninguém declarou reprova pedindo o veredito. Sem isto, o defeito N2 volta na
# primeira vez que alguém acrescentar um prompt — que é exatamente como ele nasceu.
def _declaracao_errors() -> list[str]:
    """Declaração + presença: as duas checagens que leem SÓ o disco local."""
    if not PROMPT_YAML_DIR.exists():
        return []
    no_disco = {f for f in PROMPT_YAML_DIR.glob("*.yaml")}
    declarados = set(YAML_VERSIONADO) | set(YAML_SEM_CACHE_VERSIONADO)
    faltando = sorted(str(f) for f in no_disco - declarados)
    fantasma = sorted(str(f) for f in declarados - no_disco)
    erros = [
        f"{f}: YAML em {PROMPT_YAML_DIR}/ não declarado — some em YAML_VERSIONADO "
        f"(a `version:` entra em chave de cache que não hasheia o prompt) ou em "
        f"YAML_SEM_CACHE_VERSIONADO, com o motivo."
        for f in faltando
    ]
    erros += [
        f"{f}: declarado em {__file__} e ausente do disco — remova a entrada." for f in fantasma
    ]
    return erros + _presenca_errors()


# Vale só para o que está em YAML_VERSIONADO, e a assimetria é deliberada: no .py a
# ausência da constante significa "não é prompt" (auto-discovery); no YAML a lista É a
# declaração de que aquela `version:` é load-bearing, então ausência é contradição.
# Roda com `_declaracao_errors`, FORA do ramo que exige a ref: lê só o disco local, e
# assim sobrevive a ref ausente — ao contrário da guarda equivalente do .py, que vive
# dentro de `_check_bump` e depende de `_read_upstream` ter sucesso. A primeira escrita
# desta função a pôs em `_errors_for`, onde o check de ref a curto-circuitava: o
# comentário afirmava hermeticidade que o call-site não entregava.
def _presenca_errors() -> list[str]:
    return [
        f"{path}: declarado em YAML_VERSIONADO ({motivo}) e sem `version:` em coluna 0 "
        f"— restaure-a, ou mova para YAML_SEM_CACHE_VERSIONADO."
        for path, motivo in sorted(YAML_VERSIONADO.items())
        if (c := _read_local(path)) is not None and _extract_version(c, path) is None
    ]


def _check_format(path: Path, version: str) -> str | None:
    """Devolve mensagem de erro se formato inválido, None se OK."""
    if CANONICAL_VERSION_RE.match(version):
        return None
    return (
        f"{path}: PROMPT_VERSION={version!r} não casa com formato canônico "
        f"(ADR-233). Use semver puro 'X.Y.Z' (ex.: '1.0.0', '2.1.3') ou "
        f"o prefix legado '<slug>-v<semver>' (ex.: 'e16-v1.1.0')."
    )


def _check_bump(path: Path, local_content: str) -> str | None:
    """Devolve mensagem de erro se conteúdo mudou mas PROMPT_VERSION não."""
    upstream_content = _read_upstream(path)
    if upstream_content is None or upstream_content == local_content:
        return None
    local_version = _extract_version(local_content, path)
    upstream_version = _extract_version(upstream_content, path)
    if local_version is None:
        return (
            f"{path}: arquivo modificado e tem versão declarada em "
            f"{UPSTREAM_REF}, mas ela foi removida — restaure-a."
        )
    if upstream_version is None or local_version != upstream_version:
        return None
    return (
        f"{path}: conteúdo mudou mas a versão continua "
        f"{local_version!r}. Bump (ex.: '{local_version}' → "
        f"'{_suggest_bump(local_version)}') para invalidar cache LLM "
        f"(W2-T05, ADR-233)."
    )


def _suggest_bump(current: str) -> str:
    """Sugere próximo patch — ajuda mensagem de erro, não validação."""
    m = re.match(r"^(.*?)(\d+)\.(\d+)\.(\d+)$", current)
    if not m:
        return f"{current}+1"
    prefix, major, minor, patch = m.groups()
    return f"{prefix}{major}.{minor}.{int(patch) + 1}"


def _filter_to_prompt_files(argv: list[str]) -> list[Path]:
    """Filtra argv para .py com PROMPT_VERSION + YAML declarado em YAML_VERSIONADO."""
    out: list[Path] = []
    for raw in argv:
        p = Path(raw)
        if p in YAML_VERSIONADO:
            out.append(p)
            continue
        if not any(p.is_relative_to(d) for d in PROMPT_DIRS):
            continue
        content = _read_local(p)
        if not content or not PROMPT_VERSION_RE.search(content):
            continue
        out.append(p)
    return out


def _errors_for(path: Path) -> list[str]:
    """Coleta erros de formato + bump para um único arquivo (exige a ref)."""
    content = _read_local(path)
    if content is None:
        return []
    version = _extract_version(content, path)
    if version is None:
        return []
    fmt_err = _check_format(path, version)
    if fmt_err:
        return [fmt_err]
    bump_err = _check_bump(path, content)
    return [bump_err] if bump_err else []


def _collect_errors(argv: list[str]) -> list[str]:
    """Erros de bump (exigem a ref) + declaração/presença (leem só o disco local)."""
    ref_error = _upstream_ref_error()
    if ref_error:
        return [ref_error, *_declaracao_errors()]
    files = _filter_to_prompt_files(argv) if argv else _discover_prompts()
    return [e for f in files for e in _errors_for(f)] + _declaracao_errors()


def _report(errors: list[str]) -> None:
    print("ERRO: gate PROMPT_VERSION (W2-T05 · ADR-233) — falhou:", file=sys.stderr)
    for e in errors:
        print(f"  • {e}", file=sys.stderr)
    print(
        "\nVer docs/adr/233-prompt-version-format.md para o formato canônico.\n"
        "Bypass (raro): MATHOMS_SKIP_PROMPT_VERSION_CHECK=1.",
        file=sys.stderr,
    )


def main(argv: list[str]) -> int:
    if os.environ.get("MATHOMS_SKIP_PROMPT_VERSION_CHECK"):
        return 0
    errors = _collect_errors(argv)
    if not errors:
        return 0
    _report(errors)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
