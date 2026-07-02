"""Goldens de ``informe_aluguel`` + família 5 membros (A20.l15 · ADR-259).

5 fixtures cobrem os casos BR do critério de aceite (PF→PF, vacância
multi-imóvel, PF→PJ IR retido, comunhão ADR-246, dedução IPTU/condomínio)
— todas PII-free por construção (``cpf_present`` flag, nunca valor).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from pipeline.llm.schemas.e1_members import MembersExtractOutput
from pipeline.llm.schemas.informe_aluguel import InformeAluguelExtract

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "llm_golden"

_ALUGUEL_FIXTURES = (
    "informe_aluguel_pf_pf.json",
    "informe_aluguel_multi_imovel_vacancia.json",
    "informe_aluguel_pf_pj_ir_retido.json",
    "informe_aluguel_comunhao.json",
    "informe_aluguel_pf_deducao_iptu_condominio.json",
)


@pytest.mark.parametrize("fixture_name", _ALUGUEL_FIXTURES)
def test_aluguel_golden_valida_no_schema(fixture_name: str) -> None:
    data = json.loads((GOLDEN_DIR / fixture_name).read_text())
    ext = InformeAluguelExtract(**data)
    assert ext.confidence >= 0.7
    assert ext.locador_cpf_present is True
    assert ext.imoveis


@pytest.mark.parametrize("fixture_name", _ALUGUEL_FIXTURES)
def test_aluguel_golden_livre_de_cpf(fixture_name: str) -> None:
    """Gate LGPD: nenhuma fixture carrega CPF (11 dígitos) em lugar nenhum."""
    from pipeline.domain.services.informe_member_matcher import extract_document_cpfs

    raw = (GOLDEN_DIR / fixture_name).read_text()
    assert extract_document_cpfs(raw) == set()
    assert "locador_cpf_present" in raw


def test_aluguel_golden_pf_pj_tem_ir_retido() -> None:
    data = json.loads((GOLDEN_DIR / "informe_aluguel_pf_pj_ir_retido.json").read_text())
    ext = InformeAluguelExtract(**data)
    imovel = ext.imoveis[0]
    assert imovel.locatario_cnpj is not None
    assert imovel.ir_retido_anual > Decimal("0")


def test_aluguel_golden_vacancia_meses_parciais() -> None:
    data = json.loads(
        (GOLDEN_DIR / "informe_aluguel_multi_imovel_vacancia.json").read_text()
    )
    ext = InformeAluguelExtract(**data)
    meses = sorted(i.meses_locado_no_periodo for i in ext.imoveis)
    assert meses == [6, 12]


def test_e1_familia_5_membros_golden() -> None:
    data = json.loads((GOLDEN_DIR / "e1_members_familia_5.json").read_text())
    out = MembersExtractOutput(**data)
    assert len(out.members) == 5
    roles = {m.role for m in out.members}
    assert {"titular", "conjuge", "filho", "dependente"} <= roles
    # Dependente menor sem CPF no documento — flag False, nunca valor.
    gustavo = next(m for m in out.members if m.key == "gustavo")
    assert gustavo.cpf_present is False
    assert sum(1 for m in out.members if m.cpf_present) == 4
