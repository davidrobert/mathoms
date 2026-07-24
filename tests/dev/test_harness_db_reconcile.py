"""parse-certify Passo 3 — cross-check harness↔DB por content_hash (ADR-302)."""

from __future__ import annotations

from dev.harness_db_reconcile import reconcile


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
