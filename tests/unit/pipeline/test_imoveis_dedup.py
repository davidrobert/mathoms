"""Unit tests do helper de dedup de imóveis co-declarados (ADR-246)."""

from __future__ import annotations

import pytest

from pipeline.domain.services.imoveis_dedup import (
    dedup_imoveis_consolidados,
    resolve_dedup_winner_by_property_id,
)


def _fuzzy_entry(proprietario, valor, codigo, canonical, descricao) -> dict:
    return _entry(
        descricao=descricao,
        proprietario=proprietario,
        valor_31_12=valor,
        codigo_rfb=codigo,
        endereco_canonical=canonical,
    )


def _entry(*, proprietario: str, valor_31_12, ano: str = "2024", **kw) -> dict:
    e: dict = {
        "descricao": kw.get("descricao", "APT LIVING WISH"),
        "proprietario": proprietario,
        "codigo_rfb": kw.get("codigo_rfb", "11"),
        "valores_31_12": {ano: valor_31_12},
        "tipo": "imovel",
    }
    if "property_id" in kw:
        e["property_id"] = kw["property_id"]
    if "endereco_canonical" in kw:
        e["endereco_canonical"] = kw["endereco_canonical"]
    return e


class TestNoDuplication:
    def test_empty_list_returns_empty(self):
        result = dedup_imoveis_consolidados([])
        assert result.count_before == 0
        assert result.count_after == 0
        assert result.imoveis == []

    def test_none_input_returns_empty(self):
        result = dedup_imoveis_consolidados(None)
        assert result.count_after == 0

    def test_single_entry_passes_through(self):
        e = _entry(proprietario="david_robert", valor_31_12=477436.58, property_id="uuid-a")
        result = dedup_imoveis_consolidados([e])
        assert result.count_after == 1
        assert result.imoveis[0]["proprietario"] == "david_robert"
        # Single entry passa direto — não introduz `proprietarios` nem muta
        assert "proprietarios" not in result.imoveis[0]

    def test_two_distinct_imoveis_preserved(self):
        a = _entry(proprietario="david", valor_31_12=400000, property_id="uuid-a")
        b = _entry(proprietario="david", valor_31_12=600000, property_id="uuid-b")
        result = dedup_imoveis_consolidados([a, b])
        assert result.count_after == 2
        assert {e["property_id"] for e in result.imoveis} == {"uuid-a", "uuid-b"}


class TestDedupByPropertyId:
    def test_same_property_id_two_members_merges(self):
        a = _entry(proprietario="david_robert", valor_31_12=477436.58, property_id="uuid-x")
        b = _entry(proprietario="mariana_xxx", valor_31_12=530000.0, property_id="uuid-x")
        result = dedup_imoveis_consolidados([a, b], titular_key="david_robert")
        assert result.count_after == 1
        merged = result.imoveis[0]
        # Maior valor vence
        assert merged["valores_31_12"]["2024"] == 530000.0
        # Co-titularidade
        assert merged["proprietario"] == "casal"
        assert set(merged["proprietarios"]) == {"david_robert", "mariana_xxx"}

    def test_no_warning_when_divergence_below_10pct(self):
        a = _entry(proprietario="david", valor_31_12=500000, property_id="uuid-y")
        b = _entry(proprietario="mariana", valor_31_12=525000, property_id="uuid-y")
        result = dedup_imoveis_consolidados([a, b])
        assert result.count_after == 1
        # 5% de divergência → sem warning
        assert len(result.warnings) == 0
        assert "_dedup_warning" not in result.imoveis[0]

    def test_warning_marks_entry_when_divergence_above_threshold(self):
        a = _entry(proprietario="david", valor_31_12=400000, property_id="uuid-z")
        b = _entry(proprietario="mariana", valor_31_12=600000, property_id="uuid-z")
        result = dedup_imoveis_consolidados([a, b])
        assert result.count_after == 1
        # diff_pct = (600 - 400) / 600 * 100 ≈ 33% → warning
        merged = result.imoveis[0]
        assert "_dedup_warning" in merged
        assert merged["_dedup_warning"]["type"] == "valor_divergente"
        assert merged["_dedup_warning"]["diff_pct"] > 10.0

    def test_three_declarations_merge_into_one(self):
        # caso atípico: 3 IRPFs (titular + cônjuge + dependente declarando)
        a = _entry(proprietario="david", valor_31_12=300000, property_id="uuid-3")
        b = _entry(proprietario="mariana", valor_31_12=400000, property_id="uuid-3")
        c = _entry(proprietario="filho", valor_31_12=350000, property_id="uuid-3")
        result = dedup_imoveis_consolidados([a, b, c])
        assert result.count_after == 1
        merged = result.imoveis[0]
        # Maior vence: 400k (mariana)
        assert merged["valores_31_12"]["2024"] == 400000
        assert set(merged["proprietarios"]) == {"david", "mariana", "filho"}


