"""Testes unitários do mapper DTO do agregado FamilyMember.

Cobrem:
- ``member_to_response`` decripta CPF via vault e monta accounts
- ``birth_name`` extraído de ``extra.nome_nascimento`` (+ variações legadas)
- ``convert_global_defaults_to_responses`` neutraliza identidade
  (F6.5E.6 / BUG-004 regression gate)
- Mapper funciona sem session (pré-condição: accounts já eager-loaded).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace

from backend.app.schemas.dto.family_member.mapper import (
    convert_global_defaults_to_responses,
    member_to_response,
)


@dataclass
class _FakeVault:
    """Vault fake — decifra retornando prefixo fixo p/ confirmar chamada."""

    calls: list[str]

    def decrypt(self, ciphertext: str) -> str | None:
        self.calls.append(ciphertext)
        # CPF válido (11 dígitos) — respeita constraint max_length=14 do DTO.
        return "123.456.789-09"


def _fake_account(**overrides) -> SimpleNamespace:
    defaults = dict(
        id="acc-1",
        institution_code="itau",
        account_type="extratoconta",
        agency="0001",
        account_number="12345-6",
        label=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _fake_member(**overrides) -> SimpleNamespace:
    defaults = dict(
        id="m-1",
        key="david",
        full_name="David Robert Camargo",
        short_name="David",
        cpf_encrypted=None,
        birth_date=date(1981, 9, 5),
        role="titular",
        order=0,
        extra=None,
        accounts=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestMemberToResponse:
    def test_minimal_member_no_cpf_no_accounts(self):
        vault = _FakeVault(calls=[])
        member = _fake_member(cpf_encrypted=None, accounts=[])

        resp = member_to_response(member, vault=vault)

        assert resp.id == "m-1"
        assert resp.key == "david"
        assert resp.cpf is None
        assert resp.accounts == []
        assert resp.birth_name is None
        assert vault.calls == []  # sem CPF encriptado → não chama decrypt

    def test_cpf_is_decrypted_via_vault(self):
        vault = _FakeVault(calls=[])
        member = _fake_member(cpf_encrypted="gAAAA...ciphered")

        resp = member_to_response(member, vault=vault)

        # CPF plain veio do fake vault; ver _FakeVault.decrypt.
        assert resp.cpf == "123.456.789-09"
        assert vault.calls == ["gAAAA...ciphered"]

    def test_birth_name_extracted_from_extra(self):
        vault = _FakeVault(calls=[])
        member = _fake_member(extra={"nome_nascimento": "Maria Solteira"})

        resp = member_to_response(member, vault=vault)

        assert resp.birth_name == "Maria Solteira"

    def test_birth_name_legacy_aliases(self):
        """Aceita ``nome_solteiro`` e ``nome_solteira`` como fallback."""
        vault = _FakeVault(calls=[])
        member_f = _fake_member(extra={"nome_solteira": "Maria F"})
        member_m = _fake_member(extra={"nome_solteiro": "João M"})

        assert member_to_response(member_f, vault=vault).birth_name == "Maria F"
        assert member_to_response(member_m, vault=vault).birth_name == "João M"

    def test_birth_name_empty_or_whitespace_treated_as_none(self):
        vault = _FakeVault(calls=[])
        member_empty = _fake_member(extra={"nome_nascimento": ""})
        member_ws = _fake_member(extra={"nome_nascimento": "   "})

        assert member_to_response(member_empty, vault=vault).birth_name is None
        assert member_to_response(member_ws, vault=vault).birth_name is None

    def test_accounts_are_mapped_from_eager_loaded_orm(self):
        vault = _FakeVault(calls=[])
        member = _fake_member(
            accounts=[
                _fake_account(id="a1", institution_code="itau"),
                _fake_account(id="a2", institution_code="c6bank"),
            ]
        )

        resp = member_to_response(member, vault=vault)

        assert [a.id for a in resp.accounts] == ["a1", "a2"]
        assert [a.institution_code for a in resp.accounts] == ["itau", "c6bank"]


class TestConvertGlobalDefaultsToResponses:
    """F6.5E.6 / BUG-004 regression — nunca expor identidade real via fallback."""

    def test_identity_fields_are_neutralized(self):
        founder_config = {
            "membros": {
                "david": {
                    "nome_completo": "David Robert Camargo",
                    "nome_curto": "David",
                    "data_nascimento": "1981-09-05",
                    "cpf": "000.000.000-00",
                    "papel": "titular",
                }
            }
        }

        responses = convert_global_defaults_to_responses(founder_config)

        assert len(responses) == 1
        r = responses[0]
        # key e role são preservados (estrutura, não identidade)
        assert r.key == "david"
        assert r.role == "titular"
        # identidade neutralizada
        assert r.full_name == "Titular Exemplo"
        assert r.short_name == "Titular"
        assert r.cpf is None
        assert r.birth_date is None

    def test_order_is_preserved(self):
        cfg = {
            "membros": {
                "a": {"papel": "titular"},
                "b": {"papel": "conjuge"},
                "c": {"papel": "filho"},
            }
        }

        responses = convert_global_defaults_to_responses(cfg)

        assert [r.key for r in responses] == ["a", "b", "c"]
        assert [r.order for r in responses] == [0, 1, 2]

    def test_all_roles_have_distinct_placeholders(self):
        cfg = {
            "membros": {
                "t": {"papel": "titular"},
                "c": {"papel": "conjuge"},
                "f": {"papel": "filho"},
                "d": {"papel": "dependente"},
            }
        }

        responses = convert_global_defaults_to_responses(cfg)

        names = {r.role: r.full_name for r in responses}
        assert names == {
            "titular": "Titular Exemplo",
            "conjuge": "Cônjuge Exemplo",
            "filho": "Filho Exemplo",
            "dependente": "Dependente Exemplo",
        }

    def test_empty_config_returns_empty_list(self):
        assert convert_global_defaults_to_responses({}) == []
        assert convert_global_defaults_to_responses({"membros": {}}) == []
