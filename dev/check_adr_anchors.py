#!/usr/bin/env python3
"""Valida anchor links de ADRs — modo legado (DECISIONS.md monolítico) e modo vault (docs/adr/ + shim DECISIONS.md pós-F2.E)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS = REPO_ROOT / "docs" / "DECISIONS.md"
ADR_DIR = REPO_ROOT / "docs" / "adr"

SHIM_MARKER = "<!-- F2.E shim -->"
SHIM_LINES_THRESHOLD = 500

HEADING_RE = re.compile(r"^## (ADR-[\w-]+ —.+)$", re.MULTILINE)
ANCHOR_RE = re.compile(r"\[([^\]]+)\]\(#(adr-[\w\-]+)\)", re.UNICODE)
SHIM_ANCHOR_RE = re.compile(r'<a\s+id="(adr-[\w\-]+)"\s*>\s*</a>', re.UNICODE)
FM_ID_RE = re.compile(r"^id:\s*(ADR-\d{3}(?:-[A-Z]+)?)\s*$", re.MULTILINE)
FM_TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)
FILENAME_RE = re.compile(r"^(\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
NNN_FROM_ANCHOR_RE = re.compile(r"^adr-(\d{3})(?:-|$)")
NNN_FROM_BROKEN_SLUG_RE = re.compile(r"^(adr-\d{3}(?:-[a-z]+)?)--?")


def _display_path(path: Path) -> str:
    """Path relativo a REPO_ROOT quando possível, absoluto fora."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def github_slug(heading_text: str) -> str:
    """Slug do GitHub Slugger (lowercase, remove pontuação ASCII, espaços viram hífen)."""
    s = heading_text.lower()
    s = re.sub(r"[^\w\- ]+", "", s, flags=re.UNICODE)
    return s.replace(" ", "-")


def collect_headings(content: str) -> dict[str, str]:
    """Mapeia título→slug para cada `## ADR-NNN — ...` no arquivo."""
    out: dict[str, str] = {}
    for match in HEADING_RE.finditer(content):
        title = match.group(1).strip()
        out[title] = github_slug(title)
    return out


def collect_anchor_refs(content: str) -> list[tuple[int, str, str]]:
    """Retorna [(linha, texto, slug)] para cada `[X](#adr-...)`, pulando code blocks."""
    refs: list[tuple[int, str, str]] = []
    in_code_block = False
    for line_no, line in enumerate(content.splitlines(), start=1):
        stripped = line.lstrip("> \t")
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        for match in ANCHOR_RE.finditer(line):
            refs.append((line_no, match.group(1), match.group(2)))
    return refs


def find_closest(slug: str, valid_slugs: set[str]) -> str | None:
    """Heurística: retorna slug válido com mesmo prefixo `adr-NNN` se único."""
    m = NNN_FROM_BROKEN_SLUG_RE.match(slug)
    if not m:
        return None
    adr_id = m.group(1)
    candidates = [s for s in valid_slugs if s.startswith(adr_id + "--")]
    return candidates[0] if len(candidates) == 1 else None


def is_shim(content: str) -> bool:
    """True se DECISIONS.md está em modo shim (marcador presente ou < threshold linhas)."""
    if SHIM_MARKER in content:
        return True
    return content.count("\n") < SHIM_LINES_THRESHOLD


def _strip_yaml_quotes(value: str) -> str:
    """Remove aspas externas que YAML pode ter posto em uma string simples."""
    return value.strip().strip('"').strip("'")


def parse_frontmatter(content: str) -> dict[str, str]:
    """Extrai `id` e `title` do frontmatter; vazio se não houver delimitador `---`."""
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}
    block = content[4:end]
    out: dict[str, str] = {}
    id_match = FM_ID_RE.search(block)
    if id_match:
        out["id"] = id_match.group(1)
    title_match = FM_TITLE_RE.search(block)
    if title_match:
        out["title"] = _strip_yaml_quotes(title_match.group(1))
    return out


def _validate_filename(name: str) -> tuple[str | None, str | None]:
    """Retorna (nnn, erro). nnn None + erro se filename inválido."""
    m = FILENAME_RE.match(name)
    if not m:
        return None, (
            f"filename inválido — esperado NNN-slug.md (kebab-case lowercase). Atual: {name!r}."
        )
    return m.group(1), None


