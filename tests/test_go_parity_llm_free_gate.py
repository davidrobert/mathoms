"""A40.l24 — a asserção "0 LLM" do gate F2 tem que poder ficar VERMELHA.

Prova de mutação, não inspeção: sem um teste que force a chamada de visão da
Caixa, a asserção volta a ser vacuamente verde no próximo refactor. Foi
exatamente o que aconteceu duas vezes — contar `stage LIKE '%llm%'` não via a
chamada, e ler `requires_llm_fallback` (#1151) viu a polaridade INVERTIDA.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

from dev.go_parity_errors import GateError
from dev.go_parity_llm_free import (
    LLM_FREE_MARKER,
    assert_llm_free,
    assert_scrub_applied,
    escalated_docs,
)
from dev.go_parity_run import PYTHON_ARM
from tests.fakes.anthropic_sdk import RecordingAnthropicSDK

_REPO = Path(__file__).resolve().parents[1]
_RUN = "11111111-1111-1111-1111-111111111111"


def _caixa_result() -> dict:
    """O MESMO template que `parse_caixa` monta — fixture divergente daria falso verde."""
    from scripts.e2.common import BANCO_CAIXA, make_result_template

    return make_result_template(BANCO_CAIXA, "extratoconta", "BRL")


def _scanned_pdf(tmp_path: Path) -> Path:
    pdf = tmp_path / "caixa_extratoconta_202606-0_original.pdf"
    pdf.write_bytes(b"%PDF-1.4 sem camada de texto")
    return pdf


def _sdk_com_extrato(monkeypatch) -> RecordingAnthropicSDK:
    return RecordingAnthropicSDK(
        payload={
            "numero_conta": "0001",
            "periodo_inicio": "2026-06-01",
            "periodo_fim": "2026-06-30",
            "transacoes": [{"data": "2026-06-10", "descricao": "CREDITO", "valor": 10.0}],
        }
    ).install(monkeypatch)


def _db(tmp_path: Path) -> sqlite3.Connection:
    """SQLite mínimo com as duas tabelas que o gate consulta por SQL cru."""
    con = sqlite3.connect(tmp_path / "gate.db")
    con.execute("CREATE TABLE llm_call_log (pipeline_run_id TEXT, stage TEXT)")
    con.execute("CREATE TABLE pipeline_artifacts (pipeline_run_id TEXT, stage TEXT, key TEXT)")
    con.commit()
    return con


# ───────────────────── a mutação: forçar a visão da Caixa ─────────────────────


def test_visao_da_caixa_chama_o_sdk_e_nao_deixa_rastro_no_flag(tmp_path, monkeypatch):
    """Positivo conhecido: chamada PAGA feita e `requires_llm_fallback` ausente."""
    # É o caso que #1151 não vê — sucesso não seta o flag, então gatear "0 LLM"
    # nele aprova justamente o run que gastou API.
    from scripts.e2.banks import caixa

    sdk = _sdk_com_extrato(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-forced-for-mutation-proof")
    result = _caixa_result()

    assert caixa._extract_via_llm(_scanned_pdf(tmp_path), result) is True
    assert len(sdk.calls) == 1, "a mutação não chegou ao SDK — o teste não prova nada"
    assert (
        "requires_llm_fallback" not in result
    ), "sucesso da visão NÃO seta o flag — por isso ele não pode gatear 0-LLM"
    assert result["transacoes"], "extração via visão deveria ter populado o extrato"


def test_sem_credencial_a_visao_da_caixa_nao_chama_o_sdk(tmp_path, monkeypatch):
    """A garantia do Tier-1 é impedir a chamada (credencial ausente), não detectá-la."""
    from scripts.e2.banks import caixa

    sdk = RecordingAnthropicSDK(payload={}).install(monkeypatch)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert caixa._extract_via_llm(_scanned_pdf(tmp_path), _caixa_result()) is False
    assert sdk.calls == [], "sem credencial no env não pode sair chamada"


# ───────────────────── o gate: fica vermelho / não fica ─────────────────────


def test_tier1_fica_vermelho_com_chamada_registrada(tmp_path):
    con = _db(tmp_path)
    con.execute("INSERT INTO llm_call_log VALUES (?, ?)", (_RUN, "extract_statements"))
    con.commit()

    with pytest.raises(GateError, match="não é 0-LLM"):
        assert_llm_free(con, _RUN, PYTHON_ARM, "tier1")


def test_tier1_fica_vermelho_com_artefato_de_stage_llm(tmp_path):
    con = _db(tmp_path)
    con.execute(
        "INSERT INTO pipeline_artifacts VALUES (?, ?, ?)", (_RUN, "extract_with_llm", "doc")
    )
    con.commit()

    with pytest.raises(GateError, match="não é 0-LLM"):
        assert_llm_free(con, _RUN, PYTHON_ARM, "tier1")


def test_tier1_nao_reprova_run_que_so_escalou_documento(tmp_path):
    """Desinverte #1151: stub de escalação é corpus encolhido, não gasto de LLM."""
    # No Tier-1 o stub é o ESPERADO (extract_with_llm está fora de
    # DETERMINISTIC_ORDER). Gatear nele reprovava o braço sem credencial — o
    # único dos dois que de fato não gastou nada.
    con = _db(tmp_path)
    con.execute(
        "INSERT INTO pipeline_artifacts VALUES (?, ?, ?)",
        (_RUN, "extract_statements", "caixa_extratoconta_BRL_202606_202606"),
    )
    con.commit()

    assert assert_llm_free(con, _RUN, PYTHON_ARM, "tier1") == 0


