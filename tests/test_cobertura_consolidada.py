"""União documento ∪ cadastro de cobertura (ADR-240 §Emenda 2026-08-08)."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.cobertura_consolidada import consolidar_cobertura
from pipeline.domain.services.protecao_analyzer import (
    FamilyMemberSnapshot,
    ProtecaoInput,
    compute_protecao,
)

REF = date(2026, 6, 1)


def _cadastro(
    categoria: str,
    *,
    status: str = "Ativa",
    starts_at: str = "2025-01-01",
    ends_at: str | None = "2027-01-01",
) -> dict:
    return {
        "id": f"p-{categoria}",
        "category": categoria,
        "holder_family_member_id": None,
        "insurer": "Seguradora Exemplo",
        "coverage_brl_cents": 50_000_00,
        "premium_monthly_brl_cents": 120_00,
        "coverage_type": "term",
        "starts_at": starts_at,
        "ends_at": ends_at,
        "status": status,
    }


def _apolice_com_cobertura_pessoa(tipo: str) -> dict:
    return {
        "apolice_numero": "VIDA-1",
        "bens_segurados": [{"tipo": "pessoa", "coberturas": [{"tipo": tipo}]}],
    }


# ─────────────────────── União ────────────────────────────────────────────


def test_cadastro_sozinho_cobre_a_categoria():
    """O caso que motivou a emenda: cliente cadastrou, não subiu o PDF."""
    cob = consolidar_cobertura([], [_cadastro("vida")], REF)
    assert cob.tem_cobertura("vida") is True
    assert cob.origens("vida") == {"cadastro"}


def test_documento_sozinho_cobre_a_categoria():
    cob = consolidar_cobertura([_apolice_com_cobertura_pessoa("vida")], [], REF)
    assert cob.tem_cobertura("vida") is True
    assert cob.origens("vida") == {"documento"}


def test_duas_fontes_registram_as_duas_origens():
    cob = consolidar_cobertura([_apolice_com_cobertura_pessoa("vida")], [_cadastro("vida")], REF)
    assert cob.origens("vida") == {"documento", "cadastro"}


def test_sem_evidencia_alguma_nao_cobre():
    cob = consolidar_cobertura([], [], REF)
    assert cob.tem_cobertura("vida") is False
    assert cob.origens("vida") == frozenset()


# ─────────────────────── Vigência do cadastro ─────────────────────────────


def test_cadastro_vencido_nao_fecha_o_gap():
    cob = consolidar_cobertura([], [_cadastro("vida", ends_at="2026-01-01")], REF)
    assert cob.tem_cobertura("vida") is False


def test_cadastro_que_ainda_nao_comecou_nao_fecha_o_gap():
    cob = consolidar_cobertura([], [_cadastro("vida", starts_at="2026-12-01")], REF)
    assert cob.tem_cobertura("vida") is False


def test_cadastro_vitalicio_sem_fim_cobre():
    cob = consolidar_cobertura([], [_cadastro("vida", ends_at=None)], REF)
    assert cob.tem_cobertura("vida") is True


def test_cadastro_cancelado_nao_fecha_o_gap():
    cob = consolidar_cobertura([], [_cadastro("vida", status="Cancelada")], REF)
    assert cob.tem_cobertura("vida") is False


# ─────────────────────── Vocabulário deliberadamente parcial ──────────────


def test_invalidez_cadastrada_nao_silencia_gap_de_vida():
    """Produtos distintos: mapear por semelhança fabricaria cobertura."""
    cob = consolidar_cobertura([], [_cadastro("invalidez")], REF)
    assert cob.tem_cobertura("vida") is False


def test_acidentes_no_documento_nao_silencia_gap_de_vida():
    cob = consolidar_cobertura([_apolice_com_cobertura_pessoa("acidentes")], [], REF)
    assert cob.tem_cobertura("vida") is False


# ─────────────────────── Escopo do agregado monetário ─────────────────────


def test_categoria_so_no_cadastro_marca_premio_documental_incompleto():
    cob = consolidar_cobertura([], [_cadastro("vida")], REF)
    assert cob.categorias_somente_no_cadastro() == {"vida"}
    assert cob.premio_documental_e_completo() is False


def test_categoria_fora_do_vocabulario_tambem_marca_incompleto():
    """`patrimonial` não entra na união, mas o prêmio dele existe e falta."""
    cob = consolidar_cobertura([], [_cadastro("patrimonial")], REF)
    assert cob.categorias_somente_no_cadastro() == {"patrimonial"}
    assert cob.premio_documental_e_completo() is False


def test_categoria_presente_nos_dois_lados_nao_marca_incompleto():
    cob = consolidar_cobertura([_apolice_com_cobertura_pessoa("vida")], [_cadastro("vida")], REF)
    assert cob.categorias_somente_no_cadastro() == frozenset()
    assert cob.premio_documental_e_completo() is True


def test_cadastro_vencido_nao_conta_como_escopo_faltante():
    cob = consolidar_cobertura([], [_cadastro("vida", ends_at="2026-01-01")], REF)
    assert cob.premio_documental_e_completo() is True


def test_sem_cadastro_o_premio_documental_e_completo():
    cob = consolidar_cobertura([_apolice_com_cobertura_pessoa("vida")], [], REF)
    assert cob.premio_documental_e_completo() is True


# ─────── Efeito no payload do analyzer (KPI F + escopo do KPI B) ──────────


def _inp(**kwargs) -> ProtecaoInput:
    defaults = dict(
        apolices=[],
        vehicles_by_id={},
        data_referencia=REF,
        renda_anual_liquida_brl=Decimal("100000"),
    )
    defaults.update(kwargs)
    return ProtecaoInput(**defaults)


def _com_dependente_menor(**kwargs) -> ProtecaoInput:
    return _inp(
        family_members=(
            FamilyMemberSnapshot(parentesco="titular", idade=42),
            FamilyMemberSnapshot(parentesco="filho", idade=8, is_dependente=True),
        ),
        **kwargs,
    )


def _apolice_vida_extraida() -> dict:
    return {
        "apolice_numero": "VIDA-1",
        "seguradora": "portoseguro",
        "vigencia_inicio": "2026-01-01",
        "vigencia_fim": "2027-01-01",
        "premio_total_brl": "900.00",
        "bens_segurados": [
            {"tipo": "pessoa", "coberturas": [{"tipo": "vida", "premio_brl": "900.00"}]}
        ],
    }


def _gap(out: dict, categoria: str) -> dict:
    return [g for g in out["gap_qualitativo"] if g["categoria"] == categoria][0]


def test_apolice_de_vida_so_cadastrada_fecha_o_gap():
    """O caso da emenda: antes, a seção afirmava "não identificamos apólice de
    vida ativa" para quem cadastrou a apólice e não subiu o PDF."""
    out = compute_protecao(_com_dependente_menor(cobertura_cadastrada=(_cadastro("vida"),)))
    assert _gap(out, "vida")["flag"] is False
    assert _gap(out, "vida")["rationale"] == "cobertura_vida_cadastrada"


