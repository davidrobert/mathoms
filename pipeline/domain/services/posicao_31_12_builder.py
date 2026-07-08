"""Builders do breakdown de informes 31/12 para o payload E5 (A17 L3 P4 + A33.l2)."""

from __future__ import annotations


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


def _posicao_from_informe(entry: dict) -> dict:
    moeda = entry.get("moeda") or "BRL"
    valor_original = _as_payload_number(entry.get("saldo_original")) if moeda != "BRL" else None
    return {
        "instituicao": entry.get("descricao") or entry.get("cnpj_emissor") or "",
        "moeda": moeda,
        "valor_original": valor_original,
        "valor_brl": _as_payload_number(entry.get("saldo_brl")),
        "fonte": "informe_31_12",
        "ptax_data": entry.get("ptax_data"),
        "ptax_status": entry.get("ptax_status"),
        "informe_venceu_extrato": bool(entry.get("informe_venceu_extrato")),
        "divergencia_relevante": bool(entry.get("divergencia_relevante")),
        "ano_base": entry.get("ano_base"),
        "tipo": entry.get("tipo") or "outros",
    }


def _posicao_from_extrato(detalhe: dict) -> dict:
    moeda = detalhe.get("moeda") or "BRL"
    return {
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
    }
