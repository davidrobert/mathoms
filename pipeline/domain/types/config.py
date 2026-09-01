"""Tipos retornados pelo ``ConfigStore`` (ADR-134) — frozen dataclasses cross-boundary."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal, Mapping


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


_logger = logging.getLogger("mathoms.config_types")

# `curada` = row de bank_accounts (clique humano / import) — tier 5 editorial
# (ADR-146), vence sempre. `irpf_hint` = conta do artefato E1 extraída por LLM —
# tier 1, não é fato declarado. A distinção é pré-condição do fix E1→E4: fechado
# o wiring, `fallback_bank` sustenta quase toda a atribuição, e sem carregar a
# origem o relatório afirmaria titularidade inferida com o peso da declarada
# (ADR-430 §3; ADR-394 fato ≠ hint).
AccountOrigem = Literal["curada", "irpf_hint"]
"""De onde veio a conta (ADR-430 §2)."""


def coerce_account_origem(raw: object) -> AccountOrigem:
    """Normaliza ``origem`` vinda de blob externo, degradando para ``curada``."""
    # Não levanta: family_members.json também chega de import de config do
    # usuário (backend/app/api/config.py), e derrubar o run por um campo
    # cosmético trocaria precisão por indisponibilidade (ADR-430 §Alternativas).
    if raw == "irpf_hint":
        return "irpf_hint"
    if raw not in (None, "", "curada"):
        _logger.warning(
            "account_origem.desconhecida",
            extra={"event": "account_origem.desconhecida", "valor": repr(raw)},
        )
    return "curada"


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
    origem: AccountOrigem = "curada"


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


# O redutor da Lei 15.270/2025 NÃO cabe em `ir_brackets`: a tabela progressiva
# indexa a BASE de cálculo e o redutor indexa o rendimento BRUTO ([[ADR-414]] D1).
# São duas publicações com vigências distintas — a mensal vale de 01/01/2026, a
# anual só a partir do exercício 2027 (AC2026) — e AC <= 2025 tem redutor ZERO nas
# duas. Sem esse eixo o PR3 desarmaria o D5 para 2024/2025, hoje correto.
@dataclass(frozen=True)
class RedutorIRPF:
    """Redutor do imposto apurado, função do rendimento bruto ([[ADR-414]] D3)."""

    # Banda 1 (bruto <= piso): redutor = todo o imposto apurado.
    # Banda 2 (até o teto): `intercepto − coeficiente × bruto`. Acima: zero.
    # O art. 11-A limita a redução ao imposto apurado, então o efetivo é sempre
    # `min(redutor, IR)` — clamp POR LADO, e é ele que produz a não-linearidade.

    piso_bruto_brl_cents: int = 0
    teto_bruto_brl_cents: int = 0
    intercepto_brl_cents: int = 0
    # Reais por real de rendimento. `Decimal` porque compõe valor monetário.
    coeficiente: Decimal = Decimal("0")
    vigencia_ref: str = ""
    source: str = ""

    @property
    def vigente(self) -> bool:
        """Row de ano sem redutor publica o VO zerado — não `None`, para o
        consumidor não confundir 'não existe' com 'não carregou'."""
        return self.teto_bruto_brl_cents > 0


@dataclass(frozen=True)
class FiscalParameters:
    """Parâmetros fiscais vigentes em um período (stub A7.2b — ADR-135)."""

    year: int
    pgbl_limit_brl_cents: int = 0
    inss_ceiling_brl_cents: int = 0
    lucro_presumido_aliquota: Decimal = Decimal("0")
    ir_brackets_anual: TabelaProgressiva = field(default_factory=TabelaProgressiva)
    ir_brackets_mensal: TabelaProgressiva = field(default_factory=TabelaProgressiva)
    # ADR-414 D3: co-localizados na row porque `regime_completo` afirma sobre ELA.
    # Em tabela própria, virar `true` seria afirmação sobre outra tabela com outra
    # vigência — a row mentiria sobre si mesma sempre que o ano faltasse lá.
    redutor_anual: RedutorIRPF = field(default_factory=RedutorIRPF)
    redutor_mensal: RedutorIRPF = field(default_factory=RedutorIRPF)
    # Piso do IRPFM (art. 16-A). `0` = ano sem imposto mínimo — a vigência vem do
    # DADO, não de `if year >= 2026`, mesma política do redutor ([[ADR-414]] D5).
    irpfm_limiar_brl_cents: int = 0
    # Não existe row de `fiscal_parameters` para o ano. Distinto de
    # `regime_completo=False`, que é uma AFIRMAÇÃO sobre um regime conhecido:
    # aqui não se conhece nada. Sem este campo, ausência virava o dict legado e
    # o consumidor não tinha como perceber ([[A40.l79]]).
    tabela_ausente: bool = False
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
