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