class TestDedupByCanonicalFallback:
    def test_canonical_fallback_when_no_property_id(self):
        a = _entry(
            proprietario="david",
            valor_31_12=400000,
            codigo_rfb="11",
            endereco_canonical="av joao dias 2192",
        )
        b = _entry(
            proprietario="mariana",
            valor_31_12=500000,
            codigo_rfb="11",
            endereco_canonical="av joao dias 2192",
        )
        result = dedup_imoveis_consolidados([a, b])
        assert result.count_after == 1
        assert result.imoveis[0]["proprietario"] == "casal"

    def test_different_codigo_same_canonical_does_not_dedup(self):
        a = _entry(
            proprietario="david",
            valor_31_12=400000,
            codigo_rfb="11",
            endereco_canonical="av paulista 1500",
        )
        b = _entry(
            proprietario="mariana",
            valor_31_12=500000,
            codigo_rfb="12",
            endereco_canonical="av paulista 1500",
        )
        # codigos diferentes → chaves diferentes → não dedup
        result = dedup_imoveis_consolidados([a, b])
        assert result.count_after == 2


class TestNoIdentityKey:
    def test_no_property_id_no_canonical_not_deduped(self):
        # Sem property_id E sem endereco_canonical: helper deixa passar
        a = _entry(proprietario="david", valor_31_12=400000, codigo_rfb="11")
        b = _entry(proprietario="mariana", valor_31_12=500000, codigo_rfb="11")
        result = dedup_imoveis_consolidados([a, b])
        # Sem chave robusta, NÃO dedup (evita falso-positivo)
        assert result.count_after == 2

    def test_empty_codigo_rfb_not_deduped(self):
        a = _entry(
            proprietario="david", valor_31_12=400000, codigo_rfb="", endereco_canonical="rua x"
        )
        b = _entry(
            proprietario="mariana", valor_31_12=500000, codigo_rfb="", endereco_canonical="rua x"
        )
        result = dedup_imoveis_consolidados([a, b])
        # codigo_rfb vazio → fallback canonical não aplica
        assert result.count_after == 2


class TestTieBreaker:
    def test_tie_value_year_titular_wins(self):
        # Mesmo valor + mesmo ano → titular vence
        a = _entry(proprietario="david_robert", valor_31_12=500000, property_id="uuid-t")
        b = _entry(proprietario="mariana", valor_31_12=500000, property_id="uuid-t")
        result = dedup_imoveis_consolidados([a, b], titular_key="david_robert")
        assert result.count_after == 1
        # No tie de valor+ano, titular vence (sua entry é o "winner" base)
        # Os campos não-de-merge devem vir da entry do titular
        # Ambos têm mesma descrição neste teste, então valor é o suficiente
        assert result.imoveis[0]["valores_31_12"]["2024"] == 500000

    def test_recent_year_wins(self):
        a = _entry(proprietario="david", valor_31_12=500000, ano="2023", property_id="uuid-y")
        b = _entry(proprietario="mariana", valor_31_12=500000, ano="2024", property_id="uuid-y")
        result = dedup_imoveis_consolidados([a, b])
        assert result.count_after == 1
        # Ano mais recente vence
        merged = result.imoveis[0]
        assert "2024" in merged["valores_31_12"]


