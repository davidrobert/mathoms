#!/usr/bin/env python3
"""Snapshot PII-safe + `--compare` anti-regressão para a skill pipeline-review (ADR-343).

Duas responsabilidades puras (testáveis sem DB):

- ``build_snapshot(...)`` — reduz os insumos de um run a um
  ``review_snapshot.json`` **PII-safe** (zero literal monetário; drift de valor
  vem do report_data cru no compare, nunca aqui).
- ``compare_reviews(...)`` — regressão em **3 pernas** (conservação, drift de
  valor via ``golden_diff``, saúde de execução), com **suppressors** (tier
  downgrade / corpus cresceu) que evitam falso-fail. Reusa
  ``golden_diff.diff_golden``, nunca o gate de manifesto de CI.

CLI: ``--current <dir> --baseline <dir> [--strict] [--band 10]``, cada ``<dir>``
com ``review_snapshot.json`` + ``report_data.json``. Exit 1 em regressão HARD.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.golden_diff import diff_golden, to_cents
from dev.review_snapshot import (
    _SECTION_KEYS,
    SCHEMA_VERSION,
    _leaf,
    build_snapshot,
    elapsed_minutes,
)
from dev.serie_cambial import serie_reiniciada_cambial

# Conservação numérica (tolerância zero): estende o set de pausa da produção
# (_CONSERVATION_CHECKS = {CV1,CV2,CV3,CV6} em scripts/validate_cross.py) com os
# checks simétricos CV16/CV17. Regressão nesses é HARD, nunca suprimida.
_CONSERVATION_HARD = frozenset({"CV1", "CV2", "CV3", "CV6", "CV16", "CV17"})
# Render/narrativa: falham legítimo em run incremental que reusa narrativa
# (A36.l3) → SOFT (só com --strict), fora do gate default.
_RENDER_SOFT = frozenset({"CV10", "CV11", "CV12", "CV13", "CV14"})
# ENTREGA de narrativa de seção (CV9 pós-ADR-356): destino declarado no layout
# que deixa de renderizar é parágrafo que sumiu do relatório, não ruído de run
# incremental — HARD no gate default. Sem isso o check nasceria silenciado no
# pipeline-review e trocaria-se um verde vazio por outro.
_DELIVERY_HARD = frozenset({"CV9"})

# Seções derivadas de LLM (dependem do tier premium) — regressão suprimida em
# tier downgrade (skip_llm / hard-stop ADR-173).
_TIER_DEPENDENT_SECTIONS = frozenset({"narrativas"})

# Voláteis: mudam entre runs idênticos, nunca são regressão (espelha
# _VOLATILE_LEAVES de backend/tests/test_report_view_model_snapshot.py). ADR-360
# tirou `prob_if_ate_idade_meta` do mascaramento no snapshot (o cone é
# reprodutível); a cópia aqui sobrevivia e mantinha o campo cego nesta ferramenta.
_VOLATILE_LEAVES = frozenset({"data_analise"})

_BRACKET_RE = re.compile(r"\[[^\]]*\]")


# ─────────────────────────────── compare ────────────────────────────────


def _llm_off(base: dict, cur: dict) -> bool:
    """LLM ausente no run atual — cache hit não conta."""
    # Parecer servido do cache (TTL 7 dias) tem zero chamadas LLM e continua
    # íntegro e comparável. Contá-lo como tier_downgrade zerava
    # `_parecer_regressions` inteiro — falso-verde ativo no gate da ADR-343.
    had = bool(base.get("run_health", {}).get("llm_calls"))
    has = bool(cur.get("run_health", {}).get("llm_calls"))
    if not (had and not has):
        return False
    return not cur.get("parecer", {}).get("cache_hit", False)


def _suppressors(base: dict, cur: dict) -> dict[str, bool]:
    bh, ch = base.get("run_health", {}), cur.get("run_health", {})
    tier_down = bh.get("tier_at_run") == "premium" and ch.get("tier_at_run") != "premium"
    bd, cd = bh.get("total_documents") or 0, ch.get("total_documents") or 0
    return {
        "tier_downgrade": tier_down or _llm_off(base, cur),
        "corpus_grew": cd > bd,
        "corpus_shrank": cd < bd,
    }


def _status_regression(base: dict, cur: dict) -> list[str]:
    b, c = base["run_health"].get("status"), cur["run_health"].get("status")
    if b == "completed" and c != "completed":
        stage = cur["run_health"].get("failed_at_stage") or "?"
        return [f"status {b} -> {c} (falhou em {stage})"]
    return []


def _cv_index(snap: dict) -> dict[str, dict]:
    return {c["check_id"]: c for c in snap.get("cross_validation", [])}


def _cv_regression_for(cid: str, b: dict | None, c: dict | None) -> str | None:
    if b is None:
        return None
    if c is None:
        return f"conservação {cid} presente -> ausente"
    if b["passed"] and not c["passed"]:
        return f"conservação {cid} passa -> falha"
    return None


def _cv_regressions(base: dict, cur: dict) -> list[str]:
    bi, ci = _cv_index(base), _cv_index(cur)
    out = [_cv_regression_for(cid, bi.get(cid), ci.get(cid)) for cid in _CONSERVATION_HARD]
    return [m for m in out if m]


def _delivery_regressions(base: dict, cur: dict) -> list[str]:
    """CV9 (ADR-356) — entrega de narrativa de seção que passa a falhar."""
    bi, ci = _cv_index(base), _cv_index(cur)
    return [
        f"entrega {cid} passa -> falha"
        for cid in sorted(_DELIVERY_HARD)
        if _render_regressed(bi.get(cid), ci.get(cid))
    ]


def _tx_regression(base: dict, cur: dict, sup: dict) -> list[str]:
    b, c = base["run_health"].get("transacoes_total"), cur["run_health"].get("transacoes_total")
    if b and c is not None and c < b and not sup["corpus_shrank"]:
        return [f"transacoes_total {b} -> {c} (corpus não encolheu)"]
    return []


def _section_regression_for(key: str, b: str, c: str, sup: dict) -> str | None:
    if b != "populated" or c == "populated":
        return None
    if sup["tier_downgrade"] and key in _TIER_DEPENDENT_SECTIONS:
        return None
    return f"seção {key} populated -> {c}"


def _section_regressions(base: dict, cur: dict, sup: dict) -> list[str]:
    cur_sections = cur.get("sections", {})
    out = [
        _section_regression_for(key, b, cur_sections.get(key, "absent"), sup)
        for key, b in base.get("sections", {}).items()
    ]
    return [m for m in out if m]


def _parecer_regressions(base: dict, cur: dict, sup: dict) -> list[str]:
    if sup["tier_downgrade"]:
        return []
    b, c = base.get("parecer", {}), cur.get("parecer", {})
    out = []
    if b.get("status") == "ok" and c.get("status") != "ok":
        out.append(f"parecer ok -> {c.get('status')}")
    if b.get("schema_valid") and not c.get("schema_valid"):
        out.append("parecer schema_valid True -> False")
    if (b.get("n_secoes") or 0) > (c.get("n_secoes") or 0):
        out.append(f"parecer n_secoes {b.get('n_secoes')} -> {c.get('n_secoes')}")
    return out


def _mask_path(path: str) -> str:
    """Colapsa chaves-natural (`[Nome]`) do path — evita PII no output do compare."""
    return _BRACKET_RE.sub("[]", path)


def _pct(old_c: int, new_c: int) -> float:
    return (new_c - old_c) / abs(old_c) * 100 if old_c else float("inf")


def _drift_line(d: Any, band: float) -> tuple[str | None, str | None]:
    """Retorna (desaparecimento HARD, drift partial) para um FieldDiff monetário."""
    if not d.is_monetary_value_delta() or _leaf(d.path) in _VOLATILE_LEAVES:
        return None, None
    old_c, new_c = to_cents(d.old), to_cents(d.new)
    if old_c and new_c == 0:
        return f"{_mask_path(d.path)} -> 0 (balde zerado)", None
    p = _pct(old_c, new_c)
    if abs(p) > band or (old_c and new_c and (old_c > 0) != (new_c > 0)):
        return None, f"{_mask_path(d.path)}: {p:+.1f}%"
    return None, None


def _value_drift(base_rd: dict, cur_rd: dict, band: float) -> tuple[list[str], list[str]]:
    """Retorna (desaparecimentos HARD, drifts partial). Só monetário; volátil fora."""
    gone, drift = [], []
    for d in diff_golden(base_rd, cur_rd):
        g, dr = _drift_line(d, band)
        if g:
            gone.append(g)
        if dr:
            drift.append(dr)
    return gone, drift


def _soft_changes(base: dict, cur: dict, sup: dict) -> list[str]:
    bi, ci = _cv_index(base), _cv_index(cur)
    out = [
        f"render {cid} passa -> falha"
        for cid in _RENDER_SOFT
        if _render_regressed(bi.get(cid), ci.get(cid))
    ]
    bnr, cnr = sum(base.get("needs_review", {}).values()), sum(cur.get("needs_review", {}).values())
    if cnr > bnr and not sup["corpus_grew"]:
        out.append(f"needs_review {bnr} -> {cnr}")
    return out + _diagnostic_changes(base, cur, sup) + _cost_changes(base, cur)


def _render_regressed(b: dict | None, c: dict | None) -> bool:
    return bool(b and c and b["passed"] and not c["passed"])


def _cost_changes(base: dict, cur: dict) -> list[str]:
    bd = base["run_health"].get("duration_min") or 0
    cd = cur["run_health"].get("duration_min") or 0
    if bd and cd > bd * 1.5:
        return [f"duração {bd} -> {cd} min (+{(cd / bd - 1) * 100:.0f}%)"]
    return []


# Piso de 0,10pp: abaixo disso o par é ruído de arredondamento, não migração.
_RECLASSIFICACAO_MIN_CENTESIMOS = 10
# Tolerância do fechamento do par (0,02pp) — Σ dos dois lados deve zerar.
_RECLASSIFICACAO_TOL_CENTESIMOS = 2


# Assinatura de RECLASSIFICAÇÃO, e por isso `corpus_grew` não a suprime: corpus
# maior move muitas classes na MESMA direção, nunca duas em módulo igual e sinal
# oposto com o resto parado. É a dimensão que os 16 CV não cobrem — migração
# entre baldes preserva Σ por construção ([[ADR-406]]).
def _reclassificacao_regression(base: dict, cur: dict) -> list[str]:
    b = (base.get("investimentos_mix") or {}).get("classes") or {}
    c = (cur.get("investimentos_mix") or {}).get("classes") or {}
    if not b or not c:
        return []
    deltas = {k: c.get(k, 0) - b.get(k, 0) for k in set(b) | set(c)}
    moveram = {k: d for k, d in deltas.items() if abs(d) >= _RECLASSIFICACAO_MIN_CENTESIMOS}
    if len(moveram) != 2 or abs(sum(moveram.values())) > _RECLASSIFICACAO_TOL_CENTESIMOS:
        return []
    par = " <-> ".join(sorted(moveram))
    return [
        f"reclassificação entre baldes: {par} ({max(abs(d) for d in moveram.values()) / 100:+.2f}pp)"
    ]


# A queda de instituições distintas só é comparável contra o número de posições:
# medida no §r7 como 18→16 com o corpus parado. Totais, não pares por índice —
# a lista é ordenada pelo próprio par e o índice não é identidade de membro.
def _identidade_regression(base: dict, cur: dict) -> list[str]:
    bm = (base.get("investimentos_mix") or {}).get("membros") or []
    cm = (cur.get("investimentos_mix") or {}).get("membros") or []
    if not bm or not cm:
        return []
    b_pos, b_inst = (sum(x) for x in zip(*bm))
    c_pos, c_inst = (sum(x) for x in zip(*cm))
    if c_inst < b_inst and c_pos >= b_pos:
        return [f"instituições distintas {b_inst} -> {c_inst} com posições {b_pos} -> {c_pos}"]
    return []


# A tabela `review_reasons` ganha leitor aqui (ADR-411 D5). Leitura TOLERANTE de
# propósito: baseline em schema v2 não tem a chave, e lê-la como `{}` diria "o
# canal morreu" sobre um run que nunca a escreveu — veredito fabricado.
def _sem_diagnostico(snap: dict) -> bool:
    return "review_reasons" not in snap


# Prova de fecho da A40.l81: num run sem pausa a tabela não pode ficar vazia se
# algum stage emitiu razão. Vazia depois de cheia é o sink tendo voltado a rodar
# só no ramo de pausa.
def _diagnostic_regression(base: dict, cur: dict) -> list[str]:
    """HARD: o canal emudeceu — tinha razão, agora não tem nenhuma."""
    if _sem_diagnostico(base) or _sem_diagnostico(cur):
        return []
    b, c = base["review_reasons"], cur["review_reasons"]
    if b and not c:
        return [f"review_reasons {sum(b.values())} ocorrência(s) -> tabela VAZIA (canal mudo)"]
    return []


def _diagnostic_changes(base: dict, cur: dict, sup: dict) -> list[str]:
    """SOFT: a razão cresceu, ou apareceu numa posição nova."""
    if _sem_diagnostico(base) or _sem_diagnostico(cur):
        return ["snapshot sem `review_reasons` (baseline pré-ADR-411) — perna de diagnóstico CEGA"]
    b, c = base["review_reasons"], cur["review_reasons"]
    out = []
    novas = sorted(set(c) - set(b))
    if novas:
        out.append(f"review_reasons: {len(novas)} posição(ões) nova(s) — {', '.join(novas[:3])}")
    bt, ct = sum(b.values()), sum(c.values())
    if ct > bt and not sup["corpus_grew"]:
        out.append(f"review_reasons {bt} -> {ct} ocorrências (corpus não cresceu)")
    return out


def _hard_regressions(
    base: dict, cur: dict, base_rd: dict, cur_rd: dict, sup: dict, band: float
) -> tuple[list[str], list[str]]:
    """Retorna (hard, drift). ``drift`` vira hard ou soft conforme corpus_grew."""
    hard = _status_regression(base, cur) + _cv_regressions(base, cur)
    hard += _delivery_regressions(base, cur)
    hard += _tx_regression(base, cur, sup) + _section_regressions(base, cur, sup)
    hard += _parecer_regressions(base, cur, sup)
    hard += _reclassificacao_regression(base, cur) + _identidade_regression(base, cur)
    hard += _diagnostic_regression(base, cur)
    gone, drift = _value_drift(base_rd, cur_rd, band)
    return hard + gone, drift


_BLIND_DIMENSION_NOTE = (
    "dimensão CEGA: config em DB (categorização, fiscal, câmbio, metas) muda "
    "número sem commit — nenhum veredito de não-determinismo é válido aqui"
)


def provenance_notes(base: dict, cur: dict) -> list[str]:
    """Contexto de proveniência — jamais supressor, jamais perna de regressão."""
    # O amplificador "zero commits + drift ⇒ severidade sobe" foi MEDIDO como dead
    # code (52/15/24 commits nas 3 janelas reais) e a inferência seria inválida.
    bp, cp = base.get("provenance") or {}, cur.get("provenance") or {}
    # Decide pelo PLURAL: sob execução mista o escalar é None de propósito, e ler
    # dele reportaria "desconhecida" para um run cuja proveniência é conhecida.
    bl, cl = _revision_list(bp), _revision_list(cp)
    out = []
    if bl and cl and bl != cl:
        out.append(f"revisão do executor mudou: {','.join(bl)} -> {','.join(cl)}")
    if not bl or not cl:
        out.append("revisão do executor desconhecida em um dos runs — comparação sem proveniência")
    for lado, prov in (("baseline", bp), ("atual", cp)):
        if prov.get("execucao_mista"):
            out.append(f"execução mista no run {lado}: stages rodaram em revisões diferentes")
        if prov.get("atribuicao_parcial"):
            out.append(f"atribuição PARCIAL no run {lado}: alguns stages sem revisão declarada")
    return out + [_BLIND_DIMENSION_NOTE] if out else out


def _revision_list(prov: dict) -> list[str]:
    plural = prov.get("executor_revisions")
    if isinstance(plural, list) and plural:
        return [str(x) for x in plural]
    single = prov.get("executor_revision")
    return [str(single)] if single else []


def compare_reviews(
    base: dict, cur: dict, base_rd: dict, cur_rd: dict, *, strict: bool = False, band: float = 10.0
) -> tuple[list[str], list[str], list[str]]:
    """Retorna (hard, soft, notes). ``hard`` não-vazio ⇒ exit 1."""
    sup = _suppressors(base, cur)
    notes = [f"suppressor ativo — {k}" for k, v in sup.items() if v]
    notes += [f"contexto — {n}" for n in provenance_notes(base, cur)]
    reinicio = serie_reiniciada_cambial(base_rd, cur_rd)
    if reinicio:
        notes.append(reinicio)
    hard, drift = _hard_regressions(base, cur, base_rd, cur_rd, sup, band)
    soft = _soft_changes(base, cur, sup)
    if sup["corpus_grew"]:
        soft += [f"drift de valor (informativo, corpus cresceu): {d}" for d in drift]
    else:
        hard += [f"drift de valor: {d}" for d in drift]
    if strict:
        hard, soft = hard + soft, []
    return hard, soft, notes


# ─────────────────────────────── CLI ────────────────────────────────


def _load(dir_path: Path, name: str) -> dict:
    return json.loads((dir_path / name).read_text(encoding="utf-8"))


def _compare_dirs(
    current: Path, baseline: Path, strict: bool, band: float
) -> tuple[list[str], list[str], list[str]]:
    return compare_reviews(
        _load(baseline, "review_snapshot.json"),
        _load(current, "review_snapshot.json"),
        _load(baseline, "report_data.json"),
        _load(current, "report_data.json"),
        strict=strict,
        band=band,
    )


def _print_compare(hard: list[str], soft: list[str], notes: list[str]) -> None:
    for n in notes:
        print(f"NOTE: {n}")
    for s in soft:
        print(f"CHANGED: {s}")
    for h in hard:
        print(f"FAIL: {h}")


def _run_compare(current: Path, baseline: Path, *, strict: bool, band: float) -> int:
    if not (baseline / "review_snapshot.json").exists():
        print(
            f"baseline não encontrado: {baseline}/review_snapshot.json — rode o run baseline antes"
        )
        return 2
    hard, soft, notes = _compare_dirs(current, baseline, strict, band)
    _print_compare(hard, soft, notes)
    verdict = f"{len(hard)} regressão(ões)" if hard else "sem regressões"
    print(f"\n{verdict} vs {baseline}")
    return 1 if hard else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--current", type=Path, required=True, help="dir do run atual (coletado)")
    parser.add_argument("--baseline", type=Path, required=True, help="dir do run baseline")
    parser.add_argument("--strict", action="store_true", help="regras SOFT viram HARD")
    parser.add_argument("--band", type=float, default=10.0, help="banda %% de drift de valor")
    args = parser.parse_args(argv)
    return _run_compare(args.current, args.baseline, strict=args.strict, band=args.band)


if __name__ == "__main__":
    raise SystemExit(main())
