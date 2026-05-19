"""ADR-226 PR3 §5 — E1 ``_output_to_family_members_json`` gera `contas[]` aditivo."""

from dataclasses import dataclass
from typing import Optional

from pipeline.stages.extract_members import _output_to_family_members_json


@dataclass
class _FakeAccount:
    institution_code: str
    account_type: str = "extratoconta"
    account_number: Optional[str] = None
    agency: Optional[str] = None


@dataclass
class _FakeMember:
    key: str
    full_name: str
    short_name: str
    role: str
    accounts: list
    cpf: Optional[str] = None
    birth_date: Optional[str] = None


@dataclass
class _FakeOutput:
    members: list
    titular_key: str


def test_e1_output_includes_contas_array() -> None:
    david = _FakeMember(
        key="david",
        full_name="David",
        short_name="D",
        role="titular",
        accounts=[_FakeAccount(institution_code="itau", account_number="12345-6", agency="1234")],
    )
    mariana = _FakeMember(
        key="mariana",
        full_name="Mariana",
        short_name="M",
        role="conjuge",
        accounts=[_FakeAccount(institution_code="itau", account_number="78901-2", agency="1234")],
    )
    output = _FakeOutput(members=[david, mariana], titular_key="david")

    result = _output_to_family_members_json(output)

    assert "contas" in result
    assert len(result["contas"]) == 2

    by_member = {c["member_key"]: c for c in result["contas"]}
    assert by_member["david"]["account_number_norm"] == "123456"
    assert by_member["mariana"]["account_number_norm"] == "789012"

    # banco_membro legado preservado (colide em itau — bug latente, mas contas[] resolve)
    assert result["banco_membro"]["itau"] in {"david", "mariana"}


def test_e1_output_without_accounts_skips_contas() -> None:
    member = _FakeMember(key="solo", full_name="Solo", short_name="S", role="titular", accounts=[])
    output = _FakeOutput(members=[member], titular_key="solo")
    result = _output_to_family_members_json(output)
    assert "contas" not in result
