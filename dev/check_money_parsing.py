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
# Detecção por AST, coletando os pares por CORPO DE FUNÇÃO (não por cadeia) e resolvendo
# separador em constante de módulo. Não casa strip de pontuação em CPF/CNPJ nem
# formatação de saída (`.replace(".", ",")`, que é o inverso).
#
# LIMITE CONHECIDO, medido com 4 sondas: pega 3 de 4 reintroduções plausíveis
# (encadeada, dois-statements, constante). NÃO pega `float(v)` cru em campo
# monetário — é classe distinta, sem idioma para casar, e foi 1 dos 6 defeitos que
# o PR #1417 corrigiu. Sondas versionadas em tests/unit/pipeline/test_check_money_parsing_gate.py.

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


def _literal(no: ast.expr, consts: dict[str, str]) -> str | None:
    """Literal str, ou nome que resolve para constante str de módulo."""
    if isinstance(no, ast.Constant) and isinstance(no.value, str):
        return no.value
    if isinstance(no, ast.Name):
        return consts.get(no.id)
    return None


def _replace_args(call: ast.Call, consts: dict[str, str]) -> tuple[str, str] | None:
    """`x.replace(a, b)` com a/b resolvíveis para str → `(a, b)`; senão ``None``."""
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "replace":
        return None
    if len(call.args) != 2:
        return None
    primeiro = _literal(call.args[0], consts)
    segundo = _literal(call.args[1], consts)
    if primeiro is None or segundo is None:
        return None
    return primeiro, segundo


def _atribuicao_str(node: ast.stmt) -> tuple[str, str] | None:
    """`NOME = "literal"` → `(NOME, literal)`; senão ``None``."""
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return None
    alvo, valor = node.targets[0], node.value
    if not isinstance(alvo, ast.Name) or not isinstance(valor, ast.Constant):
        return None
    return (alvo.id, valor.value) if isinstance(valor.value, str) else None


def _constantes_de_modulo(tree: ast.Module) -> dict[str, str]:
    """`NOME = "literal"` no topo do módulo — fecha a fuga por separador em constante."""
    pares = (_atribuicao_str(node) for node in tree.body)
    return dict(p for p in pares if p is not None)


# Coletar por CORPO DE FUNÇÃO, não por cadeia: `s = v.replace(".", "")` seguido de
# `s = s.replace(",", ".")` em statements separados é a mesma reintrodução e a versão
# por-cadeia passava batido (medido com 4 sondas na review do PR #1417).
def _pares_no_escopo(node: ast.AST, consts: dict[str, str]) -> list[tuple[int, tuple[str, str]]]:
    """Todos os `(linha, (de, para))` de `.replace()` dentro deste escopo."""
    chamadas = (c for c in ast.walk(node) if isinstance(c, ast.Call))
    achados = ((c.lineno, _replace_args(c, consts)) for c in chamadas)
    return [(linha, par) for linha, par in achados if par is not None]


def _escopos(tree: ast.Module):
    """Cada função é um escopo; o módulo entra sem os corpos de função (evita dupla)."""
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    yield from funcs
    dentro = {id(f) for f in funcs}
    modulo = ast.Module(body=[s for s in tree.body if id(s) not in dentro], type_ignores=[])
    yield modulo


def violacoes(source: str, rel: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{rel}:{exc.lineno}: não parseia ({exc.msg})"]
    consts = _constantes_de_modulo(tree)
    achados = []
    for escopo in _escopos(tree):
        pares = _pares_no_escopo(escopo, consts)
        formas = {p for _, p in pares}
        if _STRIP_PONTO in formas and _VIRGULA_PARA_PONTO in formas:
            linha = min(ln for ln, p in pares if p in (_STRIP_PONTO, _VIRGULA_PARA_PONTO))
            nome = getattr(escopo, "name", "<módulo>")
            achados.append(
                f"{rel}:{linha}: parse monetário à mão em `{nome}` "
                '(`.replace(".", "")` + `.replace(",", ".")`) — infla valor ISO em 100×. '
                "Use `money_parsing.parse_valor_monetario` (dinheiro) ou "
                "`parse_taxa_ou_cotacao` (taxa/cotação/percentual)."
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
