"""Injection do catálogo de instituições nos user prompts LLM (A33.l8 · ADR-137).

Cobre o critério de aceite da lane: adicionar instituição no catálogo (DB)
reflete no prompt gerado sem editar código; sem provider (CLI isolado) o
bloco degrada para fallback documentado; nenhuma lista hardcoded sobrevive
nos módulos de prompt.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.llm.institution_catalog import (
    CATALOG_UNAVAILABLE_BLOCK,
    INSURANCE_CATEGORY,
    InstitutionEntry,
    render_institution_catalog,
)


class FakeCatalogProvider:
    def __init__(self, entries: list[InstitutionEntry]):
        self._entries = entries

    def list_institutions(self) -> list[InstitutionEntry]:
        return list(self._entries)


def _entries() -> list[InstitutionEntry]:
    return [
        InstitutionEntry(code="bancoalfa", name="Banco Alfa", category="bank"),
        InstitutionEntry(code="corretorabeta", name="Corretora Beta", category="broker"),
        InstitutionEntry(
            code="seguradoragama", name="Seguradora Gama", category=INSURANCE_CATEGORY
        ),
    ]


def test_render_lista_code_e_nome_ordenado_por_code():
    block = render_institution_catalog(FakeCatalogProvider(_entries()))
    assert block.splitlines() == [
        "- bancoalfa (Banco Alfa)",
        "- corretorabeta (Corretora Beta)",
        "- seguradoragama (Seguradora Gama)",
    ]


def test_exclude_insurance_para_prompts_bancarios():
    block = render_institution_catalog(
        FakeCatalogProvider(_entries()), exclude_categories=(INSURANCE_CATEGORY,)
    )
    assert "seguradoragama" not in block
    assert "bancoalfa" in block and "corretorabeta" in block


def test_include_somente_insurance_para_apolice():
    block = render_institution_catalog(
        FakeCatalogProvider(_entries()), include_categories=(INSURANCE_CATEGORY,)
    )
    assert block == "- seguradoragama (Seguradora Gama)"


def test_sem_provider_degrada_para_fallback_documentado():
    assert render_institution_catalog(None) == CATALOG_UNAVAILABLE_BLOCK


def test_catalogo_vazio_degrada_para_fallback_documentado():
    assert render_institution_catalog(FakeCatalogProvider([])) == CATALOG_UNAVAILABLE_BLOCK
    filtered = render_institution_catalog(
        FakeCatalogProvider(_entries()), include_categories=("categoria_inexistente",)
    )
    assert filtered == CATALOG_UNAVAILABLE_BLOCK


def test_instituicao_nova_no_catalogo_reflete_no_prompt_sem_editar_codigo():
    """Critério de aceite A33.l8 #2 — catálogo (DB) é a única fonte da lista."""
    from pipeline.llm.prompts.e2_llm import USER_PROMPT_TEMPLATE

    entries = _entries()
    entries.append(InstitutionEntry(code="bancodelta", name="Banco Delta", category="bank"))
    block = render_institution_catalog(
        FakeCatalogProvider(entries), exclude_categories=(INSURANCE_CATEGORY,)
    )
    prompt = USER_PROMPT_TEMPLATE.format(
        filename="doc.pdf",
        doc_type="unknown",
        institution="unknown",
        institution_catalog=block,
        document_text="conteudo",
    )
    assert "- bancodelta (Banco Delta)" in prompt


def test_prompt_apolice_recebe_catalogo_de_seguradoras():
    from pipeline.llm.prompts.apolice import USER_PROMPT_TEMPLATE

    block = render_institution_catalog(
        FakeCatalogProvider(_entries()), include_categories=(INSURANCE_CATEGORY,)
    )
    prompt = USER_PROMPT_TEMPLATE.format(
        filename="apolice.pdf", document_text="conteudo", seguradoras_catalog=block
    )
    assert "- seguradoragama (Seguradora Gama)" in prompt


def test_prompts_sem_lista_hardcoded_de_instituicoes():
    """Critério de aceite A33.l8 #1 — zero lista hardcoded nos 3 prompts;
    sobra só o placeholder de injection (regressão contra drift do catálogo).
    """
    prompts_dir = Path(__file__).resolve().parents[3] / "pipeline" / "llm" / "prompts"
    hardcoded = re.compile(
        r"\b(itau|santander|c6bank|btgpactual|picpay|bankofamerica|quintoandar"
        r"|binance|nubank|tokiomarine|zurich)\b",
        re.IGNORECASE,
    )
    for module in ("e1_members.py", "e2_llm.py", "apolice.py"):
        content = (prompts_dir / module).read_text(encoding="utf-8")
        matches = hardcoded.findall(content)
        assert not matches, f"{module}: lista hardcoded reapareceu: {sorted(set(matches))}"
        assert (
            "catálogo" in content or "catalogo" in content
        ), f"{module}: placeholder de injection do catálogo ausente"
