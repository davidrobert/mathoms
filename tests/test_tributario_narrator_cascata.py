"""Unit tests CTO-05 (emenda ADR-236) — narrate_cascata no caminho perfil-pendente.

Perfil PJ incompleto (`regime=None`) com entradas PJ detectadas no fluxo cita o
valor observado no CTA (sem derivar faturamento); sem receita, cai na mensagem
estática. Nenhum número tributário derivado quando o regime é desconhecido.
"""

from __future__ import annotations

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.tributario_narrator import narrate_cascata


def _ctx() -> NarrativasContext:
    return NarrativasContext.from_family_config(
        {
            "titular": "t",
            "membros": {
                "t": {"papel": "titular", "nome_curto": "Maria"},
                "c": {"papel": "conjuge", "nome_curto": "João"},
            },
        }
    )


def _section_simples(cascata_extra: dict) -> dict:
    return {
        "regime": "simples",
        "regime_label": "Simples Nacional (Anexo III)",
        "cascata": {
            "receita_bruta": 600_000.0,
            "tributos_federais": 40_000.0,
            "carga_total_pct": 0.0667,
            "pgbl_base_anual": 144_000.0,
            "pgbl_limite_anual": 17_280.0,
            **cascata_extra,
        },
    }


# Sem a cláusula, o motivo cai no fall-through genérico ("indisponível"), que
# esconde qual insumo falta — o oposto de nomear a precondição.
def test_declaracao_desconhecida_nao_narra_deducao_como_permitida():
    """ADR-375 D4 cond. 1 — o consumidor da narrativa também precisa do motivo novo."""
    out = narrate_cascata(
        _section_simples(
            {"pgbl_aplicavel": False, "pgbl_motivo_inaplicavel": "tipo_declaracao_desconhecido"}
        ),
        _ctx(),
    )
    assert "modelo de declaração" in out["conclusion"]
    assert "indisponível" not in out["conclusion"]
    assert "permite dedução" not in out["conclusion"]


def test_pgbl_aplicavel_narra_base_e_ponteiro_sem_republicar_teto():
    out = narrate_cascata(
        _section_simples({"pgbl_aplicavel": True, "pgbl_motivo_inaplicavel": None}),
        _ctx(),
    )
    assert "Base PGBL identificada" in out["conclusion"]
    assert "Otimização Tributária" in out["conclusion"]
    assert "17.280" not in out["conclusion"]
    assert "12%" not in out["conclusion"]


def test_perfil_pendente_com_receita_cita_valor_detectado():
    section = {
        "regime": None,
        "cascata": {
            "motivo_nao_suportado": "perfil_incompleto",
            "regime_nao_suportado": True,
            "receita_pj_detectada_anual": 1_000_000.0,
            "signals": ["perfil_incompleto_com_receita"],
        },
    }
    out = narrate_cascata(section, _ctx())
    assert "entradas PJ" in out["context"]
    # fmt_currency abrevia milhões: R$ 1,0M.
    assert "1,0M" in out["context"]
    # Correção CTO-05: deixa explícito que não é faturamento.
    assert "não o faturamento" in out["conclusion"]


def test_perfil_pendente_sem_receita_usa_mensagem_estatica():
    section = {
        "regime": None,
        "cascata": {
            "motivo_nao_suportado": "perfil_incompleto",
            "regime_nao_suportado": True,
            "receita_pj_detectada_anual": 0,
        },
    }
    out = narrate_cascata(section, _ctx())
    assert "Perfil tributário PJ pendente" in out["context"]
    assert out["conclusion"] == ""


def test_section_ausente_usa_mensagem_estatica():
    out = narrate_cascata(None, _ctx())
    assert "Perfil tributário PJ pendente" in out["context"]
