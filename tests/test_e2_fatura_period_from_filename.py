#!/usr/bin/env python3
"""A32.l3 — período de fatura vem do token canônico no fim do stem.

Parsers de fatura re-derivavam ``data_vencimento`` com
``re.search(r"(\\d{4})(\\d{2})")`` não-ancorada, que casava os primeiros 6
dígitos do prefixo content-addressed ``sha256[:12]`` (ADR-084) e produzia
datas-fantasma via clamp de ``safe_date`` (``2100-01-06``, ``1899-12-07``,
``2100-06-05``, ``2100-01-05`` — 7/7 na run dogfood). ``documents.period``
estava correto no DB/filename; o parser corrompia re-derivando.

Estes testes assertam a DATA EXATA — nunca "dentro da faixa [1900, 2100]" —
para que o clamp não mascare regressão.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e2.banks.c6bank import parse_c6_carbon_csv
from scripts.e2.banks.itau import parse_itau_paoacucar_csv
from scripts.e2.banks.santander import parse_santander_fatura_csv
from scripts.e2.common import canonical_period_token, infer_fatura_ref_from_filename
from scripts.e2.registry import route_to_parser

# =============================================================================
# Fixtures sintéticas (PII-zero)
# =============================================================================

_SANTANDER_FATURA_CSV = """data,lancamento,valor
2026-02-05,LOJA SINTETICA,100.00
2026-02-12,PAGAMENTO EFETUADO,-100.00
"""

_C6_CARBON_CSV = (
    "Data de Compra;Nome no Cartão;Final do Cartão;Categoria;Descrição;Parcela;"
    "Valor (em US$);Cotação (em R$);Valor (em R$)\n"
    "05/01/2026;TITULAR SINTETICO;1234;Mercado;MERCADO SINTETICO;Única;0;0;250.50\n"
)

_PAOACUCAR_CSV = """data,lançamento,valor
2026-03-05,RESTAURANTE SINTETICO,150.00
"""

# Datas-fantasma observadas na run dogfood — nunca podem reaparecer.
_PHANTOM_DATES = {"2100-01-06", "1899-12-07", "2100-06-05", "2100-01-05", "1900-01-06"}


def _write(tmp_path: Path, filename: str, content: str) -> Path:
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    return path


# =============================================================================
# Helper: token canônico ancorado ao fim do stem
# =============================================================================


class TestCanonicalPeriodToken:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            # Prefixo hash com 6 dígitos consecutivos — o caso que corrompia.
            ("285768f03c9b_santander_faturaunique_202602-0_original.csv", "202602"),
            # Prefixo hash sem 6 dígitos consecutivos.
            ("a1b2c3d4e5f6_c6bank_faturacarbon_202603-0_original.csv", "202603"),
            # Sem prefixo hash, com e sem -0_original.
            ("santander_faturaunique_202602-0_original.csv", "202602"),
            ("santander_faturaunique_202604.csv", "202604"),
            ("quintoandar_faturaaluguelapt01_202604.pdf", "202604"),
            # Sufixo de colisão [a-z] (resolve_collision).
            ("santander_faturaunique_202602a-0_original.csv", "202602"),
            # Token de 8 dígitos (period default YYYYMMDD do build_final_name).
            ("bancox_faturax_20260410-0_original.pdf", "20260410"),
            # Sentinel propaga como token.
            ("c6bank_faturacarbon_999999-0_original.csv", "999999"),
            # Sem token de período no fim do stem.
            ("285768f03c9b_santander_faturaunique-0_original.csv", None),
            ("itau_faturapaoacucar_fatura-20260410.csv", None),
        ],
    )
    def test_token(self, filename, expected):
        assert canonical_period_token(filename) == expected


class TestInferFaturaRefFromFilename:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("285768f03c9b_santander_faturaunique_202602-0_original.csv", (2026, 2)),
            ("090976aab3c9_santander_faturaunique_202601-0_original.csv", (2026, 1)),
            ("761406aa03c9_c6bank_faturacarbon_202606-0_original.csv", (2026, 6)),
            ("285799aa03c9_c6bank_faturacarbon_202601-0_original.csv", (2026, 1)),
            ("a1b2c3d4e5f6_c6bank_faturacarbon_202603-0_original.csv", (2026, 3)),
            ("santander_faturaunique_202604.csv", (2026, 4)),
            ("santander_faturaunique_202602a-0_original.csv", (2026, 2)),
            ("bancox_faturax_20260410-0_original.pdf", (2026, 4)),
            # Sentinel 999999 (E0→E2→E3) — nunca vira data.
            ("c6bank_faturacarbon_999999-0_original.csv", (None, None)),
            ("285768f03c9b_santander_faturaunique_999999-0_original.csv", (None, None)),
            # Sem token / token implausível — nunca inventa data.
            ("285768f03c9b_santander_faturaunique-0_original.csv", (None, None)),
            ("bancox_faturax_209912-0_original.csv", (None, None)),
            ("bancox_faturax_202613-0_original.csv", (None, None)),
        ],
    )
    def test_ref(self, filename, expected):
        assert infer_fatura_ref_from_filename(filename) == expected


# =============================================================================
# Parsers: data EXATA de vencimento (os 4 padrões corrompidos da dogfood)
# =============================================================================


class TestFaturaVencimentoExato:
    def test_santander_hash_prefix_202602(self, tmp_path):
        """Dogfood: 285768 → ano 2857 → clamp → 2100-01-06. Agora: 2026-02-06."""
        filename = "285768f03c9b_santander_faturaunique_202602-0_original.csv"
        path = _write(tmp_path, filename, _SANTANDER_FATURA_CSV)
        result = parse_santander_fatura_csv(path, filename)
        assert result["data_vencimento"] == "2026-02-06"
        assert len(result["transacoes"]) == 2

    def test_santander_hash_prefix_low_year(self, tmp_path):
        """Dogfood: 090976 → ano 909 → clamp 1900-01-06 → início 1899-12-07."""
        filename = "090976aab3c9_santander_faturaunique_202601-0_original.csv"
        path = _write(tmp_path, filename, _SANTANDER_FATURA_CSV)
        result = parse_santander_fatura_csv(path, filename)
        assert result["data_vencimento"] == "2026-01-06"

    def test_c6_carbon_hash_prefix_202606(self, tmp_path):
        """Dogfood: 761406 → ano 7614 → clamp → 2100-06-05. Agora: 2026-06-05."""
        filename = "761406aa03c9_c6bank_faturacarbon_202606-0_original.csv"
        path = _write(tmp_path, filename, _C6_CARBON_CSV)
        result = parse_c6_carbon_csv(path, filename)
        assert result["data_vencimento"] == "2026-06-05"
        assert len(result["transacoes"]) == 1

    def test_c6_carbon_hash_prefix_202601(self, tmp_path):
        """Dogfood: 285799 → mês 99 → clamp → 2100-01-05. Agora: 2026-01-05."""
        filename = "285799aa03c9_c6bank_faturacarbon_202601-0_original.csv"
        path = _write(tmp_path, filename, _C6_CARBON_CSV)
        result = parse_c6_carbon_csv(path, filename)
        assert result["data_vencimento"] == "2026-01-05"

    def test_itau_paoacucar_hash_prefix(self, tmp_path):
        filename = "285768f03c9b_itau_faturapaoacucar_202603-0_original.csv"
        path = _write(tmp_path, filename, _PAOACUCAR_CSV)
        result = parse_itau_paoacucar_csv(path, filename)
        assert result["data_vencimento"] == "2026-03-06"

    @pytest.mark.parametrize(
        "filename,builder_content,parser",
        [
            (
                "285768f03c9b_santander_faturaunique_202602-0_original.csv",
                _SANTANDER_FATURA_CSV,
                parse_santander_fatura_csv,
            ),
            (
                "090976aab3c9_c6bank_faturacarbon_202601-0_original.csv",
                _C6_CARBON_CSV,
                parse_c6_carbon_csv,
            ),
        ],
    )
    def test_phantom_dates_never_emitted(self, tmp_path, filename, builder_content, parser):
        path = _write(tmp_path, filename, builder_content)
        result = parser(path, filename)
        assert result["data_vencimento"] not in _PHANTOM_DATES


class TestFaturaVencimentoRegressao:
    """Corpus que já parseava certo — não pode regredir."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("santander_faturaunique_202604.csv", "2026-04-06"),
            ("santander_faturaunique_202602-0_original.csv", "2026-02-06"),
            ("santander_faturaunique_202602a-0_original.csv", "2026-02-06"),
        ],
    )
    def test_santander_sem_hash(self, tmp_path, filename, expected):
        path = _write(tmp_path, filename, _SANTANDER_FATURA_CSV)
        result = parse_santander_fatura_csv(path, filename)
        assert result["data_vencimento"] == expected

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("c6bank_faturacarbon_202604.csv", "2026-04-05"),
            ("a1b2c3d4e5f6_c6bank_faturacarbon_202603-0_original.csv", "2026-03-05"),
        ],
    )
    def test_c6_carbon(self, tmp_path, filename, expected):
        path = _write(tmp_path, filename, _C6_CARBON_CSV)
        result = parse_c6_carbon_csv(path, filename)
        assert result["data_vencimento"] == expected

    def test_itau_paoacucar_legacy_fatura_token(self, tmp_path):
        """Formato legado ``fatura-YYYYMMDD`` continua tendo precedência."""
        filename = "itau_faturapaoacucar_fatura-20260410.csv"
        path = _write(tmp_path, filename, _PAOACUCAR_CSV)
        result = parse_itau_paoacucar_csv(path, filename)
        assert result["data_vencimento"] == "2026-04-10"

    def test_itau_paoacucar_fatura_aberta(self, tmp_path):
        filename = "itau_faturapaoacucar_fatura-99999999.csv"
        path = _write(tmp_path, filename, _PAOACUCAR_CSV)
        result = parse_itau_paoacucar_csv(path, filename)
        assert result["data_vencimento"] is None
        assert any("aberta" in n for n in result.get("notas", []))


