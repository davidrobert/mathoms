"""A22.l4 — pin do model do parecer é snapshot literal, nunca alias móvel."""

from __future__ import annotations

import re

from pipeline.llm.models_catalog import PARECER_MODEL


def test_parecer_model_e_literal_pinado():
    assert not re.search(r"latest|newest|preview", PARECER_MODEL, re.IGNORECASE)
    assert re.fullmatch(r"[a-z]+/[a-z0-9.\-]+", PARECER_MODEL)
    assert any(ch.isdigit() for ch in PARECER_MODEL), "id sem componente de versão"
