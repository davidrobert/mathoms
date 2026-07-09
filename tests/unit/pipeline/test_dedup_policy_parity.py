"""ADR-276 — gate diferencial do refactor EntityDedupPolicy (A21.l3): congela o
output byte-a-byte das funções públicas de dedup sobre um corpus que exercita
todo caminho (single/cross-year/joint/split/diverge investimentos;
pid/canon/cross-código/fuzzy/tie/diverge imóveis). Fixture gerado PRÉ-refactor;
policies sobre o runner devem reproduzi-lo idêntico (``fn``/``fp`` l2 são lossy).
Regenerar (só com mudança intencional + ADR): ``python -m
tests.unit.pipeline.test_dedup_policy_parity --write``.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from pipeline.domain.services.imoveis_dedup import dedup_imoveis_consolidados
from pipeline.domain.services.investimentos_dedup import (
    dedup_investimentos_consolidados,
)

_SNAPSHOT = (
    Path(__file__).parent.parent.parent / "fixtures" / "dedup" / "policy_parity_snapshot.json"
)


def _inv(
    *,
    proprietario: str,
    valores: dict[str, float],
    tipo: str = "renda_fixa",
    descricao: str = "Tesouro Selic 2029",
    instituicao: str | None = "XP Investimentos",
) -> dict:
    e: dict = {
        "descricao": descricao,
        "tipo": tipo,
        "proprietario": proprietario,
        "valores_31_12": dict(valores),
    }
    if instituicao is not None:
        e["instituicao"] = instituicao
    return e


def _imo(*, proprietario: str, valor, ano: str = "2024", **kw) -> dict:
    e: dict = {
        "descricao": kw.get("descricao", "APT COND EXEMPLO B"),
        "proprietario": proprietario,
        "codigo_rfb": kw.get("codigo_rfb", "11"),
        "valores_31_12": {ano: valor},
        "tipo": "imovel",
    }
    if "property_id" in kw:
        e["property_id"] = kw["property_id"]
    if "endereco_canonical" in kw:
        e["endereco_canonical"] = kw["endereco_canonical"]
    return e


# (nome, items) — investimentos. Cobre todos os ramos de investimentos_dedup.
_CORPUS_INVEST: list[tuple[str, list[dict]]] = [
    ("single", [_inv(proprietario="david", valores={"2024": 10000.0})]),
    (
        "two_distinct",
        [
            _inv(proprietario="david", valores={"2024": 1000.0}, descricao="Selic"),
            _inv(proprietario="david", valores={"2024": 2000.0}, descricao="IPCA"),
        ],
    ),
    (
        "cross_year_series",
        [
            _inv(proprietario="david", valores={"2023": 8000.0}),
            _inv(proprietario="david", valores={"2024": 9500.0}),
        ],
    ),
    (
        "same_year_conflict",
        [
            _inv(proprietario="david", valores={"2024": 10000.0}),
            _inv(proprietario="david", valores={"2024": 10500.0}),
        ],
    ),
    (
        "absent_recent_year",
        [
            _inv(proprietario="david", valores={"2022": 5000.0}),
            _inv(proprietario="david", valores={"2024": 6000.0}),
        ],
    ),
    (
        "joint_identical",
        [
            _inv(proprietario="david", valores={"2024": 25000.00}),
            _inv(proprietario="mariana", valores={"2024": 25000.00}),
        ],
    ),
    (
        "divergent_split",
        [
            _inv(proprietario="david", valores={"2024": 10000.0}),
            _inv(proprietario="mariana", valores={"2024": 7000.0}),
        ],
    ),
    (
        "zero_never_joint",
        [
            _inv(proprietario="david", valores={"2024": 0.0}),
            _inv(proprietario="mariana", valores={"2024": 0.0}),
        ],
    ),
    (
        "three_partial_match",
        [
            _inv(proprietario="david", valores={"2024": 100.0}),
            _inv(proprietario="mariana", valores={"2024": 100.0}),
            _inv(proprietario="joao", valores={"2024": 999.0}),
        ],
    ),
    (
        "unidentified_no_desc",
        [{"tipo": "outros", "proprietario": "david", "valores_31_12": {"2024": 1.0}}],
    ),
    (
        "different_institution",
        [
            _inv(proprietario="david", valores={"2024": 1000.0}, instituicao="XP"),
            _inv(proprietario="david", valores={"2024": 1000.0}, instituicao="BTG"),
        ],
    ),
    (
        "desc_normalized",
        [
            _inv(proprietario="david", valores={"2023": 1.0}, descricao="Tesouro  SELIC"),
            _inv(proprietario="david", valores={"2024": 2.0}, descricao="tesouro selic"),
        ],
    ),
]

# (nome, items, titular_key) — imóveis. Cobre todos os ramos de imoveis_dedup.
_CORPUS_IMOVEIS: list[tuple[str, list[dict], str | None]] = [
    ("single", [_imo(proprietario="david_robert", valor=477436.58, property_id="uuid-a")], None),
    (
        "two_distinct",
        [
            _imo(proprietario="david", valor=400000, property_id="uuid-a"),
            _imo(proprietario="david", valor=600000, property_id="uuid-b"),
        ],
        None,
    ),
    (
        "same_pid_two_members",
        [
            _imo(proprietario="david_robert", valor=477436.58, property_id="uuid-x"),
            _imo(proprietario="mariana_xxx", valor=530000.0, property_id="uuid-x"),
        ],
        "david_robert",
    ),
    (
        "divergence_below_10pct",
        [
            _imo(proprietario="david", valor=500000, property_id="uuid-y"),
            _imo(proprietario="mariana", valor=525000, property_id="uuid-y"),
        ],
        None,
    ),
    (
        "divergence_above_threshold",
        [
            _imo(proprietario="david", valor=400000, property_id="uuid-z"),
            _imo(proprietario="mariana", valor=600000, property_id="uuid-z"),
        ],
        None,
    ),
    (
        "three_declarations",
        [
            _imo(proprietario="david", valor=300000, property_id="uuid-3"),
            _imo(proprietario="mariana", valor=400000, property_id="uuid-3"),
            _imo(proprietario="filho", valor=350000, property_id="uuid-3"),
        ],
        None,
    ),
    (
        "canonical_fallback",
        [
            _imo(
                proprietario="david",
                valor=400000,
                codigo_rfb="11",
                endereco_canonical="av exemplo 2192",
            ),
            _imo(
                proprietario="mariana",
                valor=500000,
                codigo_rfb="11",
                endereco_canonical="av exemplo 2192",
            ),
        ],
        None,
    ),
    (
        "diff_codigo_same_canonical",
        [
            _imo(
                proprietario="david",
                valor=400000,
                codigo_rfb="11",
                endereco_canonical="av paulista 1500",
            ),
            _imo(
                proprietario="mariana",
                valor=500000,
                codigo_rfb="12",
                endereco_canonical="av paulista 1500",
            ),
        ],
        None,
    ),
    (
        "no_pid_no_canonical",
        [
            _imo(proprietario="david", valor=400000, codigo_rfb="11"),
            _imo(proprietario="mariana", valor=500000, codigo_rfb="11"),
        ],
        None,
    ),
    (
        "empty_codigo",
        [
            _imo(proprietario="david", valor=400000, codigo_rfb="", endereco_canonical="rua x"),
            _imo(proprietario="mariana", valor=500000, codigo_rfb="", endereco_canonical="rua x"),
        ],
        None,
    ),
    (
        "tie_value_year_titular",
        [
            _imo(proprietario="david_robert", valor=500000, property_id="uuid-t"),
            _imo(proprietario="mariana", valor=500000, property_id="uuid-t"),
        ],
        "david_robert",
    ),
    (
        "recent_year_wins",
        [
            _imo(proprietario="david", valor=500000, ano="2023", property_id="uuid-ry"),
            _imo(proprietario="mariana", valor=500000, ano="2024", property_id="uuid-ry"),
        ],
        None,
    ),
    (
        "cross_codigo_especifico_generico",
        [
            _imo(
                proprietario="david",
                valor=212000,
                codigo_rfb="11",
                endereco_canonical="exemplo 496",
            ),
            _imo(
                proprietario="david_camargo",
                valor=0,
                codigo_rfb="01",
                endereco_canonical="exemplo 496",
            ),
        ],
        None,
    ),
    (
        "dois_especificos_divergentes",
        [
            _imo(
                proprietario="david", valor=500000, codigo_rfb="11", endereco_canonical="rua y 200"
            ),
            _imo(
                proprietario="mariana",
                valor=400000,
                codigo_rfb="12",
                endereco_canonical="rua y 200",
            ),
        ],
        None,
    ),
    (
        "especifico_dois_genericos",
        [
            _imo(
                proprietario="david", valor=500000, codigo_rfb="11", endereco_canonical="rua w 400"
            ),
            _imo(proprietario="mariana", valor=0, codigo_rfb="01", endereco_canonical="rua w 400"),
            _imo(
                proprietario="david_alt", valor=0, codigo_rfb="01", endereco_canonical="rua w 400"
            ),
        ],
        None,
    ),
    (
        "fuzzy_founder_190_186",
        [
            _imo(
                descricao="APTO 34 EXEMPLO 190",
                proprietario="david",
                valor=800000,
                codigo_rfb="11",
                endereco_canonical="exemplo 190",
            ),
            _imo(
                descricao="Ap 34 Exemplo 186",
                proprietario="david",
                valor=750000,
                codigo_rfb="01",
                endereco_canonical="exemplo 186",
            ),
        ],
        None,
    ),
    (
        "fuzzy_delta_grande",
        [
            _imo(
                descricao="EDIFICIO X PAULISTA 1500",
                proprietario="david",
                valor=500000,
                codigo_rfb="11",
                endereco_canonical="paulista 1500",
            ),
            _imo(
                descricao="EDIFICIO Y PAULISTA 1490",
                proprietario="david",
                valor=600000,
                codigo_rfb="11",
                endereco_canonical="paulista 1490",
            ),
        ],
        None,
    ),
    (
        "fuzzy_complemento_divergente",
        [
            _imo(
                descricao="APTO 34 - PAULISTA 100",
                proprietario="david",
                valor=500000,
                codigo_rfb="11",
                endereco_canonical="paulista 100",
            ),
            _imo(
                descricao="APTO 51 - PAULISTA 102",
                proprietario="mariana",
                valor=600000,
                codigo_rfb="11",
                endereco_canonical="paulista 102",
            ),
        ],
        None,
    ),
    (
        "cross_codigo_antes_fuzzy_3",
        [
            _imo(
                descricao="APTO 34 EXEMPLO 190",
                proprietario="david",
                valor=800000,
                codigo_rfb="11",
                endereco_canonical="exemplo 190",
            ),
            _imo(
                descricao="APTO 34 EXEMPLO 190",
                proprietario="alt1",
                valor=0,
                codigo_rfb="01",
                endereco_canonical="exemplo 190",
            ),
            _imo(
                descricao="APTO 34 EXEMPLO 186",
                proprietario="alt2",
                valor=750000,
                codigo_rfb="01",
                endereco_canonical="exemplo 186",
            ),
        ],
        None,
    ),
]


def _ser(items, warnings, count_before, count_after, dropped) -> dict:
    return {
        "items": items,
        "warnings": [dataclasses.asdict(w) for w in warnings],
        "count_before": count_before,
        "count_after": count_after,
        "dropped": list(dropped),
    }


def _run_corpus() -> dict:
    snapshot: dict = {}
    for name, items in _CORPUS_INVEST:
        r = dedup_investimentos_consolidados(items)
        snapshot[f"invest::{name}"] = _ser(
            r.investimentos, r.warnings, r.count_before, r.count_after, r.dropped_keys
        )
    for name, items, titular_key in _CORPUS_IMOVEIS:
        r = dedup_imoveis_consolidados(items, titular_key=titular_key)
        snapshot[f"imovel::{name}"] = _ser(
            r.imoveis, r.warnings, r.count_before, r.count_after, r.dropped_property_ids
        )
    return snapshot


def test_dedup_output_matches_frozen_snapshot() -> None:
    """Output byte-a-byte idêntico ao baseline pré-refactor (ADR-276 gate)."""
    expected = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(_run_corpus(), sort_keys=True))
    assert actual == expected


if __name__ == "__main__":
    import sys

    if "--write" in sys.argv:
        _SNAPSHOT.write_text(
            json.dumps(_run_corpus(), sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {_SNAPSHOT}")
