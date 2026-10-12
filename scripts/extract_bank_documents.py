#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2 Extraction — Unified CLI for deterministic financial document parsers.

Replaces the previous e2_extract_extratos.py and e2_extract_faturas.py with a
single entry point that routes all supported file types (extratos, faturas,
CDB positions) through modular bank-specific parsers.

Usage:
    python scripts/extract_bank_documents.py [--dry-run] [--file ARQUIVO] [--output-dir DIR] [--quiet]
    python scripts/extract_bank_documents.py --extratos-only
    python scripts/extract_bank_documents.py --faturas-only
"""

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from scripts.e2.common import log
from scripts.e2.registry import (
    NON_STATEMENT_TYPES,
    is_investment_type,
    known_bank_extrato_without_parser,
    route_to_parser,
)
from scripts.e2.validation import validate_extrato_result, validate_fatura_result

if TYPE_CHECKING:
    from pipeline.domain.services.e2_natural_key import NaturalKeyStats

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


VALID_EXTENSIONS = (
    "-0_original.pdf",
    "-0_original.csv",
    "-0_original.xls",
    "-0_original.xlsx",
)

LOG_EXTRATO = "E2-EXTRATO"
LOG_FATURA = "E2-FATURA"
LOG_UNIFIED = "E2-EXTRACT"


def _is_fatura_file(filename: str) -> bool:
    return "fatura" in filename.lower()


def _is_extrato_file(filename: str) -> bool:
    return "extrato" in filename.lower()


def _is_investment_file(filename: str) -> bool:
    return is_investment_type(filename)


def find_all_files(
    statements_dir: Path, extratos_only: bool = False, faturas_only: bool = False
) -> List[Path]:
    """Find all processable financial files in the run tenant's data/financial_statements/."""
    if not statements_dir.is_dir():
        log(LOG_UNIFIED, "WARN", f"Diretório não encontrado: {statements_dir}")
        return []

    files = []
    for f in sorted(statements_dir.iterdir()):
        if not f.is_file():
            continue
        if not any(f.name.endswith(ext) for ext in VALID_EXTENSIONS):
            continue

        is_fatura = _is_fatura_file(f.name)
        is_investment = _is_investment_file(f.name)

        if extratos_only and is_fatura:
            continue
        if faturas_only and not is_fatura:
            continue

        # Investment files (CDB) are always included when not faturas_only
        if is_investment:
            files.append(f)
            continue

        # Skip non-statement types that aren't faturas
        if not is_fatura and NON_STATEMENT_TYPES.search(f.name):
            continue

        # Must contain "extrato" or "fatura" in filename
        if not is_fatura and "extrato" not in f.name.lower():
            continue

        files.append(f)

    return files


def generate_llm_fallback(file_path: Path, filename: str) -> Dict[str, Any]:
    """Generate a stub JSON for unknown file types, flagged for LLM processing."""
    text_preview = ""
    if pdfplumber and filename.endswith(".pdf"):
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:3]:
                    t = page.extract_text()
                    if t:
                        text_preview += t + "\n"
        except Exception:
            pass

    is_fatura = _is_fatura_file(filename)
    return {
        "tipo": "fatura_desconhecida" if is_fatura else "extrato_desconhecido",
        "arquivo_origem": filename,
        "requires_llm_fallback": True,
        "texto_extraido_preview": text_preview[:5000] if text_preview else None,
        "transacoes": [],
        "nota": "Banco/formato não reconhecido pelo parser determinístico. Requer processamento LLM.",
    }


