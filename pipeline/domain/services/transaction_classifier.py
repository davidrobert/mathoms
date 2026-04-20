"""TransactionClassifier — classifica transações E3 em receitas/despesas/transferências
(Sessão A4a · Fase 7 foundation).

Decompõe ``process_transactions`` (``e4_categorize.py:589-730``) em um domain
service puro, compondo os services já extraídos nas sessões anteriores:

- :class:`KeywordMatcher` (A4a) — matching de expense/income keywords com
  wildcards e longest-match.
- :class:`InternalTransferDetector` (A3a) — detecção em 4 camadas de
  transferências internas.
- :class:`IncomeOriginResolver` (A3a) — resolve origem (PJ/CLT/Aluguel/etc.).

Responsabilidades do classifier:

1. Normalização de `tipo` (crédito/débito) — strip de acento + inferência por
   sinal do valor quando ausente (paridade com ``e4_categorize`` v5.1/v5.2).
2. Coerção de `valor` string → float quando aplicável.
3. Roteamento:
   - `tipo == "credito"` → receita (categorizada por ``INCOME_KEYWORDS``,
     fallback ``"outras_receitas"``), com origem via :class:`IncomeOriginResolver`.
   - `tipo == "debito"` → despesa (categorizada por ``EXPENSE_KEYWORDS``,
     fallback ``"nao_identificado"``), a menos que seja transferência interna.
4. Detecção de transferência interna (cobre também faturas: crédito com
   descrição de transferência).

Zero I/O. Recebe value objects de config tipados (R9/ISP). Integra no
``E4CategorizerAdapter`` que lê/escreve via ``ArtifactStore``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

from pipeline.domain.services.income_origin_resolver import (
    IncomeOriginConfig,
    IncomeOriginResolver,
)
from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferConfig,
    InternalTransferDetector,
)
from pipeline.domain.services.keyword_matcher import KeywordMatcher


# =============================================================================
# Helpers
# =============================================================================


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    t = str(text).upper().strip()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", t)
    return t


def _coerce_valor(raw) -> float:
    """Converte ``valor`` para ``float``. Aceita BR string ``"1.234,56"``.

    Paridade com ``e4_categorize.process_transactions`` (linha 618-623).
    Valores não-numéricos retornam ``0.0``.
    """
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            # BR: remove thousands separator and swap decimal comma.
            s = raw.strip().replace(".", "").replace(",", ".")
            return float(s)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def _normalize_tipo(tipo_raw, valor: float, tipo_conta: str) -> str | None:
    """Normaliza ``tipo`` → ``"credito"`` / ``"debito"`` / ``None``.

    - Strip de acento + lowercase (``"crédito"`` → ``"credito"``).
    - Inferência por sinal quando ausente: em conta (não fatura), positivo =
      crédito, negativo = débito. Em fatura, negativo = crédito (estorno); o
      caso normal (valor positivo sem tipo) permanece ``None`` — será tratado
      como débito no roteador de classificação.

    Paridade com ``e4_categorize`` linhas 624-635.
    """
    if tipo_raw is not None:
        return _normalize_text(tipo_raw).lower()

    if valor is None:
        return None

    is_fatura = tipo_conta.startswith("fatura")
    if not is_fatura:
        return "credito" if valor > 0 else "debito"
    if valor < 0:
        return "credito"
    return None  # fatura com valor positivo sem tipo → caller trata como débito


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class ClassifierConfig:
    """Value object de config do ``TransactionClassifier`` (R9/ISP).

    Compõe configs de 3 services + regras de keywords. Usa ``frozen=True``
    para garantir imutabilidade; recebe via ``from_configs`` que lê os JSONs.
    """

    expense_keywords: dict[str, list[str]] = field(default_factory=dict)
    income_keywords: dict[str, list[str]] = field(default_factory=dict)
    transfer_config: InternalTransferConfig = field(
        default_factory=InternalTransferConfig
    )
    origin_config: IncomeOriginConfig = field(default_factory=IncomeOriginConfig)
    # Fallback de categoria quando keyword não bate (paridade com e4_categorize
    # v4.8/#3.2): receitas → "outras_receitas"; despesas → "nao_identificado".
    default_income_category: str = "outras_receitas"
    default_expense_category: str = "nao_identificado"

    @classmethod
    def from_configs(
        cls,
        *,
        categorization: dict | None = None,
        family: dict | None = None,
    ) -> "ClassifierConfig":
        """Constrói a partir dos dicts ``categorization.json`` e
        ``family_members.json``. Equivalente ao ``_init_config`` do legado."""
        cat = categorization or {}
        fam = family or {}

        # Internal transfer config combina categorization + family (legado
        # linhas 74-79 faz exatamente isso).
        transfers = fam.get("transferencias_internas", {}) or {}
        combined_cat = {
            "internal_transfer_patterns": list(
                cat.get("internal_transfer_patterns") or []
            )
            + list(transfers.get("patterns_pix") or []),
            "internal_transfer_recipients": list(transfers.get("recipients") or []),
            "bank_specific_transfer_patterns": transfers.get(
                "patterns_bank_specific", {}
            )
            or {},
            "global_transfer_patterns": list(transfers.get("patterns_global") or []),
        }

        return cls(
            expense_keywords=cat.get("expense_keywords") or {},
            income_keywords=cat.get("income_keywords") or {},
            transfer_config=InternalTransferConfig.from_categorization(combined_cat),
            origin_config=IncomeOriginConfig.from_categorization(cat),
        )


# =============================================================================
# Value object — saída do classifier
# =============================================================================


@dataclass(frozen=True)
class ClassifiedTransaction:
    """Transação classificada, pronta para agregação/serialização em E4.

    ``kind``: ``"receita"`` | ``"despesa"`` | ``"transferencia"``.
    ``valor``: positivo para receitas/despesas/transferências (mesmo que o
        original fosse negativo em débito) — paridade com
        ``e4_categorize.process_transactions`` linha 718 (``valor_abs``).
    """

    kind: str  # receita | despesa | transferencia
    data: str
    descricao: str
    valor: float
    banco: str
    moeda: str
    tipo_conta: str
    titular: str
    tipo: str  # credito | debito
    categoria: str | None = None  # None para transferências
    origem: str | None = None  # só em receitas

    def to_legacy_dict(self) -> dict:
        """Serializa no schema usado pelo `process_transactions` legado."""
        out: dict = {
            "data": self.data,
            "descricao": self.descricao,
            "valor": self.valor,
            "banco": self.banco,
            "tipo_conta": self.tipo_conta,
            "titular": self.titular,
            "moeda": self.moeda,
        }
        if self.kind == "transferencia":
            out["tipo"] = self.tipo
        else:
            out["categoria"] = self.categoria
            if self.kind == "receita":
                out["origem"] = self.origem
        return out


# =============================================================================
# Service
# =============================================================================


class TransactionClassifier:
    """Classifica transações E3 reconciliadas em receitas/despesas/transferências.

    Stateless (config é imutável). Reutilize a instância entre chamadas.
    """

    def __init__(self, config: ClassifierConfig) -> None:
        self._config = config
        self._expense_matcher = KeywordMatcher(config.expense_keywords)
        self._income_matcher = KeywordMatcher(config.income_keywords)
        self._transfer_detector = InternalTransferDetector(config.transfer_config)
        self._origin_resolver = IncomeOriginResolver(config.origin_config)

    # -- API --

    def classify_account(
        self, account: dict
    ) -> list[ClassifiedTransaction]:
        """Processa todas as transações de um extrato reconciliado (E3).

        Formato de entrada: dict conforme ``*-3_reconciled.json`` (``banco``,
        ``tipo_conta``, ``titular``, ``moeda``, ``transacoes``...).
        """
        if not isinstance(account, dict) or "transacoes" not in account:
            return []

        # Meta da conta (paridade com `process_transactions` v5.3 —
        # `banco_raw` preservado, `normalize_text().lower()` para matching).
        banco_raw = account.get("banco", "Unknown") or "Unknown"
        banco_norm = _normalize_text(banco_raw).lower() if banco_raw else "unknown"
        tipo_conta_raw = account.get("tipo_conta", "") or ""
        tipo_conta = (
            _normalize_text(tipo_conta_raw).lower() if tipo_conta_raw else ""
        )
        titular = account.get("titular", "") or ""
        moeda = account.get("moeda", "BRL") or "BRL"

        results: list[ClassifiedTransaction] = []
        for tx in account["transacoes"] or []:
            if not isinstance(tx, dict):
                continue
            results.append(self._classify_one(
                tx,
                banco_raw=banco_raw,
                banco_norm=banco_norm,
                tipo_conta=tipo_conta,
                tipo_conta_raw=tipo_conta_raw,
                titular=titular,
                moeda=moeda,
            ))
        return results

    def classify_all(
        self, accounts: Iterable[dict]
    ) -> list[ClassifiedTransaction]:
        """Classifica todas as transações de múltiplos extratos reconciliados."""
        out: list[ClassifiedTransaction] = []
        for acc in accounts:
            out.extend(self.classify_account(acc))
        return out

    # -- Implementação --

    def _classify_one(
        self,
        tx: dict,
        *,
        banco_raw: str,
        banco_norm: str,
        tipo_conta: str,
        tipo_conta_raw: str,
        titular: str,
        moeda: str,
    ) -> ClassifiedTransaction:
        data = tx.get("data", "")
        descricao_raw = tx.get("descricao", "")
        valor = _coerce_valor(tx.get("valor"))
        tipo = _normalize_tipo(tx.get("tipo"), valor, tipo_conta)

        # 1. Detecção precoce de transferência interna (antes de decidir
        #    receita vs despesa). Paridade com `process_transactions`
        #    linhas 640-651.
        if self._transfer_detector.is_internal_transfer(
            descricao_raw, banco=banco_raw
        ):
            return ClassifiedTransaction(
                kind="transferencia",
                data=data,
                descricao=descricao_raw,
                valor=valor,
                banco=banco_raw,
                moeda=moeda,
                tipo_conta=tipo_conta_raw,
                titular=titular,
                tipo=tipo or "debito",
            )

        # 2. Crédito → receita.
        if tipo == "credito":
            categoria = self._income_matcher.category_of(descricao_raw)
            if not categoria:
                categoria = self._config.default_income_category
            origem = self._origin_resolver.resolve_for_category(
                categoria, descricao_raw
            )
            return ClassifiedTransaction(
                kind="receita",
                data=data,
                descricao=descricao_raw,
                valor=valor,
                banco=banco_raw,
                moeda=moeda,
                tipo_conta=tipo_conta_raw,
                titular=titular,
                tipo=tipo,
                categoria=categoria,
                origem=origem,
            )

        # 3. Débito (ou fatura sem tipo) → despesa, com fallback de transferência.
        categoria_exp = self._expense_matcher.category_of(descricao_raw)
        if categoria_exp is None:
            # Segundo check de transferência interna (paridade com v5.1, linha
            # 697): algumas descrições só batem em transferência via `banco`.
            if self._transfer_detector.is_internal_transfer(
                descricao_raw, banco=banco_norm
            ):
                return ClassifiedTransaction(
                    kind="transferencia",
                    data=data,
                    descricao=descricao_raw,
                    valor=valor,
                    banco=banco_raw,
                    moeda=moeda,
                    tipo_conta=tipo_conta_raw,
                    titular=titular,
                    tipo=tipo or "debito",
                )
            categoria_exp = self._config.default_expense_category

        # `valor_abs` (despesas são positivas no output, mesmo em débitos negativos).
        valor_abs = abs(valor)
        return ClassifiedTransaction(
            kind="despesa",
            data=data,
            descricao=descricao_raw,
            valor=valor_abs,
            banco=banco_raw,
            moeda=moeda,
            tipo_conta=tipo_conta_raw,
            titular=titular,
            tipo=tipo or "debito",
            categoria=categoria_exp,
        )
