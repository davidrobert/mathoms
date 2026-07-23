#!/usr/bin/env python3
"""Certificação local de parse: classify→route→parse sobre um diretório de PDFs reais.

Gate manual de KR-E da Sprint A38 ([[A38.l1]]): roda o caminho real de produção
E0→E2 (classify_file → build_final_name → route_to_parser → process_file) sobre
um corpus local que NUNCA entra no git, e imprime somente métricas mascaradas
(contagens, booleans, códigos — sem valores monetários, CPF ou números longos).

Uso:
    python3 dev/certify_parse_local.py --dir <pasta-local-de-documentos>
    python3 dev/certify_parse_local.py --dir <pasta> --baseline _scratch/a38_base.json
    python3 dev/certify_parse_local.py --dir <pasta> --compare _scratch/a38_base.json

`--compare` retorna exit != 0 se qualquer doc regredir vs o baseline:
n_tx menor, conservação passa→falha, ou parser determinístico perdido.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

VALID_SUFFIXES = {".pdf", ".csv", ".xls", ".xlsx"}

_MONEY_RE = re.compile(r"-?\d{1,3}(?:[\.,]\d{3})*[\.,]\d{2}")
_CPF_RE = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
_LONGNUM_RE = re.compile(r"\d{5,}")


def mask_text(value: Any) -> str:
    """Remove valores monetários, CPFs e sequências numéricas longas."""
    text = str(value)
    text = _CPF_RE.sub("<CPF>", text)
    text = _MONEY_RE.sub("<VAL>", text)
    return _LONGNUM_RE.sub("<NUM>", text)


def masked_key(filename: str) -> str:
    """Nome mascarado + hash curto do nome real: sem PII e único por arquivo."""
    digest = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:4]
    return f"{mask_text(filename)}#{digest}"


def _strip_hash_prefix(final_name: str) -> str:
    return re.sub(r"^[a-f0-9]{12}_", "", final_name)


def conservation_status(result: dict) -> Optional[bool]:
    """True/False quando saldos presentes; None quando não verificável."""
    saldo_ini = result.get("saldo_inicial")
    saldo_fim = result.get("saldo_final")
    txs = result.get("transacoes") or []
    if saldo_ini is None or saldo_fim is None or not txs:
        return None
    soma = sum(t.get("valor") or 0 for t in txs)
    return abs((saldo_ini + soma) - saldo_fim) < 0.011


def _classify(path: Path) -> dict:
    from backend.app.services.documents.content_classifier import classify_file
    from scripts.route_documents import _extract_file_preview

    cc = classify_file(path, _extract_file_preview)
    return {
        "doc_type": cc.doc_type,
        "institution": cc.institution,
        "period": cc.period,
        "confidence": cc.confidence,
        "dest_group": cc.dest_group,
    }


def _final_name(classification: dict, suffix: str) -> Optional[str]:
    from scripts.route_documents import build_final_name

    if not classification["doc_type"] or not classification["dest_group"]:
        return None
    return build_final_name(
        {
            "dest_group": classification["dest_group"],
            "doc_type": classification["doc_type"],
            "institution": classification["institution"] or "unknown",
            "period": classification["period"],
        },
        suffix,
    )


def _parse_staged(src: Path, final_name: str, staging: Path) -> Optional[dict]:
    from scripts.extract_bank_documents import process_file

    staged = staging / final_name
    shutil.copy2(src, staged)
    try:
        return process_file(staged)
    finally:
        staged.unlink(missing_ok=True)


def _classified_record(src: Path) -> tuple[dict, Optional[str]]:
    record: dict[str, Any] = {"file": masked_key(src.name)}
    classification = _classify(src)
    record.update(
        doc_type=classification["doc_type"],
        institution=classification["institution"],
        confidence=classification["confidence"],
    )
    return record, _final_name(classification, src.suffix.lower())


def certify_file(src: Path, staging: Path) -> dict:
    """Roda o caminho de produção completo para um arquivo; retorna record mascarado."""
    from scripts.e2.registry import route_to_parser

    record, final_name = _classified_record(src)
    if final_name is None:
        record.update(parser=None, n_tx=0, status="sem_classificacao_regex")
        return record
    record["final_name"] = mask_text(_strip_hash_prefix(final_name))
    parser = route_to_parser(final_name)
    record["parser"] = parser.__name__ if parser else None
    result = _parse_staged(src, final_name, staging)
    if result is None:
        record.update(n_tx=0, status="process_file_none")
        return record
    return _fill_parse_metrics(record, result)


def _fill_parse_metrics(record: dict, result: dict) -> dict:
    txs = result.get("transacoes") or []
    record.update(
        n_tx=len(txs),
        moeda=result.get("moeda"),
        banco=result.get("banco"),
        escalated=bool(result.get("requires_llm_fallback")),
        conservacao=conservation_status(result),
        total_fatura_set=result.get("total_fatura") is not None,
        vencimento_set=result.get("vencimento") is not None,
        notas=[mask_text(n)[:160] for n in (result.get("notas") or [])[:6]],
        status="ok",
    )
    return record


def run_dir(corpus_dir: Path) -> list[dict]:
    files = sorted(
        f for f in corpus_dir.iterdir() if f.is_file() and f.suffix.lower() in VALID_SUFFIXES
    )
    if not files:
        sys.exit(f"nenhum documento em {corpus_dir} (sufixos: {sorted(VALID_SUFFIXES)})")
    records = []
    with tempfile.TemporaryDirectory(prefix="certify_parse_") as staging:
        for f in files:
            try:
                records.append(certify_file(f, Path(staging)))
            except Exception as exc:  # noqa: BLE001 — 1 doc ruim não derruba o run
                records.append({"file": masked_key(f.name), "status": f"erro:{type(exc).__name__}"})
    return records


def compare_records(current: list[dict], baseline: list[dict]) -> tuple[list[str], list[str]]:
    """Retorna (regressões que falham o gate, mudanças informativas)."""
    base_by_file = {r["file"]: r for r in baseline}
    regressions: list[str] = []
    changes: list[str] = []
    for rec in current:
        base = base_by_file.get(rec["file"])
        if base is None:
            changes.append(f"{rec['file']}: novo doc (sem baseline)")
            continue
        regressions.extend(_regressions_for(rec, base))
        changes.extend(_changes_for(rec, base))
    return regressions, changes


def _regressions_for(rec: dict, base: dict) -> list[str]:
    out = []
    if rec.get("n_tx", 0) < base.get("n_tx", 0):
        out.append(f"{rec['file']}: n_tx {base['n_tx']} -> {rec['n_tx']} (REGRESSÃO)")
    if base.get("conservacao") is True and rec.get("conservacao") is False:
        out.append(f"{rec['file']}: conservação passa -> falha (REGRESSÃO)")
    if base.get("parser") and not rec.get("parser"):
        out.append(f"{rec['file']}: parser {base['parser']} -> nenhum (REGRESSÃO)")
    return out


def _changes_for(rec: dict, base: dict) -> list[str]:
    out = []
    for field in ("doc_type", "institution", "moeda", "parser"):
        if rec.get(field) != base.get(field):
            out.append(f"{rec['file']}: {field} {base.get(field)} -> {rec.get(field)}")
    return out


def _print_report(records: list[dict]) -> None:
    for rec in records:
        line = (
            f"{rec.get('file')}: type={rec.get('doc_type')} inst={rec.get('institution')} "
            f"conf={rec.get('confidence')} parser={rec.get('parser')} n_tx={rec.get('n_tx')} "
            f"moeda={rec.get('moeda')} conserv={rec.get('conservacao')} "
            f"escala={rec.get('escalated')} status={rec.get('status')}"
        )
        print(mask_text(line))


def main() -> int:
    args = _parse_args()
    _init_pipeline_config()
    records = run_dir(args.dir)
    _print_report(records)
    if args.baseline:
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(records, ensure_ascii=False, indent=2))
        print(f"\nbaseline gravado: {args.baseline}")
    if args.compare:
        return _run_compare(records, args.compare)
    return 0


def _run_compare(records: list[dict], baseline_path: Path) -> int:
    baseline = json.loads(baseline_path.read_text())
    regressions, changes = compare_records(records, baseline)
    for c in changes:
        print(f"CHANGED: {c}")
    for r in regressions:
        print(f"FAIL: {r}")
    if regressions:
        print(f"\n{len(regressions)} regressão(ões) vs {baseline_path}")
        return 1
    print(f"\nsem regressões vs {baseline_path}")
    return 0


def _init_pipeline_config() -> None:
    from scripts.route_documents import _init_config

    _init_config(Path(__file__).resolve().parent.parent)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, required=True, help="pasta local com os documentos")
    parser.add_argument("--baseline", type=Path, help="grava snapshot JSON mascarado")
    parser.add_argument("--compare", type=Path, help="compara com snapshot e falha em regressão")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
