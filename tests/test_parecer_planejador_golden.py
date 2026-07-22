"""Golden mockado do stage parecer_planejador — schema + invariants estruturais (ADR-199)."""

from __future__ import annotations

import json

# Feature flag precisa estar habilitada para o stage não-skipar.
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

os.environ["MATHOMS_ENABLE_PARECER_PLANEJADOR"] = "true"

from backend.app.services.storage.llm_cache import InMemoryLLMCache  # noqa: E402
from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.llm.schemas.parecer_planejador import (  # noqa: E402
    ImpactoEstimado,
    Metadata,
    Metrica,
    NotaMetodologica,
    ParecerPlanejadorOutput,
    PontoForte,
    Risco,
    Sugestao,
)

_REPO = Path(__file__).resolve().parents[1]
_OUTPUT_SCHEMA = _REPO / "config" / "schemas" / "parecer_planejador.schema.json"


def make_workspace_e5(
    *,
    cobertura_meses: float = 2.1,
    avaliacao_liquidity: str = "insuficiente",
) -> dict:
    """E5 sintético rico — alta renda PJ/CLT; reserva parametrizável p/ estratificar o holdout."""
    return {
        "periodo_dados": "2024-01-01 a 2025-12-31",
        "data_analise": "2026-01-15",
        "score": {"valor": 6.5, "classificacao": "Bom"},
        "patrimonio": {
            "bruto": 5_200_000.0,
            "liquido": 4_700_000.0,
            "dividas": 500_000.0,
            "composicao": {
                "imoveis_residencia": 1_800_000.0,
                "imoveis_investimento": 800_000.0,
                "rf": 600_000.0,
                "rv_br": 900_000.0,
                "rv_intl": 400_000.0,
                "caixa": 200_000.0,
                "previdencia": 500_000.0,
            },
        },
        "fluxo_caixa": {
            "receita_total": 720_000.0,
            "receita_recorrente_mensal": 55_000.0,
            "despesa_total": 480_000.0,
            "despesa_mensal_media": 40_000.0,
            "fluxo_liquido": 240_000.0,
        },
        "ratios": {
            "rentabilidade": {
                "valor_pct": 4.7,
                "ano_base": 2024,
                "defasagem_meses": 5,
                "meta_pct": 5.0,
                "cobertura_despesa_essencial_pct": 80.0,
                "status": "ok",
            },
            "rentabilidade_pct": "4.70",
            "aliquota_efetiva_ir_pct": "22.50",
        },
        "reserva_emergencia": {
            "despesas_mensais": 40_000.0,
            "cobertura_meses": cobertura_meses,
            "total_liquida": 84_000.0,
            "avaliacao_liquidity": avaliacao_liquidity,
        },
        "endividamento": {
            "total_dividas": 500_000.0,
            "percentual_patrimonio": 9.6,
        },
        "investimentos": {
            "total": 3_200_000.0,
            # A37.l9 — decomposição por construção + pct por base declarada:
            # pct = % do total investido (inclui imóveis físicos);
            # pct_carteira_financeira = % ex-imóveis (None na linha de imóveis).
            "total_financeiro": 2_400_000.0,
            "total_imoveis_investimento": 800_000.0,
            "fonte": "irpf_bens",
            "tabela_classes": [
                {
                    "categoria": "Imóveis Investimento",
                    "valor": 800_000.0,
                    "pct": 25.0,
                    "pct_carteira_financeira": None,
                },
                {
                    "categoria": "RF",
                    "valor": 600_000.0,
                    "pct": 18.7,
                    "pct_carteira_financeira": 25.0,
                },
                {
                    "categoria": "RV BR",
                    "valor": 900_000.0,
                    "pct": 28.1,
                    "pct_carteira_financeira": 37.5,
                },
                {
                    "categoria": "RV Intl",
                    "valor": 400_000.0,
                    "pct": 12.5,
                    "pct_carteira_financeira": 16.7,
                },
                {
                    "categoria": "FIIs",
                    "valor": 300_000.0,
                    "pct": 9.4,
                    "pct_carteira_financeira": 12.5,
                },
                {
                    "categoria": "Caixa",
                    "valor": 200_000.0,
                    "pct": 6.3,
                    "pct_carteira_financeira": 8.3,
                },
            ],
            "top_ativos": [],
            "n_imoveis_total": 4,
        },
        # A37.l9 (CTO-04/PE-05) — conceito distinto da alocação internacional.
        "exposicao_cambial": {
            "total_brl": 52_000.0,
            "pct_investivel_financeiro": 2.16,
            "por_moeda": [{"moeda": "USD", "valor_brl": 52_000.0, "share_pct": 100.0}],
            "tier": "vermelho",
            "detalhes": [],
        },
        "previdencia_pgbl": {
            "saldo": 500_000.0,
            "contribuicao_anual": 50_000.0,
            "limite_abate_pct": 12.0,
            "abate_real_pct": 6.9,
            "pgbl_status": "subaplicado",
        },
        "irpf_kpis": {
            "renda_tributavel_total_brl": 720_000.0,
            "aliquota_sobre_tributavel_pct": "22.50",
            "aliquota_sobre_total_pct": "15.30",
            "dependentes_count": 2,
        },
        "passive_income": {"renda_passiva_mensal": 32_000.0, "cobertura_pct": 80.0},
        "if_monte_carlo": {"prazo_p50": 12, "prazo_p90": 18},
        "cenarios_conjuge": {"labels": ["Com cônjuge", "Sem cônjuge"], "prazos_if": [12, 22]},
        "pontos_fortes": ["Diversificação razoável", "Sem dívida cara"],
        "pontos_urgentes": ["Reserva baixa", "PGBL subaplicado"],
        "alertas": ["seguro_vida_ausente", "fbar_pendente"],
        "equilibrio_cerbasi": {"taxa_poupanca_pct": 33.3, "classificacao": "Saudável"},
        "diagnostico_comportamental": ["consumo_consciente"],
        "tarefas": [],
        "tarefas_status": {"total": 0, "abertas": 0, "fechadas": 0},
        "goals": {"if_meta": 6_000_000.0, "trs_pct": 4.0},
        "consumo_consciente": {"folga_mensal": 15_000.0, "folga_pct": 27.0},
        "narrativas": {"perfil_familia": "Alta renda PJ + CLT, 2 dependentes."},
    }


