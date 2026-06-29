"""Unit tests do helper de dedup de dívidas cross-IRPF (ADR-301).

Cobre os invariantes INV-D1..D8: conservação do saldo-corrente, não-double-count
cross-year, quitação, idempotência, tie-break determinístico, casal sem
double-count, conflito cross-declarante e unidentified intacto.
"""

from __future__ import annotations

from pipeline.domain.services.dividas_dedup import dedup_dividas_consolidadas


def _entry(
    *,
    proprietario: str,
    saldo: dict[str, float],
    descricao: str = "Financiamento imobiliário CEF",
    **opt: str | None,
) -> dict:
    """Builder de entry de dívida; campos opcionais (tipo/credor/numero_contrato/
    indexador) passam via **opt e só entram quando não-None."""
    base = {
        "descricao": descricao,
        "proprietario": proprietario,
        "saldo_31_12": dict(saldo),
    }
    return {**base, **{k: v for k, v in opt.items() if v is not None}}


def _latest(entry: dict) -> float:
    saldos = entry["saldo_31_12"]
    return saldos[max(saldos.keys())]


class TestNoDuplication:
    def test_empty_list_returns_empty(self):
        result = dedup_dividas_consolidadas([])
        assert result.count_before == 0
        assert result.count_after == 0
        assert result.dividas == []

    def test_none_input_returns_empty(self):
        assert dedup_dividas_consolidadas(None).count_after == 0

    def test_single_entry_passes_through_with_id(self):
        e = _entry(proprietario="david", saldo={"2024": 100000.0})
        result = dedup_dividas_consolidadas([e])
        assert result.count_after == 1
        assert result.dividas[0]["divida_id"]
        assert "proprietarios" not in result.dividas[0]

    def test_two_distinct_debts_preserved(self):
        a = _entry(proprietario="david", saldo={"2024": 1000.0}, descricao="Veículo")
        b = _entry(proprietario="david", saldo={"2024": 2000.0}, descricao="Imóvel")
        assert dedup_dividas_consolidadas([a, b]).count_after == 2


class TestCrossYearINV_D2:
    def test_three_years_collapse_into_one_entry(self):
        """INV-D2: dívida em 3 IRPFs → 1 entry com série completa."""
        ys = [
            _entry(proprietario="david", saldo={"2022": 120000.0}),
            _entry(proprietario="david", saldo={"2023": 110000.0}),
            _entry(proprietario="david", saldo={"2024": 100000.0}),
        ]
        result = dedup_dividas_consolidadas(ys)
        assert result.count_after == 1
        assert result.dividas[0]["saldo_31_12"] == {
            "2022": 120000.0,
            "2023": 110000.0,
            "2024": 100000.0,
        }

    def test_current_saldo_is_max_year(self):
        """INV-D1: saldo corrente = ano máximo."""
        ys = [
            _entry(proprietario="david", saldo={"2023": 110000.0}),
            _entry(proprietario="david", saldo={"2024": 100000.0}),
        ]
        result = dedup_dividas_consolidadas(ys)
        assert _latest(result.dividas[0]) == 100000.0


class TestQuitacaoINV_D3:
    def test_debt_absent_in_new_year_keeps_only_old_series(self):
        """INV-D3: dívida quitada (ausente no ano novo) some do saldo corrente."""
        quitada = _entry(proprietario="david", saldo={"2023": 5000.0}, descricao="Cartão BB")
        viva = _entry(proprietario="david", saldo={"2024": 80000.0}, descricao="Imóvel")
        result = dedup_dividas_consolidadas([quitada, viva])
        assert result.count_after == 2
        by_desc = {d["descricao"]: d for d in result.dividas}
        assert max(by_desc["Cartão BB"]["saldo_31_12"].keys()) == "2023"


class TestIdempotenciaINV_D4:
    def test_dedup_of_dedup_is_stable(self):
        """INV-D4: dedup(dedup(x)) == dedup(x), divida_id estável."""
        ys = [
            _entry(proprietario="david", saldo={"2023": 110000.0}),
            _entry(proprietario="david", saldo={"2024": 100000.0}),
        ]
        once = dedup_dividas_consolidadas(ys).dividas
        twice = dedup_dividas_consolidadas(once).dividas
        assert once == twice


class TestTieBreakINV_D5:
    def test_insertion_order_preserved(self):
        """INV-D5: ordem de inserção preservada (runner garante)."""
        a = _entry(proprietario="david", saldo={"2024": 1.0}, descricao="AAA")
        b = _entry(proprietario="david", saldo={"2024": 2.0}, descricao="BBB")
        c = _entry(proprietario="david", saldo={"2024": 3.0}, descricao="CCC")
        result = dedup_dividas_consolidadas([a, b, c])
        assert [d["descricao"] for d in result.dividas] == ["AAA", "BBB", "CCC"]

    def test_divida_id_deterministic(self):
        e = _entry(proprietario="david", saldo={"2024": 100.0})
        id1 = dedup_dividas_consolidadas([e]).dividas[0]["divida_id"]
        id2 = dedup_dividas_consolidadas([e]).dividas[0]["divida_id"]
        assert id1 == id2


