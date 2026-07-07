"""Testes unit\u00e1rios A6d.2 — parsers content-based de scripts/analyze_finances.py.

Objetivo: provar que ``parse_tarefas_md_content``, ``parse_milhas_md_content`` e
``extract_if_*`` s\u00e3o **puros** — rodam sem tocar em disco, sem fixture de
config, sem tmp_path.

Exclui goldens (test_e5_golden_execution.py j\u00e1 cobre paridade com disco).
"""

from __future__ import annotations

import pytest

from scripts.analyze_finances import (
    extract_if_target_from_life_plan,
    extract_if_trs,
    extract_renda_passiva_from_life_plan,
    parse_milhas_md_content,
    parse_tarefas_md_content,
)

# =============================================================================
# parse_tarefas_md_content — fun\u00e7\u00e3o pura
# =============================================================================


def test_tarefas_content_empty_string_returns_empty_lists():
    tarefas, status = parse_tarefas_md_content("")
    assert tarefas == []
    assert status == {}


def test_tarefas_content_essenciais_mapped_to_alta():
    md = """
## Essenciais
| # | Tarefa | Categoria | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 1 | Criar reserva | Reserva | 30d | pendente | R1 |
"""
    tarefas, status = parse_tarefas_md_content(md)
    assert len(tarefas) == 1
    assert tarefas[0]["p"] == "alta"
    assert tarefas[0]["n"] == 1
    assert tarefas[0]["t"] == "Criar reserva"
    assert tarefas[0]["categoria"] == "Reserva"
    assert status["1"] == "pendente"


def test_tarefas_content_recomendadas_mapped_to_media():
    md = """
## Recomendadas
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 2 | Rebalancear | Inv | 90d | feito | R2 |
"""
    tarefas, status = parse_tarefas_md_content(md)
    assert tarefas[0]["p"] == "media"
    assert status["2"] == "feito"


def test_tarefas_content_opcionais_mapped_to_baixa():
    md = """
## Opcionais
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 3 | Estudar REITs | Educ | 180d | pendente | - |
"""
    tarefas, _ = parse_tarefas_md_content(md)
    assert tarefas[0]["p"] == "baixa"


def test_tarefas_content_mixed_sections():
    md = """
## Essenciais
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 1 | A | C | 30d | pendente | - |

## Recomendadas
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 2 | B | C | 60d | feito | - |

## Opcionais
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 3 | C | C | 180d | pendente | - |
"""
    tarefas, status = parse_tarefas_md_content(md)
    assert len(tarefas) == 3
    prios = {t["n"]: t["p"] for t in tarefas}
    assert prios == {1: "alta", 2: "media", 3: "baixa"}
    assert status == {"1": "pendente", "2": "feito", "3": "pendente"}


def test_tarefas_content_concluidas_section_ignored():
    md = """
## Essenciais
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 1 | Ativa | C | 30d | pendente | - |

## Conclu\u00eddas
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 99 | Hist\u00f3rica | C | - | feito | - |
"""
    tarefas, _ = parse_tarefas_md_content(md)
    nums = {t["n"] for t in tarefas}
    assert nums == {1}


def test_tarefas_content_canceladas_section_ignored():
    md = """
## Essenciais
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 1 | Ativa | C | 30d | pendente | - |

## Canceladas
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 50 | Descartada | C | - | cancelado | - |
"""
    tarefas, _ = parse_tarefas_md_content(md)
    assert {t["n"] for t in tarefas} == {1}


def test_tarefas_content_invalid_rows_skipped():
    md = """
## Essenciais
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| abc | Sem numero | C | 30d | pendente | - |
| 1 | V\u00e1lida | C | 30d | pendente | - |
| 2 | Poucas cols | C |
"""
    tarefas, status = parse_tarefas_md_content(md)
    nums = {t["n"] for t in tarefas}
    assert nums == {1}
    assert status == {"1": "pendente"}


def test_tarefas_content_status_normalized_to_pendente_if_invalid():
    md = """
## Essenciais
| # | Tarefa | Cat | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 1 | A | C | 30d | em-progresso | - |
"""
    _, status = parse_tarefas_md_content(md)
    assert status["1"] == "pendente"


# =============================================================================
# parse_milhas_md_content — fun\u00e7\u00e3o pura
# =============================================================================


def test_milhas_content_empty_string_returns_empty_dict():
    result = parse_milhas_md_content("")
    assert result["programas"] == []
    assert result["programas_registrados"] == []
    assert result["total_valor_estimado_brl"] == 0
    assert result["total_economia_periodo_brl"] == 0
    assert result["total_pontos_resgatados"] == 0