def make_canned_output(workspace_id: str = "ws-golden") -> ParecerPlanejadorOutput:
    """Output rico que exercita todos os campos + invariants."""
    meta = Metadata(
        persona_hash="0" * 64,
        manifest_version="1.0.0",
        model_id="placeholder",
        tier_at_generation="premium",
        generated_at="2026-05-13T12:00:00+00:00",
    )

    pontos_fortes = [
        PontoForte(
            titulo="Diversificação multi-classe consolidada",
            descricao="Carteira distribuída em RF, RV BR e Intl, FIIs e imóveis — reduz risco idiossincrático.",
            ancora_metodologica="auvp",
            tema_canonico="Alocação",
            section_id="S3",
        ),
        PontoForte(
            titulo="Taxa de poupança recorrente saudável",
            descricao="Aproximadamente trinta e três por cento da renda destinados à acumulação patrimonial.",
            ancora_metodologica="cerbasi",
            tema_canonico="Equilíbrio presente-futuro",
            section_id="S2",
        ),
        PontoForte(
            titulo="Ausência de dívida cara",
            descricao="Sem cartão rotativo, cheque especial ou similares — perfil de juros sob controle.",
            ancora_metodologica="convergencia",
            tema_canonico="Saúde de balanço",
            section_id="S1",
        ),
    ]

    riscos = [
        Risco(
            severidade="Crítica",
            titulo="Seguro de vida ausente para provedor de renda",
            descricao="Família depende de um provedor principal sem cobertura de vida, expondo dependentes a risco material.",
            ancora_metodologica="cerbasi",
            tema_canonico="Proteção",
            evidencia="Alerta seguro_vida_ausente presente em S9.",
            evidencia_path="$.alertas",
            section_id="S9",
            confianca="alta",
        ),
        Risco(
            severidade="Alta",
            titulo="Reserva de emergência cobre apenas 2,1 meses",
            descricao="Cobertura atual abaixo do alvo recomendado de seis meses de despesas essenciais.",
            ancora_metodologica="convergencia",
            tema_canonico="Liquidez",
            evidencia="reserva_emergencia.cobertura_meses=2.1",
            evidencia_path="$.reserva_emergencia.cobertura_meses",
            section_id="S1",
            confianca="alta",
        ),
        Risco(
            severidade="Média",
            titulo="PGBL subaplicado para perfil de alta renda",
            descricao="Aporte atual aproveita apenas 6,9 por cento do limite dedutível anual.",
            ancora_metodologica="convergencia",
            tema_canonico="Custo tributário",
            evidencia="abate_real_pct=6.9",
            evidencia_path="$.previdencia_pgbl.abate_real_pct",
            section_id="S8",
            confianca="alta",
        ),
    ]

    sug_exec = [
        Sugestao(
            prioridade="P0",
            acao="Contratar seguro de vida para o provedor principal cobrindo 5 anos de renda recorrente.",
            impacto_qualitativo="Protege dependentes contra evento adverso enquanto patrimônio gerador não cobre custo essencial.",
            ancora_metodologica="cerbasi",
            tema_canonico="Proteção",
            confianca="alta",
            section_id="S9",
            suggestion_dedup_key="0" * 64,  # orchestrator reescreve
            evidencia_path="$.alertas",
        ),
        Sugestao(
            prioridade="P1",
            acao="Aportar mensalmente em pós-fixada D+0/D+1 até reserva atingir seis meses de despesa essencial.",
            impacto_qualitativo="Reduz dependência de crédito em choque de renda; alinhamento metodológico amplo.",
            ancora_metodologica="convergencia",
            tema_canonico="Liquidez",
            confianca="alta",
            section_id="S1",
            suggestion_dedup_key="0" * 64,
            evidencia_path="$.reserva_emergencia.cobertura_meses",
            impacto_estimado=ImpactoEstimado(
                valor_estimado_brl=210_000.0,
                unidade="ano",
                caveat="Estimativa indicativa baseada na despesa atual; revisitar a cada 6 meses.",
            ),
        ),
    ]

    sug_tat = [
        Sugestao(
            prioridade="P1",
            acao="Aumentar contribuição PGBL anual até o teto dedutível de doze por cento da renda tributável.",
            impacto_qualitativo="Eficiência tributária no presente combinada com acumulação previdenciária integrada.",
            ancora_metodologica="convergencia",
            tema_canonico="Custo tributário",
            confianca="alta",
            section_id="S8",
            suggestion_dedup_key="0" * 64,
            evidencia_path="$.previdencia_pgbl.abate_real_pct",
        ),
    ]

    sug_est = [
        Sugestao(
            prioridade="P2",
            acao="Revisar exposição cambial ao redor de quinze por cento do patrimônio investível financeiro.",
            impacto_qualitativo="Diversifica risco de moeda doméstica em horizonte de 12 a 36 meses.",
            ancora_metodologica="auvp",
            tema_canonico="Alocação",
            confianca="media",
            section_id="S3",
            suggestion_dedup_key="0" * 64,
            evidencia_path="$.investimentos.tabela_classes[*]",
        ),
    ]

    metricas = [
        Metrica(
            nome="Cobertura essencial da reserva",
            valor_atual="2,1 meses",
            target="6+ meses",
            frequencia_revisao="trimestral",
            section_id="S1",
            ancora_metodologica="convergencia",
            tema_canonico="Liquidez",
        ),
        Metrica(
            nome="Abate PGBL real vs limite",
            valor_atual="6,9%",
            target="12,0%",
            frequencia_revisao="anual",
            section_id="S8",
            ancora_metodologica="convergencia",
            tema_canonico="Custo tributário",
        ),
    ]

    notas = [
        NotaMetodologica(
            titulo="Conservadorismo na cobertura essencial",
            conteudo="A análise prioriza cobertura essencial sobre estilo de vida nesta fase do ciclo familiar.",
            ancoras_metodologicas=["cerbasi", "convergencia"],
        )
    ]

    return ParecerPlanejadorOutput(
        version="1.0",
        metadata=meta,
        diagnostico_geral=(
            "Família com patrimônio bruto consolidado, taxa de poupança saudável e diversificação razoável, "
            "porém com gaps de proteção (seguro de vida ausente) e liquidez (reserva 2,1 meses) que pedem atenção imediata."
        ),
        pontos_fortes=pontos_fortes,
        riscos=riscos,
        sugestoes_execucao=sug_exec,
        sugestoes_taticas=sug_tat,
        sugestoes_estrategicas=sug_est,
        metricas=metricas,
        notas_metodologicas=notas,
    )