class TestCrossDeclaranteINV_D6_D7:
    def test_joint_debt_identical_merges_as_casal(self):
        """INV-D6: financiamento conjunto saldo idêntico → 1 entry 'casal'."""
        a = _entry(proprietario="david", saldo={"2024": 300000.0})
        b = _entry(proprietario="mariana", saldo={"2024": 300000.0})
        result = dedup_dividas_consolidadas([a, b])
        assert result.count_after == 1
        assert result.dividas[0]["proprietario"] == "casal"
        assert sorted(result.dividas[0]["proprietarios"]) == ["david", "mariana"]

    def test_divergent_saldo_preserves_both_with_warning(self):
        """INV-D7: saldo divergente entre declarantes → 2 entries + warning."""
        a = _entry(proprietario="david", saldo={"2024": 300000.0})
        b = _entry(proprietario="mariana", saldo={"2024": 150000.0})
        result = dedup_dividas_consolidadas([a, b])
        assert result.count_after == 2
        assert any(w.type == "possivel_duplicata" for w in result.warnings)


class TestUnidentifiedINV_D8:
    def test_entry_without_descricao_passes_intact(self):
        """INV-D8: sem descricao → identity_key None → preservada."""
        bad = {"proprietario": "david", "saldo_31_12": {"2024": 1.0}}
        result = dedup_dividas_consolidadas([bad])
        assert result.count_after == 1
        assert "divida_id" not in result.dividas[0]


class TestContratoKey:
    def test_same_contract_merges_across_description_variants(self):
        """numero_contrato é discriminador forte — funde apesar de descrição variar."""
        a = _entry(
            proprietario="david",
            saldo={"2023": 110000.0},
            descricao="Financiamento imovel",
            numero_contrato="CT-123",
        )
        b = _entry(
            proprietario="david",
            saldo={"2024": 100000.0},
            descricao="Financ. imóvel CEF",
            numero_contrato="CT-123",
        )
        result = dedup_dividas_consolidadas([a, b])
        assert result.count_after == 1

    def test_renegotiation_new_contract_does_not_merge(self):
        """Renegociação muda contrato → dívida nova, não funde (ADR-301 §2)."""
        a = _entry(
            proprietario="david",
            saldo={"2023": 50000.0},
            descricao="Consignado",
            numero_contrato="CT-A",
        )
        b = _entry(
            proprietario="david",
            saldo={"2024": 80000.0},
            descricao="Consignado",
            numero_contrato="CT-B",
        )
        result = dedup_dividas_consolidadas([a, b])
        assert result.count_after == 2


class TestMonotonicidade:
    def test_amortizavel_growing_saldo_emits_warning(self):
        """Amortizável fixa com saldo crescente → warning saldo_nao_monotonico."""
        ys = [
            _entry(proprietario="david", saldo={"2023": 90000.0}, tipo="financiamento_imobiliario"),
            _entry(proprietario="david", saldo={"2024": 95000.0}, tipo="financiamento_imobiliario"),
        ]
        result = dedup_dividas_consolidadas(ys)
        assert any(w.type == "saldo_nao_monotonico" for w in result.warnings)

    def test_revolving_growing_saldo_no_warning(self):
        """Revolvente (cheque especial) com saldo crescente é legítimo → sem warning."""
        ys = [
            _entry(
                proprietario="david", saldo={"2023": 2000.0}, tipo="cheque_especial", descricao="CE"
            ),
            _entry(
                proprietario="david", saldo={"2024": 3000.0}, tipo="cheque_especial", descricao="CE"
            ),
        ]
        result = dedup_dividas_consolidadas(ys)
        assert not any(w.type == "saldo_nao_monotonico" for w in result.warnings)

    def test_no_tipo_growing_saldo_no_warning(self):
        """Tipo ausente → não classificável → sem warning (conservador)."""
        ys = [
            _entry(proprietario="david", saldo={"2023": 2000.0}),
            _entry(proprietario="david", saldo={"2024": 3000.0}),
        ]
        result = dedup_dividas_consolidadas(ys)
        assert not any(w.type == "saldo_nao_monotonico" for w in result.warnings)

    def test_indexed_amortizavel_growing_no_warning(self):
        """Indexada (correção > amortização) → sem warning mesmo amortizável."""
        ys = [
            _entry(
                proprietario="david",
                saldo={"2023": 90000.0},
                tipo="financiamento_imobiliario",
                indexador="IPCA",
            ),
            _entry(
                proprietario="david",
                saldo={"2024": 95000.0},
                tipo="financiamento_imobiliario",
                indexador="IPCA",
            ),
        ]
        result = dedup_dividas_consolidadas(ys)
        assert not any(w.type == "saldo_nao_monotonico" for w in result.warnings)


class TestConservacaoINV_D1:
    def test_current_saldo_sum_preserved_multi_entry(self):
        """INV-D1: soma do saldo-corrente pós-dedup == soma pré-dedup (ano corrente)."""
        entries = [
            _entry(proprietario="david", saldo={"2024": 100000.0}, descricao="Imóvel"),
            _entry(proprietario="david", saldo={"2023": 110000.0}, descricao="Imóvel"),
            _entry(proprietario="david", saldo={"2024": 20000.0}, descricao="Veículo"),
        ]
        result = dedup_dividas_consolidadas(entries)
        # Imóvel funde (2023+2024 → corrente 2024=100k); Veículo intacto (20k).
        total_corrente = sum(_latest(d) for d in result.dividas)
        assert total_corrente == 120000.0
