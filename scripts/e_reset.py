#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
E-reset / E-reset-from — Pipeline completo: reset + reprocessamento

Usage:
  python scripts/e_reset.py                  # Reprocessamento completo (E0→E6)
  python scripts/e_reset.py --from E3        # Reprocessamento parcial de E3 em diante
  python scripts/e_reset.py --from E4        # Reprocessamento parcial de E4 em diante
  python scripts/e_reset.py --dry-run        # Show what would be deleted (no changes)
  python scripts/e_reset.py --from E5 --dry-run
  python scripts/e_reset.py --move-to-inbox  # E-full-reset: data/+members/ → inbox/
  python scripts/e_reset.py --move-to-inbox --interactive  # E-full-reset interativo (para em etapas LLM)
  python scripts/e_reset.py --continue       # Retoma pipeline interativo após etapa LLM

Valid --from values: E0, E1, E2-faturas, E3, E4, E5, E5.N, E6, E7

Sequência completa (sem --from):
  E0 Unlock → E0 Audit → E0 Route → E1 → E1.5 → E1.5c → E2-llm → E2-fat → E2-ext →
  E3 → E4 → E5 → E5.N → E6 → E7-crossval → E7-review → E7-apply → E6-final

Modo padrão: etapas determinísticas rodam automaticamente, LLM são puladas com lembrete.
Modo --interactive: pipeline PARA em cada etapa LLM (exit code 10), retoma com --continue.

Author: Claude Opus 4.6
Date: 2026-04-05
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# =============================================================================
# Paths
# =============================================================================
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent

PROCESSED_DIR = PROJECT_DIR / "processed"
E2_EXTRACTS   = PROCESSED_DIR / "E2_extracts"
E3_RECONCILED = PROCESSED_DIR / "E3_reconciled"
E4_UNIFIED    = PROCESSED_DIR / "E4_unified"
E5_ANALYSIS   = PROCESSED_DIR / "E5_analysis"

MEMBERS_DIR   = PROJECT_DIR / "members"
DATA_DIR      = PROJECT_DIR / "data"
INBOX_DIR     = PROJECT_DIR / "inbox"
OUTPUT_DIR    = PROJECT_DIR / "output"
LOGS_DIR      = PROJECT_DIR / "logs"
SCRATCH_DIR   = PROJECT_DIR / "_scratch"
STATE_FILE    = SCRATCH_DIR / ".e_reset_state.json"
E7_REVIEW    = PROCESSED_DIR / "E7_review"
REVIEW_TEMPLATE_PATH = E7_REVIEW / "e7_review_template.json"

