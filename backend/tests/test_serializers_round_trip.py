"""Round-trip tests para os 6 serializers do `config_materializer` — F6.5E.1.

# Por que round-trip?

Os 6 serializers (DB → JSON pipeline) são **contratos silenciosos**: pipeline
lê do disco e nada quebra se o serializer perder um campo. Foi exatamente
como BUG-015 escapou (perdia `familia.sobrenome`).

# Padrão

Para cada serializer:
1. Criar estado canônico no DB (factory chamadas idempotentes)
2. Chamar `serialize_*(workspace_id, db)`
3. Assertir que **todos os campos** estão presentes e equivalentes
4. Quando aplicável, materializar para disco e ler de volta (round-trip total)

# Cobertura

- serialize_family_members  ← **inclui anti-regressão BUG-015 (6.5E.5)**
- serialize_categorization
- serialize_pipeline_config
- serialize_institution_config
- serialize_report_layout
- serialize_llm_config

# Convenção de fixtures

Reutilizo o pattern de `test_config_materializer.py` (sync session em SQLite
in-memory dedicado) porque os serializers são síncronos. NÃO toca a
fixture async global do conftest — isolation total.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.app.models  # noqa: F401 — ensure model registry
from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models import (
    BankAccount,
    Category,
    CategoryKeyword,
    FamilyMember,
    InstitutionConfig,
    LLMConfig,
    PipelineConfig,
    ReportLayout,
    User,
    Workspace,
)
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

_engine = create_engine("sqlite://", echo=False)
_Session = sessionmaker(bind=_engine)
_vault = VaultService()


@pytest.fixture(autouse=True)
def setup_sync_db():
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture
def db():
    s = _Session()
    yield s
    s.close()


@pytest.fixture
def workspace(db) -> Workspace:
    """Workspace canônico SEM family_surname — ajuste no test específico."""
    u = User(
        email="rt@test.com",
        hashed_password=hash_password("x"),
        full_name="Round Trip",
    )
    db.add(u)
    db.flush()
    ws = Workspace(name="RT WS", owner_id=u.id)
    db.add(ws)
    db.commit()
    return ws


# ─────────────────────────────────────────────────────────────────────
# 1. serialize_family_members — round-trip + BUG-015 anti-regressão
# ─────────────────────────────────────────────────────────────────────


class TestRoundTripFamilyMembers:
    """6.5E.1 + 6.5E.5 — preservação completa, incluindo `familia.sobrenome`."""

    def test_round_trip_all_fields_preserved(self, db, workspace):
        # Workspace COM sobrenome (caminho feliz)
        workspace.family_surname = "Silva Souza"
        cpf_plain = "910.428.398-01"  # noqa: PII-ok (gerado por tests/utils/cpf.py seed=42)
        cpf_enc = _vault.encrypt(cpf_plain)
        m = FamilyMember(
            workspace_id=workspace.id,
            key="david",
            full_name="David Silva Souza",
            short_name="David",
            cpf_encrypted=cpf_enc,
            birth_date=None,
            role="titular",
            order=0,
            extra={"profissao": "CTO", "telefone": "+55 11 99999-0000"},
        )
        db.add(m)
        db.flush()
        db.add(
            BankAccount(
                member_id=m.id,
                workspace_id=workspace.id,
                institution_code="itau",
                account_type="corrente",
                agency="0001",
                account_number="12345-6",
            )
        )
        db.commit()

        result = serialize_family_members(workspace.id, db)
        assert result is not None

        # Membro
        david = result["membros"]["david"]
        assert david["nome_completo"] == "David Silva Souza"
        assert david["nome_curto"] == "David"
        assert david["cpf"] == cpf_plain  # decifrado
        assert david["papel"] == "titular"
        # extra fields são merged in-line
        assert david["profissao"] == "CTO"
        assert david["telefone"] == "+55 11 99999-0000"

        # Conta
        assert result["banco_membro"]["itau"] == "david"
        # Titular
        assert result["titular"] == "david"
        # ★ BUG-015 — familia.sobrenome PRESENTE quando workspace.family_surname setado
        assert result["familia"] == {"sobrenome": "Silva Souza"}

    def test_bug015_anti_regression_no_surname_no_familia_key(self, db, workspace):
        """6.5E.5 — workspace SEM family_surname não deve gerar `familia` no JSON.

        Antes do fix de BUG-015, `familia.sobrenome` vinha do `config/family_members.json`
        global (do founder) e era OVERWRITE-ado pelo serializer com vazio → capa
        em branco. Agora, sem family_surname:
        - serializer NÃO inclui `familia` no dict (preserva o que estiver no
          arquivo global copiado)
        - quando workspace TEM members mas SEM surname, a chave `familia` NÃO
          aparece no resultado (caso contrário, vazaria `"Ferreira Campos"` do
          founder via fallback global).
        """
        # Workspace SEM family_surname (default)
        assert workspace.family_surname is None
        m = FamilyMember(
            workspace_id=workspace.id,
            key="anon",
            full_name="Anônimo Teste",
            short_name="Anon",
            role="titular",
            order=0,
        )
        db.add(m)
        db.commit()

        result = serialize_family_members(workspace.id, db)
        assert result is not None
        # Members presentes
        assert "anon" in result["membros"]
        # ★ Crítico: NÃO existe `familia` no dict — não vaza nome do global
        assert "familia" not in result, (
            "BUG-015 REGRESSION: serializer está emitindo `familia` mesmo sem "
            "workspace.family_surname. Isso causa overwrite com nome do founder "
            "e capa do relatório fica errada para usuários multi-tenant."
        )

    def test_bug015_anti_regression_no_members_no_surname_returns_none(self, db, workspace):
        """Workspace vazio (sem members nem surname) → None (não materializa)."""
        result = serialize_family_members(workspace.id, db)
        assert result is None

    def test_bug015_only_surname_without_members_still_serializes(self, db, workspace):
        """Workspace com APENAS surname (sem members) ainda serializa.

        Edge case importante: se o user só definiu o sobrenome via tab Members
        mas ainda não cadastrou ninguém, o serializer deve emitir `familia`
        para que a capa do relatório funcione.
        """
        workspace.family_surname = "Apenas Sobrenome"
        db.commit()

        result = serialize_family_members(workspace.id, db)
        assert result is not None
        assert result["familia"] == {"sobrenome": "Apenas Sobrenome"}
        assert result["membros"] == {}  # explicit empty

    def test_round_trip_through_disk_preserves_familia(self, db, workspace, tmp_path):
        """Round-trip serializer → disco → ler JSON → validar (post-A7.5: escrita manual)."""
        workspace.family_surname = "Round Trip Family"
        m = FamilyMember(
            workspace_id=workspace.id,
            key="t1",
            full_name="Titular 1",
            short_name="T1",
            role="titular",
            order=0,
        )
        db.add(m)
        db.commit()

        result = serialize_family_members(workspace.id, db)
        family_json = tmp_path / "family_members.json"
        family_json.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

        on_disk = json.loads(family_json.read_text(encoding="utf-8"))
        assert on_disk["familia"]["sobrenome"] == "Round Trip Family"
        assert "t1" in on_disk["membros"]


# ─────────────────────────────────────────────────────────────────────
# 2. serialize_categorization — round-trip
# ─────────────────────────────────────────────────────────────────────


class TestRoundTripCategorization:
    def test_expense_and_income_keywords_preserved(self, db, workspace):
        cat_exp = Category(
            workspace_id=workspace.id,
            code="alimentacao",
            name="Alimentação",
            category_type="expense",
            order=0,
        )
        cat_inc = Category(
            workspace_id=workspace.id,
            code="salario",
            name="Salário",
            category_type="income",
            order=0,
        )
        db.add_all([cat_exp, cat_inc])
        db.flush()
        db.add_all(
            [
                CategoryKeyword(category_id=cat_exp.id, keyword="mercado"),
                CategoryKeyword(category_id=cat_exp.id, keyword="ifood"),
                CategoryKeyword(category_id=cat_inc.id, keyword="folha"),
            ]
        )
        db.commit()

        result = serialize_categorization(workspace.id, db)
        assert result is not None
        assert set(result["expense_keywords"]["alimentacao"]) == {"mercado", "ifood"}
        assert result["income_keywords"]["salario"] == ["folha"]
        # Não vaza categoria de outro tipo
        assert "salario" not in result["expense_keywords"]
        assert "alimentacao" not in result["income_keywords"]

    def test_no_categories_returns_none(self, db, workspace):
        assert serialize_categorization(workspace.id, db) is None


# ─────────────────────────────────────────────────────────────────────
# 3-5. serialize_pipeline / institution / report_layout — blob round-trip
# ─────────────────────────────────────────────────────────────────────


class TestRoundTripBlobConfigs:
    """Pipeline / institutions / report_layout são blobs JSON puros — round-trip
    é preservação byte-perfect do `config_json`."""

    def test_pipeline_config_blob_preserved(self, db, workspace):
        nested = {
            "llm": {"max_tokens": 4096, "temperature": 0.0, "providers": ["anthropic"]},
            "file_limits": {"max_size_mb": 50, "max_pages": 200},
            "qa_thresholds": {"reconciliation_min": 0.95},
            "period_regex": {"YYYY-MM": r"^\d{4}-\d{2}$"},
        }
        db.add(PipelineConfig(workspace_id=workspace.id, config_json=nested))
        db.commit()

        out = serialize_pipeline_config(workspace.id, db)
        assert out == nested  # identidade total

    def test_institution_config_blob_preserved(self, db, workspace):
        blob = {"banco_canonical": {"itau": "Itaú"}, "fatura_patterns": {"itau": [r"^Fatura"]}}
        db.add(InstitutionConfig(workspace_id=workspace.id, config_json=blob))
        db.commit()
        assert serialize_institution_config(workspace.id, db) == blob

    def test_report_layout_blob_preserved(self, db, workspace):
        blob = {
            "secoes": [
                {"nome": "capa", "ordem": 1},
                {"nome": "kpis", "ordem": 2, "cards": ["receitas", "despesas"]},
            ]
        }
        db.add(ReportLayout(workspace_id=workspace.id, config_json=blob))
        db.commit()
        assert serialize_report_layout(workspace.id, db) == blob

    def test_blob_configs_return_none_when_absent(self, db, workspace):
        assert serialize_pipeline_config(workspace.id, db) is None
        assert serialize_institution_config(workspace.id, db) is None
        assert serialize_report_layout(workspace.id, db) is None

    def test_report_layout_serializer_round_trip_via_yaml(self, db, workspace, tmp_path):
        """Report layout: serializer + write yaml → ler → identidade (post-A7.5: escrita manual)."""
        blob = {"secoes": [{"nome": "capa", "ordem": 1}]}
        db.add(ReportLayout(workspace_id=workspace.id, config_json=blob))
        db.commit()

        out = serialize_report_layout(workspace.id, db)
        yaml_path = tmp_path / "report_layout.yaml"
        yaml_path.write_text(
            yaml.dump(out, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        on_disk = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert on_disk == blob


# ─────────────────────────────────────────────────────────────────────
# 6. serialize_llm_config — round-trip com decifração de api_key
# ─────────────────────────────────────────────────────────────────────


class TestRoundTripLLMConfig:
    def test_all_fields_preserved_with_decrypted_api_key(self, db, workspace):
        plain_key = "sk-ant-test-1234567890"
        enc_key = _vault.encrypt(plain_key)
        cfg = LLMConfig(
            workspace_id=workspace.id,
            provider="anthropic",
            api_key_encrypted=enc_key,
            model_name="claude-opus-4-6",
            max_tokens=8192,
            temperature=0.2,
        )
        db.add(cfg)
        db.commit()

        out = serialize_llm_config(workspace.id, db)
        assert out is not None
        assert out["provider"] == "anthropic"
        assert out["api_key"] == plain_key  # decifrada para o pipeline
        assert out["model_name"] == "claude-opus-4-6"
        assert out["max_tokens"] == 8192
        assert out["temperature"] == 0.2

    def test_no_llm_config_returns_none(self, db, workspace):
        assert serialize_llm_config(workspace.id, db) is None

    def test_round_trip_through_disk(self, db, workspace, tmp_path):
        """``prepare_pipeline_config_dir`` escreve llm_config.json via serializer (post-A7.5)."""
        cfg = LLMConfig(
            workspace_id=workspace.id,
            provider="anthropic",
            api_key_encrypted=_vault.encrypt("sk-test-key"),
            model_name="claude-haiku-4-5",
            max_tokens=2048,
            temperature=0.0,
        )
        db.add(cfg)
        db.commit()

        config_dir = prepare_pipeline_config_dir(workspace.id, tmp_path, db)
        llm_json = config_dir / "llm_config.json"
        assert llm_json.exists()
        on_disk = json.loads(llm_json.read_text(encoding="utf-8"))
        assert on_disk["api_key"] == "sk-test-key"
        assert on_disk["model_name"] == "claude-haiku-4-5"
