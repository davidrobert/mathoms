"""Unit tests do helper de dedup de investimentos cross-IRPF (ADR-271)."""

from __future__ import annotations

from pipeline.domain.services.investimentos_dedup import (
    dedup_investimentos_consolidados,
)


def _entry(
    *,
    proprietario: str,
    valores: dict[str, float],
    tipo: str = "renda_fixa",
    descricao: str = "Tesouro Selic 2029",
    instituicao: str | None = "XP Investimentos",
) -> dict:
    e: dict = {
        "descricao": descricao,
        "tipo": tipo,
        "proprietario": proprietario,
        "valores_31_12": dict(valores),
    }
    if instituicao is not None:
        e["instituicao"] = instituicao
    return e


class TestNoDuplication:
    def test_empty_list_returns_empty(self):
        result = dedup_investimentos_consolidados([])
        assert result.count_before == 0
        assert result.count_after == 0
        assert result.investimentos == []

    def test_none_input_returns_empty(self):
        result = dedup_investimentos_consolidados(None)
        assert result.count_after == 0

    def test_single_entry_passes_through_with_id(self):
        e = _entry(proprietario="david", valores={"2024": 10000.0})
        result = dedup_investimentos_consolidados([e])
        assert result.count_after == 1
        assert result.investimentos[0]["investment_id"]
        assert "proprietarios" not in result.investimentos[0]

    def test_two_distinct_assets_preserved(self):
        a = _entry(proprietario="david", valores={"2024": 1000.0}, descricao="Selic")
        b = _entry(proprietario="david", valores={"2024": 2000.0}, descricao="IPCA")
        result = dedup_investimentos_consolidados([a, b])
        assert result.count_after == 2


class TestCrossYear:
    def test_successive_years_union_into_series(self):
        """AC1: mesmo proprietário, anos distintos → 1 entry com série."""
        y2023 = _entry(proprietario="david", valores={"2023": 8000.0})
        y2024 = _entry(proprietario="david", valores={"2024": 9500.0})
        result = dedup_investimentos_consolidados([y2023, y2024])
        assert result.count_after == 1
        assert result.investimentos[0]["valores_31_12"] == {
            "2023": 8000.0,
            "2024": 9500.0,
        }

    def test_same_year_conflict_max_wins_with_warning(self):
        a = _entry(proprietario="david", valores={"2024": 10000.0})
        b = _entry(proprietario="david", valores={"2024": 10500.0})
        result = dedup_investimentos_consolidados([a, b])
        assert result.count_after == 1
        assert result.investimentos[0]["valores_31_12"]["2024"] == 10500.0
        assert any(w.type == "valor_divergente_ano" for w in result.warnings)

    def test_asset_absent_in_recent_year_stays_in_series(self):
        old = _entry(proprietario="david", valores={"2022": 5000.0})
        new = _entry(proprietario="david", valores={"2024": 6000.0})
        result = dedup_investimentos_consolidados([old, new])
        assert result.investimentos[0]["valores_31_12"] == {
            "2022": 5000.0,
            "2024": 6000.0,
        }


class TestCrossDeclarante:
    def test_joint_account_identical_value_merges(self):
        """AC2: conta conjunta (valor idêntico ao centavo) → 1 entry casal."""
        david = _entry(proprietario="david", valores={"2024": 25000.00})
        mariana = _entry(proprietario="mariana", valores={"2024": 25000.00})
        result = dedup_investimentos_consolidados([david, mariana])
        assert result.count_after == 1
        merged = result.investimentos[0]
        assert merged["proprietario"] == "casal"
        assert merged["proprietarios"] == ["david", "mariana"]
        assert merged["valores_31_12"]["2024"] == 25000.00

    def test_divergent_values_do_not_merge(self):
        """AC3: homônimos com valores diferentes → 2 entries preservadas."""
        david = _entry(proprietario="david", valores={"2024": 10000.0})
        mariana = _entry(proprietario="mariana", valores={"2024": 7000.0})
        result = dedup_investimentos_consolidados([david, mariana])
        assert result.count_after == 2
        assert any(w.type == "possivel_duplicata" for w in result.warnings)

    def test_zero_value_never_treated_as_joint(self):
        a = _entry(proprietario="david", valores={"2024": 0.0})
        b = _entry(proprietario="mariana", valores={"2024": 0.0})
        result = dedup_investimentos_consolidados([a, b])
        assert result.count_after == 2

    def test_three_declarantes_partial_match_does_not_merge(self):
        """Match parcial ao centavo entre 3 donos → NÃO funde (ADR-271, conservador)."""
        a = _entry(proprietario="david", valores={"2024": 100.0})
        b = _entry(proprietario="mariana", valores={"2024": 100.0})
        c = _entry(proprietario="joao", valores={"2024": 999.0})
        result = dedup_investimentos_consolidados([a, b, c])
        assert result.count_after == 3
        assert any(w.type == "possivel_duplicata" for w in result.warnings)

    def test_divergent_does_not_mutate_input(self):
        """Caminho divergente não vaza `_dedup_warning` no dict de entrada."""
        david = _entry(proprietario="david", valores={"2024": 10000.0})
        mariana = _entry(proprietario="mariana", valores={"2024": 7000.0})
        dedup_investimentos_consolidados([david, mariana])
        assert "_dedup_warning" not in david
        assert "_dedup_warning" not in mariana


class TestUnidentified:
    def test_no_description_passes_intact(self):
        """AC4: item sem descrição → unidentified, passa intacto."""
        ghost = {"tipo": "outros", "proprietario": "david", "valores_31_12": {"2024": 1.0}}
        ghost.pop("descricao", None)
        result = dedup_investimentos_consolidados([ghost])
        assert result.count_after == 1
        assert "investment_id" not in result.investimentos[0]


class TestIdempotency:
    def test_rerun_is_noop(self):
        """AC6: re-rodar dedup sobre saída já deduplicada = no-op."""
        y2023 = _entry(proprietario="david", valores={"2023": 8000.0})
        y2024 = _entry(proprietario="david", valores={"2024": 9500.0})
        first = dedup_investimentos_consolidados([y2023, y2024])
        second = dedup_investimentos_consolidados(first.investimentos)
        assert second.count_after == first.count_after == 1
        assert second.investimentos[0]["valores_31_12"] == {
            "2023": 8000.0,
            "2024": 9500.0,
        }

    def test_joint_rerun_is_noop(self):
        david = _entry(proprietario="david", valores={"2024": 25000.0})
        mariana = _entry(proprietario="mariana", valores={"2024": 25000.0})
        first = dedup_investimentos_consolidados([david, mariana])
        second = dedup_investimentos_consolidados(first.investimentos)
        assert second.count_after == 1
        assert second.investimentos[0]["proprietario"] == "casal"


class TestIdentity:
    def test_different_institution_does_not_merge(self):
        a = _entry(proprietario="david", valores={"2024": 1000.0}, instituicao="XP")
        b = _entry(proprietario="david", valores={"2024": 1000.0}, instituicao="BTG")
        result = dedup_investimentos_consolidados([a, b])
        assert result.count_after == 2

    def test_description_normalized_collapses(self):
        a = _entry(proprietario="david", valores={"2023": 1.0}, descricao="Tesouro  SELIC")
        b = _entry(proprietario="david", valores={"2024": 2.0}, descricao="tesouro selic")
        result = dedup_investimentos_consolidados([a, b])
        assert result.count_after == 1
