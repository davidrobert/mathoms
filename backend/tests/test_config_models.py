"""Tests for Phase 3A: config models (DB) and Pydantic schemas (validation)."""

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.category import Category, CategoryKeyword
from backend.app.models.config_blob import InstitutionConfig, PipelineConfig, ReportLayout
from backend.app.models.family_member import BankAccount, FamilyMember
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.config import (
    BankAccountSchema,
    CategoryCreateRequest,
    CategorySchema,
    ConfigImportRequest,
    FamilyMemberCreateRequest,
    FamilyMemberSchema,
    InstitutionConfigSchema,
    PipelineConfigSchema,
    ReportLayoutSchema,
)


@pytest_asyncio.fixture
async def workspace(db: AsyncSession) -> Workspace:
    """Create a user + workspace for config tests."""
    from backend.app.core.security import hash_password

    user = User(
        email="config@test.com", hashed_password=hash_password("test123"), full_name="Config Tester"
    )
    db.add(user)
    await db.flush()
    ws = Workspace(name="Test WS", owner_id=user.id)
    db.add(ws)
    await db.commit()
    return ws


# =============================================================================
# FamilyMember + BankAccount — DB model tests
# =============================================================================


class TestFamilyMemberModel:
    @pytest.mark.asyncio
    async def test_create_member(self, db: AsyncSession, workspace: Workspace):
        member = FamilyMember(
            workspace_id=workspace.id,
            key="david",
            full_name="David Robert Camargo",
            short_name="David",
            cpf_encrypted="encrypted_value_here",
            birth_date=date(1981, 9, 5),
            role="titular",
            order=0,
            extra={"profissao": "CTO"},
        )
        db.add(member)
        await db.commit()

        result = await db.execute(select(FamilyMember).where(FamilyMember.key == "david"))
        saved = result.scalar_one()
        assert saved.full_name == "David Robert Camargo"
        assert saved.role == "titular"
        assert saved.extra == {"profissao": "CTO"}
        assert saved.birth_date == date(1981, 9, 5)

    @pytest.mark.asyncio
    async def test_member_with_accounts(self, db: AsyncSession, workspace: Workspace):
        member = FamilyMember(
            workspace_id=workspace.id,
            key="mariana",
            full_name="Mariana Ferreira Campos",
            short_name="Mariana",
            role="conjuge",
        )
        db.add(member)
        await db.flush()

        acc1 = BankAccount(
            member_id=member.id,
            workspace_id=workspace.id,
            institution_code="bradesco",
            account_type="extratoconta",
        )
        acc2 = BankAccount(
            member_id=member.id,
            workspace_id=workspace.id,
            institution_code="btgpactual",
            account_type="investimentosposicao",
            agency="001",
            account_number="12345-6",
        )
        db.add_all([acc1, acc2])
        await db.commit()

        result = await db.execute(
            select(FamilyMember)
            .where(FamilyMember.id == member.id)
            .options(selectinload(FamilyMember.accounts))
        )
        loaded = result.scalar_one()
        assert len(loaded.accounts) == 2
        codes = {a.institution_code for a in loaded.accounts}
        assert codes == {"bradesco", "btgpactual"}

    @pytest.mark.asyncio
    async def test_cascade_delete(self, db: AsyncSession, workspace: Workspace):
        member = FamilyMember(
            workspace_id=workspace.id,
            key="theo",
            full_name="Theo FC",
            short_name="Theo",
            role="filho",
        )
        db.add(member)
        await db.flush()
        acc = BankAccount(
            member_id=member.id,
            workspace_id=workspace.id,
            institution_code="c6bank",
            account_type="extratoconta",
        )
        db.add(acc)
        await db.commit()

        await db.delete(member)
        await db.commit()

        result = await db.execute(select(BankAccount).where(BankAccount.member_id == member.id))
        assert result.scalars().all() == []


# =============================================================================
# Category + CategoryKeyword — DB model tests
# =============================================================================


