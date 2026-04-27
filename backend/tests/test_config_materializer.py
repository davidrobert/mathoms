"""Tests for Phase 3C: ConfigMaterializer — serializers and disk materialization."""

import json
from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import selectinload, sessionmaker

import backend.app.models  # noqa: F401
from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models.category import Category, CategoryKeyword
from backend.app.models.config_blob import InstitutionConfig, PipelineConfig, ReportLayout
from backend.app.models.family_member import BankAccount, FamilyMember
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.config_materializer import (
    materialize_config,
    serialize_categorization,
    serialize_family_members,
    serialize_institution_config,
    serialize_llm_config,
    serialize_pipeline_config,
    serialize_report_layout,
)
from backend.app.services.vault import VaultService

sync_engine = create_engine("sqlite://", echo=False)
SyncTestSession = sessionmaker(bind=sync_engine)

_vault = VaultService()


@pytest.fixture(autouse=True)
def setup_sync_db():
    Base.metadata.create_all(sync_engine)
    yield
    Base.metadata.drop_all(sync_engine)


@pytest.fixture
def db():
    session = SyncTestSession()
    yield session
    session.close()


@pytest.fixture
def workspace(db) -> Workspace:
    user = User(email="mat@test.com", hashed_password=hash_password("x"), full_name="Mat")
    db.add(user)
    db.flush()
    ws = Workspace(name="Mat WS", owner_id=user.id)
    db.add(ws)
    db.commit()
    return ws


# =============================================================================
# Serializer tests
# =============================================================================


class TestSerializeFamilyMembers:
    def test_empty_returns_none(self, db, workspace):
        assert serialize_family_members(workspace.id, db) is None

    def test_basic_serialization(self, db, workspace):
        # CPF gerado por tests/utils/cpf.py seed=42  # noqa: PII-ok
        cpf_enc = _vault.encrypt("910.428.398-01")  # noqa: PII-ok
        m = FamilyMember(
            workspace_id=workspace.id,
            key="david",
            full_name="David Robert",
            short_name="David",
            cpf_encrypted=cpf_enc,
            role="titular",
            order=0,
            extra={"profissao": "CTO"},
        )
        db.add(m)
        db.flush()
        db.add(BankAccount(member_id=m.id, institution_code="itau", account_type="extratoconta"))
        db.commit()

        result = serialize_family_members(workspace.id, db)
        assert result is not None
        assert "david" in result["membros"]
        assert result["membros"]["david"]["cpf"] == "910.428.398-01"  # noqa: PII-ok (gerado por tests/utils/cpf.py seed=42)
        assert result["membros"]["david"]["profissao"] == "CTO"
        assert result["banco_membro"]["itau"] == "david"
        assert result["titular"] == "david"

    def test_multiple_members(self, db, workspace):
        db.add(
            FamilyMember(
                workspace_id=workspace.id,
                key="a",
                full_name="A",
                short_name="A",
                role="titular",
                order=0,
            )
        )
        db.add(
            FamilyMember(
                workspace_id=workspace.id,
                key="b",
                full_name="B",
                short_name="B",
                role="conjuge",
                order=1,
            )
        )
        db.commit()

        result = serialize_family_members(workspace.id, db)
        assert set(result["membros"].keys()) == {"a", "b"}


class TestSerializeCategorization:
    def test_empty_returns_none(self, db, workspace):
        assert serialize_categorization(workspace.id, db) is None

    def test_basic_serialization(self, db, workspace):
        cat = Category(
            workspace_id=workspace.id,
            code="moradia",
            name="Moradia",
            category_type="expense",
            order=0,
        )
        db.add(cat)
        db.flush()
        db.add(CategoryKeyword(category_id=cat.id, keyword="ENEL"))
        db.add(CategoryKeyword(category_id=cat.id, keyword="SABESP"))
        income = Category(
            workspace_id=workspace.id,
            code="receita_pj",
            name="Receita PJ",
            category_type="income",
            order=1,
        )
        db.add(income)
        db.flush()
        db.add(CategoryKeyword(category_id=income.id, keyword="ARVO"))
        db.commit()

        result = serialize_categorization(workspace.id, db)
        assert result is not None
        assert "moradia" in result["expense_keywords"]
        assert set(result["expense_keywords"]["moradia"]) == {"ENEL", "SABESP"}
        assert "receita_pj" in result["income_keywords"]


class TestSerializeBlobs:
    def test_pipeline_config(self, db, workspace):
        assert serialize_pipeline_config(workspace.id, db) is None
        db.add(PipelineConfig(workspace_id=workspace.id, config_json={"llm": {"model": "gpt-4o"}}))
        db.commit()
        result = serialize_pipeline_config(workspace.id, db)
        assert result["llm"]["model"] == "gpt-4o"

    def test_institution_config(self, db, workspace):
        assert serialize_institution_config(workspace.id, db) is None
        db.add(
            InstitutionConfig(
                workspace_id=workspace.id, config_json={"banco_canonical": {"itau": "Itaú"}}
            )
        )
        db.commit()
        result = serialize_institution_config(workspace.id, db)
        assert result["banco_canonical"]["itau"] == "Itaú"

    def test_report_layout(self, db, workspace):
        assert serialize_report_layout(workspace.id, db) is None
        db.add(ReportLayout(workspace_id=workspace.id, config_json={"version": "2.0"}))
        db.commit()
        result = serialize_report_layout(workspace.id, db)
        assert result["version"] == "2.0"