def _validate_frontmatter(fm: dict[str, str], filename_nnn: str) -> str | None:
    """Erros estruturais do frontmatter ADR (id presente, title não-vazio, NNN bate)."""
    if "id" not in fm:
        return f"frontmatter sem campo 'id: ADR-NNN' válido (esperado regex {FM_ID_RE.pattern!r})."
    if "title" not in fm or not fm["title"]:
        return "frontmatter sem campo 'title' não-vazio."
    fm_nnn = fm["id"].split("-")[1]
    if fm_nnn != filename_nnn:
        return (
            f"divergência NNN — filename={filename_nnn!r}, "
            f"frontmatter id={fm['id']!r} (esperado NNN={fm_nnn!r})."
        )
    return None


def _validate_adr_file(path: Path) -> str | None:
    """Erro (sem prefixo de path) ou None se ADR é válida."""
    nnn, err = _validate_filename(path.name)
    if err is not None:
        return err
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"erro de leitura — {exc}."
    return _validate_frontmatter(parse_frontmatter(content), nnn or "")


def validate_adr_vault(adr_dir: Path) -> tuple[int, list[str]]:
    """Walka adr_dir/*.md e valida cada arquivo; retorna (num_ok, erros)."""
    errors: list[str] = []
    num_ok = 0
    if not adr_dir.is_dir():
        return 0, errors
    for path in sorted(adr_dir.glob("*.md")):
        problem = _validate_adr_file(path)
        if problem is None:
            num_ok += 1
        else:
            errors.append(f"  {_display_path(path)}: {problem}")
    return num_ok, errors


def _index_vault_by_nnn(adr_dir: Path) -> dict[str, Path]:
    """Indexa ADRs do vault pelo NNN extraído do filename."""
    by_nnn: dict[str, Path] = {}
    for path in adr_dir.glob("*.md"):
        m = FILENAME_RE.match(path.name)
        if m:
            by_nnn[m.group(1)] = path
    return by_nnn


def _resolve_shim_anchor(anchor_id: str, by_nnn: dict[str, Path]) -> str | None:
    """Erro descrevendo o problema, ou None se anchor resolve em adr/."""
    nnn_match = NNN_FROM_ANCHOR_RE.match(anchor_id)
    if not nnn_match:
        return f"shim anchor #{anchor_id} não casa formato 'adr-NNN-...' (NNN deve ter 3 dígitos)."
    nnn = nnn_match.group(1)
    if nnn not in by_nnn:
        return (
            f"shim anchor #{anchor_id} refere ADR-{nnn} "
            f"mas não há docs/adr/{nnn}-*.md correspondente."
        )
    return None


def validate_shim_anchors(content: str, adr_dir: Path) -> list[str]:
    """Cada `<a id="adr-NNN-...">` no shim deve ter ADR correspondente em adr/."""
    if not adr_dir.is_dir():
        return [
            f"  shim cita #{aid} mas docs/adr/ não existe."
            for aid in {m.group(1) for m in SHIM_ANCHOR_RE.finditer(content)}
        ]
    by_nnn = _index_vault_by_nnn(adr_dir)
    errors: list[str] = []
    for match in SHIM_ANCHOR_RE.finditer(content):
        problem = _resolve_shim_anchor(match.group(1), by_nnn)
        if problem is not None:
            errors.append(f"  {problem}")
    return errors


def _format_legacy_error(line_no: int, text: str, cited: str, suggestion: str | None) -> str:
    """Formata uma linha de erro de anchor legado, com sugestão quando há candidato único."""
    base = f"  L{line_no}: [{text}](#{cited})"
    if suggestion:
        return base + f"\n    → sugerido: #{suggestion}"
    return base + "\n    → (sem sugestão automática — verificar manualmente)"


def run_legacy_mode(content: str) -> tuple[int, int, list[str]]:
    """Modo legado: valida `[X](#adr-...)` contra slugs gerados dos headings."""
    headings = collect_headings(content)
    valid_slugs = set(headings.values())
    refs = collect_anchor_refs(content)
    errors: list[str] = []
    for line_no, text, cited in refs:
        if cited not in valid_slugs:
            suggestion = find_closest(cited, valid_slugs)
            errors.append(_format_legacy_error(line_no, text, cited, suggestion))
    return len(headings), len(refs), errors