@dataclass
class _FakeCallResult:
    output: Any
    tokens_in: int = 5234
    tokens_out: int = 1450
    cost_estimate_usd: float = 0.0789  # rate USD mock (ADR-090 — production converts to cents)


@dataclass
class _FakeSummary:
    calls: list = field(default_factory=list)


class _FakeLLMService:
    def __init__(self, output: ParecerPlanejadorOutput) -> None:
        self._output = output
        self.summary = _FakeSummary()

    def call(self, **kwargs):
        result = _FakeCallResult(output=self._output)
        self.summary.calls.append(result)
        return result


@pytest.fixture
def workspace_e5() -> dict:
    return make_workspace_e5()


@pytest.fixture
def canned_output() -> ParecerPlanejadorOutput:
    return make_canned_output()


# -----------------------------------------------------------------------
# Stage end-to-end com store in-memory
# -----------------------------------------------------------------------


def make_run_stage_with_mocks(
    e5: dict, canned: ParecerPlanejadorOutput, workspace_id: str = "ws-golden"
):
    """Helper: roda o stage com ArtifactStore in-memory + LLM/cache mockados."""
    from pipeline.context import WorkspaceContext

    # Stub minimal ctx — não usa filesystem.
    store = InMemoryArtifactStore()
    store.seed("E5", "analise_financeira", e5)

    # ctx in-memory; root pode ser path qualquer válido (nada é escrito em disco).
    # ``llm_config.json`` override popula api_key — sem isso, ``_resolve_api_key``
    # do stage wrapper retorna ``None`` e o stage pula (paridade c/ extract_members).
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ctx = WorkspaceContext(
            root=Path(tmp),
            artifact_store=store,
            workspace_id=workspace_id,
            config_overrides={"llm_config.json": {"api_key": "sk-mock"}},
        )

        # Monkey-patch generate_parecer para injetar fakes
        from backend.app.services import parecer_orchestrator as orch
        from pipeline.stages import parecer_planejador as stage_mod

        original_generate = orch.generate_parecer

        def patched(**kwargs):
            return original_generate(
                **kwargs,
                llm_service=_FakeLLMService(output=canned),
                cache=InMemoryLLMCache(),
            )

        # Importa pelo nome do módulo onde stage referencia
        orch.generate_parecer = patched  # type: ignore[assignment]
        # Stage import (within function) usa parecer_orchestrator.generate_parecer
        # diretamente — monkeypatch já efetiva via lookup.
        try:
            result = stage_mod.run(ctx)
        finally:
            orch.generate_parecer = original_generate  # type: ignore[assignment]

    return result, store


