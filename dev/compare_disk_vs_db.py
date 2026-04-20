"""compare_disk_vs_db.py — Paridade entre artefatos em disco e pipeline_artifacts DB.

A6b (ADR-106): gate ≥99% de paridade antes do cutover para DBArtifactStore.

Uso:
    python dev/compare_disk_vs_db.py <workspace_id> [--run-id <run_id>] [--strict]

    workspace_id  UUID do workspace a comparar.
    --run-id      Pipeline run específico (padrão: último run completo).
    --strict      Sai com código 1 se qualquer key ausente no DB (padrão: alerta).
    --json        Imprime resultado como JSON em stdout.

Saída:
    - Lista de keys presentes em disco e ausentes no DB.
    - Lista de keys com conteúdo divergente (diff de top-level keys).
    - Percentual de paridade calculado sobre a união de keys.
    - Exit code 0 se paridade ≥99%, 1 caso contrário (quando --strict).

Limitações intencionais:
    - Não compara timestamps (`created_at`, `updated_at`) — diferença esperada.
    - Não compara ordem de listas dentro de artefatos — divergência esperada em DB mode.
    - `schema_version` e `byte_size` do DB não têm equivalente em disco — ignorados.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Stage → disk directory + suffix mapping (espelha DiskArtifactStore)
# ---------------------------------------------------------------------------

def _disk_stage_dir(stage: str, processed_dir: Path) -> Path:
    """Retorna o diretório de disco para um stage (mesma lógica do DiskArtifactStore)."""
    from pipeline.artifact_store import stage_dir_name
    return processed_dir / stage_dir_name(stage)


def _disk_stage_suffix(stage: str) -> str:
    from pipeline.artifact_store import stage_suffix
    return stage_suffix(stage)


# ---------------------------------------------------------------------------
# Leitura de artefatos em disco
# ---------------------------------------------------------------------------

def _load_disk_artifacts(workspace_root: Path, stages: list[str]) -> dict[tuple[str, str], dict]:
    """Retorna {(stage, key): content_json} para todos os artefatos em disco."""
    processed_dir = workspace_root / "processed"
    artifacts: dict[tuple[str, str], dict] = {}

    for stage in stages:
        stage_dir = _disk_stage_dir(stage, processed_dir)
        suffix = _disk_stage_suffix(stage)
        if not stage_dir.exists():
            continue
        for fpath in stage_dir.glob(f"*{suffix}"):
            key = fpath.name.replace(suffix, "")
            try:
                content = json.loads(fpath.read_text(encoding="utf-8"))
                artifacts[(stage, key)] = content
            except (json.JSONDecodeError, OSError):
                pass

    return artifacts


# ---------------------------------------------------------------------------
# Leitura de artefatos no DB
# ---------------------------------------------------------------------------

def _load_db_artifacts(
    workspace_id: str,
    run_id: str | None,
    stages: list[str],
) -> tuple[dict[tuple[str, str], dict], str | None]:
    """Retorna {(stage, key): content_json} para artefatos no DB.

    Se run_id não fornecido, usa o último run completo do workspace.
    Retorna (artifacts, resolved_run_id).
    """
    from backend.app.core.database import SyncSessionLocal
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
    from sqlalchemy import select

    with SyncSessionLocal() as db:
        if run_id is None:
            row = (
                db.execute(
                    select(PipelineRun)
                    .where(
                        PipelineRun.workspace_id == workspace_id,
                        PipelineRun.status == PipelineRunStatus.completed,
                    )
                    .order_by(PipelineRun.completed_at.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if row is None:
                return {}, None
            run_id = row.id

        rows = (
            db.execute(
                select(PipelineArtifact).where(
                    PipelineArtifact.pipeline_run_id == run_id,
                    PipelineArtifact.stage.in_(stages),
                )
            )
            .scalars()
            .all()
        )

    artifacts: dict[tuple[str, str], dict] = {}
    for row in rows:
        artifacts[(row.stage, row.artifact_key)] = row.content_json

    return artifacts, run_id


# ---------------------------------------------------------------------------
# Comparação
# ---------------------------------------------------------------------------

_IGNORED_TOP_KEYS = {"_meta", "created_at", "updated_at", "generated_at"}


def _content_match(disk: dict, db: dict) -> bool:
    """True se os conteúdos são equivalentes (ignora _meta e timestamps)."""
    def _strip(d: dict) -> dict:
        return {k: v for k, v in d.items() if k not in _IGNORED_TOP_KEYS}

    return json.dumps(_strip(disk), sort_keys=True) == json.dumps(_strip(db), sort_keys=True)


def _compare(
    disk_artifacts: dict[tuple[str, str], dict],
    db_artifacts: dict[tuple[str, str], dict],
) -> dict:
    """Retorna relatório de paridade."""
    all_keys = set(disk_artifacts) | set(db_artifacts)
    only_disk = sorted(k for k in disk_artifacts if k not in db_artifacts)
    only_db = sorted(k for k in db_artifacts if k not in disk_artifacts)
    divergent = sorted(
        k for k in disk_artifacts
        if k in db_artifacts and not _content_match(disk_artifacts[k], db_artifacts[k])
    )

    matched = len(all_keys) - len(only_disk) - len(only_db) - len(divergent)
    total = len(all_keys)
    parity_pct = (matched / total * 100) if total > 0 else 100.0

    return {
        "total_keys": total,
        "matched": matched,
        "only_on_disk": [{"stage": s, "key": k} for s, k in only_disk],
        "only_in_db": [{"stage": s, "key": k} for s, k in only_db],
        "divergent": [{"stage": s, "key": k} for s, k in divergent],
        "parity_pct": round(parity_pct, 2),
        "gate_passed": parity_pct >= 99.0,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_PIPELINE_STAGES = [
    "E1.5", "E1.5c",
    "E2", "E2-extratos", "E2-faturas", "E2-llm",
    "E3",
    "E4",
    "E5", "E5-revised",
    "E5.N",
    "E7-crossval",
]


def _resolve_workspace_root(workspace_id: str) -> Path:
    from backend.app.core.config import settings
    return Path(settings.STORAGE_ROOT) / workspace_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compara artefatos disco vs DB (A6b parity gate)")
    parser.add_argument("workspace_id", help="UUID do workspace")
    parser.add_argument("--run-id", default=None, help="Pipeline run ID (padrão: último completo)")
    parser.add_argument("--strict", action="store_true", help="Sai com código 1 se gate falhar")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--stages",
        default=None,
        help="Stages a comparar, separados por vírgula (padrão: todos do pipeline)",
    )
    args = parser.parse_args(argv)

    stages = args.stages.split(",") if args.stages else _PIPELINE_STAGES
    workspace_root = _resolve_workspace_root(args.workspace_id)

    if not workspace_root.exists():
        print(f"ERRO: workspace root não encontrado: {workspace_root}", file=sys.stderr)
        return 1

    disk_artifacts = _load_disk_artifacts(workspace_root, stages)
    db_artifacts, resolved_run_id = _load_db_artifacts(args.workspace_id, args.run_id, stages)

    if resolved_run_id is None:
        print(
            "AVISO: nenhum run completo encontrado no DB para este workspace. "
            "Rode o pipeline com USE_DB_ARTIFACTS=true primeiro.",
            file=sys.stderr,
        )
        return 1

    report = _compare(disk_artifacts, db_artifacts)
    report["workspace_id"] = args.workspace_id
    report["run_id"] = resolved_run_id
    report["workspace_root"] = str(workspace_root)

    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print(f"  compare_disk_vs_db — workspace {args.workspace_id[:8]}…")
        print(f"  run_id: {resolved_run_id}")
        print(f"{'='*60}")
        print(f"  Total de keys: {report['total_keys']}")
        print(f"  Correspondências: {report['matched']}")
        print(f"  Só no disco:  {len(report['only_on_disk'])}")
        print(f"  Só no DB:     {len(report['only_in_db'])}")
        print(f"  Divergentes:  {len(report['divergent'])}")
        print(f"  Paridade:     {report['parity_pct']:.1f}%  {'✅ GATE OK' if report['gate_passed'] else '❌ GATE FALHOU'}")
        print()

        if report["only_on_disk"]:
            print("  Keys só no disco (ausentes no DB):")
            for item in report["only_on_disk"][:20]:
                print(f"    [{item['stage']}] {item['key']}")
            if len(report["only_on_disk"]) > 20:
                print(f"    … e mais {len(report['only_on_disk']) - 20}")
            print()

        if report["divergent"]:
            print("  Keys com conteúdo divergente:")
            for item in report["divergent"][:10]:
                print(f"    [{item['stage']}] {item['key']}")
            if len(report["divergent"]) > 10:
                print(f"    … e mais {len(report['divergent']) - 10}")
            print()

    if args.strict and not report["gate_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
