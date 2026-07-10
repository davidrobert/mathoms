#!/usr/bin/env python3
"""Mede o impacto da re-tag de severidade do gate de conservação E7 (A36.l3).

Guarda pré-execução da lane [[A36.l3]]: **read-only e PII-safe**. Roda os 14
checks CV sobre artefatos E5 (`analise_financeira`) e reporta quantos runs
PAUSARIAM como `needs_review` sob cada política de severidade — SEM tocar em
nenhum comportamento de produção. Só faz sentido promover CV2/CV3/CV6 de
`warning`→`error` (a mudança load-bearing de A36.l3) se a taxa de pausa
resultante for tolerável; este script produz esse número.

A saída **nunca** emite os valores monetários que vivem em
`CrossValidationResult.details` — apenas check_id, severidade e contagens.

Contexto (verificado 2026-07-10): hoje só CV1/CV9/CV10 são `severity="error"`,
e o gate de pausa (`_has_validation_errors`) conta só `error`. Logo o gate
atual pausa em narrativa/gráfico ausente (CV9/CV10, cosmético) e **não** nos
checks de conservação numérica (CV2/CV3/CV6/CV7 são `warning`). A re-tag move
os numéricos para dentro do gate e os de render para fora.

Uso:
    # direto no DB da instância (dogfood/prod) — decripta o payload se preciso:
    python3 dev/measure_conservation_gate.py --from-db

    # ou sobre E5 exportados para JSON (um `analise_financeira` por arquivo):
    python3 dev/measure_conservation_gate.py --dir <dir-com-jsons>
    python3 dev/measure_conservation_gate.py --json <um-e5.json>

`--from-db` importa o backend de forma lazy (SyncSessionLocal + crypto) — só
esse caminho depende dele; `--dir`/`--json` e os testes rodam sem backend.
Requer o env do backend (`DATABASE_URL`, `MATHOMS_FERNET_KEY`) e deve rodar na
instância. Alternativa manual sem backend: exportar cada `content_json` (query
read-only abaixo) como `<pipeline_run_id>.json` e usar `--dir`.

    SELECT pipeline_run_id, content_json FROM pipeline_artifacts
    WHERE artifact_key = 'analise_financeira'
      AND stage IN ('E5', 'analyze_finances');

O script usa os thresholds default de `validate_cross` (mesmos do código); para
casar `qa_thresholds` customizado de uma instância, rode-o naquela instância.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.validate_cross import run_cross_validation  # noqa: E402

# Checks que HOJE disparam a pausa (severity="error" possível) — validate_cross.py.
GATE_TODAY = frozenset({"CV1", "CV9", "CV10"})
# Conservação numérica core: a re-tag load-bearing da A36.l3 (financial-planner).
# CV1 já é error e permanece; CV9/CV10 (render) SAEM do gate de pausa.
CONSERVATION_CORE = frozenset({"CV2", "CV3", "CV6"})
GATE_CORE = frozenset({"CV1"}) | CONSERVATION_CORE
# Borderline: promover é defensável, medir em separado antes de decidir.
CONSERVATION_BORDERLINE = frozenset({"CV5", "CV7", "CV8"})
GATE_CORE_BORDERLINE = GATE_CORE | CONSERVATION_BORDERLINE


@dataclass(frozen=True)
class RunClassification:
    """Como um run se comporta sob cada gate de severidade. Sem PII."""

    run_id: str
    failed: frozenset[str]
    pauses_today: bool
    pauses_core: bool
    pauses_core_borderline: bool


def classify(run_id: str, failed: frozenset[str]) -> RunClassification:
    """Classifica um run a partir do conjunto de check_ids que falharam."""
    return RunClassification(
        run_id=run_id,
        failed=failed,
        pauses_today=bool(failed & GATE_TODAY),
        pauses_core=bool(failed & GATE_CORE),
        pauses_core_borderline=bool(failed & GATE_CORE_BORDERLINE),
    )


@dataclass
class ImpactReport:
    """Agregado da medição. `unparseable` torna E5 malformado observável, não silencioso."""

    classifications: list[RunClassification]
    unparseable: list[tuple[str, str]]

    @property
    def total(self) -> int:
        return len(self.classifications) + len(self.unparseable)

    @property
    def pauses_today(self) -> int:
        return sum(c.pauses_today for c in self.classifications)

    @property
    def pauses_core(self) -> int:
        return sum(c.pauses_core for c in self.classifications)

    @property
    def pauses_core_borderline(self) -> int:
        return sum(c.pauses_core_borderline for c in self.classifications)

    @property
    def newly_pausing(self) -> list[str]:
        """Runs que ganham pausa sob a re-tag core (não pausavam hoje)."""
        return [c.run_id for c in self.classifications if c.pauses_core and not c.pauses_today]

    @property
    def no_longer_pausing(self) -> list[str]:
        """Runs que só pausavam por CV9/CV10 (render) e saem do gate de pausa."""
        return [c.run_id for c in self.classifications if c.pauses_today and not c.pauses_core]

    @property
    def per_check_failures(self) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for c in self.classifications:
            counter.update(c.failed)
        return dict(sorted(counter.items()))


def measure(runs: Iterable[tuple[str, dict]]) -> ImpactReport:
    """Roda os checks CV sobre cada E5 e classifica. Não aborta o lote num E5 ruim."""
    classifications: list[RunClassification] = []
    unparseable: list[tuple[str, str]] = []
    for run_id, e5 in runs:
        try:
            results = run_cross_validation(e5)
        except Exception as exc:  # noqa: BLE001 — lote sobre E5 heterogêneo: registra tipo, segue
            unparseable.append((run_id, type(exc).__name__))
            continue
        failed = frozenset(r.check_id for r in results if not r.passed)
        classifications.append(classify(run_id, failed))
    return ImpactReport(classifications=classifications, unparseable=unparseable)


def load_e5_dir(path: Path) -> Iterator[tuple[str, dict]]:
    """Carrega cada `*.json` do diretório como um E5. run_id = stem do arquivo."""
    for jf in sorted(path.glob("*.json")):
        yield jf.stem, json.loads(jf.read_text(encoding="utf-8"))


def _decrypt_if_needed(payload: dict) -> dict:
    """Decripta o payload de um artifact se estiver encriptado (ADR-231; import lazy)."""
    from backend.app.services.security.crypto import (
        decrypt_artifact_payload,
        is_encrypted_payload,
    )

    return decrypt_artifact_payload(payload) if is_encrypted_payload(payload) else payload


def load_e5_from_db() -> list[tuple[str, dict]]:
    """Lê os E5 (`analise_financeira`) do DB, um por run (import lazy; requer env backend)."""
    from sqlalchemy import select

    from backend.app.core.database import SyncSessionLocal
    from backend.app.models.pipeline_artifact import PipelineArtifact

    stmt = (
        select(PipelineArtifact)
        .where(PipelineArtifact.artifact_key == "analise_financeira")
        .where(PipelineArtifact.stage.in_(("E5", "analyze_finances")))
        .order_by(PipelineArtifact.id)
    )
    latest_by_run: dict[str, dict] = {}
    with SyncSessionLocal() as session:
        for row in session.execute(stmt).scalars():
            latest_by_run[row.pipeline_run_id] = _decrypt_if_needed(row.content_json)
    return list(latest_by_run.items())


def _summary_lines(report: ImpactReport) -> list[str]:
    """Cabeçalho + contagens agregadas do relatório (PII-safe)."""
    return [
        "== Impacto da re-tag de severidade do gate de conservação E7 (A36.l3) ==",
        f"runs medidos: {report.total}  (validáveis: {len(report.classifications)}, "
        f"não-validáveis: {len(report.unparseable)})",
        "",
        f"pausam HOJE            (CV1/CV9/CV10 error):        {report.pauses_today}",
        f"pausam sob CORE        (CV1/CV2/CV3/CV6; render fora): {report.pauses_core}",
        f"pausam sob CORE+BORDER (+CV5/CV7/CV8):              {report.pauses_core_borderline}",
        "",
        f"NOVOS a pausar sob core (conservação real):        {len(report.newly_pausing)}",
        f"deixam de pausar (eram só render CV9/CV10):         {len(report.no_longer_pausing)}",
        "",
        "falhas por check (nº de runs em que cada CV falhou):",
    ]


def format_report(report: ImpactReport) -> str:
    """Relatório PII-safe: contagens + check_ids, nunca valores monetários."""
    lines = _summary_lines(report)
    lines.extend(f"  {cid}: {n}" for cid, n in report.per_check_failures.items())
    if report.unparseable:
        lines.append("")
        lines.append("E5 não-validáveis (run_id → exceção):")
        lines.extend(f"  {rid}: {exc}" for rid, exc in report.unparseable)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-db", action="store_true", help="Lê E5 do DB da instância.")
    src.add_argument("--dir", type=Path, help="Diretório de E5 JSON (um por run).")
    src.add_argument("--json", type=Path, help="Um único E5 JSON.")
    args = parser.parse_args(argv)

    if args.from_db:
        runs = load_e5_from_db()
    elif args.dir:
        runs = list(load_e5_dir(args.dir))
    else:
        runs = [(args.json.stem, json.loads(args.json.read_text(encoding="utf-8")))]

    if not runs:
        print("nenhum E5 encontrado na fonte informada", file=sys.stderr)
        return 1
    print(format_report(measure(runs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