# =============================================================================
# Materialization tests
# =============================================================================


class TestMaterializeConfig:
    def test_copies_global_config(self, db, workspace, tmp_path):
        """With empty DB, materialized config equals global config."""
        tenant_root = tmp_path / "tenant"
        tenant_root.mkdir()

        config_dir = materialize_config(workspace.id, tenant_root, db)

        assert config_dir == tenant_root / "config"
        assert (config_dir / "family_members.json").exists()
        assert (config_dir / "categorization.json").exists()
        assert (config_dir / "pipeline.json").exists()
        assert (config_dir / "institutions.json").exists()
        assert (config_dir / "report_layout.yaml").exists()
        assert (config_dir / "definitions.md").exists()

    def test_overrides_family_members(self, db, workspace, tmp_path):
        db.add(
            FamilyMember(
                workspace_id=workspace.id,
                key="custom",
                full_name="Custom User",
                short_name="Custom",
                role="titular",
                order=0,
            )
        )
        db.commit()

        tenant_root = tmp_path / "tenant"
        tenant_root.mkdir()
        config_dir = materialize_config(workspace.id, tenant_root, db)

        with open(config_dir / "family_members.json", "r") as f:
            data = json.load(f)
        assert "custom" in data["membros"]
        assert "david" not in data["membros"]

    def test_overrides_pipeline_json(self, db, workspace, tmp_path):
        db.add(
            PipelineConfig(workspace_id=workspace.id, config_json={"custom_key": "custom_value"})
        )
        db.commit()

        tenant_root = tmp_path / "tenant"
        tenant_root.mkdir()
        config_dir = materialize_config(workspace.id, tenant_root, db)

        with open(config_dir / "pipeline.json", "r") as f:
            data = json.load(f)
        assert data["custom_key"] == "custom_value"

    def test_overrides_report_layout_yaml(self, db, workspace, tmp_path):
        db.add(
            ReportLayout(
                workspace_id=workspace.id, config_json={"version": "custom", "sections": []}
            )
        )
        db.commit()

        tenant_root = tmp_path / "tenant"
        tenant_root.mkdir()
        config_dir = materialize_config(workspace.id, tenant_root, db)

        with open(config_dir / "report_layout.yaml", "r") as f:
            data = yaml.safe_load(f)
        assert data["version"] == "custom"

    def test_unedited_configs_remain_global(self, db, workspace, tmp_path):
        """Configs not in DB stay as copies from global."""
        db.add(PipelineConfig(workspace_id=workspace.id, config_json={"only_this": True}))
        db.commit()

        tenant_root = tmp_path / "tenant"
        tenant_root.mkdir()
        config_dir = materialize_config(workspace.id, tenant_root, db)

        with open(config_dir / "family_members.json", "r") as f:
            data = json.load(f)
        assert "membros" in data
        assert "david" in data["membros"]

    def test_idempotent(self, db, workspace, tmp_path):
        """Running materialize twice produces the same result."""
        tenant_root = tmp_path / "tenant"
        tenant_root.mkdir()

        materialize_config(workspace.id, tenant_root, db)
        materialize_config(workspace.id, tenant_root, db)

        assert (tenant_root / "config" / "pipeline.json").exists()

    def test_preserves_templates_and_schemas(self, db, workspace, tmp_path):
        """Non-editable files (templates/, schemas/, definitions.md) are copied."""
        tenant_root = tmp_path / "tenant"
        tenant_root.mkdir()
        config_dir = materialize_config(workspace.id, tenant_root, db)

        global_config = Path(__file__).resolve().parent.parent.parent.parent / "config"
        if (global_config / "templates").exists():
            assert (config_dir / "templates").exists()
        if (global_config / "schemas").exists():
            assert (config_dir / "schemas").exists()


# =============================================================================
# Phase 4 — LLM Config serializer
# =============================================================================


