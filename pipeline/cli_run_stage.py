"""CLI ``run-stage`` do orchestrator (A3.cli — ADR-150 §4).

Interface estável consumida pelo shell Go do Caminho 1 via ``exec.Command``
e por debug/ops local:

    python -m pipeline.orchestrator run-stage <stage> \
        --workspace <path> --run-id <id> --workspace-id <id> \
        [--config-dir <path>] [--incremental] [--incremental-doc <path>...] \
        [--base-run-id <id>] [--base-run-fallback-stages <csv>]

stdout: somente o JSON do ``StageResult`` (5 campos). stderr: erros
estruturados em JSON. Exit codes: 0 = sucesso, 1 = falha de stage,
2 = erro de invocação/ambiente.

Trace contínuo (A3.cli.otel): com ``TRACEPARENT`` no env, o span
``pipeline.<stage>`` nasce filho do trace do chamador (W3C context
propagation); com ``OTEL_EXPORTER_OTLP_ENDPOINT``, o provider do backend
(ADR-110) é inicializado para exportar. Ambos best-effort — ausência ou
falha de tracing nunca derruba a execução.

Injeção de ``DBArtifactStore`` por-stage herda a mecânica de ADR-303 D1/D4
(espelho de ``_open_artifact_session`` do Celery), com ``MATHOMS_DATABASE_URL``
obrigatório no env (prefixo canônico do backend). Imports de ``backend.*``
são lazy: o CLI permanece importável (``--help``) sem backend instalado e
falha cedo com erro nomeado quando o ambiente é insuficiente.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

EXIT_OK = 0
EXIT_STAGE_FAILED = 1
EXIT_USAGE = 2


class CliEnvironmentError(RuntimeError):
    """Ambiente insuficiente para executar o stage (ADR-303 D4)."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.orchestrator",
        description="Executa stages do pipeline (interface do Caminho 1, ADR-150).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_run_stage_parser(subparsers)
    return parser


def _add_run_stage_parser(subparsers) -> None:
    p = subparsers.add_parser("run-stage", help="Executa um stage individual.")
    p.add_argument("stage", help="Nome do stage (descritivo ou legado, ADR-093).")
    p.add_argument("--workspace", required=True, type=Path, help="Root do workspace.")
    p.add_argument("--run-id", required=True, help="Pipeline run id.")
    p.add_argument(
        "--workspace-id", required=True, help="Workspace id (tenancy do store, ADR-303 D3)."
    )
    _add_run_stage_optional_flags(p)


def _add_run_stage_optional_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config-dir", type=Path, default=None, help="Override de config/.")
    p.add_argument("--incremental", action="store_true", help="Modo incremental (ADR-080).")
    p.add_argument(
        "--incremental-doc",
        action="append",
        default=[],
        dest="incremental_docs",
        help="Path de documento novo (repetível).",
    )
    p.add_argument("--base-run-id", default=None, help="Run base para leitura pinada (ADR-291).")
    p.add_argument(
        "--base-run-fallback-stages",
        default="",
        help="CSV de stages com leitura pinada no run base (ADR-303 D2).",
    )


def _fail(exit_code: int, kind: str, message: str, **extra: object) -> int:
    payload = {"error": kind, "message": message, **extra}
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
    return exit_code


def _maybe_bootstrap_otel() -> None:
    """Provider OTel do backend (ADR-110) quando o export OTLP está ligado."""
    # Best-effort: trace nunca derruba a execução do stage; sem endpoint,
    # spans fluem para o provider já configurado no processo (ou no-op).
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
        return
    try:
        from backend.app.core.otel import setup_otel

        setup_otel(service_name="mathoms-pipeline-cli")
    except Exception:  # noqa: BLE001 — tracing é opcional por contrato (track F2)
        pass


def _attach_traceparent():
    """Restaura o contexto W3C de ``TRACEPARENT`` — span do stage nasce filho."""
    traceparent = os.environ.get("TRACEPARENT")
    if not traceparent:
        return None
    try:
        from opentelemetry import context as otel_context
        from opentelemetry.trace.propagation.tracecontext import (
            TraceContextTextMapPropagator,
        )
    except ImportError:
        return None
    extracted = TraceContextTextMapPropagator().extract({"traceparent": traceparent})
    return otel_context.attach(extracted)


def _detach_traceparent(token) -> None:
    if token is None:
        return
    from opentelemetry import context as otel_context

    otel_context.detach(token)


def _resolve_stage(raw: str) -> str:
    """Normaliza e valida o stage; raise ``ValueError`` listando os válidos."""
    from pipeline.stage_spec import STAGE_REGISTRY, resolve_stage_name

    resolved = resolve_stage_name(raw)
    if resolved not in STAGE_REGISTRY:
        raise ValueError(f"stage desconhecido: {raw!r}. Válidos: {sorted(STAGE_REGISTRY)}")
    return resolved


