#!/usr/bin/env python3
"""Gate: proíbe parse monetário à mão fora do parser canônico (ADR-090 · r5/M28)."""

# O idioma `.replace(".", "").replace(",", ".")` existia em 9 implementações. Aplicado
# a string que já é decimal ISO ("243285.37", que é o que os nossos stages emitem) ele
# strippa a decimal como se fosse milhar e devolve 24328537.0 — inflação de 100×.
# Chegou ao relatório: patrimônio líquido, IF (798% contra 16,7% real), prazo e gap.
#
# Por que gate e não só teste: a suíte ficou VERDE durante todo o incidente. Cada cópia
# tinha (ou não) seu teste, e nenhum comparava as cópias. Teste fixa comportamento de
# quem ele chama; gate impede a 10ª cópia de nascer.
#
# Detecção por AST — encadeamento contendo `.replace(".", "")` E `.replace(",", ".")`.
# Não casa strip de pontuação em CPF/CNPJ nem formatação de saída (`.replace(".", ",")`).

from __future__ import annotations

import ast
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BUCKETS = ("pipeline", "scripts", "backend/app")

# `money_parsing` É o parser canônico. `pipeline_common.safe_float` é divergência
# registrada: tenta `float()` primeiro (logo NÃO tem o bug de 100×) e é locale-aware;
# mantida porque a CLI depende do parâmetro `locale`. Ver §Blast radius do PR.
_ALLOWLIST = frozenset(
    {
        "pipeline/domain/services/money_parsing.py",
        "scripts/pipeline_common.py",
        # `_normalize_both_separators` devolve STRING normalizada, não valor, e só
        # roda quando os DOIS separadores estão presentes — usa a mesma regra do
        # último separador. Contrato diferente do parser; conferido em 2026-08-12.
        "backend/app/services/task_progress_service.py",
    }
)

_STRIP_PONTO = (".", "")
_VIRGULA_PARA_PONTO = (",", ".")


def _replace_args(call: ast.Call) -> tuple[str, str] | None:
    """`x.replace(a, b)` com a/b literais str → `(a, b)`; senão ``None``."""
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "replace":
        return None
    if len(call.args) != 2:
        return None
    primeiro, segundo = call.args
    if not (isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str)):
        return None
    if not (isinstance(segundo, ast.Constant) and isinstance(segundo.value, str)):
        return None
    return primeiro.value, segundo.value


def _cadeia_de_replaces(call: ast.Call) -> list[tuple[str, str]]:
    """Coleta os pares (de, para) de um encadeamento `x.replace().replace()`."""
    pares: list[tuple[str, str]] = []
    atual: ast.expr = call
    while isinstance(atual, ast.Call):
        par = _replace_args(atual)
        if par is None:
            break
        pares.append(par)
        atual = atual.func.value  # type: ignore[union-attr]
    return pares


def violacoes(source: str, rel: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{rel}:{exc.lineno}: não parseia ({exc.msg})"]
    achados = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        pares = _cadeia_de_replaces(node)
        if _STRIP_PONTO in pares and _VIRGULA_PARA_PONTO in pares:
            achados.append(
                f"{rel}:{node.lineno}: parse monetário à mão "
                '(`.replace(".", "").replace(",", ".")`) — infla valor ISO em 100×. '
                "Use `pipeline.domain.services.money_parsing.parse_valor_monetario`."
            )
    return achados


def _arquivos(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(a) for a in argv if a.endswith(".py")]
    return [p for b in _BUCKETS for p in (_ROOT / b).rglob("*.py")]


def main(argv: list[str]) -> int:
    problemas: list[str] = []
    for path in _arquivos(argv):
        if not path.is_file():
            continue
        try:
            rel = path.resolve().relative_to(_ROOT).as_posix()
        except ValueError:
            rel = path.as_posix()
        if rel in _ALLOWLIST:
            continue
        problemas += violacoes(path.read_text(encoding="utf-8", errors="replace"), rel)
    if problemas:
        print("Parse monetário duplicado — o defeito de escala ×100 nasce daqui (r5/M28):\n")
        for p in sorted(problemas):
            print(f"  {p}")
        print(
            f"\n{len(problemas)} violação(ões). Parser canônico: `money_parsing.parse_valor_monetario`."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
