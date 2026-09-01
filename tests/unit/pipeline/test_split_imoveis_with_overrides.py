"""Unit tests for `split_imoveis_with_overrides` (ADR-215 P3 · ADR-235)."""

from __future__ import annotations

from pipeline.domain.services.patrimonio_calculator import (
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    split_imoveis_with_overrides,
)
from pipeline.domain.services.patrimonio_imovel_classifier import (
    split_imoveis_alocacao_vs_fora,
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
                _make_imovel("p-casa", 1_000_000.0, "Casa Exemplo"),
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
                _make_imovel("p-casa-exemplo", 996_821.46, "CASA - RUA EXEMPLO, 100"),
                _make_imovel("p-apto-paulista", 350_000.00, "APTO EXEMPLO C 34"),
                _make_imovel("p-apto-exemplo-d", 212_706.24, "APTO EDIFICIO EXEMPLO D 12"),
                _make_imovel("p-cyrela1", 270_000.00, "APTO COND EXEMPLO A"),
                _make_imovel("p-cyrela2", 530_000.00, "APTO COND EXEMPLO B"),
            ]
        }
        overrides = {"p-casa-exemplo": CLASSIFICATION_RESIDENCIA_PRINCIPAL}
        residencia, outros = split_imoveis_with_overrides(
            titular_bens=titular,
            conjuge_bens={},
            overrides_by_property_id=overrides,
        )
        assert residencia == 996_821.46
        assert outros == 350_000.00 + 212_706.24 + 270_000.00 + 530_000.00


def test_calculator_reexporta_o_vocabulario_inteiro_de_classification():
    # ADR-235: `nu_proprietario` não era símbolo morto — era a única das sete que o
    # re-export esquecia. Quem lesse `patrimonio_calculator.__all__` concluiria que o
    # enum tem seis valores. Igualdade de conjunto fecha a CLASSE, não a instância.
    from pipeline.domain.services import patrimonio_calculator as calc
    from pipeline.domain.services import patrimonio_imovel_classifier as classifier

    do_classifier = {n for n in dir(classifier) if n.startswith("CLASSIFICATION_")}
    reexportadas = {n for n in calc.__all__ if n.startswith("CLASSIFICATION_")}

    assert do_classifier, "o classifier deixou de exportar o vocabulário"
    assert do_classifier == reexportadas, (
        f"re-export incompleto — só no classifier: {sorted(do_classifier - reexportadas)}; "
        f"só no calculator: {sorted(reexportadas - do_classifier)}"
    )


# ---------------------------------------------------------------------------
# Rebalanceabilidade ([[ADR-420]] §D1) — o eixo que o dogfood NÃO cobre inteiro
# ---------------------------------------------------------------------------


# A fixture end-to-end não tem `residencia_principal` (residencia = 0 no golden), então
# a exclusão de cat_1 dos DOIS lados é invisível lá: medido — apagar o `continue` do
# splitter deixava a suíte de golden inteira VERDE. Aqui ela tem testemunha.
class TestSplitPorRebalanceabilidade:
    def _bens(self, *pares: tuple[str, float]) -> dict:
        return {"imoveis": [_make_imovel(pid, valor, pid) for pid, valor in pares]}

    def _overrides(self) -> dict[str, str]:
        return {
            "casa": CLASSIFICATION_RESIDENCIA_PRINCIPAL,
            "sala": "locado",
            "terreno": "especulacao",
            "praia": "uso_pessoal",
            "nua": "nu_proprietario",
        }

    def test_residencia_fica_fora_dos_DOIS_lados(self):
        bens = self._bens(("casa", 500_000.0), ("sala", 150_000.0))

        alocacao, fora = split_imoveis_alocacao_vs_fora(
            titular_bens=bens, conjuge_bens={}, overrides_by_property_id=self._overrides()
        )

        assert alocacao == 150_000.0
        assert fora == 0.0
        assert alocacao + fora == 150_000.0, "a residência vazou para dentro de cat_2"

    def test_especulacao_FICA_e_uso_pessoal_SAI(self):
        bens = self._bens(("terreno", 100_000.0), ("praia", 70_000.0))

        alocacao, fora = split_imoveis_alocacao_vs_fora(
            titular_bens=bens, conjuge_bens={}, overrides_by_property_id=self._overrides()
        )

        assert alocacao == 100_000.0, "cortar por geração poria especulação fora"
        assert fora == 70_000.0

    def test_nu_proprietario_sai(self):
        bens = self._bens(("nua", 90_000.0))

        assert split_imoveis_alocacao_vs_fora(
            titular_bens=bens, conjuge_bens={}, overrides_by_property_id=self._overrides()
        ) == (0.0, 90_000.0)

    def test_imovel_sem_override_cai_na_alocacao(self):
        bens = self._bens(("orfao", 190_000.0))

        assert split_imoveis_alocacao_vs_fora(
            titular_bens=bens, conjuge_bens={}, overrides_by_property_id=self._overrides()
        ) == (190_000.0, 0.0)

    def test_imovel_sem_property_id_tambem_cai_na_alocacao(self):
        """Sem `property_id` o override é inalcançável — e o lado conservador é o mesmo."""
        bens = {"imoveis": [_make_imovel(None, 42_000.0)]}

        assert split_imoveis_alocacao_vs_fora(
            titular_bens=bens, conjuge_bens={}, overrides_by_property_id=self._overrides()
        ) == (42_000.0, 0.0)

    def test_a_soma_conserva_cat2_contra_o_splitter_irmao(self):
        """Os dois eixos partem o MESMO cat_2 — a soma tem de bater entre eles."""
        bens = self._bens(
            ("casa", 500_000.0),
            ("sala", 150_000.0),
            ("terreno", 100_000.0),
            ("praia", 70_000.0),
            ("nua", 90_000.0),
            ("orfao", 190_000.0),
        )
        kwargs = dict(
            titular_bens=bens, conjuge_bens={}, overrides_by_property_id=self._overrides()
        )

        assert sum(split_imoveis_alocacao_vs_fora(**kwargs)) == sum(
            split_imoveis_geradores_vs_nao_geradores(**kwargs)
        )