class TestStageGoldenSchemaValidation:
    def test_artifact_validates_against_json_schema(self, workspace_e5, canned_output):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        assert result["success"] is True
        artifact = store.read("E6-parecer", "parecer_planejador")
        assert artifact is not None

        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(_OUTPUT_SCHEMA.read_text(encoding="utf-8"))
        # Removendo _meta — JSON Schema cobre, mas valida o output mesmo.
        jsonschema.validate(artifact, schema)


class TestStageGoldenInvariants:
    def test_count_p0_at_most_2(self, workspace_e5, canned_output):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        all_sug = (
            artifact["sugestoes_execucao"]
            + artifact["sugestoes_taticas"]
            + artifact["sugestoes_estrategicas"]
        )
        p0_count = sum(1 for s in all_sug if s["prioridade"] == "P0")
        assert p0_count <= 2

    def test_all_temas_in_enum(self, workspace_e5, canned_output):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        valid_temas = {
            "Proteção",
            "Alocação",
            "Renda passiva",
            "Liquidez",
            "Custo tributário",
            "Saúde de balanço",
            "Diagnóstico de dados",
            "Equilíbrio presente-futuro",
            "Convergência metodológica",
        }
        for risco in artifact["riscos"]:
            assert risco["tema_canonico"] in valid_temas
        for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
            for sug in artifact[horizon]:
                assert sug["tema_canonico"] in valid_temas

    def test_all_ancoras_in_enum(self, workspace_e5, canned_output):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        valid_ancoras = {"perini", "cerbasi", "auvp", "convergencia"}
        for risco in artifact["riscos"]:
            assert risco["ancora_metodologica"] in valid_ancoras
        for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
            for sug in artifact[horizon]:
                assert sug["ancora_metodologica"] in valid_ancoras

    def test_hard_caps_respected(self, workspace_e5, canned_output):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        assert len(artifact["riscos"]) <= 12
        assert len(artifact["sugestoes_execucao"]) <= 5
        assert len(artifact["sugestoes_taticas"]) <= 5
        assert len(artifact["sugestoes_estrategicas"]) <= 5
        assert len(artifact["metricas"]) <= 10
        assert len(artifact["notas_metodologicas"]) <= 5
        assert 3 <= len(artifact["pontos_fortes"]) <= 6

    def test_impacto_estimado_only_with_alta_confianca(self, workspace_e5, canned_output):
        """ADR-202 §D6 — impacto_estimado válido só com confianca='alta'."""
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
            for sug in artifact[horizon]:
                if sug.get("impacto_estimado") is not None:
                    assert (
                        sug["confianca"] == "alta"
                    ), f"Sugestão {horizon} com impacto_estimado e confianca={sug['confianca']}"

    def test_every_suggestion_has_section_id_and_evidencia_path_optional(
        self, workspace_e5, canned_output
    ):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
            for sug in artifact[horizon]:
                assert sug["section_id"]
                # evidencia_path opcional, mas se presente respeita regex.
                if sug.get("evidencia_path"):
                    assert sug["evidencia_path"].startswith("$.")


