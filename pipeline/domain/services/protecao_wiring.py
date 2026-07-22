"""Wiring de proteção patrimonial — apólices de `extract_comprovantes_bens` → `compute_protecao` (A28.l6, ativa ADR-240).

Funções puras que resolvem os inputs do :class:`ProtecaoInput` a partir dos
artefatos já disponíveis no ``ArtifactStore`` + sub-resultados do
``E5AnalyzerAdapter``. Reconciliação apólice→bem (ADR-239 D3) acontece no
write do stage (``_persist_apolice``); aqui apenas consumimos o payload já
reconciliado.

Limitação V1 (pendência A28.l6): ``vehicles_by_id`` chega vazio — FIPE vive em
``vehicles`` (DB) e ``pipeline/**`` não importa SQLAlchemy. ``compute_protecao``
degrada gracioso: KPI C (gap por veículo) sai vazio ("FIPE pendente").
"""

from __future__ import annotations

import unicodedata
from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Optional

from pipeline.artifact_store import ArtifactStore
from pipeline.domain.services.irpf_completude import resolve_ano_base_fiscal
from pipeline.domain.services.protecao_analyzer import (
    FamilyMemberSnapshot,
    FiscalSnapshot,
    PatrimonioSnapshot,
    ProtecaoInput,
    compute_protecao,
)

COMPROVANTES_STAGE = "extract_comprovantes_bens"
_APOLICE_KEY_PREFIX = "apolice_"
_SAUDE_MIN_MESES = 3


def load_apolices(store: ArtifactStore) -> list[dict]:
    """Payloads de apólice do stage comprovantes (keys ``apolice_*``, ADR-239 D7)."""
    if not hasattr(store, "list_keys"):
        return []
    try:
        keys = sorted(store.list_keys(COMPROVANTES_STAGE))
    except Exception:
        return []
    payloads = (
        store.read(COMPROVANTES_STAGE, k) for k in keys if k.startswith(_APOLICE_KEY_PREFIX)
    )
    return [p for p in payloads if p]


# =============================================================================
# Family snapshots (gating flag_vida — ADR-240 KPI F, gate G5)
# =============================================================================


def _idade_em(data_nascimento: Any, ref: date) -> Optional[int]:
    if not isinstance(data_nascimento, str) or len(data_nascimento) < 10:
        return None
    try:
        dob = date.fromisoformat(data_nascimento[:10])
    except ValueError:
        return None
    return (ref.year - dob.year) - (1 if (ref.month, ref.day) < (dob.month, dob.day) else 0)


def _snapshot_membro(key: str, info: dict, titular_key: str, ref: date) -> FamilyMemberSnapshot:
    papel = str(info.get("papel") or ("titular" if key == titular_key else "dependente_outro"))
    return FamilyMemberSnapshot(
        parentesco=papel,
        idade=_idade_em(info.get("data_nascimento"), ref),
        is_dependente=papel not in ("titular", "conjuge"),
        # ADR-240 D3: gatilho é "cônjuge sem renda própria IDENTIFICADA" —
        # sem fonte estruturada de renda por membro, 0 preserva a semântica.
        renda_propria_brl=Decimal("0"),
    )


def family_snapshots_from_config(
    family: dict | None, reference_date: date
) -> tuple[FamilyMemberSnapshot, ...]:
    """Snapshots p/ gating vida. Sem ``membros`` → tupla vazia (G5 degrada)."""
    fam = family or {}
    membros = fam.get("membros") or {}
    if not isinstance(membros, dict):
        return ()
    titular_key = str(fam.get("titular") or "")
    return tuple(
        _snapshot_membro(k, v, titular_key, reference_date)
        for k, v in membros.items()
        if isinstance(v, dict)
    )


# =============================================================================
# Renda anual líquida (denominador KPI B — Cerbasi)
# =============================================================================


def resolve_renda_anual_liquida(irpf_analyzer, fluxo_legacy: dict) -> Decimal:
    """IRPF-first (``renda_liquida_familiar`` do ano-base default); fallback
    12× receita recorrente mensal da janela; 0 quando ambos indisponíveis
    (KPI B ausente — não divide por zero)."""
    renda_irpf = _renda_liquida_irpf(irpf_analyzer)
    if renda_irpf is not None:
        return renda_irpf
    janela = (fluxo_legacy or {}).get("janela_12m") or {}
    mensal = janela.get("receita_recorrente_mensal") or 0
    return Decimal(str(mensal)) * 12


