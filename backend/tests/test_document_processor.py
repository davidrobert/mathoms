"""Unit tests for DocumentProcessor service."""

import json
import tempfile
from pathlib import Path

import pytest

from backend.app.models.document import DocumentStatus, DocumentType
from backend.app.services.documents.document_classification import (
    map_e0_doc_type_to_document_type as _map_doc_type,
)
from backend.app.services.documents.document_processor import (
    _detect_json_type,
    process_uploaded_document,
)


class TestDetectJsonType:
    def test_members_via_membros_key(self, tmp_path):
        f = tmp_path / "m.json"
        f.write_text(json.dumps({"membros": [{"nome": "A"}]}))
        assert _detect_json_type(f) == DocumentType.e1_members_json

    def test_members_via_members_key(self, tmp_path):
        f = tmp_path / "m.json"
        f.write_text(json.dumps({"members": [{"nome": "A"}]}))
        assert _detect_json_type(f) == DocumentType.e1_members_json

    def test_baseline_via_patrimonio_key(self, tmp_path):
        f = tmp_path / "b.json"
        f.write_text(json.dumps({"patrimonio": {"total": 1000}}))
        assert _detect_json_type(f) == DocumentType.e1_5_baseline_json

    def test_baseline_via_baseline_key(self, tmp_path):
        f = tmp_path / "b.json"
        f.write_text(json.dumps({"baseline": True}))
        assert _detect_json_type(f) == DocumentType.e1_5_baseline_json

    def test_unrecognized_json(self, tmp_path):
        f = tmp_path / "x.json"
        f.write_text(json.dumps({"foo": "bar"}))
        assert _detect_json_type(f) is None

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json at all")
        assert _detect_json_type(f) is None

    def test_list_with_cpf(self, tmp_path):
        f = tmp_path / "m2.json"
        f.write_text(json.dumps([{"nome": "A", "cpf": "123"}]))
        assert _detect_json_type(f) == DocumentType.e1_members_json

    def test_list_with_valor(self, tmp_path):
        f = tmp_path / "b2.json"
        f.write_text(json.dumps([{"tipo": "CDB", "valor": 1000}]))
        assert _detect_json_type(f) == DocumentType.e1_5_baseline_json


class TestMapDocType:
    def test_extratoconta(self):
        assert _map_doc_type("extratoconta") == DocumentType.bank_statement

    def test_extratoconta_brl_variant(self):
        # E0-route produces specific currency variants
        assert _map_doc_type("extratocontabrl") == DocumentType.bank_statement
        assert _map_doc_type("extratocontausd") == DocumentType.bank_statement
        assert _map_doc_type("extratocontaeur") == DocumentType.bank_statement

    def test_extratoconta_named_variants(self):
        assert _map_doc_type("extratocontapersonnalite") == DocumentType.bank_statement
        assert _map_doc_type("extratocontapj") == DocumentType.bank_statement
        assert _map_doc_type("extratocontaglobalusd") == DocumentType.bank_statement

    def test_extratopoupanca(self):
        assert _map_doc_type("extratopoupanca") == DocumentType.bank_statement

    def test_faturacartao(self):
        assert _map_doc_type("faturacartao") == DocumentType.credit_card_bill

    def test_fatura_variants(self):
        # Real codes emitted by E0-route regex
        assert _map_doc_type("fatura") == DocumentType.credit_card_bill
        assert _map_doc_type("faturaunique") == DocumentType.credit_card_bill
        assert _map_doc_type("faturacarbon") == DocumentType.credit_card_bill
        assert _map_doc_type("faturapaoacucar") == DocumentType.credit_card_bill
        assert _map_doc_type("faturasantander") == DocumentType.credit_card_bill

    def test_faturaaluguel_is_other(self):
        # Rent invoice is not a credit card bill
        assert _map_doc_type("faturaaluguel") == DocumentType.other

    def test_investimentos(self):
        assert _map_doc_type("investimentos") == DocumentType.investment_report

    def test_cdb_variants(self):
        assert _map_doc_type("cdb") == DocumentType.investment_report
        assert _map_doc_type("cdbdetalhesdi1") == DocumentType.investment_report
        assert _map_doc_type("cdbresumo") == DocumentType.investment_report

    def test_carteira_and_posicao(self):
        assert _map_doc_type("investimentosposicao") == DocumentType.investment_report
        assert _map_doc_type("carteirarendafixa") == DocumentType.investment_report

    def test_irpfdeclaracao(self):
        assert _map_doc_type("irpfdeclaracao") == DocumentType.irpf

    def test_informerendimentos(self):
        # ADR-238 A17 L1 P3: informe genérico legado mantém compat com .irpf
        # até L2-L4 cobrirem todos os tipos canônicos; aluguel tem cutover
        # próprio (ADR-216) — vai para .other temporariamente.
        assert _map_doc_type("informerendimentos") == DocumentType.irpf
        assert _map_doc_type("informerendimentosaluguel") == DocumentType.other

    def test_informe_previdencia_privada_mapping(self):
        # ADR-238 D3: informe_previdencia_* dispara stage extract_informes_anuais.
        assert (
            _map_doc_type("informe_previdencia_privada") == DocumentType.informe_rendimentos_anuais
        )

    def test_unknown(self):
        assert _map_doc_type("weird_type") == DocumentType.other

    def test_empty(self):
        assert _map_doc_type("") == DocumentType.other


class TestProcessUploadedDocument:
    def test_json_members_bypasses_classify(self, tmp_path):
        f = tmp_path / "members.json"
        f.write_text(json.dumps({"membros": [{"nome": "Test"}]}))
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        result = process_uploaded_document(f, [], config_dir)
        assert result["status"] == DocumentStatus.ready
        assert result["doc_type"] == DocumentType.e1_members_json
        assert result["error_message"] is None

    def test_json_baseline_bypasses_classify(self, tmp_path):
        f = tmp_path / "baseline.json"
        f.write_text(json.dumps({"patrimonio": {"total": 1000}}))
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        result = process_uploaded_document(f, [], config_dir)
        assert result["status"] == DocumentStatus.ready
        assert result["doc_type"] == DocumentType.e1_5_baseline_json

    def test_csv_uses_classify(self, tmp_path):
        f = tmp_path / "extrato.csv"
        f.write_text("data,descricao,valor\n2026-01-01,Test,100\n")
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "institutions.json").write_text("{}")
        (config_dir / "pipeline.json").write_text("{}")
        (config_dir / "family_members.json").write_text("{}")
        result = process_uploaded_document(f, [], config_dir)
        assert result["status"] == DocumentStatus.ready
        assert result["error_message"] is None
