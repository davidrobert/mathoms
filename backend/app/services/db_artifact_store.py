"""DBArtifactStore — SQLAlchemy ArtifactStore. Sessão injetada (ADR-083); validate→encrypt→write (ADR-212 PR3 + ADR-231); fallback workspace para stages em _WORKSPACE_SCOPED_STAGES (ADR-132 / ADR-157 / ADR-238 / ADR-241)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.crypto import (
    decrypt_artifact_payload,
    encrypt_artifact_payload,
    is_encrypted_payload,
    should_encrypt_writes,
)

_logger = logging.getLogger("mathoms.crypto")
_artifact_logger = logging.getLogger("mathoms.pipeline.artifact")


def _maybe_encrypt(payload: dict) -> dict:
    if not should_encrypt_writes():
        return payload
    return encrypt_artifact_payload(payload)


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
    # E1.5c — baseline consolidado
    "E1.5c": "baseline_patrimonial.schema.json",
    "consolidate_baseline": "baseline_patrimonial.schema.json",
    # E1.6 — IRPF full (ADR-157)
    "extract_irpf_full": "e16_irpf_full.schema.json",
    # E2 — extratos / faturas / LLM fallback (todos compartilham mesmo schema)
    "E2": "e2_extract.schema.json",
    "E2-faturas": "e2_extract.schema.json",
    "E2-extratos": "e2_extract.schema.json",
    "E2-llm": "e2_extract.schema.json",
    "extract_invoices": "e2_extract.schema.json",
    "extract_statements": "e2_extract.schema.json",
    "extract_with_llm": "e2_extract.schema.json",
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
herdado de ``pipeline.json::schema_validation`` ou env
``MATHOMS_PIPELINE_SCHEMA_MODE``. Em ``strict`` + payload inválido,
``write()`` propaga ``ValidationError`` do jsonschema.
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
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._pipeline_run_id = pipeline_run_id

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @property
    def pipeline_run_id(self) -> str:
        return self._pipeline_run_id

    @property
    def session(self) -> Session:
        """Expõe a `Session` injetada — call-sites que precisam compartilhar a
        mesma transação (ex.: learning loop E4 em `scripts/e4_categorize.py`)
        leem aqui em vez de `store._session` (ressalva senior-cto, A12.P2)."""
        return self._session

    def _get(self, stage: str, key: str) -> Optional[PipelineArtifact]:
        return (
            self._session.query(PipelineArtifact)
            .filter_by(
                pipeline_run_id=self._pipeline_run_id,
                stage=stage,
                artifact_key=key,
            )
            .one_or_none()
        )

    def _get_latest_in_workspace(self, stage: str, key: str) -> Optional[PipelineArtifact]:
        return (
            self._session.query(PipelineArtifact)
            .filter_by(
                workspace_id=self._workspace_id,
                stage=stage,
                artifact_key=key,
            )
            .order_by(PipelineArtifact.created_at.desc())
            .first()
        )

    def read(self, stage: str, key: str) -> Optional[dict]:
        row = self._get(stage, key)
        if row is None and stage in _WORKSPACE_SCOPED_STAGES:
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
            .filter_by(workspace_id=self._workspace_id, stage=stage)
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
        payload = _maybe_encrypt(data)
        row = self._get(stage, key)
        if row is None:
            self._insert(stage, key, payload, document_id)
            return
        row.content_json = payload
        if document_id is not None:
            row.document_id = document_id

    def _insert(
        self, stage: str, key: str, payload: dict, document_id: Optional[str] = None
    ) -> None:
        self._session.add(
            PipelineArtifact(
                workspace_id=self._workspace_id,
                pipeline_run_id=self._pipeline_run_id,
                stage=stage,
                artifact_key=key,
                document_id=document_id,
                content_json=payload,
            )
        )

    @staticmethod
    def _validate_schema(stage: str, key: str, data: dict) -> None:
        # ADR-212 PR3 — strict propaga jsonschema.ValidationError; warn loga.
        schema_name = SCHEMA_BY_STAGE.get(stage)
        if schema_name is None:
            return
        from scripts.pipeline_common import validate_dict

        validate_dict(data, schema_name, source=f"{stage}/{key}")

    def delete(self, stage: str, key: str) -> None:
        row = self._get(stage, key)
        if row is not None:
            self._session.delete(row)

    def delete_stage(self, stage: str) -> int:
        count = (
            self._session.query(PipelineArtifact)
            .filter_by(pipeline_run_id=self._pipeline_run_id, stage=stage)
            .delete(synchronize_session=False)
        )
        return int(count or 0)