def _load_json_config(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

_PIPELINE_CONFIG = _load_json_config(PROJECT_DIR / "config" / "pipeline.json")
_LOG_FILES_CONFIG = _PIPELINE_CONFIG.get("log_files", {})

def _load_output_glob() -> str:
    """Build output HTML glob from family_members.json config."""
    fm_path = PROJECT_DIR / "config" / "family_members.json"
    if fm_path.exists():
        with open(fm_path, "r", encoding="utf-8") as f:
            fm = json.load(f)
        pattern = fm.get("output_filename_pattern", "")
        if pattern:
            return pattern.replace("{date}", "*")
    return "relatorio_financeiro_*.html"

_OUTPUT_HTML_GLOB = _load_output_glob()

# =============================================================================
# Artifact definitions — what to delete at each stage
# =============================================================================

OPERATIONAL_LOGS = [LOGS_DIR / name for name in _LOG_FILES_CONFIG.get("operational", [
    "run_log.md", "reconciliation.md", "divergences.md",
    "e3_e4_execution_report.md", "quick_reference.txt",
])]

PRESERVED_LOGS = {LOGS_DIR / name for name in _LOG_FILES_CONFIG.get("preserved", [
    "inbox_log.md", "qa_log.md",
])}

def _glob(pattern: str) -> list[Path]:
    """Resolve glob pattern relative to PROJECT_DIR."""
    return [Path(p) for p in glob.glob(str(PROJECT_DIR / pattern))]


def artifacts_purge_data() -> list[Path]:
    """Artifacts in data/ — all files inside subdirectories.
    Used by --purge-data to force full reprocessing from inbox/.
    Preserves directory structure (financial_statements/, income_tax_br/, etc.)
    but removes all files within them."""
    files: list[Path] = []
    if DATA_DIR.is_dir():
        for child in DATA_DIR.rglob("*"):
            if child.is_file() and child.name != ".DS_Store":
                files.append(child)
    return files


def move_data_and_members_to_inbox(dry_run: bool = False) -> int:
    """Move ALL files from data/ and members/ back to inbox/ for re-routing.

    Moves:
      - data/**/*  (all files in all subdirectories)
      - members/*-0_original.*  (only originals, NOT extract/unified/enriched)

    Preserves:
      - Empty directory structure in data/ (financial_statements/, etc.)
      - E1 artifacts in members/ (extract, unified, enriched)
      - .DS_Store files

    Returns count of files moved.
    """
    import shutil

    if not INBOX_DIR.is_dir():
        INBOX_DIR.mkdir(parents=True, exist_ok=True)

    count = 0

    # --- Move files from data/ subdirectories → inbox/ ---
    if DATA_DIR.is_dir():
        for child in sorted(DATA_DIR.rglob("*")):
            if child.is_file() and child.name != ".DS_Store":
                dest = INBOX_DIR / child.name
                # Handle name collision (unlikely but safe)
                if dest.exists():
                    stem = dest.stem
                    suffix = dest.suffix
                    i = 1
                    while dest.exists():
                        dest = INBOX_DIR / f"{stem}_dup{i}{suffix}"
                        i += 1
                if dry_run:
                    print(f"  [DRY-RUN] Moveria: data/{child.relative_to(DATA_DIR)} → inbox/{dest.name}")
                else:
                    try:
                        shutil.move(str(child), str(dest))
                        print(f"  Movido: data/{child.relative_to(DATA_DIR)} → inbox/{dest.name}")
                    except Exception as e:
                        # Fallback: copy + truncate (mounted FS may not support move)
                        try:
                            shutil.copy2(str(child), str(dest))
                            # Write valid empty JSON instead of empty bytes to prevent parsing errors
                            if child.suffix.lower() == '.json':
                                child.write_text("{}")
                            else:
                                child.write_bytes(b"")
                            child.unlink()
                            print(f"  Movido (copy+del): data/{child.relative_to(DATA_DIR)} → inbox/{dest.name}")
                        except Exception as e2:
                            print(f"  [ERRO] Não conseguiu mover {child.name}: {e2}")
                            continue
                count += 1

    # --- Move original files from members/ → inbox/ ---
    if MEMBERS_DIR.is_dir():
        for child in sorted(MEMBERS_DIR.iterdir()):
            if child.is_file() and child.name != ".DS_Store" and "-0_original." in child.name:
                dest = INBOX_DIR / child.name
                if dest.exists():
                    stem = dest.stem
                    suffix = dest.suffix
                    i = 1
                    while dest.exists():
                        dest = INBOX_DIR / f"{stem}_dup{i}{suffix}"
                        i += 1
                if dry_run:
                    print(f"  [DRY-RUN] Moveria: members/{child.name} → inbox/{dest.name}")
                else:
                    try:
                        shutil.move(str(child), str(dest))
                        print(f"  Movido: members/{child.name} → inbox/{dest.name}")
                    except Exception as e:
                        try:
                            shutil.copy2(str(child), str(dest))
                            child.unlink()
                            print(f"  Movido (copy+del): members/{child.name} → inbox/{dest.name}")
                        except Exception as e2:
                            print(f"  [ERRO] Não conseguiu mover {child.name}: {e2}")
                            continue
                count += 1

    return count


def artifacts_full_reset() -> list[Path]:
    """Artifacts deleted on a full reset (E0→E6).
    NOTE: E0 artifacts (data/, members/ originals) and E1 artifacts
    (members/*-1a_extract.json, members-1b_unified.json, members-1c_enriched.md)
    are NOT deleted because E0/E1 are LLM-driven and cannot be regenerated
    automatically. Use manual deletion if needed."""
    files: list[Path] = []
    # E2 — all extracted JSONs
    files += _glob("processed/E2_extracts/*.json")
    # E3
    files += _glob("processed/E3_reconciled/*.json")
    # E4
    files += _glob("processed/E4_unified/*.json")
    # E5
    files += _glob("processed/E5_analysis/*.json")
    # E2 summaries
    files += _glob("processed/E2_PROCESSING_SUMMARY.txt")
    files += _glob("processed/E2_TARGET_FILES_MANIFEST.txt")
    # E6 — HTML output + backups
    files += _glob(f"output/{_OUTPUT_HTML_GLOB}")
    files += _glob("output/*.html.bak")
    # Operational logs
    files += [f for f in OPERATIONAL_LOGS if f.exists()]
    # Python cache
    pycache = SCRIPTS_DIR / "__pycache__"
    if pycache.is_dir():
        files.append(pycache)
    return files


def artifacts_from(stage: str) -> list[Path]:
    """Artifacts deleted for E-reset-from <stage>."""
    files: list[Path] = []

    stages_cascade = {
        "E0":         ["E2-all", "E3", "E4", "E5", "E7", "E6"],   # Limpa TODOS E2 (extratos + faturas)
        "E1":         ["E2-all", "E3", "E4", "E5", "E7", "E6"],   # Limpa TODOS E2 (extratos + faturas)
        "E2-faturas": ["E2-faturas", "E3", "E4", "E5", "E7", "E6"],
        "E3":         ["E3", "E4", "E5", "E7", "E6"],
        "E4":         ["E4", "E5", "E7", "E6"],
        "E5":         ["E5", "E7", "E6"],
        "E5.N":       ["E5.N", "E7", "E6"],
        "E6":         ["E7", "E6"],
        "E7":         ["E7", "E6"],
    }

    cascade = stages_cascade[stage]

    if "E2-all" in cascade:
        # Full E2 cleanup: all extract JSONs + summaries (used by --from E0/E1)
        files += _glob("processed/E2_extracts/*.json")
        files += _glob("processed/E2_PROCESSING_SUMMARY.txt")
        files += _glob("processed/E2_TARGET_FILES_MANIFEST.txt")
    elif "E2-faturas" in cascade:
        # Partial E2 cleanup: only fatura JSONs (identified by 'tipo' field)
        e2_dir = PROCESSED_DIR / "E2_extracts"
        if e2_dir.is_dir():
            for fpath in e2_dir.glob("*-2_extract.json"):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    tipo = data.get("tipo", "").lower()
                    if tipo.startswith("fatura") or "cartao" in tipo:
                        files.append(fpath)
                except Exception:
                    # Fallback: match by filename pattern
                    if "fatura" in fpath.name.lower():
                        files.append(fpath)

    if "E3" in cascade:
        files += _glob("processed/E3_reconciled/*.json")

    if "E4" in cascade:
        files += _glob("processed/E4_unified/*.json")

    if "E5" in cascade:
        files += _glob("processed/E5_analysis/*.json")

    # E5.N — narrativas are stripped via strip_narrativas_from_e5_files()
    # called in main() between cleanup and execution phases (Fix #3)

    if "E7" in cascade:
        # E7 review template
        files += _glob("processed/E7_review/e7_review_template.json")

    if "E6" in cascade:
        files += _glob(f"output/{_OUTPUT_HTML_GLOB}")
        files += _glob("output/*.html.bak")

    # Operational logs (regenerated by pipeline)
    if any(s in cascade for s in ["E3", "E4", "E5"]):
        files += [f for f in OPERATIONAL_LOGS if f.exists()]

    # Python cache
    pycache = SCRIPTS_DIR / "__pycache__"
    if pycache.is_dir():
        files.append(pycache)

    return files


# =============================================================================
# Pre-checks (Fix #5)
# =============================================================================

def check_dependencies(stages: list[str]) -> list[str]:
    """Pre-check Python dependencies required by the stages that will run.
    Returns list of missing packages (empty = all OK)."""
    # Map stages to their required non-stdlib packages
    stage_deps: dict[str, list[tuple[str, str]]] = {
        "E2-faturas":  [("pdfplumber", "pip install pdfplumber")],
        "E2-extratos": [("pdfplumber", "pip install pdfplumber"),
                        ("xlrd", "pip install xlrd")],
        "E6":          [("pytz", "pip install pytz")],
    }

    missing = []
    checked = set()
    for stage in stages:
        for pkg, install_cmd in stage_deps.get(stage, []):
            if pkg in checked:
                continue
            checked.add(pkg)
            try:
                __import__(pkg)
            except ImportError:
                missing.append(f"  {pkg} (requerido por {stage}) → {install_cmd}")

    return missing


# =============================================================================
# Narrativas cleanup (Fix #3)
# =============================================================================

def strip_review_from_e5_files(dry_run: bool = False) -> int:
    """Remove 'review_metadata', 'strategic_insights', and 'inconsistencies_review'
    from E5 analysis JSON files. Ensures stale E7 review data is not carried over.
    Returns count of files modified."""
    if not E5_ANALYSIS.exists():
        return 0
    count = 0
    review_keys = ["review_metadata"]
    narr_review_keys = ["strategic_insights", "inconsistencies_review"]
    for fpath in E5_ANALYSIS.glob("*.json"):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            modified = False
            for k in review_keys:
                if k in data:
                    if dry_run:
                        print(f"  [DRY-RUN] Removeria '{k}' de {fpath.name}")
                    else:
                        del data[k]
                    modified = True
            narr = data.get("narrativas", {})
            for k in narr_review_keys:
                if k in narr:
                    if dry_run:
                        print(f"  [DRY-RUN] Removeria 'narrativas.{k}' de {fpath.name}")
                    else:
                        del narr[k]
                    modified = True
            if modified and not dry_run:
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  Removido dados E7 review de {fpath.name}")
            if modified:
                count += 1
        except Exception as e:
            print(f"  [AVISO] Falha ao processar {fpath.name}: {e}")
    return count


def strip_narrativas_from_e5_files(dry_run: bool = False) -> int:
    """Remove 'narrativas' key from all E5 analysis JSON files.
    Ensures stale narrativas are never carried over to E6 after an E5.N reset.
    Returns count of files modified."""
    if not E5_ANALYSIS.exists():
        print(f"  [WARN] Diretório {E5_ANALYSIS} não existe — nenhuma narrativa para limpar")
        return 0
    count = 0
    for fpath in E5_ANALYSIS.glob("*.json"):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "narrativas" in data:
                if dry_run:
                    print(f"  [DRY-RUN] Removeria 'narrativas' de {fpath.name}")
                else:
                    del data["narrativas"]
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"  Removido 'narrativas' de {fpath.name}")
                count += 1
        except Exception as e:
            print(f"  [AVISO] Falha ao processar {fpath.name}: {e}")
    return count