def test_milhas_content_single_programa_with_saldo():
    md = """
### Livelo \u2014 David
| Campo | Valor |
|---|---|
| saldo_pontos | 150000 |
| custo_medio_ponto_brl | 0.02 |
| valor_estimado_brl | 3000 |
"""
    result = parse_milhas_md_content(md)
    assert len(result["programas"]) == 1
    p = result["programas"][0]
    assert p["programa"] == "Livelo"
    assert p["titular"] == "David"
    assert p["saldo_pontos"] == 150000
    assert p["custo_medio_ponto_brl"] == 0.02
    assert p["valor_estimado_brl"] == 3000
    assert result["total_valor_estimado_brl"] == 3000
    assert result["programas_registrados"] == ["Livelo (David)"]


def test_milhas_content_filters_out_zero_saldo_programas():
    md = """
### Livelo \u2014 David
| Campo | Valor |
|---|---|
| saldo_pontos | 150000 |
| valor_estimado_brl | 3000 |

### Smiles \u2014 Mariana
| Campo | Valor |
|---|---|
| saldo_pontos | 0 |
| valor_estimado_brl | 0 |
"""
    result = parse_milhas_md_content(md)
    # Display apenas Livelo (tem saldo); ambos aparecem em programas_registrados
    assert len(result["programas"]) == 1
    assert result["programas"][0]["programa"] == "Livelo"
    assert set(result["programas_registrados"]) == {"Livelo (David)", "Smiles (Mariana)"}


def test_milhas_content_multiple_programas_aggregates_total():
    md = """
### Livelo \u2014 David
| Campo | Valor |
|---|---|
| saldo_pontos | 100000 |
| valor_estimado_brl | 2000 |

### Smiles \u2014 Mariana
| Campo | Valor |
|---|---|
| saldo_pontos | 50000 |
| valor_estimado_brl | 1000 |
"""
    result = parse_milhas_md_content(md)
    assert len(result["programas"]) == 2
    assert result["total_valor_estimado_brl"] == 3000


def test_milhas_content_ignores_non_table_rows():
    md = """
### Livelo \u2014 David
Texto aleat\u00f3rio antes da tabela.
| Campo | Valor |
|---|---|
| saldo_pontos | 100 |
| valor_estimado_brl | 2 |
Texto depois.
"""
    result = parse_milhas_md_content(md)
    assert len(result["programas"]) == 1
    assert result["programas"][0]["saldo_pontos"] == 100


def test_milhas_content_invalid_numeric_values_ignored():
    md = """
### Livelo \u2014 David
| Campo | Valor |
|---|---|
| saldo_pontos | 100 |
| valor_estimado_brl | N/A |
"""
    result = parse_milhas_md_content(md)
    p = result["programas"][0]
    assert p["saldo_pontos"] == 100
    assert p["valor_estimado_brl"] == 0.0  # default preserved


# =============================================================================
# extract_if_target_from_life_plan — pure com content param
# =============================================================================


def test_extract_if_target_from_content(monkeypatch):
    # Garante que GOALS_CONFIG não tem if_meta — isola o path do MD.
    import scripts.analyze_finances as e5

    monkeypatch.setattr(e5, "GOALS_CONFIG", {})
    content = """
# Plano de Vida
Meta IF: **R$ 3.000.000,00
TRS 4%.
"""
    assert extract_if_target_from_life_plan(content) == pytest.approx(3_000_000.0)


def test_extract_if_target_priority_goals_json_over_content(monkeypatch):
    """goals.json tem prioridade sobre life_plan_goals.md."""
    import scripts.analyze_finances as e5

    monkeypatch.setattr(
        e5,
        "GOALS_CONFIG",
        {"independencia_financeira": {"if_meta": 5_000_000}},
    )
    # Content com valor diferente — ignorado.
    content = "Meta: **R$ 1.000.000,00"
    assert extract_if_target_from_life_plan(content) == pytest.approx(5_000_000.0)


def test_extract_if_target_no_goals_no_content_raises(monkeypatch):
    import scripts.analyze_finances as e5

    monkeypatch.setattr(e5, "GOALS_CONFIG", {})
    # Passa explicitamente content="" — n\u00e3o cai para disco.
    with pytest.raises(ValueError, match="IF meta"):
        extract_if_target_from_life_plan("")


def test_extract_if_trs_from_content(monkeypatch):
    import scripts.analyze_finances as e5

    monkeypatch.setattr(e5, "GOALS_CONFIG", {})
    content = """
Retirada: TRS de 3,5% ao ano.
"""
    assert extract_if_trs(content) == pytest.approx(3.5)