class TestSentinelPropagaSemData:
    """Sentinel 999999 (período indeterminável) propaga E0→E2→E3: o parser
    deixa ``data_vencimento`` vazio e o E3 deriva o período das transações."""

    def test_c6_carbon_sentinel(self, tmp_path):
        filename = "c6bank_faturacarbon_999999-0_original.csv"
        path = _write(tmp_path, filename, _C6_CARBON_CSV)
        result = parse_c6_carbon_csv(path, filename)
        assert result["data_vencimento"] is None
        assert len(result["transacoes"]) == 1

    def test_santander_sentinel_com_hash(self, tmp_path):
        """Antes: hash 285768… corrompia sentinel em 2100-01-06."""
        filename = "285768f03c9b_santander_faturaunique_999999-0_original.csv"
        path = _write(tmp_path, filename, _SANTANDER_FATURA_CSV)
        result = parse_santander_fatura_csv(path, filename)
        assert result["data_vencimento"] is None


class TestRoutingComHashPrefix:
    """Filenames hash-prefixados continuam roteando para o parser certo."""

    @pytest.mark.parametrize(
        "filename,expected_parser",
        [
            (
                "285768f03c9b_santander_faturaunique_202602-0_original.csv",
                "parse_santander_fatura_csv",
            ),
            ("761406aa03c9_c6bank_faturacarbon_202606-0_original.csv", "parse_c6_carbon_csv"),
            ("285768f03c9b_itau_faturapaoacucar_202603-0_original.csv", "parse_itau_paoacucar_csv"),
        ],
    )
    def test_route(self, filename, expected_parser):
        parser = route_to_parser(filename)
        assert parser is not None
        assert parser.__name__ == expected_parser


