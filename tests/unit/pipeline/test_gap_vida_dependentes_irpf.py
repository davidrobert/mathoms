"""Metade (i) do 3c: `gap_qualitativo` reconciliado com `irpf_kpis.dependentes`.

A40.l73 · ADR-395 §D7. Sem `family_members` (ou sem data de nascimento) o
`_flag_vida` devolvia `flag: False` — silêncio que o leitor lê como "sem risco".
Com dependente declarado no IRPF, a ausência de gatilho é `nao_apurado`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pipeline.domain.services.pontos_urgentes_analyzer import _seguro_vida_item
from pipeline.domain.services.protecao_analyzer import (
    FamilyMemberSnapshot,
    ProtecaoInput,
    compute_protecao,
)

REF = date(2026, 6, 1)


def _inp(**kwargs) -> ProtecaoInput:
    defaults = dict(
        apolices=[],
        vehicles_by_id={},
        data_referencia=REF,
        renda_anual_liquida_brl=Decimal("100000"),
    )
    defaults.update(kwargs)
    return ProtecaoInput(**defaults)


def _gap_vida(out: dict) -> dict:
    return [g for g in out["gap_qualitativo"] if g["categoria"] == "vida"][0]


def test_sem_familia_e_sem_irpf_o_estado_segue_o_de_hoje():
    gap = _gap_vida(compute_protecao(_inp()))
    assert gap["flag"] is False
    assert gap["rationale"] == "sem family_members"
    assert gap["status"] == "nao_apurado"


def test_gatilho_ausente_com_familia_apurada_e_apurado():
    """Titular solteiro sem dependente: o conselho não se aplica, e isso é medido."""
    gap = _gap_vida(
        compute_protecao(
            _inp(family_members=(FamilyMemberSnapshot(parentesco="titular", idade=42),))
        )
    )
    assert gap["flag"] is False
    assert gap["rationale"] == "sem gatilho"
    assert gap["status"] == "apurado"


def test_dependente_no_irpf_sem_cadastro_e_nao_apurado():
    """O caso que motiva o item: o IRPF declara dependente, o cadastro não tem."""
    gap = _gap_vida(compute_protecao(_inp(dependentes_irpf_count=2)))
    assert gap["flag"] is False
    assert gap["rationale"] == "dependentes_irpf_sem_cadastro"
    assert gap["status"] == "nao_apurado"


def test_dependente_no_irpf_com_familia_sem_data_de_nascimento_e_nao_apurado():
    """Membro cadastrado sem idade não confirma nem nega dependência menor."""
    gap = _gap_vida(
        compute_protecao(
            _inp(
                family_members=(
                    FamilyMemberSnapshot(parentesco="titular", idade=None),
                    FamilyMemberSnapshot(parentesco="filho", idade=None, is_dependente=True),
                ),
                dependentes_irpf_count=1,
            )
        )
    )
    assert gap["flag"] is False
    assert gap["rationale"] == "dependentes_irpf_sem_cadastro"
    assert gap["status"] == "nao_apurado"


def test_gatilho_disparado_nao_e_sobrescrito_pelo_irpf():
    """Dependente menor cadastrado: o gap é apurado e continua sendo gap."""
    gap = _gap_vida(
        compute_protecao(
            _inp(
                family_members=(
                    FamilyMemberSnapshot(parentesco="titular", idade=42),
                    FamilyMemberSnapshot(parentesco="filho", idade=8, is_dependente=True),
                ),
                dependentes_irpf_count=1,
            )
        )
    )
    assert gap["flag"] is True
    assert gap["rationale"] == "dependentes_menores_18"
    assert gap["status"] == "apurado"


def test_irpf_sem_dependente_nao_cria_nao_apurado():
    """`0` é medida, não ausência — não vira retenção."""
    gap = _gap_vida(
        compute_protecao(
            _inp(
                family_members=(FamilyMemberSnapshot(parentesco="titular", idade=42),),
                dependentes_irpf_count=0,
            )
        )
    )
    assert gap["rationale"] == "sem gatilho"
    assert gap["status"] == "apurado"


# ─────────── pontos_urgentes lê o MESMO estado (senão a contradição muda de casa)


def _payload(rationale: str, status: str) -> dict:
    return {
        "gap_qualitativo": [
            {"categoria": "vida", "flag": False, "rationale": rationale, "status": status}
        ],
        "apolices_vigentes": [],
        "escopo_cobertura": {"categorias_somente_no_cadastro": []},
    }


def test_pontos_urgentes_retem_o_conselho_quando_o_irpf_declara_dependente():
    item = _seguro_vida_item(_payload("dependentes_irpf_sem_cadastro", "nao_apurado"))
    assert item is not None
    assert item.elegibilidade == "pendente_de_dado"
    assert item.origem_premissa == "cadastro_familia"
    assert "IRPF" in (item.dado_faltante or "")


def test_pontos_urgentes_nao_inventa_conselho_quando_o_gatilho_foi_medido():
    assert _seguro_vida_item(_payload("sem gatilho", "apurado")) is None


# ── Percentual em prosa sai pelo produtor único, com vírgula (PD-5 follow-up) ──


def test_taxa_de_endividamento_em_prosa_usa_virgula():
    from pipeline.domain.services.pontos_urgentes_analyzer import PontosUrgentesAnalyzer

    itens = PontosUrgentesAnalyzer().analyze(
        {"taxa_endividamento_pct": 42.5}, {}, {}, protecao=None
    )
    impacto = [i for i in itens if i.code == "endividamento_alto"][0].impacto
    assert "42,5%" in impacto
    assert "42.5%" not in impacto
