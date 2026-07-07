"""Wise fiscal flags detector — A17 L3 P5 (ADR-238 §D1).

Camada pós-extração (co-design financial-planner 2026-07-07): zero hard-fail
de boundary; flags com `needs_review=True` viram "pontos a revisar com
contador" agregados pelo narrator (anti-fadiga). Detectors:

- CBE BACEN (warning-only, nunca needs_review) — threshold USD 1MM sobre a
  posição 31/12 no exterior convertida por PTAX.
- Carnê-leão juros ME: bem alocado (código 13 em tributáveis) → footnote
  info; mal-alocado (código 13 em isentos/exclusiva) → needs_review.
- GCAP exposição cambial (heurístico V1, fact-check).
- GCAP_ISENTO: variação cambial dentro de `rendimentos_isentos[]` → needs_review.
- RFB41_ME: conta em ME classificada como código 41 (doméstico) → needs_review.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Optional

from pipeline.domain.services.ptax_types import PtaxGetter

#: CBE BACEN: declaração anual obrigatória se ativos no exterior >= USD 1MM
#: em 31/12 (Res. BCB 279/2022, Lei 14.286/2021; piso elevado de USD 100 mil
#: pela Res. CMN 4.841/2020). Comparação estrita `>` preservada do shipped P5.
_CBE_USD_THRESHOLD: Decimal = Decimal("1000000")

#: Código RFB para "rendimentos recebidos do exterior" (carnê-leão mensal).
_CODIGO_RFB_RENDIMENTOS_EXTERIOR: str = "13"

#: Código RFB para "conta-corrente no exterior em moeda estrangeira" (bens/direitos).
_CODIGO_RFB_CONTA_EXTERIOR: str = "62"

#: Código RFB para conta-corrente doméstica — em ME indica misclassificação (P5.1).
_CODIGO_RFB_CONTA_DOMESTICA: str = "41"

#: Severidades alinhadas com convenção interna (ver narrativas).
Severity = Literal["info", "atencao", "critico"]

#: Códigos canônicos de flag fiscal Wise (P5 + co-design 2026-07-07).
FlagCode = Literal["CBE", "CARNELEAO", "GCAP", "GCAP_ISENTO", "RFB41_ME"]

#: Regex de variação cambial (P5.2) — aplicado sobre descrição normalizada
#: (sem acentos, lowercase); `\bfx\b` word-bounded evita falso-positivo.
_RE_VARIACAO_CAMBIAL = re.compile(r"variacao cambial|ganho cambial|exchange gain|\bfx\b")


@dataclass(frozen=True)
class FiscalFlag:
    """Obrigação fiscal estruturada — consumida por narrativas E5 + UI (ADR-238 §D1)."""

    code: FlagCode
    severity: Severity
    title: str
    descricao: str
    codigo_rfb: str = ""
    valor_brl: Decimal | None = None
    valor_original: Decimal | None = None
    moeda: str = "BRL"
    needs_review: bool = False
    metadata: dict = field(default_factory=dict)

    def format(self) -> str:
        """Mensagem única para canais de log/warning (ADR-097 D1)."""
        return f"[{self.code}] {self.title}: {self.descricao}"


def _to_decimal(v) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _norm_descricao(s: str) -> str:
    """Normaliza para matching acento-insensitive (NFKD → ascii → lower)."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _has_conta_exterior(payload: dict) -> bool:
    """Payload tem posição no exterior (saldo `conta_exterior` ou bem código 62)?"""
    saldos = payload.get("saldos_31_12") or []
    bens = payload.get("bens_direitos") or []
    return any(s.get("tipo") == "conta_exterior" for s in saldos) or any(
        b.get("codigo_rfb") == _CODIGO_RFB_CONTA_EXTERIOR for b in bens
    )


# ─────────────────────── CBE BACEN >= USD 1MM (P5.4) ────────────────────────


