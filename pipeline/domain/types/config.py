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


# A mensal (IRRF na fonte) e a anual (ajuste da DAA, Anexo VII da IN RFB
# 1.500/2014) são publicações DISTINTAS — nenhuma deriva da outra.
@dataclass(frozen=True)
class TabelaProgressiva:
    """Uma das duas tabelas publicadas do IRPF, com proveniência própria ([[ADR-389]] D2)."""

    faixas: tuple[IRPFBracket, ...] = ()
    # Cabeçalho da norma verbatim ("Exercício de 2026, ano-calendário de 2025")
    # + o ato que a positiva. O `source` de row provou-se insuficiente: um único
    # texto cobria 3 anos idênticos e errados.
    vigencia_ref: str = ""
    source: str = ""
    # Exigido quando |anual − 12×mensal| passa do limiar (ADR-389 D3c). Em ano de
    # transição a divergência é estrutural (mistura ponderada por mês); em ano
    # limpo é arredondamento e este campo fica vazio.
    motivo_divergencia_x12: str = ""


@dataclass(frozen=True)
class FiscalParameters:
    """Parâmetros fiscais vigentes em um período (stub A7.2b — ADR-135)."""

    year: int
    pgbl_limit_brl_cents: int = 0
    inss_ceiling_brl_cents: int = 0
    lucro_presumido_aliquota: Decimal = Decimal("0")
    ir_brackets_anual: TabelaProgressiva = field(default_factory=TabelaProgressiva)
    ir_brackets_mensal: TabelaProgressiva = field(default_factory=TabelaProgressiva)
    # ADR-389 D4: completude do regime é DADO, para o consumidor recusar lendo a
    # row em vez de `if year >= 2026`. AC2026 nasce incompleto (redutor da Lei
    # 15.270/2025 + IRPFM não modelados — [[A40.l64]]).
    regime_completo: bool = True
    componentes_ausentes: tuple[str, ...] = ()
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