def process_file(file_path: Path, dry_run: bool = False) -> Optional[Dict[str, Any]]:
    """Process a single file through the appropriate parser."""
    filename = file_path.name

    parser_fn = route_to_parser(filename)
    if parser_fn is None:
        prefix = LOG_FATURA if _is_fatura_file(filename) else LOG_EXTRATO
        routing_hole_bank = known_bank_extrato_without_parser(filename)
        if routing_hole_bank:
            log(
                prefix,
                "ERROR",
                f"ROTEAMENTO FUROU: extrato de banco conhecido '{routing_hole_bank}' "
                f"sem parser determinístico ({filename}) — vai para o LLM e pode sumir "
                f"do relatório. Provável regressão de anchor; ver "
                f"tests/test_e2_parsers.py::TestExtratoRoutingInvariant.",
            )
        else:
            log(prefix, "WARN", f"Sem parser determinístico para: {filename}")
        return generate_llm_fallback(file_path, filename)

    if dry_run:
        log(LOG_UNIFIED, "INFO", f"[DRY-RUN] Processaria: {filename} → {parser_fn.__name__}")
        return None

    result = parser_fn(file_path, filename)

    # Run validation
    is_fatura = _is_fatura_file(filename)
    if is_fatura:
        if not result.get("requires_llm_fallback"):
            result = validate_fatura_result(result, filename)
    else:
        is_csv = filename.endswith(".csv") or filename.endswith(".xls")
        issues = validate_extrato_result(result, file_path, is_csv=is_csv)
        prefix = LOG_EXTRATO
        for issue in issues:
            level = issue.split(":")[0]
            log(prefix, level, f"  {filename}: {issue}")
            result.setdefault("notas", []).append(issue)

    # Parsers regex per-bank (scripts/e2/banks/*) não populam arquivo_origem
    # no top-level — só o E2-llm fallback faz. Sem isso, BankStatement.from_e2_dict
    # define tx.source_document=None, o E3 grava tx sem arquivo_origem, e os
    # ClassifiedTransaction.source_doc_id (ADR-255 Camada B) ficam vazios,
    # quebrando a auditabilidade cross-document observada no workspace 5@5.com.
    result.setdefault("arquivo_origem", filename)
    # A24.l2 (ADR-280): extração emite só numero_conta raw; a normalização
    # canônica roda nos consumidores (fallback em document.from_e2_dict).
    return result


def make_output_name(filename: str) -> str:
    """Generate output JSON filename from source filename."""
    out_name = re.sub(
        r"(-0_original)?\.(pdf|csv|xls|xlsx)$", "-2_extract.json", filename, flags=re.IGNORECASE
    )
    return out_name


