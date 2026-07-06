"""Ruleset curado A28.l5 — promoção em lote via learning loop (ADR-186/188).

Keywords derivadas da análise dos maiores ofensores de ``nao_identificado``
no dogfood (Sprint A28, lane l5). **PII-zero por política**: apenas nomes de
estabelecimentos públicos (redes de varejo, empresas) e descritores genéricos
de segmento em PT-BR — nunca nome de pessoa física, valor ou descrição de
transação real. A promoção reusa ``rule_management_service`` (invariantes do
loop: override manual sticky, mês fechado imutável, transferências internas
excluídas, conflito determinístico).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.application.categorization import rule_management_service
from backend.app.application.categorization._apply_engine import (
    apply_retroactive_async_safe,
    count_applied_overrides,
)
from backend.app.application.categorization.rule_management_service import (
    ApplyTooLargeError,
    RuleAlreadyExistsError,
    set_applied_count,
)
from backend.app.core.logging import get_logger
from backend.app.models.workspace import Workspace
from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferDetector,
)

logger = get_logger("categorization.curated_rules")

# Categorias expense válidas do category_template v1 (ADR-137 seed).
VALID_EXPENSE_CATEGORIES: frozenset[str] = frozenset(
    {
        "moradia",
        "financiamentos",
        "alimentacao",
        "transporte",
        "assinaturas",
        "saude",
        "seguros",
        "vestuario",
        "lazer_viagens",
        "melhoria_reforma",
        "educacao",
        "servicos_domesticos",
        "financeiro",
        "impostos",
        "suporte_familiar",
        "reserva_desejos",
    }
)


@dataclass(frozen=True)
class CuratedRule:
    """Par keyword→categoria promovível a ``CategorizationRule``."""

    keyword: str  # uppercase, substring match (paridade E4)
    target_category: str  # key do category_template


# Bateria medida contra o dogfood (0 flips cross-categoria por keyword;
# métricas agregadas no PR da lane A28.l5). Estabelecimentos públicos:
CURATED_RULES_A28_L5: tuple[CuratedRule, ...] = (
    # -- estabelecimentos públicos (redes/empresas) --
    CuratedRule("VILA TERRACOTA", "lazer_viagens"),
    CuratedRule("LOFT BRASIL", "moradia"),
    CuratedRule("IMIGRANTES MERCANTIL", "alimentacao"),
    CuratedRule("FASCAR", "vestuario"),
    CuratedRule("MCDONALDS", "alimentacao"),
    CuratedRule("RECANTO DOS FRIOS", "alimentacao"),
    CuratedRule("HAVAN", "reserva_desejos"),
    CuratedRule("NACAR YAMAHA", "transporte"),
    CuratedRule("REDE DUQUE", "transporte"),
    CuratedRule("POSTO AVENIDA", "transporte"),
    CuratedRule("POSTOSETEE", "transporte"),
    CuratedRule("TENIS CLUBE", "lazer_viagens"),
    CuratedRule("ITA AIR", "lazer_viagens"),
    CuratedRule("ASSIST CARD", "seguros"),
    # -- descritores genéricos de segmento (PT-BR) --
    CuratedRule("CENTRO AUTOMOTIVO", "transporte"),
    CuratedRule("POSTO DE ABASTE", "transporte"),
    CuratedRule("SERVICOS MEDICOS", "saude"),
    CuratedRule("DROGARIA", "saude"),
    CuratedRule("OTICA", "vestuario"),
    CuratedRule("BARBEARIA", "vestuario"),
    CuratedRule("RESTAURANTE", "alimentacao"),
    CuratedRule("PIZZARIA", "alimentacao"),
    CuratedRule("PADARIA", "alimentacao"),
    CuratedRule("LANCHONETE", "alimentacao"),
    CuratedRule("TXAEMBARQ", "lazer_viagens"),
    CuratedRule("CIA DE SANE", "moradia"),
    CuratedRule("CART REG PES", "financeiro"),
)


@dataclass(frozen=True)
class PromotionResult:
    """Resultado por regra: ``created`` | ``skipped_exists`` | ``failed``."""

    keyword: str
    target_category: str
    status: str
    applied_count: int = 0
    detail: Optional[str] = None


@dataclass(frozen=True)
class PromotionContext:
    """Dependências compartilhadas da promoção em lote (evita fan-out de args)."""

    workspace: Workspace
    detector: InternalTransferDetector
    transactions: list
    db: Session
    user_id: Optional[str] = None


def _create_sync(rule: CuratedRule, ctx: PromotionContext) -> int:
    response = rule_management_service.create_rule(
        workspace=ctx.workspace,
        keyword=rule.keyword,
        target_category=rule.target_category,
        priority=100,
        user_id=ctx.user_id,
        detector=ctx.detector,
        transactions=ctx.transactions,
        db=ctx.db,
    )
    return response.applied_count


def _create_async_fallback(rule: CuratedRule, ctx: PromotionContext) -> int:
    """>SYNC_APPLY_THRESHOLD matches → engine async in-process (sem Celery)."""
    created = rule_management_service.create_rule_async(
        workspace=ctx.workspace,
        keyword=rule.keyword,
        target_category=rule.target_category,
        priority=100,
        user_id=ctx.user_id,
        db=ctx.db,
    )
    applied = apply_retroactive_async_safe(
        workspace_id=ctx.workspace.id,
        rule=created,
        detector=ctx.detector,
        transactions=ctx.transactions,
        db=ctx.db,
    )
    set_applied_count(rule_id=created.id, applied=applied, db=ctx.db)
    ctx.db.commit()
    return applied


def _promote_one(rule: CuratedRule, ctx: PromotionContext) -> PromotionResult:
    try:
        try:
            applied = _create_sync(rule, ctx)
        except ApplyTooLargeError:
            ctx.db.rollback()
            applied = _create_async_fallback(rule, ctx)
        return PromotionResult(rule.keyword, rule.target_category, "created", applied)
    except RuleAlreadyExistsError as exc:
        ctx.db.rollback()
        existing_applied = count_applied_overrides(ctx.db, ctx.workspace.id, exc.existing_rule_id)
        return PromotionResult(
            rule.keyword, rule.target_category, "skipped_exists", existing_applied
        )


def _validate_targets(rules: tuple[CuratedRule, ...]) -> None:
    invalid = {r.target_category for r in rules} - VALID_EXPENSE_CATEGORIES
    if invalid:
        raise ValueError(
            f"target_category fora do category_template v1: {sorted(invalid)!r} "
            f"(esperado ∈ VALID_EXPENSE_CATEGORIES)"
        )


def _log_summary(results: list[PromotionResult], workspace_id: str) -> None:
    logger.info(
        "curated rules promotion finished",
        extra={
            "workspace_id": workspace_id,
            "created": sum(1 for r in results if r.status == "created"),
            "skipped": sum(1 for r in results if r.status == "skipped_exists"),
        },
    )


def promote_curated_rules(
    *,
    workspace: Workspace,
    detector: InternalTransferDetector,
    transactions: list,
    db: Session,
    user_id: Optional[str] = None,
    rules: tuple[CuratedRule, ...] = CURATED_RULES_A28_L5,
) -> list[PromotionResult]:
    """Promove o ruleset curado — idempotente (regra existente = skip)."""
    _validate_targets(rules)
    ctx = PromotionContext(workspace, detector, transactions, db, user_id)
    results = [_promote_one(rule, ctx) for rule in rules]
    _log_summary(results, workspace.id)
    return results
