"""Suite de injeção determinística de bug (ADR-281 · A25.l4 F7): 24 casos (6 famílias × 4) + 5 selados modelando bugs históricos (ADR-271, ADR-246, ADR-255, R$ 811k, membro-CPF) — mutação programática do payload dogfood EM MEMÓRIA (nunca disco), ground truth = node_id ``(stage, artifact_key, field)``; casos selados são NÃO-TUNÁVEIS (mudar a mutação/target exige nova decisão de lane)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from pipeline.domain.lineage_registry import LINEAGE_RULE_REFS

E5 = "E5"
KEY = "analise_financeira"

_LEAF_IMOVEIS = "patrimonio.composicao[Imóveis de Renda].valor"
_LEAF_INV_DAVID = "patrimonio.composicao[Investimentos David].valor"
_LEAF_CAIXA = "patrimonio.composicao[Caixa e Moeda Estrangeira].valor"
_LEAF_DESPESA = "fluxo_caixa.despesas_por_categoria.nao_identificado"
_LEAF_RENDA_FIXA = "investimentos.tabela_classes[Renda Fixa].valor"
_BRUTO = "patrimonio.bruto"
_LIQUIDO = "patrimonio.liquido"
_DESPESA_TOTAL = "fluxo_caixa.despesa_total"
_INVEST_TOTAL = "investimentos.total"
_RESERVA = "reserva_emergencia.total_liquida"

MutateFn = Callable[[dict], None]


@dataclass(frozen=True)
class LineageEvalCase:
    case_id: str
    family: str
    severity: str
    complaint: str
    entry_field: str
    target_node_id: tuple[str, str, str]
    expected_rule_ref: str
    mutate_fn: MutateFn
    sealed: bool = False
    renderer_flags_anomaly: bool = True


def _money(value: float) -> str:
    return f"{Decimal(str(value)):.2f}"


def _entry(payload: dict, name: str) -> dict:
    return payload["_lineage"]["fields"][name]


def _comp_item(payload: dict, categoria: str) -> dict:
    return next(c for c in payload["patrimonio"]["composicao"] if c["categoria"] == categoria)


def _classe_item(payload: dict, categoria: str) -> dict:
    return next(
        c for c in payload["investimentos"]["tabela_classes"] if c["categoria"] == categoria
    )


def _ref(rule_id: str) -> str:
    return LINEAGE_RULE_REFS[rule_id]["ref"]


def _node(field: str) -> tuple[str, str, str]:
    return (E5, KEY, field)


# ─────────────────────────── fábricas de mutação ───────────────────────────


def _bump_comp(categoria: str, delta: float) -> MutateFn:
    def mutate(payload: dict) -> None:
        _comp_item(payload, categoria)["valor"] += delta

    return mutate


def _bump_despesa_leaf(delta: float) -> MutateFn:
    def mutate(payload: dict) -> None:
        payload["fluxo_caixa"]["despesas_por_categoria"]["nao_identificado"] += delta

    return mutate


def _bump_classe(categoria: str, delta: float) -> MutateFn:
    def mutate(payload: dict) -> None:
        _classe_item(payload, categoria)["valor"] += delta

    return mutate


def _set_aggregate(dotted: str, new_value: float) -> MutateFn:
    """Seta payload + ``_lineage.value`` do agregado (dotted é o entry name)."""

    def mutate(payload: dict) -> None:
        obj = payload
        parts = dotted.split(".")
        for key in parts[:-1]:
            obj = obj[key]
        obj[parts[-1]] = new_value
        _entry(payload, dotted)["value"] = _money(new_value)

    return mutate


def _remove_input(entry_name: str, field_suffix: str) -> MutateFn:
    def mutate(payload: dict) -> None:
        entry = _entry(payload, entry_name)
        entry["inputs"] = [i for i in entry["inputs"] if not i["field"].endswith(field_suffix)]

    return mutate


def _dup_input(entry_name: str, field_suffix: str) -> MutateFn:
    def mutate(payload: dict) -> None:
        entry = _entry(payload, entry_name)
        dup = next(dict(i) for i in entry["inputs"] if i["field"].endswith(field_suffix))
        entry["inputs"] = [*entry["inputs"], dup]

    return mutate


def _swap_rule(entry_name: str, donor_rule_id: str) -> MutateFn:
    def mutate(payload: dict) -> None:
        _entry(payload, entry_name)["rule_ref"] = dict(LINEAGE_RULE_REFS[donor_rule_id])

    return mutate


def _set_needs_review(entry_name: str) -> MutateFn:
    def mutate(payload: dict) -> None:
        _entry(payload, entry_name)["needs_review"] = True

    return mutate


def _set_comp(categoria: str, new_value: float) -> MutateFn:
    def mutate(payload: dict) -> None:
        _comp_item(payload, categoria)["valor"] = new_value

    return mutate


def _set_classe(categoria: str, new_value: float) -> MutateFn:
    def mutate(payload: dict) -> None:
        _classe_item(payload, categoria)["valor"] = new_value

    return mutate


def _set_despesa_leaf(new_value: float) -> MutateFn:
    def mutate(payload: dict) -> None:
        payload["fluxo_caixa"]["despesas_por_categoria"]["nao_identificado"] = new_value

    return mutate


def _compose(*fns: MutateFn) -> MutateFn:
    def mutate(payload: dict) -> None:
        for fn in fns:
            fn(payload)

    return mutate


# ────────────────────────────── famílias × 4 ──────────────────────────────
# Tuplas: (case_id, mutate_fn, complaint, entry_field, target_field, rule_id)

_VALUE_DELTA_LEAF = (
    (
        "vdl-01",
        _bump_comp("Imóveis de Renda", 50000.0),
        "O patrimônio líquido do relatório não bate com a soma das categorias.",
        _LIQUIDO,
        _LEAF_IMOVEIS,
        _BRUTO,
    ),
    (
        "vdl-02",
        _bump_comp("Investimentos David", -30000.0),
        "O patrimônio bruto está menor do que a família esperava.",
        _LIQUIDO,
        _LEAF_INV_DAVID,
        _BRUTO,
    ),
    (
        "vdl-03",
        _bump_despesa_leaf(250.0),
        "A despesa total do período não fecha com o extrato categorizado.",
        _DESPESA_TOTAL,
        _LEAF_DESPESA,
        _DESPESA_TOTAL,
    ),
    (
        "vdl-04",
        _bump_classe("Renda Fixa", 10000.0),
        "O total investido diverge do informe da corretora.",
        _INVEST_TOTAL,
        _LEAF_RENDA_FIXA,
        _INVEST_TOTAL,
    ),
)

_VALUE_DELTA_AGGREGATE = (
    (
        "vda-01",
        _set_aggregate(_BRUTO, 780000.0),
        "O patrimônio bruto não corresponde à soma das categorias listadas.",
        _LIQUIDO,
        _BRUTO,
        _BRUTO,
    ),
    (
        "vda-02",
        _set_aggregate(_DESPESA_TOTAL, 1800.0),
        "A despesa total está maior que a soma das categorias.",
        _DESPESA_TOTAL,
        _DESPESA_TOTAL,
        _DESPESA_TOTAL,
    ),
    (
        "vda-03",
        _set_aggregate(_INVEST_TOTAL, 700000.0),
        "O total investido não é a soma das classes de ativo.",
        _INVEST_TOTAL,
        _INVEST_TOTAL,
        _INVEST_TOTAL,
    ),
    (
        "vda-04",
        _set_aggregate(_RESERVA, 160000.0),
        "A reserva de emergência informada não bate com os saldos líquidos.",
        _RESERVA,
        _RESERVA,
        _RESERVA,
    ),
)

_INPUT_REMOVED = (
    (
        "inr-01",
        _remove_input(_BRUTO, "[Imóveis de Renda].valor"),
        "O patrimônio bruto parece ignorar os imóveis de renda no rastreio.",
        _LIQUIDO,
        _BRUTO,
        _BRUTO,
    ),
    (
        "inr-02",
        _remove_input(_RESERVA, "patrimonio.caixa_moeda_estrangeira"),
        "A reserva de emergência não considera o caixa em moeda estrangeira.",
        _RESERVA,
        _RESERVA,
        _RESERVA,
    ),
    (
        "inr-03",
        _remove_input(_INVEST_TOTAL, "[Renda Fixa].valor"),
        "O total investido perdeu o rastro da renda fixa.",
        _INVEST_TOTAL,
        _INVEST_TOTAL,
        _INVEST_TOTAL,
    ),
    (
        "inr-04",
        _remove_input(_BRUTO, "[Caixa e Moeda Estrangeira].valor"),
        "O caixa sumiu do rastreio do patrimônio bruto.",
        _LIQUIDO,
        _BRUTO,
        _BRUTO,
    ),
)

_RULE_REF_WRONG = (
    (
        "rrw-01",
        _swap_rule(_BRUTO, _RESERVA),
        "A regra apontada para o patrimônio bruto não é a calculadora de patrimônio.",
        _LIQUIDO,
        _BRUTO,
        _BRUTO,
    ),
    (
        "rrw-02",
        _swap_rule(_RESERVA, _DESPESA_TOTAL),
        "A reserva de emergência referencia regra de fluxo de caixa, não de reserva.",
        _RESERVA,
        _RESERVA,
        _RESERVA,
    ),
    (
        "rrw-03",
        _swap_rule(_DESPESA_TOTAL, _INVEST_TOTAL),
        "A despesa total aponta para o analisador de investimentos como regra.",
        _DESPESA_TOTAL,
        _DESPESA_TOTAL,
        _DESPESA_TOTAL,
    ),
    (
        "rrw-04",
        _swap_rule(_INVEST_TOTAL, _BRUTO),
        "O total investido referencia a calculadora de patrimônio como regra.",
        _INVEST_TOTAL,
        _INVEST_TOTAL,
        _INVEST_TOTAL,
    ),
)

_DEDUP_OVERCOLLAPSE = (
    (
        "ddc-01",
        _compose(
            _set_comp("Imóveis de Renda", 300000.0),
            _set_aggregate(_BRUTO, 430000.0),
            _set_aggregate(_LIQUIDO, 280000.0),
        ),
        "A família tem DOIS imóveis de renda de R$ 300.000 cada (R$ 600.000 no "
        "total), mas o relatório consolidou um só.",
        _LIQUIDO,
        _LEAF_IMOVEIS,
        _BRUTO,
    ),
    (
        "ddc-02",
        _compose(
            _set_classe("Renda Fixa", 40000.0),
            _set_aggregate(_INVEST_TOTAL, 640000.0),
        ),
        "Há duas posições de renda fixa de R$ 40.000, idênticas ao centavo, em "
        "bancos distintos — uma delas sumiu do total investido.",
        _INVEST_TOTAL,
        _LEAF_RENDA_FIXA,
        _INVEST_TOTAL,
    ),
    (
        "ddc-03",
        _compose(
            _set_despesa_leaf(750.0),
            _set_aggregate(_DESPESA_TOTAL, 750.0),
        ),
        "Houve duas transferências PIX de R$ 750 em dias diferentes, mas a "
        "despesa total só conta uma.",
        _DESPESA_TOTAL,
        _LEAF_DESPESA,
        _DESPESA_TOTAL,
    ),
    (
        "ddc-04",
        _compose(
            _remove_input(_RESERVA, "patrimonio.investimentos_david"),
            _set_aggregate(_RESERVA, 50000.0),
        ),
        "Os investimentos líquidos do titular sumiram do cálculo da reserva de "
        "emergência após a consolidação.",
        _RESERVA,
        _RESERVA,
        _RESERVA,
    ),
)

_NEEDS_REVIEW_IGNORED = (
    (
        "nri-01",
        _set_needs_review(_BRUTO),
        "O patrimônio bruto estava marcado para revisão humana e mesmo assim "
        "foi consumido no relatório.",
        _LIQUIDO,
        _BRUTO,
        _BRUTO,
    ),
    (
        "nri-02",
        _set_needs_review(_DESPESA_TOTAL),
        "A despesa total tem flag de revisão pendente ignorada.",
        _DESPESA_TOTAL,
        _DESPESA_TOTAL,
        _DESPESA_TOTAL,
    ),
    (
        "nri-03",
        _set_needs_review(_INVEST_TOTAL),
        "O total investido foi usado com revisão pendente.",
        _INVEST_TOTAL,
        _INVEST_TOTAL,
        _INVEST_TOTAL,
    ),
    (
        "nri-04",
        _set_needs_review(_RESERVA),
        "A reserva de emergência foi calculada sobre dado marcado para revisão.",
        _RESERVA,
        _RESERVA,
        _RESERVA,
    ),
)

# ───────────────── casos SELADOS (bugs históricos, não-tunáveis) ─────────────────

_SEALED = (
    (
        "sel-adr271",
        _compose(
            _dup_input(_INVEST_TOTAL, "[Renda Fixa].valor"),
            _set_aggregate(_INVEST_TOTAL, 760000.0),
        ),
        "A mesma posição de renda fixa aparece duplicada no total investido — a "
        "série da conta entre anos de IRPF não foi unida.",
        _INVEST_TOTAL,
        _INVEST_TOTAL,
        _INVEST_TOTAL,
    ),
    (
        "sel-adr246",
        _compose(
            _set_comp("Imóveis de Renda", 1200000.0),
            _set_aggregate(_BRUTO, 1330000.0),
            _set_aggregate(_LIQUIDO, 1180000.0),
        ),
        "Imóvel em comunhão declarado no IRPF dos dois cônjuges foi SOMADO no "
        "patrimônio — é o mesmo ativo e deveria valer uma vez.",
        _LIQUIDO,
        _LEAF_IMOVEIS,
        _BRUTO,
    ),
    (
        "sel-adr255",
        _compose(
            _set_despesa_leaf(3000.0),
            _set_aggregate(_DESPESA_TOTAL, 3000.0),
        ),
        "A mesma transação aparece duas vezes na despesa: o banco emite o PDF "
        "com sufixo PIX variante na descrição e o dedup furou.",
        _DESPESA_TOTAL,
        _LEAF_DESPESA,
        _DESPESA_TOTAL,
    ),
    (
        "sel-811k",
        _compose(
            _set_comp("Investimentos David", 160000.0),
            _set_aggregate(_BRUTO, 810000.0),
            _set_aggregate(_LIQUIDO, 660000.0),
        ),
        "O mesmo membro aparece como duas pessoas (nome de solteira e de "
        "casada) e os investimentos dele entraram duas vezes no patrimônio.",
        _LIQUIDO,
        _LEAF_INV_DAVID,
        _BRUTO,
    ),
    (
        "sel-membro-cpf",
        _compose(
            _dup_input(_RESERVA, "patrimonio.investimentos_david"),
            _set_aggregate(_RESERVA, 210000.0),
        ),
        "A identidade de membro é por slug-do-nome em vez de CPF: a mesma "
        "pessoa entra duas vezes na reserva de emergência.",
        _RESERVA,
        _RESERVA,
        _RESERVA,
    ),
)

_FAMILY_TABLES = (
    ("value_delta@leaf", "alta", True, _VALUE_DELTA_LEAF),
    ("value_delta@aggregate", "alta", True, _VALUE_DELTA_AGGREGATE),
    ("input_removed", "alta", True, _INPUT_REMOVED),
    ("rule_ref_wrong", "media", False, _RULE_REF_WRONG),
    ("dedup_overcollapse", "alta", False, _DEDUP_OVERCOLLAPSE),
    ("needs_review_ignored", "media", True, _NEEDS_REVIEW_IGNORED),
)


def _build_family(family: str, severity: str, flags_anomaly: bool, rows, *, sealed=False):
    return [
        LineageEvalCase(
            case_id=case_id,
            family=family,
            severity=severity,
            complaint=complaint,
            entry_field=entry_field,
            target_node_id=_node(target_field),
            expected_rule_ref=_ref(rule_id),
            mutate_fn=mutate_fn,
            sealed=sealed,
            renderer_flags_anomaly=flags_anomaly,
        )
        for case_id, mutate_fn, complaint, entry_field, target_field, rule_id in rows
    ]


def build_cases() -> list[LineageEvalCase]:
    """24 casos (6 famílias × 4) + 5 selados — ordem determinística."""
    cases: list[LineageEvalCase] = []
    for family, severity, flags_anomaly, rows in _FAMILY_TABLES:
        cases.extend(_build_family(family, severity, flags_anomaly, rows))
    cases.extend(_build_family("sealed", "alta", False, _SEALED, sealed=True))
    return cases
