"""Write-path do enforce de colapso cross-documento ([[ADR-364]] §Emenda 2026-08-10).

O gate morde **aqui**, no ato do operador, e nunca dentro do pipeline: `liberado` é
workspace-global e o dano é por-chave, então uma cláusula reprovada desligaria o colapso
de todos os candidatos do workspace. O que protege por-run é a retenção, a degradação do
guard e `RetencaoInstavel` — este preflight prova que o operador **olhou** e que ligar
vai fazer alguma coisa.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import PipelineRun, PipelineStageLog
from backend.app.services import feature_flags_service
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult

FLAG_ENFORCE = "cross_document_collapse_enforce_enabled"
FLAG_MEASURE = "cross_document_collapse_measure_enabled"

_STAGE = "reconcile_transactions"
_IDADE_MAXIMA = timedelta(hours=72)

# Cláusulas do MECANISMO, não `liberado` ([[ADR-364]] §Emenda 2026-08-10). `medido` e
# `hits` saíram por serem identidades: todo relatório que chega ao `output_summary` tem
# `corpus_observado > 0`, e `sem_snapshot == 0 ⇒ hits == 0` porque `_alvos` já exclui o
# retido. `vivacidade` saiu por não ter elo causal com o dano — vai para a auditoria.
_CLAUSULAS = (
    ("collapse_retention", "lido", True),
    ("collapse_retention", "degradado", False),
    ("collapse_retention", "retencao_instavel", False),
    ("collapse_precondition", "sem_snapshot", 0),
    ("collapse_precondition", "tx_data_nao_iso", 0),
)


# Run `from_stage` completa sem executar E3, e `needs_review` executa E3 sem completar:
# ancorar no run é errado nas duas direções. `PipelineStageLog` admite N rows por
# `(run, stage)` (resume/redelivery), daí o `ORDER BY started_at DESC`.
async def _run_de_referencia(db: AsyncSession, workspace_id: str) -> PipelineStageLog | None:
    """Execução mais recente do E3 **que mediu** — não "último run completado"."""
    stmt = (
        select(PipelineStageLog)
        .join(PipelineRun, PipelineRun.id == PipelineStageLog.pipeline_run_id)
        .where(PipelineRun.workspace_id == workspace_id, PipelineStageLog.stage == _STAGE)
        .order_by(PipelineStageLog.started_at.desc())
        .limit(20)
    )
    for log in (await db.execute(stmt)).scalars():
        if isinstance(log.output_summary, dict) and "collapse_retention" in log.output_summary:
            return log
    return None


def _idade_ok(log: PipelineStageLog) -> bool:
    inicio = log.started_at
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - inicio <= _IDADE_MAXIMA


# Leitura por chave EXPLÍCITA: `.get(k, default)` reintroduz o fail-open que `_alvos` pagou
# para fechar — chave ausente leria como cláusula satisfeita.
def _falha_da_clausula(summary: dict, bloco: str, chave: str, esperado) -> str | None:
    conteudo = summary.get(bloco)
    if not isinstance(conteudo, dict) or chave not in conteudo:
        return f"{bloco}.{chave}=ausente"
    return None if conteudo[chave] == esperado else f"{bloco}.{chave}={conteudo[chave]!r}"


def _reprovadas(summary: dict) -> list[str]:
    falhas = (_falha_da_clausula(summary, *clausula) for clausula in _CLAUSULAS)
    return [f for f in falhas if f]


def _observado(summary: dict) -> dict:
    """O que vai para a auditoria sem bloquear — inclusive `liberado` e `vivacidade`."""
    precondicao = summary.get("collapse_precondition") or {}
    retencao = summary.get("collapse_retention") or {}
    return {
        "liberado": precondicao.get("liberado"),
        "clausulas_reprovadas": precondicao.get("clausulas_reprovadas"),
        "snapshot_casa_corpus": precondicao.get("snapshot_casa_corpus"),
        "reservatorio_llm_sem_gemea": retencao.get("reservatorio_llm_sem_gemea"),
        "retido_por_override": retencao.get("retido_por_override"),
    }


async def _preflight(db: AsyncSession, workspace_id: str) -> tuple[OpResult | None, dict]:
    log = await _run_de_referencia(db, workspace_id)
    if log is None:
        return OpResult.failure("medicao_ausente", workspace_id=workspace_id), {}
    if not _idade_ok(log):
        return OpResult.failure("medicao_velha", started_at=str(log.started_at)), {}
    reprovadas = _reprovadas(log.output_summary)
    observado = {**_observado(log.output_summary), "pipeline_run_id": log.pipeline_run_id}
    if reprovadas:
        return OpResult.failure("preflight_reprovado", clausulas=reprovadas), observado
    return None, observado


# Assimetria deliberada: `enabled=False` NÃO passa por preflight. Kill-switch com gate é
# kill-switch quebrado — e desligar é sempre a direção segura.
# As DUAS: enforce é inerte sem measure (`_e3_build_collapser` devolve `None` e o adapter
# exige os dois), e escrever só a de enforce criaria o estado silenciosamente morto.
async def _escreve_as_duas_flags(db: AsyncSession, workspace_id: str, *, enabled: bool) -> None:
    await feature_flags_service.set_flag(workspace_id, FLAG_MEASURE, True, db=db)
    await feature_flags_service.set_flag(workspace_id, FLAG_ENFORCE, enabled, db=db)


async def set_collapse_enforce(
    db: AsyncSession, workspace_id: str, *, enabled: bool, actor: str
) -> OpResult:
    """Liga/desliga o enforce. Ligar exige preflight sobre o run de referência."""
    observado: dict = {}
    if enabled:
        falha, observado = await _preflight(db, workspace_id)
        if falha is not None:
            return falha

    await _escreve_as_duas_flags(db, workspace_id, enabled=enabled)
    _registra(db, workspace_id, enabled=enabled, actor=actor, observado=observado)
    return OpResult.success(workspace_id=workspace_id, enabled=enabled, **observado)


def _registra(db, workspace_id: str, *, enabled: bool, actor: str, observado: dict) -> None:
    """`liberado` e `vivacidade` chegam aqui: deixaram de bloquear, não de ser medidos."""
    append_audit(
        AuditRecord(
            action="workspace.set_collapse_enforce",
            actor=actor,
            target_type="workspace",
            target_id=workspace_id,
            details={"enabled": enabled, **observado},
        ),
        db,
    )
