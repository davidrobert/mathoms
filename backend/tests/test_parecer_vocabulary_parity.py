"""Paridade dos vocabulários do parecer entre suas cópias manuais (ADR-366 §Consequências)."""

# `outcome` e `retention.reason` são declarados à mão em três lugares — a Enum
# SQLAlchemy, o `Literal` do DTO e a união TS do cliente — e nada os ligava. É o
# padrão que a A40.l18 PR1 estabeleceu em `test_pipeline_status_enum_parity.py`,
# estendido de 2 para 3 cópias porque aqui existe a intermediária (o `Literal`),
# que o caso da l18 não tinha.
#
# ARMADILHA MEDIDA, e é a razão de este arquivo não ser um copy-paste: o extrator
# da l18 usa `r'"([a-z_]+)"'`, que NÃO casa o ponto de `parecer.sigilo` nem as
# maiúsculas de `Gerado`. Copiado tal-e-qual, ele devolve conjunto vazio e o gate
# fica verde comparando vazio com vazio. `test_extrator_enxerga_o_namespace`
# existe para matar exatamente essa mutação.

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, get_args

import pytest

from backend.app.models.planner_review import (
    VALID_PLANNER_REVIEW_STATUSES,
    ParecerOutcome,
    ParecerRetentionReason,
)
from backend.app.schemas.dto.planner_review import (
    PlannerReviewAbsenceDetail,
    PlannerReviewResponse,
    RetentionDetail,
)

_TS_CLIENT = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "api" / "planner-review.ts"
)


def _ts_union_members(type_name: str) -> set[str]:
    """Literais de `export type <T> = "a" | "b";` — aceita ponto e maiúscula."""
    source = re.sub(r"//[^\n]*", "", _TS_CLIENT.read_text(encoding="utf-8"))
    match = re.search(rf"export type {type_name} =(.*?);", source, re.DOTALL)
    if match is None:
        pytest.fail(f"união {type_name} não encontrada em {_TS_CLIENT}")
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def _dto_literal_members(model, field: str) -> set[str]:
    """Membros do `Literal` do DTO — por introspecção, não por regex sobre o fonte."""
    annotation = model.model_fields[field].annotation
    members = set(get_args(annotation))
    if not members:
        pytest.fail(f"{model.__name__}.{field} não é Literal — a 3ª cópia sumiu do gate")
    return members


def _absence_codes() -> set[str]:
    """Códigos de 404 que o ROUTER realmente produz (ADR-366 §D6 + emenda 2026-08-07)."""
    return set(get_args(PlannerReviewAbsenceDetail.model_fields["code"].annotation))


_VOCABULARIOS = [
    ("ParecerOutcome", {m.value for m in ParecerOutcome}, (PlannerReviewResponse, "outcome")),
    (
        "ParecerRetentionReason",
        {m.value for m in ParecerRetentionReason},
        (RetentionDetail, "reason"),
    ),
    ("PlannerReviewStatus", set(VALID_PLANNER_REVIEW_STATUSES), None),
    ("PlannerReviewAbsenceCode", _absence_codes(), (PlannerReviewAbsenceDetail, "code")),
]


@pytest.mark.parametrize(("ts_type", "python_members", "dto_field"), _VOCABULARIOS)
def test_vocabulario_bate_em_todas_as_copias(ts_type, python_members, dto_field):
    """Membro novo em qualquer cópia sem as outras duas deixa este teste vermelho."""
    assert python_members == _ts_union_members(ts_type), f"Python ↔ TS divergem em {ts_type}"
    if dto_field is not None:
        model, field = dto_field
        assert python_members == _dto_literal_members(model, field), f"Python ↔ DTO em {ts_type}"


def test_extrator_enxerga_o_namespace_e_a_maiuscula():
    """Mata a mutação de copiar o `[a-z_]+` da A40.l18: ali estes dois dão vazio."""
    assert "parecer.sigilo" in _ts_union_members("ParecerRetentionReason")
    assert "Gerado" in _ts_union_members("PlannerReviewStatus")


def test_retention_reason_e_nulo_exatamente_nos_desfechos_sem_motivo():
    """A função é TOTAL: cada membro de `outcome` decide se admite motivo (ADR-366 §D3)."""
    from backend.app.models.planner_review import OUTCOMES_WITHOUT_REASON

    com_motivo = {ParecerOutcome.entregue_com_retencao, ParecerOutcome.retido}
    assert OUTCOMES_WITHOUT_REASON | com_motivo == set(ParecerOutcome)
    assert not (OUTCOMES_WITHOUT_REASON & com_motivo)


def test_todo_motivo_da_enum_e_servivel_pelo_dto():
    """Sem membro genérico de fallback: o mapa é total, então não há ramo não-mapeado."""
    for reason in ParecerRetentionReason:
        assert RetentionDetail(reason=reason.value).reason == reason.value


def test_dto_recusa_motivo_fora_da_classe_fechada():
    """`error_detail` cru nunca vira `reason` — o boundary rejeita por tipo."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RetentionDetail(reason="evidencia unverified (severidade alta): risco:3")


def test_literal_do_dto_nao_e_str_livre():
    """Trocar o Literal por `str` passaria nos 2 acima; aqui não."""
    assert get_args(PlannerReviewResponse.model_fields["outcome"].annotation)
    assert RetentionDetail.model_fields["reason"].annotation is not str
    assert get_args(RetentionDetail.model_fields["reason"].annotation) != get_args(Literal[""])
