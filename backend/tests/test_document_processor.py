"""Unit tests for DocumentProcessor service."""

import json
import tempfile
from pathlib import Path

import pytest

from backend.app.models.document import DocumentStatus, DocumentType
from backend.app.services.document_processor import (
    _detect_json_type,
    _map_doc_type,
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

    def test_faturacartao(self):
        assert _map_doc_type("faturacartao") == DocumentType.credit_card_bill

    def test_investimentos(self):
        assert _map_doc_type("investimentos") == DocumentType.investment_report

    def test_irpfdeclaracao(self):
        assert _map_doc_type("irpfdeclaracao") == DocumentType.irpf

    def test_unknown(self):
        assert _map_doc_type("weird_type") == DocumentType.other


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