# =============================================================================
# Script execution — deterministic steps only
# =============================================================================

DETERMINISTIC_SCRIPTS = {
    "E1.5c":       SCRIPTS_DIR / "e15_consolidate.py",
    "E2-faturas":  SCRIPTS_DIR / "e2_extract.py",
    "E2-extratos": SCRIPTS_DIR / "e2_extract.py",
    "E3":          SCRIPTS_DIR / "e3_reconcile.py",
    "E4":          SCRIPTS_DIR / "e4_categorize.py",
    "E5":          SCRIPTS_DIR / "e5_analyze.py",
    "E5.N":        SCRIPTS_DIR / "e5n_narrativas.py",
    "E6":          SCRIPTS_DIR / "e6_render.py",
    "E7-crossval": SCRIPTS_DIR / "e7_review.py",
    "E7-apply":    SCRIPTS_DIR / "e7_review.py",
    "E6-final":    SCRIPTS_DIR / "e6_render.py",
}

LLM_STAGES = {"E1", "E1.5", "E2-llm", "E7-review"}

EXECUTION_ORDER_FULL = [
    "E1", "E1.5",                              # Wall 1 (LLM)
    "E1.5c",                                    # Deterministic consolidation
    "E2-llm",                                   # Wall 2 (LLM)
    "E2-faturas", "E2-extratos",
    "E3", "E4", "E5",
    "E5.N",                                     # Deterministic (narrativas)
    "E6",
    "E7-crossval",                              # Deterministic (cross-validation)
    "E7-review",                                # Wall 3 (LLM)
    "E7-apply",                                 # Deterministic (apply review)
    "E6-final",
]
EXECUTION_ORDER_FROM = {
    "E0":          ["E1", "E1.5", "E1.5c", "E2-llm", "E2-faturas", "E2-extratos", "E3", "E4", "E5", "E5.N", "E6", "E7-crossval", "E7-review", "E7-apply", "E6-final"],
    "E1":          ["E1", "E1.5", "E1.5c", "E2-llm", "E2-faturas", "E2-extratos", "E3", "E4", "E5", "E5.N", "E6", "E7-crossval", "E7-review", "E7-apply", "E6-final"],
    "E2-faturas":  ["E2-faturas", "E2-extratos", "E3", "E4", "E5", "E5.N", "E6", "E7-crossval", "E7-review", "E7-apply", "E6-final"],
    "E3":          ["E3", "E4", "E5", "E5.N", "E6", "E7-crossval", "E7-review", "E7-apply", "E6-final"],
    "E4":          ["E4", "E5", "E5.N", "E6", "E7-crossval", "E7-review", "E7-apply", "E6-final"],
    "E5":          ["E5", "E5.N", "E6", "E7-crossval", "E7-review", "E7-apply", "E6-final"],
    "E5.N":        ["E5.N", "E6", "E7-crossval", "E7-review", "E7-apply", "E6-final"],
    "E6":          ["E6", "E7-crossval", "E7-review", "E7-apply", "E6-final"],
    "E7":          ["E7-crossval", "E7-review", "E7-apply", "E6-final"],
}


STAGE_EXTRA_ARGS = {
    "E2-faturas":  ["--faturas-only"],
    "E2-extratos": ["--extratos-only"],
    "E7-crossval": [],
    "E7-apply":    ["--apply"],  # review JSON path appended dynamically
}


def run_script(stage: str, dry_run: bool, state: dict | None = None) -> bool:
    """Run a deterministic script. Returns True on success.
    For E7-apply, reads the review JSON path from state file."""
    script = DETERMINISTIC_SCRIPTS.get(stage)
    if not script:
        return False
    if not script.exists():
        print(f"  [ERRO] Script não encontrado: {script}")
        return False

    extra_args = list(STAGE_EXTRA_ARGS.get(stage, []))

    if stage == "E7-apply":
        review_path = (state or {}).get("review_json_path", "")
        if not review_path:
            candidates = sorted(SCRATCH_DIR.glob("e7_review_*.json"), reverse=True)
            if candidates:
                review_path = str(candidates[0])
            elif not dry_run:
                print(f"  [ERRO] E7-apply: nenhum review JSON encontrado.")
                print(f"         Salve o review preenchido em _scratch/e7_review_filled.json")
                return False
            else:
                review_path = "_scratch/e7_review_filled.json"
        extra_args.append(review_path)

    if dry_run:
        args_str = " ".join(extra_args)
        print(f"  [DRY-RUN] Executaria: python {script.name} {args_str}".rstrip())
        return True

    cmd = [sys.executable, str(script)] + extra_args
    args_str = " ".join(extra_args)
    print(f"  Executando: python {script.name} {args_str} ...".rstrip())
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_DIR),
        env=env,
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"  [ERRO] {script.name} falhou (exit code {result.returncode})")
        return False
    print(f"  [OK] {script.name} concluído")
    return True


