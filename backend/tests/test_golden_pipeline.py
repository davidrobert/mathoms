"""Golden file pipeline com PDFs sintéticos — F6.5E.2.

# Escopo desta suíte (entregue agora)

Cobre o **caminho crítico** que motivou a sub-fase 6.5E:
1. Workspace fixture completa (User + Workspace + FamilyMember + family_surname)
2. `materialize_config` produz `family_members.json` no tenant_root corretamente
3. PDFs sintéticos do gerador (6.5F.12) são abertos por `pdfplumber` (parseáveis)
4. Substituição de tokens estilo `{{COVER_FAMILIA}}` no template HTML do E6 funciona
   com o `family_surname` materializado (regressão BUG-015 end-to-end)

# Escopo deferido (full pipeline E2E)

Rodar E0→E1→E1.5→E2→E3→E4→E5→E6 com PDFs sintéticos requer:
- **Roteamento + execução dos parsers:** `tests/test_e2_synthetic_pdf_parsers.py`
  (filename canônico por banco → `route_to_parser` → parse sem exceção). Extração
  detalhada de transações ainda depende de alinhar layout do gerador às regex de
  cada `scripts/e2/banks/<banco>.py` (evolução contínua).
- Mockar/skipar stages LLM (E1, E1.5, E2-llm) com fixtures pré-computadas
  (parte de 6.5F.4 — `--real-pipeline` flag opt-in).
- Workaround do uso pesado de `globals` em `e6_render.py` (nas funções
  `_load_config_files`, `FAMILY_SOBRENOME`, etc.) — refatorar para receber
  ctx puro é separado e maior.

Esses 3 itens viram backlog explícito (ver final do arquivo) e a sub-fase
6.5C.0 (Golden Path E2E via Playwright + backend real) cobre o end-to-end
de produto pelo lado do usuário.

# Como rodar

    pytest backend/tests/test_golden_pipeline.py -v
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models import (
    BankAccount,
    Category,
    CategoryKeyword,
    FamilyMember,
    User,
    Workspace,
)
from backend.app.services.config_materializer import materialize_config

import backend.app.models  # noqa: F401

# ─── PDFs sintéticos ───
# Import via path absoluto: pytest cria conflito de namespace entre
# `backend/tests/` e o `tests/` da raiz (ambos têm __init__.py). Carregamento
# manual evita o shadowing.
import importlib.util as _ilu
import sys as _sys

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PDF_GEN_PATH = _PROJECT_ROOT / "tests" / "fixtures" / "pdf_generator.py"
_spec = _ilu.spec_from_file_location("_synthetic_pdf_generator", _PDF_GEN_PATH)
_pdf_gen = _ilu.module_from_spec(_spec)
_sys.modules["_synthetic_pdf_generator"] = _pdf_gen
_spec.loader.exec_module(_pdf_gen)
generate_statement = _pdf_gen.generate_statement


_engine = create_engine("sqlite://", echo=False)
_Session = sessionmaker(bind=_engine)


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


def _seed_golden_user_and_workspace(db) -> Workspace:
    u = User(
        email="golden@test.com",
        hashed_password=hash_password("x"),
        full_name="Golden User",
    )
    db.add(u)
    db.flush()

    ws = Workspace(
        name="Família Silva Souza",
        family_surname="Silva Souza",
        owner_id=u.id,
    )
    db.add(ws)
    db.flush()
    return ws


def _seed_golden_titular_with_account(db, ws: Workspace) -> FamilyMember:
    titular = FamilyMember(
        workspace_id=ws.id,
        key="founder",
        full_name="Founder Silva Souza",
        short_name="Founder",
        role="titular",
        order=0,
    )
    db.add(titular)
    db.flush()
    db.add(
        BankAccount(
            member_id=titular.id,
            institution_code="c6bank",
            account_type="corrente",
            agency="0001",
            account_number="12345-6",
        )
    )
    return titular


def _seed_golden_categories_with_keywords(db, ws: Workspace) -> None:
    cat_ali = Category(
        workspace_id=ws.id,
        code="alimentacao",
        name="Alimentação",
        category_type="expense",
        order=0,
    )
    cat_sal = Category(
        workspace_id=ws.id,
        code="salario",
        name="Salário",
        category_type="income",
        order=0,
    )
    db.add_all([cat_ali, cat_sal])
    db.flush()
    db.add_all(
        [
            CategoryKeyword(category_id=cat_ali.id, keyword="mercado"),
            CategoryKeyword(category_id=cat_ali.id, keyword="ifood"),
            CategoryKeyword(category_id=cat_sal.id, keyword="folha"),
        ]
    )


@pytest.fixture
def golden_workspace(db) -> Workspace:
    """Workspace canônico para o golden test:
    - 1 user
    - 1 workspace com family_surname='Silva Souza' (BUG-015 anti-regression)
    - 1 titular com 1 conta C6Bank
    - 1 categoria de despesa + 1 de receita com keywords
    """
    ws = _seed_golden_user_and_workspace(db)
    _seed_golden_titular_with_account(db, ws)
    _seed_golden_categories_with_keywords(db, ws)
    db.commit()
    return ws


# ─────────────────────────────────────────────────────────────────────
# Caminho crítico 1 — materialize gera family_members.json correto
# ─────────────────────────────────────────────────────────────────────


class TestMaterializedConfigEndToEnd:
    """6.5E.2 cobertura mínima: workspace DB → materialize → assert no disco."""

    def test_family_members_json_has_familia_sobrenome(self, db, golden_workspace, tmp_path):
        config_dir = materialize_config(golden_workspace.id, tmp_path, db)
        family_json = config_dir / "family_members.json"
        assert family_json.exists()

        data = json.loads(family_json.read_text(encoding="utf-8"))
        # ★ BUG-015 end-to-end: chave familia.sobrenome propaga até o JSON consumido por E6
        assert data["familia"]["sobrenome"] == "Silva Souza"
        assert "founder" in data["membros"]
        assert data["banco_membro"]["c6bank"] == "founder"
        assert data["titular"] == "founder"

    def test_categorization_json_separa_expense_income(self, db, golden_workspace, tmp_path):
        config_dir = materialize_config(golden_workspace.id, tmp_path, db)
        cat_json = config_dir / "categorization.json"
        assert cat_json.exists()
        data = json.loads(cat_json.read_text(encoding="utf-8"))
        assert "mercado" in data["expense_keywords"]["alimentacao"]
        assert "folha" in data["income_keywords"]["salario"]
        # Cross-contaminação não-permitida
        assert "alimentacao" not in data["income_keywords"]
        assert "salario" not in data["expense_keywords"]

    def test_global_template_files_preserved(self, db, golden_workspace, tmp_path):
        """`_copy_global` copia o template HTML do E6 — sem ele, nada renderiza."""
        config_dir = materialize_config(golden_workspace.id, tmp_path, db)
        template_html = config_dir / "templates" / "report_template.html"
        assert template_html.exists(), (
            "Template HTML do E6 não foi copiado pelo materializer. "
            "Sem isso, nenhum relatório renderiza."
        )


# ─────────────────────────────────────────────────────────────────────
# Caminho crítico 2 — PDFs sintéticos do 6.5F.12 são parseáveis
# ─────────────────────────────────────────────────────────────────────


class TestSyntheticPDFsAreParseable:
    """Smoke: pdfplumber consegue abrir e extrair texto dos PDFs gerados.

    Não testa alinhamento fino parser↔layout (isso é `tests/test_e2_synthetic_pdf_parsers.py`
    + evolução do gerador). Aqui só prova PDF válido com texto extraível por banco.
    """

    @pytest.mark.parametrize(
        "bank,kind",
        [
            ("c6bank", "extrato"),
            ("itau", "extrato"),
            ("santander", "extrato"),
            ("bradesco", "fatura"),
            ("btgpactual", "extrato"),
            ("rico", "extrato"),
            ("picpay", "fatura"),
            ("bankofamerica", "extrato"),
            ("wise", "extrato"),
            ("binance", "extrato"),
            ("quintoandar", "extrato"),
            ("receitafederal", "extrato"),
            ("einstein", "extrato"),
            ("caixa", "extrato"),
        ],
    )
    def test_pdf_for_bank_is_parseable(self, bank, kind, tmp_path):
        try:
            import pdfplumber
        except ImportError:
            pytest.skip("pdfplumber não instalado (já está em backend/requirements.txt)")

        pdf_bytes = generate_statement(
            bank,
            kind,
            transactions=[
                {"date": "2026-04-05", "description": "Mercado Sintetico", "amount": -250.50},
                {"date": "2026-04-01", "description": "Pagto Folha", "amount": 12500.00},
            ],
            account_holder="Founder Silva Souza",
        )
        path = tmp_path / f"{bank}_{kind}.pdf"
        path.write_bytes(pdf_bytes)

        with pdfplumber.open(path) as pdf:
            assert len(pdf.pages) >= 1
            text = pdf.pages[0].extract_text() or ""
            # Smoke assertions: header do banco + transações aparecem.
            # Case-insensitive porque santander faz `.upper()` nas descrições
            # (paridade com output real do banco, consumido por
            # `scripts/e2/banks/santander.py`).
            text_lower = text.lower()
            assert "periodo" in text_lower or "per" in text_lower
            assert "mercado sintetico" in text_lower
            assert "pagto folha" in text_lower


# ─────────────────────────────────────────────────────────────────────
# Caminho crítico 3 — Token replacement do template HTML usa o sobrenome
# ─────────────────────────────────────────────────────────────────────


class TestE6TemplateUsesFamilySurname:
    """Verifica que `{{COVER_FAMILIA}}` no template é substituído pelo
    `family_surname` quando o JSON materializado é consumido — simula a
    parte do E6 sem precisar rodar o pipeline inteiro.
    """

    def test_template_has_cover_familia_token(self):
        """Sanity: o template do E6 ainda usa `{{COVER_FAMILIA}}`."""
        template_path = (
            Path(__file__).resolve().parents[2]
            / "config"
            / "templates"
            / "report_template.html"
        )
        if not template_path.exists():
            pytest.skip(f"Template não encontrado em {template_path}")
        content = template_path.read_text(encoding="utf-8")
        assert "{{COVER_FAMILIA}}" in content, (
            "Token {{COVER_FAMILIA}} sumiu do template. "
            "Se foi renomeado intencionalmente, atualize este test e o "
            "scripts/e6_render.py em sincronia."
        )

    def test_token_replacement_with_materialized_surname(self, db, golden_workspace, tmp_path):
        """Pega o template, materializa o config, faz substituição manual,
        valida que o cover renderizado contém 'Silva Souza'.
        """
        # 1. Materializa config
        config_dir = materialize_config(golden_workspace.id, tmp_path, db)
        family_data = json.loads((config_dir / "family_members.json").read_text("utf-8"))
        surname = family_data["familia"]["sobrenome"]

        # 2. Lê template (do projeto global — não copiado para tenant ainda
        # se materialize não copiou, fallback para template global).
        template_path = config_dir / "templates" / "report_template.html"
        if not template_path.exists():
            template_path = (
                Path(__file__).resolve().parents[2]
                / "config"
                / "templates"
                / "report_template.html"
            )
        if not template_path.exists():
            pytest.skip(f"Template global não encontrado em {template_path}")
        html = template_path.read_text(encoding="utf-8")

        # 3. Substituição mínima (subset do que e6_render faz)
        rendered = html.replace("{{COVER_FAMILIA}}", surname)

        # 4. Asserts: surname aparece, token não vazou
        assert surname in rendered, "Surname não foi inserido no HTML."
        assert "{{COVER_FAMILIA}}" not in rendered, "Token {{COVER_FAMILIA}} ficou sem substituição."
        # E o cover tem alguma estrutura mínima (não é string vazia)
        assert "<html" in rendered.lower() or "<!DOCTYPE" in rendered.lower()


# ─────────────────────────────────────────────────────────────────────
# Backlog explícito — 6.5E.2 escopo deferido
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.skip(
    reason=(
        "Full pipeline E2E (E0→E6) com PDFs sintéticos — escopo deferido. "
        "Requer: (a) gerador refinado por banco para casar regex/coordenadas "
        "dos parsers em scripts/e2/banks/, (b) mocks pré-computados de stages "
        "LLM (parte de 6.5F.4), (c) refator de e6_render.py para evitar globals. "
        "6.5C.0 (Golden Path E2E via Playwright) cobre o end-to-end pelo lado do "
        "usuário enquanto este permanece deferido."
    )
)
def test_full_pipeline_with_synthetic_pdfs():
    """Quando implementado:
    1. Cria workspace fixture (golden_workspace)
    2. Gera 2 PDFs sintéticos (extrato + fatura) compatíveis com 1 parser
    3. Roda pipeline.run_pipeline(ctx) com skip_llm=True
    4. Lê output/relatorio_*.html
    5. Assert: contém "Silva Souza" em <h1>, KPIs renderizados, score > 0
    """
    pass
