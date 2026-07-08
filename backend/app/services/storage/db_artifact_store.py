"""DBArtifactStore — SQLAlchemy ArtifactStore. Sessão injetada (ADR-083); validate→encrypt→write (ADR-212 PR3 + ADR-231); fallback workspace para stages em _WORKSPACE_SCOPED_STAGES (ADR-132 / ADR-157 / ADR-238 / ADR-241); fallback run-pinado em base_run para from_stage (ADR-291)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Callable, Optional, TypeVar

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.artifact_retention import (
    ArtifactRetentionPolicy,
    load_artifact_retention_policy,
)
from backend.app.services.crypto import (
    decrypt_artifact_payload,
    encrypt_artifact_payload,
    is_encrypted_payload,
    should_encrypt_writes,
)
from pipeline.artifact_store import stage_aliases

_logger = logging.getLogger("mathoms.crypto")
_artifact_logger = logging.getLogger("mathoms.pipeline.artifact")
_db_logger = logging.getLogger("mathoms.db")

# Threshold (ms) acima do qual uma query é considerada candidata a lock retry
# do SQLite busy_timeout. Calibrado para ser bem acima de query típica (~5ms)
# e bem abaixo do busy_timeout default (30s) — sinaliza contenção real.
_LOCK_RETRY_THRESHOLD_MS = 250

_T = TypeVar("_T")


def _log_lock_event(
    op: str, elapsed_ms: float, *, locked: bool, stage: str = "", key: str = ""
) -> None:
    """Emite `mathoms.db.lock_retry_count` quando autoflush/query do artifact_store demora ou estoura busy_timeout (ADR-256 instrumentação)."""
    _db_logger.warning(
        "mathoms.db.lock_retry_count",
        extra={
            "op": op,
            "elapsed_ms": round(elapsed_ms, 1),
            "locked_error": locked,
            "stage": stage,
            "artifact_key": key,
        },
    )


def _with_lock_telemetry(op: str, fn: Callable[[], _T], *, stage: str = "", key: str = "") -> _T:
    """Mede `fn()`; loga warning se exceder _LOCK_RETRY_THRESHOLD_MS ou se OperationalError(database is locked) escapar."""
    start = time.monotonic()
    try:
        result = fn()
    except OperationalError as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        if "database is locked" in str(exc).lower():
            _log_lock_event(op, elapsed_ms, locked=True, stage=stage, key=key)
        raise
    elapsed_ms = (time.monotonic() - start) * 1000
    if elapsed_ms > _LOCK_RETRY_THRESHOLD_MS:
        _log_lock_event(op, elapsed_ms, locked=False, stage=stage, key=key)
    return result


def _maybe_encrypt(payload: dict) -> dict:
    if not should_encrypt_writes():
        return payload
    return encrypt_artifact_payload(payload)


def _payload_prompt_version(data: dict) -> Optional[str]:
    """ADR-311 — versão de extração consultável, lift do ``prompt_version`` top-level do payload (ADR-233) pré-encrypt; a coluna espelha o payload atual (inclusive overwrite) e nunca entra na ``artifact_key`` (quebraria o dedupe por documento)."""
    pv = data.get("prompt_version")
    if isinstance(pv, str) and pv:
        return pv[:20]
    return None


def _maybe_decrypt(payload: Optional[dict] = None) -> Optional[dict]:
    if payload is None:
        return None
    if not is_encrypted_payload(payload):
        return payload
    if not should_encrypt_writes():
        # config drift observável (kill switch off + row encriptada)
        _logger.warning("mathoms.crypto.read_in_disabled_mode")
    return decrypt_artifact_payload(payload)


SCHEMA_BY_STAGE: dict[str, str] = {
    # Stage → schema em config/schemas/. Aplicado em DBArtifactStore.write
    # (ADR-212 PR3). Cobre tanto nomes legados quanto descritivos durante
    # a janela F9.2 → F9.6.
    # E1.5/E1.5a — extract per-IRPF + agregado (A20.l11; string decimal ADR-090)
    "E1.5": "e15_baseline_extract.schema.json",
    "E1.5a": "e15_baseline_extract.schema.json",
    "extract_baseline": "e15_baseline_extract.schema.json",
    # E1.5c — baseline consolidado
    "E1.5c": "baseline_patrimonial.schema.json",
    "consolidate_baseline": "baseline_patrimonial.schema.json",
    # E1.6 — IRPF full (ADR-157)
    "extract_irpf_full": "e16_irpf_full.schema.json",
    # E2 — extratos / faturas (parsers determinísticos, vocabulário banco/tipo)
    "E2": "e2_extract.schema.json",
    "E2-faturas": "e2_extract.schema.json",
    "E2-extratos": "e2_extract.schema.json",
    "extract_invoices": "e2_extract.schema.json",
    "extract_statements": "e2_extract.schema.json",
    # E2-llm — writer LLM tem vocabulário próprio (instituicao/tipo_documento);
    # contrato dedicado, transação compartilhada via $ref (ADR-284/A24.l7).
    "E2-llm": "e2_llm_artifact.schema.json",
    "extract_with_llm": "e2_llm_artifact.schema.json",
    # E2-informe-aluguel — informe de rendimentos de imobiliária (Onda 0.5 · ADR-216).
    # Schema dedicado para cap rate líquido em S4 (cascade D9 fonte #1).
    "E2-informe-aluguel": "informe_aluguel.schema.json",
    "extract_informe_aluguel": "informe_aluguel.schema.json",
    # extract_informes_anuais — informes anuais avulsos polimórficos (ADR-238).
    # L1: previdência (PGBL/VGBL). L2-L4 expandem para financeiro_pj/pf,
    # proventos, aluguel migra do standalone acima.
    "extract_informes_anuais": "informe_base.schema.json",
    # extract_comprovantes_bens — comprovantes de bens polimórficos (ADR-239).
    # A18 L1: CRLV-e (veículos). A18 V2 estende para imóveis (RGI/IPTU) e
    # outros bens com identidade canônica.
    "extract_comprovantes_bens": "crlv.schema.json",
    # E3 — reconciliação
    "E3": "e3_reconciled.schema.json",
    "reconcile_transactions": "e3_reconciled.schema.json",
    # E4 — categorização
    "E4": "e4_unified.schema.json",
    "categorize_transactions": "e4_unified.schema.json",
    # E5 — análise financeira
    "E5": "e5_analysis.schema.json",
    "analyze_finances": "e5_analysis.schema.json",
}
"""Stage → schema file mapping para validação pós-write (ADR-212 PR3).

