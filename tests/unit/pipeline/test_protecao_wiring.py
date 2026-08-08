"""Tests — ``protecao_wiring`` (A28.l6 · ADR-240/ADR-239): apólices → compute_protecao."""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.services.protecao_wiring import (  # noqa: E402
    ProtecaoSources,
    build_fiscal_snapshot,
    build_patrimonio_snapshot,
    compute_protecao_via_store,
    family_snapshots_from_config,
    load_apolices,
    resolve_renda_anual_liquida,
)

_REPO = Path(__file__).resolve().parents[3]
_REF = date(2026, 7, 1)
_STAGE = "extract_comprovantes_bens"


def _apolice(numero: str, premio: str, bens: list[dict], meses_restantes: int = 8) -> dict:
    """Apólice sintética PII-zero, vigente em ``_REF`` por default."""
    inicio = _REF - timedelta(days=120)
    fim = _REF + timedelta(days=meses_restantes * 30)
    return {
        "apolice_numero": numero,
        "seguradora": "seguradora-sintetica",
        "vigencia_inicio": inicio.isoformat(),
        "vigencia_fim": fim.isoformat(),
        "premio_total_brl": premio,
        "forma_pagamento": "cartao",
        "corretor": {"susep_code": "000000000", "nome": "Corretora X", "cpf_or_cnpj": ""},
        "bens_segurados": bens,
        "confidence": 0.95,
    }


def _bem_veiculo() -> dict:
    return {
        "tipo": "veiculo",
        "veiculo_id": "v-1",
        "marca": "MARCA",
        "modelo": "MODELO",
        "ano_modelo": 2024,
        "coberturas": [
            {"tipo": "material", "nome": "Casco", "lmi_modo": "valor_fixo", "lmi_brl": "50000.00"}
        ],
    }


def _bem_imovel() -> dict:
    return {
        "tipo": "imovel",
        "imovel_id": "p-1",
        "tipo_imovel": "casa",
        "coberturas": [
            {
                "tipo": "material",
                "nome": "Incêndio",
                "lmi_modo": "valor_fixo",
                "lmi_brl": "400000.00",
            }
        ],
    }


def _store_com_3_apolices() -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.seed(_STAGE, "apolice_auto_2026", _apolice("AUTO-1", "1500.00", [_bem_veiculo()]))
    store.seed(_STAGE, "apolice_auto2_2026", _apolice("AUTO-2", "1800.00", [_bem_veiculo()]))
    store.seed(_STAGE, "apolice_res_2026", _apolice("RES-1", "650.00", [_bem_imovel()]))
    return store


class TestLoadApolices:
    def test_le_somente_keys_apolice(self):
        store = _store_com_3_apolices()
        store.seed(_STAGE, "crlv_abc_2026", {"tipo": "crlv"})

        apolices = load_apolices(store)

        assert len(apolices) == 3
        assert {a["apolice_numero"] for a in apolices} == {"AUTO-1", "AUTO-2", "RES-1"}

    def test_store_vazio_retorna_lista_vazia(self):
        assert load_apolices(InMemoryArtifactStore()) == []


class TestComputeProtecaoViaStore:
    def _payload(self, store: InMemoryArtifactStore) -> dict:
        return compute_protecao_via_store(
            store,
            ProtecaoSources(
                patrimonio_full={"liquido": 1_000_000, "dividas": 50_000},
                fluxo_legacy={"janela_12m": {"receita_recorrente_mensal": 20_000}},
            ),
            family_snapshots=(),
            reference_date=_REF,
        )

    def test_3_apolices_produzem_flags_e_kpis(self):
        """Critério de aceite A28.l6: 3 apólices → payload com flags."""
        payload = self._payload(_store_com_3_apolices())

        assert len(payload["apolices_vigentes"]) == 3
        assert payload["premio_total_anual_brl"] == "3950.00"
        flags = {g["categoria"]: g["flag"] for g in payload["gap_qualitativo"]}
        assert "vida" in flags and "saude" in flags

    def test_payload_valida_schema_protecao_patrimonial(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(
            (_REPO / "config" / "schemas" / "protecao_patrimonial.schema.json").read_text(
                encoding="utf-8"
            )
        )

        jsonschema.validate(self._payload(_store_com_3_apolices()), schema)

    def test_workspace_sem_apolice_degrada_g6b(self):
        payload = self._payload(InMemoryArtifactStore())

        assert payload["apolices_vigentes"] == []
        assert payload["premio_total_anual_brl"] == "0.00"
        assert payload["gap_qualitativo"]

    def test_payload_nao_vaza_pii(self):
        """Resumos LGPD-safe: nome do corretor e IDs de bens ficam fora do E5."""
        blob = json.dumps(self._payload(_store_com_3_apolices()), ensure_ascii=False)

        assert "Corretora X" not in blob
        assert "susep_code" not in blob


class TestResolveRendaAnualLiquida:
    def test_fallback_12x_receita_recorrente(self):
        renda = resolve_renda_anual_liquida(
            None, {"janela_12m": {"receita_recorrente_mensal": 10_000}}
        )
        assert renda == Decimal("120000")

    def test_zero_quando_ambos_indisponiveis(self):
        assert resolve_renda_anual_liquida(None, {}) == Decimal("0")

    def test_irpf_first_quando_disponivel(self):
        from pipeline.domain.services.irpf_completude import CompletudeAno

        class FakeIRPF:
            def estados_completude(self):
                return {2025: (CompletudeAno.completo, None)}

            def renda_liquida_familiar(self, ano):
                assert ano == 2025
                return Decimal("300000")

        renda = resolve_renda_anual_liquida(
            FakeIRPF(), {"janela_12m": {"receita_recorrente_mensal": 10_000}}
        )
        assert renda == Decimal("300000")


class TestSnapshots:
    def test_family_snapshots_from_config(self):
        family = {
            "titular": "t1",
            "membros": {
                "t1": {"papel": "titular", "data_nascimento": "1985-06-15"},
                "d1": {"papel": "dependente_filho", "data_nascimento": "2018-01-10"},
            },
        }

        snaps = family_snapshots_from_config(family, _REF)

        assert len(snaps) == 2
        dep = next(s for s in snaps if s.is_dependente)
        assert dep.idade == 8

    def test_family_vazio_degrada_para_tupla_vazia(self):
        assert family_snapshots_from_config(None, _REF) == ()

    def test_patrimonio_snapshot_requer_liquido_e_dividas(self):
        assert build_patrimonio_snapshot({}) is None
        snap = build_patrimonio_snapshot({"liquido": 100, "dividas": 10})
        assert snap.passivo_total_brl == Decimal("10")

    def test_fiscal_snapshot_categoria_saude_3_meses(self):
        fluxo = {
            "despesas": {
                "por_mes": {
                    "2026-01": {"Saúde": 500},
                    "2026-02": {"saude": 300},
                    "2026-03": {"SAÚDE E BEM ESTAR": 200},
                }
            }
        }

        snap = build_fiscal_snapshot(None, fluxo)

        assert snap.has_categoria_saude_e4_3_meses is True
        assert snap.has_deducao_saude_irpf is False
