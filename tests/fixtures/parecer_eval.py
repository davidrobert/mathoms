"""Fixtures E5 PII-zero para o eval golden do evidencia_path (A26.l1)."""

# 25 variantes estratificadas derivadas do E5 sintético do golden (zero PII —
# valores e nomes fictícios). Split 15 tuning / 10 holdout; o holdout é lacrado e
# estratificado (cada modo de falha tem ≥1 caso), nunca visto no tuning.

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

from tests.test_parecer_planejador_golden import make_workspace_e5


@dataclass(frozen=True)
class EvalFixture:
    """Um caso de eval: id legível, estrato, payload E5, split tuning/holdout."""

    fixture_id: str
    stratum: str
    split: str  # "tuning" | "holdout"
    e5: dict


def _scale_block(block: dict, factor: float) -> None:
    for k, v in block.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            block[k] = round(v * factor, 2)


def _scale_money(e5: dict, factor: float) -> dict:
    """Perturba valores monetários por um fator (variedade entre fixtures)."""
    for key in ("patrimonio", "fluxo_caixa", "reserva_emergencia", "investimentos"):
        block = e5.get(key)
        if isinstance(block, dict):
            _scale_block(block, factor)
    return e5


def _mut_happy(e5: dict) -> dict:
    return e5


def _mut_sem_previdencia(e5: dict) -> dict:
    e5["previdencia_pgbl"] = {}
    return e5


def _mut_sem_imovel(e5: dict) -> dict:
    e5["investimentos"]["n_imoveis_total"] = 0
    comp = e5["patrimonio"].get("composicao", {})
    comp["imoveis_residencia"] = 0.0
    comp["imoveis_investimento"] = 0.0
    return e5


def _mut_leaf_nulo(e5: dict) -> dict:
    e5["reserva_emergencia"]["total_liquida"] = None
    e5["passive_income"]["renda_passiva_mensal"] = None
    return e5


def _mut_periodo_999999(e5: dict) -> dict:
    e5["periodo_dados"] = "999999"
    return e5


def _mut_solteiro(e5: dict) -> dict:
    e5["cenarios_conjuge"] = {}
    e5["irpf_kpis"]["dependentes_count"] = 0
    return e5


# (estrato, mutador, n_casos, n_holdout) — soma 25 fixtures, 10 holdout.
_PLAN: list[tuple[str, Callable[[dict], dict], int, int]] = [
    ("happy", _mut_happy, 6, 2),
    ("sem_previdencia", _mut_sem_previdencia, 4, 1),
    ("sem_imovel", _mut_sem_imovel, 4, 1),
    ("leaf_nulo", _mut_leaf_nulo, 4, 2),
    ("periodo_999999", _mut_periodo_999999, 3, 2),
    ("solteiro", _mut_solteiro, 4, 2),
]


def _build() -> list[EvalFixture]:
    fixtures: list[EvalFixture] = []
    for stratum, mutator, n, n_holdout in _PLAN:
        for i in range(n):
            e5 = _scale_money(copy.deepcopy(make_workspace_e5()), 0.7 + 0.1 * i)
            split = "holdout" if i < n_holdout else "tuning"
            fixtures.append(EvalFixture(f"{stratum}_{i}", stratum, split, mutator(e5)))
    return fixtures


EVAL_FIXTURES: list[EvalFixture] = _build()
TUNING = [f for f in EVAL_FIXTURES if f.split == "tuning"]
HOLDOUT = [f for f in EVAL_FIXTURES if f.split == "holdout"]