# Warning-only (nunca needs_review). Sem PTAX, degrada para soma nominal
# das posições USD (comportamento do P5 shipped).
def detect_cbe_threshold(
    saldos_31_12: list[dict],
    ptax_getter: Optional[PtaxGetter] = None,
    ano_base: Optional[int] = None,
) -> list[FiscalFlag]:
    """Flag CBE quando posição exterior 31/12 convertida por PTAX > USD 1MM (P5.4)."""
    total_usd = _total_exterior_em_usd(saldos_31_12, ptax_getter, ano_base)
    if total_usd <= _CBE_USD_THRESHOLD:
        return []
    return [_build_cbe_flag(total_usd)]


def _total_exterior_em_usd(
    saldos_31_12: list[dict],
    ptax_getter: Optional[PtaxGetter] = None,
    ano_base: Optional[int] = None,
) -> Decimal:
    """Converte cada posição `conta_exterior` para USD via PTAX 31/12 (P5.4)."""
    exterior = [s for s in saldos_31_12 if s.get("tipo") == "conta_exterior"]
    nominal_usd = sum(
        (_to_decimal(s.get("saldo")) for s in exterior if s.get("moeda") == "USD"),
        Decimal("0"),
    )
    non_usd = [s for s in exterior if s.get("moeda", "BRL") != "USD"]
    if not non_usd or ptax_getter is None or ano_base is None:
        return nominal_usd
    usd_quote = ptax_getter("USD", ano_base)
    if usd_quote is None:
        return nominal_usd
    return nominal_usd + _soma_non_usd_em_usd(non_usd, ptax_getter, ano_base, usd_quote.rate)


def _soma_non_usd_em_usd(
    non_usd: list[dict], ptax_getter: PtaxGetter, ano_base: int, usd_rate: Decimal
) -> Decimal:
    """Equivalente USD das posições não-USD; moeda sem cotação fica de fora (graceful)."""
    total = Decimal("0")
    for s in non_usd:
        quote = ptax_getter(s.get("moeda", "BRL"), ano_base)
        if quote is None:
            continue
        total += _to_decimal(s.get("saldo")) * quote.rate / usd_rate
    return total


def _build_cbe_flag(total_usd: Decimal) -> FiscalFlag:
    return FiscalFlag(
        code="CBE",
        severity="info",
        title="Capital Brasileiro no Exterior (CBE BACEN)",
        descricao=(
            f"Total de ativos no exterior: USD {total_usd:,.2f} (equivalente, PTAX 31/12). "
            f"A partir de USD 1.000.000 (Res. BCB 279/2022; piso elevado de USD 100 mil "
            f"pela Res. CMN 4.841/2020), há obrigação de declaração anual ao Banco Central "
            f"via sistema CBE. Mathoms não emite — apenas sinaliza."
        ),
        valor_original=total_usd,
        moeda="USD",
    )


# ─────────────────────── Carnê-leão juros ME (P5.3) ─────────────────────────


# Co-design financial-planner 2026-07-07: alocação correta não é ponto de
# revisão — severity info sem needs_review (narrator renderiza como nota).
def detect_juros_me_carne_leao(rendimentos_tributaveis: list[dict]) -> list[FiscalFlag]:
    """Código 13 + ME corretamente em tributáveis → footnote informativo (P5.3)."""
    return [_build_carne_leao_flag(r) for r in rendimentos_tributaveis if _is_juros_me(r)]


def detect_juros_me_mal_alocado(
    rendimentos_isentos: list[dict], rendimentos_exclusiva: list[dict]
) -> list[FiscalFlag]:
    """Código 13 + ME **fora de tributáveis** → needs_review (DARF mensal em risco)."""
    fora_de_lugar = [r for r in rendimentos_isentos + rendimentos_exclusiva if _is_juros_me(r)]
    return [_build_carne_leao_mal_alocado_flag(r) for r in fora_de_lugar]


def _is_juros_me(r: dict) -> bool:
    return (
        r.get("codigo_rfb") == _CODIGO_RFB_RENDIMENTOS_EXTERIOR and r.get("moeda", "BRL") != "BRL"
    )


