#!/usr/bin/env python3
"""Golden file / snapshot tests — validate that LLM output schemas parse
golden fixtures correctly and that validators accept them.

Fixture inventory: tests/fixtures/llm_golden/README.md
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "llm_golden"


class TestE1GoldenFile:
    @pytest.fixture
    def golden_data(self):
        return json.loads((GOLDEN_DIR / "e1_members_output.json").read_text())

    def test_schema_parses(self, golden_data):
        from pipeline.llm.schemas.e1_members import MembersExtractOutput

        output = MembersExtractOutput(**golden_data)
        assert len(output.members) == 2
        assert output.titular_key == "david"
        assert output.confidence == 0.95

    def test_validator_accepts(self, golden_data):
        from pipeline.llm.schemas.e1_members import MembersExtractOutput
        from pipeline.llm.validators import validate_e1_output

        output = MembersExtractOutput(**golden_data)
        result = validate_e1_output(output)
        assert result.valid, f"Errors: {result.errors}"
        assert len(result.warnings) == 0

    def test_output_converter(self, golden_data):
        from pipeline.llm.schemas.e1_members import MembersExtractOutput
        from pipeline.stages.extract_members import _output_to_family_members_json

        output = MembersExtractOutput(**golden_data)
        fmj = _output_to_family_members_json(output)

        assert "david" in fmj["membros"]
        assert "mariana" in fmj["membros"]
        assert fmj["membros"]["david"]["cpf"] == "12345678901"
        assert fmj["banco_membro"]["itau"] == "david"
        assert fmj["banco_membro"]["c6bank"] == "david"
        assert fmj["banco_membro"]["nubank"] == "mariana"

    def test_member_keys_are_lowercase_no_spaces(self, golden_data):
        for m in golden_data["members"]:
            assert m["key"].islower()
            assert " " not in m["key"]


class TestE15GoldenFile:
    @pytest.fixture
    def golden_data(self):
        return json.loads((GOLDEN_DIR / "e15_baseline_output.json").read_text())

    def test_schema_parses(self, golden_data):
        from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput

        output = BaselinePatrimonialOutput(**golden_data)
        assert len(output.items) == 5
        assert output.net_worth_brl == 897000.00
        assert output.reference_year == 2024

    def test_validator_accepts(self, golden_data):
        from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput
        from pipeline.llm.validators import validate_e15_output

        output = BaselinePatrimonialOutput(**golden_data)
        result = validate_e15_output(output)
        assert result.valid, f"Errors: {result.errors}"

    def test_output_converter(self, golden_data):
        from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput
        from pipeline.stages.extract_baseline import _output_to_baseline_json

        output = BaselinePatrimonialOutput(**golden_data)
        baseline = _output_to_baseline_json(output)

        assert baseline["resumo"]["patrimonio_liquido"] == 897000.00
        assert len(baseline["itens"]) == 5
        assert baseline["_meta"]["source"] == "E1.5-llm"
        assert baseline["itens"][0]["categoria"] == "imovel"

    def test_items_sum_matches_total(self, golden_data):
        total = sum(i["value_brl"] for i in golden_data["items"])
        assert abs(total - golden_data["total_assets_brl"]) < 0.01


class TestE2LLMGoldenFile:
    @pytest.fixture
    def golden_data(self):
        return json.loads((GOLDEN_DIR / "e2_llm_extract_output.json").read_text())

    def test_schema_parses(self, golden_data):
        from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput

        output = LLMExtractOutput(**golden_data)
        assert len(output.transactions) == 2
        assert len(output.investments) == 3
        assert output.institution == "btgpactual"

    def test_validator_accepts(self, golden_data):
        from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
        from pipeline.llm.validators import validate_e2_llm_output

        output = LLMExtractOutput(**golden_data)
        result = validate_e2_llm_output(output)
        assert result.valid, f"Errors: {result.errors}"

    def test_output_converter(self, golden_data):
        from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
        from pipeline.stages.extract_with_llm import _output_to_e2_json

        output = LLMExtractOutput(**golden_data)
        e2 = _output_to_e2_json(output)

        assert e2["extraido_por"] == "llm"
        assert e2["instituicao"] == "btgpactual"
        assert e2["periodo"] == {"inicio": "2024-12-01", "fim": "2024-12-31"}
        assert len(e2["transacoes"]) == 2
        assert len(e2["investimentos"]) == 3
        assert e2["investimentos"][0]["taxa"] == "100% CDI"

    def test_transactions_have_valid_dates(self, golden_data):
        import re

        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for t in golden_data["transactions"]:
            assert date_re.match(t["date"]), f"Invalid date: {t['date']}"

    def test_investments_have_positive_values(self, golden_data):
        for inv in golden_data["investments"]:
            assert inv["value_brl"] > 0


class TestE16Goldens:
    """Goldens E1.6 — schema parses, validator accepts, analyzer KPIs match (ADR-157)."""

    FIXTURE_NAMES = ("completo", "simplificado", "edge_cases")

    @pytest.fixture
    def fixtures(self):
        return {
            name: json.loads((GOLDEN_DIR / f"e16_irpf_full_{name}.json").read_text())
            for name in self.FIXTURE_NAMES
        }

    @pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
    def test_schema_parses(self, fixtures, fixture_name):
        from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput

        IRPFFullOutput.model_validate(fixtures[fixture_name])

    @pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
    def test_validator_accepts_no_errors(self, fixtures, fixture_name):
        from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput
        from pipeline.llm.validators import validate_e16_output

        out = IRPFFullOutput.model_validate(fixtures[fixture_name])
        result = validate_e16_output(out)
        assert result.valid, f"{fixture_name} errors: {result.errors}"

    @pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
    def test_no_unmasked_cpf_in_free_text(self, fixtures, fixture_name):
        import re

        cpf_re = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
        eleven_digits = re.compile(r"\b\d{11}\b")
        text_blob = json.dumps(fixtures[fixture_name])
        assert not cpf_re.search(text_blob), f"{fixture_name} has unmasked CPF literal"
        assert not eleven_digits.search(text_blob), f"{fixture_name} has 11-digit run (CPF-shaped)"

    @pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
    def test_prompt_version_pinned(self, fixtures, fixture_name):
        assert fixtures[fixture_name]["prompt_version"] == "e16-v1.0.0"

    @pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
    def test_reconcile_ir_pago_within_tolerance(self, fixtures, fixture_name):
        from decimal import Decimal

        d = fixtures[fixture_name]
        soma = Decimal("0")
        for fp in d["rendimentos_pj"]:
            soma += Decimal(fp["ir_retido_brl"])
            if fp.get("decimo_terceiro_ir_retido_brl") is not None:
                soma += Decimal(fp["decimo_terceiro_ir_retido_brl"])
        for fp in d["rendimentos_pf"]:
            soma += Decimal(fp["ir_recolhido_brl"])
        ir_pago = Decimal(d["imposto_apurado"]["ir_pago_brl"])
        assert abs(ir_pago - soma) <= Decimal(
            "0.02"
        ), f"{fixture_name}: ir_pago={ir_pago} vs soma_retidos={soma}"

    def test_completo_renda_e_aliquotas(self, fixtures):
        from decimal import Decimal

        from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer

        a = IRPFAnalyzer.from_payloads([fixtures["completo"]])
        assert a.anos_base_disponiveis() == [2024]
        assert a.renda_anual_familiar(2024) == Decimal("371800.00")
        assert a.rendimentos_tributaveis(2024) == Decimal("310300.00")
        # ir_pago = 38000 (PJ) + 1880 (13º RFB tabela exclusiva) + 5500 (PJ) + 2700 (PF) = 48080.
        assert a.ir_pago_total(2024) == Decimal("48080.00")
        assert a.renda_liquida_familiar(2024) == Decimal("297720.00")
        ali = a.aliquotas(2024)
        assert round(ali.sobre_tributavel_pct, 2) == Decimal("15.49")
        assert round(ali.sobre_total_pct, 2) == Decimal("12.93")

    def test_completo_split_pgbl_dependentes(self, fixtures):
        from decimal import Decimal

        from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer

        a = IRPFAnalyzer.from_payloads([fixtures["completo"]])
        assert a.contrib_previdenciaria_total(2024) == Decimal("8000.00")
        assert a.pensao_alimenticia_paga(2024) == Decimal("18000.00")
        assert a.pgbl_capacidade_dedutivel(2024) == Decimal("7236.0000")
        sp = a.split_trabalho_vs_capital(2024)
        # A8.3 PR-B: aluguéis PF (R$ 30.000 — Inquilino Ficcional A) saíram
        # de trabalho e entraram em capital (Perini/AUVP capital imobiliário).
        # Trabalho 320000 → 290000 (-30000); capital 46800 → 76800 (+30000).
        assert sp.trabalho_brl == Decimal("290000.00")
        assert sp.capital_brl == Decimal("76800.00")
        assert len(a.dependentes_validos(2024)) == 2

    def test_simplificado_pgbl_capacity_zero(self, fixtures):
        from decimal import Decimal

        from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer

        a = IRPFAnalyzer.from_payloads([fixtures["simplificado"]])
        # Modelo simplificado nunca usa PGBL — capacidade deve ser zero por design (G0).
        assert a.pgbl_capacidade_dedutivel(2024) == Decimal("0")
        assert a.renda_anual_familiar(2024) == Decimal("81500.00")
        assert a.ir_pago_total(2024) == Decimal("3000.00")
        # Nenhum dependente.
        assert a.dependentes_validos(2024) == []

    def test_edge_cases_multi_currency_exterior(self, fixtures):
        from decimal import Decimal

        from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer

        a = IRPFAnalyzer.from_payloads([fixtures["edge_cases"]])
        # PJ 180k + 13º exclusiva 15k = 195k trabalho; exterior USD+EUR = 43.150 capital.
        sp = a.split_trabalho_vs_capital(2024)
        assert sp.trabalho_brl == Decimal("195000.00")
        assert sp.capital_brl == Decimal("43150.00")
        # Confidence baixo permitido — não bloqueia parse.
        assert fixtures["edge_cases"]["confidence"] == 0.82
        # Dois dependentes (1 sem CPF, 1 com CPF — universitária <24 anos).
        deps = a.dependentes_validos(2024)
        assert len(deps) == 2
        cpf_present = [d.cpf_masked for d in deps]
        assert None in cpf_present
        assert any(c is not None for c in cpf_present)

    def test_simplificado_with_pgbl_emits_warning(self, fixtures):
        """Sandtrap: simplificado + PGBL deve disparar warning (G2 coverage gap)."""
        from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput
        from pipeline.llm.validators import validate_e16_output

        mutated = json.loads(json.dumps(fixtures["simplificado"]))
        mutated["pagamentos_efetuados"] = [
            {
                "codigo_rfb": "36",
                "beneficiario_nome": "Itau Previdencia",
                "beneficiario_cpf_cnpj_masked": "60.701.190/0001-04",
                "valor_pago_brl": "20000.00",
                "valor_dedutivel_brl": "20000.00",
                "teto_aplicado": False,
            }
        ]
        out = IRPFFullOutput.model_validate(mutated)
        result = validate_e16_output(out)
        assert result.valid, f"unexpected errors: {result.errors}"
        assert any("simplificado" in w and "PGBL" in w for w in result.warnings)

    def test_codigo_99_outro_fallback_in_edge_cases(self, fixtures):
        """Coverage do enum fallback `99_outro` (G2 coverage gap)."""
        edge = fixtures["edge_cases"]
        codigos = [r["codigo_rfb"] for r in edge["rendimentos_isentos"]]
        assert "99_outro" in codigos, "edge_cases deve exercitar `99_outro` fallback"

    def test_evolucao_renda_multi_year(self, fixtures):
        from decimal import Decimal

        from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer

        # Combinar fixture completo (ano 2024) com edge_cases reescrito p/ 2023.
        completo = fixtures["completo"]
        edge_2023 = json.loads(json.dumps(fixtures["edge_cases"]))
        edge_2023["contribuinte"]["ano_base"] = 2023
        edge_2023["contribuinte"]["exercicio"] = 2024
        a = IRPFAnalyzer.from_payloads([completo, edge_2023])
        ev = a.evolucao_renda_anos()
        assert ev[2024] == Decimal("371800.00")
        # 2023 = trib (180k+25.75k+17.4k) + isento (99_outro 8k) + exclusiva (13º 15k) = 246.150,00.
        assert ev[2023] == Decimal("246150.00")


class TestE7ReviewGoldenFile:
    @pytest.fixture
    def golden_data(self):
        return json.loads((GOLDEN_DIR / "e7_review_output.json").read_text())

    def test_schema_parses(self, golden_data):
        from pipeline.llm.schemas.e7_review import E7ReviewOutput

        output = E7ReviewOutput(**golden_data)
        assert len(output.insights) == 3
        assert len(output.recommendations) == 3
        assert output.risk_level == "moderate"
        assert output.confidence == 0.85

    def test_output_converter(self, golden_data):
        from pipeline.llm.schemas.e7_review import E7ReviewOutput
        from pipeline.stages.review_finances import _output_to_review_json

        output = E7ReviewOutput(**golden_data)
        result = _output_to_review_json(output)

        assert result["nivel_risco"] == "moderate"
        assert len(result["insights"]) == 3
        assert len(result["recomendacoes"]) == 3
        assert len(result["ajustes_score"]) == 2
        assert "resumo_executivo" in result["narrativas"]
        assert "patrimonio_analise" in result["narrativas"]

    def test_insights_have_valid_categories(self, golden_data):
        valid = {
            "patrimonio",
            "fluxo_caixa",
            "investimentos",
            "endividamento",
            "planejamento",
            "score",
        }
        for ins in golden_data["insights"]:
            assert ins["category"] in valid, f"Invalid category: {ins['category']}"

    def test_insights_have_valid_severities(self, golden_data):
        valid = {"info", "attention", "warning", "critical"}
        for ins in golden_data["insights"]:
            assert ins["severity"] in valid, f"Invalid severity: {ins['severity']}"

    def test_risk_level_valid(self, golden_data):
        valid = {"low", "moderate", "high", "critical"}
        assert golden_data["risk_level"] in valid
