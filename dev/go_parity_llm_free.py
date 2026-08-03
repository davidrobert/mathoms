"""Contrato de credencial LLM dos dois braços do gate (A40.l24 · [[ADR-355]]).

Extraído de ``go_parity_run.py`` quando ele passou de 500 linhas (P2).

O que os dois tiers exigem é a **mesma** coisa por caminhos opostos: os dois
braços com o mesmo estado de credencial. O Tier-1 garante 0-LLM **impedindo** a
chamada (credencial apagada dos dois, ``LLM_FREE=1`` no Makefile) em vez de
detectá-la depois; o Tier-2 é run full e precisa da credencial **nos dois**.
Assimetria em qualquer direção faz o mesmo documento parsear diferente e a
divergência vira falso bug de executor.

Detecção pós-hoc é estruturalmente incompleta hoje: ``scripts/e2/banks/caixa.py``
e ``scripts/route_documents.py`` montam o SDK ``anthropic`` direto de
``os.environ`` e nunca aparecem em ``llm_call_log``. Fechar essa rota é a A41.l4.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from dev.go_parity_errors import GateError

if TYPE_CHECKING:
    from dev.go_parity_run import Arm

_REPO = Path(__file__).resolve().parents[1]

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


def _shell_declares_credential() -> bool:
    """Env do processo do harness — é o que `make dev-worker-up` vai herdar."""
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _dotenv_declares_credential(env_file: Path) -> bool:
    """Só presença, nunca o valor: o `.env` alimenta o shell Go, não o worker."""
    if not env_file.exists():
        return False
    for line in env_file.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return bool(line.partition("=")[2].strip().strip("\"'"))
    return False


def assert_credential_symmetry(tier: str, *, env_file: Path | None = None) -> None:
    """Tier-2 exige a credencial nos DOIS braços — `.env` sozinho alimenta só o Go."""
    # Espelho do scrub do Tier-1: lá a simetria vem de apagar dos dois; aqui, de ter
    # nos dois. `_go-on-native` lê ANTHROPIC_API_KEY do `.env` e injeta no shell Go,
    # que a repassa a cada subprocess (`os.Environ()`); `dev-worker-up` só herda o env
    # do shell. `.env` com key + shell sem = Go com credencial e Python sem, que é a
    # divergência de 2026-08-03 (mesmo artifact_key, 2986 vs 1002 bytes). Falha ANTES
    # de gastar run: o Tier-2 custa LLM, e descobrir depois é pagar duas vezes.
    if tier != "tier2" or _shell_declares_credential():
        return
    raise GateError(_credential_gap_message(env_file or _REPO / ".env"))


def _credential_gap_message(env_file: Path) -> str:
    """Diagnóstico distinto: key só no `.env` (assimétrica) vs. ausente em todo lugar."""
    if _dotenv_declares_credential(env_file):
        return (
            "Tier-2 com credencial ASSIMÉTRICA: `ANTHROPIC_API_KEY` está no `.env` "
            "(que o `_go-on-native` injeta no shell Go) mas NÃO no env deste shell "
            "(que é o que o `dev-worker-up` herda).\n"
            "   O braço Go faria chamada de LLM que o braço Python não faz, e o diff "
            "apareceria como bug de executor.\n"
            "   Exporte a chave no shell antes do gate: `export ANTHROPIC_API_KEY=…`"
        )
    return (
        "Tier-2 sem `ANTHROPIC_API_KEY` no env: o run full não exercita LLM algum, "
        "então o tier não mede o que promete (envelope WS + subtrees LLM).\n"
        "   Exporte a chave no shell, ou rode `--tier tier1`."
    )


def assert_scrub_applied(arm: "Arm", make_output: str) -> None:
    """Sem marcador o scrub não rodou — e o Tier-1 perde a garantia de 0-LLM."""
    if LLM_FREE_MARKER in make_output:
        return
    raise GateError(
        f"braço {arm.name}: `make {arm.make_target} LLM_FREE=1` não emitiu "
        f"`{LLM_FREE_MARKER}` — a credencial LLM NÃO foi apagada do env.\n"
        f"   Ver `LLM_FREE_SCRUB` no Makefile."
    )