Stages sem entrada aqui não são validados (passthrough). Modo strict/warn
por schema: env ``MATHOMS_PIPELINE_SCHEMA_MODE`` (global) >
``pipeline.json::schema_validation.mode_overrides[<schema>]`` (flip
per-schema, ADR-284) > ``mode`` global. Em ``strict`` + payload inválido,
``write()`` propaga ``ValidationError`` do jsonschema (enforcement real
desde ADR-284 — antes o bool de ``validate_dict`` era descartado).
"""


_WORKSPACE_SCOPED_STAGES: frozenset[str] = frozenset(
    {
        # Legacy names — escritos literalmente por extract_members/extract_baseline
        # /consolidate_baseline durante a janela F9.2 → F9.6 (ADR-093).
        "E1",
        "E1.5",
        "E1.5a",
        "E1.5c",
        # Descritivos equivalentes — protege contra cutover parcial onde algum
        # caller começa a usar nome descritivo antes da migration Alembic F9.3.
        "extract_members",
        "extract_baseline",
        "consolidate_baseline",
        # ADR-157 — escrito/lido em forma descritiva desde o dia 1 (E1.6 não
        # passa pelo legado). Sem entrada aqui, run que não reprocessa IRPF
        # perde IRPF da última run silenciosamente.
        "extract_irpf_full",
        # ADR-216 Onda 0.5b — informe anual de imobiliária. Mesma lógica do
        # IRPF: dataset de referência por ano-base, gerado por upload e
        # consumido por cascade D9 fonte #1 em S4. Sem fallback workspace,
        # rerun do pipeline sem reprocessar informes os perderia.
        "extract_informe_aluguel",
        # ADR-238 A17 — informes anuais avulsos polimórficos (PGBL/VGBL +
        # financeiro PJ/PF + proventos). Dataset de referência por ano-base,
        # gerado por evento de upload. Sem fallback, rerun perderia o
        # informe da última run.
        "extract_informes_anuais",
        # ADR-239 A18 — comprovantes de bens (CRLV em L1; imóveis V2).
        # Identidade canônica do bem é workspace-scoped, sobrevive entre
        # runs (não é run-scoped).
        "extract_comprovantes_bens",
        # ADR-241 — E2 é per-documento idempotente: extrair o mesmo PDF/CSV
        # duas vezes produz o mesmo payload. Em incremental, o pipeline
        # só re-extrai docs novos; sem fallback workspace, E3 ficaria cego
        # aos E2 das runs anteriores e o relatório sairia subdimensionado.
        # E3/E4/E5 **continuam run-scoped** e recomputam o universo a cada
        # run (mantém invariantes cross-account: dedup, saldo continuity).
        # Legacy + descritivo (compat F9.2 → F9.6, ADR-093).
        "E2-extratos",
        "E2-faturas",
        "E2-llm",
        "extract_statements",
        "extract_invoices",
        "extract_with_llm",
    }
)
"""Stages cujo artefato é dataset de **referência** (lifecycle por workspace,
não por run). ``read()`` faz fallback para o artefato mais recente do
workspace quando o ``pipeline_run_id`` atual não tem o key.

