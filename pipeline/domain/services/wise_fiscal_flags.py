"""Wise fiscal flags detector — A17 L3 P5 (ADR-238 §D1): CBE BACEN + carnê-leão + GCAP cambial."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

#: CBE BACEN: declaração obrigatória se total ativos exterior > USD 1MM.
_CBE_USD_THRESHOLD: Decimal = Decimal("1000000")

#: Código RFB para "rendimentos recebidos do exterior" (carnê-leão mensal).
_CODIGO_RFB_RENDIMENTOS_EXTERIOR: str = "13"

#: Código RFB para "conta-corrente no exterior em moeda estrangeira" (bens/direitos).
_CODIGO_RFB_CONTA_EXTERIOR: str = "62"

#: Severidades alinhadas com convenção interna (ver narrativas).
Severity = Literal["info", "atencao", "critico"]

#: Códigos canônicos de flag fiscal Wise (P5).
FlagCode = Literal["CBE", "CARNELEAO", "GCAP"]


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
    metadata: dict = field(default_factory=dict)


def _to_decimal(v) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


# ─────────────────────── CBE BACEN > USD 1MM ─────────────────────────────────


def detect_cbe_threshold(saldos_31_12: list[dict]) -> list[FiscalFlag]:
    """Flag CBE quando soma de `tipo=conta_exterior` em USD > USD 1MM."""
    total_usd = sum(
        _to_decimal(s.get("saldo"))
        for s in saldos_31_12
        if s.get("tipo") == "conta_exterior" and s.get("moeda") == "USD"
    )
    if total_usd <= _CBE_USD_THRESHOLD:
        return []
    return [_build_cbe_flag(total_usd)]


def _build_cbe_flag(total_usd: Decimal) -> FiscalFlag:
    return FiscalFlag(
        code="CBE",
        severity="info",
        title="Capital Brasileiro no Exterior (CBE BACEN)",
        descricao=(
            f"Total de ativos no exterior: USD {total_usd:,.2f}. Acima do limite "
            f"USD 1.000.000 (Circular BACEN 3.624/2013), há obrigação de declaração "
            f"anual ao Banco Central via sistema CBE. Mathoms não emite — apenas sinaliza."
        ),
        valor_original=total_usd,
        moeda="USD",
    )


# ─────────────────────── Carnê-leão juros ME (código RFB 13) ────────────────


def detect_juros_me_carne_leao(rendimentos_tributaveis: list[dict]) -> list[FiscalFlag]:
    """Flag para cada entrada com codigo_rfb=13 + moeda != BRL — juros do exterior."""
    return [_build_carne_leao_flag(r) for r in rendimentos_tributaveis if _is_juros_me(r)]


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
        severity="atencao",
        title="Carnê-leão mensal — juros recebidos do exterior",
        descricao=(
            f"Juros em {moeda} de {fonte} ({moeda} {valor:,.2f}) classificados em código "
            f"RFB 13 (rendimentos recebidos do exterior). Sujeitos a carnê-leão mensal "
            f"(DARF código 0190) — IR compensa na declaração anual. Verifique se já foi "
            f"recolhido; se não, há multa por atraso. Fact-check apenas."
        ),
        codigo_rfb=_CODIGO_RFB_RENDIMENTOS_EXTERIOR,
        valor_original=valor,
        moeda=moeda,
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


# ─────────────────────── Aggregator — chamada do merger ──────────────────────


def detect_all_wise_flags(informe_pf_payload: dict) -> list[FiscalFlag]:
    """Roda os 3 detectors sobre 1 payload `financeiro_pf` e concatena os flags."""
    saldos = informe_pf_payload.get("saldos_31_12") or []
    rendimentos_trib = informe_pf_payload.get("rendimentos_tributaveis") or []
    bens = informe_pf_payload.get("bens_direitos") or []
    return [
        *detect_cbe_threshold(saldos),
        *detect_juros_me_carne_leao(rendimentos_trib),
        *detect_gcap_cambial_exposure(bens, saldos),
    ]