def save_result(result: Dict[str, Any], filename: str, output_dir: Path) -> Path:
    """Save extraction result to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_name = make_output_name(filename)
    out_path = output_dir / out_name

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Schema check (warn by default); skip stubs que ainda não têm campos canônicos E2
    if not result.get("requires_llm_fallback"):
        try:
            import scripts.pipeline_common as _pc_common

            _pc_common.validate_artifact(out_path, "e2_extract.schema.json")
        except ImportError:
            pass

    return out_path


def _target_stage_for_file(file_path: Path, *, extratos_only: bool, faturas_only: bool) -> str:
    """Decide em qual artifact stage o output vai (Caminho B, Fase 3.2).

    Decisão 1:1 com ``STAGE_REGISTRY``:
    - ``E2-faturas``: arquivos de fatura de cartão
    - ``E2-extratos``: extratos bancários + investimentos (CDBs)
    - ``E2-llm``: fallback quando não há parser determinístico (set externamente)
    """
    if faturas_only:
        return "extract_invoices"
    if extratos_only:
        return "extract_statements"
    # Modo unificado (CLI legacy): decide por filename.
    if _is_fatura_file(file_path.name):
        return "extract_invoices"
    return "extract_statements"


def _artifact_key_for_file(file_path: Path) -> str:
    """Stem do documento, sem ``-0_original`` nem extensão.

    Espelha ``_normalize_stem_for_incremental`` em ``pipeline/stages/e2.py``.
    """
    stem = file_path.stem
    if "-0_original" in stem:
        stem = stem.split("-0_original")[0]
    return stem


@dataclass(frozen=True)
class _Routing:
    """Para onde vai o artefato de cada documento nesta execução do stage."""

    target_stage: str | None
    extratos_only: bool
    faturas_only: bool
    dry_run: bool

    @property
    def escalates_in_place(self) -> bool:
        return self.target_stage is not None and not self.dry_run

    def stage_for(self, file_path: Path) -> str:
        return self.target_stage or _target_stage_for_file(
            file_path, extratos_only=self.extratos_only, faturas_only=self.faturas_only
        )


@dataclass(frozen=True)
class _ExtractedDocument:
    """Documento que passou pela fase de parse e aguarda o store."""

    stage: str
    key: str
    payload: Dict[str, Any]
    n_tx: int = 0
    escalation_stub: bool = False
    counts_as_processed: bool = False
    nk_stats: Optional["NaturalKeyStats"] = None


def _count_validation_notes(result: Dict[str, Any], stats: dict) -> None:
    notes = [note for note in result.get("notas", []) if isinstance(note, str)]
    stats["erros_validacao"] += sum(note.startswith("ERROR") for note in notes)
    stats["warnings"] += sum(note.startswith("WARN") for note in notes)


def _ready_document(
    file_path: Path, result: Dict[str, Any], routing: _Routing
) -> _ExtractedDocument:
    is_llm = bool(result.get("requires_llm_fallback"))
    # ADR-278 B4: estampa K4 natural_key + direction antes de persistir.
    from pipeline.domain.services.e2_natural_key import stamp_natural_key

    return _ExtractedDocument(
        stage="extract_with_llm" if is_llm else routing.stage_for(file_path),
        key=_artifact_key_for_file(file_path),
        payload=result,
        n_tx=len(result.get("transacoes", [])) + len(result.get("itens", [])),
        counts_as_processed=not is_llm,
        nk_stats=stamp_natural_key(result),
    )


def _parse_document(
    file_path: Path, stats: dict, routing: _Routing
) -> Optional[_ExtractedDocument]:
    result = process_file(file_path, dry_run=routing.dry_run)
    if result is None:
        return None
    is_llm = bool(result.get("requires_llm_fallback"))
    if is_llm:
        stats["llm_fallback"] += 1
        log(LOG_UNIFIED, "WARN", f"  → Requer LLM fallback: {file_path.name}")
    if is_llm and routing.escalates_in_place:
        key = _artifact_key_for_file(file_path)
        return _ExtractedDocument(
            stage=routing.target_stage, key=key, payload=result, escalation_stub=True
        )
    doc = _ready_document(file_path, result, routing)
    # Depois do stamp: se ele levantar, o documento conta uma vez só no except.
    _count_validation_notes(result, stats)
    return doc


def _extract_document(
    file_path: Path, stats: dict, routing: _Routing
) -> Optional[_ExtractedDocument]:
    """Fase de parse: falha aqui é do documento — conta em ``erros_validacao`` e o lote segue."""
    try:
        return _parse_document(file_path, stats, routing)
    except Exception as e:
        stats["erros_validacao"] += 1
        log(LOG_UNIFIED, "ERROR", f"  Failed: {file_path.name} — {e}")
        return None


def _count_processed(doc: _ExtractedDocument, stats: dict) -> None:
    if doc.counts_as_processed:
        stats["processados"] += 1
        stats["transacoes_total"] += doc.n_tx


def _write_escalation_stub(store, doc: _ExtractedDocument) -> None:
    # ADR-342: grava o stub de escalação NO stage determinístico —
    # supersede parcial de run anterior (senão o fallback
    # workspace-scoped do store ressuscita o parcial e a
    # escalação vira no-op). E3 pula stubs; o pickup do E2-llm
    # trata key-só-stub como não-processada.
    store.write(doc.stage, doc.key, doc.payload)
    log(LOG_UNIFIED, "WARN", f"  → stub de escalação: {doc.stage}/{doc.key}")


def _keeps_existing_artifact(store, doc: _ExtractedDocument, stats: dict) -> bool:
    # Overwrite protection: não sobrescrever extrato com 0 txns se já
    # há artefato com txns (mesma lógica do main legado).
    if doc.n_tx > 0 or not store.exists(doc.stage, doc.key):
        return False
    existing = store.read(doc.stage, doc.key) or {}
    existing_txns = len(existing.get("transacoes", [])) + len(existing.get("itens", []))
    if existing_txns == 0:
        return False
    # Não é processado: a key já foi gravada — e contada — por outro arquivo deste run.
    stats["skipped_overwrite"] += 1
    log(
        LOG_UNIFIED,
        "WARN",
        f"  SKIP: {doc.stage}/{doc.key} já tem {existing_txns} txns; "
        f"não sobrescrever com resultado de 0 txns",
    )
    return True


def _write_extracted(store, doc: _ExtractedDocument, stats: dict) -> None:
    store.write(doc.stage, doc.key, doc.payload)
    # Conta só depois do write: recusado em strict, o documento não é progresso.
    _count_processed(doc, stats)
    nk = doc.nk_stats
    log(
        LOG_UNIFIED,
        "INFO" if doc.n_tx > 0 else "WARN",
        f"  → store.write({doc.stage}, {doc.key}, {doc.n_tx} tx) "
        f"[natural_key {nk.with_key}/{nk.tx_total}]",
    )


def run_with_store(
    *,
    store,
    statements_dir: Path,
    target_stage: str | None = None,
    extratos_only: bool = False,
    faturas_only: bool = False,
    incremental_allowed_stems: set[str] | None = None,
    dry_run: bool = False,
    pipeline_run_id: str | None = None,
) -> dict:
    """Caminho B (Fase 3.2): processa documentos e grava via ``ArtifactStore``.

    Não toca ``processed/`` diretamente — ``DiskArtifactStore`` traduz writes
    para o layout legado transparentemente.

    Args:
        store: ``ArtifactStore`` alvo (Disk ou DB).
        statements_dir: ``data/financial_statements`` do tenant DESTE run. Nunca global
            de módulo: o 1º import congelava o tenant do 1º run do processo.
        target_stage: quando não-None, todos os outputs vão para este stage
            (``"extract_statements"``, ``"extract_invoices"``, ``"extract_with_llm"``). Quando ``None``,
            o stage é decidido por arquivo (``_target_stage_for_file``).
        extratos_only / faturas_only: filtra ``find_all_files``.
        incremental_allowed_stems: se informado, processa apenas arquivos cujo
            ``_artifact_key_for_file`` está no conjunto (modo incremental).
        dry_run: se True, não escreve nada no store.

    Returns:
        Dict com estatísticas: ``processados``, ``transacoes_total``,
        ``llm_fallback``, ``erros_validacao``, ``warnings``, ``skipped_overwrite``.

    Falha de parse é do documento e o lote segue. Exceção do store propaga: o
    stage é a unidade de trabalho (ADR-256), e documento só conta como
    processado depois do write — um write recusado em strict nunca é progresso.
    """
    files = find_all_files(statements_dir, extratos_only=extratos_only, faturas_only=faturas_only)

    if incremental_allowed_stems is not None:
        files = [f for f in files if _artifact_key_for_file(f) in incremental_allowed_stems]

    stats = {
        "processados": 0,
        "transacoes_total": 0,
        "llm_fallback": 0,
        "erros_validacao": 0,
        "warnings": 0,
        "skipped_overwrite": 0,
    }

    emit_stage = target_stage or "E2"
    total_files = len(files)
    from pipeline.live_progress import emit_item_progress

    routing = _Routing(target_stage, extratos_only, faturas_only, dry_run)
    for idx, file_path in enumerate(files):
        emit_item_progress(
            pipeline_run_id,
            emit_stage,
            current_item=file_path.name,
            items_done=idx,
            items_total=total_files,
            phase="preparing",
        )
        doc = _extract_document(file_path, stats, routing)
        if doc is None or dry_run:
            continue
        if doc.escalation_stub:
            _write_escalation_stub(store, doc)
            continue
        if _keeps_existing_artifact(store, doc, stats):
            continue
        emit_item_progress(
            pipeline_run_id,
            emit_stage,
            current_item=file_path.name,
            items_done=idx,
            items_total=total_files,
            phase="persisting",
        )
        _write_extracted(store, doc, stats)

    if total_files > 0:
        emit_item_progress(
            pipeline_run_id,
            emit_stage,
            current_item=None,
            items_done=total_files,
            items_total=total_files,
            phase="finalizing",
        )

    return stats
