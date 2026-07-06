"""``EmergencyReserveCalculator`` — reserva de emergência conforme FORMULAS.md §Reserva (A28.l1).

Contrato (FORMULAS.md §Reserva de emergência + [[ADR-306]] §D4):

- **Numerador** ``reserva_liquida_disponivel``: liquidez imediata de baixo
  risco — filtro em :mod:`pipeline.domain.services.reserva_liquidez`
  (buckets Caixa + Renda Fixa; caixa ME só com finalidade explícita =
  reserva via ``incluir_caixa_me``, default False — o parecer pede a
  finalidade ao cliente).
- **Denominador** ``custo_essencial_mensal``: média mensal das 9 categorias
  canônicas (``scoring.json:reserva_emergencia._base_calculo``) na janela
  canônica de 12 meses documentados. Sem categoria essencial documentada,
  fallback rotulado (``base_denominador: "despesa_total"``) para a despesa
  mensal média da mesma janela.
- **Alvo** ``meses_alvo`` por composição de renda (CLT 6 · mista 12 ·
  PJ-dominante 18); ``avaliacao_liquidity`` "Excessiva" exige cobertura
  acima do alvo do perfil.

Interno em ``Decimal`` (ADR-090); serializa float no payload por paridade
com o shape legado do E5 (mesmo padrão de ``Janela12m``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from pipeline.domain.services.asset_classifier import merge_asset_keywords
from pipeline.domain.services.patrimonio_types import MemberIdentity, safe_float
from pipeline.domain.services.reserva_liquidez import (
    ReservaLiquida,
    build_reserva_liquida,
)

_ZERO = Decimal("0")

# Thresholds de composição de renda (scoring.json §meses_alvo_por_perfil_renda,
# campo ``criterio``): PJ ≥60% dominante; ≥30% relevante; ≥10% mista.
_PJ_DOMINANTE_MIN_PCT = 60.0
_PJ_RELEVANTE_MIN_PCT = 30.0
_RENDA_MISTA_MIN_PCT = 10.0

_DEFAULT_MESES_ALVO: dict[str, int] = {
    "clt_estavel": 6,
    "clt_unica_fonte": 12,
    "renda_mista": 12,
    "pj_relevante": 12,
    "pj_dominante": 18,
}
# Perfil sem receita PJ/CLT identificável — alvo conservador de renda mista.
_PERFIL_FALLBACK = "renda_mista"


def _dec(value: object) -> Decimal:
    return Decimal(str(safe_float(value)))


def _legacy_number(value: Decimal) -> float:
    """Decimal → float 2 casas no boundary do payload (paridade shape legado)."""
    return float(value.quantize(Decimal("0.01")))


@dataclass(frozen=True)
class ReservaClassificacao:
    """Faixa de avaliação de reserva (mínimo de meses → label + ação)."""

    minimo_meses: int
    label: str
    acao: str = ""


@dataclass(frozen=True)
class ReservaEmergenciaConfig:
    """Config do :class:`EmergencyReserveCalculator`."""

    members: MemberIdentity
    niveis_meses: tuple[int, ...] = (6, 12)
    classificacao: tuple[ReservaClassificacao, ...] = (
        ReservaClassificacao(minimo_meses=12, label="Excelente"),
        ReservaClassificacao(minimo_meses=6, label="Adequada"),
        ReservaClassificacao(minimo_meses=0, label="Insuficiente"),
    )
    meses_alvo_por_perfil: Mapping[str, int] = field(
        default_factory=lambda: dict(_DEFAULT_MESES_ALVO)
    )
    # Caixa ME só compõe reserva com finalidade explícita = reserva.
    incluir_caixa_me: bool = False
    keywords_por_classe: Mapping[str, tuple[str, ...]] | None = None

    @classmethod
    def from_scoring_json(cls, scoring: dict, members: MemberIdentity) -> "ReservaEmergenciaConfig":
        """Constrói config a partir de ``config/scoring.json`` (estrutura legada)."""
        reserva_cfg = scoring.get("reserva_emergencia", {}) or {}
        return cls(
            members=members,
            niveis_meses=tuple(int(n) for n in (reserva_cfg.get("niveis_meses") or [6, 12])),
            classificacao=_classificacao_from_scoring(reserva_cfg),
            meses_alvo_por_perfil=_meses_alvo_from_scoring(reserva_cfg),
            keywords_por_classe=merge_asset_keywords(scoring),
        )

    def meses_alvo(self, perfil: str) -> int:
        return int(
            self.meses_alvo_por_perfil.get(
                perfil, _DEFAULT_MESES_ALVO.get(perfil, _DEFAULT_MESES_ALVO[_PERFIL_FALLBACK])
            )
        )


def _classificacao_from_scoring(reserva_cfg: dict) -> tuple[ReservaClassificacao, ...]:
    classif_raw = reserva_cfg.get("classificacao") or [
        {"minimo_meses": 12, "label": "Excelente"},
        {"minimo_meses": 6, "label": "Adequada"},
        {"minimo_meses": 0, "label": "Insuficiente"},
    ]
    return tuple(
        ReservaClassificacao(
            minimo_meses=int(faixa.get("minimo_meses", 0)),
            label=str(faixa.get("label", "")),
            acao=str(faixa.get("acao", "")),
        )
        for faixa in classif_raw
    )


def _meses_alvo_from_scoring(reserva_cfg: dict) -> dict[str, int]:
    base_calc = reserva_cfg.get("_base_calculo") or {}
    perfis_raw = base_calc.get("meses_alvo_por_perfil_renda") or {}
    merged = dict(_DEFAULT_MESES_ALVO)
    for perfil, spec in perfis_raw.items():
        meses = spec.get("meses") if isinstance(spec, dict) else spec
        if meses is not None:
            merged[str(perfil)] = int(safe_float(meses))
    return merged


# =============================================================================
# Resultados intermediários (Decimal — ADR-090)
# =============================================================================


@dataclass(frozen=True)
class _BaseMensal:
    valor: Decimal
    custo_essencial: Decimal
    base_denominador: str  # "custo_essencial" | "despesa_total"
    janela: str
    janela_meses: int


@dataclass(frozen=True)
class _PerfilRenda:
    perfil: str
    receita_pj_pct: float | None
    meses_alvo: int


class EmergencyReserveCalculator:
    """Calcula reserva de emergência + avaliação de cobertura (FORMULAS.md §Reserva).

    Uso::

        config = ReservaEmergenciaConfig.from_scoring_json(scoring, identity)
        calc = EmergencyReserveCalculator(config)
        report = calc.calculate(
            fluxo=fluxo,
            patrimonio=patrimonio,
            investimentos_atuais=investimentos_raw,
            bens_por_membro={identity.titular_key: titular_data, ...},
        )
    """

    def __init__(self, config: ReservaEmergenciaConfig) -> None:
        self._config = config

    def calculate(
        self,
        *,
        fluxo: dict,
        patrimonio: dict,
        investimentos_atuais: dict | None = None,
        bens_por_membro: Mapping[str, dict] | None = None,
    ) -> dict:
        """Produz o bloco ``reserva_emergencia`` do payload E5."""
        base = _resolve_base_mensal(fluxo)
        liquidez = build_reserva_liquida(
            patrimonio,
            investimentos_atuais,
            bens_por_membro,
            identity=self._config.members,
            keywords=self._config.keywords_por_classe,
        )
        perfil = self._resolve_perfil(fluxo)
        return self._build_payload(base, liquidez, perfil)

    # -- Perfil de renda --------------------------------------------------------

    def _resolve_perfil(self, fluxo: dict) -> _PerfilRenda:
        por_fonte = (fluxo or {}).get("por_fonte") or {}
        pj = safe_float(por_fonte.get("receita_pj", 0))
        clt = safe_float(por_fonte.get("receita_clt", 0))
        base = pj + clt
        if base <= 0:
            return _PerfilRenda(
                perfil="indefinido",
                receita_pj_pct=None,
                meses_alvo=self._config.meses_alvo(_PERFIL_FALLBACK),
            )
        pct = pj / base * 100
        perfil = _perfil_por_pct(pct)
        return _PerfilRenda(
            perfil=perfil, receita_pj_pct=round(pct, 2), meses_alvo=self._config.meses_alvo(perfil)
        )

    # -- Payload ----------------------------------------------------------------

    def _build_payload(
        self, base: _BaseMensal, liquidez: ReservaLiquida, perfil: _PerfilRenda
    ) -> dict:
        componentes = liquidez.componentes(
            incluir_caixa_me=self._config.incluir_caixa_me,
            solo=not self._config.members.conjuge_key,
        )
        total_liquida = sum(componentes.values(), _ZERO)
        cobertura_meses = float(total_liquida / base.valor) if base.valor > 0 else 0.0
        return {
            **self._payload_base(base, perfil, total_liquida),
            "composicao_liquida": _composicao_dict(componentes, total_liquida, cobertura_meses),
            "excluido_da_reserva": self._build_excluidos(liquidez),
            "total_liquida": _legacy_number(total_liquida),
            "cobertura_meses": round(cobertura_meses, 1),
            "avaliacao_liquidity": self._classify(cobertura_meses, perfil.meses_alvo),
            "niveis": [f"{n} meses" for n in sorted(self._config.niveis_meses)],
        }

    def _payload_base(self, base: _BaseMensal, perfil: _PerfilRenda, total: Decimal) -> dict:
        alvo_brl = base.valor * perfil.meses_alvo
        return {
            "despesas_mensais": _legacy_number(base.valor),
            "custo_essencial_mensal": _legacy_number(base.custo_essencial),
            "base_denominador": base.base_denominador,
            "janela": base.janela,
            "janela_meses": base.janela_meses,
            "perfil_renda": perfil.perfil,
            "receita_pj_pct": perfil.receita_pj_pct,
            "meses_alvo": perfil.meses_alvo,
            "alvo_brl": _legacy_number(alvo_brl),
            "gap_brl": _legacy_number(max(_ZERO, alvo_brl - total)),
            "nivel_6_meses": _legacy_number(base.valor * 6),
            "nivel_12_meses": _legacy_number(base.valor * 12),
        }

    def _build_excluidos(self, liquidez: ReservaLiquida) -> dict:
        caixa_me = _ZERO if self._config.incluir_caixa_me else liquidez.caixa_me
        return {
            "investimentos_nao_liquidos": _legacy_number(liquidez.investimentos_nao_liquidos()),
            "caixa_moeda_estrangeira": _legacy_number(caixa_me),
            "caixa_nao_classificado": _legacy_number(liquidez.caixa_nao_classificado),
        }

    def _classify(self, cobertura_meses: float, meses_alvo: int) -> str:
        """Faixas do scoring.json; "Excessiva" (realocar_excedente) exige
        cobertura acima do alvo do perfil (A28.l1 — nunca induzir
        desmobilização de reserva abaixo do alvo)."""
        ordered = sorted(
            self._config.classificacao,
            key=lambda f: f.minimo_meses,
            reverse=True,
        )
        for faixa in ordered:
            if cobertura_meses < faixa.minimo_meses:
                continue
            if faixa.acao == "realocar_excedente" and cobertura_meses <= meses_alvo:
                continue
            return faixa.label
        return "Insuficiente"


# =============================================================================
# Helpers puros
# =============================================================================


def _resolve_base_mensal(fluxo: dict) -> _BaseMensal:
    """Denominador canônico — janela 12m (ADR-306 §D4), essencial-first."""
    j12m = (fluxo or {}).get("janela_12m") or {}
    if isinstance(j12m, dict) and j12m.get("despesa_mensal_media") is not None:
        return _base_from_window(
            j12m, janela="12m", janela_meses=int(safe_float(j12m.get("n_meses", 0)))
        )
    src = fluxo or {}
    return _base_from_window(
        src, janela="full", janela_meses=int(safe_float(src.get("janela_meses", 0)))
    )


def _base_from_window(window: dict, *, janela: str, janela_meses: int) -> _BaseMensal:
    essencial = _dec(window.get("despesa_mensal_essencial", 0))
    if essencial > 0:
        return _BaseMensal(
            valor=essencial,
            custo_essencial=essencial,
            base_denominador="custo_essencial",
            janela=janela,
            janela_meses=janela_meses,
        )
    return _BaseMensal(
        valor=_dec(window.get("despesa_mensal_media", 0)),
        custo_essencial=_ZERO,
        base_denominador="despesa_total",
        janela=janela,
        janela_meses=janela_meses,
    )


def _perfil_por_pct(pj_pct: float) -> str:
    if pj_pct >= _PJ_DOMINANTE_MIN_PCT:
        return "pj_dominante"
    if pj_pct >= _PJ_RELEVANTE_MIN_PCT:
        return "pj_relevante"
    if pj_pct >= _RENDA_MISTA_MIN_PCT:
        return "renda_mista"
    # clt_estavel (6 meses) exige ≥2 fontes CLT independentes — contagem de
    # fontes não disponível no fluxo v1; assume a variante conservadora.
    return "clt_unica_fonte"


def _composicao_dict(
    componentes: Mapping[str, Decimal], total_liquida: Decimal, cobertura_meses: float
) -> dict:
    composicao: dict[str, float] = {k: _legacy_number(v) for k, v in componentes.items()}
    composicao["total_liquido"] = _legacy_number(total_liquida)
    composicao["cobertura_meses"] = round(cobertura_meses, 1)
    return composicao
