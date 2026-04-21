"""Detectores P1-P10 (CLAUDE.md §Code style)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from dev._audit_cs_internals.models import (
    FORBIDDEN_IDENTIFIERS,
    MONEY_NAME_PATTERN,
    Offender,
    REPO_ROOT,
    WHAT_COMMENT_PATTERNS,
)


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _is_bank_parser(rel: str) -> bool:
    return rel.startswith("scripts/e2/banks/") and rel.endswith(".py")


def _is_test_fixture_fn(rel: str, name: str) -> bool:
    base = Path(rel).name
    is_conf_or_test = base == "conftest.py" or base.startswith("test_")
    return is_conf_or_test and (name.startswith("make_") or name.startswith("pytest_"))


def _is_golden_test(rel: str) -> bool:
    name = Path(rel).name
    return "golden" in name and name.startswith("test_")


def _severity_for_fn_length(length: int) -> str:
    return "high" if length > 40 else "med"


def _severity_for_file_length(length: int) -> str:
    return "high" if length > 1000 else "med"


def parse_ast(path: Path) -> tuple[ast.Module | None, str]:
    """Parse arquivo Python; retorna (tree, src). tree=None se syntax error."""
    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, ""
    try:
        return ast.parse(src, filename=str(path)), src
    except SyntaxError:
        return None, src


def detect_long_functions(path: Path, tree: ast.Module) -> list[Offender]:
    """P1: funções >20 linhas (inclui docstring/comentários)."""
    rel = _rel(path)
    out: list[Offender] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            maybe = _long_function_offender(node, rel)
            if maybe is not None:
                out.append(maybe)
    return out


def _long_function_offender(node: ast.FunctionDef | ast.AsyncFunctionDef, rel: str) -> Offender | None:
    end = node.end_lineno or node.lineno
    length = end - node.lineno + 1
    if length <= 20:
        return None
    allow = _is_bank_parser(rel) or _is_test_fixture_fn(rel, node.name)
    severity = "info" if allow else _severity_for_fn_length(length)
    return Offender(
        id="", category="P1_long_functions", severity=severity, file=rel,
        line_start=node.lineno, line_end=end, length=length, identifier=node.name,
        message=f"Function {length} lines; max 20 (CLAUDE.md 'Funções 4-20 linhas')",
        allowlisted=allow,
    )


def detect_long_file(path: Path, src: str) -> list[Offender]:
    """P2: arquivos >500 linhas."""
    lines = src.count("\n") + 1
    if lines <= 500:
        return []
    rel = _rel(path)
    allow = _is_golden_test(rel)
    severity = "info" if allow else _severity_for_file_length(lines)
    return [Offender(
        id="", category="P2_long_files", severity=severity, file=rel,
        line_start=1, line_end=lines, length=lines, identifier=Path(rel).name,
        message=f"File {lines} lines; max 500 (CLAUDE.md 'Arquivos ≤500 linhas')",
        allowlisted=allow,
    )]


def _ann_is_dict_str_any(node: ast.expr | None) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    if not isinstance(node.value, ast.Name) or node.value.id not in ("Dict", "dict"):
        return False
    slice_ = node.slice
    if not isinstance(slice_, ast.Tuple) or len(slice_.elts) != 2:
        return False
    first, second = slice_.elts
    return (isinstance(first, ast.Name) and first.id == "str"
            and isinstance(second, ast.Name) and second.id == "Any")


def _is_boundary_py(rel: str) -> bool:
    return rel.startswith("backend/app/api/") or rel.startswith("pipeline/domain/services/")


def detect_dict_str_any_boundary(path: Path, tree: ast.Module) -> list[Offender]:
    """P3: Dict[str, Any] em API pública ou domain service."""
    rel = _rel(path)
    if not _is_boundary_py(rel):
        return []
    out: list[Offender] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.extend(_check_fn_annotations(node, rel))
    return out


def _check_fn_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef, rel: str) -> list[Offender]:
    out: list[Offender] = []
    checks: list[tuple[ast.expr | None, str]] = [(node.returns, "return")]
    for arg in node.args.args + node.args.kwonlyargs:
        checks.append((arg.annotation, arg.arg))
    for ann, label in checks:
        if _ann_is_dict_str_any(ann):
            out.append(Offender(
                id="", category="P3_dict_str_any_boundary", severity="high", file=rel,
                line_start=ann.lineno, line_end=ann.end_lineno or ann.lineno,
                length=1, identifier=f"{node.name}.{label}",
                message=f"Dict[str, Any] em {label} de boundary; use Pydantic/DTO tipado",
            ))
    return out


def _ann_is_optional(node: ast.expr | None) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    return isinstance(node.value, ast.Name) and node.value.id == "Optional"


def detect_optional_without_default(path: Path, tree: ast.Module, src: str) -> list[Offender]:
    """P4: Optional[...] em parâmetro sem default=None (heurística low)."""
    out: list[Offender] = []
    rel = _rel(path)
    lines = src.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.extend(_check_optional_in_fn(node, rel, lines))
    return out


def _check_optional_in_fn(node: ast.FunctionDef | ast.AsyncFunctionDef, rel: str, lines: list[str]) -> list[Offender]:
    out: list[Offender] = []
    positional = node.args.args
    first_default_idx = len(positional) - len(node.args.defaults)
    for i, arg in enumerate(positional):
        if not _ann_is_optional(arg.annotation) or i >= first_default_idx:
            continue
        line_idx = (arg.lineno or 1) - 1
        if _has_nearby_comment(lines, line_idx):
            continue
        out.append(Offender(
            id="", category="P4_optional_no_default", severity="low", file=rel,
            line_start=arg.lineno, line_end=arg.end_lineno or arg.lineno, length=1,
            identifier=f"{node.name}.{arg.arg}",
            message="Optional[...] sem default None e sem comentário WHY",
        ))
    return out


def _has_nearby_comment(lines: list[str], line_idx: int) -> bool:
    for offset in (-1, 0):
        target = line_idx + offset
        if 0 <= target < len(lines) and "#" in lines[target]:
            return True
    return False


def _ann_is_float(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Name) and node.id == "float"


def detect_float_money(path: Path, tree: ast.Module) -> list[Offender]:
    """P5: float em contexto monetário (ADR-090)."""
    out: list[Offender] = []
    rel = _rel(path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.extend(_float_money_in_fn(node, rel))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if _ann_is_float(node.annotation) and MONEY_NAME_PATTERN.search(node.target.id):
                out.append(_float_offender(rel, node.lineno, node.end_lineno or node.lineno, node.target.id, "variable"))
    return out


def _float_money_in_fn(node: ast.FunctionDef | ast.AsyncFunctionDef, rel: str) -> list[Offender]:
    out: list[Offender] = []
    for arg in node.args.args + node.args.kwonlyargs:
        if _ann_is_float(arg.annotation) and MONEY_NAME_PATTERN.search(arg.arg):
            out.append(_float_offender(rel, arg.lineno, arg.end_lineno or arg.lineno,
                                       f"{node.name}({arg.arg})", "parameter"))
    if _ann_is_float(node.returns) and MONEY_NAME_PATTERN.search(node.name):
        out.append(_float_offender(rel, node.lineno, node.returns.end_lineno or node.lineno, node.name, "return"))
    return out


def _float_offender(rel: str, start: int, end: int, identifier: str, kind: str) -> Offender:
    return Offender(
        id="", category="P5_float_money", severity="high", file=rel,
        line_start=start, line_end=end, length=1, identifier=identifier,
        message=f"float em {kind} com nome monetário; use Money.brl/Decimal (ADR-090)",
    )


def _node_name(node: ast.AST) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    return None


def detect_forbidden_names(path: Path, tree: ast.Module) -> list[Offender]:
    """P6: nomes proibidos (CLAUDE.md 'Nomes específicos e únicos')."""
    rel = _rel(path)
    out: list[Offender] = []
    base = Path(rel).stem
    if base in FORBIDDEN_IDENTIFIERS:
        out.append(_forbidden_name_offender(rel, 1, 1, base, "Filename"))
    for node in ast.walk(tree):
        name = _node_name(node)
        if name and name in FORBIDDEN_IDENTIFIERS:
            end = node.end_lineno or node.lineno
            out.append(_forbidden_name_offender(rel, node.lineno, end, name, "Identifier"))
    return out


def _forbidden_name_offender(rel: str, start: int, end: int, name: str, kind: str) -> Offender:
    return Offender(
        id="", category="P6_forbidden_names", severity="med", file=rel,
        line_start=start, line_end=end, length=1, identifier=name,
        message=f"{kind} '{name}' é nome genérico proibido",
    )


def detect_multiparagraph_docstring(path: Path, tree: ast.Module) -> list[Offender]:
    """P7: docstrings multi-parágrafo (CLAUDE.md 'Uma linha de intent')."""
    rel = _rel(path)
    candidates: list[ast.AST] = [tree]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            candidates.append(node)
    return [o for o in (_docstring_offender(node, rel) for node in candidates) if o is not None]


def _docstring_offender(node: ast.AST, rel: str) -> Offender | None:
    doc = ast.get_docstring(node, clean=False)
    if not doc or "\n\n" not in doc:
        return None
    name = _node_name(node) or "<module>"
    line = getattr(node, "lineno", 1)
    return Offender(
        id="", category="P7_multiparagraph_docstring", severity="low", file=rel,
        line_start=line, line_end=line, length=doc.count("\n") + 1,
        identifier=name,
        message="Docstring multi-parágrafo; preferir 1-linha de intent",
    )


def detect_what_comments(path: Path, src: str) -> list[Offender]:
    """P8: comentários WHAT heurísticos."""
    out: list[Offender] = []
    rel = _rel(path)
    for i, line in enumerate(src.splitlines(), start=1):
        if any(pat.search(line) for pat in WHAT_COMMENT_PATTERNS):
            out.append(Offender(
                id="", category="P8_what_comments", severity="low", file=rel,
                line_start=i, line_end=i, length=1,
                identifier=line.strip()[:60],
                message="Comentário WHAT heurístico; prefira WHY ou remova",
            ))
    return out


def detect_deep_nesting(path: Path, tree: ast.Module) -> list[Offender]:
    """P9: profundidade >2 de If/For/While/Try em funções."""
    out: list[Offender] = []
    rel = _rel(path)
    if _is_bank_parser(rel):
        return out
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        depth = _max_ctrl_depth(node.body, 0)
        if depth <= 2:
            continue
        out.append(Offender(
            id="", category="P9_deep_nesting", severity="low", file=rel,
            line_start=node.lineno, line_end=node.end_lineno or node.lineno,
            length=depth, identifier=node.name,
            message=f"Nesting depth {depth}; máx 2 (3 aceitável só em parsing)",
        ))
    return out


def _max_ctrl_depth(body: list[ast.stmt], current: int) -> int:
    best = current
    for stmt in body:
        best = max(best, _depth_for_stmt(stmt, current))
    return best


def _depth_for_stmt(stmt: ast.stmt, current: int) -> int:
    if isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try)):
        body = _max_ctrl_depth(stmt.body, current + 1)
        orelse = _max_ctrl_depth(getattr(stmt, "orelse", []), current + 1)
        return max(body, orelse)
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return current
    inner = getattr(stmt, "body", None)
    if isinstance(inner, list):
        return _max_ctrl_depth(inner, current)
    return current


def detect_pipeline_boundary() -> list[Offender]:
    """P10: pipeline/ não importa fastapi/celery/sqlalchemy (delega ao check existente)."""
    if not (REPO_ROOT / "pipeline").is_dir():
        return []
    sys.path.insert(0, str(REPO_ROOT))
    from dev.check_pipeline_boundaries import collect_violations
    out: list[Offender] = []
    for line in collect_violations():
        if ": forbidden" not in line:
            continue
        out.append(_boundary_line_to_offender(line))
    return [o for o in out if o]


def _boundary_line_to_offender(line: str) -> Offender | None:
    path_line, msg = line.split(": forbidden", 1)
    try:
        file_path, lineno = path_line.rsplit(":", 1)
        ln = int(lineno)
    except ValueError:
        return None
    try:
        rel = Path(file_path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel = file_path
    return Offender(
        id="", category="P10_pipeline_boundary", severity="critical",
        file=rel, line_start=ln, line_end=ln, length=1,
        identifier=f"line {ln}",
        message=f"Pipeline boundary: forbidden{msg.rstrip()}",
    )
