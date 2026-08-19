"""DE-6 — eixo decidido por fato é precondição de mint de identidade ([[ADR-396]]).

`secao` é OPCIONAL no `e15_baseline_extract.schema.json` e 766 artefatos
históricos não a carregam. Sem ela, o eixo cai no último degrau da [[ADR-394]]
D1 — o `categoria_hint` do LLM —, e um item da ficha `dividas_onus` (saldo
devedor POSITIVO, como o prompt 1.3.0 manda transcrever) rotulado `"imovel"`
entra em `imoveis_consolidados`. O mint então grava identidade durável para um
passivo, e o relatório a apresenta como imóvel pendente de rótulo.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.domain.services.endereco_canonicalizer import canonicalize
from scripts.consolidate_baseline import main_with_store

WS = "ws-de6"
_IMOVEL = "APARTAMENTO - Rua Exemplo, 100"
_DIVIDA = "CREDITO IMOBILIARIO - Rua Exemplo, 100"


def _item(descricao: str, valor_brl, *, hint: str = "imovel", secao: str | None = None) -> dict:
    item = {
        "codigo": "11",
        "descricao": descricao,
        "categoria_hint": hint,
        "valor_brl": valor_brl,
        "membro": "david_robert",
        "ano": 2024,
    }
    if secao is not None:
        item["secao"] = secao
    return item


def _run(itens: list[dict]) -> tuple[dict, InMemoryPropertyIdentityResolver]:
    """Roda o E1.5c real (consolidação + mint + dedup) sobre `itens[]` sintéticos."""
    tmp = Path(tempfile.mkdtemp())
    (tmp / "config").mkdir(parents=True, exist_ok=True)
    (tmp / "config" / "pipeline.json").write_text("{}")
    (tmp / "config" / "family_members.json").write_text("{}")
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", {"itens": itens, "resumo": {}})
    resolver = InMemoryPropertyIdentityResolver()
    ctx = WorkspaceContext(
        root=tmp,
        artifact_store=store,
        workspace_id=WS,
        property_identity_resolver=resolver,
    )
    main_with_store(ctx)
    return store.read("E1.5c", "baseline_patrimonial"), resolver


def _by_descricao(imoveis: list[dict], descricao: str) -> dict | None:
    return next((e for e in imoveis if e.get("descricao") == descricao), None)


def test_divida_sem_secao_nao_recebe_property_id() -> None:
    """O item de dívida cuja `secao` não sobreviveu não vira identidade durável."""
    out, resolver = _run(
        [_item(_IMOVEL, 600000.0, secao="bens_direitos"), _item(_DIVIDA, 200000.0)]
    )
    imoveis = out["imoveis_consolidados"]
    divida = _by_descricao(imoveis, _DIVIDA)

    assert divida is not None, "o item de dívida sumiu do payload (absorvido pelo dedup)"
    assert divida["property_id"] is None
    assert divida["needs_review"] is True
    assert "domain.property_identity_eixo_por_hint" in [r["code"] for r in divida["review_reasons"]]
    assert [r.endereco_canonical for r in resolver.all()] == ["exemplo 100"]


def test_divida_sem_secao_nao_rouba_a_identidade_do_imovel_financiado() -> None:
    """A descrição do financiamento canonicaliza IGUAL à do imóvel — e não pode casar."""
    assert canonicalize(_DIVIDA) == canonicalize(_IMOVEL) == "exemplo 100"
    out, _ = _run([_item(_IMOVEL, 600000.0, secao="bens_direitos"), _item(_DIVIDA, 200000.0)])
    imovel = _by_descricao(out["imoveis_consolidados"], _IMOVEL)
    divida = _by_descricao(out["imoveis_consolidados"], _DIVIDA)

    assert imovel is not None and imovel["property_id"] is not None
    assert divida is not None and divida["property_id"] != imovel["property_id"]
    assert divida["endereco_canonical"] is None, "canonical do imóvel vazaria para o passivo"


def test_imovel_com_secao_de_bens_segue_mintando() -> None:
    """Trava de não-regressão: o eixo atestado por `secao` mantém o mint intacto."""
    out, resolver = _run([_item(_IMOVEL, 600000.0, secao="bens_direitos")])
    entry = out["imoveis_consolidados"][0]

    assert entry["property_id"] is not None
    assert entry.get("needs_review") is not True
    assert len(resolver.all()) == 1


def test_secao_de_dividas_nunca_chega_ao_mint() -> None:
    """Trava do roteamento [[ADR-394]] D1: com `secao`, o item nem entra em imóveis."""
    out, resolver = _run([_item(_DIVIDA, 200000.0, secao="dividas_onus")])

    assert out["imoveis_consolidados"] == []
    assert len(out["dividas"]) == 1
    assert resolver.all() == []


# 766 artefatos históricos não carregam `secao` e o modo incremental os reagrega.
# Recusar o mint por ausência do fato tiraria `property_id` de todo imóvel antigo —
# e com ele o dedup, os overrides e a seção de imóveis inteira.
def test_declaracao_legada_sem_secao_segue_mintando() -> None:
    """[[ADR-396]] D2 — onde a fonte nunca ofereceu o fato, exigi-lo apagaria o corpus."""
    out, resolver = _run(
        [_item(_IMOVEL, 600000.0), _item("APARTAMENTO - Rua Exemplo, 200", 300000.0)]
    )
    pids = [e["property_id"] for e in out["imoveis_consolidados"]]

    assert all(p is not None for p in pids)
    assert len(resolver.all()) == 2
