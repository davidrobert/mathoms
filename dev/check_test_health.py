#!/usr/bin/env python3
"""Detecta anti-padrões de teste que custam tempo de CI sem dar sinal.

Roda em pre-commit (AST/regex em backend/tests/ + tests/). Modo --profile
está reservado para nightly (não implementado em pre-commit). Política
completa em ADR-210.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_DIRS = [REPO_ROOT / "backend" / "tests", REPO_ROOT / "tests"]

# Env vars que ligam hard-fail de testes soft-fail. Se um teste tem
# `print(...)` em path de fail e a env var não está em nenhum workflow
# do CI, é noise — sinaliza só.
KNOWN_HARDFAIL_VARS = {"MATHOMS_ENFORCE_STAGE_RENAME"}

EXPENSIVE_HELPER_SIGNALS = (
    ".read_text(",
    ".read_bytes(",
    ".rglob(",
    ".glob(",
    ".walk(",
    "subprocess.",
    "requests.",
    "httpx.",
    "asyncio.run(",
    "for ",
)


def _iter_test_files() -> list[Path]:
    out: list[Path] = []
    for d in TEST_DIRS:
        if d.is_dir():
            out.extend(sorted(d.rglob("test_*.py")))
    return out


def _parametrize_names(decorator: ast.Call) -> set[str]:
    """Extrai nomes da string passada para `pytest.mark.parametrize`."""
    if not (decorator.args and isinstance(decorator.args[0], ast.Constant)):
        return set()
    raw = decorator.args[0].value
    if not isinstance(raw, str):
        return set()
    return {n.strip() for n in re.split(r"[,\s]+", raw) if n.strip()}


def _collect_parametrize_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for d in node.decorator_list:
        if (
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr == "parametrize"
        ):
            names |= _parametrize_names(d)
    return names


def _helper_is_cached(helper_id: str, source: str) -> bool:
    pat = re.compile(
        rf"@(?:functools\.)?lru_cache.*?\n[^\n]*def\s+{re.escape(helper_id)}\s*\(",
        re.DOTALL,
    )
    return bool(pat.search(source))


def _helper_is_expensive(helper_id: str, source: str) -> bool:
    pat = re.compile(
        rf"def\s+{re.escape(helper_id)}\s*\([^)]*\)[^:]*:([\s\S]+?)(?=\n(?:def|class|@|\Z))",
    )
    m = pat.search(source)
    if not m:
        return True  # sem corpo identificável → assume expensive
    body = m.group(1)
    return any(sig in body for sig in EXPENSIVE_HELPER_SIGNALS)


def _suspect_recompute_call(call: ast.Call, params: set[str], param_names: set[str]) -> bool:
    """Call é suspeita de recomputo? Helper privado, sem args, fora de params."""
    if not (isinstance(call.func, ast.Name) and call.func.id.startswith("_")):
        return False
    if call.args or call.keywords:
        return False
    if call.func.id in params:
        return False
    call_arg_names: set[str | None] = set()
    for a in call.args:
        if isinstance(a, ast.Name):
            call_arg_names.add(a.id)
    return param_names.isdisjoint(call_arg_names)


def _recompute_finding(
    call: ast.Call, source: str, param_names: set[str]
) -> tuple[int, str] | None:
    helper_id = call.func.id  # type: ignore[union-attr]
    if _helper_is_cached(helper_id, source) or not _helper_is_expensive(helper_id, source):
        return None
    return (
        call.lineno,
        f"`{helper_id}()` em test parametrizado por {sorted(param_names)} ignora o param "
        f"— provável recomputo (use @functools.lru_cache no helper ou despararametrize).",
    )


def _iter_body_calls(node: ast.FunctionDef | ast.AsyncFunctionDef):
    """Itera todas as Call no corpo da função (não em decorator_list)."""
    import itertools

    return (
        sub
        for sub in itertools.chain.from_iterable(ast.walk(stmt) for stmt in node.body)
        if isinstance(sub, ast.Call)
    )


def _scan_function_body(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source: str,
    param_names: set[str],
) -> list[tuple[int, str]]:
    """Procura calls suspeitas no corpo (não em decorator_list)."""
    params = {a.arg for a in node.args.args}
    findings: list[tuple[int, str]] = []
    for call in _iter_body_calls(node):
        if not _suspect_recompute_call(call, params, param_names):
            continue
        finding = _recompute_finding(call, source, param_names)
        if finding is not None:
            findings.append(finding)
    return findings


def _find_parametrize_ignoring_arg(tree: ast.AST, source: str) -> list[tuple[int, str]]:
    """Parametrize que recomputa scan caro a cada caso."""
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        param_names = _collect_parametrize_names(node)
        if not param_names:
            continue
        findings.extend(_scan_function_body(node, source, param_names))
    return findings


_SKIPIF_PATTERN = re.compile(
    r"@pytest\.mark\.skipif\([\s\S]*?os\.environ\.get\(['\"]MATHOMS_\w+['\"]"
)


def _soft_fail_msg(env_var: str) -> str:
    return (
        f"Teste é soft-fail enquanto `{env_var}` não estiver em nenhum workflow do CI. "
        f"Considere `@pytest.mark.skipif(os.getenv('{env_var}') != '1', reason=...)` "
        f"até o switch para hard-fail."
    )


def _find_soft_fail_without_active_hardfail(source: str, path: Path) -> list[tuple[int, str]]:
    """`os.environ.get('MATHOMS_*')` em path de fail sem `skipif` correspondente."""
    if not re.search(r"os\.environ\.get\(['\"]MATHOMS_\w+['\"]", source):
        return []
    if _SKIPIF_PATTERN.search(source):
        return []
    findings: list[tuple[int, str]] = []
    for line_no, line in enumerate(source.splitlines(), start=1):
        m = re.search(r"os\.environ\.get\(['\"](MATHOMS_\w+)['\"]", line)
        if m and m.group(1) in KNOWN_HARDFAIL_VARS:
            findings.append((line_no, _soft_fail_msg(m.group(1))))
    return findings


def _find_migration_tests_without_marker(source: str, path: Path) -> list[tuple[int, str]]:
    """Migration test sem `pytest.mark.migration`."""
    is_migration_test = "migration" in path.name or "alembic.versions" in source
    if not is_migration_test:
        return []
    if "pytest.mark.migration" in source or "pytestmark" in source:
        return []
    return [
        (
            1,
            "Test parece exercitar código de migration one-shot mas não tem "
            "`pytestmark = pytest.mark.migration` — roda em todo PR. Adicione o marker.",
        )
    ]


def _find_orphan_cutover_tests(source: str, path: Path) -> list[tuple[int, str]]:
    """Docstring "Após Sprint X" cujo cutover já passou (verificação humana)."""
    docstring_match = re.match(r"^['\"]{3}([\s\S]+?)['\"]{3}", source)
    if not docstring_match:
        return []
    doc = docstring_match.group(1)
    m = re.search(r"[Aa]p[óo]s a [Ss]print\s+([A-Z]?\d+(?:\.\d+)*)", doc)
    if not m:
        return []
    return [
        (
            1,
            f"Docstring marca este teste como descartável após Sprint {m.group(1)}. "
            f"Confira docs/CHANGELOG.md — se já entregue, delete o arquivo + código testado.",
        )
    ]


def _has_fast_bcrypt_fixture() -> bool:
    """Conftest define `_fast_bcrypt_for_tests` (patch global rounds=4)."""
    conftest = REPO_ROOT / "backend" / "tests" / "conftest.py"
    if not conftest.is_file():
        return False
    return "_fast_bcrypt_for_tests" in conftest.read_text(encoding="utf-8")


def _find_bcrypt_in_test(source: str, path: Path) -> list[tuple[int, str]]:
    """`bcrypt.hashpw`/`gensalt` em test individual sem o fixture global rounds=4."""
    if "conftest" in path.name:
        return []
    if _has_fast_bcrypt_fixture():
        return []
    findings: list[tuple[int, str]] = []
    for line_no, line in enumerate(source.splitlines(), start=1):
        if re.search(r"\bbcrypt\.(hashpw|gensalt)\s*\(", line):
            findings.append(
                (
                    line_no,
                    "`bcrypt.hashpw`/`gensalt` em test individual usa work-factor de prod "
                    "(~0.5-2 s/call no runner). Mova para conftest com `rounds=4` "
                    "ou use o `_fast_bcrypt_for_tests` autouse session fixture.",
                )
            )
    return findings


def _check_file(test_file: Path) -> tuple[int, str | None]:
    try:
        source = test_file.read_text(encoding="utf-8")
    except OSError as exc:
        return -1, f"ERR: {test_file}: {exc}"
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return 0, f"ERR: {test_file}: {exc}"
    rel = test_file.relative_to(REPO_ROOT).as_posix()
    findings = (
        _find_parametrize_ignoring_arg(tree, source)
        + _find_soft_fail_without_active_hardfail(source, test_file)
        + _find_migration_tests_without_marker(source, test_file)
        + _find_orphan_cutover_tests(source, test_file)
        + _find_bcrypt_in_test(source, test_file)
    )
    for line_no, msg in findings:
        print(f"{rel}:{line_no}: {msg}")
    return len(findings), None


def check_all() -> int:
    total = 0
    for test_file in _iter_test_files():
        count, err = _check_file(test_file)
        if count < 0:
            print(err, file=sys.stderr)
            return 2
        if err:
            print(err, file=sys.stderr)
        total += count
    if total:
        print(
            f"\n{total} test-health finding(s) — leia em CLAUDE.md §Code style › Testes (ADR-210)."
        )
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="store_true", help="(nightly) não implementado.")
    args = parser.parse_args()
    if args.profile:
        print("--profile não suportado em pre-commit; rode no workflow nightly.", file=sys.stderr)
        return 2
    return check_all()


if __name__ == "__main__":
    sys.exit(main())