# =============================================================================
# Delete artifacts
# =============================================================================

def delete_artifacts(files: list[Path], dry_run: bool) -> int:
    """Delete artifact files. Returns count of items deleted."""
    # Safety check: never delete preserved files
    safe_files = [f for f in files if f not in PRESERVED_LOGS]

    if not safe_files:
        print("  Nenhum artefato encontrado para deletar.")
        return 0

    count = 0
    for f in sorted(set(safe_files)):
        if f.is_dir():
            if dry_run:
                print(f"  [DRY-RUN] Removeria diretório: {f.relative_to(PROJECT_DIR)}")
            else:
                import shutil
                try:
                    shutil.rmtree(f)
                    print(f"  Removido dir: {f.relative_to(PROJECT_DIR)}")
                except PermissionError:
                    # Truncate all files inside directory instead
                    # Use valid empty JSON for .json files to prevent parsing errors
                    for child in f.rglob("*"):
                        if child.is_file():
                            try:
                                if child.suffix.lower() == '.json':
                                    child.write_text("{}")
                                else:
                                    child.write_text("")
                            except Exception:
                                pass
                    print(f"  Truncado conteúdo dir (sem permissão p/ deletar): {f.relative_to(PROJECT_DIR)}")
            count += 1
        elif f.is_file():
            if dry_run:
                print(f"  [DRY-RUN] Removeria: {f.relative_to(PROJECT_DIR)}")
            else:
                try:
                    f.unlink()
                    print(f"  Removido: {f.relative_to(PROJECT_DIR)}")
                except PermissionError:
                    # Fallback: truncate file when delete is not permitted (mounted FS)
                    # Use valid empty JSON for .json files to prevent parsing errors
                    try:
                        if f.suffix.lower() == '.json':
                            f.write_text("{}")
                        else:
                            f.write_text("")
                        print(f"  Truncado (sem permissão p/ deletar): {f.relative_to(PROJECT_DIR)}")
                    except Exception as e2:
                        print(f"  [AVISO] Não foi possível remover/truncar: {f.relative_to(PROJECT_DIR)} ({e2})")
            count += 1

    return count


# =============================================================================
# Interactive mode — state management
# =============================================================================

EXIT_CODE_WALL = 10  # Pipeline paused, awaiting LLM intervention

WALL_INSTRUCTIONS = {
    "E1": {
        "wall": "wall_1",
        "title": "WALL 1: E1 (mapeamento de membros) + E1.5 (baseline patrimonial IRPF)",
        "stages_covered": ["E1", "E1.5"],
        "instructions": [
            "1. Leia os documentos em data/ (holerites, currículos, docs pessoais)",
            "2. Leia config/definitions.md para dados cadastrais canônicos",
            "3. Para cada membro, crie members/[membro]_[tipo]-1a_extract.json",
            "4. Consolide em members/members-1b_unified.json",
            "5. Gere members/members-1c_enriched.md",
            "6. Leia declarações IRPF em data/income_tax_br/",
            "7. Crie processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json",
            "   (formato: {declarations: [...], membros: [...]})",
        ],
        "artifacts_expected": [
            "members/members-1b_unified.json",
            "members/members-1c_enriched.md",
            "processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json",
        ],
        "next_stage_after_wall": "E1.5c",
    },
    "E2-llm": {
        "wall": "wall_2",
        "title": "WALL 2: E2-llm (extração LLM de investimentos/CDBs/IRPF)",
        "stages_covered": ["E2-llm"],
        "instructions": [
            "1. Identifique arquivos em data/ sem parser determinístico:",
            "   investimentosposicao, carteirarendafixa, cdbdetalhes, cdbresumo,",
            "   informerendimentos, irpf",
            "2. Para cada arquivo, leia o conteúdo e extraia transações/posições",
            "3. Crie processed/E2_extracts/[nome]-2_extract.json para cada um",
            "4. Use o formato padrão E2 (tipo, membro, instituicao, transacoes[])",
        ],
        "artifacts_expected": [],  # Variable — depends on files present
        "next_stage_after_wall": "E2-faturas",
    },
    "E7-review": {
        "wall": "wall_3",
        "title": "WALL 3: E7-review (review holístico pós-relatório)",
        "stages_covered": ["E7-review"],
        "instructions": [
            "1. Leia o template em processed/E7_review/e7_review_template.json",
            "2. Leia o relatório HTML em output/",
            "3. Leia config/methodology.md para persona e abordagem",
            "4. Preencha o template com refinamentos usando visão holística",
            "5. Salve o review preenchido em _scratch/e7_review_filled.json",
        ],
        "artifacts_expected": [
            "_scratch/e7_review_filled.json",
        ],
        "next_stage_after_wall": "E7-apply",
    },
}


def _save_state(state: dict) -> None:
    """Persist interactive pipeline state to _scratch/."""
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _load_state() -> dict | None:
    """Load interactive pipeline state. Returns None if no state file."""
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _clear_state() -> None:
    """Remove state file after pipeline completes."""
    if STATE_FILE.exists():
        try:
            STATE_FILE.unlink()
        except OSError:
            pass


def _print_wall(wall_info: dict, state: dict) -> None:
    """Print wall instructions and save state."""
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE PAUSADO — {wall_info['title']}")
    print("=" * 60)
    print()
    print("  Instruções para o agente LLM:")
    for line in wall_info["instructions"]:
        print(f"    {line}")
    if wall_info["artifacts_expected"]:
        print()
        print("  Artefatos esperados após conclusão:")
        for art in wall_info["artifacts_expected"]:
            print(f"    - {art}")
    print()
    print("  Após concluir, retome o pipeline com:")
    print("    python scripts/e_reset.py --continue")
    print()

    state["wall_hit"] = wall_info["wall"]
    state["next_stage"] = wall_info["next_stage_after_wall"]
    state["llm_stages_pending"] = wall_info["stages_covered"]
    _save_state(state)


def _validate_wall_artifacts(wall_info: dict) -> list[str]:
    """Check that expected artifacts from a wall exist. Returns list of warnings."""
    warnings = []
    for art_rel in wall_info.get("artifacts_expected", []):
        art_path = PROJECT_DIR / art_rel
        if not art_path.exists():
            warnings.append(f"Artefato esperado não encontrado: {art_rel}")
        elif art_path.stat().st_size < 10:
            warnings.append(f"Artefato vazio ou muito pequeno: {art_rel}")
    return warnings