def _require_backend_factory():
    """Valida o env e importa a factory de sessão do backend (ADR-303 D4)."""
    if not os.environ.get("MATHOMS_DATABASE_URL"):
        raise CliEnvironmentError(
            "MATHOMS_DATABASE_URL ausente no env — o CLI grava artefatos exclusivamente "
            "em pipeline_artifacts via DBArtifactStore (ADR-212/ADR-303 D4). Exigir o env "
            "explícito evita escrita silenciosa no DB default de dev."
        )
    try:
        from backend.app.services.storage import artifact_session_factory as factory
    except ImportError as exc:
        raise CliEnvironmentError(
            f"pacote 'backend' não importável — necessário para DBArtifactStore (ADR-303 D4): {exc}"
        ) from exc
    return factory


def _open_artifact_store(args: argparse.Namespace):
    """Sessão nova + ``DBArtifactStore`` para UM stage (ADR-303 D1/D4)."""
    # Mecânica de sessão vive no backend (artifact_session_factory) — ADR-256
    # proíbe pipeline/** de abrir Session própria.
    factory = _require_backend_factory()
    fallback = frozenset(s for s in args.base_run_fallback_stages.split(",") if s)
    try:
        return factory.open_artifact_store(
            workspace_id=args.workspace_id,
            run_id=args.run_id,
            base_run_id=args.base_run_id,
            base_run_fallback_stages=fallback,
        )
    except factory.ArtifactSessionUnavailable as exc:
        raise CliEnvironmentError(str(exc)) from exc


def _hydration_kwargs(args: argparse.Namespace) -> dict:
    return {
        "ws_id": args.workspace_id,
        "tenant_root": args.workspace,
        "run_id": args.run_id,
        "config_dir": args.config_dir,
        "incremental": args.incremental,
        "incremental_doc_paths": list(args.incremental_docs),
        "materialize_tarefas": True,
    }


def _build_hydrated_context(args: argparse.Namespace):
    """WorkspaceContext hidratado — paridade com Celery/HTTP (run_context_factory)."""
    try:
        from backend.app.services.pipeline.run_context_factory import build_hydrated_context
    except ImportError as exc:
        raise CliEnvironmentError(
            f"pacote 'backend' não importável — necessário para hidratar o contexto (ADR-303 D4): {exc}"
        ) from exc
    try:
        return build_hydrated_context(**_hydration_kwargs(args))
    except Exception as exc:
        raise CliEnvironmentError(
            f"falha ao hidratar o WorkspaceContext (ADR-303 D4): {exc}"
        ) from exc


def _commit_and_close(session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _rollback_and_close(session) -> None:
    try:
        session.rollback()
    finally:
        session.close()


def _run_with_store(ctx, stage: str, session):
    """Executa o stage e fecha a sessão — commit no sucesso, rollback em raise."""
    from pipeline.orchestrator import _run_stage

    try:
        result = _run_stage(ctx, stage)
    except BaseException:
        _rollback_and_close(session)
        raise
    else:
        _commit_and_close(session)
    return result


def _run_hydrated(stage: str, args: argparse.Namespace):
    """Abre as duas sessões (artifact + config), executa e fecha na ordem certa.

    Invariante ADR-256: a sessão de config é read-only enquanto o artifact
    store detém o write-lock; fechamento artifact primeiro, config depois.
    """
    session, store = _open_artifact_store(args)
    try:
        hydrated = _build_hydrated_context(args)
    except BaseException:
        _rollback_and_close(session)
        raise
    try:
        hydrated.ctx.artifact_store = store
        return _run_with_store(hydrated.ctx, stage, session)
    finally:
        hydrated.close()


def _execute_run_stage(stage: str, args: argparse.Namespace) -> int:
    """Executa o stage com store injetado e emite o ``StageResult`` em stdout."""
    # Swap stdout→stderr durante a execução: handlers de logging criados pelo
    # caminho do stage (ex.: echo do engine com MATHOMS_DEBUG) capturam
    # sys.stdout na criação — só o JSON do StageResult sai no stdout real.
    real_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        result = _run_hydrated(stage, args)
    finally:
        sys.stdout = real_stdout
    print(json.dumps(asdict(result), ensure_ascii=False, default=str))
    return EXIT_OK if result.success else EXIT_STAGE_FAILED


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        stage = _resolve_stage(args.stage)
    except ValueError as exc:
        return _fail(EXIT_USAGE, "unknown_stage", str(exc))
    _maybe_bootstrap_otel()
    token = _attach_traceparent()
    try:
        return _execute_run_stage(stage, args)
    except CliEnvironmentError as exc:
        return _fail(EXIT_USAGE, "environment", str(exc), adr="ADR-303 D4")
    finally:
        _detach_traceparent(token)
