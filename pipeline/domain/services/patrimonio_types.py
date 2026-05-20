"""Value objects + helpers puros para ``PatrimonioCalculator`` (A6d.3.3 — ADR-100).

Módulo sem dependência de globals: cada função recebe explicitamente a config
de que precisa (:class:`MemberIdentity`, :class:`PatrimonioConfig`).

A hierarquia de arquivos:

- ``patrimonio_types.py`` — value objects + extractors triviais (este módulo)
- ``patrimonio_resolvers.py`` — resolvers de baseline em 4 formatos
- ``patrimonio_calculator.py`` — ``PatrimonioCalculator.calculate(inputs) -> dict``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal, Mapping


def safe_float(val: Any, default: float = 0.0) -> float:
    """Converte ``val`` para ``float``; retorna ``default`` se falhar."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# =============================================================================
# Value objects
# =============================================================================


@dataclass(frozen=True)
class MemberIdentity:
    """Identidade dos dois membros da família (titular + cônjuge).

    Substitui os globals ``_TITULAR_KEY``/``_CONJUGE_KEY``/``_TITULAR_NOME``/
    ``_CONJUGE_NOME``/``_KEY_INV_TITULAR``/``_KEY_INV_CONJUGE`` do script
    legado ``scripts/e5_analyze.py``.
    """

    titular_key: str
    conjuge_key: str
    titular_nome: str
    conjuge_nome: str

    @property
    def key_inv_titular(self) -> str:
        return f"investimentos_{self.titular_key}"

    @property
    def key_inv_conjuge(self) -> str:
        return f"investimentos_{self.conjuge_key}"


@dataclass(frozen=True)
class PatrimonioConfig:
    """Config completa do :class:`PatrimonioCalculator`."""

    members: MemberIdentity

    # ADR-215 §1: mapping `property_id` → `classification` enum
    # (residencia_principal | uso_pessoal | locado | comercial | especulacao
    # | desconhecido). Vem do DB (`workspace_property_overrides`) via
    # `DBPropertyOverridesResolver` + `WorkspaceContext`. Empty dict ↔
    # workspace ainda não classificou nenhum imóvel — todos caem em cat_2.
    property_classification_overrides: dict[str, str] = field(default_factory=dict)

    # ADR-142 §Decisão (per-workspace via ADR-222): se `True`, `cat_2` (imóveis
    # de renda — somente classificações `locado` ou `comercial`) entra em
    # ``investivel_efetivo``; se `False`, fica fora (apenas cat_3+4+5+6 =
    # `investivel_financeiro`). ``uso_pessoal`` / ``especulacao`` /
    # ``desconhecido`` nunca entram, independente do toggle (Perini/Cerbasi).
    # Default ``True`` preserva retro-compat com `pipeline.json:14` legado.
    include_real_estate_in_if: bool = True


@dataclass(frozen=True)
class CaixaDetalhe:
    """Linha de saldo em caixa ou moeda estrangeira (output legado)."""

    conta: str
    moeda: str
    saldo_original: float
    valor_brl: float
    tipo: str  # "caixa" | "moeda_estrangeira"

    def to_dict(self) -> dict:
        return {
            "conta": self.conta,
            "moeda": self.moeda,
            "saldo_original": round(self.saldo_original, 2),
            "valor_brl": round(self.valor_brl, 2),
            "tipo": self.tipo,
        }


@dataclass(frozen=True)
class MarketValueResolution:
    """Resolução de valor de mercado para um imóvel (ADR-227 §D4)."""

    property_id: str
    valor_brl: Decimal
    source: Literal["mercado"]
    valuation_date: date
    staleness_days: int


@dataclass(frozen=True)
class RealEstateValuationContext:
    """Contexto pré-carregado (ADR-227 §D4); dict de market_values + debts evita I/O no domínio (ADR-111 stateless)."""

    market_values: Mapping[str, MarketValueResolution] = field(default_factory=dict)
    debts_by_property: Mapping[str, Decimal] = field(default_factory=dict)
    today: date = field(default_factory=date.today)


@dataclass(frozen=True)
class PatrimonioInputs:
    """Inputs completos para ``PatrimonioCalculator.calculate``.

    O adapter carrega tudo via ``ArtifactStore`` + taxas.json + institutions.json
    e monta este value object. A calculadora opera pura sobre ele.
    """

    baseline: dict
    investimentos_atuais: dict | None = None
    caixa_total_brl: float = 0.0
    caixa_detalhes: list[CaixaDetalhe] = field(default_factory=list)
    valuation_context: RealEstateValuationContext | None = None

    @property
    def has_current_positions(self) -> bool:
        return (
            self.investimentos_atuais is not None
            and isinstance(self.investimentos_atuais, dict)
            and len(self.investimentos_atuais.get("dados", [])) > 0
        )


# =============================================================================
# Extractors triviais — pure value extraction with fallback keys
# =============================================================================


def imovel_valor(imovel: dict) -> float:
    """Valor de imóvel tentando chaves alternativas."""
    for key in ("valor_31_12_ano_base", "valor_irpf", "valor"):
        v = imovel.get(key)
        if v is not None:
            return safe_float(v)
    return 0.0


def imovel_property_id(imovel: dict) -> str | None:
    """Retorna `property_id` (ADR-215 P2) anexado ao imóvel pelo E1.5c, ou None."""
    pid = imovel.get("property_id")
    if isinstance(pid, str) and pid:
        return pid
    return None


def imovel_desc(imovel: dict) -> str:
    """Descrição de imóvel (lowercase) tentando múltiplas chaves.

    Tenta ``description``, ``descricao``, ``endereco`` e
    ``dados_completos.imovel`` — reproduz a lógica de ``_imovel_desc`` legacy.
    """
    desc = imovel.get("description") or imovel.get("descricao") or ""
    if not desc:
        desc = imovel.get("endereco") or ""
    if not desc:
        dc = imovel.get("dados_completos", {})
        if isinstance(dc, dict):
            desc = dc.get("imovel", "") or ""
    return desc.lower()


def veiculo_valor(veiculo: dict) -> float:
    """Valor de veículo tentando chaves alternativas."""
    for key in ("valor_31_12_ano_base", "valor_irpf", "valor"):
        v = veiculo.get(key)
        if v is not None:
            return safe_float(v)
    return 0.0


def investimento_valor(inv: Any) -> float:
    """Valor de investimento — aceita dict ou escalar.

    Um investimento pode ser ``{"valor_31_12_ano_base": 1000.0}`` ou um
    float puro (em formatos v1.5 consolidated que usam ``contas_bancarias``
    como escalar em vez de lista).
    """
    if isinstance(inv, dict):
        for key in ("valor_31_12_ano_base", "valor"):
            v = inv.get(key)
            if v is not None:
                return safe_float(v)
    return safe_float(inv)


def get_bens(member: dict) -> dict:
    """Retorna sub-dict ``bens`` (layout aninhado) ou o próprio membro (flat)."""
    if "bens" in member and isinstance(member["bens"], dict):
        return member["bens"]
    return member
