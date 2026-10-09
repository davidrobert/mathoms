"""X8 — o parecer viu o corpo inteiro? Orçamento do exec context publicado pelo stage."""

# `PV13-17` (`U5`) + [[A40.l124]]: a eviction por seção ([[ADR-341]] D2) tirou
# `investimentos` (2026-08-26) e `independencia_financeira` (2026-08-29) do parecer do
# dogfood e nenhuma rodada viu — o marcador só existia DENTRO do prompt, e medir exigia
# decifrar o E5 à mão. Desde a l124 o stage publica o orçamento em
# `pipeline_stage_logs.output_summary.exec_context` (texto claro: só bytes e ids de
# seção) e este check o lê por SELECT.
#
# Ausência de medição NÃO é medição de ausência: run anterior à telemetria, stage
# pulado e orçamento desconhecido (hit de envelope de cache antigo) saem INAPLICAVEL,
# jamais verde.

from __future__ import annotations

import json

from dev._unified_xchecks.base import _db, veredito

STAGE_DO_PARECER = "review_finances_holistic"
# Limiar de REDIMENSIONAMENTO ([[ADR-341]] §Emenda 2026-10-09): o cap é dimensionado com
# folga >= 20% sobre a demanda medida; abaixo de 15% o manifest tem de ser re-medido.
FOLGA_MINIMA = 0.15


def _inaplicavel(nome: str, motivo: str) -> None:
    print(f"  INDETERMINADO: {motivo}")
    veredito(nome, 0, 1, 0, n_falsificavel=0, nota=motivo)


def _motivo_sem_orcamento(summary: dict | None) -> str | None:
    """Por que não há orçamento legível; ``None`` = há."""
    if summary is None:
        return "o parecer nao tem log de stage neste run"
    if summary.get("skipped"):
        return "stage do parecer pulado neste run"
    if "exec_context" not in summary:
        return "stage anterior a telemetria (A40.l124): orcamento nunca publicado"
    if not isinstance(summary["exec_context"], dict):
        return "orcamento DESCONHECIDO: hit de envelope antigo ou corpo nao montado"
    return None


def _secoes(orcamento: dict) -> None:
    ids = list(orcamento.get("section_bytes") or {})
    evictadas = list(orcamento.get("evicted_section_ids") or [])
    cortada = 1 if orcamento.get("hard_cut") else 0
    print(f"secoes no corpo: {len(ids) - len(evictadas)}/{len(ids)} · evictadas: {evictadas}")
    print(f"  corte degenerado (secao restante cortada no meio): {bool(cortada)}")
    nota = "secao evictada e nao-mostrada ao modelo — o parecer deste run nao a leu"
    veredito("X8", len(ids), len(ids), len(evictadas) + cortada, n_falsificavel=len(ids), nota=nota)


def _folga(orcamento: dict) -> None:
    cap, demanda = int(orcamento.get("cap_bytes") or 0), int(orcamento.get("demand_bytes") or 0)
    if cap <= 0:
        return _inaplicavel("X8-folga", "cap ilegivel no orcamento publicado")
    folga = (cap - demanda) / cap
    print(f"demanda {demanda} B · cap {cap} B · folga {folga:.1%} (minima {FOLGA_MINIMA:.0%})")
    print(
        f"  fora do orcamento: hints {orcamento.get('hints_bytes')} B · catalogo "
        f"{orcamento.get('catalog_bytes')} B"
    )
    nota = "abaixo da minima: redimensionar o cap pela regra da ADR-341 §Emenda 2026-10-09"
    veredito("X8-folga", 1, 1, int(folga < FOLGA_MINIMA), n_falsificavel=1, nota=nota)


def avaliar_orcamento(summary: dict | None) -> None:
    """Vereditos X8 sobre o ``output_summary`` do stage do parecer (``None`` = sem log)."""
    motivo = _motivo_sem_orcamento(summary)
    if motivo is not None:
        return _inaplicavel("X8", motivo)
    _secoes(summary["exec_context"])
    _folga(summary["exec_context"])


def _summary_do_parecer(run: str) -> dict | None:
    text, SyncSessionLocal, *_ = _db()
    sql = (
        "SELECT output_summary FROM pipeline_stage_logs "
        "WHERE pipeline_run_id=:r AND stage=:s ORDER BY started_at DESC"
    )
    with SyncSessionLocal() as s:
        row = s.execute(text(sql), {"r": run, "s": STAGE_DO_PARECER}).first()
    if row is None or row[0] is None:
        return None
    return json.loads(row[0]) if isinstance(row[0], str) else row[0]


def x8(ws: str, run: str) -> None:
    """Orçamento do exec context do parecer do run: seções fora do corpo e folga."""
    print(f"## X8 — o parecer viu o corpo inteiro? (ws {ws[:8]} · run {run[:8]})")
    avaliar_orcamento(_summary_do_parecer(run))
