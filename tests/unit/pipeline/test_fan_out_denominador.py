"""A40.l68 itens D3 e D5 (ADR-393) — o denominador do fan-out."""

# D5: formato sem leitor é recusado no E0. Roteá-lo para `data/` o faz sumir
# depois — nenhum stage o enfileira e o balanço fecha sobre um denominador que
# nunca o contou (o buraco que o §Ataque A mediu e a DE-4 nomeou).
# D3: a lista de stages de fan-out é DECLARADA. Descoberta por reflexão cresce
# sozinha e fica verde no stage novo — a direção errada do erro.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pipeline.llm.text_extractor import READABLE_SUFFIXES, DocumentTextExtractor
from pipeline.stage_spec import (
    FAN_OUT_STAGES,
    FAN_OUT_STAGES_TYPED_READER,
    FAN_OUT_STAGES_UNTYPED_READER,
    STAGE_REGISTRY,
)

REPO = Path(__file__).resolve().parents[3]


class TestFonteUnicaDeFormatoLegivel:
    def test_todo_sufixo_legivel_tem_leitor_ou_e_imagem(self) -> None:
        from pipeline.llm.text_extractor import IMAGE_EXTENSIONS

        extractor = DocumentTextExtractor()
        for suffix in READABLE_SUFFIXES:
            tem_leitor = extractor._reader_for(suffix) is not None
            assert tem_leitor or suffix in IMAGE_EXTENSIONS, suffix

    @pytest.mark.parametrize("suffix", [".zip", ".docx", ".ofx", ".eml", ".7z", ""])
    def test_formato_sem_leitor_fica_fora(self, suffix) -> None:
        assert suffix not in READABLE_SUFFIXES
        assert DocumentTextExtractor()._reader_for(suffix) is None


class TestE0RecusaFormatoSemLeitor:
    def _route(self, tmp_path: Path, nome: str, conteudo: bytes = b"x" * 5000):
        from scripts.route_documents import route_file

        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        doc = inbox / nome
        doc.write_bytes(conteudo)
        return route_file(doc, tmp_path, dry_run=True, use_llm=False)

    @pytest.mark.parametrize("nome", ["extrato.zip", "carta.docx", "movimento.ofx", "semext"])
    def test_recusa_na_entrada_com_motivo_nomeado(self, tmp_path: Path, nome) -> None:
        resultado = self._route(tmp_path, nome)

        assert resultado["status"] == "unreadable_format"
        assert resultado["dest"] == "(inbox)"
        assert "nenhum extrator" in resultado["reason"]
        assert resultado["file"] == nome

    def test_formato_legivel_nao_e_recusado_por_este_gate(self, tmp_path: Path) -> None:
        """O gate não pode engolir o corpus — só recusa o que ninguém lê."""
        resultado = self._route(tmp_path, "extrato.csv", b"data,valor\n2026-01-01,10\n")

        assert resultado["status"] != "unreadable_format"

    def test_integridade_vem_antes_do_formato(self, tmp_path: Path) -> None:
        """Arquivo minúsculo continua `skipped`; as duas classes não se fundem."""
        resultado = self._route(tmp_path, "vazio.pdf", b"")

        assert resultado["status"] == "skipped"


class TestDenominadorEnumerado:
    def test_conjuntos_sao_disjuntos(self) -> None:
        assert not (FAN_OUT_STAGES_TYPED_READER & FAN_OUT_STAGES_UNTYPED_READER)

    def test_todo_stage_declarado_existe(self) -> None:
        assert not [s for s in FAN_OUT_STAGES if s not in STAGE_REGISTRY]

    def test_extract_with_llm_e_o_unico_tipado_hoje(self) -> None:
        """A ADR-393 §D2 declara os outros seis como cegos — mover, nunca deletar."""
        assert FAN_OUT_STAGES_TYPED_READER == {"extract_with_llm"}
        assert len(FAN_OUT_STAGES_UNTYPED_READER) == 6

    def test_gate_passa_no_repo_de_hoje(self) -> None:
        r = subprocess.run(
            [sys.executable, str(REPO / "dev" / "check_fan_out_reader_contract.py")],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stdout + r.stderr