class TestSerializeLLMConfig:
    def test_empty_returns_none(self, db, workspace):
        assert serialize_llm_config(workspace.id, db) is None

    def test_basic_serialization(self, db, workspace):
        from backend.app.models.llm_config import LLMConfig as LLMConfigModel

        cfg = LLMConfigModel(
            workspace_id=workspace.id,
            provider="anthropic",
            api_key_encrypted=_vault.encrypt("sk-ant-test-key-123"),
            model_name="claude-sonnet-4-20250514",
            max_tokens=8192,
            temperature=0.2,
        )
        db.add(cfg)
        db.commit()

        data = serialize_llm_config(workspace.id, db)
        assert data is not None
        assert data["provider"] == "anthropic"
        assert data["api_key"] == "sk-ant-test-key-123"
        assert data["model_name"] == "claude-sonnet-4-20250514"
        assert data["max_tokens"] == 8192
        assert data["temperature"] == 0.2

    def test_materialize_writes_llm_config(self, db, workspace, tmp_path):
        """materialize_config() writes llm_config.json to tenant config dir."""
        from backend.app.models.llm_config import LLMConfig as LLMConfigModel

        cfg = LLMConfigModel(
            workspace_id=workspace.id,
            provider="openai",
            api_key_encrypted=_vault.encrypt("sk-openai-key"),
            model_name="gpt-4o",
            max_tokens=4096,
            temperature=0.1,
        )
        db.add(cfg)
        db.commit()

        tenant_root = tmp_path / "tenant_llm"
        tenant_root.mkdir()
        config_dir = materialize_config(workspace.id, tenant_root, db)

        llm_path = config_dir / "llm_config.json"
        assert llm_path.exists()

        with open(llm_path) as f:
            data = json.load(f)
        assert data["provider"] == "openai"
        assert data["api_key"] == "sk-openai-key"
        assert data["model_name"] == "gpt-4o"

    def test_materialize_without_llm_config(self, db, workspace, tmp_path):
        """materialize_config() does not write llm_config.json if no LLM config in DB."""
        tenant_root = tmp_path / "tenant_no_llm"
        tenant_root.mkdir()
        config_dir = materialize_config(workspace.id, tenant_root, db)

        llm_path = config_dir / "llm_config.json"
        assert not llm_path.exists()


# ═══════════════════════════════════════════════════════════════════════
# A7.1 (ADR-134) — prepare_pipeline_config_dir + DeprecationWarning
# ═══════════════════════════════════════════════════════════════════════


def _capture_materialize_logs():
    """Captura logs de ``mathoms.config.materialize`` durante o teste."""
    import logging

    records: list[logging.LogRecord] = []

    class _H(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _H()
    logger = logging.getLogger("mathoms.config.materialize")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return records, handler, logger


_SENTINEL_MEMBER_KEY = "ws_sentinel_member_xyz"
_SENTINEL_CATEGORY_CODE = "ws_sentinel_category_xyz"


def _seed_sentinel_member(db, workspace_id: str) -> None:
    db.add(
        FamilyMember(
            workspace_id=workspace_id,
            key=_SENTINEL_MEMBER_KEY,
            full_name="X",
            short_name="X",
            role="titular",
            order=0,
        )
    )


def _seed_sentinel_category(db, workspace_id: str) -> None:
    db.add(
        Category(
            workspace_id=workspace_id,
            code=_SENTINEL_CATEGORY_CODE,
            name="X",
            category_type="expense",
            order=1,
        )
    )


def _seed_a7_1_sentinels(db, workspace_id: str) -> tuple[str, str]:
    """Adiciona FamilyMember + Category sentinela para verificar não-materialização."""
    _seed_sentinel_member(db, workspace_id)
    _seed_sentinel_category(db, workspace_id)
    db.commit()
    return _SENTINEL_MEMBER_KEY, _SENTINEL_CATEGORY_CODE


def test_materialize_config_emits_deprecation_warning(db, workspace, tmp_path):
    """A7.1: ``materialize_config`` agora é deprecated; legacy_call log fires."""
    from backend.app.services.config_materializer import materialize_config

    tenant_root = tmp_path / "tenant_dep"
    tenant_root.mkdir()
    with pytest.warns(DeprecationWarning, match="materialize_config"):
        materialize_config(workspace.id, tenant_root, db)

    records, handler, logger = _capture_materialize_logs()
    try:
        materialize_config(workspace.id, tenant_root, db)
    finally:
        logger.removeHandler(handler)
    assert any("legacy_call" in r.getMessage() for r in records)


def test_prepare_pipeline_config_dir_skips_a7_1_configs(db, workspace, tmp_path):
    """A7.1: novo helper não materializa categorization/family_members/etc."""
    from backend.app.services.config_materializer import prepare_pipeline_config_dir

    sentinel_key, sentinel_cat = _seed_a7_1_sentinels(db, workspace.id)
    tenant_root = tmp_path / "tenant_thin"
    tenant_root.mkdir()
    config_dir = prepare_pipeline_config_dir(workspace.id, tenant_root, db)

    fm_disk = json.loads((config_dir / "family_members.json").read_text(encoding="utf-8"))
    assert sentinel_key not in (fm_disk.get("membros") or {})

    cat_disk = json.loads((config_dir / "categorization.json").read_text(encoding="utf-8"))
    assert sentinel_cat not in (cat_disk.get("expense_keywords") or {})


def test_prepare_pipeline_config_dir_does_not_emit_legacy_call(db, workspace, tmp_path):
    """A7.1: o novo helper NÃO emite ``mathoms.config.materialize.legacy_call``."""
    from backend.app.services.config_materializer import prepare_pipeline_config_dir

    tenant_root = tmp_path / "tenant_clean"
    tenant_root.mkdir()
    records, handler, logger = _capture_materialize_logs()
    try:
        prepare_pipeline_config_dir(workspace.id, tenant_root, db)
    finally:
        logger.removeHandler(handler)
    assert all("legacy_call" not in r.getMessage() for r in records)
