"""Unit tests para ``IrpfDeclarationDeduplicator`` — política do data-engineer."""

# Cobertura: score-based winner por (cpf_masked, ano_base, natureza); tie-break
# por tie_break_key; shell declarations; name_divergence (> 0.3); cross_cpf_same_name;
# idempotência. Regressão do workspace 1b9f2cf5: 7 fragmentos DAVID -36 ano 2025
# + 1 fragmento -87 (OCR ruim) → 1 winner por CPF + warning cross-CPF.

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.irpf_declaration_deduplicator import (
    DeduplicatedIRPFSet,
    IrpfFragment,
    deduplicate_irpf_declarations,
)
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoRendimentoIsento,
    Contribuinte,
    FontePagadoraPJ,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    RendimentoIsento,
)


def _zero_imposto() -> ImpostoApurado:
    return ImpostoApurado(
        base_calculo_brl=Decimal("0"),
        ir_devido_brl=Decimal("0"),
        deducoes_totais_brl=Decimal("0"),
        ir_pago_brl=Decimal("0"),
        ir_a_pagar_brl=Decimal("0"),
    )


def _build_pj_list(n: int) -> list[FontePagadoraPJ]:
    return [
        FontePagadoraPJ(
            cnpj="**.***.***/****-**",
            nome=f"PJ {i}",
            rendimentos_tributaveis_brl=Decimal("1000"),
            contrib_previdenciaria_brl=Decimal("0"),
            ir_retido_brl=Decimal("0"),
        )
        for i in range(n)
    ]


def _build_iso_list(n: int) -> list[RendimentoIsento]:
    return [
        RendimentoIsento(
            codigo_rfb=CodigoRendimentoIsento.lucros_dividendos,
            descricao=f"isento {i}",
            valor_brl=Decimal("500"),
        )
        for i in range(n)
    ]


def _make_contribuinte(
    cpf: str, nome: str, ano: int, natureza: NaturezaContribuinte
) -> Contribuinte:
    return Contribuinte(
        cpf_masked=cpf,
        nome=nome,
        ano_base=ano,
        exercicio=ano + 1,
        modelo=ModeloDeclaracao.completo,
        natureza=natureza,
    )


def _make_decl(
    *,
    cpf: str = "***.***.***-36",
    nome: str = "DAVID ROBERT MARTINS ANDRADE SILVA",
    ano: int = 2025,
    natureza: NaturezaContribuinte = NaturezaContribuinte.titular,
    pj: int = 0,
    iso: int = 0,
) -> IRPFFullOutput:
    return IRPFFullOutput(
        contribuinte=_make_contribuinte(cpf, nome, ano, natureza),
        rendimentos_pj=_build_pj_list(pj),
        rendimentos_isentos=_build_iso_list(iso),
        imposto_apurado=_zero_imposto(),
        confidence=0.95,
    )


def _frag(decl: IRPFFullOutput, tie: str = "") -> IrpfFragment:
    return IrpfFragment(declaration=decl, tie_break_key=tie)


# -----------------------------------------------------------------------------
# Score-based winner
# -----------------------------------------------------------------------------


def test_single_fragment_no_dedup():
    decl = _make_decl(pj=2, iso=3)
    result = deduplicate_irpf_declarations([_frag(decl)])
    assert len(result.winners) == 1
    assert result.winners[0] is decl
    assert result.discarded == []
    assert result.collisions == []


def test_higher_score_wins():
    rich = _make_decl(pj=2, iso=3)  # score = 5
    poor = _make_decl(pj=0, iso=1)  # score = 1
    result = deduplicate_irpf_declarations([_frag(poor, "a"), _frag(rich, "b")])
    assert len(result.winners) == 1
    assert result.winners[0] is rich
    assert len(result.discarded) == 1
    assert result.discarded[0].declaration is poor
    assert result.discarded[0].reason == "lower_score"


def test_shell_declaration_discarded_with_reason():
    rich = _make_decl(pj=2)
    shell = _make_decl(pj=0, iso=0)  # tudo vazio
    result = deduplicate_irpf_declarations([_frag(rich, "a"), _frag(shell, "b")])
    discarded_reasons = {d.reason for d in result.discarded}
    assert "shell_declaration" in discarded_reasons