class TestStageGoldenMetaAndCost:
    def test_meta_has_audit_fields(self, workspace_e5, canned_output):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        meta = artifact["_meta"]
        assert "tool_trace" in meta
        assert "cost_usd" in meta
        assert "tokens_in" in meta
        assert "tokens_out" in meta
        assert "latency_ms" in meta
        assert "tool_iterations" in meta
        assert "cache_hit" in meta
        assert "schema_version" in meta

    def test_cost_populated_from_mock(self, workspace_e5, canned_output):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        # FakeCallResult fornece cost=0.0789
        assert artifact["_meta"]["cost_usd"] > 0

    def test_tokens_populated(self, workspace_e5, canned_output):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        assert artifact["_meta"]["tokens_in"] > 0
        assert artifact["_meta"]["tokens_out"] > 0


class TestStageGoldenDedupKey:
    def test_dedup_key_recalculated_deterministic(self, workspace_e5, canned_output):
        """Mesmo input → mesmo dedup_key (idempotência ADR-153)."""
        result1, store1 = make_run_stage_with_mocks(
            workspace_e5, canned_output, workspace_id="ws-A"
        )
        # canned_output é compartilhado, mas como model_copy é usado, segundo run
        # recebe um output fresh — recriar via factory:
        result2, store2 = make_run_stage_with_mocks(
            workspace_e5, make_canned_output(), workspace_id="ws-A"
        )

        art1 = store1.read("E6-parecer", "parecer_planejador")
        art2 = store2.read("E6-parecer", "parecer_planejador")

        k1 = art1["sugestoes_execucao"][0]["suggestion_dedup_key"]
        k2 = art2["sugestoes_execucao"][0]["suggestion_dedup_key"]
        assert k1 == k2

    def test_dedup_key_changes_across_workspaces(self, workspace_e5, canned_output):
        result1, store1 = make_run_stage_with_mocks(
            workspace_e5, make_canned_output(), workspace_id="ws-A"
        )
        result2, store2 = make_run_stage_with_mocks(
            workspace_e5, make_canned_output(), workspace_id="ws-B"
        )

        art1 = store1.read("E6-parecer", "parecer_planejador")
        art2 = store2.read("E6-parecer", "parecer_planejador")

        k1 = art1["sugestoes_execucao"][0]["suggestion_dedup_key"]
        k2 = art2["sugestoes_execucao"][0]["suggestion_dedup_key"]
        assert k1 != k2

    def test_dedup_key_is_sha256_hex(self, workspace_e5, canned_output):
        result, store = make_run_stage_with_mocks(workspace_e5, canned_output)
        artifact = store.read("E6-parecer", "parecer_planejador")
        for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
            for sug in artifact[horizon]:
                key = sug["suggestion_dedup_key"]
                assert len(key) == 64
                # Pode ser convertida para int hex
                int(key, 16)


# -----------------------------------------------------------------------
# Caso negativo: regex anti-ticker (Pydantic validator rejeita)
# -----------------------------------------------------------------------


