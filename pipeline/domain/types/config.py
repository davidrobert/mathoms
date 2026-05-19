"""Tipos retornados pelo ``ConfigStore`` (ADR-134) — frozen dataclasses cross-boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class CategoryDef:
    """Definição canônica de uma categoria do plano de contas."""

    code: str
    name: str
    keywords: tuple[str, ...] = ()
    monthly_cap_cents: int | None = None


@dataclass(frozen=True)
class CategorizationConfig:
    """Taxonomia + keywords usados pelo categorizador (E4)."""

    categories: Mapping[str, CategoryDef]
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FamilyMemberRecord:
    """Membro da família — ``cpf`` pode vir redacted."""

    key: str
    full_name: str
    short_name: str
    role: str
    cpf: str | None = None
    birth_date: str | None = None
    extra: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TransferInternalConfig:
    """Padrões e recipients do ``InternalTransferDetector`` (ADR-133)."""

    recipients: tuple[str, ...] = ()
    patterns_pix: tuple[str, ...] = ()
    patterns_global: tuple[str, ...] = ()
    patterns_bank_specific: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class BankAccountRecord:
    """Conta bancária declarada por membro (ADR-226 §2)."""

    member_key: str
    institution_code: str
    account_type: str
    account_number_norm: str | None = None
    account_number_raw: str | None = None
    agency: str | None = None
    is_joint: bool = False
    co_titulares: tuple[str, ...] = ()


@dataclass(frozen=True)
class FamilyMembersConfig:
    """Membros + accounts + bank_to_member (legado) + transferências + meta."""

    members: tuple[FamilyMemberRecord, ...]
    bank_to_member: Mapping[str, str] = field(default_factory=dict)
    accounts: tuple[BankAccountRecord, ...] = ()
    family_surname: str | None = None
    transfers: TransferInternalConfig | None = None


@dataclass(frozen=True)
class InstitutionDef:
    """Catálogo de instituição financeira."""

    code: str
    name: str
    parser: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class InstitutionsCatalog:
    """Catálogo global; subset consumido por workspace vem de ``BankAccount`` rows."""

    institutions: Mapping[str, InstitutionDef]


@dataclass(frozen=True)
class ReportLayout:
    """Layout do relatório — estrutura interna é codegen-bound (opaca aqui)."""

    sections: tuple[Mapping[str, object], ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TransferConfig:
    """Wrapper de ``TransferInternalConfig`` para a key dedicada do Protocol."""

    config: TransferInternalConfig


@dataclass(frozen=True)
class IRPFBracket:
    """Faixa progressiva da tabela IRPF; ``upper_brl_cents=None`` é a terminal."""

    upper_brl_cents: int | None
    aliquota_pct: Decimal
    deducao_brl_cents: int


@dataclass(frozen=True)
class FiscalParameters:
    """Parâmetros fiscais vigentes em um período (stub A7.2b — ADR-135)."""

    year: int
    pgbl_limit_brl_cents: int = 0
    inss_ceiling_brl_cents: int = 0
    lucro_presumido_aliquota: Decimal = Decimal("0")
    ir_brackets: tuple[IRPFBracket, ...] = ()
    effective_from: date | None = None
    effective_to: date | None = None
    source: str = ""


@dataclass(frozen=True)
class MarketRate:
    """Cotação observada (stub A7.2b — ADR-135)."""

    pair: str
    rate: Decimal
    observed_at: date
    source: str = ""
