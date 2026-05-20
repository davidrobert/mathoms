"""Testes do use case ``get_irpf_suggestions`` + ``dismiss_irpf_suggestion`` (ADR-229)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import pytest

from backend.app.application.family_member import (
    IrpfArtifactPayload,
    dismiss_irpf_suggestion,
    get_irpf_suggestions,
)
from backend.app.schemas.dto.family_member import IrpfDismissCommand
from backend.tests.fakes import FakeFamilyMemberRepository


@dataclass
class _FakeIrpfSource:
    """Stub do ``IrpfArtifactSourceProtocol``."""

    payload: Optional[IrpfArtifactPayload] = None

    async def get_latest(self, workspace_id: str) -> Optional[IrpfArtifactPayload]:
        return self.payload


@dataclass
class _FakeLabels:
    mapping: dict[str, str]

    async def resolve(self, codes: list[str]) -> dict[str, str]:
        return {c: self.mapping[c] for c in codes if c in self.mapping}


def _payload(*contas_dicts: dict[str, Any], year: int = 2024) -> IrpfArtifactPayload:
    return IrpfArtifactPayload(
        irpf_year=year,
        processed_at=datetime(year + 1, 4, 15, tzinfo=timezone.utc),
        contas=list(contas_dicts),
        membros={
            "david": {"nome_completo": "David Robert", "papel": "titular", "cpf": "12345678901"},
            "mariana": {"nome_completo": "Mariana Silva", "papel": "conjuge", "cpf": "98765432100"},
        },
    )


def _conta(
    *,
    member_key: str = "david",
    institution_code: str = "itau",
    account_number_norm: Optional[str] = "123456",
    account_number_raw: Optional[str] = "12345-6",
    account_type: str = "corrente",
) -> dict[str, Any]:
    return {
        "member_key": member_key,
        "institution_code": institution_code,
        "account_type": account_type,
        "account_number_raw": account_number_raw,
        "account_number_norm": account_number_norm,
        "agency": "1234",
        "is_joint": False,
        "co_titulares": [],
    }


async def _seed_member(repo: FakeFamilyMemberRepository, workspace_id: str, key: str) -> str:
    """Cria membro mínimo e retorna o id."""
    m = await repo.create(
        workspace_id,
        key=key,
        full_name=key.capitalize() + " Test",
        short_name=key.capitalize(),
        role="titular" if key == "david" else "conjuge",
    )
    return m.id


@pytest.mark.asyncio
async def test_no_artifact_returns_empty_response():
    repo = FakeFamilyMemberRepository()
    response = await get_irpf_suggestions(
        "ws-1",
        repo=repo,
        irpf_source=_FakeIrpfSource(payload=None),
        institution_labels=_FakeLabels(mapping={}),
    )
    assert response.suggestions == []
    assert response.irpf_year == 0
    assert response.total_filtered_exact_match == 0
    assert response.total_dismissed == 0


@pytest.mark.asyncio
async def test_all_new_when_no_existing_accounts():
    repo = FakeFamilyMemberRepository()
    await _seed_member(repo, "ws-1", "david")
    payload = _payload(
        _conta(member_key="david", institution_code="itau", account_number_norm="123456"),
        _conta(member_key="david", institution_code="c6bank", account_number_norm="789012"),
    )
    response = await get_irpf_suggestions(
        "ws-1",
        repo=repo,
        irpf_source=_FakeIrpfSource(payload=payload),
        institution_labels=_FakeLabels(mapping={"itau": "Itaú", "c6bank": "C6 Bank"}),
    )
    assert len(response.suggestions) == 2
    assert all(s.match_kind == "new" for s in response.suggestions)
    assert {s.institution_label for s in response.suggestions} == {"Itaú", "C6 Bank"}
    assert response.suggestions[0].cpf_titular_masked == "***.456.789-**"


@pytest.mark.asyncio
async def test_all_partial_collision_when_existing_account_has_different_number():
    repo = FakeFamilyMemberRepository()
    member_id = await _seed_member(repo, "ws-1", "david")
    # cadastro existente com número diferente (99999) → sugestão IRPF (123456) vira partial
    await _seed_account(repo, member_id, "ws-1", "itau", "99999-9")
    payload = _payload(_conta(institution_code="itau", account_number_norm="123456"))
    response = await get_irpf_suggestions(
        "ws-1",
        repo=repo,
        irpf_source=_FakeIrpfSource(payload=payload),
        institution_labels=_FakeLabels(mapping={"itau": "Itaú"}),
    )
    assert len(response.suggestions) == 1
    assert response.suggestions[0].match_kind == "partial_collision"
    assert response.suggestions[0].collision_with_account_id is not None


@pytest.mark.asyncio
async def test_all_dismissed_filtered_out():
    repo = FakeFamilyMemberRepository()
    await _seed_member(repo, "ws-1", "david")
    await repo.add_irpf_dismissal(
        workspace_id="ws-1",
        irpf_year=2024,
        institution_code="itau",
        account_number_norm="123456",
    )
    payload = _payload(_conta(institution_code="itau", account_number_norm="123456"))
    response = await get_irpf_suggestions(
        "ws-1",
        repo=repo,
        irpf_source=_FakeIrpfSource(payload=payload),
        institution_labels=_FakeLabels(mapping={"itau": "Itaú"}),
    )
    assert response.suggestions == []
    assert response.total_dismissed == 1


async def _seed_account(repo, member_id, ws, inst, num):
    await repo.add_account(
        member_id,
        workspace_id=ws,
        institution_code=inst,
        account_type="corrente",
        account_number=num,
    )


async def _seed_mix_scenario(repo):
    david_id = await _seed_member(repo, "ws-1", "david")
    await _seed_member(repo, "ws-1", "mariana")
    await _seed_account(repo, david_id, "ws-1", "itau", "11111-1")  # exact match
    await _seed_account(repo, david_id, "ws-1", "c6bank", "99999-9")  # partial
    await repo.add_irpf_dismissal(
        workspace_id="ws-1",
        irpf_year=2024,
        institution_code="bradesco",
        account_number_norm="222222",
    )


@pytest.mark.asyncio
async def test_mix_new_partial_exact_dismissed():
    repo = FakeFamilyMemberRepository()
    await _seed_mix_scenario(repo)
    payload = _payload(
        _conta(member_key="david", institution_code="itau", account_number_norm="111111"),
        _conta(member_key="david", institution_code="c6bank", account_number_norm="123123"),
        _conta(member_key="david", institution_code="bradesco", account_number_norm="222222"),
        _conta(member_key="mariana", institution_code="nubank", account_number_norm="333333"),
    )
    labels = _FakeLabels(mapping={"itau": "I", "c6bank": "C", "bradesco": "B", "nubank": "N"})
    response = await get_irpf_suggestions(
        "ws-1", repo=repo, irpf_source=_FakeIrpfSource(payload=payload), institution_labels=labels
    )
    assert len(response.suggestions) == 2
    kinds = {s.institution_code: s.match_kind for s in response.suggestions}
    assert kinds == {"c6bank": "partial_collision", "nubank": "new"}
    assert response.total_filtered_exact_match == 1
    assert response.total_dismissed == 1


@pytest.mark.asyncio
async def test_re_upload_same_irpf_does_not_duplicate_suggestions():
    """Idempotência: chamar 2× com mesmo payload retorna mesmas N sugestões (não 2N)."""
    repo = FakeFamilyMemberRepository()
    await _seed_member(repo, "ws-1", "david")
    payload = _payload(_conta(institution_code="itau", account_number_norm="123456"))
    src = _FakeIrpfSource(payload=payload)
    labels = _FakeLabels(mapping={"itau": "Itaú"})
    r1 = await get_irpf_suggestions("ws-1", repo=repo, irpf_source=src, institution_labels=labels)
    r2 = await get_irpf_suggestions("ws-1", repo=repo, irpf_source=src, institution_labels=labels)
    assert len(r1.suggestions) == 1
    assert len(r2.suggestions) == 1


@pytest.mark.asyncio
async def test_dismissal_is_idempotent_on_resubmit():
    repo = FakeFamilyMemberRepository()
    cmd = IrpfDismissCommand(
        irpf_year=2024,
        institution_code="itau",
        account_number_norm="123456",
        member_key="david",
    )
    await dismiss_irpf_suggestion(cmd, workspace_id="ws-1", repo=repo)
    await dismiss_irpf_suggestion(cmd, workspace_id="ws-1", repo=repo)
    dismissals = await repo.list_irpf_dismissals("ws-1")
    assert len(dismissals) == 1


@pytest.mark.asyncio
async def test_dismissal_of_different_year_does_not_filter_other_year():
    """Dismissal 2024 não ressuscita em payload 2025 — UNIQUE inclui irpf_year."""
    repo = FakeFamilyMemberRepository()
    await _seed_member(repo, "ws-1", "david")
    await repo.add_irpf_dismissal(
        workspace_id="ws-1", irpf_year=2024, institution_code="itau", account_number_norm="123456"
    )
    payload = _payload(_conta(institution_code="itau", account_number_norm="123456"), year=2025)
    response = await get_irpf_suggestions(
        "ws-1",
        repo=repo,
        irpf_source=_FakeIrpfSource(payload=payload),
        institution_labels=_FakeLabels(mapping={"itau": "Itaú"}),
    )
    assert len(response.suggestions) == 1
    assert response.suggestions[0].irpf_year == 2025
    assert response.total_dismissed == 0


@pytest.mark.asyncio
async def test_institution_label_falls_back_to_code_when_catalog_missing():
    repo = FakeFamilyMemberRepository()
    await _seed_member(repo, "ws-1", "david")
    payload = _payload(_conta(institution_code="banco_desconhecido", account_number_norm="123"))
    response = await get_irpf_suggestions(
        "ws-1",
        repo=repo,
        irpf_source=_FakeIrpfSource(payload=payload),
        institution_labels=_FakeLabels(mapping={}),
    )
    assert response.suggestions[0].institution_label == "banco_desconhecido"


@pytest.mark.asyncio
async def test_account_without_number_in_artifact_is_emitted():
    repo = FakeFamilyMemberRepository()
    await _seed_member(repo, "ws-1", "david")
    payload = _payload(
        _conta(
            institution_code="nubank",
            account_number_raw=None,
            account_number_norm=None,
        )
    )
    response = await get_irpf_suggestions(
        "ws-1",
        repo=repo,
        irpf_source=_FakeIrpfSource(payload=payload),
        institution_labels=_FakeLabels(mapping={"nubank": "Nubank"}),
    )
    assert len(response.suggestions) == 1
    assert response.suggestions[0].account_number_norm is None