def _build_carne_leao_flag(r: dict) -> FiscalFlag:
    valor = _to_decimal(r.get("valor"))
    moeda = r.get("moeda", "USD")
    fonte = r.get("fonte_pagadora_nome", "")[:50]
    return FiscalFlag(
        code="CARNELEAO",
        severity="info",
        title="Carnê-leão mensal — juros recebidos do exterior",
        descricao=(
            f"Juros em {moeda} de {fonte} ({moeda} {valor:,.2f}) classificados em código "
            f"RFB 13 (rendimentos recebidos do exterior). Sujeitos a carnê-leão mensal "
            f"(DARF código 0190) — IR compensa na declaração anual. Fact-check apenas."
        ),
        codigo_rfb=_CODIGO_RFB_RENDIMENTOS_EXTERIOR,
        valor_original=valor,
        moeda=moeda,
        metadata={"fonte_pagadora_cnpj": r.get("fonte_pagadora_cnpj", "")},
    )


def _build_carne_leao_mal_alocado_flag(r: dict) -> FiscalFlag:
    valor = _to_decimal(r.get("valor"))
    moeda = r.get("moeda", "USD")
    return FiscalFlag(
        code="CARNELEAO",
        severity="atencao",
        title="Juros do exterior fora de rendimentos tributáveis",
        descricao=(
            f"Rendimento código RFB 13 em {moeda} ({moeda} {valor:,.2f}) apareceu fora de "
            f"rendimentos tributáveis. Juros do exterior sujeitam-se a carnê-leão mensal "
            f"(DARF código 0190) — mal-alocado, o recolhimento mensal pode estar em atraso. "
            f"Revise com contador."
        ),
        codigo_rfb=_CODIGO_RFB_RENDIMENTOS_EXTERIOR,
        valor_original=valor,
        moeda=moeda,
        needs_review=True,
        metadata={"fonte_pagadora_cnpj": r.get("fonte_pagadora_cnpj", "")},
    )


# ─────────────────────── GCAP cambial — heurística V1 ────────────────────────


def detect_gcap_cambial_exposure(
    bens_direitos: list[dict],
    saldos_31_12: list[dict],
) -> list[FiscalFlag]:
    """Sinaliza exposição em ME (RFB 62 ou conta_exterior) — V1 heurístico, fact-check apenas."""
    saldos_me = [_pick_saldo_me(s) for s in saldos_31_12]
    bens_me = [_pick_bem_exterior(b) for b in bens_direitos]
    exposicoes: list[dict] = [e for e in saldos_me + bens_me if e is not None]
    if not exposicoes:
        return []
    return [_build_gcap_flag(exposicoes)]


def _pick_saldo_me(s: dict) -> dict | None:
    if s.get("tipo") != "conta_exterior":
        return None
    moeda = s.get("moeda", "BRL")
    if moeda == "BRL":
        return None
    return {"moeda": moeda, "valor": _to_decimal(s.get("saldo"))}


def _pick_bem_exterior(b: dict) -> dict | None:
    if b.get("codigo_rfb") != _CODIGO_RFB_CONTA_EXTERIOR:
        return None
    return {"moeda": b.get("moeda", "USD"), "valor": _to_decimal(b.get("valor"))}


def _build_gcap_flag(exposicoes: list[dict]) -> FiscalFlag:
    moedas = sorted({e["moeda"] for e in exposicoes})
    total_por_moeda = ", ".join(
        f"{m} {sum(e['valor'] for e in exposicoes if e['moeda'] == m):,.2f}" for m in moedas
    )
    return FiscalFlag(
        code="GCAP",
        severity="atencao",
        title="Variação cambial — possível GCAP em resgate",
        descricao=(
            f"Exposição cambial detectada ({total_por_moeda}). Variação USD/BRL sobre o "
            f"saldo não é rendimento isento — é ganho de capital em moeda estrangeira "
            f"(Lei 9.250/95). Há GCAP via DARF 15% (código 4600) sobre o valor convertido "
            f"em BRL pelo PTAX do dia do resgate. Verifique se houve resgate no ano e "
            f"se DARF foi recolhido. Fact-check apenas — Mathoms não calcula GCAP."
        ),
        codigo_rfb=_CODIGO_RFB_CONTA_EXTERIOR,
        metadata={"moedas_expostas": moedas},
    )


# ─────────────────────── Variação cambial em isentos (P5.2) ─────────────────


