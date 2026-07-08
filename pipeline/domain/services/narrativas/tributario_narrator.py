"""Narrativas da cascata fiscal PJ — ramifica por regime (ADR-236 §D4)."""

from __future__ import annotations

from typing import Any, Mapping, TypedDict

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import fmt_currency, fmt_percent


class WiseFiscalFlagsNarrative(TypedDict):
    """Forma da narrativa agregada de Wise fiscal flags (A17 L3 P5)."""

    context: str
    conclusion: str
    items: list[dict[str, str | bool]]
    # A33.l2 (anti-fadiga, co-design financial-planner 2026-07-07): needs_review
    # agregados por informe num bloco único — "N pontos a revisar com contador".
    pontos_revisao: int


_PERFIL_PENDENTE: dict[str, str] = {
    "context": (
        "Perfil tributário PJ pendente — peça ao seu consultor preencher "
        "regime, anexo (Simples), CNAE e modelo de declaração IRPF para ver "
        "a cascata fiscal completa."
    ),
    "conclusion": "",
}


def narrate_cascata(section: Mapping[str, Any] | None, ctx: NarrativasContext) -> dict[str, str]:
    """Narrativa do card impostos_pj — ramifica por regime ([[ADR-236]] §D4)."""
    if not section:
        return _PERFIL_PENDENTE
    cascata = section.get("cascata") or {}
    regime = section.get("regime")
    if _is_perfil_pendente(section, cascata):
        return _PERFIL_PENDENTE
    if cascata.get("regime_nao_suportado"):
        return _narrate_regime_nao_suportado(cascata)
    return _dispatch_regime(regime, cascata, section.get("regime_label", ""), ctx)


def _dispatch_regime(
    regime: Any, cascata: Mapping[str, Any], regime_label: str, ctx: NarrativasContext
) -> dict[str, str]:
    if regime == "simples":
        return _narrate_simples(cascata, regime_label, ctx)
    if regime == "lucro_presumido":
        return _narrate_presumido(cascata, regime_label, ctx)
    if regime == "mei":
        return _narrate_mei(cascata, regime_label, ctx)
    return _PERFIL_PENDENTE


def _is_perfil_pendente(section: Mapping[str, Any], cascata: Mapping[str, Any]) -> bool:
    if not section or section.get("regime") is None:
        return True
    return cascata.get("motivo_nao_suportado") in (
        "perfil_incompleto",
        "anexo_simples_pendente",
    )


def _narrate_regime_nao_suportado(cascata: Mapping[str, Any]) -> dict[str, str]:
    if cascata.get("motivo_nao_suportado") == "lucro_real":
        return {
            "context": (
                "Regime Lucro Real exige escrituração contábil completa (LALUR, "
                "depreciações, ajustes IRPJ) — fora do escopo desta cascata na "
                "versão atual."
            ),
            "conclusion": (
                "A versão V2 da cascata cobrirá Lucro Real. Por enquanto, "
                "trabalhe diretamente com seu contador para os números detalhados."
            ),
        }
    return _PERFIL_PENDENTE


def _fmt_money_safe(value: Any) -> str:
    return fmt_currency(value or 0)


def _fmt_pct_safe(value: Any) -> str:
    if value is None:
        return fmt_percent(0)
    return fmt_percent(float(value) * 100)


def _fmt_fator_r(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value) * 100:.1f}%"


def _triggers_summary(cascata: Mapping[str, Any]) -> str:
    triggers = cascata.get("triggers") or []
    if not triggers:
        return ""
    codes = [t.get("code") for t in triggers if isinstance(t, dict) and t.get("code")]
    if not codes:
        return ""
    return f" Sinalizadores ativos: {', '.join(codes)}."


def _pgbl_clause(cascata: Mapping[str, Any]) -> str:
    aplicavel = cascata.get("pgbl_aplicavel")
    limite = cascata.get("pgbl_limite_anual") or 0
    motivo = cascata.get("pgbl_motivo_inaplicavel")
    if aplicavel and limite > 0:
        return (
            f"Base PGBL (renda tributável PF) permite dedução de até "
            f"{_fmt_money_safe(limite)}/ano (limite 12% da base)."
        )
    if motivo == "declaracao_simplificada":
        return (
            "PGBL não dedutível: declaração simplificada foi escolhida "
            "(desconto simplificado substitui deduções legais)."
        )
    if motivo == "renda_tributavel_pf_zerada":
        return (
            "Base PGBL ainda não detectada — IRPF processado é necessário "
            "para calcular a renda tributável PF."
        )
    return "Base PGBL indisponível neste momento."