# =============================================================================
# Validation
# =============================================================================

def _check_json_content(fpath: Path, required_keys: list[str]) -> str | None:
    """Check that a JSON file is parseable and has non-empty required keys.
    Returns warning string or None if OK."""
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in required_keys:
            val = data.get(key)
            if val is None or val == {} or val == []:
                return f"{fpath.name}: campo '{key}' vazio ou ausente"
    except json.JSONDecodeError:
        return f"{fpath.name}: JSON inválido (parse error)"
    except Exception as e:
        return f"{fpath.name}: erro ao ler ({e})"
    return None


def validate(from_stage: str | None) -> list[str]:
    """Post-execution validation: checks file existence AND content. Returns list of warnings."""
    warnings = []

    # Stages that affect E3 and downstream (E0/E1 trigger full cascade)
    triggers_e3 = (None, "E0", "E1", "E2-faturas", "E3")
    triggers_e4 = triggers_e3 + ("E4",)
    triggers_e5 = triggers_e4 + ("E5",)

    if from_stage in triggers_e3:
        e3_files = list(E3_RECONCILED.glob("*.json"))
        if not e3_files:
            warnings.append("E3_reconciled/ está vazio — faltam arquivos reconciliados")
        else:
            for fpath in e3_files:
                w = _check_json_content(fpath, ["transacoes"])
                if w:
                    warnings.append(f"  E3: {w}")

    if from_stage in triggers_e4:
        e4_files = list(E4_UNIFIED.glob("*.json"))
        if not e4_files:
            warnings.append("E4_unified/ está vazio — faltam arquivos categorizados")
        else:
            for fpath in e4_files:
                # receitas/despesas have total_geral; others have dados
                fname_lower = fpath.name.lower()
                if "receitas" in fname_lower:
                    w = _check_json_content(fpath, ["total_geral", "periodo"])
                elif "despesas" in fname_lower:
                    w = _check_json_content(fpath, ["total_geral", "periodo"])
                elif "fluxo" in fname_lower:
                    w = _check_json_content(fpath, ["meses_ordenados"])
                elif "transferencias" in fname_lower:
                    w = _check_json_content(fpath, ["total_geral"])
                else:
                    w = _check_json_content(fpath, [])
                if w:
                    warnings.append(f"  E4: {w}")

    if from_stage in triggers_e5:
        e5_files = list(E5_ANALYSIS.glob("*.json"))
        if not e5_files:
            warnings.append("E5_analysis/ está vazio — falta análise")
        else:
            for fpath in e5_files:
                w = _check_json_content(fpath, ["score", "patrimonio"])
                if w:
                    warnings.append(f"  E5: {w}")

    html_files = list(OUTPUT_DIR.glob(_OUTPUT_HTML_GLOB))
    if not html_files:
        warnings.append("output/ não contém relatório HTML")

    return warnings


# =============================================================================
# Main
# =============================================================================

VALID_FROM_STAGES = ["E0", "E1", "E2-faturas", "E3", "E4", "E5", "E5.N", "E6", "E7"]


