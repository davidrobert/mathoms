#!/usr/bin/env python3
"""Snapshot de selecao E2 + baseline da rodada unificada, e o diff que o julga."""

# O runbook (§5 F1/F2) exige IDENTIDADE entre o mapa pre-run e o pos-run:
# `{(stage, artifact_key) -> (id, byte_size)}`, colapsado no mais recente.
#
# O modo `--compare` existe porque o `U3` publicou `E2 ✅` sobre um predicado que
# REPROVA — leu o delta como ruido. Aqui o veredito e sobre o mapa inteiro e
# nomeia cada unidade divergente, e o exit code impede a leitura otimista.
#
#     dev/unified_e2_snapshot.py <workspace_id> [--db mathoms.db]
#     dev/unified_e2_snapshot.py --compare <pre.json> <pos.json>

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

STAGES = ("consolidate_baseline", "extract_invoices", "extract_statements", "extract_with_llm")


def snapshot(workspace_id: str, db_path: str) -> dict[str, dict[str, object]]:
    """Mapa {stage|artifact_key -> {id, byte_size, run}}, ultimo por chave."""
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            f"SELECT stage, artifact_key, id, byte_size, pipeline_run_id FROM pipeline_artifacts "
            f"WHERE workspace_id=? AND stage IN ({','.join('?' * len(STAGES))}) ORDER BY id",
            (workspace_id, *STAGES),
        ).fetchall()
    finally:
        con.close()
    snap: dict[str, dict[str, object]] = {}
    for stage, key, artifact_id, byte_size, run in rows:
        snap[f"{stage}|{key}"] = {"id": artifact_id, "byte_size": byte_size, "run": run}
    return dict(sorted(snap.items()))


def compare(pre: dict, pos: dict) -> dict[str, object]:
    """Diff nomeado, separando churn de linha de mudanca de CONTEUDO."""
    # O runbook pedia identidade de `(id, byte_size)`. Medido no `U4`: um run
    # completo re-extrai e cunha `id` novo em 135 de 171 unidades — o predicado
    # literal e insatisfazivel e so pode sair vermelho. O que discrimina e a
    # COMPOSICAO (chaves) mais o CONTEUDO (`byte_size`); `id` e ruido esperado.
    only_pre = sorted(set(pre) - set(pos))
    only_pos = sorted(set(pos) - set(pre))
    comuns = sorted(set(pre) & set(pos))
    # 3o eixo: PROCEDENCIA. Unidade cuja `id` nao mudou nao foi reescrita por este
    # run — ela e HERDADA de outro. Chamar `id` de ruido zera o unico discriminador
    # entre re-derivada e herdada, e o veredito de conteudo passa a ter denominador
    # tautologico: no `U4`, 34 de 171 unidades (20%) nao podiam variar. Refutado
    # pela lente de invariante, medido: `extract_with_llm` = 0/34 deste run, 11 runs.
    herdadas = [k for k in comuns if pre[k]["id"] == pos[k]["id"]]
    rederivadas = [k for k in comuns if pre[k]["id"] != pos[k]["id"]]
    so_id = [k for k in rederivadas if pre[k]["byte_size"] == pos[k]["byte_size"]]
    conteudo = [
        {
            "chave": k,
            "pre": pre[k],
            "pos": pos[k],
            "delta_bytes": (pos[k]["byte_size"] or 0) - (pre[k]["byte_size"] or 0),
        }
        for k in comuns
        if pre[k]["byte_size"] != pos[k]["byte_size"]
    ]
    return {
        "n_pre": len(pre),
        "n_pos": len(pos),
        "n_rederivadas": len(rederivadas),
        "n_herdadas": len(herdadas),
        "composicao_estavel": not (only_pre or only_pos),
        "conteudo_estavel": not conteudo,
        "removidas": only_pre,
        "acrescentadas": only_pos,
        "so_id_mudou": so_id,
        "conteudo_mudou": conteudo,
        "herdadas": herdadas,
    }


def _print_compare(r: dict[str, object]) -> int:
    print(json.dumps(r, indent=2, ensure_ascii=False))
    n_comp = len(r["removidas"]) + len(r["acrescentadas"])
    # Denominador do conteudo e RUN-SCOPED: so unidade re-derivada podia variar.
    resumo = (
        f"n_unidades={r['n_pre']}/{r['n_pos']} · composicao_divergente={n_comp} · "
        f"conteudo_divergente={len(r['conteudo_mudou'])}/{r['n_rederivadas']} re-derivadas "
        f"(+{r['n_herdadas']} herdadas, inertes por construcao) · so_id={len(r['so_id_mudou'])}"
    )
    if r["composicao_estavel"] and r["conteudo_estavel"]:
        print(f"\nE2: PASS — {resumo}", file=sys.stderr)
        return 0
    if not r["composicao_estavel"]:
        print(
            f"\nE2: REPROVA (composicao) — {resumo}; o corpus mudou sob a medicao", file=sys.stderr
        )
        return 1
    print(
        f"\nE2: REPROVA (conteudo) — {resumo}; mesma populacao, unidade(s) re-extraida(s) "
        f"com conteudo diferente",
        file=sys.stderr,
    )
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_id", nargs="?")
    parser.add_argument("--db", default="mathoms.db")
    parser.add_argument("--compare", nargs=2, metavar=("PRE", "POS"))
    args = parser.parse_args()

    if args.compare:
        pre = json.loads(Path(args.compare[0]).read_text())
        pos = json.loads(Path(args.compare[1]).read_text())
        return _print_compare(compare(pre, pos))

    if not args.workspace_id:
        parser.error("workspace_id e obrigatorio fora do modo --compare")
    print(json.dumps(snapshot(args.workspace_id, args.db), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
