#!/usr/bin/env python3
"""A40.l56 · ADR-389 D3 — invariantes das tabelas progressivas que a migration grava.

Lê `TABELAS_POR_ANO` do módulo da migration por `spec_from_file_location` e aplica
os invariantes de `tabela_progressiva_coerencia`. Os bytes verificados são os que
vão para o banco — cópia à mão em teste mediria a cópia.

Por que gate de pre-commit e não teste: `dev/check_test_health.py` marca como
`migration` qualquer teste cujo source contenha o literal `alembic.versions`, e o
CI desliga esses com `-m "not migration"`. Escrito do jeito óbvio, o teste
nasceria desligado.

Exit 0 quando todas as tabelas passam; 1 listando a fronteira ofensora.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

_MIGRATION = (
    _REPO / "backend" / "alembic" / "versions" / "adr389tabelas_ir_brackets_anual_e_mensal.py"
)
_INVARIANTES = _REPO / "pipeline" / "domain" / "services" / "tabela_progressiva_coerencia.py"


# Carga por PATH, não por pacote. `import pipeline.domain.services.X` dispara o
# `__init__` do pacote, que puxa `e5_analyzer_adapter` → litellm → pydantic, e
# explode com ModuleNotFoundError na env MÍNIMA do job de lint — onde este gate
# roda. `pipeline.domain.types` é leve (stdlib só) e pode vir por import normal.
def _modulo(nome: str, caminho: Path):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"não consegui carregar {caminho}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


from pipeline.domain.types.config import IRPFBracket  # noqa: E402

_inv = _modulo("_adr389_invariantes", _INVARIANTES)
Violacao = _inv.Violacao
divergencia_x12 = _inv.divergencia_x12
verificar_congruencia = _inv.verificar_congruencia
verificar_continuidade = _inv.verificar_continuidade
verificar_monotonicidade = _inv.verificar_monotonicidade
verificar_primeira_fronteira = _inv.verificar_primeira_fronteira


def _carrega_tabelas() -> dict:
    return _modulo("_adr389_migration", _MIGRATION).TABELAS_POR_ANO


def _brackets(tabela: dict) -> tuple[IRPFBracket, ...]:
    return tuple(
        IRPFBracket(
            upper_brl_cents=f["upper_brl_cents"],
            aliquota_pct=Decimal(f["aliquota_pct"]),
            deducao_brl_cents=f["deducao_brl_cents"],
        )
        for f in tabela["faixas"]
    )


def _verifica_uma(rotulo: str, faixas) -> list[str]:
    achados: list[Violacao] = []
    achados.extend(verificar_continuidade(faixas))
    achados.extend(verificar_primeira_fronteira(faixas))
    achados.extend(verificar_monotonicidade(faixas))
    return [f"{rotulo}: {v.format()}" for v in achados]


def _verifica_divergencia(ano: int, mensal, anual, dados: dict) -> list[str]:
    indices = divergencia_x12(mensal, anual)
    if not indices:
        return []
    # Divergência sem motivo declarado é o que falha — a divergência em si é
    # esperada em ano de transição (ADR-389 D3c).
    if dados["anual"].get("motivo_divergencia_x12"):
        return []
    return [
        f"{ano}: faixas {list(indices)} divergem de 12× a mensal sem "
        f"`motivo_divergencia_x12` declarado"
    ]


def _anos_diferem(tabelas: dict) -> list[str]:
    # Só as ANUAIS têm de diferir. As mensais de 2025 e 2026 são byte-idênticas
    # e isso é correto — a Lei 15.270/2025 não alterou faixas nem parcelas.
    anuais = {ano: str(d["anual"]["faixas"]) for ano, d in tabelas.items()}
    if len(set(anuais.values())) == len(anuais):
        return []
    return ["tabelas ANUAIS repetidas entre anos — é o defeito que a ADR-389 conserta"]


def main() -> int:
    tabelas = _carrega_tabelas()
    erros: list[str] = []
    for ano, dados in sorted(tabelas.items()):
        mensal, anual = _brackets(dados["mensal"]), _brackets(dados["anual"])
        erros.extend(_verifica_uma(f"{ano} mensal", mensal))
        erros.extend(_verifica_uma(f"{ano} anual", anual))
        erros.extend(f"{ano}: {v.format()}" for v in verificar_congruencia(mensal, anual))
        erros.extend(_verifica_divergencia(ano, mensal, anual, dados))
    erros.extend(_anos_diferem(tabelas))
    if erros:
        print("Tabelas progressivas violam os invariantes da ADR-389 D3:\n")
        for e in erros:
            print(f"  ✗ {e}")
        return 1
    print(f"✓ {len(tabelas)} anos × 2 tabelas passam os invariantes da ADR-389 D3.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
