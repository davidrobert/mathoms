"""AlocacaoAlvoDeviationCalculator — desvio atual vs alvo v2 (7 classes AUVP, ADR-141 §Emenda 2026-07-08)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Optional

# Ordem canônica das chaves comparáveis — também é o tie-break do
# next-aporte (ADR-141 emenda item 3).
COMPARABLE_KEYS: tuple[str, ...] = ("renda_fixa", "acoes_br", "acoes_int", "fiis", "fora_alvo")

# Bucket ADR-193 → chave comparável. Caixa e Imóveis Investimento ficam
# fora da carteira líquida (ADR-141 emenda itens 1-2).
_BUCKET_TO_COMPARABLE: dict[str, str] = {
    "Renda Fixa": "renda_fixa",
    "Previdência": "renda_fixa",
    "Ações BR": "acoes_br",
    "Fundos": "acoes_br",
    "Internacional": "acoes_int",
    "FIIs": "fiis",
    "Cripto": "fora_alvo",
    "Outros": "fora_alvo",
}
_BUCKET_CAIXA = "Caixa"
_BUCKET_IMOVEIS = "Imóveis Investimento"

# Inputs v2 que agregam em cada chave comparável (renormalização exclui caixa_pct).
_ALVO_INPUTS_BY_COMPARABLE: dict[str, tuple[str, ...]] = {
    "renda_fixa": ("rf_pos_pct", "rf_pre_pct", "rf_ipca_pct"),
    "acoes_br": ("acoes_br_pct",),
    "acoes_int": ("acoes_int_pct",),
    "fiis": ("fiis_pct",),
    "fora_alvo": (),
}

SEVERITY_ALINHADO_MAX_PP = 2.0
SEVERITY_ATENCAO_MAX_PP = 5.0

AlvoInputs = Mapping[str, object]


def severity_for_desvio(desvio_pp: Optional[float] = None) -> str:
    if desvio_pp is None:
        return "neutro"
    magnitude = abs(desvio_pp)
    if magnitude <= SEVERITY_ALINHADO_MAX_PP:
        return "alinhado"
    if magnitude <= SEVERITY_ATENCAO_MAX_PP:
        return "atencao"
    return "rebalancear"


def _dec(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return Decimal("0")


def _pct_of(part: Decimal, whole: Decimal) -> float:
    if whole <= 0:
        return 0.0
    return float(part / whole * Decimal("100"))


def _round_or_none(value: Optional[float] = None) -> Optional[float]:
    return None if value is None else round(value, 2)


def _json_number(value: Decimal) -> float:
    # Wire JSON emite number (ADR-090 §consequências); Decimal em memória.
    return float(value.quantize(Decimal("0.01")))


@dataclass(frozen=True)
class AlocacaoComparableRow:
    classe: str
    valor_brl: Decimal
    componentes: tuple[str, ...]
    atual_pct: float
    alvo_pct: Optional[float]
    desvio_pp: Optional[float]
    severity: str

    def to_dict(self) -> dict:
        return {
            "classe": self.classe,
            "valor_brl": _json_number(self.valor_brl),
            "componentes": list(self.componentes),
            "atual_pct": round(self.atual_pct, 2),
            "alvo_pct": _round_or_none(self.alvo_pct),
            "desvio_pp": _round_or_none(self.desvio_pp),
            "severity": self.severity,
        }


@dataclass(frozen=True)
class AlocacaoCaixaInfo:
    """Linha informativa — caixa nunca entra no desvio (ADR-141 emenda item 1)."""

    valor_brl: Decimal
    atual_pct_patrimonio: float  # percentual sobre o patrimônio inteiro (adimensional)
    alvo_pct: Optional[float]
    excesso_pp: Optional[float]
    sinal_excesso: bool

    def to_dict(self) -> dict:
        return {
            "valor_brl": _json_number(self.valor_brl),
            "atual_pct_patrimonio": round(self.atual_pct_patrimonio, 2),
            "alvo_pct": _round_or_none(self.alvo_pct),
            "excesso_pp": _round_or_none(self.excesso_pp),
            "sinal_excesso": self.sinal_excesso,
        }


@dataclass(frozen=True)
class AlocacaoDeviationResult:
    comparaveis: tuple[AlocacaoComparableRow, ...]
    desvio_max_pct: Optional[float]
    next_aporte_classe: Optional[str]
    carteira_liquida_brl: Decimal
    caixa: AlocacaoCaixaInfo
    imoveis_fisicos_brl: Decimal
    has_alvo: bool
    rf_comparacao: str
    alvo_renormalizado_defensivo: bool

    def to_dict(self) -> dict:
        return {
            "comparaveis": [row.to_dict() for row in self.comparaveis],
            "desvio_max_pct": _round_or_none(self.desvio_max_pct),
            "next_aporte_classe": self.next_aporte_classe,
            "carteira_liquida_brl": _json_number(self.carteira_liquida_brl),
            "caixa": self.caixa.to_dict(),
            "imoveis_fisicos_brl": _json_number(self.imoveis_fisicos_brl),
            "has_alvo": self.has_alvo,
            "rf_comparacao": self.rf_comparacao,
            "alvo_renormalizado_defensivo": self.alvo_renormalizado_defensivo,
        }


@dataclass
class _Carteira:
    valores: dict[str, Decimal]
    componentes: dict[str, list[str]]
    caixa_brl: Decimal
    imoveis_brl: Decimal

    @property
    def liquida_brl(self) -> Decimal:
        return sum(self.valores.values(), Decimal("0"))


def _empty_carteira() -> _Carteira:
    return _Carteira(
        valores={key: Decimal("0") for key in COMPARABLE_KEYS},
        componentes={key: [] for key in COMPARABLE_KEYS},
        caixa_brl=Decimal("0"),
        imoveis_brl=Decimal("0"),
    )


def _ingest_classe(carteira: _Carteira, categoria: str, valor: Decimal) -> None:
    if categoria == _BUCKET_CAIXA:
        carteira.caixa_brl += valor
        return
    if categoria == _BUCKET_IMOVEIS:
        carteira.imoveis_brl += valor
        return
    key = _BUCKET_TO_COMPARABLE.get(categoria)
    if key is None:
        return
    carteira.valores[key] += valor
    carteira.componentes[key].append(categoria)


def _aggregate_carteira(tabela_classes: list[dict]) -> _Carteira:
    carteira = _empty_carteira()
    for row in tabela_classes or []:
        valor = _dec(row.get("valor"))
        if valor > 0:
            _ingest_classe(carteira, str(row.get("categoria") or ""), valor)
    return carteira


@dataclass(frozen=True)
class _AlvoNormalizado:
    por_comparable: dict[str, Optional[float]]
    caixa_pct: Optional[float]
    has_alvo: bool
    defensivo: bool


def _alvo_input_pct(alvo_inputs: AlvoInputs, key: str) -> Optional[float]:
    value = alvo_inputs.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _soma_alvo_investimento(alvo_inputs: AlvoInputs) -> float:
    campos = [c for keys in _ALVO_INPUTS_BY_COMPARABLE.values() for c in keys]
    return sum(_alvo_input_pct(alvo_inputs, c) or 0.0 for c in campos)


def _normalize_alvo(alvo_inputs: AlvoInputs) -> _AlvoNormalizado:
    """Renormaliza alvos de investimento excluindo caixa_pct (ADR-141 emenda item 1)."""
    declarados = [
        _alvo_input_pct(alvo_inputs, campo)
        for keys in _ALVO_INPUTS_BY_COMPARABLE.values()
        for campo in keys
    ]
    caixa_pct = _alvo_input_pct(alvo_inputs, "caixa_pct")
    has_alvo = any(v is not None for v in declarados) or caixa_pct is not None
    soma_investimento = _soma_alvo_investimento(alvo_inputs)
    soma_total = soma_investimento + (caixa_pct or 0.0)
    return _AlvoNormalizado(
        por_comparable=_normalized_targets(alvo_inputs, soma_investimento, has_alvo),
        caixa_pct=caixa_pct,
        has_alvo=has_alvo,
        defensivo=has_alvo and abs(soma_total - 100.0) > 0.01,
    )


def _normalized_targets(
    alvo_inputs: AlvoInputs, soma_investimento: float, has_alvo: bool
) -> dict[str, Optional[float]]:
    # caixa_pct = 100 → soma_investimento = 0 → carteira comparável vazia:
    # tudo null, inclusive fora_alvo (edge case da emenda item 1).
    if not has_alvo or soma_investimento <= 0:
        return {key: None for key in COMPARABLE_KEYS}
    out: dict[str, Optional[float]] = {"fora_alvo": 0.0}
    for key, campos in _ALVO_INPUTS_BY_COMPARABLE.items():
        if key == "fora_alvo":
            continue
        declarado = sum(_alvo_input_pct(alvo_inputs, c) or 0.0 for c in campos)
        out[key] = declarado / soma_investimento * 100.0
    return out


def _comparable_row(
    key: str, carteira: _Carteira, alvo_pct: Optional[float] = None
) -> AlocacaoComparableRow:
    atual_pct = _pct_of(carteira.valores[key], carteira.liquida_brl)
    desvio = None if alvo_pct is None else atual_pct - alvo_pct
    return AlocacaoComparableRow(
        classe=key,
        valor_brl=carteira.valores[key],
        componentes=tuple(carteira.componentes[key]),
        atual_pct=atual_pct,
        alvo_pct=alvo_pct,
        desvio_pp=desvio,
        severity=severity_for_desvio(desvio),
    )


def _build_comparable_rows(
    carteira: _Carteira, alvo: _AlvoNormalizado
) -> tuple[AlocacaoComparableRow, ...]:
    rows = [_comparable_row(key, carteira, alvo.por_comparable[key]) for key in COMPARABLE_KEYS]
    rows.sort(key=lambda r: -abs(r.desvio_pp) if r.desvio_pp is not None else 1)
    return tuple(rows)


def _desvio_max(rows: tuple[AlocacaoComparableRow, ...]) -> Optional[float]:
    desvios = [abs(r.desvio_pp) for r in rows if r.desvio_pp is not None]
    return max(desvios) if desvios else None


def _next_aporte(rows: tuple[AlocacaoComparableRow, ...]) -> Optional[str]:
    """Classe mais subalocada; tie-break pela ordem canônica (emenda item 3)."""
    candidatas = [
        r for r in rows if r.desvio_pp is not None and r.desvio_pp < 0 and r.classe != "fora_alvo"
    ]
    if not candidatas:
        return None
    candidatas.sort(key=lambda r: (r.desvio_pp, COMPARABLE_KEYS.index(r.classe)))
    return candidatas[0].classe


def _build_caixa_info(
    carteira: _Carteira,
    total_brl: Decimal,
    caixa_alvo_pct: Optional[float] = None,
    reserva_completa: Optional[bool] = None,
) -> AlocacaoCaixaInfo:
    # Sinal unidirecional de excesso; reserva incompleta (ou desconhecida)
    # silencia (ADR-141 emenda item 1 — precedência do goal de reserva).
    atual_pct = _pct_of(carteira.caixa_brl, total_brl)
    excesso = None
    if caixa_alvo_pct is not None and atual_pct > caixa_alvo_pct:
        excesso = atual_pct - caixa_alvo_pct
    return AlocacaoCaixaInfo(
        valor_brl=carteira.caixa_brl,
        atual_pct_patrimonio=atual_pct,
        alvo_pct=caixa_alvo_pct,
        excesso_pp=excesso,
        sinal_excesso=bool(excesso is not None and reserva_completa is True),
    )


class AlocacaoAlvoDeviationCalculator:
    """Compara carteira observada (10 buckets ADR-193) com alvo v2 (7 classes AUVP)."""

    def calculate(
        self,
        tabela_classes: list[dict],
        alvo_inputs: Optional[AlvoInputs] = None,
        reserva_completa: Optional[bool] = None,
    ) -> AlocacaoDeviationResult:
        carteira = _aggregate_carteira(tabela_classes)
        alvo = _normalize_alvo(alvo_inputs or {})
        rows = _build_comparable_rows(carteira, alvo)
        total_brl = carteira.liquida_brl + carteira.caixa_brl + carteira.imoveis_brl
        caixa = _build_caixa_info(carteira, total_brl, alvo.caixa_pct, reserva_completa)
        return _assemble_result(carteira, alvo, rows, caixa)


def _assemble_result(
    carteira: _Carteira,
    alvo: _AlvoNormalizado,
    rows: tuple[AlocacaoComparableRow, ...],
    caixa: AlocacaoCaixaInfo,
) -> AlocacaoDeviationResult:
    return AlocacaoDeviationResult(
        comparaveis=rows,
        desvio_max_pct=_desvio_max(rows),
        next_aporte_classe=_next_aporte(rows),
        carteira_liquida_brl=carteira.liquida_brl,
        caixa=caixa,
        imoveis_fisicos_brl=carteira.imoveis_brl,
        has_alvo=alvo.has_alvo,
        rf_comparacao="agregada",
        alvo_renormalizado_defensivo=alvo.defensivo,
    )
