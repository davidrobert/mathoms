"""Unit tests for `split_imoveis_with_overrides` (ADR-215 P3 · ADR-235)."""

from __future__ import annotations

from pipeline.domain.services.patrimonio_calculator import (
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    split_imoveis_with_overrides,
)
from pipeline.domain.services.patrimonio_imovel_classifier import (
    split_imoveis_geradores_vs_nao_geradores,
)


def _make_imovel(property_id: str | None, n: float, descricao: str = "Imóvel") -> dict:
    valor = n
    entry: dict = {
        "descricao": descricao,
        "valor_31_12_ano_base": valor,
        "endereco": "",
        "tipo": "imovel",
    }
    if property_id:
        entry["property_id"] = property_id
    return entry


class TestSplitImoveisWithOverrides:
    def test_residencia_via_override(self):
        titular = {
            "imoveis": [
                _make_imovel("p-casa", 1_000_000.0, "Casa Tasso"),
                _make_imovel("p-apto1", 500_000.0, "Apto Paulista"),
            ]
        }
        overrides = {"p-casa": CLASSIFICATION_RESIDENCIA_PRINCIPAL, "p-apto1": "locado"}
        residencia, outros = split_imoveis_with_overrides(
            titular_bens=titular,
            conjuge_bens={},
            overrides_by_property_id=overrides,
        )
        assert residencia == 1_000_000.0
        assert outros == 500_000.0

    def test_residencia_via_conjuge(self):
        """Residência declarada pelo cônjuge — override válido."""
        conjuge = {"imoveis": [_make_imovel("p-casa", 800_000.0)]}
        overrides = {"p-casa": CLASSIFICATION_RESIDENCIA_PRINCIPAL}
        residencia, outros = split_imoveis_with_overrides(
            titular_bens={},
            conjuge_bens=conjuge,
            overrides_by_property_id=overrides,
        )
        assert residencia == 800_000.0
        assert outros == 0.0

    def test_no_overrides_no_keyword_all_to_outros(self):
        """Sem overrides + sem keyword → tudo cai em imoveis_outros (paridade legado)."""
        titular = {"imoveis": [_make_imovel("p1", 100.0), _make_imovel("p2", 200.0)]}
        residencia, outros = split_imoveis_with_overrides(
            titular_bens=titular,
            conjuge_bens={},
            overrides_by_property_id={},
        )
        assert residencia == 0.0
        assert outros == 300.0

    def test_classification_uso_pessoal_goes_to_outros(self):
        """Itens marcados uso_pessoal/locado/etc não viram residência."""
        titular = {"imoveis": [_make_imovel("p1", 100.0)]}
        non_principal = [
            "uso_pessoal",
            "locado",
            "comercial",
            "especulacao",
            "nu_proprietario",  # ADR-235: paridade com uso_pessoal
            "desconhecido",
        ]
        for classification in non_principal:
            r, o = split_imoveis_with_overrides(
                titular_bens=titular,
                conjuge_bens={},
                overrides_by_property_id={"p1": classification},
            )
            assert r == 0.0, f"classification={classification}"
            assert o == 100.0, f"classification={classification}"

    def test_nu_proprietario_goes_to_outros_not_geradores(self):
        """ADR-235: nu_proprietario é cat_2 não-gerador (paridade uso_pessoal)."""
        titular = {
            "imoveis": [
                _make_imovel("p-nu", 800_000.0, "nu-proprietário"),
                _make_imovel("p-locado", 400_000.0, "Apto locado"),
            ]
        }
        overrides = {"p-nu": "nu_proprietario", "p-locado": "locado"}
        geradores, nao_geradores = split_imoveis_geradores_vs_nao_geradores(
            titular_bens=titular, conjuge_bens={}, overrides_by_property_id=overrides
        )
        assert geradores == 400_000.0
        assert nao_geradores == 800_000.0

    def test_property_without_override_goes_to_outros(self):
        """Pós-sunset do fallback keyword (ADR-215 §1): imóvel sem override
        em `workspace_property_overrides` cai em cat_2 — fonte ÚNICA é
        classificação user-driven persistida via UI."""
        titular = {
            "imoveis": [
                _make_imovel("p-marked", 100.0, "marcado override"),
                _make_imovel("p-unmark", 200.0, "casa sem classificação ainda"),
            ]
        }
        r, o = split_imoveis_with_overrides(
            titular_bens=titular,
            conjuge_bens={},
            overrides_by_property_id={"p-marked": "locado"},
        )
        assert r == 0.0
        assert o == 300.0

    def test_real_case_dogfood_5at5(self):
        """Caso real workspace 5@5.com: 1 casa código 12 + 4 apartamentos código 11."""
        titular = {
            "imoveis": [
                _make_imovel("p-casa-tasso", 996_821.46, "CASA - RUA TASSO DA SILVEIRA, 61"),
                _make_imovel("p-apto-paulista", 350_000.00, "APTO BARAO DE CAPANEMA 34"),
                _make_imovel("p-apto-gisele", 212_706.24, "APTO EDIFICIO GISELE 12"),
                _make_imovel("p-cyrela1", 270_000.00, "APTO LIVING CONCEPT"),
                _make_imovel("p-cyrela2", 530_000.00, "APTO LIVING WISH"),
            ]
        }
        overrides = {"p-casa-tasso": CLASSIFICATION_RESIDENCIA_PRINCIPAL}
        residencia, outros = split_imoveis_with_overrides(
            titular_bens=titular,
            conjuge_bens={},
            overrides_by_property_id=overrides,
        )
        assert residencia == 996_821.46
        assert outros == 350_000.00 + 212_706.24 + 270_000.00 + 530_000.00