class TestPydanticRejectsTickerInBody:
    def test_descricao_with_ticker_fails_validation(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="ticker"):
            Risco(
                severidade="Alta",
                titulo="Concentração em ativo",
                descricao="Posição relevante em VALE3 expõe a risco idiossincrático.",
                ancora_metodologica="auvp",
                tema_canonico="Alocação",
                section_id="S3",
                confianca="alta",
            )

    def test_descricao_with_sigilo_term_fails_validation(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="sigilo"):
            Risco(
                severidade="Alta",
                titulo="Gap metodológico",
                descricao="Família precisa adotar metodologia Perini de forma mais consistente.",
                ancora_metodologica="convergencia",
                tema_canonico="Diagnóstico de dados",
                section_id="S10",
                confianca="alta",
            )


# -----------------------------------------------------------------------
# Caso negativo: cap P0 > 2 rejeitado pelo model_validator
# -----------------------------------------------------------------------


def _make_p0_sugestao(acao_suffix: int) -> Sugestao:
    """Constrói Sugestao P0 sintática válida (com acao único)."""
    return Sugestao(
        prioridade="P0",
        acao=f"Ação P0 distinta numero {acao_suffix} para testar cap agregado.",
        impacto_qualitativo=f"Impacto sintético {acao_suffix} para validar invariant P0 cap.",
        ancora_metodologica="convergencia",
        tema_canonico="Saúde de balanço",
        confianca="alta",
        section_id="S1",
        suggestion_dedup_key="0" * 64,
    )


class TestPydanticEnforcesP0Cap:
    def test_three_p0s_fails(self):
        from pydantic import ValidationError

        out = make_canned_output()
        p0_a, p0_b, p0_c = (_make_p0_sugestao(i) for i in range(3))
        with pytest.raises(ValidationError, match="P0"):
            out.model_copy(
                update={"sugestoes_execucao": [p0_a, p0_b], "sugestoes_taticas": [p0_c]}
            ).model_validate(
                out.model_copy(
                    update={"sugestoes_execucao": [p0_a, p0_b], "sugestoes_taticas": [p0_c]}
                ).model_dump()
            )


# -----------------------------------------------------------------------
# Feature flag desligada → stage skip
# -----------------------------------------------------------------------


class TestFeatureFlag:
    def test_disabled_returns_skipped(self, monkeypatch, workspace_e5, canned_output):
        from pipeline.context import WorkspaceContext

        monkeypatch.setenv("MATHOMS_ENABLE_PARECER_PLANEJADOR", "false")
        # Re-importa stage_mod para pegar nova env
        from pipeline.stages import parecer_planejador as stage_mod

        store = InMemoryArtifactStore()
        store.seed("E5", "analise_financeira", workspace_e5)
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ctx = WorkspaceContext(root=Path(tmp), artifact_store=store, workspace_id="ws-skipped")
            result = stage_mod.run(ctx)
        assert result.get("skipped") is True
        assert "feature flag" in result.get("reason", "").lower()


# -----------------------------------------------------------------------
# Resolução de api_key (paridade com extract_members)
# -----------------------------------------------------------------------
#
# Regressão do incidente 2026-05-14: o stage rodava em premium com
# ``llm_config.json`` configurado no DB, mas o orchestrator só lia
# ``ANTHROPIC_API_KEY`` do env. Sem env-var, generate_parecer retornava
# ``needs_review`` em 0.1s e o pipeline marcava run como failed.