def main():
    parser = argparse.ArgumentParser(
        description="Reprocessamento completo do pipeline financeiro (E0→E6)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Exemplos:
  python scripts/e_reset.py                                  # Reprocessamento completo (E0→E6)
  python scripts/e_reset.py --from E4                        # Reprocessamento de E4 em diante
  python scripts/e_reset.py --from E3 --dry-run              # Ver o que seria apagado
  python scripts/e_reset.py --clean-only                     # Só limpar, não executar
  python scripts/e_reset.py --move-to-inbox --interactive    # E-full-reset interativo
  python scripts/e_reset.py --continue                       # Retomar após etapa LLM

Sequência completa (modo interativo):
  [E1] → [E1.5] → E1.5c → [E2-llm] → E2-fat → E2-ext → E3 → E4 → E5 →
  E5.N → E6 → E7-crossval → [E7-review] → E7-apply → E6-final
  Colchetes = etapa LLM (wall — pipeline para e aguarda)

Estágios válidos para --from: {', '.join(VALID_FROM_STAGES)}
        """,
    )
    parser.add_argument(
        "--from", dest="from_stage", choices=VALID_FROM_STAGES, default=None,
        help="Etapa inicial para reset parcial (E-reset-from). Sem este flag = reset completo.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Mostrar o que seria feito sem executar nenhuma mudança.",
    )
    parser.add_argument(
        "--clean-only", action="store_true",
        help="Apenas apagar artefatos, sem re-executar o pipeline.",
    )
    parser.add_argument(
        "--no-validate", action="store_true",
        help="Pular validação pós-execução.",
    )
    parser.add_argument(
        "--no-audit", action="store_true",
        help="Pular auditoria de integridade (e0_audit) antes do reset.",
    )
    parser.add_argument(
        "--no-unlock", action="store_true",
        help="Pular desbloqueio de PDFs protegidos por senha (e0_unlock) antes do reset.",
    )
    parser.add_argument(
        "--no-route", action="store_true",
        help="Pular roteamento automático do inbox (e0_route) antes do reset.",
    )
    parser.add_argument(
        "--move-to-inbox", action="store_true",
        help="Mover TODOS os arquivos de data/ e originais de members/ de volta para inbox/ "
             "antes do reset, permitindo re-roteamento completo (usado por E-full-reset).",
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="Modo interativo: pipeline PARA em etapas LLM (exit code 10) e retoma com --continue. "
             "Permite orquestrar o pipeline completo incluindo etapas LLM.",
    )
    parser.add_argument(
        "--continue", dest="continue_from_state", action="store_true",
        help="Retomar pipeline interativo a partir do state file (_scratch/.e_reset_state.json). "
             "Usar após concluir a etapa LLM indicada na wall anterior.",
    )

    args = parser.parse_args()
    dry_run = args.dry_run
    from_stage = args.from_stage
    interactive = args.interactive
    continue_mode = args.continue_from_state

    # --- Handle --continue: resume from state file ---
    if continue_mode:
        return _main_continue(args)

    # Header
    if from_stage:
        mode = f"Reprocessamento a partir de {from_stage}"
    elif interactive:
        mode = "Reprocessamento INTERATIVO completo (E0→E6, com walls LLM)"
    else:
        mode = "Reprocessamento completo (E0→E6)"

    print("=" * 60)
    print(f"  {mode}")
    if dry_run:
        print("  MODO: --dry-run (nenhuma mudança será feita)")
    if interactive:
        print("  MODO: --interactive (pipeline para em etapas LLM)")
    print(f"  Projeto: {PROJECT_DIR}")
    print("=" * 60)

    # Initialize interactive state
    state: dict | None = None
    if interactive:
        state = {
            "started_at": datetime.now().isoformat(),
            "flags": {
                "move_to_inbox": args.move_to_inbox,
                "interactive": True,
                "dry_run": dry_run,
                "from_stage": from_stage,
                "no_validate": args.no_validate,
            },
            "completed_stages": [],
            "next_stage": None,
            "wall_hit": None,
        }
        _save_state(state)

    # --- Phase -1: Move data/ + members/ originals back to inbox/ ---
    if args.move_to_inbox:
        print(f"\n--- Fase -1: Movendo arquivos de data/ e members/ → inbox/ ---")
        moved = move_data_and_members_to_inbox(dry_run)
        print(f"  Total: {moved} arquivo(s) {'identificados' if dry_run else 'movidos'} para inbox/")

        # Also clean E1 artifacts from members/ (extract, unified, enriched)
        # since originals are gone and E1 must be re-executed
        if not dry_run:
            e1_artifacts = []
            if MEMBERS_DIR.is_dir():
                for child in MEMBERS_DIR.iterdir():
                    if child.is_file() and child.name != ".DS_Store" and "-0_original." not in child.name:
                        e1_artifacts.append(child)
            if e1_artifacts:
                print(f"\n  Limpando {len(e1_artifacts)} artefato(s) E1 em members/ (serão recriados):")
                for f in e1_artifacts:
                    try:
                        f.unlink()
                        print(f"    Removido: members/{f.name}")
                    except Exception:
                        try:
                            f.write_text("")
                            print(f"    Truncado: members/{f.name}")
                        except Exception as e2:
                            print(f"    [AVISO] Não removeu: members/{f.name} ({e2})")
        else:
            e1_count = 0
            if MEMBERS_DIR.is_dir():
                for child in MEMBERS_DIR.iterdir():
                    if child.is_file() and child.name != ".DS_Store" and "-0_original." not in child.name:
                        print(f"  [DRY-RUN] Removeria artefato E1: members/{child.name}")
                        e1_count += 1
            if e1_count:
                print(f"  Total: {e1_count} artefato(s) E1 seriam removidos")

    # --- Fix #10: Warn about --clean-only with E5.N ---
    if args.clean_only and from_stage == "E5.N":
        print("\n  ⚠️  AVISO: --clean-only com --from E5.N")
        print("     Narrativas são internas ao JSON do E5 — não há artefatos de arquivo para limpar.")
        print("     Apenas output/relatorio_*.html será removido.")
        print("     Para limpar narrativas + re-executar, rode sem --clean-only.")
        print()

    # --- Phase 0.0: Unlock password-protected PDFs in inbox ---
    unlock_script = SCRIPTS_DIR / "e0_unlock.py"
    passwords_file = PROJECT_DIR / "config" / "passwords.txt"
    inbox_dir = PROJECT_DIR / "inbox"
    if not args.no_unlock and unlock_script.exists() and passwords_file.exists() and inbox_dir.exists():
        inbox_pdfs = list(inbox_dir.glob("*.pdf"))
        if inbox_pdfs:
            print(f"\n--- Fase 0.0: Desbloqueio de PDFs no inbox ({len(inbox_pdfs)} PDFs) ---")
            if dry_run:
                print("  [DRY-RUN] Executaria: python e0_unlock.py --dry-run")
                subprocess.run(
                    [sys.executable, str(unlock_script), "--dry-run"],
                    cwd=str(PROJECT_DIR),
                    capture_output=False,
                )
            else:
                result = subprocess.run(
                    [sys.executable, str(unlock_script)],
                    cwd=str(PROJECT_DIR),
                    capture_output=False,
                )
                if result.returncode == 2:
                    # Exit 2 = PDFs protegidos sem senha válida (alerta, não fatal)
                    print("\n  [ALERTA] Alguns PDFs não puderam ser desbloqueados.")
                    print("  O pipeline prosseguirá, mas esses arquivos serão ignorados em E2.")
                    print("  Veja logs/qa_log.md para detalhes.\n")
                elif result.returncode != 0:
                    print("  [AVISO] e0_unlock falhou inesperadamente. Prosseguindo.")
        else:
            print(f"\n--- Fase 0.0: Inbox vazio, pulando unlock ---")

    # --- Phase 0: Pre-audit (e0_audit) ---
    audit_script = SCRIPTS_DIR / "e0_audit.py"
    if not args.no_audit and audit_script.exists():
        print(f"\n--- Fase 0: Auditoria de integridade (e0_audit) ---")
        if dry_run:
            print("  [DRY-RUN] Executaria: python e0_audit.py --json")
        else:
            result = subprocess.run(
                [sys.executable, str(audit_script), "--json"],
                cwd=str(PROJECT_DIR),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                try:
                    audit = json.loads(result.stdout)
                    summary = audit.get("summary", {})
                    errors = summary.get("errors", 0)
                    warnings_count = summary.get("warnings", 0)
                    info = summary.get("info", 0)

                    if errors > 0:
                        print(f"  [ERRO] Auditoria encontrou {errors} erro(s)!")
                        # Show the issues
                        for check_data in audit.get("checks", {}).values():
                            for issue in check_data.get("issues", []):
                                if issue["severity"] == "ERROR":
                                    print(f"    - {issue['file']}: {issue['issue']}")
                        print(f"\n  Corrija os erros acima antes de rodar o reset.")
                        print(f"  Para detalhes: python scripts/e0_audit.py")
                        print(f"  Para ignorar: adicione --no-audit")
                        sys.exit(1)
                    elif warnings_count > 0:
                        print(f"  [AVISO] {warnings_count} aviso(s), {info} info(s)")
                        for check_data in audit.get("checks", {}).values():
                            for issue in check_data.get("issues", []):
                                if issue["severity"] == "WARNING":
                                    print(f"    - {issue['file']}: {issue['issue']}")
                        print(f"  Prosseguindo (avisos não bloqueiam o reset).")
                    else:
                        print(f"  [OK] Nenhum problema significativo ({info} info).")
                except json.JSONDecodeError:
                    print("  [AVISO] Não foi possível parsear saída do e0_audit. Prosseguindo.")
            else:
                print(f"  [AVISO] e0_audit falhou (exit {result.returncode}). Prosseguindo.")

    # --- Phase 0.5: Auto-route inbox files (e0_route) ---
    route_script = SCRIPTS_DIR / "e0_route.py"
    if not args.no_route and route_script.exists() and inbox_dir.exists():
        inbox_files = [f for f in inbox_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
        if inbox_files:
            print(f"\n--- Fase 0.5: Roteamento automático do inbox ({len(inbox_files)} arquivos) ---")
            try:
                from e0_route import route_all as e0_route_all
                route_stats = e0_route_all(base=PROJECT_DIR, dry_run=dry_run, use_llm=True)
                routed = route_stats.get("routed", 0)
                unid = route_stats.get("unidentified", 0)
                print(f"  Roteados: {routed} | Não identificados: {unid} | Duplicatas: {route_stats.get('duplicates', 0)}")
                if unid > 0:
                    print(f"  [AVISO] {unid} arquivo(s) não identificado(s) — verificar nao_identificados/")
            except Exception as e:
                print(f"  [AVISO] e0_route falhou: {e}. Prosseguindo.")
        else:
            print(f"\n--- Fase 0.5: Inbox vazio, pulando roteamento ---")

    # --- Fix #5: Pre-check dependencies before any destructive action ---
    if from_stage:
        stages = EXECUTION_ORDER_FROM[from_stage]
    else:
        stages = EXECUTION_ORDER_FULL

    if not args.clean_only:
        det_stages = [s for s in stages if s in DETERMINISTIC_SCRIPTS]
        missing_deps = check_dependencies(det_stages)
        if missing_deps:
            print("\n  [ERRO] Dependências Python faltando:")
            for dep in missing_deps:
                print(f"    {dep}")
            print("\n  Instale as dependências antes de rodar o reset.")
            sys.exit(1)

    # --- Phase 1: Clean artifacts ---
    print(f"\n--- Fase 1: Limpeza de artefatos ---")
    if from_stage:
        files = artifacts_from(from_stage)
    else:
        files = artifacts_full_reset()

    count = delete_artifacts(files, dry_run)
    print(f"  Total: {count} item(s) {'identificados' if dry_run else 'removidos'}")

    # --- Fix #3: Strip narrativas from E5 JSON when E5.N is in cascade ---
    if "E5.N" in stages:
        print(f"\n--- Fase 1.5: Limpeza de narrativas (E5.N) ---")
        stripped = strip_narrativas_from_e5_files(dry_run)
        if stripped:
            print(f"  Total: {stripped} arquivo(s) com narrativas {'identificados' if dry_run else 'limpos'}")
        else:
            print("  Nenhum arquivo E5 com narrativas encontrado.")

    # --- Strip E7 review data when E7-crossval or E7-review is in cascade ---
    if "E7-crossval" in stages or "E7-review" in stages:
        print(f"\n--- Fase 1.6: Limpeza de review E7 ---")
        stripped_r = strip_review_from_e5_files(dry_run)
        if stripped_r:
            print(f"  Total: {stripped_r} arquivo(s) com review {'identificados' if dry_run else 'limpos'}")
        else:
            print("  Nenhum dado de review E7 encontrado.")

    if args.clean_only:
        print("\n--clean-only: pulando re-execução do pipeline.")
        print("Concluído.")
        return

    llm_descriptions = {
        "E1":       "Extração de dados dos membros (holerite, docs pessoais)",
        "E1.5":     "Baseline patrimonial (IRPF, XLSX imóveis/veículos)",
        "E2-llm":   "Extração LLM de investimentos/CDBs sem parser determinístico",
        "E7-review": "Review holístico pós-relatório (preencher template com persona)",
    }

    # --- Pre-flight: detect if LLM stages must run before deterministic ones ---
    leading_llm = []
    first_det = None
    for s in stages:
        if s in LLM_STAGES and first_det is None:
            leading_llm.append(s)
        elif s in DETERMINISTIC_SCRIPTS and first_det is None:
            first_det = s
            break

    if not interactive:
        # Non-interactive mode: same behavior as before (skip LLM, run det)
        needs_llm_first = False
        if leading_llm and first_det and not dry_run:
            if first_det in ("E1.5c", "E2-faturas"):
                data_fs = PROJECT_DIR / "data" / "financial_statements"
                has_inputs = data_fs.is_dir() and any(data_fs.glob("*fatura*-0_original.pdf"))
                if not has_inputs:
                    needs_llm_first = True
            elif first_det == "E3":
                has_inputs = E2_EXTRACTS.is_dir() and any(E2_EXTRACTS.glob("*-2_extract.json"))
                if not has_inputs:
                    needs_llm_first = True

        if needs_llm_first:
            print(f"\n--- Fase 2: Etapas LLM necessárias primeiro ---")
            print(f"\n  Os inputs para {first_det} não existem ainda.")
            print(f"  As etapas LLM abaixo precisam ser executadas primeiro:\n")
            for s in leading_llm:
                desc = llm_descriptions.get(s, "")
                print(f"    {s}: {desc}" if desc else f"    {s}")
            print(f"\n  Após concluir essas etapas, continue o pipeline com:")
            print(f"    python scripts/e_reset.py --from {first_det}")
            print(f"\n  Ou use --interactive para orquestrar o pipeline completo:")
            print(f"    python scripts/e_reset.py --move-to-inbox --interactive")
            print(f"\n{'=' * 60}")
            print(f"  {mode} — limpeza concluída, aguardando etapas LLM")
            print("=" * 60)
            return

        # Non-interactive execution: skip LLM, run deterministic
        print(f"\n--- Fase 2: Re-execução do pipeline ---")

        llm_pending = []
        for s in stages:
            if s in LLM_STAGES:
                desc = llm_descriptions.get(s, "")
                print(f"\n  [{s}] ⏭  REQUER LLM — pulado" + (f" ({desc})" if desc else ""))
                llm_pending.append(s)
            elif s in DETERMINISTIC_SCRIPTS:
                print(f"\n  [{s}]")
                ok = run_script(s, dry_run)
                if not ok and not dry_run:
                    print(f"\n  [ABORTADO] Falha em {s}. Pipeline parado.")
                    sys.exit(1)

        _run_validation_and_summary(args, from_stage, mode, dry_run, llm_pending, leading_llm, llm_descriptions)
        return

    # =========================================================================
    # INTERACTIVE MODE: run stages, stop at LLM walls
    # =========================================================================
    assert state is not None
    print(f"\n--- Fase 2: Execução interativa do pipeline ---")

    _run_interactive_stages(stages, state, dry_run, args, from_stage, mode)


def _run_validation_and_summary(
    args, from_stage: str | None, mode: str, dry_run: bool,
    llm_pending: list[str], leading_llm: list[str], llm_descriptions: dict[str, str],
) -> None:
    """Run post-pipeline validation and print summary (non-interactive mode)."""
    if not args.no_validate and not dry_run:
        print(f"\n--- Fase 3: Validação ---")
        warnings_list = validate(from_stage)
        if warnings_list:
            print("  Avisos:")
            for w in warnings_list:
                print(f"    - {w}")
        else:
            print("  [OK] Todos os artefatos esperados estão presentes e com conteúdo válido.")

    print(f"\n{'=' * 60}")
    print(f"  {mode} — {'simulação concluída' if dry_run else 'concluído'}")
    if llm_pending:
        trailing_llm = [s for s in llm_pending if s not in leading_llm]
        if trailing_llm:
            print(f"\n  AÇÃO REQUERIDA — etapas LLM pendentes:")
            for s in trailing_llm:
                desc = llm_descriptions.get(s, "")
                print(f"    - {s}" + (f": {desc}" if desc else ""))
            print(f"\n  Após concluir as etapas LLM acima, re-rode E6 para")
            print(f"  gerar o relatório final com narrativas:")
            print(f"    python scripts/e6_render.py")
    print("=" * 60)


def _run_interactive_stages(
    stages: list[str], state: dict, dry_run: bool,
    args, from_stage: str | None, mode: str,
) -> None:
    """Execute stages in interactive mode, stopping at LLM walls."""
    # Map stages that are grouped into another stage's wall
    _WALL_GROUP = {"E1.5": "E1"}

    for stage in stages:
        if stage in LLM_STAGES:
            # Check if this stage is grouped with a prior wall
            parent_wall = _WALL_GROUP.get(stage)
            if parent_wall:
                parent_info = WALL_INSTRUCTIONS.get(parent_wall, {})
                wall_name = parent_info.get("wall", parent_wall)
                print(f"\n  [{stage}] ↳ incluído na {wall_name} ({parent_wall})")
                state["completed_stages"].append(stage)
                continue

            wall_info = WALL_INSTRUCTIONS.get(stage)
            if not wall_info:
                print(f"\n  [{stage}] ⏭  REQUER LLM — pulado")
                state["completed_stages"].append(stage)
                continue

            if dry_run:
                print(f"\n  [{stage}] ⏸  WALL — pipeline pararia aqui (modo interativo)")
                state["completed_stages"].append(stage)
                continue

            _print_wall(wall_info, state)
            sys.exit(EXIT_CODE_WALL)

        elif stage in DETERMINISTIC_SCRIPTS:
            print(f"\n  [{stage}]")
            ok = run_script(stage, dry_run, state)
            if not ok and not dry_run:
                print(f"\n  [ABORTADO] Falha em {stage}. Pipeline parado.")
                state["completed_stages"].append(f"{stage}:FAILED")
                _save_state(state)
                sys.exit(1)
            state["completed_stages"].append(stage)
            _save_state(state)

    # All stages completed
    if not args.no_validate and not dry_run:
        print(f"\n--- Fase 3: Validação ---")
        warnings_list = validate(from_stage)
        if warnings_list:
            print("  Avisos:")
            for w in warnings_list:
                print(f"    - {w}")
        else:
            print("  [OK] Todos os artefatos esperados estão presentes e com conteúdo válido.")

    _clear_state()

    print(f"\n{'=' * 60}")
    print(f"  {mode} — {'simulação concluída' if dry_run else 'PIPELINE COMPLETO'}")
    print(f"  Todas as etapas (determinísticas + LLM) foram concluídas.")
    print("=" * 60)


def _main_continue(args) -> None:
    """Resume interactive pipeline from state file."""
    state = _load_state()
    if not state:
        print("[ERRO] Nenhum state file encontrado em _scratch/.e_reset_state.json")
        print("       Use --interactive para iniciar um pipeline interativo.")
        sys.exit(1)

    wall_hit = state.get("wall_hit", "?")
    next_stage = state.get("next_stage")
    completed = state.get("completed_stages", [])
    flags = state.get("flags", {})
    dry_run = args.dry_run or flags.get("dry_run", False)
    from_stage = flags.get("from_stage")
    no_validate = args.no_validate or flags.get("no_validate", False)

    print("=" * 60)
    print(f"  Retomando pipeline interativo (após {wall_hit})")
    print(f"  Próxima etapa: {next_stage}")
    print(f"  Etapas concluídas: {', '.join(completed) if completed else 'nenhuma'}")
    print(f"  Projeto: {PROJECT_DIR}")
    print("=" * 60)

    # Validate artifacts from the wall that was just completed
    pending_stages = state.get("llm_stages_pending", [])
    for ps in pending_stages:
        wall_info = WALL_INSTRUCTIONS.get(ps)
        if wall_info:
            warnings = _validate_wall_artifacts(wall_info)
            if warnings:
                print(f"\n  [AVISO] Validação pós-wall ({wall_info['wall']}):")
                for w in warnings:
                    print(f"    - {w}")
                print(f"  Prosseguindo mesmo assim (artefatos podem ter nomes diferentes).")
            else:
                expected = wall_info.get("artifacts_expected", [])
                if expected:
                    print(f"\n  [OK] Artefatos de {wall_info['wall']} verificados.")

    # Mark the LLM stages as completed
    for ps in pending_stages:
        if ps not in completed:
            completed.append(ps)
    state["completed_stages"] = completed

    # Build remaining stages from next_stage onward
    if from_stage:
        all_stages = EXECUTION_ORDER_FROM.get(from_stage, EXECUTION_ORDER_FULL)
    else:
        all_stages = EXECUTION_ORDER_FULL

    if next_stage not in all_stages:
        print(f"\n  [ERRO] Etapa '{next_stage}' não encontrada na ordem de execução.")
        print(f"         Ordem disponível: {', '.join(all_stages)}")
        sys.exit(1)

    idx = all_stages.index(next_stage)
    remaining_stages = all_stages[idx:]

    mode = f"Pipeline interativo (continuação de {wall_hit})"
    print(f"\n--- Fase 2 (continuação): Execução de {next_stage} em diante ---")

    # Patch args for validation
    args.no_validate = no_validate

    _run_interactive_stages(remaining_stages, state, dry_run, args, from_stage, mode)


if __name__ == "__main__":
    main()