def _narrate_simples(
    cascata: Mapping[str, Any], regime_label: str, ctx: NarrativasContext
) -> dict[str, str]:
    receita = _fmt_money_safe(cascata.get("receita_bruta"))
    tributos = _fmt_money_safe(cascata.get("tributos_federais"))
    carga = _fmt_pct_safe(cascata.get("carga_total_pct"))
    fator_r_pct = _fmt_fator_r(cascata.get("fator_r_pct"))
    fator_str = f" Fator-R: {fator_r_pct}." if fator_r_pct else ""
    return {
        "context": (
            f"Cascata fiscal de {ctx.titular_nome} — {regime_label}: "
            f"receita PJ anualizada de {receita}, tributos federais (DAS) "
            f"de {tributos}/ano.{fator_str}"
        ),
        "conclusion": (
            f"Carga tributária total estimada em {carga} da receita. "
            f"{_pgbl_clause(cascata)}{_triggers_summary(cascata)}"
        ),
    }


def _narrate_presumido(
    cascata: Mapping[str, Any], regime_label: str, ctx: NarrativasContext
) -> dict[str, str]:
    receita = _fmt_money_safe(cascata.get("receita_bruta"))
    tributos = _fmt_money_safe(cascata.get("tributos_federais"))
    iss = _fmt_money_safe(cascata.get("iss_total"))
    carga = _fmt_pct_safe(cascata.get("carga_total_pct"))
    iss_clause = f" ISS destacado: {iss}/ano." if (cascata.get("iss_total") or 0) > 0 else ""
    return {
        "context": (
            f"Cascata fiscal de {ctx.titular_nome} — {regime_label}: "
            f"receita PJ anualizada de {receita}, tributos federais "
            f"(PIS+COFINS+IRPJ+CSLL) de {tributos}/ano.{iss_clause}"
        ),
        "conclusion": (
            f"Carga tributária total estimada em {carga} da receita. "
            f"{_pgbl_clause(cascata)}{_triggers_summary(cascata)}"
        ),
    }


def _narrate_mei(
    cascata: Mapping[str, Any], regime_label: str, ctx: NarrativasContext
) -> dict[str, str]:
    receita = _fmt_money_safe(cascata.get("receita_bruta"))
    das_anual = _fmt_money_safe(cascata.get("tributos_federais"))
    carga = _fmt_pct_safe(cascata.get("carga_total_pct"))
    return {
        "context": (
            f"Cascata fiscal de {ctx.titular_nome} — {regime_label}: "
            f"receita PJ anualizada de {receita}, DAS-MEI fixo de {das_anual}/ano."
        ),
        "conclusion": (
            f"Carga tributária total estimada em {carga} da receita. "
            f"{_pgbl_clause(cascata)}{_triggers_summary(cascata)}"
        ),
    }


# ─────────────────────── Wise fiscal flags (A17 L3 P5 · ADR-238 §D1) ─────────


def narrate_wise_fiscal_flags(
    flags: list[Mapping[str, Any]] | None, ctx: NarrativasContext
) -> WiseFiscalFlagsNarrative:
    """Narrativa agregada para `wise_fiscal_flags[]` — fact-check fiscal Wise/exterior."""
    if not flags:
        return WiseFiscalFlagsNarrative(context="", conclusion="", items=[], pontos_revisao=0)
    items = [_render_flag_item(f) for f in flags]
    pontos_revisao = sum(1 for f in flags if f.get("needs_review"))
    summary = _summarize_flags(flags, ctx, pontos_revisao)
    return WiseFiscalFlagsNarrative(
        context=summary["context"],
        conclusion=summary["conclusion"],
        items=items,
        pontos_revisao=pontos_revisao,
    )


def _render_flag_item(flag: Mapping[str, Any]) -> dict[str, str | bool]:
    return {
        "code": str(flag.get("code") or ""),
        "severity": str(flag.get("severity") or "info"),
        "title": str(flag.get("title") or ""),
        "descricao": str(flag.get("descricao") or ""),
        "needs_review": bool(flag.get("needs_review")),
    }


def _summarize_flags(
    flags: list[Mapping[str, Any]], ctx: NarrativasContext, pontos_revisao: int
) -> dict[str, str]:
    codes = sorted({str(f.get("code") or "") for f in flags if f.get("code")})
    labels = ", ".join(_CODE_LABEL.get(c, c) for c in codes)
    return {
        "context": (
            f"Sinalizadores fiscais detectados em informes do exterior de "
            f"{ctx.titular_nome}: {labels}. Cada item abaixo é fact-check — "
            f"Mathoms não calcula, não recolhe, apenas alerta."
        ),
        "conclusion": _conclusion_flags(pontos_revisao),
    }


def _conclusion_flags(pontos_revisao: int) -> str:
    base = (
        "Confirme com seu contador se as obrigações vigentes (CBE BACEN, "
        "carnê-leão mensal, GCAP cambial em DARF) já foram cumpridas no "
        "ano-base referenciado."
    )
    if pontos_revisao == 0:
        return base
    plural = "ponto" if pontos_revisao == 1 else "pontos"
    return f"{pontos_revisao} {plural} a revisar com contador. {base}"


_CODE_LABEL: dict[str, str] = {
    "CBE": "Capital Brasileiro no Exterior",
    "CARNELEAO": "Carnê-leão (juros do exterior)",
    "GCAP": "GCAP cambial",
    "GCAP_ISENTO": "Variação cambial em isentos",
    "RFB41_ME": "Conta em ME com código doméstico",
}
