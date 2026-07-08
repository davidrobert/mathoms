"""Loader dos códigos RFB anuais do e16 (A33.l8) — falha-fast com valor ofensor."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.llm.rfb_codes import (
    available_rfb_years,
    load_rfb_codes,
    render_rfb_codes_block,
    resolve_rfb_codes,
    rfb_codes_path,
)

_MINIMAL_YAML = """\
version: 1
ano_base: {ano}
fonte: "teste"
rendimentos_isentos:
  "09": "Lucros e dividendos recebidos"
tributacao_exclusiva:
  "06": "Ganho de capital"
pagamentos_efetuados:
  "36": "PGBL (limite 12% dos rendimentos tributáveis)"
"""


def _write_year(tmp_path: Path, ano: int, content: str | None = None) -> Path:
    path = tmp_path / f"e16_codigos_rfb_{ano}.yaml"
    path.write_text(content or _MINIMAL_YAML.format(ano=ano), encoding="utf-8")
    return path


def test_carrega_yaml_2024_do_repo():
    codes = load_rfb_codes(2024)
    assert codes.ano_base == 2024
    assert codes.rendimentos_isentos["09"] == "Lucros e dividendos recebidos"
    assert codes.tributacao_exclusiva["06"] == "Ganho de capital"
    assert "12%" in codes.pagamentos_efetuados["36"]


def test_ano_inexistente_falha_fast_com_valor_ofensor(tmp_path):
    _write_year(tmp_path, 2024)
    with pytest.raises(FileNotFoundError) as exc:
        load_rfb_codes(2031, prompts_dir=tmp_path)
    msg = str(exc.value)
    assert "ano_base 2031" in msg
    assert str(rfb_codes_path(2031, tmp_path)) in msg
    assert "2024" in msg, "mensagem deve listar anos disponíveis"


def test_secao_ausente_falha_fast_com_valor_ofensor(tmp_path):
    broken = 'version: 1\nano_base: 2024\nrendimentos_isentos:\n  "09": "x"\n'
    _write_year(tmp_path, 2024, broken)
    with pytest.raises(ValueError, match="tributacao_exclusiva"):
        load_rfb_codes(2024, prompts_dir=tmp_path)


def test_ano_base_declarado_diferente_do_filename_falha_fast(tmp_path):
    _write_year(tmp_path, 2025, _MINIMAL_YAML.format(ano=2024))
    with pytest.raises(ValueError, match=r"ano_base declarado 2024 != 2025"):
        load_rfb_codes(2025, prompts_dir=tmp_path)


def test_available_years_ordenado(tmp_path):
    _write_year(tmp_path, 2025)
    _write_year(tmp_path, 2024)
    assert available_rfb_years(tmp_path) == [2024, 2025]


def test_resolve_usa_hint_quando_existe_e_latest_quando_nao(tmp_path):
    _write_year(tmp_path, 2024)
    _write_year(tmp_path, 2025)
    assert resolve_rfb_codes(2024, prompts_dir=tmp_path).ano_base == 2024
    assert resolve_rfb_codes(2030, prompts_dir=tmp_path).ano_base == 2025
    assert resolve_rfb_codes(None, prompts_dir=tmp_path).ano_base == 2025


def test_resolve_sem_nenhum_yaml_falha_fast(tmp_path):
    with pytest.raises(FileNotFoundError, match="nenhum e16_codigos_rfb"):
        resolve_rfb_codes(2024, prompts_dir=tmp_path)


def test_render_block_contem_as_tres_tabelas():
    block = render_rfb_codes_block(load_rfb_codes(2024))
    assert "ano-base 2024" in block
    assert "Rendimentos isentos e não tributáveis" in block
    assert "tributação exclusiva/definitiva" in block
    assert "Pagamentos efetuados" in block
    assert '- "36": PGBL' in block


def test_e16_template_formata_com_codigos_rfb_e_texto_verbatim():
    from pipeline.llm.prompts.e16_irpf_full import USER_PROMPT_TEMPLATE

    raw = '{"ficha": {"campo": 1}}'
    block = render_rfb_codes_block(load_rfb_codes(2024))
    filled = USER_PROMPT_TEMPLATE.format(codigos_rfb=block, documents_text=raw)
    assert raw in filled
    assert '- "36": PGBL' in filled
