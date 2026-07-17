"""Fixtures E5 PII-zero para o eval golden do Parecer (A26.l9 + ADR-300 §holdout).

Holdout estratificado para o gate de ``needs_review``/RL1 ter significado. O eixo
primário é a **saúde da reserva** (``reserva_emergencia.cobertura_meses``), em 4 faixas
ponderadas ao ICP do Mathoms (PJ/CLT alta renda + famílias com patrimônio diversificado —
tendem a reserva ACIMA da média, NÃO 100% distressed):

| estrato     | cobertura_meses | avaliacao_liquidity | papel no eval                         | n holdout |
| ----------- | --------------- | ------------------- | ------------------------------------- | --------- |
| ``sub_meta``   | < 3          | insuficiente        | stress — RL1 deve disparar se houver deploy de risco | 6 (25%) |
| ``borderline`` | 3–6          | adequada            | zona cinzenta                          | 4 (17%) |
| ``saudavel``   | ≥ 6          | adequada            | **controle negativo** — RL1 ~0% (precision) | 10 (42%) |
| ``folgado``    | > 12         | confortavel         | reserva ampla                          | 4 (17%) |

n_holdout = 24 (≥20 exigido por ADR-300). ``saudavel + folgado = 14/24 ≈ 58%`` — maioria,
coerente com o ICP. O estrato ``saudavel`` é o **controle negativo**: mede *precision* (RL1
disparando aqui é falso-positivo), métrica que o holdout monocultura anterior (100%
~1,5 mês) não tinha — só provava recall, cego a FP (ADR-300 §Item 3).

Eixos secundários variados entre fixtures (para o número do gate não ser dominado por
uma red line): presença/ausência de dívida cara (RL2 — ``endividamento.dividas[].taxa_juros``),
concentração imobiliária > 40 (RL7 — ``real_estate.concentracao_pct``), presença de seguro
(RL6 — ``alertas`` sem ``seguro_vida_ausente``). PII-zero: nenhum CPF, valores sintéticos.

``make_workspace_e5`` fixa a reserva pelos parâmetros explícitos por estrato — ``cobertura_meses``
é *ratio*, não dinheiro; escalá-lo (bug do ``_scale_money`` anterior) é semanticamente errado e
mantinha 2.1×fator < 6 (monocultura). ``_scale_money`` agora perturba só valores monetários
genuínos e NÃO toca ``reserva_emergencia``.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

from tests.test_parecer_planejador_golden import make_workspace_e5

# Faixas de reserva por estrato: (cobertura_meses, avaliacao_liquidity, total_liquida).
# total_liquida ≈ cobertura_meses × despesas_mensais (40k no E5 base) — coerência interna.
_RESERVA_POR_ESTRATO: dict[str, tuple[float, str, float]] = {
    "sub_meta": (2.1, "insuficiente", 84_000.0),
    "borderline": (4.5, "adequada", 180_000.0),
    "saudavel": (8.0, "adequada", 320_000.0),
    "folgado": (18.0, "confortavel", 720_000.0),
}


@dataclass(frozen=True)
class EvalFixture:
    """Um caso de eval: id legível, estrato de reserva, payload E5, split tuning/holdout."""

    fixture_id: str
    stratum: str
    split: str  # "tuning" | "holdout"
    e5: dict


def _scale_block(block: dict, factor: float) -> None:
    for k, v in block.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            block[k] = round(v * factor, 2)


def _scale_money(e5: dict, factor: float) -> dict:
    """Perturba só valores monetários genuínos; NÃO toca reserva_emergencia (ratio, não R$)."""
    # reserva_emergencia fica fora: cobertura_meses é ratio e os campos vêm de _set_reserva.
    for key in ("patrimonio", "fluxo_caixa", "investimentos"):
        block = e5.get(key)
        if isinstance(block, dict):
            _scale_block(block, factor)
    return e5


def _set_reserva(e5: dict, stratum: str) -> dict:
    """Seta cobertura_meses + avaliacao_liquidity + total_liquida coerentes ao estrato."""
    cobertura, avaliacao, total = _RESERVA_POR_ESTRATO[stratum]
    res = e5.setdefault("reserva_emergencia", {})
    res["cobertura_meses"] = cobertura
    res["avaliacao_liquidity"] = avaliacao
    res["total_liquida"] = total
    return e5


# --- eixos secundários (RL2 dívida cara / RL7 concentração imobiliária / RL6 seguro) ---


def _add_divida_cara(e5: dict) -> dict:
    """RL2: dívida com taxa mensal > 1,5% conhecida no E5."""
    endiv = e5.setdefault("endividamento", {})
    endiv.setdefault("dividas", []).append(
        {"descricao": "rotativo cartão", "taxa_juros": "12,90% a.m.", "saldo": 25_000.0}
    )
    return e5


def _add_concentracao_imovel(e5: dict) -> dict:
    """RL7 + casos-alvo R3.3. Concentração alta: o SSOT de RISCO é
    ratios.concentracao_imobiliaria (base carteira produtiva, ADR-340) — o parecer
    cita este (severidade Alta em ~60%, não Crítica; meta <50%), não a composição.
    PGBL no teto (FP-04): limite=0 é confirmação, não 'investigar do zero'."""
    e5["real_estate"] = {"concentracao_pct": 59.97, "valor_total_imoveis": 2_600_000.0}
    e5.setdefault("ratios", {})["concentracao_imobiliaria"] = 59.97
    # Alinha os campos de abate ao cenário de teto (abate_real == limite) p/ o bloco
    # não afirmar "subaplicado" e "teto atingido" ao mesmo tempo — sinal limpo p/ FP-04.
    e5.setdefault("previdencia_pgbl", {}).update(
        {
            "limite_pgbl_anual": 0.0,
            "pgbl_status": "teto_atingido",
            "abate_real_pct": 12.0,
            "contribuicao_anual": 86_400.0,
        }
    )
    return e5


def _add_seguro(e5: dict) -> dict:
    """RL6: seguro presente — remove o alerta seguro_vida_ausente."""
    e5["alertas"] = [a for a in e5.get("alertas", []) if a != "seguro_vida_ausente"]
    return e5


# (label, mutador) — combináveis; cada fixture aplica um subconjunto p/ variar os eixos.
_AXIS_DIVIDA = ("divida", _add_divida_cara)
_AXIS_IMOVEL = ("imovel", _add_concentracao_imovel)
_AXIS_SEGURO = ("seguro", _add_seguro)

# Combinações de eixos secundários, cicladas dentro de cada estrato para cobrir o produto
# cartesiano relevante sem explodir n. ``()`` = baseline (sem dívida cara, sem concentração,
# seguro ausente — o default do E5 base).
_AXIS_CYCLE: list[tuple[tuple[str, Callable[[dict], dict]], ...]] = [
    (),
    (_AXIS_DIVIDA,),
    (_AXIS_IMOVEL,),
    (_AXIS_SEGURO,),
    (_AXIS_DIVIDA, _AXIS_IMOVEL),
    (_AXIS_SEGURO, _AXIS_IMOVEL),
]


# (estrato, n_holdout, n_tuning) — holdout ponderado ao ICP (saudável+folgado = maioria).
_PLAN: list[tuple[str, int, int]] = [
    ("sub_meta", 6, 4),
    ("borderline", 4, 3),
    ("saudavel", 10, 6),
    ("folgado", 4, 3),
]


def _make_e5(stratum: str, idx: int) -> dict:
    """E5 do estrato com reserva explícita + eixos secundários ciclados + jitter monetário."""
    e5 = copy.deepcopy(make_workspace_e5())
    _scale_money(e5, 0.7 + 0.05 * idx)
    _set_reserva(e5, stratum)
    for _label, mutator in _AXIS_CYCLE[idx % len(_AXIS_CYCLE)]:
        mutator(e5)
    return e5


def _axes_label(stratum: str, idx: int) -> str:
    axes = [label for label, _ in _AXIS_CYCLE[idx % len(_AXIS_CYCLE)]]
    return "_".join([stratum, *axes]) if axes else f"{stratum}_base"


def _build() -> list[EvalFixture]:
    fixtures: list[EvalFixture] = []
    for stratum, n_holdout, n_tuning in _PLAN:
        for i in range(n_holdout + n_tuning):
            split = "holdout" if i < n_holdout else "tuning"
            fixtures.append(
                EvalFixture(f"{_axes_label(stratum, i)}_{i}", stratum, split, _make_e5(stratum, i))
            )
    return fixtures


EVAL_FIXTURES: list[EvalFixture] = _build()
TUNING = [f for f in EVAL_FIXTURES if f.split == "tuning"]
HOLDOUT = [f for f in EVAL_FIXTURES if f.split == "holdout"]
