#!/usr/bin/env python3
"""Garante que prompts LLM injetam JSON/texto com `{`/`}` via str.format(**kwargs) com segurança.

O *format string* é o template; os valores são inseridos literalmente — não há reinterpretação
de chaves dentro do valor (comportamento Python 3). Duplicar `{{`/`}}` no valor corromperia o
conteúdo enviado ao modelo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_e1_template_inserts_nested_json_verbatim():
    from pipeline.llm.prompts.e1_members import USER_PROMPT_TEMPLATE

    raw = '{"membro": {"nome": "a"}, "lista": [1, 2]}'
    filled = USER_PROMPT_TEMPLATE.format(documents_text=raw)
    assert raw in filled
    assert "{{" not in filled


def test_e15_template_inserts_nested_json_verbatim():
    from pipeline.llm.prompts.e15_baseline import USER_PROMPT_TEMPLATE

    raw = '{"bens": [{"codigo": "01", "valor": 1.5}]}'
    filled = USER_PROMPT_TEMPLATE.format(documents_text=raw)
    assert raw in filled


def test_e7_template_inserts_three_json_blobs_verbatim():
    from pipeline.llm.prompts.e7_review import USER_PROMPT_TEMPLATE

    e5 = '{"patrimonio": {"total": {"a": 1}}}'
    cv = '{"checks": [{"detalhe": {"ok": true}}]}'
    fam = '{"membros": {"x": {"papel": "titular"}}}'
    filled = USER_PROMPT_TEMPLATE.format(
        e5_analysis_json=e5,
        e7_crossval_json=cv,
        family_config=fam,
    )
    assert e5 in filled
    assert cv in filled
    assert fam in filled


def test_e2_llm_template_inserts_document_text_verbatim():
    from pipeline.llm.prompts.e2_llm import USER_PROMPT_TEMPLATE

    blob = 'Saldo: 1\n{"linha": {"nested": true}}\n---'
    filled = USER_PROMPT_TEMPLATE.format(
        filename="x.pdf",
        doc_type="unknown",
        institution="unknown",
        document_text=blob,
    )
    assert blob in filled
    assert "{{" not in filled
