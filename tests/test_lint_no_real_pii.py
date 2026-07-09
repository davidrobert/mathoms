"""Testes do lint anti-PII estendido (A34.l4 · ADR-319).

Todas as fixtures são sintéticas por construção — CPFs com DV calculado a
partir de bases obviamente fictícias, endereços/placas inventados. Este
arquivo está em `_SELF_PATHS` do linter (define a política; fora do scan).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).parent.parent / "tests" / "utils" / "lint_no_real_pii.py"
_SPEC = importlib.util.spec_from_file_location("lint_no_real_pii", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
lint = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(lint)


# ─── CPF: só dígito verificador válido é PII potencial ─────────────────


def test_cpf_valid_dv_flagged() -> None:
    # 987.654.321-00 tem DV mod-11 válido e não é placeholder allowlistado.
    assert lint._cpf_findings('cpf = "987.654.321' + '-00"')


def test_cpf_placeholder_allowlisted() -> None:
    assert not lint._cpf_findings("CPF de exemplo: 123.456.789-09")
    assert not lint._cpf_findings("CPF zerado: 000.000.000-00")


def test_cpf_invalid_dv_is_synthetic() -> None:
    # DV inválido é sintético por construção — não flagra.
    assert not lint._cpf_findings("qualquer 123.456.789-10 na linha")


def test_cpf_repeated_digits_not_flagged() -> None:
    assert not lint._cpf_findings("teste 222.222.222-22 repetido")


# ─── Endereço ───────────────────────────────────────────────────────────


def test_endereco_flagged() -> None:
    assert lint._endereco_findings("mora na Rua Fulana Sintética, 123 apto 4")
    assert lint._endereco_findings("CASA - RUA TESTE FICTICIA, 45 - SP")
    assert lint._endereco_findings("Av Paulista 1500 apt 42")
    assert lint._endereco_findings("Praça Fictícia Qualquer 186")


def test_endereco_abreviado_com_particula_flagged() -> None:
    assert lint._endereco_findings("residência R Nome da Serra")


def test_endereco_placeholder_allowlisted() -> None:
    assert not lint._endereco_findings("use Rua Exemplo, 100 como fixture")


def test_endereco_prosa_nao_flagra() -> None:
    assert not lint._endereco_findings("a rua estava vazia às 10")
    assert not lint._endereco_findings("R Studio é uma IDE")


# ─── Placa ──────────────────────────────────────────────────────────────


def test_placa_mercosul_e_antiga_flagged() -> None:
    assert lint._placa_findings('descricao: "TST1A23-ESTACIONAMENTO"')
    assert lint._placa_findings("placa TST-1234 formato antigo")


def test_placa_placeholders_e_tokens_tecnicos() -> None:
    assert not lint._placa_findings("crlv_abc1d23_2024 usa ABC1D23 sintética")
    assert not lint._placa_findings("datas em ISO8601 ou ISO-8601")
    assert not lint._placa_findings("changelog CHG-2026-05-12 não é placa")


# ─── Matrícula / contrato ───────────────────────────────────────────────


def test_contrato_flagged() -> None:
    assert lint._contrato_findings("contrato nº 123456-7 do financiamento")
    assert lint._contrato_findings("Matrícula 456.789.012 do imóvel")


def test_matricula_placeholder_allowlisted() -> None:
    assert not lint._contrato_findings("matrícula 999.999 (placeholder canônico)")


# ─── Homedir ────────────────────────────────────────────────────────────


def test_homedir_flagged() -> None:
    assert lint._homedir_findings("path /Use" + "rs/fulano/repo hardcoded")


def test_homedir_placeholder_mascarado_passa() -> None:
    assert not lint._homedir_findings("use /Use" + "rs/<owner>/... nos docs")


# ─── scan_file: marcador PII-ok por tipo de arquivo ────────────────────


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_scan_file_marker_honored_in_code(tmp_path: Path) -> None:
    p = _write(tmp_path, "f.py", 'cpf = "987.654.321' + '-00"  # noqa: PII-ok\n')
    assert lint.scan_file(p) == []


def test_scan_file_marker_ignored_in_markdown(tmp_path: Path) -> None:
    # Prosa que cita "PII-ok" não pode auto-suprimir o gate (caso real de
    # doc de archive transcrevendo CPF na linha que menciona a anotação).
    p = _write(tmp_path, "f.md", "CPF real 987.654.321" + "-00 anotado PII-ok\n")
    assert lint.scan_file(p) == [(1, "CPF")]


def test_scan_file_reports_tipo_por_linha(tmp_path: Path) -> None:
    p = _write(tmp_path, "f.md", "Rua Sintética Nova, 77\nplaca TST1A23\n")
    assert lint.scan_file(p) == [(1, "ENDERECO"), (2, "PLACA")]


# ─── Baseline burn-down ─────────────────────────────────────────────────


def test_baseline_file_shape() -> None:
    entries = lint._load_baseline()
    assert entries, "baseline não pode ser vazio enquanto W1 não zera os hits"
    assert all(isinstance(p, str) and isinstance(t, str) for p, t in entries)
    tipos = {t for _, t in entries}
    assert tipos <= set(lint.DETECTORS)


def test_baseline_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    lint._write_baseline({("a/b.md", "CPF"), ("c.py", "PLACA")}, path)
    assert lint._load_baseline(path) == {("a/b.md", "CPF"), ("c.py", "PLACA")}
