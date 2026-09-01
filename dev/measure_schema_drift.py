#!/usr/bin/env python3
"""Mede o drift de schema no corpus de `pipeline_artifacts` — gate do flip warn→strict (ADR-284 §2, runbook `schema_validation_strict_flip.md`)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# Schemas cujo contrato ainda não foi re-derivado do produtor: nunca `GO`. A
# [[ADR-409]] §F recusa promover schema cujo contrato descreve uma fração do payload
# ("o flip seria verde sobre contrato que descreve 5/13" — medida de 2026-08-24, hoje
# 5 de 11: o PR-A tirou 2 properties nunca emitidas), mas a recusa vivia só em
# prosa e a elegibilidade é só a medição — bastava o drift ir a 0. A [[A40.l110]]
# PR-A levou `baseline_patrimonial` de 59,8% a 3,6% ao matar 2 `required` fósseis, e
# o resto é defeito de dado da [[A40.l111]], que já mergeou (#1917) — o corpus
# histórico conserva os negativos, então o verde chega quando as runs virarem, não
# na data do merge. Chegando, o contrato continua irreal. Não muda o exit code de `--gate`, pela mesma razão de
# `mass_trivial` — contrato incompleto é insumo de decisão, não drift.
_CONTRATO_NAO_DERIVADO: dict[str, str] = {
    "baseline_patrimonial.schema.json": (
        "contrato declara 5 de 11 chaves emitidas (medido 2026-08-31) — [[ADR-409]] §F; "
        "levanta com a [[A40.l110]] PR-B"
    ),
}


class SchemaDrift:
    """Acumulador por schema — contadores que o go/no-go do runbook consulta."""

    def __init__(self, nome: str = "") -> None:
        self.nome = nome
        self.artifacts = 0
        self.drifted = 0
        self.unreadable = 0
        self.runs: set = set()
        self.drifted_runs: set = set()
        self.payloads: set = set()
        self.paths: Counter = Counter()
        self.last_drift: Optional[str] = None

    @property
    def contrato_nao_derivado(self) -> Optional[str]:
        """Razão pela qual este schema não é promovível, mesmo com drift zero."""
        return _CONTRATO_NAO_DERIVADO.get(self.nome)

    @property
    def is_go(self) -> bool:
        """Critério binário do §1.3: zero record na janela. Schema **sem massa** não é GO (janela sem run não mede nada), e artefato **ilegível** também não — não-validado não é validado-sem-drift. Schema com contrato não re-derivado também não: drift zero sobre contrato que descreve uma fração do payload é o falso-verde que a [[ADR-409]] §F nomeia."""
        if self.contrato_nao_derivado:
            return False
        return self.artifacts > 0 and self.drifted == 0 and self.unreadable == 0

    @property
    def mass_trivial(self) -> bool:
        """Massa que não sustenta promoção, ainda que `is_go` seja True."""
        # A [[ADR-409]] §D já recusou `e2_llm_artifact` à mão ("n=2 em 1 run não é
        # evidência"); isto encoda a recusa. NÃO muda o exit code: massa é insumo de
        # decisão, não gate de drift — vermelho aqui trocaria falso-verde por falso-vermelho.
        return len(self.payloads) <= 1 or len(self.runs) < 3

    @property
    def drift_pct(self) -> float:
        return 100.0 * self.drifted / self.artifacts if self.artifacts else 0.0


def _validator_for(schema_name: str) -> Any:
    """Validator do schema em ``config/schemas/``; ``None`` quando o arquivo não existe."""
    import scripts.pipeline_common as pipeline_common

    path = pipeline_common.CONFIG_DIR / "schemas" / schema_name
    if not path.exists():
        return None
    return pipeline_common._build_schema_validator(json.loads(path.read_text(encoding="utf-8")))


def _decode(content: Any) -> Optional[dict]:
    """Payload persistido → dict, decriptando em repouso (ADR-319); ``None`` se ilegível."""
    from backend.app.services.storage.db_artifact_store import _maybe_decrypt

    try:
        payload = json.loads(content) if isinstance(content, str) else content
        payload = _maybe_decrypt(payload)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _window_start(
    days: int, since: Optional[str] = None, newest: Optional[str] = None
) -> Optional[str]:
    """Início da janela: ``--since`` explícito vence; senão N dias contados do write mais recente."""
    if since:
        return since
    if not newest or days <= 0:
        return None
    return (date.fromisoformat(newest[:10]) - timedelta(days=days - 1)).isoformat()


def _accumulate(stats: SchemaDrift, row: Any, errors: list) -> None:
    from scripts.schema_drift_telemetry import _count_drift_paths

    stats.drifted += 1
    stats.drifted_runs.add(row.pipeline_run_id)
    created = str(row.created_at or "")
    stats.last_drift = max(stats.last_drift or "", created)
    for pair, occurrences in _count_drift_paths(errors).items():
        stats.paths[pair] += occurrences


def _payload_digest(payload: Any) -> str:
    """Identidade de conteúdo do artefato — a unidade de massa desde 2026-08-31."""
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _validate_row(stats: SchemaDrift, row: Any, validator: Any) -> None:
    """Conta o artefato e, se houver erro, acumula os paths de drift."""
    stats.artifacts += 1
    stats.runs.add(row.pipeline_run_id)
    payload = _decode(row.content_json)
    if payload is None:
        stats.unreadable += 1
        return
    # Massa por payload distinto, não por `documents`: `document_id` é FK de documento
    # de ENTRADA (contrato E2-only, [[ADR-408]]) e é NULL em 100% do corpus, então
    # `documents` degenerava para "artifact_keys distintas" — e reportava massa 1 como
    # se fossem N. Emenda de 2026-08-31 na [[ADR-409]] §B.
    stats.payloads.add(_payload_digest(payload))
    if validator is None:
        return
    errors = list(validator.iter_errors(payload))
    if errors:
        _accumulate(stats, row, errors)


def _measure(rows: Iterable[Any], resolve: Callable[[str, str], Optional[str]]) -> dict:
    """Valida cada artefato contra o schema que o guard de escrita aplicaria; devolve ``{schema_name: SchemaDrift}``."""
    # `resolve` é `(stage, artifact_key) → schema`, não dict por stage (A42.l19): medir
    # o E4 contra o backstop do stage diria `GO` para os 7 baldes sem checar contrato
    # nenhum — falso-verde no instrumento que gateia a fila da ADR-409.
    validators: dict = {}
    by_schema: dict = defaultdict(SchemaDrift)
    for row in rows:
        schema_name = resolve(row.stage, row.artifact_key)
        if schema_name is None:
            continue
        if schema_name not in validators:
            validators[schema_name] = _validator_for(schema_name)
        stats = by_schema[schema_name]
        stats.nome = schema_name
        _validate_row(stats, row, validators[schema_name])
    return dict(by_schema)


def _stages_do_schema(only: str) -> list:
    """Stages que podem produzir ``only`` — pelo mapa por stage E pelo mapa por chave.
    Sem o segundo, `--schema e4_cashflow.schema.json` filtraria para conjunto vazio."""
    from backend.app.services.storage.db_artifact_store import (
        SCHEMA_BY_STAGE,
        SCHEMA_BY_STAGE_KEY,
    )

    stages = {stage for stage, name in SCHEMA_BY_STAGE.items() if name == only}
    stages |= {stage for (stage, _), name in SCHEMA_BY_STAGE_KEY.items() if name == only}
    return sorted(stages)


def _fetch(session, start: Optional[str] = None, only: Optional[str] = None) -> list:
    from backend.app.models import PipelineArtifact

    query = session.query(PipelineArtifact)
    if start:
        query = query.filter(PipelineArtifact.created_at >= start)
    if only:
        query = query.filter(PipelineArtifact.stage.in_(_stages_do_schema(only)))
    return query.order_by(PipelineArtifact.created_at).all()


def _veredito(s: SchemaDrift) -> str:
    """Rótulo do go/no-go — contrato não re-derivado vence drift zero."""
    if s.contrato_nao_derivado:
        return "NO-GO (contrato)"
    if not s.is_go:
        return "NO-GO"
    return "GO (massa trivial)" if s.mass_trivial else "GO"


def _print_table(results: dict, start: Optional[str] = None, newest: Optional[str] = None) -> None:
    print(f"janela: {start or '(corpus inteiro)'} .. {newest or '?'}\n")
    header = (
        f"{'schema':<40} {'artef':>6} {'drift':>6} {'%':>6} {'runs':>5} {'paylds':>6}  veredito"
    )
    print(header)
    print("-" * len(header))
    for name in sorted(results, key=lambda n: (-results[n].drifted, n)):
        s = results[name]
        print(
            f"{name:<40} {s.artifacts:>6} {s.drifted:>6} {s.drift_pct:>5.1f}% "
            f"{len(s.runs):>5} {len(s.payloads):>6}  "
            f"{_veredito(s)}"
        )
    for name in sorted(results):
        razao = results[name].contrato_nao_derivado
        if razao:
            print(f"\n  {name}: contrato não re-derivado — {razao}")


def _print_paths(results: dict, limit: int) -> None:
    for name in sorted(results, key=lambda n: -results[n].drifted):
        stats = results[name]
        if not stats.drifted:
            continue
        print(f"\n### {name} — {stats.drifted}/{stats.artifacts}, último drift {stats.last_drift}")
        for (path, keyword), count in stats.paths.most_common(limit):
            print(f"   {count:>6}x {keyword:<22} {path}")
        if len(stats.paths) > limit:
            print(f"   ... +{len(stats.paths) - limit} paths distintos (use --paths N)")


def _schema_summary(stats: SchemaDrift) -> dict:
    return {
        "artifacts": stats.artifacts,
        "drifted": stats.drifted,
        "drift_pct": round(stats.drift_pct, 2),
        "runs": len(stats.runs),
        "drifted_runs": len(stats.drifted_runs),
        "payloads": len(stats.payloads),
        "mass_trivial": stats.mass_trivial,
        "unreadable": stats.unreadable,
        "last_drift": stats.last_drift,
        "go": stats.is_go,
        "contrato_nao_derivado": stats.contrato_nao_derivado,
        "paths": [
            {"path": p, "validator": k, "occurrences": n} for (p, k), n in stats.paths.most_common()
        ],
    }


def _as_json(results: dict, start: Optional[str] = None) -> str:
    payload = {
        "window_start": start,
        "schemas": {name: _schema_summary(s) for name, s in results.items()},
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days", type=int, default=7, help="janela em dias (default 7, ADR-284 §1.3)"
    )
    parser.add_argument("--since", help="início explícito YYYY-MM-DD; vence --days")
    parser.add_argument("--all", action="store_true", help="corpus inteiro, sem janela")
    parser.add_argument("--schema", help="mede só este schema (ex.: e2_extract.schema.json)")
    parser.add_argument("--paths", type=int, default=12, help="paths de drift listados por schema")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--gate",
        action="store_true",
        help="exit 1 se algum schema medido tiver drift — trava o PR de flip",
    )
    return parser.parse_args(argv)


def _silence_sql_echo() -> None:
    """Com ``DEBUG=true`` a engine nasce ``echo=True`` e despeja SQL no stdout, quebrando o ``| jq``. Baixar o nível do logger não basta — o ``InstanceLogger`` do ``echo`` ignora o nível; é o atributo da engine que manda."""
    import logging

    from backend.app.core.database import sync_engine

    sync_engine.echo = False
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _collect(args: argparse.Namespace) -> tuple:
    """Lê o corpus na janela pedida; devolve ``(results, start, newest)``."""
    from backend.app.core.database import SyncSessionLocal
    from backend.app.models import PipelineArtifact
    from backend.app.services.storage.db_artifact_store import resolve_schema_name

    _silence_sql_echo()
    with SyncSessionLocal() as session:
        newest = (
            session.query(PipelineArtifact.created_at)
            .order_by(PipelineArtifact.created_at.desc())
            .limit(1)
            .scalar()
        )
        newest = str(newest) if newest else None
        start = None if args.all else _window_start(args.days, args.since, newest)
        rows = _fetch(session, start, args.schema)
        return _measure(rows, resolve_schema_name), start, newest


def main(argv: Optional[list] = None) -> int:
    args = _parse_args(argv)
    results, start, newest = _collect(args)
    if args.format == "json":
        print(_as_json(results, start))
    else:
        _print_table(results, start, newest[:10] if newest else None)
        _print_paths(results, args.paths)
    return 1 if args.gate and any(s.drifted for s in results.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
