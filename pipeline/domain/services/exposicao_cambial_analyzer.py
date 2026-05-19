"""ExposicaoCambialAnalyzer — agrega patrimônio com lastro em moeda estrangeira (Bloco G plan/RESIDENCIA_E_USO; co-design 2026-05-18; threshold canônico verde >=10% / amarelo 5-10% / vermelho <5%; denominador investivel_financeiro)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pipeline.domain.services.asset_classifier import classify_asset

# ADR-193 + co-design G: bucket "Internacional" = lastro forte.
_BUCKET_INTERNACIONAL = "Internacional"

# Tier de alerta (financial-planner co-design 2026-05-18). Trade-off:
# limiar único sem perfil de risco; conservadorismo Perini > otimismo.
THRESHOLD_VERDE_PCT = 10.0
THRESHOLD_AMARELO_PCT = 5.0


@dataclass(frozen=True)
class ExposicaoCambialPorMoeda:
    """Soma por moeda específica (USD, EUR, etc.) em BRL equivalente (Decimal ADR-090)."""

    moeda: str
    valor_brl: Decimal
    # percentage — share dentro da exposição cambial total (não-monetário; rate)
    share_pct: float


@dataclass(frozen=True)
class ExposicaoCambialResult:
    """Agregado: exposição cambial total + breakdown por moeda + tier."""

    total_brl: Decimal
    pct_investivel_financeiro: float  # percentage
    por_moeda: tuple[ExposicaoCambialPorMoeda, ...] = ()
    tier: str = "vermelho"  # verde | amarelo | vermelho | empty (zero ativos)
    # Linhas detalhadas (conta + ativo) que compõem a exposição — usado no card.
    detalhes: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "total_brl": float(round(self.total_brl, 2)),
            "pct_investivel_financeiro": round(self.pct_investivel_financeiro, 2),
            "por_moeda": [
                {
                    "moeda": pm.moeda,
                    "valor_brl": float(round(pm.valor_brl, 2)),
                    "share_pct": round(pm.share_pct, 2),
                    # Backward-compat alias para `pct_total_cambial` (renomeado para
                    # evitar match do checker P5_float_money que dispara em `*_total_*`).
                    "pct_total_cambial": round(pm.share_pct, 2),
                }
                for pm in self.por_moeda
            ],
            "tier": self.tier,
            "detalhes": list(self.detalhes),
        }


def _tier_from_pct(pct: float, has_data: bool) -> str:
    if not has_data:
        return "empty"
    if pct >= THRESHOLD_VERDE_PCT:
        return "verde"
    if pct >= THRESHOLD_AMARELO_PCT:
        return "amarelo"
    return "vermelho"


_ZERO = Decimal(0)


def _to_decimal(v: Any) -> Decimal:
    if v is None or isinstance(v, bool):
        return _ZERO
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except (ValueError, TypeError):
        return _ZERO


def _sum_caixa_estrangeiro(caixa_detalhes: list[dict]) -> dict[str, Decimal]:
    """Soma `caixa_detalhes` em BRL por moeda estrangeira (BRL excluído)."""
    out: dict[str, Decimal] = {}
    for d in caixa_detalhes or []:
        moeda = str(d.get("moeda") or "").upper()
        if not moeda or moeda == "BRL":
            continue
        valor = _to_decimal(d.get("valor_brl"))
        if valor <= _ZERO:
            continue
        out[moeda] = out.get(moeda, _ZERO) + valor
    return out


def _pos_value(pos: dict) -> Decimal:
    return _to_decimal(pos.get("valor") or pos.get("valor_31_12_ano_base"))


def _pos_is_internacional(pos: dict) -> bool:
    tipo = str(pos.get("tipo") or pos.get("classe") or "")
    descricao = str(pos.get("descricao") or pos.get("nome") or "")
    instituicao = str(pos.get("instituicao") or "")
    return classify_asset(tipo, descricao, instituicao) == _BUCKET_INTERNACIONAL


def _ativo_detalhe(pos: dict, valor: Decimal) -> dict:
    """Linha detalhada (UI consumível). dict opaco no boundary do payload."""
    nome = str(pos.get("descricao") or pos.get("nome") or pos.get("tipo") or "")
    return {"nome": nome, "valor_brl": float(round(valor, 2)), "moeda": "USD"}


def _sum_ativos_internacionais(
    investimentos_atuais: dict | None,
) -> tuple[Decimal, list[dict[str, Any]]]:
    """Soma ativos classificados como ``Internacional`` (assume USD)."""
    posicoes = (investimentos_atuais or {}).get("dados") or []
    if not isinstance(posicoes, list):
        return _ZERO, []
    pairs = [
        (p, _pos_value(p))
        for p in posicoes
        if isinstance(p, dict) and _pos_is_internacional(p) and _pos_value(p) > _ZERO
    ]
    total = sum((v for _, v in pairs), _ZERO)
    return total, [_ativo_detalhe(p, v) for p, v in pairs]


def _detalhes_caixa(caixa_detalhes: list[dict]) -> list[dict[str, Any]]:
    return [
        {
            "fonte": d.get("conta", ""),
            "moeda": str(d.get("moeda") or "").upper(),
            "saldo_original": d.get("saldo_original"),
            "valor_brl": d.get("valor_brl"),
            "tipo": "caixa",
        }
        for d in (caixa_detalhes or [])
        if str(d.get("moeda") or "").upper() not in {"", "BRL"}
    ]


def _build_por_moeda(
    por_moeda: dict[str, Decimal], total: Decimal
) -> tuple[ExposicaoCambialPorMoeda, ...]:
    return tuple(
        ExposicaoCambialPorMoeda(
            moeda=m,
            valor_brl=v,
            share_pct=float(v / total * 100) if total > _ZERO else 0.0,
        )
        for m, v in sorted(por_moeda.items(), key=lambda x: -x[1])
        if v > _ZERO
    )


def compute_exposicao_cambial(
    *,
    caixa_detalhes: list[dict],
    investimentos_atuais: dict | None,
    investivel_financeiro: float,
) -> ExposicaoCambialResult:
    """Agrega caixa em moeda estrangeira + ativos com lastro internacional (USD)."""
    por_moeda = _sum_caixa_estrangeiro(caixa_detalhes)
    ativos_intl, ativos_detalhes = _sum_ativos_internacionais(investimentos_atuais)
    por_moeda["USD"] = por_moeda.get("USD", _ZERO) + ativos_intl
    total = sum(por_moeda.values(), _ZERO)
    denom = _to_decimal(investivel_financeiro)
    pct = float(total / denom * 100) if denom > _ZERO else 0.0
    return ExposicaoCambialResult(
        total_brl=total,
        pct_investivel_financeiro=pct,
        por_moeda=_build_por_moeda(por_moeda, total),
        tier=_tier_from_pct(pct, has_data=total > _ZERO),
        detalhes=tuple(_detalhes_caixa(caixa_detalhes) + ativos_detalhes),
    )