def _ano_base_fiscal(irpf_analyzer) -> Optional[int]:
    """Ano-base fiscal único (ADR-305) — mesmo ano de irpf_kpis/previdencia_pgbl."""
    if irpf_analyzer is None:
        return None
    try:
        resolved = resolve_ano_base_fiscal(irpf_analyzer.estados_completude())
    except Exception:
        return None
    return resolved.ano if resolved is not None else None


def _renda_liquida_irpf(irpf_analyzer) -> Optional[Decimal]:
    ano = _ano_base_fiscal(irpf_analyzer)
    if ano is None:
        return None
    try:
        renda = irpf_analyzer.renda_liquida_familiar(ano)
    except Exception:
        return None
    return Decimal(renda) if renda > 0 else None


# =============================================================================
# Fiscal snapshot (gating flag_saude — ADR-240 KPI F)
# =============================================================================


def _norm_categoria(nome: str) -> str:
    text = nome.strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _meses_com_categoria_saude(fluxo_mensal_raw: dict) -> int:
    por_mes = ((fluxo_mensal_raw or {}).get("despesas") or {}).get("por_mes") or {}
    count = 0
    for categorias in por_mes.values():
        if not isinstance(categorias, dict):
            continue
        if any(
            "saude" in _norm_categoria(str(cat)) and _as_positive(valor)
            for cat, valor in categorias.items()
        ):
            count += 1
    return count


def _as_positive(valor: Any) -> bool:
    try:
        return float(valor) > 0
    except (TypeError, ValueError):
        return False


def _has_deducao_saude_irpf(irpf_analyzer) -> bool:
    ano = _ano_base_fiscal(irpf_analyzer)
    if ano is None:
        return False
    try:
        return "saude" in irpf_analyzer.dedutiveis_aplicados(ano)
    except Exception:
        return False


def build_fiscal_snapshot(irpf_analyzer, fluxo_mensal_raw: dict) -> FiscalSnapshot:
    return FiscalSnapshot(
        has_deducao_saude_irpf=_has_deducao_saude_irpf(irpf_analyzer),
        has_categoria_saude_e4_3_meses=_meses_com_categoria_saude(fluxo_mensal_raw)
        >= _SAUDE_MIN_MESES,
    )


# =============================================================================
# Patrimônio snapshot (ratio passivo/patrimônio — gatilho vida)
# =============================================================================


def build_patrimonio_snapshot(patrimonio_full: dict) -> Optional[PatrimonioSnapshot]:
    liquido = (patrimonio_full or {}).get("liquido")
    dividas = (patrimonio_full or {}).get("dividas")
    if liquido is None or dividas is None:
        return None
    return PatrimonioSnapshot(
        passivo_total_brl=Decimal(str(dividas)),
        patrimonio_liquido_brl=Decimal(str(liquido)),
    )


# =============================================================================
# Orquestrador
# =============================================================================


def compute_protecao_via_store(
    store: ArtifactStore,
    *,
    irpf_analyzer,
    patrimonio_full: dict,
    fluxo_legacy: dict,
    fluxo_mensal_raw: dict,
    family_snapshots: tuple[FamilyMemberSnapshot, ...],
    reference_date: date,
    seguradoras_catalog: Optional[Mapping[str, str]] = None,
) -> dict:
    """Payload ``protecao_patrimonial`` (ADR-240 D8) — sempre retorna (cenário G6-b);
    ``seguradoras_catalog`` (A37.l11) canonicaliza ``seguradora`` antes de contar."""
    renda = resolve_renda_anual_liquida(irpf_analyzer, fluxo_legacy)
    fiscal = build_fiscal_snapshot(irpf_analyzer, fluxo_mensal_raw)
    catalog = seguradoras_catalog or {}
    inp = _protecao_input(
        store, reference_date, renda, family_snapshots, patrimonio_full, fiscal, catalog
    )
    return compute_protecao(inp)


def _protecao_input(
    store: ArtifactStore,
    ref: date,
    renda: Decimal,
    family: tuple[FamilyMemberSnapshot, ...],
    patrimonio_full: dict,
    fiscal: FiscalSnapshot,
    seguradoras_catalog: Mapping[str, str],
) -> ProtecaoInput:
    return ProtecaoInput(
        apolices=load_apolices(store),
        vehicles_by_id={},
        data_referencia=ref,
        renda_anual_liquida_brl=renda,
        family_members=family,
        patrimonio=build_patrimonio_snapshot(patrimonio_full),
        fiscal=fiscal,
        seguradoras_catalog=seguradoras_catalog,
    )