def test_two_shells_lose_tie_break_not_shell():
    # 2 shells: ambas score=0. Vencedor é shell tb — outra fica como
    # `lost_tie_break` OU `shell_declaration` (ambas válidas; shell vem antes).
    shell_a = _make_decl(pj=0, iso=0)
    shell_b = _make_decl(pj=0, iso=0)
    result = deduplicate_irpf_declarations([_frag(shell_a, "a"), _frag(shell_b, "b")])
    assert len(result.winners) == 1
    assert len(result.discarded) == 1
    assert result.discarded[0].reason == "shell_declaration"


# -----------------------------------------------------------------------------
# Tie-break por tie_break_key
# -----------------------------------------------------------------------------


def test_tie_break_higher_key_wins():
    a = _make_decl(pj=1, iso=1)  # score = 2
    b = _make_decl(pj=1, iso=1)  # score = 2 (mesmo)
    result = deduplicate_irpf_declarations([_frag(a, "2026-05-23"), _frag(b, "2026-05-24")])
    assert result.winners[0] is b
    assert result.discarded[0].declaration is a
    assert result.discarded[0].reason == "lost_tie_break"


# -----------------------------------------------------------------------------
# Group key: (cpf, ano, natureza)
# -----------------------------------------------------------------------------


def test_different_cpf_no_dedup():
    david = _make_decl(cpf="***.***.***-36", nome="DAVID", pj=2)
    mariana = _make_decl(cpf="***.***.***-60", nome="MARIANA", pj=2)
    result = deduplicate_irpf_declarations([_frag(david), _frag(mariana)])
    assert len(result.winners) == 2
    assert result.discarded == []


def test_different_ano_no_dedup():
    y23 = _make_decl(ano=2023, pj=2)
    y24 = _make_decl(ano=2024, pj=2)
    result = deduplicate_irpf_declarations([_frag(y23), _frag(y24)])
    assert len(result.winners) == 2


def test_different_natureza_no_dedup():
    titular = _make_decl(natureza=NaturezaContribuinte.titular, pj=2)
    dep = _make_decl(natureza=NaturezaContribuinte.dependente_titular, pj=2)
    result = deduplicate_irpf_declarations([_frag(titular), _frag(dep)])
    assert len(result.winners) == 2


# -----------------------------------------------------------------------------
# Collision warnings — name_divergence
# -----------------------------------------------------------------------------


def test_name_divergence_emits_collision_warning():
    a = _make_decl(nome="JOAO DA SILVA SANTOS", pj=1)
    b = _make_decl(nome="MARIA OLIVEIRA PEREIRA", pj=2)  # nome muito diferente
    # mesmo CPF mascarado mas nomes irreconciliáveis → potencial colisão de
    # último dígito; queremos warning.
    result = deduplicate_irpf_declarations([_frag(a), _frag(b)])
    name_div = [c for c in result.collisions if c.kind == "name_divergence"]
    assert len(name_div) == 1
    assert name_div[0].cpf_masked == "***.***.***-36"
    assert name_div[0].ano_base == 2025


def test_small_name_variation_no_warning():
    # Caso real: "DAVID ROBERT MARTINS ANDRADE SILVA" vs "DAVID ROBERT
    # MARTINS DE SILVA" — diferença ~7/36 ≈ 0.19, abaixo do threshold 0.3.
    a = _make_decl(nome="DAVID ROBERT MARTINS ANDRADE SILVA", pj=1)
    b = _make_decl(nome="DAVID ROBERT MARTINS DE SILVA", pj=2)
    result = deduplicate_irpf_declarations([_frag(a), _frag(b)])
    name_div = [c for c in result.collisions if c.kind == "name_divergence"]
    assert name_div == []
    assert len(result.winners) == 1
    assert result.winners[0] is b  # maior score (pj=2)


def test_name_divergence_threshold_configurable():
    a = _make_decl(nome="DAVID CAMPOS", pj=1)
    b = _make_decl(nome="DAVID PEREIRA", pj=1)
    # Threshold 0.5 (alto) — abaixo de divergência típica, sem warning.
    result = deduplicate_irpf_declarations([_frag(a), _frag(b)], name_divergence_threshold=0.9)
    assert [c for c in result.collisions if c.kind == "name_divergence"] == []


# -----------------------------------------------------------------------------
# Collision warnings — cross_cpf_same_name
# -----------------------------------------------------------------------------


def test_cross_cpf_same_name_emits_warning():
    # Caso real do workspace: DAVID -36 e DAVID -87 (OCR ruim no último dígito).
    d36 = _make_decl(cpf="***.***.***-36", nome="DAVID ROBERT", pj=2)
    d87 = _make_decl(cpf="***.***.***-87", nome="DAVID ROBERT", pj=1)
    result = deduplicate_irpf_declarations([_frag(d36), _frag(d87)])
    cross = [c for c in result.collisions if c.kind == "cross_cpf_same_name"]
    assert len(cross) == 1
    assert "-36" in cross[0].cpf_masked and "-87" in cross[0].cpf_masked


