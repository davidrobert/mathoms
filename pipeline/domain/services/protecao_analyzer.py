"""Proteção Patrimonial analyzer (S_PROTECAO — pilar AUVP, ADR-240 D2/D3/D8)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, Mapping, Optional

from pipeline.domain.services.seguradora_resolver import (
    canonicalize_apolice_seguradora,
    fallback_seguradora_display,
)

_logger = logging.getLogger("mathoms.relatorio.protecao")

# ===========================================================================
# Faixas Cerbasi (ADR-240 D3 KPI B) — calibradas em código (rules-as-code).
# Threshold de gap por veículo (KPI C V1) também em código.
# ===========================================================================

_PCT_RENDA_FAIXAS: tuple[tuple[Decimal, Decimal, str], ...] = (
    # (lo, hi exclusivo, sinal). Hi=None → infinity.
    (Decimal("0"), Decimal("0.01"), "atencao"),
    (Decimal("0.01"), Decimal("0.03"), "ok"),
    (Decimal("0.03"), Decimal("0.05"), "ok_forte"),
)
_PCT_RENDA_ACIMA_TETO_SINAL = "atencao"  # > 0.05

_GAP_AUTO_FAIXAS: tuple[tuple[Decimal, Decimal, str], ...] = (
    (Decimal("-1"), Decimal("0.10"), "ok"),
    (Decimal("0.10"), Decimal("0.25"), "atencao_branda"),
)
_GAP_AUTO_ATENCAO_SINAL = "atencao"  # >= 0.25

_PASSIVO_PATRIMONIO_THRESHOLD = Decimal("0.30")
_APOLICE_VENCENDO_DIAS = 30


GapAutoSinal = Literal["ok", "atencao_branda", "atencao"]
PctRendaSinal = Literal["atencao", "ok", "ok_forte"]


# ===========================================================================
# Inputs tipados (ADR-097 D3 — value objects)
# ===========================================================================


@dataclass(frozen=True)
class FamilyMemberSnapshot:
    """Membro consumido para gating de flag_vida (ADR-240 KPI F)."""

    parentesco: str  # "titular", "conjuge", "filho", "dependente_outro"
    idade: Optional[int] = None
    is_dependente: bool = False
    renda_propria_brl: Decimal = Decimal("0")


@dataclass(frozen=True)
class PatrimonioSnapshot:
    """Snapshot mínimo p/ ratio passivo/patrimônio (KPI F vida)."""

    passivo_total_brl: Decimal
    patrimonio_liquido_brl: Decimal


@dataclass(frozen=True)
class FiscalSnapshot:
    """Snapshot mínimo p/ gating de flag_saude (KPI F saúde)."""

    has_deducao_saude_irpf: bool = False
    has_categoria_saude_e4_3_meses: bool = False


@dataclass(frozen=True)
class ProtecaoInput:
    """Input agregado do ProtecaoAnalyzer (puro, sem DB)."""

    apolices: list[dict]
    """Lista de payloads ApolicePayload (top-level lenient). Sem PII."""

    vehicles_by_id: dict[str, dict]
    """Map vehicle_id → {fipe_value_brl: Decimal | None, ...}."""

    data_referencia: date
    renda_anual_liquida_brl: Decimal
    family_members: tuple[FamilyMemberSnapshot, ...] = ()
    patrimonio: Optional[PatrimonioSnapshot] = None
    fiscal: FiscalSnapshot = FiscalSnapshot()

    seguradoras_catalog: Mapping[str, str] = field(default_factory=dict)
    """Codes ``category=insurance`` → nome de exibição (A37.l11). Vazio degrada
    para normalização pura (sem unificação de variantes)."""


# ===========================================================================
# Helpers determinísticos
# ===========================================================================


def _to_decimal(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _is_vigente(apolice: dict, ref: date) -> bool:
    inicio = _parse_date(apolice.get("vigencia_inicio"))
    fim = _parse_date(apolice.get("vigencia_fim"))
    if inicio is None or fim is None:
        return False
    return inicio <= ref <= fim


def _is_vencendo(apolice: dict, ref: date) -> bool:
    if not _is_vigente(apolice, ref):
        return False
    fim = _parse_date(apolice.get("vigencia_fim"))
    return fim is not None and fim <= ref + timedelta(days=_APOLICE_VENCENDO_DIAS)


def _is_vencida(apolice: dict, ref: date) -> bool:
    fim = _parse_date(apolice.get("vigencia_fim"))
    return fim is not None and fim < ref


def _parse_date(v) -> Optional[date]:
    if isinstance(v, date):
        return v
    if isinstance(v, str) and len(v) >= 10:
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


def _faixa_sinal(value: Decimal, faixas, fallback: str) -> str:
    for lo, hi, sinal in faixas:
        if lo <= value < hi:
            return sinal
    return fallback


# ===========================================================================
# KPI G — Σ prêmios + decomposição
# ===========================================================================


def _premio_total_anual(apolices_vigentes: list[dict]) -> Decimal:
    return sum((_to_decimal(a.get("premio_total_brl")) for a in apolices_vigentes), Decimal("0"))


def _categoriza_apolice(apolice: dict) -> str:
    """Classifica apólice em {auto, residencial, vida, saude, ap} pelo bem dominante."""
    tipos = {b.get("tipo") for b in (apolice.get("bens_segurados") or [])}
    if "imovel" in tipos and "veiculo" not in tipos:
        return "residencial"
    if "veiculo" in tipos:
        return "auto"
    if "pessoa" in tipos:
        return _classifica_pessoa(apolice)
    return "auto"  # fallback


def _coberturas_pessoa(apolice: dict):
    for bem in apolice.get("bens_segurados") or []:
        if bem.get("tipo") == "pessoa":
            yield from bem.get("coberturas") or []


def _classifica_pessoa(apolice: dict) -> str:
    """Sub-classificação V2 (vida/saude/ap) pelo tipo da 1ª cobertura."""
    for cov in _coberturas_pessoa(apolice):
        t = cov.get("tipo")
        if t in ("vida", "saude", "acidentes"):
            return "ap" if t == "acidentes" else t
    return "vida"


def _premio_decomposicao(apolices_vigentes: list[dict]) -> dict[str, Decimal]:
    decomp: dict[str, Decimal] = {}
    for a in apolices_vigentes:
        cat = _categoriza_apolice(a)
        decomp[cat] = decomp.get(cat, Decimal("0")) + _to_decimal(a.get("premio_total_brl"))
    return decomp


# ===========================================================================
# KPI B — % renda
# ===========================================================================


def _pct_renda(premio_anual: Decimal, renda_anual: Decimal) -> Optional[Decimal]:
    if renda_anual <= 0:
        return None
    return premio_anual / renda_anual


def _pct_renda_sinal(pct: Decimal) -> PctRendaSinal:
    return _faixa_sinal(pct, _PCT_RENDA_FAIXAS, _PCT_RENDA_ACIMA_TETO_SINAL)


# ===========================================================================
# KPI C — gap auto V1 (LMI vs FIPE por veículo)
# ===========================================================================


def _gap_auto_sinal(gap: Decimal) -> GapAutoSinal:
    return _faixa_sinal(gap, _GAP_AUTO_FAIXAS, _GAP_AUTO_ATENCAO_SINAL)


def _lmi_efetivo(cobertura: dict, fipe_value: Decimal) -> Decimal:
    """Resolve LMI efetivo conforme lmi_modo (ADR-239 D2)."""
    modo = cobertura.get("lmi_modo")
    if modo == "fipe_percentual":
        pct = _to_decimal(cobertura.get("lmi_fipe_percentual"))
        return fipe_value * pct
    return _to_decimal(cobertura.get("lmi_brl"))


def _iter_bens_segurados(apolices_vigentes: list[dict]):
    """Flatten bens_segurados de todas as apólices vigentes."""
    for apolice in apolices_vigentes:
        yield from apolice.get("bens_segurados") or []


def _iter_veiculos_segurados(apolices_vigentes: list[dict]):
    """Bens do tipo veículo (filtro plano sobre flatten)."""
    return (b for b in _iter_bens_segurados(apolices_vigentes) if b.get("tipo") == "veiculo")


def _bens_com_gap_cobertura(
    apolices_vigentes: list[dict], vehicles_by_id: dict[str, dict]
) -> list[dict]:
    bens_gap: list[dict] = []
    for bem in _iter_veiculos_segurados(apolices_vigentes):
        gap_entry = _build_gap_entry(bem, vehicles_by_id)
        if gap_entry is not None:
            bens_gap.append(gap_entry)
    return bens_gap


def _resolve_fipe_e_lmi(
    bem: dict, vehicles_by_id: dict[str, dict]
) -> Optional[tuple[Decimal, Decimal]]:
    """Resolve (FIPE, LMI) ou None quando FIPE pendente/LMI inválido."""
    veiculo_id = bem.get("veiculo_id")
    if not veiculo_id:
        return None
    v = vehicles_by_id.get(veiculo_id)
    if v is None:
        return None
    fipe = _to_decimal(v.get("fipe_value_brl"))
    if fipe <= 0:
        return None
    lmi = _lmi_casco(bem, fipe)
    return (fipe, lmi) if lmi > 0 else None


def _build_gap_entry(bem: dict, vehicles_by_id: dict[str, dict]) -> Optional[dict]:
    """1 entry de gap por veículo segurado; None quando FIPE pendente."""
    resolved = _resolve_fipe_e_lmi(bem, vehicles_by_id)
    if resolved is None:
        return None
    fipe, lmi = resolved
    gap = (fipe - lmi) / fipe
    return {
        "veiculo_id": bem["veiculo_id"],
        "veiculo_descricao": f"{bem.get('marca', '')} {bem.get('modelo', '')}".strip(),
        "lmi_brl": str(lmi.quantize(Decimal("0.01"))),
        "fipe_brl": str(fipe.quantize(Decimal("0.01"))),
        "gap_pct": str(gap.quantize(Decimal("0.000001"))),
        "sinal": _gap_auto_sinal(gap),
    }


def _lmi_casco(bem_veiculo: dict, fipe_value: Decimal) -> Decimal:
    """Encontra LMI da 1ª cobertura material com lmi_modo válido."""
    for cov in bem_veiculo.get("coberturas") or []:
        if cov.get("tipo") != "material":
            continue
        modo = cov.get("lmi_modo")
        if modo in ("valor_fixo", "fipe_percentual", "primeiro_risco_absoluto"):
            return _lmi_efetivo(cov, fipe_value)
    return Decimal("0")


# ===========================================================================
# KPI F — gap qualitativo (vida + saúde V1)
# ===========================================================================


def _has_apolice_pessoa_cobertura(apolices_vigentes: list[dict], tipo_cov: str) -> bool:
    """True quando há apólice vigente com cobertura pessoa do tipo (vida/saude/acidentes)."""
    return any(
        cov.get("tipo") == tipo_cov for a in apolices_vigentes for cov in _coberturas_pessoa(a)
    )


def _flag_vida(inp: ProtecaoInput, apolices_vigentes: list[dict]) -> dict:
    """Gating heurístico vida (ADR-240 KPI F). Sem family_members → False (G5)."""
    if not inp.family_members:
        return {"categoria": "vida", "flag": False, "rationale": "sem family_members"}
    risco = _detecta_risco_vida(inp.family_members, inp.patrimonio)
    if not risco:
        return {"categoria": "vida", "flag": False, "rationale": "sem gatilho"}
    if _has_apolice_pessoa_cobertura(apolices_vigentes, "vida"):
        return {"categoria": "vida", "flag": False, "rationale": "apolice_vida_ativa"}
    return {"categoria": "vida", "flag": True, "rationale": risco}


def _detecta_risco_vida(
    members,
    patrimonio: Optional[PatrimonioSnapshot] = None,
) -> Optional[str]:
    """Retorna primeiro gatilho disparado, None se nenhum."""
    for m in members:
        if m.is_dependente and m.idade is not None and m.idade < 18:
            return "dependentes_menores_18"
    for m in members:
        if m.parentesco == "conjuge" and m.renda_propria_brl == 0:
            return "conjuge_sem_renda_propria"
    if patrimonio and patrimonio.patrimonio_liquido_brl > 0:
        if (
            patrimonio.passivo_total_brl / patrimonio.patrimonio_liquido_brl
            > _PASSIVO_PATRIMONIO_THRESHOLD
        ):
            return "passivo_acima_30_pct_patrimonio"
    return None


def _flag_saude(inp: ProtecaoInput, apolices_vigentes: list[dict]) -> dict:
    """Gating heurístico saúde (ADR-240 KPI F)."""
    if inp.fiscal.has_deducao_saude_irpf or inp.fiscal.has_categoria_saude_e4_3_meses:
        return {"categoria": "saude", "flag": False, "rationale": "evidencia_pagamento_saude"}
    if _has_apolice_pessoa_cobertura(apolices_vigentes, "saude"):
        return {"categoria": "saude", "flag": False, "rationale": "apolice_saude_ativa"}
    return {"categoria": "saude", "flag": True, "rationale": "sem_evidencia_cobertura"}


# ===========================================================================
# Apólices resumo (vigentes / vencendo / vencidas)
# ===========================================================================


def apolice_resumo(a: dict) -> dict:
    """Resumo LGPD-safe de 1 apólice (sem CPF/endereço/placa) — consumido no
    payload E5 e no balde E4 ``seguros`` (A28.l6)."""
    bens = a.get("bens_segurados") or []
    return {
        "apolice_numero": a.get("apolice_numero", ""),
        "seguradora": a.get("seguradora", ""),
        # A37.l11 — display via catálogo quando canonicalizado; fallback
        # capitalizado para callers sem catálogo (E4 seguros / artifacts antigos).
        "seguradora_nome": a.get("seguradora_nome")
        or fallback_seguradora_display(a.get("seguradora", "")),
        "vigencia_inicio": str(_parse_date(a.get("vigencia_inicio")) or ""),
        "vigencia_fim": str(_parse_date(a.get("vigencia_fim")) or ""),
        "premio_total_brl": str(_to_decimal(a.get("premio_total_brl")).quantize(Decimal("0.01"))),
        "bens_count": len(bens),
        "tipos_bem": sorted({b.get("tipo") for b in bens if b.get("tipo")}),
    }


def _corretoras_count(apolices_vigentes: list[dict]) -> int:
    cnpjs = {
        (a.get("corretor") or {}).get("cpf_or_cnpj") for a in apolices_vigentes if a.get("corretor")
    }
    cnpjs.discard(None)
    cnpjs.discard("")
    return len(cnpjs)


def _seguradoras_count(apolices_vigentes: list[dict]) -> int:
    return len({a.get("seguradora") for a in apolices_vigentes if a.get("seguradora")})


# ===========================================================================
# Orquestrador
# ===========================================================================


def _format_pct_renda(pct: Optional[Decimal] = None) -> str:
    """None → "0.000000" (KPI ausente quando renda=0); else formata 6 decimais."""
    if pct is None:
        return "0.000000"
    return str(pct.quantize(Decimal("0.000001")))


def _split_apolices_por_vigencia(apolices: list[dict], ref: date) -> tuple[list, list, list]:
    vigentes = [a for a in apolices if _is_vigente(a, ref)]
    vencendo = [a for a in apolices if _is_vencendo(a, ref)]
    vencidas = [a for a in apolices if _is_vencida(a, ref)]
    return vigentes, vencendo, vencidas


def _emit_telemetry(payload: dict, seguradoras_fora_catalogo: int = 0) -> None:
    """ADR-240 D8: telemetria sem PII (counts agregados + flags + has_apolice_vencida)."""
    _logger.info(
        "mathoms.relatorio.protecao_rendered",
        extra={
            "kpis_status": {
                "tem_apolice_vigente": len(payload.get("apolices_vigentes") or []) > 0,
                "bens_com_gap_count": len(payload.get("bens_com_gap_cobertura") or []),
            },
            "has_gap_vida": _flag_categoria(payload, "vida"),
            "has_gap_saude": _flag_categoria(payload, "saude"),
            "has_apolice_vencida": len(payload.get("apolices_vencidas") or []) > 0,
            "has_apolice_vencendo": len(payload.get("apolices_vencendo") or []) > 0,
            "corretoras_count": payload.get("corretoras_count", 0),
            "seguradoras_count": payload.get("seguradoras_count", 0),
            # Flag SOFT A37.l11 — codes fora do institution_catalog (catálogo esparso).
            "seguradoras_fora_catalogo": seguradoras_fora_catalogo,
        },
    )


def _flag_categoria(payload: dict, categoria: str) -> bool:
    """True quando gap_qualitativo[categoria].flag == True."""
    return any(
        g.get("categoria") == categoria and g.get("flag", False)
        for g in (payload.get("gap_qualitativo") or [])
    )


def _canonical_apolices(inp: ProtecaoInput) -> list[dict]:
    """A37.l11 — boundary E2→domínio: canonicaliza ``seguradora`` contra o
    catálogo antes de contar/resumir (artifacts antigos não migram; re-run
    recomputa aqui)."""
    return [canonicalize_apolice_seguradora(a, inp.seguradoras_catalog) for a in inp.apolices]


def _fora_catalogo_count(apolices: list[dict]) -> int:
    return sum(1 for a in apolices if a.get("_seguradora_fora_catalogo"))


def _protecao_payload(inp: ProtecaoInput, vigentes, vencendo, vencidas) -> dict:
    premio_total = _premio_total_anual(vigentes)
    pct = _pct_renda(premio_total, inp.renda_anual_liquida_brl)
    decomp = _premio_decomposicao(vigentes)
    return {
        "premio_total_anual_brl": str(premio_total.quantize(Decimal("0.01"))),
        "premio_decomposicao": {k: str(v.quantize(Decimal("0.01"))) for k, v in decomp.items()},
        "pct_renda_anual": _format_pct_renda(pct),
        "bens_com_gap_cobertura": _bens_com_gap_cobertura(vigentes, inp.vehicles_by_id),
        "gap_qualitativo": [_flag_vida(inp, vigentes), _flag_saude(inp, vigentes)],
        "apolices_vigentes": [apolice_resumo(a) for a in vigentes],
        "apolices_vencendo": [apolice_resumo(a) for a in vencendo],
        "apolices_vencidas": [apolice_resumo(a) for a in vencidas],
        "corretoras_count": _corretoras_count(vigentes),
        "seguradoras_count": _seguradoras_count(vigentes),
    }


def compute_protecao(inp: ProtecaoInput) -> dict:
    """Retorna payload `protecao_patrimonial` conforme schema ADR-240 D8."""
    apolices = _canonical_apolices(inp)
    vigentes, vencendo, vencidas = _split_apolices_por_vigencia(apolices, inp.data_referencia)
    payload = _protecao_payload(inp, vigentes, vencendo, vencidas)
    _emit_telemetry(payload, seguradoras_fora_catalogo=_fora_catalogo_count(vigentes))
    return payload


def pct_renda_sinal(pct: Decimal) -> PctRendaSinal:
    """Exporta sinal de % renda (consumido por UI / E6-parecer)."""
    return _pct_renda_sinal(pct)
