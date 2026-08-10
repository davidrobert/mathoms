#!/usr/bin/env python3
"""Paridade Py↔TS do formatador de probabilidade do MC (A40.l25 · ADR-237)."""
# Duas superfícies publicam o MESMO campo (`prob_if_ate_prazo_declarado`): o
# parágrafo do narrador (Python) e a legenda do cone em S7 (TS). Os dois
# declaravam paridade em docstring e nunca foram comparados — medido no domínio
# real do estimador (`k/50000`), discordavam em 45 dos 50 001 desfechos.
#
# Hook de pre-commit, não teste: um teste em `tests/` não roda em PR que só toca
# `frontend/`, e um Vitest não roda em PR que só toca `pipeline/`. O par vive
# nos dois lados, então o gate tem de rodar nos dois — o que o `pre-commit
# --all-files` do job Lint garante (precedente: decisão do dono na A40.l5).

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TS_SOURCE = REPO_ROOT / "frontend" / "src" / "components" / "report" / "utils" / "probabilidade.ts"
PY_SOURCE = REPO_ROOT / "pipeline" / "domain" / "services" / "narrativas" / "probabilidade_fmt.py"

# `n` do Monte Carlo (ADR-360): a probabilidade é sempre `k/n`, então este é o
# domínio EXATO do estimador — não uma grade sintética que erra os boundaries.
_N_SIMULACOES = 50_000


def _extrai_corpo_ts() -> str:
    """Corpo de `formatProbability` lido da fonte — nunca reescrito aqui."""
    # Reimplementar a função neste arquivo criaria uma 3ª cópia, e o gate
    # passaria a comparar duas cópias minhas em vez da que o cliente recebe.
    texto = TS_SOURCE.read_text(encoding="utf-8")
    marcador = "export function formatProbability(prob: number): string {"
    inicio = texto.find(marcador)
    if inicio == -1:
        raise SystemExit(
            f"formatProbability não encontrado em {TS_SOURCE.relative_to(REPO_ROOT)} "
            "— o parser precisa de ajuste (não silencie: o gate ficaria vácuo)."
        )
    corpo = texto[inicio + len(marcador) :]
    fim = corpo.find("\n}")
    if fim == -1:
        raise SystemExit("fim de formatProbability não encontrado")
    return corpo[:fim]


def _roda_lado_ts(corpo: str) -> list[str]:
    """Executa a função TS real no node sobre todo o domínio."""
    script = (
        f"const f = (prob) => {{{corpo}\n}};\n"
        f"const out = [];\n"
        f"for (let k = 0; k <= {_N_SIMULACOES}; k++) out.push(f(k / {_N_SIMULACOES}));\n"
        f"process.stdout.write(JSON.stringify(out));"
    )
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"node falhou ao avaliar formatProbability:\n{proc.stderr}")
    return json.loads(proc.stdout)


# Carrega o módulo-folha por CAMINHO, sem executar
# `pipeline/domain/services/__init__.py` — que tem 34 imports e puxa
# `pipeline.llm` → `pydantic`, ausente do ambiente do job de Lint. Importar o
# narrador inteiro fazia este hook explodir com ModuleNotFoundError lá, e a
# saída seria SKIP no Lint — que reintroduziria exatamente o buraco de cobertura
# que este gate existe para fechar.
def _roda_lado_py() -> list[str]:
    spec = importlib.util.spec_from_file_location("_probabilidade_fmt", PY_SOURCE)
    if spec is None or spec.loader is None:
        raise SystemExit(f"não consegui carregar {PY_SOURCE.relative_to(REPO_ROOT)}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return [modulo.fmt_probabilidade(k / _N_SIMULACOES) for k in range(_N_SIMULACOES + 1)]


def main() -> int:
    ts = _roda_lado_ts(_extrai_corpo_ts())
    py = _roda_lado_py()
    divergencias = [(k, p, t) for k, (p, t) in enumerate(zip(py, ts)) if p != t]
    if not divergencias:
        print(f"✓ paridade Py↔TS em {len(py)} desfechos de probabilidade.")
        return 0

    print(f"✗ {len(divergencias)} divergências entre narrador (Py) e card (TS):")
    for k, p, t in divergencias[:10]:
        print(f"    k={k:<6} prob={k / _N_SIMULACOES:.5f}  narrador={p:<6} card={t}")
    if len(divergencias) > 10:
        print(f"    … e mais {len(divergencias) - 10}")
    print(
        "\nAs duas superfícies publicam o MESMO campo no MESMO relatório. "
        "Use a mesma expressão nos dois lados — `floor(x + 0.5)` é idêntico "
        "em IEEE-754; `round()` do Python e `.toFixed(0)` do JS não são."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
