"""ADR-399 — boundary de `review_reasons`: normalização de TIPO e largura.

Puro-Python, sem DB de propósito: as larguras vêm de `__table__` e o SQLite
ignora `VARCHAR(n)`. Afirmar comprimento com teste SQLite seria falso-verde
documentado (RV6-11); aqui a prova é estática e vale para qualquer dialeto.
"""

from __future__ import annotations

from backend.app.models.review_reason import ReviewReason
from backend.app.services.diagnostics.review_reason_boundary import (
    ReviewReasonRow,
    sanitize_review_reasons,
)

_STAGE = "reconcile_transactions"


def _one(**over):
    base = {"code": "domain.balance_gap", "artifact_key": "abc123def456_x", "occurrence_count": 1}
    base.update(over)
    return sanitize_review_reasons([base], stage_name=_STAGE)


class TestTipo:
    def test_dict_em_campo_de_texto_vira_str(self):
        assert isinstance(_one(offending_value={"a": 1})[0]["offending_value"], str)

    def test_occurrence_nao_numerico_vira_um(self):
        assert _one(occurrence_count="muitas")[0]["occurrence_count"] == 1

    def test_occurrence_negativo_vira_um(self):
        assert _one(occurrence_count=-5)[0]["occurrence_count"] == 1

    def test_occurrence_numerico_em_string_e_respeitado(self):
        assert _one(occurrence_count="7")[0]["occurrence_count"] == 7

    def test_entrada_nao_dict_e_descartada(self):
        assert sanitize_review_reasons(["texto"], stage_name=_STAGE) == []

    def test_raw_nao_lista_e_descartado(self):
        assert sanitize_review_reasons({"code": "x"}, stage_name=_STAGE) == []

    def test_sem_code_e_descartado(self):
        assert sanitize_review_reasons([{"message": "m"}], stage_name=_STAGE) == []


class TestLargura:
    def test_artifact_key_trunca_preservando_a_cabeca(self):
        limit = ReviewReason.__table__.c.artifact_key.type.length
        row = _one(artifact_key="abc123def456_" + "k" * 500)[0]
        assert len(row["artifact_key"]) <= limit
        assert row["artifact_key"].startswith("abc123def456_")

    def test_texto_livre_tem_teto_sanitario(self):
        row = _one(message="m" * 50_000)[0]
        assert len(row["message"]) <= 4096

    def test_stage_vem_do_orquestrador(self):
        assert _one(stage="s" * 400)[0]["stage"] == _STAGE

    def test_document_id_largo_demais_vira_none(self):
        assert _one(document_id="x" * 200)[0]["document_id"] is None


class TestIdempotencia:
    def test_normalizar_duas_vezes_da_o_mesmo(self):
        """O sink re-sanitiza para ser seguro standalone — não pode divergir
        do que o orquestrador já normalizou."""
        once = _one(offending_value={"a": 1}, artifact_key="k" * 500)
        twice = sanitize_review_reasons(once, stage_name=_STAGE)
        assert once == twice


class TestRedacao:
    def test_texto_coagido_passa_por_redact_pii(self):
        """Payload cru não passou pelo `__post_init__` da dataclass do domínio."""
        row = _one(offending_value={"cpf": "123.456.789-01"})[0]
        assert "123.456.789-01" not in row["offending_value"]


class TestContrato:
    def test_dto_e_imutavel(self):
        row = ReviewReasonRow(code="c", stage=_STAGE)
        try:
            row.code = "outro"
        except Exception:
            return
        raise AssertionError("ReviewReasonRow deveria ser frozen")
