"""TransactionClassifier — classifica transações E3 em receitas/despesas/transferências.

Decompõe ``process_transactions`` legado em domain service puro, compondo
services já extraídos (``KeywordMatcher``, ``InternalTransferDetector``,
``IncomeOriginResolver``). Labels PJ (5 novas em A16 L2 P2 · [[ADR-236]] §D2)
ficam isoladas em :mod:`transaction_classifier_pj` para limitar tamanho deste
arquivo. Zero I/O.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

from pipeline.domain.services.categorization_service import CategorizationRulesV2
from pipeline.domain.services.income_origin_resolver import (
    IncomeOriginConfig,
    IncomeOriginResolver,
)
from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferConfig,
    InternalTransferDetector,
)
from pipeline.domain.services.keyword_matcher import KeywordMatcher
from pipeline.domain.services.llm_category_hint import (
    is_info_fiscal_anual,
    is_internal_transfer_hint,
    map_hint_to_expense_category,
    map_hint_to_income_category,
)
from pipeline.domain.services.transaction_classifier_pj import (
    PJ_LABELS,
    RUN_CONTEXT_DISABLED,
    ClassifierWarning,
    FolhaPJProxyUnavailable,
    PJLabelConfig,
    RunContext,
    build_run_context,
    normalize_pj_mapping,
    try_classify_pj_label,
)

# Re-export para retrocompat de imports (callers usavam o classifier como
# único entry-point). Manter público.
__all__ = [
    "ClassifiedTransaction",
    "ClassifierConfig",
    "ClassifierWarning",
    "FolhaPJProxyUnavailable",
    "PJ_LABELS",
    "TransactionClassifier",
]

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
    """Value object de config do ``TransactionClassifier`` (R9/ISP; frozen)."""

    expense_keywords: dict[str, list[str]] = field(default_factory=dict)
    income_keywords: dict[str, list[str]] = field(default_factory=dict)
    transfer_config: InternalTransferConfig = field(default_factory=InternalTransferConfig)
    origin_config: IncomeOriginConfig = field(default_factory=IncomeOriginConfig)
    # Fallback de categoria quando keyword não bate (paridade com e4_categorize
    # v4.8/#3.2): receitas → "outras_receitas"; despesas → "nao_identificado".
    default_income_category: str = "outras_receitas"
    default_expense_category: str = "nao_identificado"
    # ADR-186 §D5 — regras workspace-aprendidas (já ordenadas estavelmente).
    # None = workspace sem regras (paridade legado). Adapter constrói via DB.
    learned_rules_v2: CategorizationRulesV2 | None = None
    # ADR-236 §D2 — sub-config dos 5 labels PJ. Vazio = labels degradam
    # graciosamente; transaction_classifier_pj.py tem os defaults de keyword.
    pj_label_config: PJLabelConfig = field(
        default_factory=lambda: PJLabelConfig(pj_source_mapping={})
    )

    @classmethod
    def from_configs(
        cls,
        *,
        categorization: dict | None = None,
        family: dict | None = None,
    ) -> "ClassifierConfig":
        """Constrói a partir dos dicts ``categorization.json`` e ``family_members.json``."""
        cat = categorization or {}
        fam = family or {}
        transfers = fam.get("transferencias_internas", {}) or {}
        combined_cat = {
            "internal_transfer_patterns": list(cat.get("internal_transfer_patterns") or [])
            + list(transfers.get("patterns_pix") or []),
            "internal_transfer_recipients": list(transfers.get("recipients") or []),
            "bank_specific_transfer_patterns": transfers.get("patterns_bank_specific", {}) or {},
            "global_transfer_patterns": list(transfers.get("patterns_global") or []),
        }
        return cls(
            expense_keywords=cat.get("expense_keywords") or {},
            income_keywords=cat.get("income_keywords") or {},
            transfer_config=InternalTransferConfig.from_categorization(combined_cat),
            origin_config=IncomeOriginConfig.from_categorization(cat),
            pj_label_config=PJLabelConfig(
                pj_source_mapping=normalize_pj_mapping(cat.get("pj_source_mapping"))
            ),
        )


# =============================================================================
# Value object — saída do classifier
# =============================================================================


@dataclass(frozen=True)
class ClassifiedTransaction:
    """Transação classificada, pronta para agregação/serialização em E4."""

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
    learned_rule_id: str | None = None  # ADR-186 §D5 (A12.P2)
    categorization_origin: str | None = None  # ADR-242 — audit trail

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
    """Stateless classifier de transações E3 (config imutável; reutilize entre chamadas)."""

    def __init__(self, config: ClassifierConfig) -> None:
        self._config = config
        self._expense_matcher = KeywordMatcher(config.expense_keywords)
        self._income_matcher = KeywordMatcher(config.income_keywords)
        self._transfer_detector = InternalTransferDetector(config.transfer_config)
        self._origin_resolver = IncomeOriginResolver(config.origin_config)
        self._pj_label_config = config.pj_label_config

    # -- API --

    def classify_account(self, account: dict) -> list[ClassifiedTransaction]:
        """Processa transações de 1 account E3 (pre-pass `has_pj_income` no escopo deste account)."""
        run_ctx = build_run_context(
            [account],
            self._pj_label_config,
            coerce_valor=_coerce_valor,
            normalize_tipo=_normalize_tipo,
        )
        txs, _ = self._classify_account_audit(account, run_ctx=run_ctx)
        return txs

    def classify_all(self, accounts: Iterable[dict]) -> list[ClassifiedTransaction]:
        """Classifica múltiplos accounts (descarta warnings; use ``classify_all_with_warnings`` para acesso)."""
        transactions, _ = self.classify_all_with_warnings(accounts)
        return transactions

    def classify_all_with_warnings(
        self, accounts: Iterable[dict]
    ) -> tuple[list[ClassifiedTransaction], list[ClassifierWarning]]:
        """Classifica multi-account + emite warnings PJ-side ([[ADR-236]] §D2 · [[ADR-097]] D1)."""
        accounts_list = [a for a in accounts if isinstance(a, dict)]
        run_ctx = build_run_context(
            accounts_list,
            self._pj_label_config,
            coerce_valor=_coerce_valor,
            normalize_tipo=_normalize_tipo,
        )

        all_transactions: list[ClassifiedTransaction] = []
        folha_pj_candidatas: list[str] = []
        for account in accounts_list:
            txs, candidatas = self._classify_account_audit(account, run_ctx=run_ctx)
            all_transactions.extend(txs)
            folha_pj_candidatas.extend(candidatas)

        return all_transactions, _build_warnings(folha_pj_candidatas, run_ctx)

    # -- Classificação por conta --

    def _classify_account_audit(
        self, account: dict, *, run_ctx: RunContext
    ) -> tuple[list[ClassifiedTransaction], list[str]]:
        """Classifica conta + coleta candidatas a ``folha_pj`` (audit para warning)."""
        if not isinstance(account, dict) or "transacoes" not in account:
            return [], []

        banco_raw = account.get("banco", "Unknown") or "Unknown"
        banco_norm = _normalize_text(banco_raw).lower() if banco_raw else "unknown"
        tipo_conta_raw = account.get("tipo_conta", "") or ""
        tipo_conta = _normalize_text(tipo_conta_raw).lower() if tipo_conta_raw else ""
        titular = account.get("titular", "") or ""
        moeda = account.get("moeda", "BRL") or "BRL"

        results: list[ClassifiedTransaction] = []
        folha_pj_candidatas: list[str] = []
        for tx in account["transacoes"] or []:
            if not isinstance(tx, dict):
                continue
            # ADR-242 — linhas anuais de informe fiscal (valor a declarar,
            # parcelas acumuladas) NÃO entram no fluxo de caixa mensal.
            # Skipa cedo para evitar double-counting + distorção de KPIs
            # (taxa de poupança, despesa_mensal_media, etc.).
            if is_info_fiscal_anual(tx.get("categoria_sugerida")):
                continue
            classified, folha_pj_candidata = self._classify_one(
                tx,
                banco_raw=banco_raw,
                banco_norm=banco_norm,
                tipo_conta=tipo_conta,
                tipo_conta_raw=tipo_conta_raw,
                titular=titular,
                moeda=moeda,
                run_ctx=run_ctx,
            )
            results.append(classified)
            if folha_pj_candidata is not None:
                folha_pj_candidatas.append(folha_pj_candidata)
        return results, folha_pj_candidatas

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
        run_ctx: RunContext = RUN_CONTEXT_DISABLED,
    ) -> tuple[ClassifiedTransaction, str | None]:
        """Classifica uma tx; retorna ``(classified, folha_pj_candidata)``."""
        descricao_raw = tx.get("descricao", "")
        valor = _coerce_valor(tx.get("valor"))
        tipo = _normalize_tipo(tx.get("tipo"), valor, tipo_conta)
        category_hint = tx.get("categoria_sugerida")

        common = dict(
            data=tx.get("data", ""),
            descricao=descricao_raw,
            banco=banco_raw,
            moeda=moeda,
            tipo_conta=tipo_conta_raw,
            titular=titular,
        )

        # 1. Transferência interna precoce (paridade legado + hint LLM reforça).
        if self._transfer_detector.is_internal_transfer(
            descricao_raw, banco=banco_raw
        ) or is_internal_transfer_hint(category_hint):
            return _classified_transferencia(valor, tipo, **common), None

        # 2. Labels PJ ([[ADR-236]] §D2) têm precedência sobre learned + template.
        pj_label, folha_pj_candidata = try_classify_pj_label(
            descricao_raw, tipo=tipo, config=self._pj_label_config, run_ctx=run_ctx
        )
        if pj_label is not None:
            return self._make_pj(pj_label, valor, tipo, descricao_raw, common), None

        learned_match = self._learned_rules_match(descricao_raw)

        if tipo == "credito":
            return self._classify_credito(
                descricao_raw, valor, tipo, category_hint, learned_match, common
            ), None

        return self._classify_debito(
            descricao_raw, banco_norm, valor, tipo, category_hint, learned_match, common
        ), folha_pj_candidata

    def _make_pj(self, pj_label, valor, tipo, descricao_raw, common):
        kind, categoria_pj = pj_label
        origem = self._origin_resolver.resolve_pj(descricao_raw) if kind == "receita" else None
        tipo_out = tipo or ("credito" if kind == "receita" else "debito")
        valor_out = valor if kind == "receita" else abs(valor)
        return ClassifiedTransaction(
            kind=kind,
            valor=valor_out,
            tipo=tipo_out,
            categoria=categoria_pj,
            origem=origem,
            categorization_origin="pj_label",
            **common,
        )

    def _classify_credito(
        self, descricao_raw, valor, tipo, category_hint, learned_match, common
    ) -> ClassifiedTransaction:
        categoria, learned_id, origin_tag = self._resolve_categoria_receita(
            descricao_raw, category_hint, learned_match
        )
        origem = self._origin_resolver.resolve_for_category(categoria, descricao_raw)
        return ClassifiedTransaction(
            kind="receita",
            valor=valor,
            tipo=tipo,
            categoria=categoria,
            origem=origem,
            learned_rule_id=learned_id,
            categorization_origin=origin_tag,
            **common,
        )

    def _resolve_categoria_receita(self, descricao_raw, category_hint, learned_match):
        # ADR-242 hierarchy: learned > rule > llm_hint > default.
        if learned_match is not None:
            categoria, learned_id = learned_match
            return categoria, learned_id, "learned"
        categoria = self._income_matcher.category_of(descricao_raw)
        if categoria is not None:
            return categoria, None, "rule"
        hint_cat = map_hint_to_income_category(category_hint)
        if hint_cat is not None:
            return hint_cat, None, "llm_hint"
        return self._config.default_income_category, None, "default"

    def _classify_debito(
        self, descricao_raw, banco_norm, valor, tipo, category_hint, learned_match, common
    ):
        # learned > rule (early); se nenhum casa, checa transferência tardia
        # via banco_norm e só depois aplica hint LLM ou default.
        if learned_match is not None:
            categoria_exp, learned_id = learned_match
            origin_tag = "learned"
        else:
            categoria_exp = self._expense_matcher.category_of(descricao_raw)
            learned_id = None
            origin_tag = "rule" if categoria_exp is not None else "default"
        if categoria_exp is None:
            if self._transfer_detector.is_internal_transfer(descricao_raw, banco=banco_norm):
                return _classified_transferencia(valor, tipo, **common)
            hint_cat = map_hint_to_expense_category(category_hint)
            if hint_cat is not None:
                categoria_exp = hint_cat
                origin_tag = "llm_hint"
            else:
                categoria_exp = self._config.default_expense_category
        return ClassifiedTransaction(
            kind="despesa",
            valor=abs(valor),
            tipo=tipo or "debito",
            categoria=categoria_exp,
            learned_rule_id=learned_id,
            categorization_origin=origin_tag,
            **common,
        )

    # ADR-186 §D5 (A12.P2) — helper interno isolado para testabilidade.
    def _learned_rules_match(self, descricao_raw: str) -> tuple[str, str] | None:
        """Retorna ``(target_category, rule_id)`` se alguma learned_rule casa."""
        rules_v2 = self._config.learned_rules_v2
        if rules_v2 is None or not rules_v2.learned_rules:
            return None
        return rules_v2.match(descricao_raw)


# =============================================================================
# Helpers de construção (fora do classifier — funções puras)
# =============================================================================


def _classified_transferencia(valor, tipo, **common) -> ClassifiedTransaction:  # noqa: ANN001 — valor é float legacy do JSON E3, ADR-090 incidence em Money
    """Constrói uma `ClassifiedTransaction(kind=transferencia)` aproveitando kwargs comuns."""
    return ClassifiedTransaction(kind="transferencia", valor=valor, tipo=tipo or "debito", **common)


def _build_warnings(folha_pj_candidatas: list[str], run_ctx: RunContext) -> list[ClassifierWarning]:
    """Agrega candidatas de ``folha_pj`` em 1 warning quando proxy desabilitado."""
    if not folha_pj_candidatas or run_ctx.folha_pj_enabled:
        return []
    reason = "no_pj_source_mapping" if not run_ctx.pj_mapping_populated else "no_pj_income_observed"
    return [
        FolhaPJProxyUnavailable(
            reason=reason,
            candidatas_count=len(folha_pj_candidatas),
            sample_descricao=folha_pj_candidatas[0],
        )
    ]