def test_apolice_de_vida_extraida_preserva_o_rationale_historico():
    out = compute_protecao(_com_dependente_menor(apolices=[_apolice_vida_extraida()]))
    assert _gap(out, "vida")["rationale"] == "apolice_vida_ativa"


def test_documento_tem_precedencia_no_rationale_quando_ha_as_duas_fontes():
    out = compute_protecao(
        _com_dependente_menor(
            apolices=[_apolice_vida_extraida()], cobertura_cadastrada=(_cadastro("vida"),)
        )
    )
    assert _gap(out, "vida")["rationale"] == "apolice_vida_ativa"


def test_cadastro_de_invalidez_nao_fecha_o_gap_de_vida_no_payload():
    out = compute_protecao(_com_dependente_menor(cobertura_cadastrada=(_cadastro("invalidez"),)))
    assert _gap(out, "vida")["flag"] is True


def test_cadastro_de_vida_vencido_nao_fecha_o_gap_no_payload():
    out = compute_protecao(
        _com_dependente_menor(cobertura_cadastrada=(_cadastro("vida", ends_at="2026-01-01"),))
    )
    assert _gap(out, "vida")["flag"] is True


def test_cadastro_de_saude_fecha_o_gap_de_saude():
    out = compute_protecao(_inp(cobertura_cadastrada=(_cadastro("saude"),)))
    assert _gap(out, "saude")["flag"] is False
    assert _gap(out, "saude")["rationale"] == "cobertura_saude_cadastrada"


def test_cadastro_nao_entra_na_soma_do_premio():
    """Sem chave de identidade entre as fontes, somar arriscaria dupla-contagem."""
    out = compute_protecao(
        _inp(apolices=[_apolice_vida_extraida()], cobertura_cadastrada=(_cadastro("patrimonial"),))
    )
    assert out["premio_total_anual_brl"] == "900.00"


def test_cobertura_fora_do_documento_suprime_o_veredito_de_pct_renda():
    out = compute_protecao(
        _inp(apolices=[_apolice_vida_extraida()], cobertura_cadastrada=(_cadastro("patrimonial"),))
    )
    escopo = out["escopo_cobertura"]
    assert escopo["veredito_pct_renda_suprimido"] is True
    assert escopo["categorias_somente_no_cadastro"] == ["patrimonial"]
    assert escopo["premio_inclui_cadastro_manual"] is False


def test_sem_cadastro_o_veredito_de_pct_renda_e_emitido():
    """Todo workspace de hoje: sem cadastro, o payload é o pré-emenda."""
    escopo = compute_protecao(_inp(apolices=[_apolice_vida_extraida()]))["escopo_cobertura"]
    assert escopo["veredito_pct_renda_suprimido"] is False
    assert escopo["categorias_somente_no_cadastro"] == []
