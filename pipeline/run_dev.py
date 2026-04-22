"""Runner offline para desenvolvimento — mesmos wrappers do worker (orchestrator).

Executa estágios sobre um diretório de tenant já materializado (``config/``, ``data/``, …).

Exemplos::

    python -m pipeline.run_dev --root /path/to/storage/ws_id
    python -m pipeline.run_dev --root ./tenant --stages E3,E4
    python -m pipeline.run_dev --root ./tenant --from-stage E4
    python -m pipeline.run_dev --root ./tenant --include-llm

Por omissão, estágios LLM são **pulados** (equivalente a ``skip_llm=True`` no Celery).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pipeline.context import WorkspaceContext
from pipeline.orchestrator import run_from, run_pipeline, run_stages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline offline: orquestra estágios sobre --root (tenant materializado).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Raiz do workspace (deve conter config/; data/, processed/ criados se faltar)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--stages",
        type=str,
        metavar="LIST",
        help="Estágios separados por vírgula (ex.: E3,E4,E5)",
    )
    group.add_argument(
        "--from-stage",
        type=str,
        metavar="STAGE",
        dest="from_stage",
        help="Executa a partir deste marco (ex.: E3, E4, E7 — ver orchestrator.FROM_MAP)",
    )
    parser.add_argument(
        "--include-llm",
        action="store_true",
        help="Não pular estágios LLM (E1, E1.5, E2-llm, E7-review).",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Não parar no primeiro estágio com falha.",
    )

    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}), file=sys.stderr)
        return 2

    # Required before lazy-import of scripts.* (pipeline_common).
    os.environ["MATHOMS_WORKSPACE_ROOT"] = str(root)

    ctx = WorkspaceContext(root=root)
    ctx.ensure_dirs()

    skip_llm = not args.include_llm
    stop_on_error = not args.continue_on_error

    if args.stages:
        stages = [s.strip() for s in args.stages.split(",") if s.strip()]
        if not stages:
            print(json.dumps({"error": "empty --stages"}), file=sys.stderr)
            return 2
        result = run_stages(ctx, stages, skip_llm=skip_llm, stop_on_error=stop_on_error)
    elif args.from_stage:
        result = run_from(ctx, args.from_stage, skip_llm=skip_llm, stop_on_error=stop_on_error)
    else:
        # Default: full deterministic pipeline (same as orchestrator.run_pipeline)
        result = run_pipeline(ctx, skip_llm=skip_llm, stop_on_error=stop_on_error)

    summary = result.summary()
    summary["stages"] = [
        {
            "stage": s.stage,
            "success": s.success,
            "duration_ms": round(s.duration_ms, 2),
            "error": s.error,
        }
        for s in result.stages
    ]
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
