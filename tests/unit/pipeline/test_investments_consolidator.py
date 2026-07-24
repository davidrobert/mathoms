"""Tests — ``InvestmentsConsolidator`` (Sessão A4a)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.investments_consolidator import (  # noqa: E402
    ConsolidatedInvestments,
    InvestmentsConsolidator,
    InvestmentsConsolidatorConfig,
)

_FIXED_NOW = datetime(2026, 4, 19)


def _consolidator(family: dict | None = None) -> InvestmentsConsolidator:
    cfg = InvestmentsConsolidatorConfig.from_family(family)
    return InvestmentsConsolidator(cfg, now=_FIXED_NOW)


def _posicao(nome: str, valor: float, **kwargs) -> dict:
    out = {"nome": nome, "valor_total": valor}
    out.update(kwargs)
    return out


def _extract(
    *,
    source: str,
    instituicao: str = "BTG Pactual",
    membro: str = "",
    data_ref: str = "2026-03-31",
    total: float | None = None,
    posicoes: list | None = None,
) -> dict:
    out: dict = {
        "_source": source,
        "instituicao": instituicao,
        "membro": membro,
        "data_referencia": data_ref,
        "posicoes": posicoes or [],
    }
    if total is not None:
        out["total"] = total
    return out


def _valued(
    source: str, ticker: str, valor, *, inst: str = "", data_ref: str = "2026-07-31"
) -> dict:
    return _extract(
        source=source,
        instituicao=inst,
        membro="david",
        data_ref=data_ref,
        total=valor,
        posicoes=[_posicao(ticker, valor)],
    )


def _rv_valued(source: str, inst: str, ticker: str, qtd: int, valor) -> dict:
    pos = {"nome": ticker, "ticker": ticker, "quantidade": qtd, "valor_total": valor}
    return _extract(source=source, instituicao=inst, membro="david", total=valor, posicoes=[pos])


def _rv_qtyonly(source: str, inst: str, ticker: str, qtd: int) -> dict:  # custódia sem valor
    pos = {"nome": ticker, "ticker": ticker, "quantidade": qtd}
    return _extract(source=source, instituicao=inst, membro="david", posicoes=[pos])


class TestBasic:
    def test_consolidates_single_extract(self):
        c = _consolidator()
        e = _extract(
            source="btg_202603-2_extract.json",
            instituicao="BTG Pactual",
            membro="david",
            total=150_000,
            posicoes=[
                _posicao("Tesouro Selic", 100_000),
                _posicao("CDB", 50_000),
            ],
        )

        out = c.consolidate([e])

        assert isinstance(out, ConsolidatedInvestments)
        assert out.n_posicoes == 2
        assert out.total_por_membro == {"david": 150_000.0}
        assert out.total_geral == 150_000.0
        assert out.fontes == ["btg_202603-2_extract.json"]

    def test_skips_candidates_without_posicoes(self):
        c = _consolidator()
        e = {"_source": "empty.json", "posicoes": []}

        out = c.consolidate([e])

        assert out.n_posicoes == 0
        assert out.fontes == []

    def test_handles_empty_input(self):
        out = _consolidator().consolidate([])

        assert out.n_posicoes == 0
        assert out.total_geral == 0.0

    def test_reads_investimentos_field_with_valor_brl(self):
        """E2-llm investment_report grava ``investimentos[{valor_brl, descricao}]``
        em vez de ``posicoes[{valor_total, nome}]`` — ambos devem consolidar."""
        c = _consolidator()
        e = {
            "_source": "btg_portfolio.json",
            "instituicao": "btgpactual",
            "membro": "mariana_ribeiro_andrade",
            "data_referencia": "2026-03-31",
            "tipo_documento": "investment_report",
            "investimentos": [
                {"tipo": "cdb", "descricao": "CDB BTG Agibank", "valor_brl": 29353.39},
                {"tipo": "cdb", "descricao": "CDB PicPay", "valor_brl": 30442.60},
            ],
        }

        out = c.consolidate([e])

        assert out.n_posicoes == 2
        assert out.total_por_membro == {"mariana_ribeiro_andrade": 59795.99}
        assert out.dados[0]["nome"] == "CDB BTG Agibank"
        assert out.dados[0]["valor_atual"] == 29353.39


class TestDedup:
    def test_keeps_most_recent_per_institution_member(self):
        c = _consolidator()
        old = _extract(
            source="old.json",
            instituicao="BTG",
            membro="david",
            data_ref="2026-02-28",
            total=100_000,
            posicoes=[_posicao("A", 100_000)],
        )
        new = _extract(
            source="new.json",
            instituicao="BTG",
            membro="david",
            data_ref="2026-03-31",
            total=120_000,
            posicoes=[_posicao("A", 120_000)],
        )

        out = c.consolidate([old, new])

        assert out.fontes == ["new.json"]
        assert out.total_por_membro["david"] == 120_000.0

    def test_different_institutions_not_deduped(self):
        c = _consolidator()
        btg = _extract(
            source="btg.json",
            instituicao="BTG",
            membro="david",
            total=100_000,
            posicoes=[_posicao("A", 100_000)],
        )
        rico = _extract(
            source="rico.json",
            instituicao="Rico",
            membro="david",
            total=50_000,
            posicoes=[_posicao("B", 50_000)],
        )

        out = c.consolidate([btg, rico])

        assert len(out.fontes) == 2
        assert out.total_por_membro["david"] == 150_000.0


class TestEmptyInstitutionDedup:
    """ADR-346 (A39.l9) — instituição vazia nunca é chave que descarta em
    silêncio; todo descarte do dedup source-level é registrado."""

    def test_two_empty_institution_sources_both_survive(self):
        # Invariante 4: 2 fontes valoradas inst-vazia do mesmo membro NÃO
        # colapsam em ("", membro) — ambas somam (senão uma sumiria).
        out = _consolidator().consolidate(
            [
                _valued("rico_investimentosposicao_202607.json", "PETR4", 80_000),
                _valued("xp_investimentosposicao_202607.json", "VALE3", 50_000),
            ]
        )
        assert out.n_posicoes == 2
        assert out.total_por_membro["david"] == 130_000.0
        assert len(out.fontes) == 2
        assert any("instituição não resolvida" in a for a in out.avisos_validacao)

    def test_dedup_discard_is_logged(self):
        # Invariante 2: colapso datado registra o descarte (mantém o recente).
        out = _consolidator().consolidate(
            [
                _valued("btg_202602.json", "A", 100_000, inst="BTG", data_ref="2026-02-28"),
                _valued("btg_202603.json", "A", 120_000, inst="BTG", data_ref="2026-03-31"),
            ]
        )
        assert out.total_por_membro["david"] == 120_000.0  # só o mais recente
        assert any("dedup posição" in a and "2026-02-28" in a for a in out.avisos_validacao)


class TestResolucaoRV:
    """ADR-346 (A39.l9) — colapso de identidade RV por (ticker_norm, membro)."""

    def test_a_collapse_custodia_qtyonly_into_valued(self):
        # (a) mesma ticker+qtd, corretora valorada + custódia qty-only → colapsa;
        # total = só a valorada (Leitura A); sem falso alarme de ressalva.
        corretora = _rv_valued("rico.json", "Rico", "BRKM5", 300, 1821)
        custodia = _rv_qtyonly("itau.json", "Itau", "BRKM5", 300)
        out = _consolidator().consolidate([corretora, custodia])
        assert out.n_posicoes == 1
        assert out.total_por_membro["david"] == 1821.0
        assert out.posicoes_sem_marcacao_por_membro == {}

    def test_c_qty_diferente_never_funds(self):
        corretora = _rv_valued("rico.json", "Rico", "BRKM5", 300, 1821)
        custodia = _rv_qtyonly("itau.json", "Itau", "BRKM5", 500)
        out = _consolidator().consolidate([corretora, custodia])
        assert out.n_posicoes == 2  # never-fund
        assert any(p.get("possivel_posicao_espelho") for p in out.dados)

    def test_b_duas_valoradas_sinalizam_superestimado(self):
        a = _rv_valued("rico.json", "Rico", "BRKM5", 300, 1821)
        b = _rv_valued("xp.json", "XP", "BRKM5", 300, 1821)
        out = _consolidator().consolidate([a, b])
        assert out.n_posicoes == 2  # never-fund
        assert all(p.get("pl_possivel_superestimado") for p in out.dados)

    def test_fractional_suffix_normaliza_e_colapsa(self):
        corretora = _rv_valued("rico.json", "Rico", "PETR4", 300, 1821)
        custodia = _rv_qtyonly("itau.json", "Itau", "PETR4F", 300)
        out = _consolidator().consolidate([corretora, custodia])
        assert out.n_posicoes == 1  # PETR4F → PETR4 → colapsa


class TestMemberInference:
    def test_infers_member_from_banco_membro_config(self):
        c = _consolidator(family={"banco_membro": {"btgpactual": "david"}})
        e = _extract(
            source="btg.json",
            instituicao="BTG Pactual",
            membro="",
            total=100_000,
            posicoes=[_posicao("A", 100_000)],
        )

        out = c.consolidate([e])

        assert out.total_por_membro == {"david": 100_000.0}

    def test_empty_member_when_no_config_match(self):
        c = _consolidator()
        e = _extract(
            source="x.json",
            instituicao="Unknown Bank",
            membro="",
            total=100_000,
            posicoes=[_posicao("A", 100_000)],
        )

        out = c.consolidate([e])

        assert "" in out.total_por_membro
        assert out.total_por_membro[""] == 100_000.0


class TestValidationWarnings:
    def test_warns_when_saldo_diverges_from_sum_of_positions(self):
        c = _consolidator()
        e = _extract(
            source="x.json",
            instituicao="BTG",
            membro="david",
            total=200_000,  # declarado
            posicoes=[
                _posicao("A", 100_000),
                _posicao("B", 50_000),
            ],  # soma 150_000
        )

        out = c.consolidate([e])

        assert len(out.avisos_validacao) == 1
        assert "R$ 200,000.00" in out.avisos_validacao[0] or "200.000" in out.avisos_validacao[0]

    def test_no_warning_when_within_tolerance(self):
        c = _consolidator()
        e = _extract(
            source="x.json",
            instituicao="BTG",
            membro="david",
            total=150_000.50,
            posicoes=[_posicao("A", 150_000)],  # gap 0.50 < 1.00 default
        )

        out = c.consolidate([e])

        assert out.avisos_validacao == ()

    def test_custom_tolerance(self):
        cfg = InvestmentsConsolidatorConfig(divergence_tolerance=100.0)
        c = InvestmentsConsolidator(cfg, now=_FIXED_NOW)
        e = _extract(
            source="x.json",
            instituicao="BTG",
            membro="david",
            total=150_000,
            posicoes=[_posicao("A", 149_950)],  # gap 50, dentro de 100
        )

        out = c.consolidate([e])

        assert out.avisos_validacao == ()


class TestPositionFieldFallbacks:
    def test_valor_fallback_chain(self):
        c = _consolidator()
        e = _extract(
            source="x.json",
            instituicao="X",
            membro="m",
            posicoes=[
                {"nome": "A", "valor_atual": 1000},  # sem valor_total
                {"nome": "B", "current_value": 2000},  # inglês
            ],
        )

        out = c.consolidate([e])

        # total_fonte=0 → cai pra positions_sum
        assert out.total_geral == 3000.0

    def test_preserves_extra_position_fields(self):
        c = _consolidator()
        e = _extract(
            source="x.json",
            instituicao="X",
            membro="m",
            posicoes=[
                _posicao(
                    "Tesouro",
                    1000,
                    taxa="IPCA+6%",
                    vencimento="2035-12-31",
                    tipo="tesouro_ipca",
                ),
            ],
        )

        out = c.consolidate([e])

        pos = out.dados[0]
        assert pos["taxa"] == "IPCA+6%"
        assert pos["vencimento"] == "2035-12-31"
        assert pos["tipo"] == "tesouro_ipca"


class TestLegacyDict:
    def test_to_legacy_dict_matches_shape(self):
        c = _consolidator()
        e = _extract(
            source="x.json",
            instituicao="BTG",
            membro="david",
            total=100_000,
            posicoes=[_posicao("A", 100_000)],
        )

        out = c.consolidate([e]).to_legacy_dict()

        assert set(out.keys()) >= {
            "dados",
            "total_por_membro",
            "total_geral",
            "fontes",
            "data_consolidacao",
            "n_posicoes",
        }
        assert out["data_consolidacao"] == "2026-04-19"

    def test_avisos_omitted_when_empty(self):
        c = _consolidator()
        out = c.consolidate([]).to_legacy_dict()

        assert "avisos_validacao" not in out


class TestParseAccountRecordNormFallback:
    def test_members_without_norm_rederives_from_raw(self):
        # A24.l2 (ADR-280): members novos emitem só account_number_raw.
        from pipeline.domain.services.investments_consolidator import (
            InvestmentsConsolidatorConfig,
        )

        cfg = InvestmentsConsolidatorConfig.from_family(
            {
                "contas": [
                    {
                        "member_key": "david",
                        "institution_code": "itau",
                        "account_type": "corrente",
                        "account_number_raw": "12.345-6",
                    }
                ]
            }
        )
        assert cfg.accounts[0].account_number_norm == "123456"

    def test_legacy_members_with_norm_keeps_emitted_value(self):
        from pipeline.domain.services.investments_consolidator import (
            InvestmentsConsolidatorConfig,
        )

        cfg = InvestmentsConsolidatorConfig.from_family(
            {
                "contas": [
                    {
                        "member_key": "david",
                        "institution_code": "itau",
                        "account_type": "corrente",
                        "account_number_raw": "12.345-6",
                        "account_number_norm": "123456",
                    }
                ]
            }
        )
        assert cfg.accounts[0].account_number_norm == "123456"


class TestRVIntegrationRealShape:
    """E2→E4 com a shape REAL dos parsers (A39.l9 PR3b): SEM `membro` explícito
    (resolve via banco_membro, como no fluxo de produção) + Itaú custódia
    só-quantidade + Rico carteira valorada sem `total` (fallback Σ posições).
    Cobre o gap que TestResolucaoRV (membro explícito) não exercita."""

    def _itau(self) -> dict:  # custódia acionária: nome+ticker+quantidade, SEM valor
        return _extract(
            source="itau_investimentosposicao-2_extract.json",
            instituicao="itau",
            posicoes=[
                {"nome": "BRASKEM S.A.", "ticker": "BRKM5", "quantidade": 300},
                {"nome": "ITAUSA S.A. Preferencial", "ticker": "ITSA4", "quantidade": 778},
            ],
        )

    def _rico(self) -> dict:  # carteira valorada: nome/ticker + valor_atual (sem `total`)
        return _extract(
            source="rico_investimentosposicao-2_extract.json",
            instituicao="rico",
            posicoes=[
                {"nome": "BRKM5", "ticker": "BRKM5", "quantidade": 300, "valor_atual": 800.0},
                {"nome": "ITSA4", "ticker": "ITSA4", "quantidade": 778, "valor_atual": 300.0},
            ],
        )

    def test_collapse_quando_instituicoes_resolvem_mesmo_membro(self):
        # itau + rico → david: custódia só-quantidade COLAPSA na carteira valorada
        # (mesmo ticker+membro) → PL uma vez (Σ posições Rico), SEM ressalva falsa.
        c = _consolidator(family={"banco_membro": {"itau": "david", "rico": "david"}})
        out = c.consolidate([self._itau(), self._rico()])
        assert out.total_por_membro == {"david": 1100.0}
        assert out.n_posicoes == 2  # 4 posições → 2 após colapso
        assert out.posicoes_sem_marcacao_por_membro == {}

    def test_membro_nao_resolvido_escala_sem_perder_nem_mostrar_interrogacao(self):
        # rico sem mapeamento → valor sob "" (NÃO some) + david ganha ressalva
        # com rótulo legível (`nome`), nunca "?". Conservador (ADR-346: escala).
        c = _consolidator(family={"banco_membro": {"itau": "david"}})
        out = c.consolidate([self._itau(), self._rico()])
        assert out.total_por_membro.get("") == 1100.0  # valor preservado
        assert out.n_posicoes == 4  # sem colapso (membros divergem)
        david_badge = out.posicoes_sem_marcacao_por_membro.get("david", [])
        assert "BRASKEM S.A." in david_badge
        assert "?" not in david_badge