class TestCategoryModel:
    @pytest.mark.asyncio
    async def test_create_category_with_keywords(self, db: AsyncSession, workspace: Workspace):
        cat = Category(
            workspace_id=workspace.id,
            code="moradia",
            name="Moradia",
            category_type="expense",
            monthly_cap=5000.0,
            order=0,
        )
        db.add(cat)
        await db.flush()

        keywords = [
            CategoryKeyword(category_id=cat.id, keyword=kw)
            for kw in ["ELETROPAULO", "ENEL", "CONDOMINIO"]
        ]
        db.add_all(keywords)
        await db.commit()

        result = await db.execute(
            select(Category).where(Category.id == cat.id).options(selectinload(Category.keywords))
        )
        loaded = result.scalar_one()
        assert loaded.code == "moradia"
        assert loaded.monthly_cap == 5000.0
        assert len(loaded.keywords) == 3
        assert {kw.keyword for kw in loaded.keywords} == {"ELETROPAULO", "ENEL", "CONDOMINIO"}

    @pytest.mark.asyncio
    async def test_category_types(self, db: AsyncSession, workspace: Workspace):
        for ct in ("expense", "income"):
            cat = Category(
                workspace_id=workspace.id, code=f"test_{ct}", name=f"Test {ct}", category_type=ct
            )
            db.add(cat)
        await db.commit()

        result = await db.execute(select(Category).where(Category.workspace_id == workspace.id))
        cats = result.scalars().all()
        assert len(cats) == 2

    @pytest.mark.asyncio
    async def test_keyword_cascade_delete(self, db: AsyncSession, workspace: Workspace):
        cat = Category(workspace_id=workspace.id, code="temp", name="Temp", category_type="expense")
        db.add(cat)
        await db.flush()
        kw = CategoryKeyword(category_id=cat.id, keyword="TEST")
        db.add(kw)
        await db.commit()

        await db.delete(cat)
        await db.commit()

        result = await db.execute(
            select(CategoryKeyword).where(CategoryKeyword.category_id == cat.id)
        )
        assert result.scalars().all() == []


# =============================================================================
# JSON blob configs — DB model tests
# =============================================================================


class TestConfigBlobModels:
    @pytest.mark.asyncio
    async def test_pipeline_config(self, db: AsyncSession, workspace: Workspace):
        cfg = PipelineConfig(
            workspace_id=workspace.id,
            config_json={
                "llm": {"model": "gpt-4o", "max_tokens": 1000},
                "qa_thresholds": {"score_diff_max": 1.0},
            },
        )
        db.add(cfg)
        await db.commit()

        result = await db.execute(
            select(PipelineConfig).where(PipelineConfig.workspace_id == workspace.id)
        )
        loaded = result.scalar_one()
        assert loaded.config_json["llm"]["model"] == "gpt-4o"
        assert loaded.config_json["qa_thresholds"]["score_diff_max"] == 1.0

    @pytest.mark.asyncio
    async def test_institution_config(self, db: AsyncSession, workspace: Workspace):
        cfg = InstitutionConfig(
            workspace_id=workspace.id,
            config_json={"banco_canonical": {"itau": "Itaú"}, "institution_patterns": []},
        )
        db.add(cfg)
        await db.commit()

        result = await db.execute(
            select(InstitutionConfig).where(InstitutionConfig.workspace_id == workspace.id)
        )
        loaded = result.scalar_one()
        assert loaded.config_json["banco_canonical"]["itau"] == "Itaú"

    @pytest.mark.asyncio
    async def test_report_layout(self, db: AsyncSession, workspace: Workspace):
        cfg = ReportLayout(
            workspace_id=workspace.id,
            config_json={"version": "1.1", "estrategico": {"sections": []}},
        )
        db.add(cfg)
        await db.commit()

        result = await db.execute(
            select(ReportLayout).where(ReportLayout.workspace_id == workspace.id)
        )
        loaded = result.scalar_one()
        assert loaded.config_json["version"] == "1.1"

    @pytest.mark.asyncio
    async def test_one_per_workspace(self, db: AsyncSession, workspace: Workspace):
        """Each blob config is unique per workspace (enforced by unique constraint)."""
        cfg1 = PipelineConfig(workspace_id=workspace.id, config_json={"v": 1})
        db.add(cfg1)
        await db.commit()

        from sqlalchemy.exc import IntegrityError

        cfg2 = PipelineConfig(workspace_id=workspace.id, config_json={"v": 2})
        db.add(cfg2)
        with pytest.raises(IntegrityError):
            await db.commit()


# =============================================================================
# Pydantic schema validation tests
# =============================================================================


