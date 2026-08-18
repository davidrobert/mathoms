"""Prova por mutação do seam ativo × passivo ([[A40.l66]] · [[ADR-394]]).

Critério de aceite da lane. Duas correções que o §Ataque II mediu e que estão
embutidas aqui:

- a comparação é sobre **projeção canônica** — `property_id` é `uuid4()` por run,
  então dois runs do MESMO payload nunca são byte-idênticos e a versão ingênua do
  critério reprova a hipótese nula;
- o flip de item **negativo** é satisfeito só pelo degrau do sinal e não prova
  nada acima dele. Os casos que discriminam são o **positivo com `secao`** (que o
  IRPF declara assim) e o **sem `secao`**.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext

_BALDES = ("imoveis_consolidados", "veiculos_consolidados", "investimentos_consolidados")
#: Identidade mintada por run — fora da projeção, senão a comparação é sempre falsa.
_VOLATEIS = {"property_id", "divida_id"}

_IMOVEL = {
    "codigo": "11",
    "descricao": "Rua Exemplo, 100",
    "categoria_hint": "imovel",
    "valor_brl": 600000.0,
    "membro": "titular",
    "ano": 2024,
}
_DIVIDA_NEGATIVA = {
    "codigo": "11",
    "descricao": "FINANCIAMENTO IMOVEL",
    "categoria_hint": "imovel",
    "valor_brl": -200000.0,
    "membro": "titular",
    "ano": 2024,
}
_RESUMO = {
    "total_ativos": 600000.0,
    "total_passivos": 200000.0,
    "patrimonio_liquido": 400000.0,
    "ano_referencia": 2024,
}


def _payload(*itens: dict) -> dict:
    return copy.deepcopy({"itens": list(itens), "resumo": _RESUMO})


def _run(tmp_path: Path, payload: dict) -> dict:
    from scripts.consolidate_baseline import main_with_store

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "pipeline.json").write_text("{}")
    (tmp_path / "config" / "family_members.json").write_text("{}")
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", payload)
    ctx = WorkspaceContext(
        root=tmp_path,
        artifact_store=store,
        workspace_id="test-ws-mutacao",
        property_identity_resolver=InMemoryPropertyIdentityResolver(),
    )
    main_with_store(ctx)
    return store.read("E1.5c", "baseline_patrimonial")


def _baldes_canonicos(out: dict) -> str:
    limpo = {
        balde: [
            {k: v for k, v in entrada.items() if k not in _VOLATEIS}
            for entrada in (out.get(balde) or [])
        ]
        for balde in _BALDES
    }
    return json.dumps(limpo, sort_keys=True, ensure_ascii=False)


def test_hipotese_nula_dois_runs_do_mesmo_payload_sao_identicos(tmp_path: Path) -> None:
    """Sem isto, "byte-idênticos" mede o uuid4 do `property_id`, não o seam."""
    a = _baldes_canonicos(_run(tmp_path / "a", _payload(_IMOVEL, _DIVIDA_NEGATIVA)))
    b = _baldes_canonicos(_run(tmp_path / "b", _payload(_IMOVEL, _DIVIDA_NEGATIVA)))
    assert a == b


@pytest.mark.parametrize("hint", ["investimento", "veiculo", "poupanca", "outros", "previdencia"])
def test_flipar_o_hint_do_item_negativo_nao_move_balde(tmp_path: Path, hint: str) -> None:
    """O rótulo do LLM deixou de decidir: flipá-lo não muda nada."""
    base = _baldes_canonicos(_run(tmp_path / "base", _payload(_IMOVEL, _DIVIDA_NEGATIVA)))
    mutado = dict(_DIVIDA_NEGATIVA, categoria_hint=hint)
    assert _baldes_canonicos(_run(tmp_path / hint, _payload(_IMOVEL, mutado))) == base


def test_divida_positiva_com_secao_nao_vira_ativo(tmp_path: Path) -> None:
    """O caso que o sinal NÃO pega — e é como o IRPF declara saldo devedor."""
    divida = dict(_DIVIDA_NEGATIVA, valor_brl=200000.0, secao="dividas_onus")
    out = _run(tmp_path, _payload(_IMOVEL, divida))
    assert [d["descricao"] for d in out["dividas"]] == ["FINANCIAMENTO IMOVEL"]
    assert out["dividas"][0]["tipo"] == "financiamento_imobiliario", "catálogo (secao, codigo)"
    assert out["dividas"][0]["fonte"] == "irpf"
    assert not [e for b in _BALDES for e in (out.get(b) or []) if "FINANCIAMENTO" in e["descricao"]]


def test_flipar_o_hint_da_divida_positiva_tambem_nao_move_balde(tmp_path: Path) -> None:
    """Com `secao`, o hint é inerte nos dois sinais — não só no negativo."""
    divida = dict(_DIVIDA_NEGATIVA, valor_brl=200000.0, secao="dividas_onus")
    base = _baldes_canonicos(_run(tmp_path / "base", _payload(_IMOVEL, divida)))
    mutado = dict(divida, categoria_hint="imovel")
    assert _baldes_canonicos(_run(tmp_path / "mut", _payload(_IMOVEL, mutado))) == base


def test_sem_secao_o_sinal_decide_e_a_decisao_fica_declarada(tmp_path: Path) -> None:
    """Degrau 3 ainda roteia o histórico — mas nunca em silêncio ([[ADR-394]] D3)."""
    out = _run(tmp_path, _payload(_IMOVEL, _DIVIDA_NEGATIVA))
    assert len(out["dividas"]) == 1
    reasons = (out.get("validation") or {}).get("review_reasons") or []
    assert [r for r in reasons if r["code"].startswith("domain.")], reasons


def test_divida_positiva_sem_secao_nao_e_silenciosa(tmp_path: Path) -> None:
    """Sem `secao` e sem sinal, quem decide é o hint — e isso tem de sair escrito."""
    divida = dict(_DIVIDA_NEGATIVA, valor_brl=200000.0)
    out = _run(tmp_path, _payload(_IMOVEL, divida))
    reasons = (out.get("validation") or {}).get("review_reasons") or []
    assert any("categoria_hint" in r["message"] for r in reasons), reasons