def test_extract_if_trs_priority_goals_over_content(monkeypatch):
    import scripts.analyze_finances as e5

    monkeypatch.setattr(
        e5,
        "GOALS_CONFIG",
        {"independencia_financeira": {"trs_pct": 4.0}},
    )
    content = "TRS 10%"  # ignorado
    assert extract_if_trs(content) == pytest.approx(4.0)


def test_extract_if_trs_no_goals_no_content_raises(monkeypatch):
    import scripts.analyze_finances as e5

    monkeypatch.setattr(e5, "GOALS_CONFIG", {})
    with pytest.raises(ValueError, match="TRS"):
        extract_if_trs("")


def test_extract_renda_passiva_from_content():
    content = """
# Renda passiva
Renda passiva atual: R$ 2.345,67
"""
    assert extract_renda_passiva_from_life_plan(content) == pytest.approx(2345.67)


def test_extract_renda_passiva_empty_returns_zero():
    assert extract_renda_passiva_from_life_plan("") == 0.0


def test_extract_renda_passiva_no_match_returns_zero():
    content = "# Outras seções sem renda passiva"
    assert extract_renda_passiva_from_life_plan(content) == 0.0


# =============================================================================
# Sanity — shell loaders NÃO quebram quando arquivos ausentes
# =============================================================================


def test_parse_tarefas_md_shell_loader_returns_empty_when_file_missing(monkeypatch, tmp_path):
    """Shell loader tolera CONFIG_TAREFAS ausente — back-compat."""
    import scripts.analyze_finances as e5

    monkeypatch.setattr(e5, "CONFIG_TAREFAS", tmp_path / "nonexistent.md")
    tarefas, status = e5.parse_tarefas_md()
    assert tarefas == []
    assert status == {}


def test_parse_milhas_md_shell_loader_returns_empty_when_file_missing(monkeypatch, tmp_path):
    import scripts.analyze_finances as e5

    monkeypatch.setattr(e5, "CONFIG_MILHAS", tmp_path / "nonexistent.md")
    monkeypatch.setattr(e5, "CONFIG_MILHAS_NEW", tmp_path / "nonexistent_new.md")
    monkeypatch.setattr(e5, "CONFIG_MILHAS_LEGACY", tmp_path / "nonexistent_legacy.md")
    assert e5.parse_milhas_md() == {}


def test_parse_milhas_md_prefers_new_path(monkeypatch, tmp_path):
    """ADR-147 (A7.6): bridge tenta path novo antes do legado."""
    import scripts.analyze_finances as e5

    new_path = tmp_path / "notes" / "milhas.md"
    legacy_path = tmp_path / "docs" / "methodology" / "milhas.md"
    new_path.parent.mkdir(parents=True)
    legacy_path.parent.mkdir(parents=True)
    new_path.write_text("### ProgramaNew — TitularExemplo\n", encoding="utf-8")
    legacy_path.write_text("### ProgramaLegacy — TitularExemplo\n", encoding="utf-8")

    monkeypatch.setattr(e5, "CONFIG_MILHAS_NEW", new_path)
    monkeypatch.setattr(e5, "CONFIG_MILHAS_LEGACY", legacy_path)
    monkeypatch.setattr(e5, "CONFIG_MILHAS", new_path)

    result = e5.parse_milhas_md()
    registered = result.get("programas_registrados", [])
    assert any("ProgramaNew" in name for name in registered)
    assert not any("ProgramaLegacy" in name for name in registered)


def test_parse_milhas_md_falls_back_to_legacy_with_warning(monkeypatch, tmp_path):
    """ADR-147 (A7.6): quando path novo não existe, fallback ao legado emite
    DeprecationWarning. Bridge é removido em A7.5 cleanup."""
    import warnings

    import scripts.analyze_finances as e5

    new_path = tmp_path / "notes" / "milhas.md"  # não existe
    legacy_path = tmp_path / "docs" / "methodology" / "milhas.md"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        "### ProgramaExemplo — TitularExemplo\n"
        "| Campo | Valor |\n"
        "| --- | --- |\n"
        "| saldo_pontos | 1000 |\n"
        "| valor_estimado_brl | 50.0 |\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(e5, "CONFIG_MILHAS_NEW", new_path)
    monkeypatch.setattr(e5, "CONFIG_MILHAS_LEGACY", legacy_path)
    monkeypatch.setattr(e5, "CONFIG_MILHAS", new_path)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = e5.parse_milhas_md()

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
    registered = result.get("programas_registrados", [])
    assert any("ProgramaExemplo" in name for name in registered)