def run_shim_mode(content: str, adr_dir: Path) -> tuple[int, int, list[str]]:
    """Modo shim: valida anchors HTML preservados + walk em adr_dir."""
    shim_errors = validate_shim_anchors(content, adr_dir)
    num_anchors = len(SHIM_ANCHOR_RE.findall(content))
    num_files_ok, vault_errors = validate_adr_vault(adr_dir)
    return num_anchors, num_files_ok, shim_errors + vault_errors


def _parse_args() -> argparse.Namespace:
    """Argparse com `--suggest [TITLE]` (bare flag ou string), `--file`, `--adr-dir`."""
    parser = argparse.ArgumentParser(
        description="Valida anchor links de ADRs (modo legado ou shim/vault)."
    )
    parser.add_argument(
        "--suggest",
        nargs="?",
        const="",
        default=None,
        help=(
            "Sem string: imprime sed-friendly fixes. "
            "Com string: imprime o slug GitHub Slugger desse título."
        ),
    )
    parser.add_argument("--file", type=Path, default=DECISIONS)
    parser.add_argument("--adr-dir", type=Path, default=ADR_DIR)
    return parser.parse_args()


def _print_legacy_header(file_label: str) -> None:
    """Cabeçalho de modo legado (DECISIONS.md monolítico)."""
    print(f"{file_label} — modo legado (DECISIONS.md monolítico)")


def _print_shim_header(file_label: str, adr_label: str) -> None:
    """Cabeçalho de modo shim (DECISIONS.md pós-F2.E + vault docs/adr/)."""
    print(
        f"{file_label} — modo shim (F2.E pós-split); "
        f"validando anchors históricos + vault em {adr_label}/"
    )


def _print_sed_hint_for(err: str) -> None:
    """Imprime `sed: s|...|...|g` quando o erro tem candidato único."""
    cited = re.search(r"\(#([^)]+)\)", err)
    sug = re.search(r"sugerido: #(\S+)", err)
    if cited and sug:
        print(f"    sed: s|#{cited.group(1)}|#{sug.group(1)}|g")


def _print_errors(errors: list[str], with_sed_hint: bool) -> None:
    """Lista erros formatados; opcionalmente injeta sed hints quando aplicável."""
    print(f"✗ {len(errors)} problema(s) encontrado(s):\n")
    for err in errors:
        print(err)
        if with_sed_hint and "sugerido:" in err:
            _print_sed_hint_for(err)
        print()


def _run_shim(content: str, file_label: str, adr_dir: Path, adr_label: str) -> list[str]:
    """Imprime header+summary do modo shim e retorna erros."""
    _print_shim_header(file_label, adr_label)
    num_anchors, num_files_ok, errors = run_shim_mode(content, adr_dir)
    print(f"  anchors históricos preservados: {num_anchors}; ADRs válidas em vault: {num_files_ok}")
    return errors


def _run_legacy(content: str, file_label: str, adr_dir: Path, adr_label: str) -> list[str]:
    """Imprime header+summary do modo legado, agrega vault opcional, retorna erros."""
    _print_legacy_header(file_label)
    num_headings, num_refs, errors = run_legacy_mode(content)
    print(f"  {num_headings} headings, {num_refs} anchor refs")
    if adr_dir.is_dir():
        num_files_ok, vault_errors = validate_adr_vault(adr_dir)
        print(f"  vault {adr_label}/: {num_files_ok} ADR(s) válidas")
        errors.extend(vault_errors)
    return errors


def _run_validation(args: argparse.Namespace) -> list[str]:
    """Despacha modo (shim ou legado) com base no conteúdo de args.file."""
    content = args.file.read_text(encoding="utf-8")
    file_label = _display_path(args.file)
    adr_label = _display_path(args.adr_dir)
    if is_shim(content):
        return _run_shim(content, file_label, args.adr_dir, adr_label)
    return _run_legacy(content, file_label, args.adr_dir, adr_label)


def main() -> int:
    """Entry point: roteia `--suggest TITLE` (slug stdout) vs validação completa."""
    args = _parse_args()
    if args.suggest is not None and args.suggest != "":
        print(github_slug(args.suggest))
        return 0
    if not args.file.is_file():
        print(f"erro: {args.file} não existe.", file=sys.stderr)
        return 1
    errors = _run_validation(args)
    if not errors:
        print("✓ todos os invariantes válidos")
        return 0
    _print_errors(errors, with_sed_hint=args.suggest == "")
    return 1


if __name__ == "__main__":
    sys.exit(main())