Critério de inclusão (origem ADR-132, estendido em ADR-241):

- Artefato é gerado por **evento de domínio** (upload de IRPF, edição de
  family_members) e deve sobreviver entre runs sem custo de
  reprocessamento (E1.x, extract_irpf_full, extract_informe_aluguel,
  extract_informes_anuais).
- Artefato é **per-documento idempotente** — `artifact_key` referencia
  um documento individual e re-extrair produz o mesmo payload (E2-*).
  Em incremental, sem este fallback o pipeline ficaria cego aos
  documentos não-reprocessados.

E3/E4/E5 **não** entram aqui: têm invariantes cross-account (dedup, saldo
continuity entre extratos contíguos, fatura sintetizada por ADR-097 D2).
Cada run é dono dos próprios outputs; recomputação a cada run preserva
determinismo.

Inclui legacy + descritivo durante a janela de compat F9.2 → F9.6 (ADR-093).
``extract_irpf_full`` (ADR-157) só existe em forma descritiva.

Mudança aqui exige ADR (origem: ADR-132).
"""


class DBArtifactStore:
    """Persistência de artefatos em ``pipeline_artifacts`` via SQLAlchemy."""

    def __init__(
        self,
        session: Session,
        *,
        workspace_id: str,
        pipeline_run_id: str,
        base_run_id: Optional[str] = None,
        base_run_fallback_stages: frozenset[str] = frozenset(),
        retention_policy: Optional[ArtifactRetentionPolicy] = None,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._pipeline_run_id = pipeline_run_id
        # ADR-291 — from_stage lê stages run-scoped upstream de UM run base
        # coerente (pin, não latest-per-key — preserva invariantes ADR-241).
        # O set nunca contém stage agendado no run atual.
        self._base_run_id = base_run_id
        self._base_run_fallback_stages = base_run_fallback_stages
        # A33.l6 — injetável em teste; default lazy (env > pipeline.json > 180d).
        self._retention_policy = retention_policy

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @property
    def pipeline_run_id(self) -> str:
        return self._pipeline_run_id

    @property
    def session(self) -> Session:
        """Expõe a `Session` injetada — call-sites que precisam compartilhar a
        mesma transação (ex.: learning loop E4 em `scripts/categorize_transactions.py`)
        leem aqui em vez de `store._session` (ressalva senior-cto, A12.P2)."""
        return self._session

    def _get(self, stage: str, key: str) -> Optional[PipelineArtifact]:
        # Wrapped por _with_lock_telemetry — query dispara autoflush e pode
        # bater write-lock SQLite (ADR-256). Loga warning se >250ms ou OperationalError.
        # stage.in_(aliases): runs pré-F9.2 gravaram nome legado ("E5"); código
        # novo lê pelo descritivo. Um único ponto de compat (ADR-093, até F9.6).
        return _with_lock_telemetry(
            "get",
            lambda: (
                self._session.query(PipelineArtifact)
                .filter(
                    PipelineArtifact.pipeline_run_id == self._pipeline_run_id,
                    PipelineArtifact.stage.in_(stage_aliases(stage)),
                    PipelineArtifact.artifact_key == key,
                )
                .one_or_none()
            ),
            stage=stage,
            key=key,
        )

    def _get_in_base_run(self, stage: str, key: str) -> Optional[PipelineArtifact]:
        # ADR-291 — match EXATO no run base (não latest-per-key); mecânica
        # distinta de _get_latest_in_workspace, não fundir.
        return (
            self._session.query(PipelineArtifact)
            .filter(
                PipelineArtifact.pipeline_run_id == self._base_run_id,
                PipelineArtifact.stage.in_(stage_aliases(stage)),
                PipelineArtifact.artifact_key == key,
            )
            .one_or_none()
        )

    def _get_latest_in_workspace(self, stage: str, key: str) -> Optional[PipelineArtifact]:
        return (
            self._session.query(PipelineArtifact)
            .filter(
                PipelineArtifact.workspace_id == self._workspace_id,
                PipelineArtifact.stage.in_(stage_aliases(stage)),
                PipelineArtifact.artifact_key == key,
            )
            # id como tie-break: created_at (default datetime.now) pode empatar
            # no microssegundo entre writes do mesmo flush — "mais recente"
            # precisa ser determinístico no hot path ADR-241.
            .order_by(PipelineArtifact.created_at.desc(), PipelineArtifact.id.desc())
            .first()
        )

    def read(self, stage: str, key: str) -> Optional[dict]:
        aliases = stage_aliases(stage)
        row = self._get(stage, key)
        if (
            row is None
            and self._base_run_id is not None
            and any(a in self._base_run_fallback_stages for a in aliases)
        ):
            row = self._get_in_base_run(stage, key)
            if row is not None:
                _artifact_logger.info(
                    "mathoms.pipeline.artifact.base_run_fallback",
                    extra={
                        "workspace_id": self._workspace_id,
                        "stage": stage,
                        "artifact_key": key,
                        "current_run_id": self._pipeline_run_id,
                        "base_run_id": self._base_run_id,
                    },
                )
        if row is None and any(a in _WORKSPACE_SCOPED_STAGES for a in aliases):
            row = self._get_latest_in_workspace(stage, key)
            if row is not None:
                # ADR-241 — sinaliza consumo via fallback workspace-scoped.
                # Sem ele, regressão silenciosa em incremental (stage que
                # deveria ler do run atual mas só existe em runs anteriores)
                # passa despercebida.
                _artifact_logger.info(
                    "mathoms.pipeline.artifact.workspace_fallback",
                    extra={
                        "workspace_id": self._workspace_id,
                        "stage": stage,
                        "artifact_key": key,
                        "current_run_id": self._pipeline_run_id,
                        "source_run_id": row.pipeline_run_id,
                    },
                )
        if row is None:
            return None
        return _maybe_decrypt(row.content_json)

    def list_keys(self, stage: str) -> list[str]:
        rows = (
            self._session.query(PipelineArtifact.artifact_key)
            .filter(
                PipelineArtifact.workspace_id == self._workspace_id,
                PipelineArtifact.stage.in_(stage_aliases(stage)),
            )
            .distinct()
            .order_by(PipelineArtifact.artifact_key.asc())
            .all()
        )
        return [r[0] for r in rows]

    def exists(self, stage: str, key: str) -> bool:
        return self._get(stage, key) is not None

    def write(
        self,
        stage: str,
        key: str,
        data: dict,
        *,
        document_id: Optional[str] = None,
    ) -> None:
        self._validate_schema(stage, key, data)
        prompt_version = _payload_prompt_version(data)
        payload = _maybe_encrypt(data)
        row = self._get(stage, key)
        if row is None:
            self._insert(stage, key, payload, document_id, prompt_version)
            self._mark_superseded_previous(stage, key)
            return
        row.content_json = payload
        row.prompt_version = prompt_version
        if document_id is not None:
            row.document_id = document_id

    def _resolve_retention_policy(self) -> ArtifactRetentionPolicy:
        if self._retention_policy is None:
            self._retention_policy = load_artifact_retention_policy()
        return self._retention_policy

    def _mark_superseded_previous(self, stage: str, key: str) -> None:
        """A33.l6 (W6-T05) — nova versão corrente inserida: rows anteriores do
        grupo (workspace, stage-alias, artifact_key) viram superseded e ganham
        ``retention_until``. NULL-only (nunca estende prazo já atribuído); a
        row recém-inserida fica NULL — corrente ≡ fail-safe permanente."""
        until = self._resolve_retention_policy().retention_until(now=datetime.now(timezone.utc))
        (
            self._session.query(PipelineArtifact)
            .filter(
                PipelineArtifact.workspace_id == self._workspace_id,
                PipelineArtifact.stage.in_(stage_aliases(stage)),
                PipelineArtifact.artifact_key == key,
                PipelineArtifact.pipeline_run_id != self._pipeline_run_id,
                PipelineArtifact.retention_until.is_(None),
            )
            .update({"retention_until": until}, synchronize_session=False)
        )

    def _insert(
        self,
        stage: str,
        key: str,
        payload: dict,
        document_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
    ) -> None:
        self._session.add(
            PipelineArtifact(
                workspace_id=self._workspace_id,
                pipeline_run_id=self._pipeline_run_id,
                stage=stage,
                artifact_key=key,
                document_id=document_id,
                content_json=payload,
                prompt_version=prompt_version,
            )
        )

    def _validation_context(self, stage: str, key: str) -> dict:
        return {
            "workspace_id": self._workspace_id,
            "pipeline_run_id": self._pipeline_run_id,
            "stage": stage,
            "artifact_key": key,
        }

    def _validate_schema(self, stage: str, key: str, data: dict) -> None:
        # ADR-212 PR3 + ADR-284 — warn loga drift com workspace_id; strict
        # propaga ValidationError e o write não acontece (antes o bool era
        # descartado e strict era no-op).
        schema_name = SCHEMA_BY_STAGE.get(stage)
        if schema_name is None:
            return
        from scripts.pipeline_common import validate_dict

        valid = validate_dict(
            data, schema_name, source=f"{stage}/{key}", context=self._validation_context(stage, key)
        )
        if not valid:
            import jsonschema

            raise jsonschema.ValidationError(
                f"payload de {stage}/{key} viola {schema_name} em modo strict — "
                "paths em drift no logger mathoms.pipeline.schema_validation"
            )

    def delete(self, stage: str, key: str) -> None:
        row = self._get(stage, key)
        if row is not None:
            self._session.delete(row)

    def delete_stage(self, stage: str) -> int:
        count = (
            self._session.query(PipelineArtifact)
            .filter(
                PipelineArtifact.pipeline_run_id == self._pipeline_run_id,
                PipelineArtifact.stage.in_(stage_aliases(stage)),
            )
            .delete(synchronize_session=False)
        )
        return int(count or 0)
