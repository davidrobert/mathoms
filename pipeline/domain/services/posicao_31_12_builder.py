"""Builders do breakdown de informes 31/12 para o payload E5 (A17 L3 P4 + A33.l2)."""

from __future__ import annotations

import hashlib
import re

from pipeline.domain.services._tx_identity import normalize_descricao


def build_caixa_me_detalhe(baseline: dict) -> list[dict]:
    """Items Wise/exterior (moeda != BRL) com saldo_brl convertido — A17 L3 P4."""
    entries = baseline.get("informe_pf_saldos_31_12") or []
    return [_caixa_me_item(e) for e in entries if (e.get("moeda") or "BRL") != "BRL"]


def _caixa_me_item(entry: dict) -> dict:
    """Render 1 entry para card S1 — preserva original + PTAX + status."""
    return {
        "descricao": entry.get("descricao") or "",
        "moeda": entry.get("moeda") or "USD",
        "saldo_original": entry.get("saldo_original"),
        "saldo_brl": entry.get("saldo_brl"),
        "taxa_ptax_aplicada": entry.get("taxa_ptax_aplicada"),
        "ptax_data": entry.get("ptax_data"),
        "ptax_status": entry.get("ptax_status") or "missing",
        "codigo_rfb": entry.get("codigo_rfb") or "",
        "ano_base": entry.get("ano_base"),
        "fonte": entry.get("fonte") or "informe_31_12",
        "informe_venceu_extrato": bool(entry.get("informe_venceu_extrato")),
        "divergencia_relevante": bool(entry.get("divergencia_relevante")),
    }


def _as_payload_number(v) -> float | None:
    """Boundary E5 JSON: string decimal do merger → number (convenção do payload E5)."""
    if v is None:
        return None
    return float(v)


# A40.l39 — id ESTÁVEL por linha (natural key do golden_diff + key do React +
# âncora de lineage). Derivado de identidade estrutural (cnpj/conta construída,
# tipo, moeda, fonte, ano) + hash curto da descrição normalizada como
# discriminador — nunca posição na lista, nunca texto livre cru.
def _row_id(*parts: object, desc: str = "") -> str:
    base = ":".join(_slug(p) for p in parts if p not in (None, ""))
    if desc:
        base += "-" + hashlib.sha1(normalize_descricao(desc).encode("utf-8")).hexdigest()[:6]
    return base


def _slug(v: object) -> str:
    s = normalize_descricao(str(v))
    return re.sub(r"_+", "_", "".join(ch if ch.isalnum() else "_" for ch in s)).strip("_")


# Rows de extrato substituídas pelo informe (fonte == "informe_31_12" em
# caixa_detalhes) não repetem — o entry do informe as representa, com
# informe_venceu_extrato acionando o nudge da UI.
def build_posicao_31_12(baseline: dict, caixa_detalhes: list[dict]) -> list[dict]:
    """Card "posição por instituição/moeda" (A33.l2 P4): informe + extrato não coberto."""
    entries = baseline.get("informe_pf_saldos_31_12") or []
    rows = [_posicao_from_informe(e) for e in entries]
    rows.extend(
        _posicao_from_extrato(d)
        for d in caixa_detalhes
        if (d.get("fonte") or "extrato") == "extrato"
    )
    return rows


# Linha de informe: snapshot fiscal certificado — a data É 31/12 do ano-base.
def _posicao_from_informe(entry: dict) -> dict:
    moeda, ano_base = entry.get("moeda") or "BRL", entry.get("ano_base")
    desc, tipo = entry.get("descricao") or "", entry.get("tipo")
    return {
        "id": _row_id("informe", entry.get("cnpj_emissor"), tipo, moeda, ano_base, desc=desc),
        "instituicao": desc or entry.get("cnpj_emissor") or "",
        "moeda": moeda,
        "valor_original": _as_payload_number(entry.get("saldo_original"))
        if moeda != "BRL"
        else None,
        "valor_brl": _as_payload_number(entry.get("saldo_brl")),
        "fonte": "informe_31_12",
        "ptax_data": entry.get("ptax_data"),
        "ptax_status": entry.get("ptax_status"),
        "informe_venceu_extrato": bool(entry.get("informe_venceu_extrato")),
        "divergencia_relevante": bool(entry.get("divergencia_relevante")),
        "ano_base": ano_base,
        "tipo": tipo or "outros",
        **_datas_31_12(ano_base),
    }


# Linha de extrato: fim de período do último reconciliado — a linha NÃO é 31/12.
def _posicao_from_extrato(detalhe: dict) -> dict:
    moeda = detalhe.get("moeda") or "BRL"
    return {
        "id": _row_id("extrato", detalhe.get("conta"), moeda),
        "instituicao": detalhe.get("conta") or "",
        "moeda": moeda,
        "valor_original": detalhe.get("saldo_original") if moeda != "BRL" else None,
        "valor_brl": detalhe.get("valor_brl"),
        "fonte": "extrato",
        "ptax_data": None,
        "ptax_status": None,
        "informe_venceu_extrato": False,
        "divergencia_relevante": False,
        "ano_base": None,
        "tipo": detalhe.get("tipo") or "caixa",
        "data_referencia": detalhe.get("data_referencia"),
        "data_referencia_precisao": detalhe.get("data_referencia_precisao") or "desconhecida",
    }


def _datas_31_12(ano_base) -> dict:
    if not ano_base:
        return {"data_referencia": None, "data_referencia_precisao": "desconhecida"}
    return {"data_referencia": f"{int(ano_base)}-12-31", "data_referencia_precisao": "dia"}
