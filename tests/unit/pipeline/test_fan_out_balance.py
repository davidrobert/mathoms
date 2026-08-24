"""A40.l68 (RV6-10 · ADR-393) — o balanço do fan-out e o leitor tipado.

O defeito medido: documento entrava na fila do `extract_with_llm` e não saía nem
como `processed` nem como `error` — sumia, e o stage devolvia `success=True`
sobre corpus incompleto. O mesmo `.xls` sumiu em 3 runs consecutivos.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from pipeline.domain.review_reason import BLOCKING_CODES, ReviewReasonCode
from pipeline.llm.text_extractor import DocumentTextExtractor, ReaderOutcome
from pipeline.stages.extract_with_llm import (
    _e2llm_validation_block,
    _fan_out_balance,
    _skip_entry,
)


class TestLeitorTipado:
    """As 5 situações que devolviam `""` indistinguível (ADR-393 D2)."""

    @pytest.mark.parametrize(
        "nome,conteudo,esperado",
        [
            ("x.txt", b"conteudo real", ReaderOutcome.ok),
            ("x.txt", b"   \n  ", ReaderOutcome.documento_vazio),
            ("x.zip", b"qualquer", ReaderOutcome.leitor_ausente),
            ("x.sem_extensao", b"qualquer", ReaderOutcome.leitor_ausente),
        ],
    )
    def test_motivo_por_situacao(self, tmp_path: Path, nome, conteudo, esperado) -> None:
        doc = tmp_path / nome
        doc.write_bytes(conteudo)
        assert DocumentTextExtractor().extract_result(doc).outcome is esperado

    def test_arquivo_corrompido_e_leitura_falhou_nao_documento_vazio(self, tmp_path: Path) -> None:
        # NÃO é o caso do r6: bytes-lixo falham em qualquer leitor, então este
        # teste ficava verde com o roteamento errado E com o certo. O r6 mora
        # em `TestXlsLegado`, que precisa de BIFF de verdade.
        """Bytes que não são planilha nenhuma: defeito de leitura, nunca `""`."""
        doc = tmp_path / "extrato.xls"
        doc.write_bytes(b"conteudo que nao e planilha")

        resultado = DocumentTextExtractor().extract_result(doc)

        assert resultado.outcome is ReaderOutcome.leitura_falhou
        assert resultado.is_defect is True

    def test_documento_vazio_nao_e_defeito(self, tmp_path: Path) -> None:
        """Zero legítimo não pode virar needs_review — é o falso-positivo a evitar."""
        doc = tmp_path / "vazio.txt"
        doc.write_text("   ")

        assert DocumentTextExtractor().extract_result(doc).is_defect is False

    def test_extract_str_continua_funcionando(self, tmp_path: Path) -> None:
        """Wrapper de compat: 4 stages fora do escopo ainda consomem `-> str`."""
        doc = tmp_path / "x.txt"
        doc.write_text("conteudo")

        assert DocumentTextExtractor().extract(doc) == "conteudo"


class TestBalanco:
    def test_fecha_quando_todo_documento_tem_destino(self) -> None:
        b = _fan_out_balance(queued=3, processed=[{}], errors=[{}], skipped=[{}])

        assert b["fecha"] is True
        assert b["contabilizado"] == 3

    def test_nao_fecha_com_documento_sem_destino(self) -> None:
        """Desbalanço construído à mão — é o estado que era invisível."""
        b = _fan_out_balance(queued=3, processed=[{}], errors=[], skipped=[])

        assert b["fecha"] is False
        assert b["contabilizado"] == 1

    def test_queued_zero_fecha(self) -> None:
        assert _fan_out_balance(queued=0, processed=[], errors=[], skipped=[])["fecha"] is True


class TestSkipNomeiaODocumento:
    def test_skip_carrega_arquivo_motivo_e_detalhe(self) -> None:
        e = _skip_entry(Path("/data/extrato.xls"), "leitura_falhou", "InvalidFileException: ...")

        assert e["file"] == "extrato.xls"
        assert e["motivo"] == "leitura_falhou"
        assert e["detalhe"]

    def test_defeito_de_leitor_vira_review_reason_nomeando_o_arquivo(self) -> None:
        skipped = [{"file": "extrato.xls", "motivo": "leitura_falhou", "detalhe": "boom"}]

        bloco = _e2llm_validation_block([], skipped)

        assert bloco["valid"] is False
        assert len(bloco["review_reasons"]) == 1
        assert bloco["review_reasons"][0]["code"] == ReviewReasonCode.extract_reader_missing.value
        # o documento é nomeado pelo artifact_key + errors; `document_id` é FK
        # para `documents` (ADR-371) e filename ali abortava o run no INSERT
        assert bloco["review_reasons"][0]["document_id"] is None
        assert bloco["review_reasons"][0]["artifact_key"] == "extrato"
        assert "extrato.xls" in bloco["errors"][0]

    def test_documento_vazio_nao_gera_review_reason(self) -> None:
        """Sem isto o banner dispara sempre e ensina o leitor a ignorá-lo."""
        skipped = [{"file": "vazio.pdf", "motivo": "documento_vazio", "detalhe": ""}]

        bloco = _e2llm_validation_block([], skipped)

        assert bloco["valid"] is True
        assert bloco["review_reasons"] == []

    def test_reader_missing_e_warn_first(self) -> None:
        """ADR-393 D4: declara, não retém o run."""
        assert ReviewReasonCode.extract_reader_missing not in BLOCKING_CODES


def _xls_biff(path: Path, linhas: list[list[object]]) -> Path:
    """BIFF de verdade (xlwt). Bytes-lixo com sufixo `.xls` não exercitam o leitor."""
    import xlwt

    wb = xlwt.Workbook()
    sh = wb.add_sheet("Extrato")
    estilo_data = xlwt.easyxf(num_format_str="DD/MM/YYYY")
    for r, linha in enumerate(linhas):
        for c, valor in enumerate(linha):
            if isinstance(valor, datetime):
                sh.write(r, c, valor, estilo_data)
            else:
                sh.write(r, c, valor)
    wb.save(str(path))
    return path


class TestXlsLegado:
    """A40.l68 §Ataque C: 168/168 `.xls` do corpus saíam `leitura_falhou` porque
    o roteamento mandava BIFF para openpyxl, que só lê OOXML."""

    def test_xls_real_e_legivel(self, tmp_path: Path) -> None:
        doc = _xls_biff(
            tmp_path / "extrato.xls",
            [["Data", "Historico", "Valor"], ["01/01/2026", "TED RECEBIDA", 1234.56]],
        )

        resultado = DocumentTextExtractor().extract_result(doc)

        assert resultado.outcome is ReaderOutcome.ok
        assert resultado.is_defect is False
        assert "TED RECEBIDA" in resultado.text
        assert "1234.56" in resultado.text

    def test_data_nao_sai_como_serial_do_excel(self, tmp_path: Path) -> None:
        """Serial float (`45678.0`) é ilegível para o LLM — o valor vira ISO."""
        doc = _xls_biff(tmp_path / "extrato.xls", [[datetime(2026, 1, 15), "SAQUE"]])

        texto = DocumentTextExtractor().extract_result(doc).text

        assert "2026-01-15" in texto
        assert "46037" not in texto

    def test_mutacao_rotear_xls_para_openpyxl_ressuscita_o_defeito(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sem esta mutação o teste acima poderia passar por outro motivo."""
        doc = _xls_biff(tmp_path / "extrato.xls", [["Data", "Valor"], ["01/01/2026", 10]])
        extractor = DocumentTextExtractor()
        assert extractor.extract_result(doc).outcome is ReaderOutcome.ok

        original = DocumentTextExtractor._reader_for
        monkeypatch.setattr(
            DocumentTextExtractor,
            "_reader_for",
            lambda self, suffix: (
                self._extract_xlsx if suffix == ".xls" else original(self, suffix)
            ),
        )

        resultado = extractor.extract_result(doc)
        assert resultado.outcome is ReaderOutcome.leitura_falhou
        assert "does not support the old .xls" in resultado.detalhe