class TestCrossCodigoMerge:
    """ADR-246: imóvel em IRPF (cod=11/12) + comprovante de bem ADR-239 (cod=01)."""

    def test_especifico_e_generico_merge(self):
        a = _entry(
            proprietario="david",
            valor_31_12=212000,
            codigo_rfb="11",
            endereco_canonical="major freire 496",
        )
        b = _entry(
            proprietario="david_camargo",
            valor_31_12=0,
            codigo_rfb="01",
            endereco_canonical="major freire 496",
        )
        result = dedup_imoveis_consolidados([a, b])
        assert result.count_after == 1
        merged = result.imoveis[0]
        assert merged["valores_31_12"]["2024"] == 212000
        assert set(merged["proprietarios"]) == {"david", "david_camargo"}

    def test_codigo_vazio_e_especifico_merge(self):
        a = _entry(
            proprietario="david",
            valor_31_12=350000,
            codigo_rfb="11",
            endereco_canonical="rua x 100",
        )
        b = _entry(
            proprietario="david_alt",
            valor_31_12=0,
            codigo_rfb="",
            endereco_canonical="rua x 100",
        )
        # codigo_rfb vazio → fallback canonical NÃO emite chave; mas cross-codigo
        # também precisa de chave válida → não merge nesse caso (entry b vai p/ unidentified).
        result = dedup_imoveis_consolidados([a, b])
        # b sem chave → fica como unidentified e não merge.
        # Esperado: 2 entries (a no grupo, b unidentified).
        assert result.count_after == 2

    def test_dois_especificos_divergentes_nao_funde(self):
        a = _entry(
            proprietario="david",
            valor_31_12=500000,
            codigo_rfb="11",
            endereco_canonical="rua y 200",
        )
        b = _entry(
            proprietario="mariana",
            valor_31_12=400000,
            codigo_rfb="12",
            endereco_canonical="rua y 200",
        )
        result = dedup_imoveis_consolidados([a, b])
        # 11 e 12 ambos específicos divergentes → não merge (conflito humano)
        assert result.count_after == 2

    def test_especifico_e_dois_genericos_mesmo_canonical_funde(self):
        canon = "rua w 400"
        a = _entry(
            proprietario="david", valor_31_12=500000, codigo_rfb="11", endereco_canonical=canon
        )
        b = _entry(proprietario="mariana", valor_31_12=0, codigo_rfb="01", endereco_canonical=canon)
        c = _entry(
            proprietario="david_alt", valor_31_12=0, codigo_rfb="01", endereco_canonical=canon
        )
        result = dedup_imoveis_consolidados([a, b, c])
        assert result.count_after == 1
        assert result.imoveis[0]["valores_31_12"]["2024"] == 500000


class TestFuzzyViaNum:
    """ADR-265: passe 4 fuzzy — mesma via, Δ numérico ≤ K."""

    def test_caso_real_founder_funde_190_vs_186(self):
        a = _entry(
            descricao="APTO 34 BENEDITO CALIXTO 190",
            proprietario="david",
            valor_31_12=800000,
            codigo_rfb="11",
            endereco_canonical="benedito calixto 190",
        )
        b = _entry(
            descricao="Ap 34 Benedito Calixto 186",
            proprietario="david",
            valor_31_12=750000,
            codigo_rfb="01",
            endereco_canonical="benedito calixto 186",
        )
        result = dedup_imoveis_consolidados([a, b])
        assert result.count_after == 1
        assert result.imoveis[0]["valores_31_12"]["2024"] == 800000

    def test_av_paulista_delta_grande_nao_funde(self):
        """Δ=10 (1500 vs 1490) na mesma via sem complemento — imóveis distintos."""
        a = _entry(
            descricao="EDIFICIO X PAULISTA 1500",
            proprietario="david",
            valor_31_12=500000,
            codigo_rfb="11",
            endereco_canonical="paulista 1500",
        )
        b = _entry(
            descricao="EDIFICIO Y PAULISTA 1490",
            proprietario="david",
            valor_31_12=600000,
            codigo_rfb="11",
            endereco_canonical="paulista 1490",
        )
        result = dedup_imoveis_consolidados([a, b])
        # Δ=10 > K=4 → 2 grupos
        assert result.count_after == 2

    def test_complemento_divergente_bloqueia_merge(self):
        """Mesma via + Δ=2 mas APTO divergente (34 vs 51) → não funde."""
        a = _entry(
            descricao="APTO 34 - PAULISTA 100",
            proprietario="david",
            valor_31_12=500000,
            codigo_rfb="11",
            endereco_canonical="paulista 100",
        )
        b = _entry(
            descricao="APTO 51 - PAULISTA 102",
            proprietario="mariana",
            valor_31_12=600000,
            codigo_rfb="11",
            endereco_canonical="paulista 102",
        )
        result = dedup_imoveis_consolidados([a, b])
        # Complementos divergem → 2 imóveis distintos
        assert result.count_after == 2

    def test_dois_especificos_divergentes_nao_funde_via_fuzzy(self):
        """cod=11 + cod=12 mesma via Δ=2 — conflito humano, não funde."""
        a = _entry(
            descricao="X 190",
            proprietario="david",
            valor_31_12=500000,
            codigo_rfb="11",
            endereco_canonical="rua x 190",
        )
        b = _entry(
            descricao="X 188",
            proprietario="mariana",
            valor_31_12=400000,
            codigo_rfb="12",
            endereco_canonical="rua x 188",
        )
        result = dedup_imoveis_consolidados([a, b])
        # cod=11 e cod=12 ambos específicos divergentes → 2 grupos (mesmo Δ=2)
        assert result.count_after == 2

    def test_cross_codigo_antes_fuzzy_3_fontes(self):
        # 3 fontes: cod=11 190 + cod=01 190 + cod=01 186 → cross-codigo + fuzzy = 1 grupo
        desc_190 = "APTO 34 BENEDITO CALIXTO 190"
        a = _fuzzy_entry("david", 800000, "11", "benedito calixto 190", desc_190)
        b = _fuzzy_entry("alt1", 0, "01", "benedito calixto 190", desc_190)
        c = _fuzzy_entry(
            "alt2", 750000, "01", "benedito calixto 186", "APTO 34 BENEDITO CALIXTO 186"
        )
        result = dedup_imoveis_consolidados([a, b, c])
        assert result.count_after == 1
        assert result.imoveis[0]["valores_31_12"]["2024"] == 800000


