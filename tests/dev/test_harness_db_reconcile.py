"""parse-certify Passo 3 — cross-check harness↔DB por content_hash (ADR-302)."""

from __future__ import annotations

from dev.harness_db_reconcile import is_stub, reconcile


def _rec(content_hash: str, label: str = "extrato|itau|202601") -> dict:
    return {"content_hash": content_hash, "label": label}


def test_ingested_quando_hash_no_db() -> None:
    r = reconcile([_rec("aaa"), _rec("bbb")], {"aaa", "bbb"}, [])
    assert r.ingested == 2 and r.not_ingested == [] and r.clean


def test_not_ingested_e_p0_quando_hash_ausente() -> None:
    r = reconcile([_rec("aaa", "fatura|c6|202602")], db_hashes=set(), live_artifacts=[])
    assert r.ingested == 0
    assert r.not_ingested == ["fatura|c6|202602"]
    assert not r.clean


def test_dedup_dir_com_mesmo_hash_e_benigno() -> None:
    # 2 arquivos no dir com o mesmo conteúdo → 1 doc no DB (DB ≤ dir)
    r = reconcile([_rec("aaa"), _rec("aaa")], {"aaa"}, [])
    assert r.ingested == 2 and r.deduped == 1 and r.clean


def test_invariante_um_vivo_nao_fallback_por_chave() -> None:
    live = [
        ("reconcile_transactions", "itau_extratoconta_BRL_202601_202604"),
        ("reconcile_transactions", "itau_extratoconta_BRL_202601_202604"),  # parcial ressuscitado
        ("reconcile_transactions", "c6_extratoconta_BRL_202601_202601"),
    ]
    r = reconcile([_rec("aaa")], {"aaa"}, live)
    assert r.invariant_violations == ["reconcile_transactions:itau_extratoconta_BRL_202601_202604"]
    assert not r.clean


def test_db_hash_extra_nao_e_perda() -> None:
    # DB tem hash não presente no dir (doc via web upload) — não é perda
    r = reconcile([_rec("aaa")], {"aaa", "web_only"}, [])
    assert r.not_ingested == [] and r.clean


def test_is_stub_llm_fallback() -> None:
    assert is_stub({"requires_llm_fallback": True})


def test_is_stub_transacoes_vazias() -> None:
    assert is_stub({"transacoes": []})


def test_is_stub_investimento_sem_chave_transacoes_e_vivo() -> None:
    # artefato de posição de investimento não tem `transacoes` → não é stub
    assert not is_stub({"posicoes": [{"x": 1}], "tipo": "cdbresumo"})


def test_is_stub_extrato_vivo() -> None:
    assert not is_stub({"transacoes": [{"valor": 1}]})


def _rec_pref(content_hash: str, prefix: str, label: str = "extrato|c6|202505") -> dict:
    return {"content_hash": content_hash, "stored_prefix": prefix, "label": label}


def test_prefix_fallback_arquivo_com_conteudo_divergente_e_ingerido() -> None:
    # arquivo em disco divergiu (content_hash não bate) mas o prefixo do nome
    # (identidade ADR-084) está no DB → ingerido, NÃO not_ingested (P0 falso)
    full = "29d69a0bb52b" + "0" * 52
    r = reconcile(
        [_rec_pref("hash_do_conteudo_atual_divergente", "29d69a0bb52b")],
        db_hashes={full},
        live_artifacts=[],
        db_prefixes={full[:12]},
    )
    assert r.ingested == 1 and r.not_ingested == [] and r.clean


def test_prefix_ausente_do_db_ainda_e_not_ingested() -> None:
    r = reconcile(
        [_rec_pref("xxx", "deadbeef0000", "extrato|x|202601")],
        db_hashes=set(),
        live_artifacts=[],
        db_prefixes={"0123456789ab"},
    )
    assert r.not_ingested == ["extrato|x|202601"] and not r.clean


def test_sem_db_prefixes_mantem_join_so_por_content_hash() -> None:
    # backward-compat: sem db_prefixes o prefixo não salva; só content_hash conta
    r = reconcile([_rec_pref("diverged", "29d69a0bb52b")], db_hashes=set(), live_artifacts=[])
    assert r.not_ingested == ["extrato|c6|202505"] and not r.clean
