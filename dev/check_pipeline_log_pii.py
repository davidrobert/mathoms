#!/usr/bin/env python3
"""Gate anti-PII em logs do pipeline (ADR-273 critério 6).

Regra (condição sre-devops): em ``pipeline/**``, chamadas ``logger.<level>(...)``
aceitam **apenas message literal** + kwargs seguros (``extra``, ``exc_info``,
``stack_info``, ``stacklevel``). Qualquer interpolação — f-string, ``%``,
``.format()``, concatenação ou args posicionais — é bloqueada: cobre
``logger.info(f"saldo {v}")``, ``logger.info("saldo %s", v)`` e variantes
que o match por nome de variável sensível deixaria passar. Dado variável
vai via ``extra={}`` (redigido por chave pela denylist compartilhada em
``pipeline/observability/redaction.py``).

Ofensores pré-ADR-273 (%-style) vivem no baseline ratchet
(``dev/pipeline_log_pii_baseline.json``): contagem por arquivo só pode
cair — ofensor novo ou arquivo novo falha o gate; burn-down acontece na
migração stage-a-stage (ADR-273 §Próximos passos PR2..N). Ao zerar um
arquivo, rode ``--save-baseline`` para travar o progresso.

Uso: ``python3 dev/check_pipeline_log_pii.py [--self-test|--save-baseline]``
"""

from __future__ import annotations

import ast
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = REPO_ROOT / "pipeline"
BASELINE_PATH = Path(__file__).resolve().parent / "pipeline_log_pii_baseline.json"

_LOG_METHODS = frozenset({"debug", "info", "warning", "error", "critical", "exception", "log"})
_SAFE_KWARGS = frozenset({"extra", "exc_info", "stack_info", "stacklevel"})
_LOGGER_NAME_HINTS = ("logger", "log", "_logger", "obs_logger")


def _is_logger_call(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in _LOG_METHODS:
        return False
    target = func.value
    if isinstance(target, ast.Name):
        return any(hint in target.id.lower() for hint in _LOGGER_NAME_HINTS)
    if isinstance(target, ast.Call):
        inner = target.func
        name = inner.attr if isinstance(inner, ast.Attribute) else getattr(inner, "id", "")
        return name in {"get_logger", "getLogger"}
    return False


def _message_arg(node: ast.Call) -> ast.expr | None:
    args = list(node.args)
    if isinstance(node.func, ast.Attribute) and node.func.attr == "log" and args:
        args = args[1:]
    return args[0] if args else None


def _violations_in_call(node: ast.Call) -> list[str]:
    problems: list[str] = []
    message = _message_arg(node)
    if message is None:
        return problems
    if not (isinstance(message, ast.Constant) and isinstance(message.value, str)):
        kind = type(message).__name__
        problems.append(f"message não-literal ({kind}) — use string fixa + extra={{}}")
    extra_positional = node.args[2:] if _is_log_variant(node) else node.args[1:]
    if extra_positional:
        problems.append("args posicionais de interpolação (%-style) — use extra={}")
    for kw in node.keywords:
        if kw.arg is not None and kw.arg not in _SAFE_KWARGS:
            problems.append(f"kwarg {kw.arg!r} fora da allowlist {sorted(_SAFE_KWARGS)}")
    return problems


def _is_log_variant(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr == "log"


def check_source(source: str, filename: str) -> list[str]:
    """Retorna violações ``arquivo:linha: motivo`` para um módulo."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [f"{filename}:{exc.lineno}: syntax error impede análise ({exc.msg})"]
    logger_calls = (
        node for node in ast.walk(tree) if isinstance(node, ast.Call) and _is_logger_call(node)
    )
    return [
        f"{filename}:{node.lineno}: {problem}"
        for node in logger_calls
        for problem in _violations_in_call(node)
    ]


_BAD_SNIPPETS = (
    'logger.info(f"saldo {saldo}")',
    'logger.warning("valor %s", valor)',
    'logger.error("cpf " + cpf)',
    'logger.info("x {}".format(v))',
    "obs_logger.info(msg_var)",
    'logging.getLogger("mathoms.pipeline.x").info(f"a {b}")',
)
_GOOD_SNIPPETS = (
    'logger.info("stage aggregate", extra={"reconciled": n})',
    'logger.warning("config load failed", extra={"error": str(exc)}, exc_info=True)',
    'logger.info("stage_start")',
    'print(f"cli output {x}")',
)


def _self_test() -> int:
    failures = [
        f"deveria falhar e passou: {s}" for s in _BAD_SNIPPETS if not check_source(s, "<bad>")
    ]
    failures += [
        f"deveria passar e falhou: {s}" for s in _GOOD_SNIPPETS if check_source(s, "<good>")
    ]
    if failures:
        print("SELF-TEST FALHOU:")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print(f"self-test ok ({len(_BAD_SNIPPETS)} bad + {len(_GOOD_SNIPPETS)} good)")
    return 0


def _collect_findings() -> list[str]:
    findings: list[str] = []
    for py_file in sorted(PIPELINE_DIR.rglob("*.py")):
        rel = py_file.relative_to(REPO_ROOT)
        findings.extend(check_source(py_file.read_text(encoding="utf-8"), str(rel)))
    return findings


def _counts_by_file(findings: list[str]) -> dict[str, int]:
    return dict(Counter(finding.split(":", 1)[0] for finding in findings))


def _load_baseline() -> dict[str, int]:
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _save_baseline(counts: dict[str, int]) -> int:
    BASELINE_PATH.write_text(
        json.dumps(dict(sorted(counts.items())), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"baseline salvo: {len(counts)} arquivos, {sum(counts.values())} offenders")
    return 0


def _report_regressions(regressions: dict[str, tuple[int, int]], findings: list[str]) -> int:
    print("Interpolação NOVA em logger.* do pipeline (PII risk — ADR-273):")
    for path, (allowed, got) in sorted(regressions.items()):
        print(f"  {path}: {allowed} → {got} (+{got - allowed})")
        offenders = (finding for finding in findings if finding.startswith(f"{path}:"))
        print("    " + "\n    ".join(offenders))
    print("Fix: message literal + dado variável em extra={} (denylist redige por chave).")
    return 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    findings = _collect_findings()
    counts = _counts_by_file(findings)
    if "--save-baseline" in argv:
        return _save_baseline(counts)
    baseline = _load_baseline()
    regressions = {
        path: (baseline.get(path, 0), count)
        for path, count in counts.items()
        if count > baseline.get(path, 0)
    }
    if regressions:
        return _report_regressions(regressions, findings)
    improved = sum(1 for p, b in baseline.items() if counts.get(p, 0) < b)
    if improved:
        print(f"burn-down em {improved} arquivo(s) — rode --save-baseline para travar.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