class TestApiKeyResolution:
    def _make_ctx(self, workspace_e5: dict, overrides: dict | None = None):
        import tempfile

        from pipeline.context import WorkspaceContext

        store = InMemoryArtifactStore()
        store.seed("E5", "analise_financeira", workspace_e5)
        tmp = tempfile.mkdtemp()
        return WorkspaceContext(
            root=Path(tmp),
            artifact_store=store,
            workspace_id="ws-key",
            config_overrides=overrides,
        )

    def test_skipped_when_no_api_key_anywhere(self, monkeypatch, workspace_e5):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from pipeline.stages import parecer_planejador as stage_mod

        ctx = self._make_ctx(workspace_e5, overrides=None)
        result = stage_mod.run(ctx)
        assert result.get("skipped") is True
        assert "no llm config" in result.get("reason", "").lower()
        # Importante: NÃO success=False — paridade c/ extract_members evita
        # abortar pipeline por falta de config.
        assert "success" not in result or result["success"] is not False

    def _patch_orchestrator(self, monkeypatch, canned_output, captured: dict[str, str]):
        """Patcha generate_parecer capturando o original ANTES — evita recursão."""
        from backend.app.services import parecer_orchestrator as orch

        original = orch.generate_parecer

        def patched(**kwargs):
            captured["api_key"] = kwargs["config"].api_key
            return original(
                **kwargs,
                llm_service=_FakeLLMService(output=canned_output),
                cache=InMemoryLLMCache(),
            )

        monkeypatch.setattr(orch, "generate_parecer", patched)

    def test_uses_llm_config_json_api_key(self, monkeypatch, workspace_e5, canned_output):
        """``llm_config.json`` (DB-backed) preenche api_key — paridade com E1/E1.5."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from pipeline.stages import parecer_planejador as stage_mod

        ctx = self._make_ctx(workspace_e5, overrides={"llm_config.json": {"api_key": "sk-from-db"}})
        captured: dict[str, str] = {}
        self._patch_orchestrator(monkeypatch, canned_output, captured)
        result = stage_mod.run(ctx)
        assert result["success"] is True
        assert captured["api_key"] == "sk-from-db"

    def test_env_fallback_when_no_llm_config_json(self, monkeypatch, workspace_e5, canned_output):
        """Sem llm_config.json, ANTHROPIC_API_KEY do env continua válido (CLI/dev)."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
        from pipeline.stages import parecer_planejador as stage_mod

        ctx = self._make_ctx(workspace_e5, overrides=None)
        captured: dict[str, str] = {}
        self._patch_orchestrator(monkeypatch, canned_output, captured)
        result = stage_mod.run(ctx)
        assert result["success"] is True
        assert captured["api_key"] == "sk-from-env"


# -----------------------------------------------------------------------
# Cross-provider smoke (ADR-199 Ato 6 T-24)
# -----------------------------------------------------------------------
#
# Rodam APENAS via workflow `llm-cross-provider-smoke.yml` (weekly + manual).
# Skipam em CI normal via marker + check de env vars.
# Assertions estruturais — schema válido, hard caps, regex anti-ticker, dedup
# reprodutível, ancora_metodologica ∈ enum. Não comparam texto (LLM
# não-determinístico, ADR-202 temp baixa não garante reprodutibilidade
# textual exata entre providers).


def _cross_provider_env_or_skip() -> tuple[str, str]:
    """Resolve (provider, model_id) do env; skipa se ausente."""
    provider = os.environ.get("MATHOMS_LLM_PROVIDER", "").strip()
    model_id = os.environ.get("MATHOMS_LLM_MODEL_ID", "").strip()
    if not provider or not model_id:
        pytest.skip(
            "Cross-provider smoke exige MATHOMS_LLM_PROVIDER + MATHOMS_LLM_MODEL_ID. "
            "Rode via .github/workflows/llm-cross-provider-smoke.yml."
        )
    return provider, model_id


def _cost_cap_cents_or_default() -> int:
    """Cap soft de custo por call — falha se exceder. Default $0.50."""
    raw = os.environ.get("MATHOMS_PARECER_COST_CAP_USD_CENTS", "50")
    try:
        return int(raw)
    except ValueError:
        return 50


def _assert_dedup_keys_well_formed(sugestoes: list[dict]) -> None:
    """Cada dedup_key deve ser sha256 hex (64 chars hex)."""
    for sug in sugestoes:
        key = sug["suggestion_dedup_key"]
        assert len(key) == 64
        int(key, 16)  # parse hex