def test_cross_cpf_normalization_ignores_accents():
    a = _make_decl(cpf="***.***.***-11", nome="João da Silva", pj=1)
    b = _make_decl(cpf="***.***.***-22", nome="JOAO DA SILVA", pj=1)
    result = deduplicate_irpf_declarations([_frag(a), _frag(b)])
    cross = [c for c in result.collisions if c.kind == "cross_cpf_same_name"]
    assert len(cross) == 1


# -----------------------------------------------------------------------------
# Regressão — workspace 1b9f2cf5
# -----------------------------------------------------------------------------


def _build_workspace_1b9f2cf5_fragments() -> list[IrpfFragment]:
    """7 frags DAVID -36 (pj/iso variando) + 1 shell -87 (OCR ruim no dígito)."""
    cpf_36 = "***.***.***-36"
    decls = [
        _make_decl(cpf=cpf_36, pj=0, iso=2),
        _make_decl(cpf=cpf_36, pj=1, iso=0),
        _make_decl(cpf=cpf_36, pj=1, iso=2),  # winner do grupo -36
        _make_decl(cpf=cpf_36, pj=0, iso=1),
        _make_decl(cpf=cpf_36, pj=0, iso=0),  # shell
        _make_decl(cpf=cpf_36, pj=0, iso=0),  # shell
        _make_decl(cpf=cpf_36, pj=0, iso=0),  # shell
        _make_decl(cpf="***.***.***-87", pj=0, iso=0),  # OCR mismatch
    ]
    return [_frag(d, str(i)) for i, d in enumerate(decls)]


def test_regression_workspace_1b9f2cf5_year_2025_winners():
    # 1 winner por CPF (não fundimos cross-CPF mesmo com nome igual).
    result = deduplicate_irpf_declarations(_build_workspace_1b9f2cf5_fragments())
    cpfs = sorted(d.contribuinte.cpf_masked for d in result.winners)
    assert cpfs == ["***.***.***-36", "***.***.***-87"]


def test_regression_workspace_1b9f2cf5_year_2025_winner_36_richest():
    # Winner do grupo -36 deve ter o fragmento mais rico (pj=1 + iso=2).
    result = deduplicate_irpf_declarations(_build_workspace_1b9f2cf5_fragments())
    winner_36 = next(d for d in result.winners if d.contribuinte.cpf_masked == "***.***.***-36")
    assert len(winner_36.rendimentos_pj) == 1
    assert len(winner_36.rendimentos_isentos) == 2


def test_regression_workspace_1b9f2cf5_year_2025_six_discarded():
    # 7 fragmentos -36 → 1 winner + 6 descartados.
    result = deduplicate_irpf_declarations(_build_workspace_1b9f2cf5_fragments())
    discarded_36 = [
        d for d in result.discarded if d.declaration.contribuinte.cpf_masked == "***.***.***-36"
    ]
    assert len(discarded_36) == 6


def test_regression_workspace_1b9f2cf5_year_2025_cross_cpf_warning():
    # Mesmo nome canônico em -36 e -87 → emite warning cross_cpf_same_name.
    result = deduplicate_irpf_declarations(_build_workspace_1b9f2cf5_fragments())
    cross = [c for c in result.collisions if c.kind == "cross_cpf_same_name"]
    assert len(cross) == 1


# -----------------------------------------------------------------------------
# Idempotência
# -----------------------------------------------------------------------------


def test_dedup_is_idempotent():
    """Aplicar dedup duas vezes produz o mesmo set de winners."""
    decls = [
        _make_decl(pj=2, iso=1),
        _make_decl(pj=1, iso=0),
        _make_decl(pj=0, iso=0),
    ]
    first = deduplicate_irpf_declarations([_frag(d, str(i)) for i, d in enumerate(decls)])
    second = deduplicate_irpf_declarations([_frag(w, str(i)) for i, w in enumerate(first.winners)])
    assert [w.contribuinte.cpf_masked for w in first.winners] == [
        w.contribuinte.cpf_masked for w in second.winners
    ]
    assert len(first.winners) == len(second.winners)


def test_empty_input():
    result = deduplicate_irpf_declarations([])
    assert isinstance(result, DeduplicatedIRPFSet)
    assert result.winners == []
    assert result.discarded == []
    assert result.collisions == []
