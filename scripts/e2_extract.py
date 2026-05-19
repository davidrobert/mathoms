#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2 Extraction — Unified CLI for deterministic financial document parsers.

Replaces the previous e2_extract_extratos.py and e2_extract_faturas.py with a
single entry point that routes all supported file types (extratos, faturas,
CDB positions) through modular bank-specific parsers.

Usage:
    python scripts/e2_extract.py [--dry-run] [--file ARQUIVO] [--output-dir DIR] [--quiet]
    python scripts/e2_extract.py --extratos-only
    python scripts/e2_extract.py --faturas-only
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.e2.common import DATA_DIR, OUTPUT_DIR, log
from scripts.e2.registry import (
    NON_STATEMENT_TYPES,
    is_investment_type,
    route_to_parser,
)
from scripts.e2.validation import validate_extrato_result, validate_fatura_result

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


def find_all_files(extratos_only: bool = False, faturas_only: bool = False) -> List[Path]:
    """Find all processable financial files in data/financial_statements/."""
    if not DATA_DIR.is_dir():
        log(LOG_UNIFIED, "WARN", f"Diretório não encontrado: {DATA_DIR}")
        return []

    files = []
    for f in sorted(DATA_DIR.iterdir()):
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

    # ADR-226 PR2 — popula numero_conta_norm canônico (idempotente, parsers
    # continuam entregando numero_conta heterogêneo)
    from scripts.e2.common import finalize_e2_result

    return finalize_e2_result(result)


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
        return "E2-faturas"
    if extratos_only:
        return "E2-extratos"
    # Modo unificado (CLI legacy): decide por filename.
    if _is_fatura_file(file_path.name):
        return "E2-faturas"
    return "E2-extratos"


def _artifact_key_for_file(file_path: Path) -> str:
    """Stem do documento, sem ``-0_original`` nem extensão.

    Espelha ``_normalize_stem_for_incremental`` em ``pipeline/stages/e2.py``.
    """
    stem = file_path.stem
    if "-0_original" in stem:
        stem = stem.split("-0_original")[0]
    return stem


def run_with_store(
    *,
    store,
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
        target_stage: quando não-None, todos os outputs vão para este stage
            (``"E2-extratos"``, ``"E2-faturas"``, ``"E2-llm"``). Quando ``None``,
            o stage é decidido por arquivo (``_target_stage_for_file``).
        extratos_only / faturas_only: filtra ``find_all_files``.
        incremental_allowed_stems: se informado, processa apenas arquivos cujo
            ``_artifact_key_for_file`` está no conjunto (modo incremental).
        dry_run: se True, não escreve nada no store.

    Returns:
        Dict com estatísticas: ``processados``, ``transacoes_total``,
        ``llm_fallback``, ``erros_validacao``, ``warnings``, ``skipped_overwrite``.
    """
    files = find_all_files(extratos_only=extratos_only, faturas_only=faturas_only)

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

    for idx, file_path in enumerate(files):
        emit_item_progress(
            pipeline_run_id,
            emit_stage,
            current_item=file_path.name,
            items_done=idx,
            items_total=total_files,
            phase="preparing",
        )
        try:
            result = process_file(file_path, dry_run=dry_run)
            if result is None:
                continue

            key = _artifact_key_for_file(file_path)
            is_llm = bool(result.get("requires_llm_fallback"))
            if is_llm:
                stats["llm_fallback"] += 1
                stage = "E2-llm"
                log(LOG_UNIFIED, "WARN", f"  → Requer LLM fallback: {file_path.name}")
                # E2-llm costuma ser tratado pelo wrapper LLM separado; aqui só
                # registramos o stub para rastreabilidade quando target_stage=None.
                if target_stage is not None and not dry_run:
                    # Se o chamador forçou um stage determinístico e o arquivo
                    # precisa de LLM, não salvamos — esse arquivo será pego pelo
                    # E2-llm wrapper.
                    continue
            else:
                stage = target_stage or _target_stage_for_file(
                    file_path, extratos_only=extratos_only, faturas_only=faturas_only
                )

            n_tx = len(result.get("transacoes", [])) + len(result.get("itens", []))
            if not is_llm:
                stats["processados"] += 1
                stats["transacoes_total"] += n_tx

            for note in result.get("notas", []):
                if isinstance(note, str):
                    if note.startswith("ERROR"):
                        stats["erros_validacao"] += 1
                    elif note.startswith("WARN"):
                        stats["warnings"] += 1

            if dry_run:
                continue

            # Overwrite protection: não sobrescrever extrato com 0 txns se já
            # há artefato com txns (mesma lógica do main legado).
            if n_tx == 0 and store.exists(stage, key):
                existing = store.read(stage, key) or {}
                existing_txns = len(existing.get("transacoes", [])) + len(existing.get("itens", []))
                if existing_txns > 0:
                    stats["skipped_overwrite"] += 1
                    log(
                        LOG_UNIFIED,
                        "WARN",
                        f"  SKIP: {stage}/{key} já tem {existing_txns} txns; "
                        f"não sobrescrever com resultado de 0 txns",
                    )
                    continue

            emit_item_progress(
                pipeline_run_id,
                emit_stage,
                current_item=file_path.name,
                items_done=idx,
                items_total=total_files,
                phase="persisting",
            )
            store.write(stage, key, result)
            log(
                LOG_UNIFIED,
                "INFO" if n_tx > 0 else "WARN",
                f"  → store.write({stage}, {key}, {n_tx} tx)",
            )

        except Exception as e:
            stats["erros_validacao"] += 1
            log(LOG_UNIFIED, "ERROR", f"  Failed: {file_path.name} — {e}")

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
