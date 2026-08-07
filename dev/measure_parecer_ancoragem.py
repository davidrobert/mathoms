#!/usr/bin/env python3
"""Re-medição retroativa da ancoragem do parecer, estratificada (A40.l30 item 3).

Decompõe o "9→5" que a [[A40.l16]] mediu em *menos âncoras por item* vs *menos itens*,
por `(prompt_version, manifest_version)`. Lê `pipeline_stage_logs.output_summary` — que
já persiste `riscos_count`/`sugestoes_*_count`/`metricas_count` e
`evidencia_verification` com `ancoras_total` + `items_dropped` — então **custa US$ 0 e
não gera nada**.

Por que `manifest_version` entra no estratificador: entre 2.1.0 e 2.2.0 o payload E5
também mudou (#1006, #1010), logo `prompt_version` sozinho conflacia mudança de prompt
com drift de payload.

`itens_total` ausente é **`unknown`**, nunca 0 — o cache do envelope ([[ADR-366]] §D7)
serve summary pré-instrumento num run novo. Para essas rows o denominador é reconstruído
de `riscos_count + Σ sugestoes_*_count`, que o stage persiste desde antes da lane; quando
nem isso existe, a row entra em `sem_denominador` e fica FORA das médias.

Saída fica **off-git** (`storage/`, gitignored) — o payload carrega ids de workspace.

Uso:
    python3 dev/measure_parecer_ancoragem.py --out storage/_scratch/ancoragem_19runs.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_HORIZONS = ("sugestoes_execucao_count", "sugestoes_taticas_count", "sugestoes_estrategicas_count")


def _denominador(summary: dict) -> tuple[int | None, str]:
    """(itens ancoráveis, procedência). `None` quando nem os counts existem."""
    verification = summary.get("evidencia_verification") or {}
    direto = verification.get("itens_total")
    if isinstance(direto, int) and direto > 0:
        return direto, "itens_total"
    # Os counts vivem NESTED em `parecer_summary` (`pipeline/stages/parecer_planejador.py:179`),
    # não no topo do `output_summary` — medido em 66 execuções reais: 53 têm
    # `parecer_summary`, 0 têm `riscos_count` no topo.
    counts_src = summary.get("parecer_summary")
    if not isinstance(counts_src, dict):
        return None, "sem_denominador"
    counts = [counts_src.get("riscos_count"), *(counts_src.get(h) for h in _HORIZONS)]
    if any(isinstance(c, int) for c in counts):
        return sum(c for c in counts if isinstance(c, int)) or None, "counts_reconstruidos"
    return None, "sem_denominador"


def _observacao(summary: dict) -> dict:
    verification = summary.get("evidencia_verification") or {}
    itens, procedencia = _denominador(summary)
    return {
        "prompt_version": str(verification.get("prompt_version") or "unversioned"),
        "manifest_version": str(summary.get("manifest_version") or "unknown"),
        "itens": itens,
        "procedencia_do_denominador": procedencia,
        "ancoras_total": verification.get("ancoras_total"),
        "money_tokens_total": verification.get("money_tokens_total"),
        "items_dropped": verification.get("items_dropped"),
        "prose_inventory_version": verification.get("prose_inventory_version"),
    }


def _agrega(observacoes: list[dict]) -> list[dict]:
    """Uma linha por `(prompt_version, manifest_version)` — a tabela do item 3."""
    grupos: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for o in observacoes:
        grupos[(o["prompt_version"], o["manifest_version"])].append(o)
    return [_linha(chave, obs) for chave, obs in sorted(grupos.items())]


def _taxas(com_denominador: list[dict]) -> tuple[list[float], list[float]]:
    densidades = [o["ancoras_total"] / o["itens"] for o in com_denominador]
    prosa = [
        o["money_tokens_total"] / o["itens"]
        for o in com_denominador
        if o["money_tokens_total"] is not None
    ]
    return densidades, prosa


def _linha(chave: tuple[str, str], obs: list[dict]) -> dict:
    com_denominador = [o for o in obs if o["itens"] and o["ancoras_total"] is not None]
    densidades, prosa = _taxas(com_denominador)
    return {
        "prompt_version": chave[0],
        "manifest_version": chave[1],
        "n_runs": len(obs),
        "n_com_denominador": len(com_denominador),
        "n_unknown": len(obs) - len(com_denominador),
        # Os dois termos que o "9→5" conflaciava.
        "ancoras_total_mediana": _mediana([o["ancoras_total"] for o in com_denominador]),
        "itens_mediana": _mediana([o["itens"] for o in com_denominador]),
        "ancoras_por_item_mediana": _mediana(densidades),
        "prosa_monetaria_por_item_mediana": _mediana(prosa),
        "items_dropped_total": sum(o["items_dropped"] or 0 for o in obs),
        "procedencias": sorted({o["procedencia_do_denominador"] for o in obs}),
        "inventarios_de_prosa": sorted({str(o["prose_inventory_version"]) for o in obs}, key=str),
    }


def _mediana(valores: list) -> float | None:
    return round(statistics.median(valores), 4) if valores else None


def _fetch(workspace_id: str | None) -> list[dict]:
    from sqlalchemy import select

    from backend.app.core.database import SyncSessionLocal
    from backend.app.models.pipeline_run import PipelineRun, PipelineStageLog
    from backend.app.services.parecer_drift_monitor import PARECER_STAGES

    stmt = (
        select(PipelineStageLog.output_summary)
        .join(PipelineRun, PipelineStageLog.pipeline_run_id == PipelineRun.id)
        .where(
            PipelineStageLog.stage.in_(PARECER_STAGES),
            PipelineStageLog.output_summary.isnot(None),
        )
        .order_by(PipelineStageLog.started_at.desc())
    )
    if workspace_id:
        stmt = stmt.where(PipelineRun.workspace_id == workspace_id)
    with SyncSessionLocal() as db:
        return [r[0] for r in db.execute(stmt).all() if isinstance(r[0], dict)]


def _print_tabela(tabela: list[dict]) -> None:
    for linha in tabela:
        print(
            f"  {linha['prompt_version']:>8} / manifest {linha['manifest_version']:>7} | "
            f"n={linha['n_runs']:>2} (unknown={linha['n_unknown']}) | "
            f"ancoras={linha['ancoras_total_mediana']} itens={linha['itens_mediana']} "
            f"→ {linha['ancoras_por_item_mediana']}/item | "
            f"prosa={linha['prosa_monetaria_por_item_mediana']}/item | "
            f"dropped={linha['items_dropped_total']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", default=None, help="filtra 1 workspace")
    parser.add_argument("--out", required=True, help="destino JSON (use storage/, off-git)")
    args = parser.parse_args()

    summaries = _fetch(args.workspace_id)
    observacoes = [_observacao(s) for s in summaries]
    tabela = _agrega(observacoes)
    destino = Path(args.out)
    destino.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "n_execucoes_do_stage": len(summaries),
        "tabela_por_versao": tabela,
        "observacoes": observacoes,
    }
    destino.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(summaries)} execuções do stage → {len(tabela)} janelas")
    _print_tabela(tabela)
    print(f"escrito em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
