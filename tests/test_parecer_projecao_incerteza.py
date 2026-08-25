"""O manifest projeta a incerteza que o parecer precisa para prescrever (A40.l83 · RV8-05).

O manifest é WHITELIST: campo não declarado não chega ao modelo. Medido no run r8, o
parecer ressalvou 3 de 3 lacunas que o payload declarou e 0 de 1 da que ele não
declarou — logo o defeito é de projeção, não de prompt, e um teste sobre o texto do
prompt mediria o lado errado. Este mede a DECLARAÇÃO, e por isso não depende de o
corpus sintético ter os campos.
"""

from __future__ import annotations

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
