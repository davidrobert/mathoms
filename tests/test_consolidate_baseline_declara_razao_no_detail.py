"""A40.l81 / ADR-411 D2 — o `detail` do E1.5c declara o que o payload carrega.

Sem isto, as razões do `consolidate_baseline` viviam SÓ no artefato, e o sink do
orquestrador — que lê o `detail` — não as via. Medido no run `d0f6260a`: 4
ocorrências no artefato, 0 no `detail`, 0 na tabela.

Mover a chamada do sink não resolveria sozinho: o canal que o sink lê estava
vazio para este produtor.
"""

from __future__ import annotations

from collections import Counter

from pipeline.domain.review_reason_harvest import harvest_review_reasons
from scripts.consolidate_baseline import _validation_block


def _razao(code: str, occ: int = 1) -> dict:
    return {
        "code": code,
        "stage": "consolidate_baseline",
        "artifact_key": "baseline_patrimonial",
        "document_id": None,
        "offending_value": "endereco_canonical=None",
        "expected": "canonical or unique",
        "message": "identity not minted",
        "occurrence_count": occ,
    }


def _payload_do_run_medido() -> dict:
    """2 razões de topo + 2 aninhadas por imóvel — a forma do `d0f6260a`."""
    return {
        "validation": {"review_reasons": [_razao("domain.baseline_divergence") for _ in range(2)]},
        "imoveis_consolidados": [
            {"review_reasons": [_razao("domain.property_identity_uncanonical")]},
            {"review_reasons": [_razao("domain.property_identity_uncanonical")]},
        ],
    }


def _occ(reasons: list[dict]) -> dict[str, int]:
    out: Counter[str] = Counter()
    for r in reasons:
        out[r["code"]] += int(r.get("occurrence_count", 1) or 1)
    return dict(out)


def test_detail_declara_toda_razao_do_payload() -> None:
    payload = _payload_do_run_medido()
    declarado = _occ(_validation_block(payload)["review_reasons"])
    assert declarado == _occ(harvest_review_reasons(payload))
    assert declarado == {
        "domain.baseline_divergence": 2,
        "domain.property_identity_uncanonical": 2,
    }


def test_razao_de_imovel_entra_no_detail() -> None:
    """Mutação que mata: declarar só `payload['validation']['review_reasons']`."""
    payload = {
        "imoveis_consolidados": [
            {"review_reasons": [_razao("domain.property_identity_uncanonical", 2)]}
        ]
    }
    assert _occ(_validation_block(payload)["review_reasons"]) == {
        "domain.property_identity_uncanonical": 2
    }


def test_bloco_nao_declara_valid_e_o_stage_segue_entregando() -> None:
    """WARN-first (ADR-357 §2): `valid` é do orquestrador. Declará-lo aqui faria
    o E1.5c PAUSAR o run inteiro por divergência informativa."""
    assert "valid" not in _validation_block(_payload_do_run_medido())


def test_payload_limpo_declara_lista_vazia() -> None:
    assert _validation_block({"imoveis_consolidados": [{}]}) == {"review_reasons": []}


def test_colheita_nao_contamina_o_payload_persistido() -> None:
    """O payload volta ao `store.write`: carimbar `locator` in-place o poria num
    artefato cujo schema não declara o campo."""
    payload = _payload_do_run_medido()
    _validation_block(payload)
    assert "locator" not in payload["validation"]["review_reasons"][0]
    assert "locator" not in payload["imoveis_consolidados"][0]["review_reasons"][0]