# =============================================================================
# Gate de fonte: nenhuma busca livre de 6 dígitos em regex de filename
# =============================================================================

_E2_DIR = Path(__file__).resolve().parent.parent / "scripts" / "e2"

# Regex literal começando direto em `(\d{4})(\d{2})` ou `(\d{4})\d{2}` — sem
# âncora (`_`, `^`, texto literal) antes. É o padrão que casava o prefixo
# sha256[:12] (A32.l3). Buscas em CONTEÚDO (ex.: `\d{2}/\d{2}/\d{4}`) não casam.
_FREE_SIX_DIGIT_SEARCH = re.compile(
    r"""re\.(?:search|match|findall)\(\s*r?['"]\(?\\d\{4\}\)?\(?\\d\{2\}"""
)


def _free_search_offenders(py: Path) -> list:
    rel = py.relative_to(_E2_DIR.parent.parent)
    lines = py.read_text(encoding="utf-8").splitlines()
    return [
        f"{rel}:{n}: {line.strip()}"
        for n, line in enumerate(lines, 1)
        if _FREE_SIX_DIGIT_SEARCH.search(line)
    ]


class TestNoFreeSixDigitFilenameSearch:
    def test_scripts_e2_sources(self):
        offenders = [
            offender
            for py in sorted(_E2_DIR.rglob("*.py"))
            for offender in _free_search_offenders(py)
        ]
        assert not offenders, (
            "busca livre de 6 dígitos em regex — casa o prefixo sha256[:12] e "
            "corrompe o período (A32.l3); use canonical_period_token/"
            "infer_fatura_ref_from_filename:\n" + "\n".join(offenders)
        )