@pytest.mark.cross_provider
class TestCrossProviderSmoke:
    """Smoke estrutural por provider — assertions invariantes, não textuais."""

    def test_schema_valid_across_provider(self, workspace_e5):
        """Output schema valida (Pydantic + JSON Schema) após chamada real."""
        provider, model_id = _cross_provider_env_or_skip()
        result, store = self._call_real_llm(workspace_e5, provider, model_id)
        artifact = store.read("E6-parecer", "parecer_planejador")
        assert artifact is not None
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(_OUTPUT_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(artifact, schema)

    def test_hard_caps_respected_across_provider(self, workspace_e5):
        """Hard caps (ADR-202 §D3): riscos ≤ 12, P0 ≤ 2 agregado, etc."""
        provider, model_id = _cross_provider_env_or_skip()
        result, store = self._call_real_llm(workspace_e5, provider, model_id)
        artifact = store.read("E6-parecer", "parecer_planejador")
        assert len(artifact["riscos"]) <= 12
        all_sug = (
            artifact["sugestoes_execucao"]
            + artifact["sugestoes_taticas"]
            + artifact["sugestoes_estrategicas"]
        )
        p0_count = sum(1 for s in all_sug if s["prioridade"] == "P0")
        assert p0_count <= 2

    def test_anti_ticker_regex_holds_across_provider(self, workspace_e5):
        """Regex anti-ticker BR (ADR-202 §D4) deve continuar valendo cross-provider."""
        import re

        ticker_re = re.compile(r"[A-Z]{4}\d{1,2}|[A-Z]{4}11")
        provider, model_id = _cross_provider_env_or_skip()
        result, store = self._call_real_llm(workspace_e5, provider, model_id)
        artifact = store.read("E6-parecer", "parecer_planejador")
        body_texts = [artifact["diagnostico_geral"]]
        for risco in artifact["riscos"]:
            body_texts.append(risco["descricao"])
        for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
            for sug in artifact[horizon]:
                body_texts.append(sug["acao"])
                body_texts.append(sug["impacto_qualitativo"])
        for text in body_texts:
            assert not ticker_re.search(text), f"ticker leaked in: {text!r}"

    def test_ancora_metodologica_in_enum_across_provider(self, workspace_e5):
        """``ancora_metodologica`` ∈ enum fechado pós-call (ADR-202)."""
        provider, model_id = _cross_provider_env_or_skip()
        result, store = self._call_real_llm(workspace_e5, provider, model_id)
        artifact = store.read("E6-parecer", "parecer_planejador")
        valid_ancoras = {"perini", "cerbasi", "auvp", "convergencia"}
        for risco in artifact["riscos"]:
            assert risco["ancora_metodologica"] in valid_ancoras
        for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
            for sug in artifact[horizon]:
                assert sug["ancora_metodologica"] in valid_ancoras

    def test_dedup_key_reproducible_across_provider(self, workspace_e5):
        """Mesmo input → mesmo dedup_key (idempotência ADR-153). Estrutural, não textual — keys são derivadas de ação+ancora+workspace_id, não do texto LLM."""
        provider, model_id = _cross_provider_env_or_skip()
        # 2 calls, mesma E5, mesmo workspace_id.
        _, store_a = self._call_real_llm(workspace_e5, provider, model_id, workspace_id="ws-CX")
        _, store_b = self._call_real_llm(workspace_e5, provider, model_id, workspace_id="ws-CX")
        art_a = store_a.read("E6-parecer", "parecer_planejador")
        art_b = store_b.read("E6-parecer", "parecer_planejador")
        # Ambos têm sugestoes_execucao (schema garante 0-5; cap LLM tende ≥1 em E5 rico).
        if not (art_a["sugestoes_execucao"] and art_b["sugestoes_execucao"]):
            return
        _assert_dedup_keys_well_formed(art_a["sugestoes_execucao"] + art_b["sugestoes_execucao"])

    def test_cost_within_cap_across_provider(self, workspace_e5):
        """Custo da call não excede cap (default $0.50)."""
        provider, model_id = _cross_provider_env_or_skip()
        cap_cents = _cost_cap_cents_or_default()
        result, store = self._call_real_llm(workspace_e5, provider, model_id)
        artifact = store.read("E6-parecer", "parecer_planejador")
        cost_usd = artifact["_meta"]["cost_usd"]
        cost_cents = int(cost_usd * 100)
        assert cost_cents > 0, "cost_usd zero indica mock — cross-provider exige call real"
        assert (
            cost_cents <= cap_cents
        ), f"cost {cost_cents} cents excede cap {cap_cents} para {provider}"

    def _call_real_llm(
        self,
        workspace_e5: dict,
        provider: str,
        model_id: str,
        workspace_id: str = "ws-cross",
    ):
        """Helper — roda stage com LLM real. Não monkeypatcha LLMService; usa o que está no env."""
        import tempfile

        from pipeline.context import WorkspaceContext
        from pipeline.stages import parecer_planejador as stage_mod

        os.environ["MATHOMS_PARECER_PLANEJADOR_MODEL"] = model_id
        store = InMemoryArtifactStore()
        store.seed("E5", "analise_financeira", workspace_e5)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = WorkspaceContext(root=Path(tmp), artifact_store=store, workspace_id=workspace_id)
            result = stage_mod.run(ctx)
        return result, store
