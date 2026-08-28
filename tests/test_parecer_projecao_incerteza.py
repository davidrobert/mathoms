"""O manifest projeta a incerteza que o parecer precisa para prescrever (A40.l83 · RV8-05).

O manifest é WHITELIST: campo não declarado não chega ao modelo. Medido no run r8, o
parecer ressalvou 3 de 3 lacunas que o payload declarou e 0 de 1 da que ele não
declarou — logo o defeito é de projeção, não de prompt, e um teste sobre o texto do
prompt mediria o lado errado. Este mede a DECLARAÇÃO, e por isso não depende de o
corpus sintético ter os campos.
"""

from __future__ import annotations

import re

import pytest

from backend.app.services.parecer_ancorabilidade import declared_fields
from backend.app.services.parecer_manifest import load_manifest

# Os seis construídos ao longo da A40 e nunca projetados até esta lane.
CAMPOS_DE_INCERTEZA = (
    "$.patrimonio.investimentos_nao_atribuidos",
    "$.patrimonio.cobertura_investimentos[*]",
    "$.patrimonio.pl_ressalva",
    "$.patrimonio.guarda_de_sinal.motivo_supressao",
    "$.investimentos.nao_classificado_pct",
    "$.diagnostico_confianca.nivel",
)

# A40.l80 (ADR-412 §D7): o eixo de atribuição existia no E5 desde o PR3a e não era
# projetado — o modelo recebia o valor BRL da fatia órfã e nunca o veredito de piso
# que decide se ela é material.
CAMPOS_DE_ATRIBUICAO = (
    "$.patrimonio.atribuicao_investimentos.pct_carteira_financeira",
    "$.patrimonio.atribuicao_investimentos.motivo",
)


def _paths_declarados(manifest) -> set[str]:
    """Todo path que algum bloco do manifest projeta (campo, escalar ou tabela)."""
    out: set[str] = set()
    for section in manifest.sections:
        for block in section.get("blocks", []) or []:
            if block.get("path"):
                out.add(block["path"])
            out.update(f["path"] for f in declared_fields(block) if f.get("path"))
    return out


@pytest.mark.parametrize("path", CAMPOS_DE_INCERTEZA)
def test_campo_de_incerteza_e_projetado(path):
    assert path in _paths_declarados(load_manifest())


def test_hints_de_incerteza_so_citam_path_projetado():
    """Hint que aponta para path não projetado instrui sobre dado que o modelo não tem —
    o defeito que o changelog do manifest já registra ('não existe $.composicao_familiar
    no E5' virou falso). Aqui ele não pode reaparecer em silêncio."""
    manifest = load_manifest()
    declarados = _paths_declarados(manifest)
    patrimonio = next(s for s in manifest.sections if s["id"] == "patrimonio")
    citados = {
        token.rstrip(".,;:)")
        for hint in patrimonio["narrative_hints"]
        for token in hint.split()
        if token.startswith("$.")
    }
    assert citados, "nenhum hint cita path — a asserção ficaria vazia"
    assert citados <= declarados, f"hint cita path não projetado: {sorted(citados - declarados)}"


# ---------------------------------------------------------------------------
# A40.l80 · ADR-412 §D7 — o manifest para de reensinar o limiar
# ---------------------------------------------------------------------------

# Este comentário afirmava que `$.diagnostico_confianca.nivel` mantinha os degraus "por
# decisão da ADR-353", e escopava o teste ao bloco cambial por isso. Medido em
# 2026-08-28: a ADR-353 está em `status: Proposto` — não há decisão — e o "não recalcule"
# é texto que a própria A40 pôs no prompt (l83), não dela. Pior, o critério que o próprio
# comentário enunciava — régua AO LADO do número cru — descrevia o caso excluído: a label
# do `nivel` trazia a escada e o `share_nao_identificado_pct` era projetado na linha
# seguinte. O teste se escusava justamente do que ele definia.
_LIMIAR_NA_LABEL = re.compile(r">=\s*\d|<=\s*\d|<\s*\d+\s*%|>\s*\d+\s*%|\d+\s*-\s*\d+\s*%")


@pytest.mark.parametrize("path", CAMPOS_DE_ATRIBUICAO)
def test_campo_de_atribuicao_e_projetado(path):
    """O veredito de piso da fatia órfã chega ao modelo, não só o valor em BRL."""
    assert path in _paths_declarados(load_manifest())


def _labels_projetadas(manifest) -> list[tuple[str, str]]:
    return [
        (str(f.get("path") or ""), f.get("label") or "")
        for section in manifest.sections
        for block in section.get("blocks", []) or []
        for f in declared_fields(block)
    ]


# O escopo é o MANIFEST INTEIRO, não um bloco: limiar canônico tem leitor único
# (`kpi_target_catalog`, ADR-399), então repeti-lo em qualquer label é cópia a mais. A
# versão anterior media só `$.exposicao_cambial.` e passava verde com o único ofensor
# restante do manifest fora do recorte — gate que escolhe o alvo depois de conhecer o
# ofensor não é gate.
def test_nenhuma_label_do_manifest_reensina_limiar():
    """Mata: régua na label ao lado do número cru — o modelo declara a faixa sozinho."""
    projetadas = _labels_projetadas(load_manifest())

    assert projetadas, "manifest sem labels — o teste ficaria vacuoso"
    ofensores = [(p, lbl) for p, lbl in projetadas if _LIMIAR_NA_LABEL.search(lbl)]
    assert not ofensores, f"label reensina limiar: {ofensores}"


def test_label_do_pct_cambial_declara_a_base():
    """Todo percentual declara a base (hint A37.l9) — e a dela inclui a fatia sem dono."""
    manifest = load_manifest()
    label = next(
        f.get("label") or ""
        for section in manifest.sections
        for block in section.get("blocks", []) or []
        for f in declared_fields(block)
        if f.get("path") == "$.exposicao_cambial.pct_investivel_financeiro"
    )

    assert "carteira financeira" in label.lower()
    assert "sem dono" in label.lower()
