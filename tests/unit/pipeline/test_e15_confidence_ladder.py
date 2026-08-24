"""A40.l68 item 2b (ADR-081 · ADR-393) — ladder de confiança no E1.5."""

# O code `extract.low_confidence` existia no enum e no JSON Schema desde a
# ADR-272 e **nunca teve emissor**. O piso 0,7 é o da ADR-081; medido no corpus,
# `confidence < 0,7` ⟺ mediana de 0 itens extraídos (contra 9 acima do piso).

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from pipeline.domain.review_reason import BLOCKING_CODES, ReviewReasonCode
from pipeline.stages.extract_baseline import (
    _CONFIDENCE_FLOOR,
    _aggregate_baselines,
    _low_confidence_reason,
)


@dataclass
class _Saida:
    confidence: float | None


def _razao(conf, nome="irpfdeclaracao_2024.pdf"):
    return _low_confidence_reason(Path(nome), _Saida(conf), artifact_key="k")


class TestAusenciaNaoEZero:
    """`0.0` como sentinela de ausência é medição fabricada — o mesmo defeito
    que este plano combate um andar acima."""

    def test_sem_nenhuma_confianca_o_agregado_nao_inventa_zero(self) -> None:
        combinado = _aggregate_baselines([{"itens": [], "resumo": {}, "_meta": {}}])

        assert combinado["_meta"]["confidence"] is None

    def test_com_confianca_o_agregado_leva_a_pior(self) -> None:
        per_file = [
            {"itens": [], "resumo": {}, "_meta": {"confidence": 0.9}},
            {"itens": [], "resumo": {}, "_meta": {"confidence": 0.35}},
        ]

        assert _aggregate_baselines(per_file)["_meta"]["confidence"] == 0.35


class TestLadder:
    @pytest.mark.parametrize("conf", [0.1, 0.35, 0.62, 0.69])
    def test_abaixo_do_piso_vira_review_reason(self, conf) -> None:
        razao = _razao(conf)

        assert razao is not None
        assert razao["code"] == ReviewReasonCode.extract_low_confidence.value
        assert razao["stage"] == "extract_baseline"
        assert str(conf) in razao["offending_value"]

    @pytest.mark.parametrize("conf", [0.7, 0.75, 0.97, 1.0])
    def test_no_piso_ou_acima_nao_dispara(self, conf) -> None:
        assert _razao(conf) is None

    def test_confianca_ausente_nao_dispara(self) -> None:
        """Ausência não é confiança baixa — disparar aqui era o medo da lane."""
        assert _razao(None) is None

    def test_nomeia_o_documento(self) -> None:
        """`low_confidence: 1` sem identificador não deixa ir atrás do arquivo."""
        razao = _razao(0.3, nome="irpfdeclaracao_2023.pdf")

        assert "irpfdeclaracao_2023.pdf" in razao["message"]

    def test_e_warn_first_nao_pausa_o_run(self) -> None:
        """4 disparos por run medidos: pausa recorrente ensina a ignorar a pausa."""
        assert ReviewReasonCode.extract_low_confidence not in BLOCKING_CODES


class TestProvaPorMutacao:
    def test_piso_no_agregado_em_vez_do_arquivo_dispararia_sempre(self) -> None:
        # Medido no corpus: 172/172 agregados ficam < 0,7 — 100% dos runs —
        # mesmo quando a maioria dos arquivos extraiu bem.
        """Por que o ladder NÃO mora no agregado: `min` sobre N arquivos colapsa."""
        per_file = [
            {"itens": [], "resumo": {}, "_meta": {"confidence": c}} for c in (0.97, 0.95, 0.15)
        ]

        agregado = _aggregate_baselines(per_file)["_meta"]["confidence"]

        assert agregado < _CONFIDENCE_FLOOR
        assert sum(1 for c in (0.97, 0.95, 0.15) if c < _CONFIDENCE_FLOOR) == 1


class TestLadderNoStageDeVerdade:
    # As classes acima chamam o helper direto — provam a regra, não o elo. Este
    # roda `extract_baseline.run()` e olha o bloco `validation` que o
    # orquestrador consome, que é onde o ladder precisa aparecer para existir.
    """O ladder visto pelo bloco `validation` que o orquestrador lê."""

    def _run(self, tmp_path: Path, confidence: float):
        import sys
        from unittest.mock import patch

        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from tests._llm_stage_fixtures import make_e15_output, make_llm_call_result, make_llm_ctx

        ctx = make_llm_ctx(tmp_path)
        (tmp_path / "data" / "income_tax_br").mkdir(parents=True)
        (tmp_path / "data" / "income_tax_br" / "irpfdeclaracao_2024.pdf").write_text("x")
        saida = make_e15_output()
        saida.confidence = confidence

        with (
            patch(
                "pipeline.llm.text_extractor.DocumentTextExtractor.extract",
                return_value="IRPF 2024",
            ),
            patch("pipeline.llm.litellm_client.LLMService._ensure_client"),
            patch(
                "pipeline.llm.litellm_client.LLMService.call",
                return_value=make_llm_call_result(saida),
            ),
        ):
            from pipeline.stages.extract_baseline import run

            return run(ctx)

    def test_confianca_baixa_aparece_no_bloco_validation(self, tmp_path: Path) -> None:
        resultado = self._run(tmp_path, 0.35)

        codes = [r["code"] for r in resultado["validation"]["review_reasons"]]
        assert ReviewReasonCode.extract_low_confidence.value in codes

    def test_confianca_baixa_nao_reprova_valid_nem_quebra_o_run(self, tmp_path: Path) -> None:
        """WARN-first: entra na fila de revisão, mas o run entrega."""
        resultado = self._run(tmp_path, 0.35)

        assert resultado["success"] is True
        assert resultado["validation"]["valid"] is True
        assert resultado["validation"]["errors"] == []

    def test_confianca_alta_nao_emite(self, tmp_path: Path) -> None:
        resultado = self._run(tmp_path, 0.95)

        codes = [r["code"] for r in resultado["validation"]["review_reasons"]]
        assert ReviewReasonCode.extract_low_confidence.value not in codes