def detect_variacao_cambial_isentos(
    rendimentos_isentos: list[dict], *, has_exterior: bool
) -> list[FiscalFlag]:
    """Descrição de variação/ganho cambial dentro de `rendimentos_isentos[]` → needs_review."""
    if not has_exterior:
        return []
    suspeitos = [
        r
        for r in rendimentos_isentos
        if _RE_VARIACAO_CAMBIAL.search(_norm_descricao(r.get("descricao") or ""))
    ]
    return [_build_gcap_isento_flag(r) for r in suspeitos]


def _build_gcap_isento_flag(r: dict) -> FiscalFlag:
    valor = _to_decimal(r.get("valor"))
    moeda = r.get("moeda", "BRL")
    return FiscalFlag(
        code="GCAP_ISENTO",
        severity="atencao",
        title="Variação cambial classificada como rendimento isento",
        descricao=(
            f"Possível ganho de capital em ME tratado como isento "
            f'({moeda} {valor:,.2f} — "{(r.get("descricao") or "")[:60]}"). Variação '
            f"cambial não é rendimento isento — apuração via GCAP (15%). Confira com contador."
        ),
        valor_original=valor,
        moeda=moeda,
        needs_review=True,
    )


# ─────────────────────── Código 41 em ME (P5.1) ─────────────────────────────


# Predicado ESTREITO (co-design financial-planner 2026-07-07):
# codigo_rfb == "41" AND (moeda != "BRL" OR has_conta_exterior).
# Código 41 puro em BRL é legítimo — não flagar.
def detect_rfb41_em_me(bens_direitos: list[dict], *, has_exterior: bool) -> list[FiscalFlag]:
    """Código 41 (conta doméstica) em ME ou junto de posição exterior → needs_review (P5.1)."""
    suspeitos = [
        b
        for b in bens_direitos
        if b.get("codigo_rfb") == _CODIGO_RFB_CONTA_DOMESTICA
        and (b.get("moeda", "BRL") != "BRL" or has_exterior)
    ]
    return [_build_rfb41_flag(b) for b in suspeitos]


def _build_rfb41_flag(b: dict) -> FiscalFlag:
    valor = _to_decimal(b.get("valor"))
    moeda = b.get("moeda", "BRL")
    return FiscalFlag(
        code="RFB41_ME",
        severity="atencao",
        title="Conta em moeda estrangeira com código RFB doméstico",
        descricao=(
            f"Conta em ME classificada como código 41 ({moeda} {valor:,.2f} — "
            f'"{(b.get("descricao") or "")[:60]}"); código correto é 62 '
            f"(conta-corrente no exterior). Revise com contador."
        ),
        codigo_rfb=_CODIGO_RFB_CONTA_DOMESTICA,
        valor_original=valor,
        moeda=moeda,
        needs_review=True,
    )


# ─────────────────────── Aggregator — chamada do merger ──────────────────────


def detect_all_wise_flags(
    informe_pf_payload: dict,
    ptax_getter: Optional[PtaxGetter] = None,
    ano_base: Optional[int] = None,
) -> list[FiscalFlag]:
    """Roda os detectors P5 sobre 1 payload `financeiro_pf` e concatena os flags."""
    saldos = informe_pf_payload.get("saldos_31_12") or []
    rendimentos_trib = informe_pf_payload.get("rendimentos_tributaveis") or []
    rendimentos_isentos = informe_pf_payload.get("rendimentos_isentos") or []
    rendimentos_exclusiva = informe_pf_payload.get("rendimentos_exclusiva") or []
    bens = informe_pf_payload.get("bens_direitos") or []
    has_exterior = _has_conta_exterior(informe_pf_payload)
    return [
        *detect_cbe_threshold(saldos, ptax_getter, ano_base),
        *detect_juros_me_carne_leao(rendimentos_trib),
        *detect_juros_me_mal_alocado(rendimentos_isentos, rendimentos_exclusiva),
        *detect_gcap_cambial_exposure(bens, saldos),
        *detect_variacao_cambial_isentos(rendimentos_isentos, has_exterior=has_exterior),
        *detect_rfb41_em_me(bens, has_exterior=has_exterior),
    ]
