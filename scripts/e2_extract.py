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

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.e2.common import DATA_DIR, OUTPUT_DIR, log, set_verbose
from scripts.e2.registry import (
    NON_STATEMENT_TYPES, is_investment_type, route_to_parser,
)
from scripts.e2.validation import validate_extrato_result, validate_fatura_result

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


VALID_EXTENSIONS = (
    "-0_original.pdf", "-0_original.csv",
    "-0_original.xls", "-0_original.xlsx",
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
    extratos_only: bool = False, faturas_only: bool = False
) -> List[Path]:
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

    return result


def make_output_name(filename: str) -> str:
    """Generate output JSON filename from source filename."""
    out_name = re.sub(
        r'(-0_original)?\.(pdf|csv|xls|xlsx)$',
        '-2_extract.json',
        filename,
        flags=re.IGNORECASE
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

    for file_path in files:
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
                    log(LOG_UNIFIED, "WARN",
                        f"  SKIP: {stage}/{key} já tem {existing_txns} txns; "
                        f"não sobrescrever com resultado de 0 txns")
                    continue

            store.write(stage, key, result)
            log(LOG_UNIFIED, "INFO" if n_tx > 0 else "WARN",
                f"  → store.write({stage}, {key}, {n_tx} tx)")

        except Exception as e:
            stats["erros_validacao"] += 1
            log(LOG_UNIFIED, "ERROR", f"  Failed: {file_path.name} — {e}")

    return stats


def main(root_dir: Path = None):
    if root_dir:
        from scripts.e2.common import _init_config as _e2_init_config
        _e2_init_config(root_dir)
        from scripts.e2 import common as _e2c
        global DATA_DIR, OUTPUT_DIR
        DATA_DIR = _e2c.DATA_DIR
        OUTPUT_DIR = _e2c.OUTPUT_DIR

    parser = argparse.ArgumentParser(
        description="E2 Extraction — Unified deterministic parsers for financial documents"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without writing files")
    parser.add_argument("--file", type=str, default=None,
                        help="Process a specific file")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: processed/E2_extracts/)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress debug output")
    parser.add_argument("--extratos-only", action="store_true",
                        help="Process only extratos (bank statements)")
    parser.add_argument("--faturas-only", action="store_true",
                        help="Process only faturas (credit card invoices)")

    args = parser.parse_args([] if root_dir else None)

    if args.quiet:
        set_verbose(False)

    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    log(LOG_UNIFIED, "INFO", "=" * 60)
    log(LOG_UNIFIED, "INFO", "E2 EXTRACTION — Unified Deterministic Parsers")
    log(LOG_UNIFIED, "INFO", "=" * 60)

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            file_path = DATA_DIR / args.file
        if not file_path.exists():
            log(LOG_UNIFIED, "ERROR", f"Arquivo não encontrado: {args.file}")
            sys.exit(1)
        files = [file_path]
    else:
        files = find_all_files(
            extratos_only=args.extratos_only,
            faturas_only=args.faturas_only
        )

    if not files:
        log(LOG_UNIFIED, "INFO", "Nenhum arquivo encontrado para processar.")
        return

    log(LOG_UNIFIED, "INFO", f"Encontrados {len(files)} arquivos para processar")

    stats = {
        "processados": 0,
        "transacoes_total": 0,
        "llm_fallback": 0,
        "erros_validacao": 0,
        "warnings": 0,
    }

    for file_path in files:
        try:
            result = process_file(file_path, dry_run=args.dry_run)
            if result is None:
                continue

            if result.get("requires_llm_fallback"):
                stats["llm_fallback"] += 1
                log(LOG_UNIFIED, "WARN", f"  → Requer LLM fallback: {file_path.name}")
                continue

            n_tx = len(result.get("transacoes", []))
            n_tx += len(result.get("itens", []))
            stats["processados"] += 1
            stats["transacoes_total"] += n_tx

            for note in result.get("notas", []):
                if isinstance(note, str):
                    if note.startswith("ERROR"):
                        stats["erros_validacao"] += 1
                    elif note.startswith("WARN"):
                        stats["warnings"] += 1

            if not args.dry_run:
                # Overwrite protection: não sobrescrever extrato/fatura com dados por resultado vazio
                is_fatura = _is_fatura_file(file_path.name)
                out_name = make_output_name(file_path.name)
                out_path = output_dir / out_name

                if n_tx == 0 and out_path.exists():
                    try:
                        existing = json.loads(out_path.read_text(encoding='utf-8'))
                        existing_txns = len(existing.get("transacoes", [])) + len(existing.get("itens", []))
                        if existing_txns > 0:
                            log(LOG_UNIFIED, "WARN",
                                f"  SKIP: {out_name} já tem {existing_txns} txns; "
                                f"não sobrescrever com resultado de 0 txns")
                            continue
                    except (json.JSONDecodeError, IOError):
                        pass

                out_path = save_result(result, file_path.name, output_dir)
                log_level = "WARN" if n_tx == 0 else "INFO"
                log(LOG_UNIFIED, log_level, f"  → Salvo: {out_path.name} ({n_tx} transações)")

        except Exception as e:
            stats["erros_validacao"] += 1
            log(LOG_UNIFIED, "ERROR", f"  Failed: {file_path.name} — {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)

    # Summary
    print("\n" + "=" * 60, file=sys.stderr)
    log(LOG_UNIFIED, "SUMMARY", f"Processados: {stats['processados']}")
    log(LOG_UNIFIED, "SUMMARY", f"Total transações: {stats['transacoes_total']}")
    log(LOG_UNIFIED, "SUMMARY", f"LLM fallback: {stats['llm_fallback']}")
    log(LOG_UNIFIED, "SUMMARY", f"Erros de validação: {stats['erros_validacao']}")
    log(LOG_UNIFIED, "SUMMARY", f"Warnings: {stats['warnings']}")
    print("=" * 60, file=sys.stderr)

    if stats["erros_validacao"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
