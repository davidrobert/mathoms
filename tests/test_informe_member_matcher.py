"""Matcher determinístico documento→membro por CPF (ADR-259 §2 · A20.l15)."""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.domain.services.informe_member_matcher import (
    extract_document_cpfs,
    resolve_member_key_by_cpf,
)


@dataclass
class _Member:
    key: str
    cpf: str | None


# Placeholders LGPD-safe (allowlist do lint_no_real_pii).
_CPF_A = "12345678909"
_CPF_ZEROS = "00000000000"


def test_extract_cpfs_com_e_sem_mascara() -> None:
    text = "Contribuinte: 123.456.789-09 · Conta: 00000000000"
    assert extract_document_cpfs(text) == {_CPF_A, _CPF_ZEROS}


def test_extract_cpfs_ignora_sequencias_maiores() -> None:
    # 12+ dígitos contíguos não são CPF (ex.: nosso número de boleto).
    assert extract_document_cpfs("boleto 123456789091234") == set()


def test_resolve_member_unico_match() -> None:
    members = [_Member("ana", _CPF_A), _Member("bruno", _CPF_ZEROS)]
    assert resolve_member_key_by_cpf("Locador CPF 123.456.789-09", members) == "ana"


def test_resolve_member_ambiguo_degrada_para_none() -> None:
    """IRPF conjunta traz CPF de 2 membros — atribuição errada é pior que ausente."""
    members = [_Member("ana", _CPF_A), _Member("bruno", _CPF_ZEROS)]
    text = "Titular 123.456.789-09 e conjuge 000.000.000-00"
    assert resolve_member_key_by_cpf(text, members) is None


def test_resolve_member_sem_cpf_no_doc() -> None:
    members = [_Member("ana", _CPF_A)]
    assert resolve_member_key_by_cpf("informe sem identificadores", members) is None


def test_resolve_member_config_sem_cpf() -> None:
    members = [_Member("ana", None), _Member("bruno", "")]
    assert resolve_member_key_by_cpf("CPF 123.456.789-09", members) is None
