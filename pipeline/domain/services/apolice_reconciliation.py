"""Reconciliação apólice → vehicle/imóvel (ADR-239 D3; placa estrita + endereço normalizado)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal, Optional

# ===========================================================================
# Resultado tipado (audit trail)
# ===========================================================================


ReconciliationOutcome = Literal[
    "matched",  # FK preenchida
    "no_candidate",  # nenhum vehicle/property casa
    "stale_cleared",  # FK existente apontava p/ row inexistente; limpa
    "idempotent_skip",  # FK já válida; sem mudança
]


@dataclass(frozen=True)
class BemReconciliationResult:
    """1 entry de ``apolice.bens_segurados[]`` reconciliada."""

    bem_index: int
    tipo: Literal["veiculo", "imovel", "pessoa"]
    outcome: ReconciliationOutcome
    target_id: Optional[str]
    reason: Optional[str] = None


@dataclass(frozen=True)
class ApoliceReconciliationSummary:
    """Sumário agregado LGPD-safe (sem PII)."""

    total_bens: int
    matched: int
    no_candidate: int
    stale_cleared: int
    idempotent_skip: int


# ===========================================================================
# Normalização (estrita p/ placa; aggressive p/ endereço)
# ===========================================================================


def _normalize_placa(placa: str) -> str:
    """Upper + strip hífen/espaço (idêntica à _normalize_placa do schema CRLV)."""
    if not placa:
        return ""
    return placa.upper().replace("-", "").replace(" ", "")


def _normalize_endereco(*parts: str) -> str:
    """lowercase + sem acento + dedupe espaços; concatena partes do endereço."""
    raw = " ".join(p for p in parts if p)
    text = raw.strip().lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def _endereco_canonical_from_struct(endereco: dict | None) -> str:
    """Canonical key de imóvel ApolicePayload — logradouro+numero+cidade+uf."""
    if not endereco:
        return ""
    return _normalize_endereco(
        endereco.get("logradouro", "") or "",
        endereco.get("numero", "") or "",
        endereco.get("cidade", "") or "",
        endereco.get("uf", "") or "",
    )


# ===========================================================================
# Match estrito
# ===========================================================================


def _find_vehicle_by_placa(placa_norm: str, vehicles_by_placa: dict[str, dict]) -> Optional[dict]:
    """Match estrito (ADR-225 identidade imutável)."""
    if not placa_norm:
        return None
    return vehicles_by_placa.get(placa_norm)


def _find_property_by_endereco(
    apolice_endereco_norm: str, properties: list[dict]
) -> Optional[dict]:
    """Match por token-set inclusivo (apolice ⊆ property OU vice-versa)."""
    if not apolice_endereco_norm:
        return None
    apolice_tokens = set(apolice_endereco_norm.split())
    if not apolice_tokens:
        return None
    for p in properties:
        if _matches_token_set(apolice_tokens, p):
            return p
    return None


def _matches_token_set(apolice_tokens: set[str], p: dict) -> bool:
    """True quando tokens canônicos da apolice ⊆ property ou inverso."""
    prop_norm = _normalize_endereco(p.get("endereco_canonical", "") or "")
    if not prop_norm:
        return False
    prop_tokens = set(prop_norm.split())
    return apolice_tokens.issubset(prop_tokens) or prop_tokens.issubset(apolice_tokens)


# ===========================================================================
# Stale check (eager: FK aponta para row inexistente ou outro workspace)
# ===========================================================================


def _veiculo_id_is_stale(
    veiculo_id: str, vehicles_by_id: dict[str, dict], workspace_id: str
) -> bool:
    v = vehicles_by_id.get(veiculo_id)
    if v is None:
        return True
    return v.get("workspace_id") != workspace_id


def _imovel_id_is_stale(
    imovel_id: str, properties_by_id: dict[str, dict], workspace_id: str
) -> bool:
    p = properties_by_id.get(imovel_id)
    if p is None:
        return True
    return p.get("workspace_id") != workspace_id


# ===========================================================================
# Reconciliador principal
# ===========================================================================


def reconcile_apolice_bens(
    apolice_payload: dict,
    vehicles: list[dict],
    properties: list[dict],
    workspace_id: str,
) -> tuple[dict, list[BemReconciliationResult]]:
    """Reconcilia ``apolice.bens_segurados[].{veiculo_id,imovel_id}`` (ADR-239 D3)."""
    indices = _build_indices(vehicles, properties)
    bens = apolice_payload.get("bens_segurados") or []
    new_bens, results = _reconcile_bens_iter(bens, indices, properties, workspace_id)
    return {**apolice_payload, "bens_segurados": new_bens}, results


def _build_indices(vehicles: list[dict], properties: list[dict]) -> dict:
    """Pré-monta indexes (by id, by placa) usados pelo reconciliador."""
    return {
        "vehicles_by_id": {v["id"]: v for v in vehicles},
        "vehicles_by_placa": {
            _normalize_placa(v.get("placa", "")): v for v in vehicles if v.get("placa")
        },
        "properties_by_id": {p["id"]: p for p in properties},
    }


def _reconcile_bens_iter(bens, indices, properties, workspace_id):
    new_bens, results = [], []
    for idx, bem in enumerate(bens):
        new_bem, result = _reconcile_one_bem(
            idx,
            bem,
            indices["vehicles_by_id"],
            indices["vehicles_by_placa"],
            indices["properties_by_id"],
            properties,
            workspace_id,
        )
        new_bens.append(new_bem)
        results.append(result)
    return new_bens, results


def _reconcile_one_bem(
    idx: int,
    bem: dict,
    vehicles_by_id: dict[str, dict],
    vehicles_by_placa: dict[str, dict],
    properties_by_id: dict[str, dict],
    properties: list[dict],
    workspace_id: str,
) -> tuple[dict, BemReconciliationResult]:
    """Despacha por tipo do bem; pessoa em V2 sai como no_candidate sem error."""
    tipo = bem.get("tipo")
    if tipo == "veiculo":
        return _reconcile_veiculo(idx, bem, vehicles_by_id, vehicles_by_placa, workspace_id)
    if tipo == "imovel":
        return _reconcile_imovel(idx, bem, properties_by_id, properties, workspace_id)
    return bem, BemReconciliationResult(
        idx, tipo or "pessoa", "no_candidate", None, "tipo_pessoa_v2_no_reconcile"
    )


def _reconcile_veiculo(
    idx: int,
    bem: dict,
    vehicles_by_id: dict[str, dict],
    vehicles_by_placa: dict[str, dict],
    workspace_id: str,
) -> tuple[dict, BemReconciliationResult]:
    """Match estrito por placa normalizada (ADR-225 identidade imutável)."""
    existing_fk = bem.get("veiculo_id")
    if existing_fk and not _veiculo_id_is_stale(existing_fk, vehicles_by_id, workspace_id):
        return bem, BemReconciliationResult(idx, "veiculo", "idempotent_skip", existing_fk, None)
    cleaned_bem = {**bem, "veiculo_id": None} if existing_fk else dict(bem)
    placa_norm = _normalize_placa(cleaned_bem.get("placa", "") or "")
    match = _find_vehicle_by_placa(placa_norm, vehicles_by_placa)
    if match is None:
        outcome = "stale_cleared" if existing_fk else "no_candidate"
        return cleaned_bem, BemReconciliationResult(idx, "veiculo", outcome, None, None)
    cleaned_bem["veiculo_id"] = match["id"]
    return cleaned_bem, BemReconciliationResult(idx, "veiculo", "matched", match["id"], None)


def _reconcile_imovel(
    idx: int,
    bem: dict,
    properties_by_id: dict[str, dict],
    properties: list[dict],
    workspace_id: str,
) -> tuple[dict, BemReconciliationResult]:
    """Match por substring inclusiva em endereço canônico (logradouro+numero+cidade+uf)."""
    existing_fk = bem.get("imovel_id")
    if existing_fk and not _imovel_id_is_stale(existing_fk, properties_by_id, workspace_id):
        return bem, BemReconciliationResult(idx, "imovel", "idempotent_skip", existing_fk, None)
    cleaned_bem = {**bem, "imovel_id": None} if existing_fk else dict(bem)
    apolice_endereco_norm = _endereco_canonical_from_struct(cleaned_bem.get("endereco"))
    match = _find_property_by_endereco(apolice_endereco_norm, properties)
    if match is None:
        outcome = "stale_cleared" if existing_fk else "no_candidate"
        return cleaned_bem, BemReconciliationResult(idx, "imovel", outcome, None, None)
    cleaned_bem["imovel_id"] = match["id"]
    return cleaned_bem, BemReconciliationResult(idx, "imovel", "matched", match["id"], None)


# ===========================================================================
# Audit summary
# ===========================================================================


def summarize_apolice(results: list[BemReconciliationResult]) -> ApoliceReconciliationSummary:
    matched = sum(1 for r in results if r.outcome == "matched")
    no_cand = sum(1 for r in results if r.outcome == "no_candidate")
    stale = sum(1 for r in results if r.outcome == "stale_cleared")
    idemp = sum(1 for r in results if r.outcome == "idempotent_skip")
    return ApoliceReconciliationSummary(
        total_bens=len(results),
        matched=matched,
        no_candidate=no_cand,
        stale_cleared=stale,
        idempotent_skip=idemp,
    )
