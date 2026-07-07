"""A21.l2 — mede fn_rate/fp_rate do dedup E1.5c sobre golden zero-PII anotado.

``fn_rate`` = pares de duplicatas reais NÃO fundidos / total de pares duplicados reais.
``fp_rate`` = pares de entidades distintas fundidos / total de pares não-duplicados.
Meta (PLAN-launch-trust §F1-O1): ``fn_rate`` ≤ 5% (A21-KR2); ``fp_rate`` = 0% (A21-KR3,
red line — fundir patrimônio real distinto é pior que deixar duplicata passar).

O golden roda o caminho real ``main_with_store`` (consolidate → dedup imóveis →
dedup investimentos) e cada item de saída é remapeado à sua entidade por
descrição+dono+ano (chave humana, não a chave interna do dedup — senão a métrica
seria circular). Dívidas não passam por dedup em E1.5c, logo ficam fora de fn/fp.

Plano: [[PLAN-launch-trust]] §F1-O1. Lane A21.l2.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.domain.services._tx_identity import normalize_descricao

_FIXTURE = Path(__file__).parent / "fixtures" / "dedup" / "multi_year_baseline.json"
# categoria do item → lista consolidada onde a entidade deduplicada aparece.
_DEDUP_LISTS = {"imovel": "imoveis_consolidados", "investimento": "investimentos_consolidados"}


def _load_golden() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _consolidate(tmp_path: Path, baseline: dict) -> dict:
    """Roda E1.5c (``main_with_store``) sobre o baseline e devolve o dict consolidado."""
    from scripts.consolidate_baseline import main_with_store

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "pipeline.json").write_text("{}")
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", baseline)
    ctx = WorkspaceContext(
        root=tmp_path,
        artifact_store=store,
        workspace_id="test-ws-l2",
        property_identity_resolver=InMemoryPropertyIdentityResolver(),
    )
    assert main_with_store(ctx)["success"] is True
    return store.read("E1.5c", "baseline_patrimonial")


def _label_of(expected: dict) -> dict[str, str]:
    """``item_id`` → ``entity_label`` (known_duplicates + distinct_entities; exclui coverage_only)."""
    labels: dict[str, str] = {}
    for block in expected["known_duplicates"] + expected["distinct_entities"]:
        for item_id in block["item_ids"]:
            labels[item_id] = block["entity_label"]
    return labels


def _owner_match(membro: str, entry: dict) -> bool:
    if (entry.get("proprietario") or "").lower() == membro:
        return True
    return membro in {str(p).lower() for p in (entry.get("proprietarios") or [])}


def _entry_years(entry: dict) -> set[str]:
    return set((entry.get("valores_31_12") or entry.get("saldo_31_12") or {}).keys())


def _locate(item: dict, entries: list[dict]) -> int | None:
    """Índice da entry consolidada que representa o item (descrição+dono+ano); None se sumiu."""
    desc = normalize_descricao(item["descricao"])
    membro = item["membro"].strip().lower()
    ano = str(item["ano"])
    for idx, entry in enumerate(entries):
        if (
            normalize_descricao(entry.get("descricao")) == desc
            and _owner_match(membro, entry)
            and ano in _entry_years(entry)
        ):
            return idx
    return None


def _predicted_entity(item: dict, out: dict) -> tuple[str, int] | None:
    """Entidade de saída onde o item caiu — ``None`` se categoria não-deduplicada ou item sumiu."""
    list_name = _DEDUP_LISTS.get((item.get("categoria") or "").lower())
    if list_name is None or item.get("valor_brl", 0) < 0:
        return None
    idx = _locate(item, out.get(list_name, []))
    return (list_name, idx) if idx is not None else None


def _measure(golden: dict, out: dict) -> dict:
    labels = _label_of(golden["_expected"])
    rows = [
        (labels[it["item_id"]], _predicted_entity(it, out))
        for it in golden["itens"]
        if it["item_id"] in labels
    ]
    return _pairwise_rates(rows)


def _pairwise_rates(rows: list[tuple[str, object]]) -> dict:
    fn = fp = real_dup = non_dup = 0
    for (label_a, pred_a), (label_b, pred_b) in itertools.combinations(rows, 2):
        is_dup = label_a == label_b
        merged = pred_a is not None and pred_a == pred_b
        real_dup += is_dup
        non_dup += not is_dup
        fn += is_dup and not merged
        fp += (not is_dup) and merged
    return {
        "fn": fn,
        "fp": fp,
        "real_dup_pairs": real_dup,
        "non_dup_pairs": non_dup,
        "fn_rate": fn / real_dup if real_dup else 0.0,
        "fp_rate": fp / non_dup if non_dup else 0.0,
    }


def _latest(entry: dict) -> float:
    valores = entry.get("valores_31_12") or {}
    return float(valores[max(valores)]) if valores else 0.0


@pytest.fixture
def consolidated(tmp_path: Path) -> dict:
    return _consolidate(tmp_path, _load_golden())


def test_fp_rate_is_zero(consolidated: dict) -> None:
    """A21-KR3 red line: nenhuma entidade real distinta pode ser fundida."""
    metrics = _measure(_load_golden(), consolidated)
    assert metrics["fp_rate"] == _load_golden()["_expected"]["metrics"]["fp_rate_max"], metrics
    assert metrics["non_dup_pairs"] > 0  # a métrica de fato exercitou pares não-dup


def test_fn_rate_within_target(consolidated: dict) -> None:
    """A21-KR2: duplicatas reais não-fundidas ≤ 5% do total de duplicatas reais."""
    metrics = _measure(_load_golden(), consolidated)
    assert metrics["fn_rate"] <= _load_golden()["_expected"]["metrics"]["fn_rate_max"], metrics
    assert metrics["real_dup_pairs"] > 0  # a métrica de fato exercitou pares duplicados


def test_golden_feeds_inv1_conservation(consolidated: dict) -> None:
    """INV-1 (l1) sobre o golden: dedup nunca cria patrimônio (soma pós ≤ soma bruta)."""
    golden = _load_golden()
    raw = sum(
        it["valor_brl"]
        for it in golden["itens"]
        if (it.get("categoria") or "").lower() in _DEDUP_LISTS and it["valor_brl"] > 0
    )
    dedup = sum(_latest(e) for e in consolidated["investimentos_consolidados"]) + sum(
        _latest(e) for e in consolidated["imoveis_consolidados"]
    )
    assert dedup <= raw


def test_known_duplicates_collapse_to_one(consolidated: dict) -> None:
    """Cada bloco known_duplicates colapsa em 1 entidade com o representativo esperado."""
    invest = consolidated["investimentos_consolidados"]
    imoveis = consolidated["imoveis_consolidados"]
    series = [e for e in invest if e["descricao"] == "TESOURO IPCA 2035"]
    joint = [e for e in invest if e["descricao"] == "CDB BANCO EXEMPLO 500"]
    apt = [e for e in imoveis if "EDIFICIO MODELO" in e["descricao"]]
    assert len(series) == 1 and set(series[0]["valores_31_12"]) == {"2022", "2023", "2024"}
    assert _latest(series[0]) == 85000.0  # representativo = max(ano), mesmo subindo
    assert len(joint) == 1 and joint[0]["proprietario"] == "casal" and _latest(joint[0]) == 50000.0
    assert len(apt) == 1 and apt[0]["proprietario"] == "casal" and _latest(apt[0]) == 500000.0


def test_adversarial_same_name_not_merged(consolidated: dict) -> None:
    """RED LINE: dois donos com mesma descrição mas valor diferente NÃO fundem (possível dup)."""
    comum = [
        e
        for e in consolidated["investimentos_consolidados"]
        if e["descricao"] == "CDB BANCO COMUM 777"
    ]
    assert len(comum) == 2
    donos = {e["proprietario"] for e in comum}
    assert donos == {"david_robert", "mariana_silva"}
    assert all(e.get("_dedup_warning", {}).get("type") == "possivel_duplicata" for e in comum)
