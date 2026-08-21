"""ExposicaoCambialAnalyzer — agrega patrimônio com lastro em moeda estrangeira (Bloco G plan/RESIDENCIA_E_USO; co-design 2026-05-18; threshold canônico verde >=10% / amarelo 5-10% / vermelho <5%; denominador investivel_financeiro)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from pipeline.domain.services.asset_classifier import classify_asset
from pipeline.domain.services.conversao_me import infer_declared_me_currency

# ADR-193 + co-design G: bucket "Internacional" = lastro forte.
_BUCKET_INTERNACIONAL = "Internacional"

# Custodiantes estrangeiros ([[ADR-400]]). Estavam como keyword de classe no
# `asset_classifier`, onde respondiam à pergunta errada: custódia diz QUEM guarda,
# não O QUE é o ativo. Aqui a pergunta é lastro cambial — e para ela o custodiante
# é resposta legítima. Lista explícita e nomeada no módulo que faz a pergunta.
_CUSTODIA_ESTRANGEIRA: tuple[str, ...] = ("wise", "bofa", "bank of america")

# Tier de alerta (financial-planner co-design 2026-05-18). Trade-off:
# limiar único sem perfil de risco; conservadorismo Perini > otimismo.
#
# A banda mede PISO DE PROTEÇÃO (estoque), NÃO alvo de alocação (ADR-403). A
# faixa 20–30% USD da ADR-224 §6 é alvo de carteira e tem dono próprio —
# `acoes_int`, no comparativo de alocação. Sem a separação declarada, o card
# dizia "verde/adequado" enquanto o comparativo prescrevia compra.
THRESHOLD_VERDE_PCT = 10.0
THRESHOLD_AMARELO_PCT = 5.0

_DONO_PRESCRICAO_ALOCACAO = "acoes_int"

# v1 = só caixa em moeda estrangeira; v2 = caixa FX + carteira com lastro
# estrangeiro (elegibilidade por ATIVO via `lastro_moeda`, ADR-224). O marcador
# nasce ANTES da mudança de definição: sem ele não há como saber, depois, qual
# fronteira uma série de tiers atravessou.
DEFINICAO_VERSAO_CAIXA_FX = 1
DEFINICAO_VERSAO_ECONOMICA = 2
DEFINICAO_VERSAO_CORRENTE = DEFINICAO_VERSAO_CAIXA_FX


class Cobertura(str, Enum):
    """Quanto do componente o run conseguiu medir — não quanto ele vale."""

    apurado = "apurado"
    parcial = "parcial"
    indeterminado = "indeterminado"


@dataclass(frozen=True)
class ComponenteExposicao:
    """Um componente nomeado da exposição, com a cobertura da própria medida."""

    valor_brl: Decimal
    cobertura: Cobertura

    def to_dict(self) -> dict:
        return {"valor_brl": float(round(self.valor_brl, 2)), "cobertura": self.cobertura.value}


@dataclass(frozen=True)
class ReferenciaBanda:
    """Contra o que o tier mede — para o consumidor nunca ler "verde" como meta."""

    tipo: str = "piso_protecao"
    verde_min_pct: float = THRESHOLD_VERDE_PCT
    amarelo_min_pct: float = THRESHOLD_AMARELO_PCT
    dono_prescricao_alocacao: str = _DONO_PRESCRICAO_ALOCACAO

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "verde_min_pct": self.verde_min_pct,
            "amarelo_min_pct": self.amarelo_min_pct,
            "dono_prescricao_alocacao": self.dono_prescricao_alocacao,
        }


@dataclass(frozen=True)
class ExposicaoCambialPorMoeda:
    """Soma por moeda específica (USD, EUR, etc.) em BRL equivalente (Decimal ADR-090)."""

    moeda: str
    valor_brl: Decimal
    # percentage — share dentro da exposição cambial total (não-monetário; rate)
    share_pct: float


# `pct_total_cambial` é alias backward-compat de `share_pct` (renomeado para
# evitar match do checker P5_float_money, que dispara em `*_total_*`).
def _moeda_dict(pm: "ExposicaoCambialPorMoeda") -> dict:
    return {
        "moeda": pm.moeda,
        "valor_brl": float(round(pm.valor_brl, 2)),
        "share_pct": round(pm.share_pct, 2),
        "pct_total_cambial": round(pm.share_pct, 2),
    }


@dataclass(frozen=True)
class ExposicaoCambialResult:
    """Agregado: exposição cambial total + breakdown por moeda + tier."""

    total_brl: Decimal
    pct_investivel_financeiro: float  # percentage
    por_moeda: tuple[ExposicaoCambialPorMoeda, ...] = ()
    # `indeterminado` quando algum componente não foi apurado — ver `_tier`.
    tier: str = "vermelho"
    # Linhas detalhadas (conta + ativo) que compõem a exposição — usado no card.
    detalhes: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    componentes: dict[str, ComponenteExposicao] = field(default_factory=dict)
    definicao_versao: int = DEFINICAO_VERSAO_CORRENTE
    referencia_banda: ReferenciaBanda = field(default_factory=ReferenciaBanda)

    def to_dict(self) -> dict:
        return {
            "definicao_versao": self.definicao_versao,
            "componentes": {k: c.to_dict() for k, c in self.componentes.items()},
            "referencia_banda": self.referencia_banda.to_dict(),
            "total_brl": float(round(self.total_brl, 2)),
            "pct_investivel_financeiro": round(self.pct_investivel_financeiro, 2),
            "por_moeda": [_moeda_dict(pm) for pm in self.por_moeda],
            "tier": self.tier,
            "detalhes": list(self.detalhes),
        }


# Cobertura incompleta suprime o VEREDITO, não a medida: `total_brl` e o `pct`
# continuam publicados como PISO. Tier sobre soma parcial afirma "você está
# protegido nesta faixa" sobre numerador que o run não fechou — e o erro é
# assimétrico: superestimar diz "está protegido" a quem não está.
def _tier(pct: float, has_data: bool, componentes: dict[str, ComponenteExposicao]) -> str:
    if any(c.cobertura is not Cobertura.apurado for c in componentes.values()):
        return "indeterminado"
    return _tier_from_pct(pct, has_data)


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
    """Soma caixa ME em BRL por moeda. Inclui IRPF já-em-BRL (ADR-390)."""
    out: dict[str, Decimal] = {}
    for d in caixa_detalhes or []:
        if not _is_caixa_me(d):
            continue
        valor = _to_decimal(d.get("valor_brl"))
        if valor <= _ZERO:
            continue
        moeda = _moeda_exposicao(d)
        out[moeda] = out.get(moeda, _ZERO) + valor
    return out


def _is_caixa_me(d: dict) -> bool:
    if d.get("tipo") == "moeda_estrangeira_irpf":
        return True
    moeda = str(d.get("moeda") or "").upper()
    return bool(moeda) and moeda != "BRL"


def _moeda_exposicao(d: dict) -> str:
    if d.get("tipo") == "moeda_estrangeira_irpf":
        return infer_declared_me_currency(str(d.get("conta") or "")) or "ME"
    return str(d.get("moeda") or "").upper()


def _pos_value(pos: dict) -> Decimal:
    # RV2-08: campo canônico de valor da posição E4 = `valor_atual`
    # (investments_consolidator); `valor`/`valor_31_12` só em posições baseline
    # legadas. Sem esta chain toda posição lia 0 (V1 é instant-render, não
    # autoritativo — V2/lastro_resolver é a fonte de verdade, ADR-224 §5).
    return _to_decimal(
        pos.get("valor_atual")
        or pos.get("valor_total")
        or pos.get("valor")
        or pos.get("valor_31_12_ano_base")
    )


def _tem_custodia_estrangeira(instituicao: str) -> bool:
    agulha = instituicao.lower().replace("_", " ").replace("-", " ")
    return any(c in agulha for c in _CUSTODIA_ESTRANGEIRA)


# De-dup POR CONSTRUÇÃO (ADR-403): caixa_fx e carteira são disjuntos. A mesma
# conta em moeda estrangeira casa `_is_caixa_me` E — desde a [[ADR-400]] — os DOIS
# gatilhos de carteira: a keyword "moeda estrangeira" do bucket `Internacional` e
# o custodiante. Somar caixa e carteira sem esta guarda infla o KPI e vira dano de
# sinal ("você já está protegido" para quem não está).
def _pos_e_caixa_fx(pos: dict) -> bool:
    return _is_caixa_me(pos)


def _pos_is_internacional(pos: dict) -> bool:
    """Classe internacional OU custodiante estrangeiro — duas perguntas distintas."""
    if _pos_e_caixa_fx(pos):
        return False
    tipo = str(pos.get("tipo") or pos.get("classe") or "")
    descricao = str(pos.get("descricao") or pos.get("nome") or "")
    if classify_asset(tipo, descricao) == _BUCKET_INTERNACIONAL:
        return True
    return _tem_custodia_estrangeira(str(pos.get("instituicao") or ""))


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
            "moeda": _moeda_exposicao(d),
            "saldo_original": d.get("saldo_original"),
            "valor_brl": d.get("valor_brl"),
            "tipo": "caixa",
        }
        for d in (caixa_detalhes or [])
        if _is_caixa_me(d)
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


# v1 soma apenas `caixa_fx`: a carteira é publicada como OBSERVACIONAL, porque o
# universo que ela lê (`investimentos_atuais["dados"]`, posições atuais do E4)
# não é o que alimenta a tabela de classes (`irpf_bens`) — o braço contribuía
# zero sem dizer que não mediu.
def _pct_sobre(total: Decimal, investivel_financeiro: Any) -> float:
    denom = _to_decimal(investivel_financeiro)
    return float(total / denom * 100) if denom > _ZERO else 0.0


def _componentes(caixa: Decimal, carteira: Decimal) -> dict[str, ComponenteExposicao]:
    return {
        "caixa_fx": ComponenteExposicao(caixa, Cobertura.apurado),
        "carteira_lastro_estrangeiro": ComponenteExposicao(carteira, Cobertura.indeterminado),
    }


def compute_exposicao_cambial(
    *,
    caixa_detalhes: list[dict],
    investimentos_atuais: dict | None,
    investivel_financeiro: float,
) -> ExposicaoCambialResult:
    """Exposição ECONÔMICA em dois componentes nomeados, com cobertura própria."""
    por_moeda = _sum_caixa_estrangeiro(caixa_detalhes)
    total = sum(por_moeda.values(), _ZERO)  # v1: só o APURADO entra no total
    carteira, ativos_detalhes = _sum_ativos_internacionais(investimentos_atuais)
    componentes = _componentes(total, carteira)
    pct = _pct_sobre(total, investivel_financeiro)
    return ExposicaoCambialResult(
        total_brl=total,
        pct_investivel_financeiro=pct,
        por_moeda=_build_por_moeda(por_moeda, total),
        tier=_tier(pct, has_data=total > _ZERO, componentes=componentes),
        detalhes=tuple(_detalhes_caixa(caixa_detalhes) + ativos_detalhes),
        componentes=componentes,
    )
