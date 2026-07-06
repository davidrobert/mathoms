"""``EmergencyReserveCalculator`` — reserva de emergência conforme FORMULAS.md §Reserva (A28.l1).

Contrato (FORMULAS.md §Reserva de emergência + [[ADR-306]] §D4):

- **Numerador** ``reserva_liquida_disponivel``: liquidez imediata de baixo
  risco — buckets ``Caixa`` + ``Renda Fixa`` (ADR-193) dos itens de
  investimento por membro + caixa BRL de E3. Ações/FII/exterior/cripto/
  fundos/previdência ficam FORA. Caixa em moeda estrangeira só entra com
  finalidade explícita = reserva (``incluir_caixa_me``, default False —
  o parecer pede a finalidade ao cliente).
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

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from pipeline.domain.services.asset_classifier import (
    classify_asset,
    merge_asset_keywords,
)
from pipeline.domain.services.patrimonio_types import (
    MemberIdentity,
    get_bens,
    investimento_valor,
    safe_float,
)

_ZERO = Decimal("0")

# Buckets ADR-193 elegíveis como reserva (liquidez D+0/D+1, baixo risco).
_LIQUID_BUCKETS = frozenset({"Caixa", "Renda Fixa"})
# Renda fixa SEM liquidez diária (crédito securitizado / mercado secundário).
_ILLIQUID_RF_RE = re.compile(r"debentur|\bcra\b|\bcri\b")

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
class _LiquidezMembro:
    valor_liquido: Decimal
    valor_excluido: Decimal
    fonte: str  # "posicoes" | "irpf" | "agregado_sem_itens"


@dataclass(frozen=True)
class _ReservaLiquida:
    por_membro: dict[str, _LiquidezMembro]
    caixa_brl: Decimal
    caixa_me: Decimal
    caixa_nao_classificado: Decimal

    def total(self, *, incluir_caixa_me: bool) -> Decimal:
        membros = sum((m.valor_liquido for m in self.por_membro.values()), _ZERO)
        return membros + self.caixa_brl + (self.caixa_me if incluir_caixa_me else _ZERO)


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
        liquidez = self._build_liquidez(patrimonio, investimentos_atuais, bens_por_membro)
        perfil = self._resolve_perfil(fluxo)
        return self._build_payload(base, liquidez, perfil)

    # -- Numerador ------------------------------------------------------------

    def _build_liquidez(
        self,
        patrimonio: dict,
        investimentos_atuais: dict | None,
        bens_por_membro: Mapping[str, dict] | None,
    ) -> _ReservaLiquida:
        por_membro = {
            member_key: self._liquidez_membro(
                member_key,
                aggregate=_dec(patrimonio.get(f"investimentos_{member_key}", 0)),
                investimentos_atuais=investimentos_atuais,
                bens=(bens_por_membro or {}).get(member_key),
            )
            for member_key in self._member_keys()
        }
        return _caixa_por_tipo(patrimonio, por_membro)

    def _member_keys(self) -> list[str]:
        identity = self._config.members
        keys = [identity.titular_key]
        if identity.conjuge_key:
            keys.append(identity.conjuge_key)
        return keys

    def _liquidez_membro(
        self,
        member_key: str,
        *,
        aggregate: Decimal,
        investimentos_atuais: dict | None,
        bens: dict | None,
    ) -> _LiquidezMembro:
        items = _positions_for_member(member_key, self._config.members, investimentos_atuais)
        fonte = "posicoes"
        if not items and bens is not None:
            items, fonte = _irpf_items(get_bens(bens)), "irpf"
        if not items:
            # Sem item-level data (fixtures antigas/aggregate puro): mantém o
            # agregado com flag — melhor superestimar rotulado que zerar cego.
            return _LiquidezMembro(aggregate, _ZERO, "agregado_sem_itens")
        liquido, excluido = self._filter_liquid(items)
        return _LiquidezMembro(liquido, excluido, fonte)

    def _filter_liquid(self, items: list[dict]) -> tuple[Decimal, Decimal]:
        liquido = _ZERO
        excluido = _ZERO
        keywords = (
            dict(self._config.keywords_por_classe) if self._config.keywords_por_classe else None
        )
        for item in items:
            valor = _item_valor(item)
            if valor <= _ZERO:
                continue
            if _is_liquid_item(item, keywords):
                liquido += valor
            else:
                excluido += valor
        return liquido, excluido

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
        self, base: _BaseMensal, liquidez: _ReservaLiquida, perfil: _PerfilRenda
    ) -> dict:
        total_liquida = liquidez.total(incluir_caixa_me=self._config.incluir_caixa_me)
        cobertura_meses = float(total_liquida / base.valor) if base.valor > 0 else 0.0
        return {
            **self._payload_base(base, perfil, total_liquida),
            "composicao_liquida": self._build_composicao(liquidez, total_liquida, cobertura_meses),
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

    def _build_composicao(
        self, liquidez: _ReservaLiquida, total_liquida: Decimal, cobertura_meses: float
    ) -> dict:
        composicao: dict[str, float] = {
            f"investimentos_{key}": _legacy_number(m.valor_liquido)
            for key, m in liquidez.por_membro.items()
        }
        if not self._config.members.conjuge_key:
            composicao.setdefault("investimentos_", 0.0)
        caixa_me = liquidez.caixa_me if self._config.incluir_caixa_me else _ZERO
        composicao["caixa"] = _legacy_number(liquidez.caixa_brl)
        composicao["caixa_moeda_estrangeira"] = _legacy_number(caixa_me)
        composicao["total_liquido"] = _legacy_number(total_liquida)
        composicao["cobertura_meses"] = round(cobertura_meses, 1)
        return composicao

    def _build_excluidos(self, liquidez: _ReservaLiquida) -> dict:
        nao_liquidos = sum((m.valor_excluido for m in liquidez.por_membro.values()), _ZERO)
        caixa_me = _ZERO if self._config.incluir_caixa_me else liquidez.caixa_me
        return {
            "investimentos_nao_liquidos": _legacy_number(nao_liquidos),
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


def _positions_for_member(
    member_key: str, identity: MemberIdentity, investimentos_atuais: dict | None
) -> list[dict]:
    """Posições atuais do membro; sem membro atribuído → titular (convenção legado)."""
    dados = (investimentos_atuais or {}).get("dados") or []
    out: list[dict] = []
    for pos in dados:
        if not isinstance(pos, dict):
            continue
        membro = str(pos.get("membro") or "").lower()
        if member_key and member_key in membro:
            out.append(pos)
        elif not membro and member_key == identity.titular_key:
            out.append(pos)
    return out


def _irpf_items(bens: dict) -> list[dict]:
    """Itens IRPF do membro: investimentos + contas bancárias (lista)."""
    items = [inv for inv in (bens.get("investimentos") or []) if isinstance(inv, dict)]
    contas = bens.get("contas_bancarias")
    if isinstance(contas, list):
        items.extend(c for c in contas if isinstance(c, dict))
    elif contas is not None and safe_float(contas) > 0:
        # Escalar consolidado (formato v1.5) — semanticamente Caixa.
        items.append({"tipo": "conta corrente", "descricao": "contas bancárias", "valor": contas})
    return items


def _item_valor(item: dict) -> Decimal:
    for key in ("valor_atual", "valor_total", "valor_brl"):
        v = item.get(key)
        if v is not None:
            return _dec(v)
    return _dec(investimento_valor(item))


def _is_liquid_item(item: dict, keywords: dict[str, tuple[str, ...]] | None) -> bool:
    tipo = str(item.get("tipo") or "")
    descricao = str(item.get("descricao") or item.get("nome") or item.get("description") or "")
    instituicao = str(item.get("instituicao") or "")
    bucket = classify_asset(tipo, descricao, instituicao, keywords=keywords)
    if bucket not in _LIQUID_BUCKETS:
        return False
    haystack = f"{tipo} {descricao} {instituicao}".lower()
    return not _ILLIQUID_RF_RE.search(haystack)


def _caixa_por_tipo(patrimonio: dict, por_membro: dict[str, _LiquidezMembro]) -> _ReservaLiquida:
    """Monta o agregado de liquidez: membros + caixa E3 split por tipo + residual."""
    caixa_brl, caixa_me = _split_caixa_detalhes(patrimonio.get("caixa_detalhes") or [])
    nao_classificado = _dec(patrimonio.get("caixa_moeda_estrangeira", 0)) - caixa_brl - caixa_me
    return _ReservaLiquida(
        por_membro=por_membro,
        caixa_brl=caixa_brl,
        caixa_me=caixa_me,
        caixa_nao_classificado=max(_ZERO, nao_classificado),
    )


def _split_caixa_detalhes(detalhes: list) -> tuple[Decimal, Decimal]:
    """Separa saldos E3 por tipo: ``caixa`` (BRL) vs ``moeda_estrangeira``."""
    caixa = _ZERO
    moeda_estrangeira = _ZERO
    for det in detalhes:
        if not isinstance(det, dict):
            continue
        valor = _dec(det.get("valor_brl", 0))
        if det.get("tipo") == "moeda_estrangeira":
            moeda_estrangeira += valor
        else:
            caixa += valor
    return caixa, moeda_estrangeira
