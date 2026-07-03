#!/usr/bin/env python3
"""Tests for validate_artifact schema validation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.pipeline_common import validate_artifact

_TOP_ATIVO_VALID = {
    "posicao": 1,
    "nome": "Tesouro IPCA+ 2045",
    "classe": "Renda Fixa",
    "membro": "david",
    "instituicao": "Btg",
    "valor": 300000,
    "pct_carteira": 30.0,
    "tipo_origem": "investimento",
}
_IMOVEL_VALID = {
    "posicao": 2,
    "nome": "Sala comercial",
    "classe": "Imóveis Investimento",
    "membro": "",
    "instituicao": "",
    "valor": 250000,
    "pct_carteira": 25.0,
    "tipo_origem": "imovel",
}
_TOP_ATIVO_INVALID_CLASSE = {**_TOP_ATIVO_VALID, "classe": "ClasseDesconhecida"}

_INST_VALID = [
    {"membro": "david", "instituicoes": ["Btg", "Itau"]},
    {"membro": "mariana", "instituicoes": ["Xp"]},
]


_E5_BUILD_DEFAULTS = {
    "periodo_dados": "2026-01 a 2026-12",
    "data_analise": "2026-04-19",
    "patrimonio": {"bruto": 1_500_000, "liquido": 1_200_000},
    "goals": {"if_meta": 5_000_000},
    "fluxo": {"receita_total": 100_000, "janela": "full", "janela_meses": 12},
    "ratios": {"taxa_poupanca_recorrente_pct": 30},
    "score": {"valor": 7.0, "classificacao": "Bom"},
    "orcamento": {"total": 5000},
    "reserva": {"cobertura_meses": 12},
    "endividamento": {"total_dividas": 0},
    "previdencia": {"status": "N/D"},
    "pontos_fortes": [{"titulo": "Score Positivo"}],
    "pontos_urgentes": [{"acao": "X", "prioridade": "Alta", "prazo": "Imediato", "impacto": "Y"}],
    "investimentos_classes": {"total": 500_000, "tabela_classes": []},
    "equilibrio_cerbasi": {"classificacao": "Equilibrado"},
    "consumo": {"total_pontuais": 0},
    "diagnostico": [],
}

_FLUXO_REAL_CONJUGE = {
    "receita_despesa_mensal_detalhado": {
        "receita_datasets": [{"label": "Receita CLT Mariana", "data": [8000] * 12}]
    }
}


def _build_real_cenarios_conjuge_config():
    """Constrói CenariosConjugeConfig com defaults da ADR-167 (titular david / cônjuge mariana)."""
    from datetime import date

    from pipeline.domain.services.cenarios_conjuge_analyzer import CenariosConjugeConfig

    return CenariosConjugeConfig(
        titular_dob=date(1985, 6, 15),
        retorno_real_anual_pct=6.0,
        aporte_base=15_000,
        fator_reduzido=0.66,
        titular_key="david",
        conjuge_key="mariana",
        conjuge_nome="Mariana",
        reference_date=date(2026, 4, 19),
    )


def _cenarios_conjuge_real_payload():
    """Roda CenariosConjugeAnalyzer real e retorna to_legacy_dict (ADR-166/167)."""
    from pipeline.domain.services.cenarios_conjuge_analyzer import CenariosConjugeAnalyzer

    analyzer = CenariosConjugeAnalyzer(_build_real_cenarios_conjuge_config())
    result = analyzer.analyze(
        patrimonio={"investivel": 1_200_000},
        goals={"if_meta": 5_000_000},
        fluxo=_FLUXO_REAL_CONJUGE,
    )
    return result.to_legacy_dict()


def _build_e5_with_cenarios(cenarios_payload):
    """Monta E5OutputInputs minimal e chama build_e5_output (paridade pipeline ↔ schema)."""
    from pipeline.domain.services.e5_serialization import E5OutputInputs, build_e5_output

    inputs = E5OutputInputs(**_E5_BUILD_DEFAULTS, cenarios_conjuge=cenarios_payload)
    return build_e5_output(inputs)


def _cenarios_conjuge_with_titular(titular_key: str):
    """Sintetiza payload cenarios_conjuge com titular_key arbitrário (testa patternProperties)."""
    return {
        "labels": ["Sem renda do cônjuge"],
        "aportes": [5000.0],
        "prazos_if": [20.0],
        "anos_if": [2046],
        f"idade_{titular_key}_if": [60],
        "premissas": {"meta_if": 3_000_000.0},
        "cenarios": [
            {
                "nome": "Sem renda do cônjuge",
                "aporte_mensal": 5000.0,
                "prazo_if_anos": 20.0,
                "ano_if": 2046,
                f"idade_{titular_key}": 60,
                "resumo": "...",
            }
        ],
    }


# ADR-166 + ADR-167 — payload real produzido por
# CenariosConjugeAnalyzer.to_legacy_dict() em
# pipeline/domain/services/cenarios_conjuge_analyzer.py.
_CENARIOS_CONJUGE_VALID = {
    "labels": ["Sem renda do cônjuge"],
    "aportes": [9900.0],
    "prazos_if": [12.5],
    "anos_if": [2038],
    "idade_david_if": [55],
    "premissas": {
        "meta_if": 5_000_000.0,
        "investivel_atual": 1_200_000.0,
        "retorno_real_anual_pct": 6.0,
        "aporte_base": 15_000.0,
        "fator_reduzido": 0.66,
        "salario_mariana_clt_brl": 8000.0,
    },
    "cenarios": [
        {
            "nome": "Sem renda do cônjuge",
            "aporte_mensal": 9900.0,
            "prazo_if_anos": 12.5,
            "ano_if": 2038,
            "idade_david": 55,
            "resumo": "Sem renda do cônjuge, aporte cai para R$ 9.900/mês (66% do base). IF em 13 anos (2038).",
        }
    ],
}


def _e5_with_top_ativos(*items):
    return {
        "score": {"valor": 6.8, "classificacao": "Bom"},
        "patrimonio": {"bruto": 5000000, "liquido": 4000000},
        "fluxo_caixa": {"receita_total": 80000, "janela": "full", "janela_meses": 0},
        "investimentos": {
            "tabela_classes": [{"categoria": "Renda Fixa", "valor": 800000, "pct": 80.0}],
            "total": 1000000,
            "top_ativos": list(items),
        },
    }


def _e5_with_instituicoes(por_membro, n_imoveis=0):
    return {
        "score": {"valor": 6.8, "classificacao": "Bom"},
        "patrimonio": {"bruto": 5000000, "liquido": 4000000},
        "fluxo_caixa": {"janela": "full", "janela_meses": 0},
        "investimentos": {
            "instituicoes_por_membro": por_membro,
            "n_imoveis_total": n_imoveis,
        },
    }


# ADR-283 — contrato por-transação E2 (audit AST dos 12 parsers em scripts/e2/banks/).
_E2_EXTRACT_BASE = {
    "pipeline_stage": "E2",
    "banco": "c6bank",
    "tipo": "faturaunique",
    "moeda": "BRL",
}
_E2_TRANSACAO_TODOS_CAMPOS = {
    "data": "2026-01-15",
    "descricao": "COMPRA INTERNACIONAL",
    "valor": -250.0,
    "direction": "debit",
    "parcela": "1/3",
    "nr_doc": "00012345",
    "cartao": "Carbon",
    "forex": {"moeda_original": "USD", "valor_original": 50.0, "cotacao": 5.0},
    "natural_key": {"hash": "abc123", "hash_version": 2},
}


class TestValidateArtifact:
    def test_valid_e2_extract(self, tmp_path):
        data = {
            "pipeline_stage": "E2",
            "banco": "itau",
            "tipo": "extratoconta",
            "moeda": "BRL",
            "transacoes": [{"data": "2026-01-15", "descricao": "PIX", "valor": -100.0}],
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e2_extract.schema.json") is True

    def test_e2_transacao_accepts_all_audited_optional_fields(self, tmp_path, monkeypatch):
        """ADR-283 — campos por-transação dos 12 parsers passam em strict."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = {**_E2_EXTRACT_BASE, "transacoes": [_E2_TRANSACAO_TODOS_CAMPOS]}
        path = tmp_path / "e2.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e2_extract.schema.json") is True

    def test_e2_contract_no_methodological_fields(self, tmp_path, monkeypatch):
        """ADR-280 (F2-B5) — campo metodológico em de-leak é proibido por AUSÊNCIA no contrato.

        `additionalProperties:false` faz o enforcement: o campo não declarado
        falha em strict. Reintroduzir `tipo_lancamento` no schema quebra a
        primeira asserção; reintroduzir num writer quebra a segunda.
        """
        schema_path = (
            Path(__file__).resolve().parent.parent / "config/schemas/e2_extract.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        # ADR-286: transação vive em $defs/transacao (compartilhada com
        # e2_llm_artifact via $ref) — o gate navega o $defs.
        transacao = schema["$defs"]["transacao"]
        assert schema["properties"]["transacoes"]["items"] == {"$ref": "#/$defs/transacao"}
        for leak_field in ("tipo_lancamento",):
            assert (
                leak_field not in transacao["properties"]
            ), f"{leak_field} voltou ao contrato E2 — de-leak ADR-280 exige re-derivar na Transform"
        assert transacao["additionalProperties"] is False

        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = {
            **_E2_EXTRACT_BASE,
            "transacoes": [{**_E2_TRANSACAO_TODOS_CAMPOS, "tipo_lancamento": "iof"}],
        }
        path = tmp_path / "e2.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e2_extract.schema.json") is False

    def test_e2_transacao_strict_rejects_unknown_field(self, tmp_path, monkeypatch):
        """ADR-283 — campo não declarado na transação falha em strict (sinal de drift)."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = {
            "pipeline_stage": "E2",
            "banco": "itau",
            "tipo": "extratoconta",
            "moeda": "BRL",
            "transacoes": [
                {"data": "2026-01-15", "descricao": "PIX", "valor": -100.0, "campo_fantasma": "x"}
            ],
        }
        path = tmp_path / "e2.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e2_extract.schema.json") is False

    def test_invalid_e2_missing_banco(self, tmp_path, caplog, monkeypatch):
        import logging

        # Força warn explicitamente — CI roda o módulo com
        # MATHOMS_PIPELINE_SCHEMA_MODE=strict para cobrir o caminho strict.
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
        caplog.set_level(logging.WARNING)
        data = {
            "pipeline_stage": "E2",
            "tipo": "extratoconta",
            "moeda": "BRL",
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        # warn mode: should return True but log warning
        result = validate_artifact(path, "e2_extract.schema.json")
        assert result is True
        assert "banco" in caplog.text

    def test_invalid_e2_strict_mode_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = {
            "pipeline_stage": "E2",
            "tipo": "extratoconta",
            "moeda": "BRL",
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e2_extract.schema.json") is False

    def test_valid_e5_analysis(self, tmp_path):
        data = {
            "score": {"valor": 6.8, "classificacao": "Bom"},
            "patrimonio": {"bruto": 5000000, "liquido": 4000000},
            "fluxo_caixa": {"receita_total": 80000, "janela": "full", "janela_meses": 0},
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_valid_e5_analysis_with_top_ativos(self, tmp_path):
        data = _e5_with_top_ativos(_TOP_ATIVO_VALID, _IMOVEL_VALID)
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_invalid_top_ativos_strict_mode_rejects_unknown_classe(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = _e5_with_top_ativos(_TOP_ATIVO_INVALID_CLASSE)
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is False

    def test_valid_e5_with_instituicoes_por_membro(self, tmp_path):
        data = _e5_with_instituicoes(_INST_VALID, n_imoveis=2)
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_invalid_instituicoes_strict_mode_rejects_duplicate(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = _e5_with_instituicoes([{"membro": "david", "instituicoes": ["Btg", "Btg"]}])
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is False

    # ---- ADR-166 + ADR-167: cenarios_conjuge formal ---------------------------

    def test_e5_schema_accepts_cenarios_conjuge_payload(self, tmp_path):
        """Payload real do CenariosConjugeAnalyzer passa em strict (ADR-166)."""
        data = {
            "score": {"valor": 6.8, "classificacao": "Bom"},
            "patrimonio": {"bruto": 5000000, "liquido": 4000000},
            "fluxo_caixa": {"janela": "full", "janela_meses": 0},
            "cenarios_conjuge": _CENARIOS_CONJUGE_VALID,
        }
        path = tmp_path / "e5.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_e5_schema_accepts_empty_cenarios_conjuge(self, tmp_path):
        """Eligibility gate (ADR-167) emite {} quando workspace não-elegível."""
        data = {
            "score": {"valor": 6.8, "classificacao": "Bom"},
            "patrimonio": {"bruto": 5000000, "liquido": 4000000},
            "fluxo_caixa": {"janela": "full", "janela_meses": 0},
            "cenarios_conjuge": {},
        }
        path = tmp_path / "e5.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_e5_schema_rejects_cenarios_conjuge_wrong_type(self, tmp_path, monkeypatch):
        """cenarios_conjuge deve ser object — string falha em strict."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = {
            "score": {"valor": 6.8, "classificacao": "Bom"},
            "patrimonio": {"bruto": 5000000, "liquido": 4000000},
            "fluxo_caixa": {"janela": "full", "janela_meses": 0},
            "cenarios_conjuge": "not_an_object",
        }
        path = tmp_path / "e5.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is False

    def test_e5_schema_rejects_cenarios_aporte_negativo(self, tmp_path, monkeypatch):
        """aporte_mensal não pode ser negativo em strict."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        bad_cenario = dict(_CENARIOS_CONJUGE_VALID)
        bad_cenario["cenarios"] = [
            {**_CENARIOS_CONJUGE_VALID["cenarios"][0], "aporte_mensal": -100.0}
        ]
        data = {
            "score": {"valor": 6.8, "classificacao": "Bom"},
            "patrimonio": {"bruto": 5000000, "liquido": 4000000},
            "fluxo_caixa": {"janela": "full", "janela_meses": 0},
            "cenarios_conjuge": bad_cenario,
        }
        path = tmp_path / "e5.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is False

    def test_e5_schema_rejects_cenario_sem_required_field(self, tmp_path, monkeypatch):
        """cenarios[*] precisa de nome/aporte_mensal/prazo_if_anos/ano_if/resumo em strict."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        bad_cenario = {
            "cenarios": [
                {"nome": "Sem renda do cônjuge", "aporte_mensal": 9900.0}
                # falta prazo_if_anos, ano_if, resumo
            ]
        }
        data = {
            "score": {"valor": 6.8, "classificacao": "Bom"},
            "patrimonio": {"bruto": 5000000, "liquido": 4000000},
            "fluxo_caixa": {"janela": "full", "janela_meses": 0},
            "cenarios_conjuge": bad_cenario,
        }
        path = tmp_path / "e5.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is False

    def test_e5_schema_aceita_idade_dynamic_key(self, tmp_path, monkeypatch):
        """patternProperties idade_<titular>_if e idade_<titular> aceitam qualquer titular_key."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = {
            "score": {"valor": 6.8, "classificacao": "Bom"},
            "patrimonio": {"bruto": 1_000_000, "liquido": 800_000},
            "fluxo_caixa": {"janela": "full", "janela_meses": 0},
            "cenarios_conjuge": _cenarios_conjuge_with_titular("alice"),
        }
        path = tmp_path / "e5.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_e5_schema_validates_real_build_e5_output(self, tmp_path):
        """build_e5_output(real_inputs) produz payload aceito pelo schema (paridade)."""
        cenarios_payload = _cenarios_conjuge_real_payload()
        payload = _build_e5_with_cenarios(cenarios_payload)
        path = tmp_path / "real_e5.json"
        path.write_text(json.dumps(payload, default=str))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_valid_e3_reconciled(self, tmp_path):
        data = {
            "banco": "itau",
            "tipo_conta": "extratoconta",
            "titular": None,
            "moeda": "BRL",
            "periodo_cobertura": {"inicio": "2026-01-01", "fim": "2026-01-31"},
            "saldo_inicial": 0.0,
            "saldo_inicial_unknown": False,
            "saldo_final": 0.0,
            "saldo_final_unknown": False,
            "fontes": ["a-2_extract.json"],
            "transacoes_total": 0,
            "transacoes_duplicadas_removidas": 0,
            "transacoes": [],
        }
        path = tmp_path / "e3.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e3_reconciled.schema.json") is True

    def test_missing_schema_returns_true(self, tmp_path):
        path = tmp_path / "test.json"
        path.write_text("{}")
        assert validate_artifact(path, "nonexistent_schema.json") is True

    def test_missing_data_file_returns_false(self, tmp_path):
        path = tmp_path / "missing.json"
        assert validate_artifact(path, "e2_extract.schema.json") is False


# Regressão: informe_base.schema.json (A17 / ADR-238 L1) é o primeiro schema do
# repo com $ref cross-file. Antes do Registry, jsonschema 4.18+ levantava
# `Unresolvable: informe_previdencia.schema.json` em vez de ValidationError, o
# que matava o stage `extract_informes_anuais` mesmo em mode=warn.
_INFORME_PREVIDENCIA_VALID = {
    "ano_base": 2024,
    "tipo_informe": "previdencia_privada",
    "fonte_pagadora_cnpj": "12345678000199",
    "fonte_pagadora_nome": "Brasilprev",
    "confidence": 0.92,
    "prompt_version": "v1.0",
    "previdencia": {
        "plano_tipo": "pgbl",
        "regime_tributacao": "progressivo",
        "contribuicoes_anuais": "24000.00",
        "saldo_31_12": "120000.00",
        "rendimentos_anuais": "8000.00",
        "resgates_anuais": "0.00",
        "ir_retido_anual": "0.00",
    },
}


class TestCrossFileRefs:
    def test_informe_base_resolves_previdencia_ref(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        path = tmp_path / "informe.json"
        path.write_text(json.dumps(_INFORME_PREVIDENCIA_VALID))
        assert validate_artifact(path, "informe_base.schema.json") is True

    def test_informe_base_strict_rejects_invalid_subschema_field(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        bad = json.loads(json.dumps(_INFORME_PREVIDENCIA_VALID))
        bad["previdencia"]["regime_tributacao"] = "invalido"
        path = tmp_path / "informe.json"
        path.write_text(json.dumps(bad))
        # Sub-schema referenciado por $ref foi efetivamente consultado.
        assert validate_artifact(path, "informe_base.schema.json") is False
