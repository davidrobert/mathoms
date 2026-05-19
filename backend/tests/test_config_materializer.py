"""Tests para ConfigMaterializer (post-A7.5) — serializers + prepare_pipeline_config_dir."""

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.app.models  # noqa: F401
from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models.category import Category, CategoryKeyword
from backend.app.models.config_blob import InstitutionConfig, PipelineConfig, ReportLayout
from backend.app.models.family_member import BankAccount, FamilyMember
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.config_materializer import (
    prepare_pipeline_config_dir,
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
        db.add(
            BankAccount(
                member_id=m.id,
                workspace_id=workspace.id,
                institution_code="itau",
                account_type="extratoconta",
            )
        )
        db.commit()

        result = serialize_family_members(workspace.id, db)
        assert result is not None
        assert "david" in result["membros"]
        assert result["membros"]["david"]["cpf"] == "910.428.398-01"  # noqa: PII-ok (gerado por tests/utils/cpf.py seed=42)
        assert result["membros"]["david"]["profissao"] == "CTO"
        assert result["banco_membro"]["itau"] == "david"
        assert result["titular"] == "david"
        # ADR-226 PR1: contas[] aditivo
        assert len(result["contas"]) == 1
        assert result["contas"][0]["member_key"] == "david"
        assert result["contas"][0]["institution_code"] == "itau"
        assert result["contas"][0]["is_joint"] is False

    def test_multi_member_same_bank_distinct_account_numbers(self, db, workspace):
        """ADR-226 — banco_membro colide (legado), contas[] preserva os dois membros."""
        _seed_two_itau_members(db, workspace.id)
        result = serialize_family_members(workspace.id, db)
        assert result is not None
        assert result["banco_membro"]["itau"] in {"david", "mariana"}
        assert len(result["contas"]) == 2
        assert {c["account_number_norm"] for c in result["contas"]} == {"123456", "789012"}
        assert {c["member_key"] for c in result["contas"]} == {"david", "mariana"}

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
# prepare_pipeline_config_dir — boundary helper (post-A7.5)
# =============================================================================


_SENTINEL_MEMBER_KEY = "ws_sentinel_member_xyz"
_SENTINEL_CATEGORY_CODE = "ws_sentinel_category_xyz"


def _seed_a7_1_sentinels(db, workspace_id: str) -> tuple[str, str]:
    """FamilyMember + Category sentinela usados para verificar não-materialização."""
    db.add(_make_sentinel_member(workspace_id))
    db.add(_make_sentinel_category(workspace_id))
    db.commit()
    return _SENTINEL_MEMBER_KEY, _SENTINEL_CATEGORY_CODE


def _make_sentinel_member(workspace_id: str) -> FamilyMember:
    return FamilyMember(
        workspace_id=workspace_id,
        key=_SENTINEL_MEMBER_KEY,
        full_name="X",
        short_name="X",
        role="titular",
        order=0,
    )


def _make_sentinel_category(workspace_id: str) -> Category:
    return Category(
        workspace_id=workspace_id,
        code=_SENTINEL_CATEGORY_CODE,
        name="X",
        category_type="expense",
        order=1,
    )


def _seed_llm_config(db, workspace_id: str, *, provider: str, api_key: str) -> None:
    """Insere ``LLMConfig`` (vault-encrypted api_key) — helper de tests."""
    from backend.app.models.llm_config import LLMConfig as LLMConfigModel

    db.add(
        LLMConfigModel(
            workspace_id=workspace_id,
            provider=provider,
            api_key_encrypted=_vault.encrypt(api_key),
            model_name="gpt-4o",
            max_tokens=4096,
            temperature=0.1,
        )
    )
    db.commit()


class TestPreparePipelineConfigDir:
    def test_copies_global_config_tree(self, db, workspace, tmp_path):
        tenant_root = tmp_path / "tenant"
        tenant_root.mkdir()

        config_dir = prepare_pipeline_config_dir(workspace.id, tenant_root, db)

        assert config_dir == tenant_root / "config"
        # pipeline.json sobreviveu ao A7.5 — marker novo de ensure_tenant_pipeline_config.
        assert (config_dir / "pipeline.json").exists()

    def test_skips_a7_1_configs(self, db, workspace, tmp_path):
        """A7.1+A7.5: helper não escreve categorization/family_members/institutions/report_layout sentinelas."""
        sentinel_key, sentinel_cat = _seed_a7_1_sentinels(db, workspace.id)
        tenant_root = tmp_path / "tenant_thin"
        tenant_root.mkdir()
        config_dir = prepare_pipeline_config_dir(workspace.id, tenant_root, db)

        fm_path = config_dir / "family_members.json"
        if fm_path.exists():
            fm_disk = json.loads(fm_path.read_text(encoding="utf-8"))
            assert sentinel_key not in (fm_disk.get("membros") or {})

        cat_path = config_dir / "categorization.json"
        if cat_path.exists():
            cat_disk = json.loads(cat_path.read_text(encoding="utf-8"))
            assert sentinel_cat not in (cat_disk.get("expense_keywords") or {})

    def test_writes_pipeline_json_override(self, db, workspace, tmp_path):
        """``pipeline.json`` continua sendo materializado (fora do escopo A7.1)."""
        db.add(
            PipelineConfig(workspace_id=workspace.id, config_json={"custom_key": "custom_value"})
        )
        db.commit()

        tenant_root = tmp_path / "tenant_pipeline"
        tenant_root.mkdir()
        config_dir = prepare_pipeline_config_dir(workspace.id, tenant_root, db)

        with open(config_dir / "pipeline.json", "r") as f:
            data = json.load(f)
        assert data["custom_key"] == "custom_value"


# =============================================================================
# Phase 4 — LLM Config serializer + override via prepare_pipeline_config_dir
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

    def test_prepare_writes_llm_config(self, db, workspace, tmp_path):
        """``prepare_pipeline_config_dir`` escreve llm_config.json quando há row."""
        _seed_llm_config(db, workspace.id, provider="openai", api_key="sk-openai-key")
        tenant_root = tmp_path / "tenant_llm"
        tenant_root.mkdir()
        config_dir = prepare_pipeline_config_dir(workspace.id, tenant_root, db)

        llm_path = config_dir / "llm_config.json"
        assert llm_path.exists()
        with open(llm_path) as f:
            data = json.load(f)
        assert data["provider"] == "openai"
        assert data["api_key"] == "sk-openai-key"
        assert data["model_name"] == "gpt-4o"

    def test_prepare_without_llm_config_omits_file(self, db, workspace, tmp_path):
        """``prepare_pipeline_config_dir`` não cria llm_config.json sem row no DB."""
        tenant_root = tmp_path / "tenant_no_llm"
        tenant_root.mkdir()
        config_dir = prepare_pipeline_config_dir(workspace.id, tenant_root, db)

        llm_path = config_dir / "llm_config.json"
        assert not llm_path.exists()


# =============================================================================
# Templates / schemas preservados
# =============================================================================


def test_prepare_preserves_templates_and_schemas(db, workspace, tmp_path):
    """Pastas estáticas (templates/, schemas/) continuam sendo copiadas em A7.5."""
    tenant_root = tmp_path / "tenant_tpl"
    tenant_root.mkdir()
    config_dir = prepare_pipeline_config_dir(workspace.id, tenant_root, db)

    global_config = Path(__file__).resolve().parent.parent.parent.parent / "config"
    if (global_config / "templates").exists():
        assert (config_dir / "templates").exists()
    if (global_config / "schemas").exists():
        assert (config_dir / "schemas").exists()


def _seed_two_itau_members(db, workspace_id: str) -> None:
    common_m = {"workspace_id": workspace_id, "short_name": "X"}
    david = FamilyMember(key="david", full_name="David", role="titular", order=0, **common_m)
    mariana = FamilyMember(key="mariana", full_name="Mariana", role="conjuge", order=1, **common_m)
    db.add_all([david, mariana])
    db.flush()
    common_a = {
        "workspace_id": workspace_id,
        "institution_code": "itau",
        "account_type": "extratoconta",
    }
    db.add_all(
        [
            BankAccount(member_id=david.id, account_number="12345-6", **common_a),
            BankAccount(member_id=mariana.id, account_number="78901-2", **common_a),
        ]
    )
    db.commit()