class TestProvaPorMutacao:
    """A prova que a lane exige: remover o leitor de um formato ⇒ motivo nomeado
    + documento em needs_review + balanço FECHA (não some)."""

    def test_remover_leitor_de_formato_produz_motivo_e_fecha_balanco(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = tmp_path / "extrato.csv"
        doc.write_text("data,valor\n2026-01-01,10.00\n")
        extractor = DocumentTextExtractor()

        # Antes da mutação: o `.csv` é legível.
        assert extractor.extract_result(doc).outcome is ReaderOutcome.ok

        # Mutação: o leitor de `.csv` deixa de existir.
        original = DocumentTextExtractor._reader_for
        monkeypatch.setattr(
            DocumentTextExtractor,
            "_reader_for",
            lambda self, suffix: None if suffix == ".csv" else original(self, suffix),
        )

        resultado = extractor.extract_result(doc)
        assert resultado.outcome is ReaderOutcome.leitor_ausente
        assert resultado.is_defect is True

        # O documento vira skip nomeado…
        skip = _skip_entry(doc, resultado.outcome.value, resultado.detalhe)
        bloco = _e2llm_validation_block([], [skip])
        assert bloco["valid"] is False
        assert bloco["review_reasons"][0]["document_id"] is None
        assert "extrato.csv" in bloco["errors"][0]

        # …e o balanço FECHA: 1 enfileirado, 1 contabilizado. Antes da ADR-393
        # ele sumia e `contabilizado` era 0 com `success=True`.
        balanco = _fan_out_balance(queued=1, processed=[], errors=[], skipped=[skip])
        assert balanco["fecha"] is True
        assert balanco["skipped"] == 1
