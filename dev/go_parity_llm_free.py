"""Contrato de "0 LLM" do Tier-1 (A40.l24 · [[ADR-355]]) — medir e impedir.

Extraído de ``go_parity_run.py`` quando ele passou de 500 linhas (P2).

O Tier-1 garante 0-LLM **impedindo** a chamada (credencial apagada dos dois
braços, ``LLM_FREE=1`` no Makefile) em vez de detectá-la depois. Detecção
pós-hoc é estruturalmente incompleta hoje: ``scripts/e2/banks/caixa.py`` e
``scripts/route_documents.py`` montam o SDK ``anthropic`` direto de
``os.environ`` e nunca aparecem em ``llm_call_log``. Fechar essa rota é a A41.l4.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from dev.go_parity_errors import GateError

if TYPE_CHECKING:
    from dev.go_parity_run import Arm

# Espelha `LLM_FREE_MARKER` no Makefile. O gate verifica que o scrub REALMENTE
# rodou em vez de confiar que passar `LLM_FREE=1` basta: se alguém quebrar o
# scrub, o gate precisa falhar alto, não voltar a comparar braços com credencial
# assimétrica em silêncio.
LLM_FREE_MARKER = "LLM-FREE: ANTHROPIC_API_KEY scrubbed"


def llm_artifact_count(con: sqlite3.Connection, run_id: str) -> int:
    """Sinal secundário de 0-LLM — não é o critério."""
    # Cego para chamada dentro de stage não-`is_llm`: a visão da Caixa grava
    # artefato NORMAL de extract_statements, e o stub de escalação vai para o
    # stage determinístico (ADR-342), não para extract_with_llm.
    row = con.execute(
        "SELECT COUNT(*) FROM pipeline_artifacts WHERE pipeline_run_id=? AND stage LIKE '%llm%'",
        (run_id,),
    ).fetchone()
    return int(row[0])


def llm_call_log_count(con: sqlite3.Connection, run_id: str) -> int:
    """Chamadas registradas no choke-point instrumentado, por run."""
    # Necessário, não suficiente: `record_call` só grava com `ctx.llm_call_hooks`
    # injetado, e quem monta o SDK direto nunca aparece aqui. Daí o Tier-1
    # IMPEDIR a chamada em vez de detectá-la — ver docstring do módulo.
    row = con.execute(
        "SELECT COUNT(*) FROM llm_call_log WHERE pipeline_run_id=?", (run_id,)
    ).fetchone()
    return int(row[0])


def escalated_docs(run_id: str) -> list[str]:
    """Docs que escalaram para LLM — mede corpus encolhido, NÃO gasto de LLM."""
    # Polaridade invertida vs. a intuição, e foi o bug de #1151: a visão da Caixa
    # não seta o flag quando FUNCIONA (chamada paga, gate verde) e seta quando não
    # há credencial (zero chamada, gate vermelho). No Tier-1 o stub é o esperado —
    # extract_with_llm está fora de DETERMINISTIC_ORDER —, então só reporta
    # (ADR-355 §Consequências). Divergência de QUAIS docs escalaram entre braços é
    # do diff de artefato do go_parity_gate.
    from dev.go_parity_gate import collect_run_artifacts

    flagged = []
    for (stage, key), payload in collect_run_artifacts(run_id).items():
        if isinstance(payload, dict) and payload.get("requires_llm_fallback"):
            flagged.append(f"{stage}/{key}")
    return sorted(flagged)


def assert_llm_free(con: sqlite3.Connection, run_id: str, arm: "Arm", tier: str) -> int:
    """Tier-1: qualquer chamada LLM registrada invalida o run. Tier-2: só reporta."""
    calls = llm_call_log_count(con, run_id)
    escalated = llm_artifact_count(con, run_id)
    if tier == "tier1" and (calls or escalated):
        raise GateError(
            f"run {run_id} do braço {arm.name} não é 0-LLM: {calls} chamada(s) em "
            f"llm_call_log + {escalated} artefato(s) de stage LLM.\n"
            f"   O Tier-1 roda os dois braços com `LLM_FREE=1` (credencial apagada do "
            f"worker e do shell Go); chamada registrada aqui significa que o scrub não "
            f"pegou — confira o marcador `{LLM_FREE_MARKER}` na saída do make."
        )
    return calls + escalated


def assert_scrub_applied(arm: "Arm", make_output: str) -> None:
    """Sem marcador o scrub não rodou — e o Tier-1 perde a garantia de 0-LLM."""
    if LLM_FREE_MARKER in make_output:
        return
    raise GateError(
        f"braço {arm.name}: `make {arm.make_target} LLM_FREE=1` não emitiu "
        f"`{LLM_FREE_MARKER}` — a credencial LLM NÃO foi apagada do env.\n"
        f"   Ver `LLM_FREE_SCRUB` no Makefile."
    )