class TestFamilyMemberSchema:
    def test_valid_member(self):
        schema = FamilyMemberCreateRequest(
            key="david",
            full_name="David RC",
            short_name="David",
            role="titular",
            cpf="910.428.398-01",  # noqa: PII-ok (gerado por tests/utils/cpf.py seed=42)
        )
        assert schema.key == "david"
        assert schema.cpf == "910.428.398-01"  # noqa: PII-ok (gerado por tests/utils/cpf.py seed=42)

    def test_cpf_wrong_digits(self):
        with pytest.raises(ValueError, match="11 dígitos"):
            FamilyMemberCreateRequest(
                key="test", full_name="Test", short_name="T", role="titular", cpf="123.456"
            )

    def test_cpf_none_allowed(self):
        schema = FamilyMemberCreateRequest(
            key="theo", full_name="Theo", short_name="Theo", role="filho"
        )
        assert schema.cpf is None

    def test_invalid_role(self):
        with pytest.raises(ValueError):
            FamilyMemberCreateRequest(key="x", full_name="X", short_name="X", role="invalid_role")

    def test_empty_key_rejected(self):
        with pytest.raises(ValueError):
            FamilyMemberCreateRequest(key="", full_name="X", short_name="X", role="titular")

    def test_from_attributes(self):
        schema = FamilyMemberSchema(
            id="abc",
            key="david",
            full_name="David",
            short_name="David",
            role="titular",
            order=0,
            accounts=[],
        )
        assert schema.id == "abc"


class TestBankAccountSchema:
    def test_valid_account(self):
        acc = BankAccountSchema(
            institution_code="itau",
            account_type="extratoconta",
            agency="001",
            account_number="12345",
        )
        assert acc.institution_code == "itau"

    def test_empty_institution_rejected(self):
        with pytest.raises(ValueError):
            BankAccountSchema(institution_code="", account_type="extratoconta")


class TestCategorySchema:
    def test_valid_expense(self):
        schema = CategoryCreateRequest(
            code="moradia", name="Moradia", category_type="expense", keywords=["ENEL", "SABESP"]
        )
        assert schema.category_type == "expense"
        assert len(schema.keywords) == 2

    def test_valid_income(self):
        schema = CategoryCreateRequest(code="receita_pj", name="Receita PJ", category_type="income")
        assert schema.category_type == "income"

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            CategoryCreateRequest(code="x", name="X", category_type="other")

    def test_negative_cap_rejected(self):
        with pytest.raises(ValueError):
            CategoryCreateRequest(code="x", name="X", category_type="expense", monthly_cap=-100)


class TestPipelineConfigSchema:
    def test_valid_full(self):
        schema = PipelineConfigSchema(
            llm={"model": "gpt-4o", "max_tokens": 1000, "confidence_threshold": 0.8},
            qa_thresholds={"score_diff_max": 1.0},
        )
        assert schema.llm.model == "gpt-4o"
        assert schema.qa_thresholds.score_diff_max == 1.0

    def test_partial_valid(self):
        schema = PipelineConfigSchema(
            llm={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "confidence_threshold": 0.7,
            }
        )
        assert schema.qa_thresholds is None

    def test_llm_max_tokens_bounds(self):
        with pytest.raises(ValueError):
            PipelineConfigSchema(llm={"model": "x", "max_tokens": 0, "confidence_threshold": 0.5})

    def test_confidence_threshold_bounds(self):
        with pytest.raises(ValueError):
            PipelineConfigSchema(llm={"model": "x", "max_tokens": 100, "confidence_threshold": 1.5})


class TestInstitutionConfigSchema:
    def test_valid(self):
        schema = InstitutionConfigSchema(config_json={"banco_canonical": {"itau": "Itaú"}})
        assert "banco_canonical" in schema.config_json


class TestReportLayoutSchema:
    def test_valid(self):
        schema = ReportLayoutSchema(config_json={"version": "1.1", "estrategico": {"sections": []}})
        assert schema.config_json["version"] == "1.1"


class TestConfigImportRequest:
    def test_partial_import(self):
        req = ConfigImportRequest(family_members={"membros": {"david": {"nome_completo": "David"}}})
        assert req.family_members is not None
        assert req.categorization is None
        assert req.pipeline is None

    def test_full_import(self):
        req = ConfigImportRequest(
            family_members={"membros": {}},
            categorization={"expense_keywords": {}},
            pipeline={"llm": {}},
            institutions={"banco_canonical": {}},
            report_layout={"version": "1.1"},
        )
        assert all(
            [
                req.family_members,
                req.categorization,
                req.pipeline,
                req.institutions,
                req.report_layout,
            ]
        )