class TestObservability:
    def test_dropped_property_ids_collected(self):
        a = _entry(proprietario="david", valor_31_12=400000, property_id="uuid-a")
        b = _entry(proprietario="mariana", valor_31_12=500000, property_id="uuid-a")
        result = dedup_imoveis_consolidados([a, b])
        # Quando IDs são iguais, nenhum é "dropped" — é só merge in-place
        # (winner mantém o mesmo id)
        assert len(result.dropped_property_ids) == 0

    def test_count_tracking(self):
        items = [
            _entry(proprietario="david", valor_31_12=400000, property_id="uuid-a"),
            _entry(proprietario="mariana", valor_31_12=500000, property_id="uuid-a"),
            _entry(proprietario="david", valor_31_12=300000, property_id="uuid-b"),
        ]
        result = dedup_imoveis_consolidados(items)
        assert result.count_before == 3
        assert result.count_after == 2


class TestResolveDedupWinnerByPropertyId:
    """`resolve_dedup_winner_by_property_id` — pid→vencedor sem merge de payload (A28.l7)."""

    def test_grupo_fuzzy_mapeia_orfaos_para_vencedor(self):
        # 4 rows órfãs do mesmo imóvel (declarante×variação); só o vencedor tem valor.
        entries = [
            _fuzzy_entry("titular", 500000, "11", "rua sintetica alfa 100", "CASA ALFA 100"),
            _fuzzy_entry("conjuge", 0, "11", "rua sintetica alfa 102", "CASA ALFA 102"),
            _fuzzy_entry("titular", 0, "01", "rua sintetica alfa 100", "CASA ALFA 100"),
            _fuzzy_entry("conjuge", 0, "", "rua sintetica alfa 103", "CASA ALFA 103"),
        ]
        for i, e in enumerate(entries):
            e["property_id"] = f"pid-{i}"
        winners = resolve_dedup_winner_by_property_id(entries)
        assert winners == {f"pid-{i}": "pid-0" for i in range(4)}

    def test_imoveis_distintos_sao_seus_proprios_vencedores(self):
        a = _fuzzy_entry("titular", 100, "11", "rua sintetica alfa 100", "CASA ALFA")
        b = _fuzzy_entry("titular", 200, "11", "avenida sintetica beta 900", "APTO BETA")
        a["property_id"], b["property_id"] = "pid-a", "pid-b"
        winners = resolve_dedup_winner_by_property_id([a, b])
        assert winners == {"pid-a": "pid-a", "pid-b": "pid-b"}

    def test_nao_muta_payload_nem_mescla(self):
        a = _entry(proprietario="titular", valor_31_12=400000, property_id="pid-a")
        b = _entry(proprietario="conjuge", valor_31_12=500000, property_id="pid-b")
        a["endereco_canonical"] = b["endereco_canonical"] = "rua sintetica alfa 100"
        snapshot = [dict(a), dict(b)]
        resolve_dedup_winner_by_property_id([a, b])
        assert [a, b] == snapshot
