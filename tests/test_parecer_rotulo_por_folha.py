"""A40.l49 — rótulo de evidência por folha, não por bloco (ADR-296 emenda)."""

from __future__ import annotations

import pytest

from tests.test_parecer_evidencia_path import _risco_entries, _run
from tests.test_parecer_planejador_golden import make_workspace_e5

_PASSIVA = ("$.passive_income.renda_passiva_anual_brl", "renda_passiva_anual")
_ATIVA_PJ = ("$.passive_income.renda_ativa_pj_excluida_brl", "renda_ativa_pj_excluida")


def _e5_folhas_passive_income() -> dict:
    e5 = make_workspace_e5()
    e5["passive_income"] = {
        **e5.get("passive_income", {}),
        "renda_passiva_anual_brl": 384_000.0,
        "renda_ativa_pj_excluida_brl": 240_000.0,
    }
    return e5


class TestRotuloPorFolha:
    """Dois campos do mesmo bloco ⇒ dois rotulo_ids; mutação root-split falha."""

    @pytest.fixture(autouse=True)
    def _strict(self, monkeypatch):
        monkeypatch.setenv("MATHOMS_PARECER_EVIDENCIA_MODE", "strict")

    def test_duas_folhas_mesmo_root_dois_rotulo_ids(self):
        result, store = _run([_PASSIVA, _ATIVA_PJ], e5=_e5_folhas_passive_income())
        assert result["success"] is True
        artifact = store.read("E6-parecer", "parecer_planejador")
        rotulos = [a["rotulo"] for a in artifact["riscos"][0]["ancoras"]]
        labels = [a["label"] for a in artifact["riscos"][0]["ancoras"]]
        assert rotulos == ["renda_passiva_anual", "renda_ativa_pj_excluida"]
        assert rotulos[0] != rotulos[1]
        assert labels == ["Renda passiva anual", "Renda ativa PJ excluída"]

    def test_rotulo_id_da_folha_verifica_nao_o_root(self):
        """Mutação: se o check voltar a rotulo == root, este caso vira pairing_mismatch."""
        result, store = _run([_PASSIVA], e5=_e5_folhas_passive_income())
        assert result["success"] is True
        assert _risco_entries(store)[0]["outcome"] == "verified"

    def test_root_como_rotulo_de_folha_mapeada_e_pairing_mismatch(self):
        """O comportamento antigo (rotulo = root) agora falha para folha mapeada."""
        result, store = _run(
            [("$.passive_income.renda_passiva_anual_brl", "passive_income")],
            e5=_e5_folhas_passive_income(),
        )
        assert result["status"] == "needs_review"
        assert _risco_entries(store)[0]["outcome"] == "pairing_mismatch"
