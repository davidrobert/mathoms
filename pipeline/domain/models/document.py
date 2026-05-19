"""Documents de domínio: ``BankStatement``, ``InvestmentStatement``, ``BaselinePatrimonial``.

``BankStatement.transactions`` é ``list`` mutável — dataclass não-frozen com
invariante documentado: apenas o pipeline de reconciliação modifica a lista.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from pipeline.domain.models.transaction import Money, Transaction


@dataclass
class BankStatement:
    """Extrato bancário — output do E2 determinístico."""

    institution: str
    member_key: Optional[str]
    period_start: date
    period_end: date
    currency: str
    transactions: list[Transaction] = field(default_factory=list)
    opening_balance: Optional[Money] = None
    closing_balance: Optional[Money] = None
    source_document: Optional[str] = None
    notes: list[str] = field(default_factory=list)
    # Tipo do extrato (e.g. ``extratoconta``, ``faturacarbon``). Preserva o
    # campo ``tipo`` do dict E2 — necessário para gerar o nome de arquivo E3
    # legado (``{banco}_{tipo_conta}_...``) sem reler os dicts originais.
    # Default ``None`` para retro-compat; ``from_e2_dict`` popula quando o
    # dict de entrada tem ``tipo``.
    account_type: Optional[str] = None
    # ADR-226 PR2 — discriminador real entre 2 membros no mesmo banco.
    # ``account_number_raw`` preserva formato do extrato; ``_norm`` é
    # digits-only canônico via ``normalize_account_number``.
    account_number_raw: Optional[str] = None
    account_number_norm: Optional[str] = None

    @property
    def net_flow(self) -> Money:
        total = Money.zero(self.currency)
        for t in self.transactions:
            total = total + t.amount
        return total

    @property
    def income(self) -> Money:
        """Soma de transações positivas (créditos)."""
        total = Money.zero(self.currency)
        zero = Money.zero(self.currency)
        for t in self.transactions:
            if zero < t.amount:
                total = total + t.amount
        return total

    @property
    def expenses(self) -> Money:
        """Soma de transações negativas, retornada como positivo."""
        total = Money.zero(self.currency)
        zero = Money.zero(self.currency)
        for t in self.transactions:
            if t.amount < zero:
                total = total + (-t.amount)
        return total

    def to_dict(self) -> dict:
        return {
            "institution": self.institution,
            "member_key": self.member_key,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "currency": self.currency,
            "opening_balance": self.opening_balance.to_float() if self.opening_balance else None,
            "closing_balance": self.closing_balance.to_float() if self.closing_balance else None,
            "source_document": self.source_document,
            "notes": list(self.notes),
            "transactions": [t.to_dict() for t in self.transactions],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BankStatement":
        currency = d.get("currency", "BRL")
        return cls(
            institution=d.get("institution", ""),
            member_key=d.get("member_key"),
            period_start=date.fromisoformat(d["period_start"]),
            period_end=date.fromisoformat(d["period_end"]),
            currency=currency,
            transactions=[Transaction.from_dict(t) for t in d.get("transactions", [])],
            opening_balance=(
                Money.of(str(d["opening_balance"]), currency)
                if d.get("opening_balance") is not None
                else None
            ),
            closing_balance=(
                Money.of(str(d["closing_balance"]), currency)
                if d.get("closing_balance") is not None
                else None
            ),
            source_document=d.get("source_document"),
            notes=list(d.get("notes", [])),
        )

    # ─── Adaptador E2 (config/schemas/e2_extract.schema.json) ───
    # O schema legado do E2 usa campos em português (``banco``, ``transacoes``,
    # ``periodo_inicio``...). Este adaptador converte entre os dois formatos
    # durante a Fase 3.2 (Caminho B), enquanto os parsers de ``scripts/e2/banks/``
    # ainda retornam ``dict``. Cada parser migrado pode eliminar o adapter para
    # si mesmo (plano R10).

    @classmethod
    def from_e2_dict(cls, d: dict) -> "BankStatement":
        """Converte output legado do E2 (JSON schema em PT-BR) para ``BankStatement``."""
        currency = d.get("moeda") or d.get("currency") or "BRL"
        start = d.get("periodo_inicio") or d.get("period_start")
        end = d.get("periodo_fim") or d.get("period_end")
        period_start = date.fromisoformat(start) if start else date.today()
        period_end = date.fromisoformat(end) if end else period_start
        transactions: list[Transaction] = []
        for t in d.get("transacoes") or []:
            tx_date_raw = t.get("data") or t.get("date")
            if isinstance(tx_date_raw, str):
                tx_date = date.fromisoformat(tx_date_raw)
            elif isinstance(tx_date_raw, date):
                tx_date = tx_date_raw
            else:
                continue
            valor = t.get("valor", 0)
            transactions.append(
                Transaction(
                    date=tx_date,
                    description=str(t.get("descricao") or t.get("description") or ""),
                    amount=Money.of(str(valor), currency),
                    category=t.get("categoria") or t.get("category"),
                    member_key=t.get("membro") or t.get("member_key"),
                    source_document=d.get("arquivo_origem") or d.get("source_document"),
                )
            )
        opening = (
            d.get("saldo_inicial")
            if d.get("saldo_inicial") is not None
            else d.get("opening_balance")
        )
        closing = (
            d.get("saldo_final") if d.get("saldo_final") is not None else d.get("closing_balance")
        )
        # Lazy import — account_normalization é peer em pipeline.domain.services,
        # mas o __init__.py de services importa BankStatement (circular).
        from pipeline.domain.services.account_normalization import normalize_account_number

        account_number_raw = d.get("numero_conta") or d.get("account_number")
        account_number_norm = d.get("numero_conta_norm") or normalize_account_number(
            account_number_raw
        )
        return cls(
            institution=d.get("banco") or d.get("institution") or "",
            member_key=d.get("documento_titular") or d.get("member_key"),
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            transactions=transactions,
            opening_balance=Money.of(str(opening), currency) if opening is not None else None,
            closing_balance=Money.of(str(closing), currency) if closing is not None else None,
            source_document=d.get("arquivo_origem") or d.get("source_document"),
            notes=list(d.get("notas") or d.get("notes") or []),
            account_type=d.get("tipo") or d.get("account_type"),
            account_number_raw=account_number_raw,
            account_number_norm=account_number_norm,
        )

    def to_e2_dict(self) -> dict:
        """Serializa no formato esperado pelo schema E2 (PT-BR)."""
        return {
            "pipeline_stage": "E2",
            "banco": self.institution,
            "tipo": self.account_type or "extrato",
            "moeda": self.currency,
            "periodo_inicio": self.period_start.isoformat(),
            "periodo_fim": self.period_end.isoformat(),
            "documento_titular": self.member_key,
            "saldo_inicial": self.opening_balance.to_float() if self.opening_balance else None,
            "saldo_final": self.closing_balance.to_float() if self.closing_balance else None,
            "arquivo_origem": self.source_document,
            "notas": list(self.notes),
            "transacoes": [
                {
                    "data": t.date.isoformat(),
                    "descricao": t.description,
                    "valor": t.amount.to_float(),
                }
                for t in self.transactions
            ],
        }


@dataclass(frozen=True)
class Investment:
    """Posição de investimento — output do E2-llm (campo ``investments[]``)."""

    type: str
    institution: str
    description: str
    value_brl: Money
    member_key: Optional[str] = None
    applied_date: Optional[date] = None
    maturity_date: Optional[date] = None
    rate: Optional[str] = None
    source_document: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "tipo": self.type,
            "instituicao": self.institution,
            "descricao": self.description,
            "valor_brl": self.value_brl.to_float(),
            "membro": self.member_key,
            "data_aplicacao": self.applied_date.isoformat() if self.applied_date else None,
            "data_vencimento": self.maturity_date.isoformat() if self.maturity_date else None,
            "taxa": self.rate,
            "source_document": self.source_document,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Investment":
        return cls(
            type=d.get("tipo", ""),
            institution=d.get("instituicao", ""),
            description=d.get("descricao", ""),
            value_brl=Money.of(str(d.get("valor_brl", 0)), "BRL"),
            member_key=d.get("membro"),
            applied_date=date.fromisoformat(d["data_aplicacao"])
            if d.get("data_aplicacao")
            else None,
            maturity_date=date.fromisoformat(d["data_vencimento"])
            if d.get("data_vencimento")
            else None,
            rate=d.get("taxa"),
            source_document=d.get("source_document"),
        )


@dataclass
class InvestmentStatement:
    """Extrato de investimentos — output do E2-llm (docs sem parser determinístico)."""

    institution: str
    member_key: Optional[str]
    currency: str
    investments: list[Investment] = field(default_factory=list)
    source_document: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    @property
    def total_value(self) -> Money:
        total = Money.zero(self.currency)
        for inv in self.investments:
            total = total + inv.value_brl
        return total

    def to_dict(self) -> dict:
        return {
            "institution": self.institution,
            "member_key": self.member_key,
            "currency": self.currency,
            "investments": [i.to_dict() for i in self.investments],
            "source_document": self.source_document,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "InvestmentStatement":
        return cls(
            institution=d.get("institution", ""),
            member_key=d.get("member_key"),
            currency=d.get("currency", "BRL"),
            investments=[Investment.from_dict(i) for i in d.get("investments", [])],
            source_document=d.get("source_document"),
            notes=list(d.get("notes", [])),
        )


@dataclass(frozen=True)
class BaselinePatrimonial:
    """Baseline patrimonial consolidado (E1.5c)."""

    total_brl: Money
    members: dict[str, Money]
    reference_date: date

    def to_dict(self) -> dict:
        return {
            "total_brl": self.total_brl.to_float(),
            "members": {k: v.to_float() for k, v in self.members.items()},
            "reference_date": self.reference_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BaselinePatrimonial":
        return cls(
            total_brl=Money.of(str(d.get("total_brl", 0)), "BRL"),
            members={k: Money.of(str(v), "BRL") for k, v in (d.get("members") or {}).items()},
            reference_date=date.fromisoformat(d.get("reference_date") or date.today().isoformat()),
        )