def test_tier2_reporta_sem_reprovar(tmp_path):
    con = _db(tmp_path)
    con.execute("INSERT INTO llm_call_log VALUES (?, ?)", (_RUN, "E6-parecer"))
    con.commit()

    assert assert_llm_free(con, _RUN, PYTHON_ARM, "tier2") == 1


def test_escalacao_e_reportada_como_corpus_encolhido(monkeypatch):
    """O flag continua sendo lido — como sinal de corpus, que é o que ele mede."""
    import dev.go_parity_gate as gate

    monkeypatch.setattr(
        gate,
        "collect_run_artifacts",
        lambda _run: {
            ("extract_statements", "caixa_extratoconta_BRL_202606_202606"): {
                "requires_llm_fallback": True
            },
            ("extract_statements", "itau_extratoconta_BRL_202606_202606"): {"transacoes": []},
        },
    )

    assert escalated_docs(_RUN) == ["extract_statements/caixa_extratoconta_BRL_202606_202606"]


# ───────────────────── o scrub tem que ter rodado de fato ─────────────────────


def test_scrub_nao_verificado_falha_alto():
    with pytest.raises(GateError, match="NÃO foi apagada"):
        assert_scrub_applied(PYTHON_ARM, "▶  subindo worker…\n  ✅ pronto\n")


def test_scrub_verificado_passa():
    assert_scrub_applied(PYTHON_ARM, f"   · {LLM_FREE_MARKER} (worker Celery)\n")


def test_marcador_do_harness_casa_com_o_makefile():
    """Marcador é contrato entre Makefile e harness — drift silencioso reprova o gate inteiro."""
    makefile = (_REPO / "Makefile").read_text(encoding="utf-8")
    declared = re.search(r"^LLM_FREE_MARKER\s*=\s*(.+)$", makefile, re.MULTILINE)
    assert declared, "LLM_FREE_MARKER desapareceu do Makefile"
    assert declared.group(1).strip() == LLM_FREE_MARKER


def test_makefile_apaga_a_credencial_nos_dois_bracos():
    """O scrub tem que existir no worker Celery E no shell Go — assimetria é o bug."""
    makefile = (_REPO / "Makefile").read_text(encoding="utf-8")
    assert "LLM_FREE_SCRUB = $(if $(LLM_FREE),ANTHROPIC_API_KEY= ,)" in makefile
    assert makefile.count("$(LLM_FREE_SCRUB) ") >= 2, "worker nativo e worker-go precisam do scrub"
    assert '[ -z "$(LLM_FREE)" ] || { AKEY=""' in makefile, "shell Go continua injetando a key"
