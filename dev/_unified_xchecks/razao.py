"""X2 · X3 · X3b — conservacao e determinismo do razao (E3 -> E4 -> view-model)."""

from __future__ import annotations

import json

from dev._unified_xchecks.base import _cents, _db, cat_despesa, e4_do_run, mes_do_label, veredito


def _flatten_fmd(nome: str, payload: dict) -> dict:
    return {
        (f"{nome}.{sec}", cat, mes): _cents(v) or 0
        for sec in ("receitas", "despesas")
        for mes, linhas in (payload.get(sec, {}).get("por_mes") or {}).items()
        for cat, v in (linhas or {}).items()
    }


def flatten_balde(nome: str, payload: dict) -> dict:
    """{(balde, categoria, mes) -> cents}."""
    # `despesas`/`receitas` guardam {categoria -> [tx]} sob `dados` (NAO `itens` —
    # um flattener que procura `itens` compara zero celulas e imprime verde).
    if nome == "fluxo_mensal_detalhado":
        return _flatten_fmd(nome, payload)
    out: dict[tuple, int] = {}
    for cat, txs in (payload.get("dados") or {}).items():
        for it in txs or []:
            c = _cents(it.get("valor")) if isinstance(it, dict) else None
            if c is None:
                continue
            k = (nome, cat, str(it.get("data") or it.get("mes") or "")[:7])
            out[k] = out.get(k, 0) + c
    return out


def _x2_coleta(ws: str, run: str) -> tuple:
    _t, SyncSessionLocal, _r, _d, _l = _db()
    from sqlalchemy import text as _text

    from dev.certify_ledger_local import _e3_of_run, _rederive_entregue

    sql = _text("SELECT COUNT(*) FROM transaction_overrides WHERE workspace_id=:w")
    with SyncSessionLocal() as s:
        antes = s.execute(sql, {"w": ws}).scalar()
        e3 = _e3_of_run(s, ws, run)
        _res, fresco = _rederive_entregue(s, ws, run, e3)
        persist = e4_do_run(s, ws, run)
        depois = s.execute(sql, {"w": ws}).scalar()
    return antes, depois, e3, fresco, persist


def _x2_par(b: str, fresco: dict, persist: dict):
    if b not in persist or b not in fresco:
        return None
    a, p = flatten_balde(b, fresco[b]), flatten_balde(b, persist[b])
    chaves = set(a) | set(p)
    return chaves, [k for k in chaves if a.get(k, 0) != p.get(k, 0)], a, p


def _x2_linha(b: str, par) -> int:
    chaves, div, a, p = par
    sa, sp = sum(a.values()), sum(p.values())
    print(
        f"| `{b}`{' ⛔VAZIO' if not chaves else ''} | {len(chaves)} | {len(div)} "
        f"| {sa} | {sp} | {sa - sp} |"
    )
    for k in sorted(div)[:8]:
        print(
            f"|   ↳ DIV | `{k[0]}` / `{k[1]}` / {k[2]} | | {a.get(k, 0)} | {p.get(k, 0)} "
            f"| {a.get(k, 0) - p.get(k, 0)} |"
        )
    return len(div)


def _x2_cabecalho(antes, depois, e3: dict, persist: dict) -> None:
    print("## X2 — E4 re-derivado do E3 PERSISTIDO do run vs E4 persistido (cents, tol-zero)")
    print(
        f"pin transaction_overrides: antes={antes} depois={depois} "
        f"{'✅ estavel' if antes == depois else '⚠️ MUDOU — confundidor de regra aprendida'}"
    )
    print(f"grupos E3 semeados: {len(e3)} · baldes E4 persistidos: {sorted(persist)}\n")
    print("| balde | celulas | divergentes | Σ fresco (cents) | Σ persistido | delta |")
    print("|---|---|---|---|---|---|")


def _x2_corpo(baldes: tuple, fresco: dict, persist: dict) -> tuple[int, int, int]:
    div_total, cel_total, lidos = 0, 0, 0
    for b in baldes:
        par = _x2_par(b, fresco, persist)
        if par is None:
            print(f"| `{b}` | — | — | — | — | AUSENTE |")
            continue
        div_total += _x2_linha(b, par)
        cel_total += len(par[0])
        lidos += 1 if par[0] else 0
    return div_total, cel_total, lidos


def x2(ws: str, run: str) -> None:
    baldes = ("despesas", "receitas", "fluxo_mensal_detalhado")
    antes, depois, e3, fresco, persist = _x2_coleta(ws, run)
    _x2_cabecalho(antes, depois, e3, persist)
    div_total, cel_total, lidos = _x2_corpo(baldes, fresco, persist)
    veredito(
        "X2",
        lidos,
        len(baldes),
        div_total,
        nota=f"celulas={cel_total} · `_rederive_entregue` semeia SO E3 ⇒ `patrimonio` "
        f"omitido e `seguros` no placeholder (ausencia estrutural, nao perda)",
    )


def _x3_specs(blk: dict, fmd: dict) -> tuple:
    return (
        (
            "receitas",
            {d["label"]: d["data"] for d in blk["receita_datasets"]},
            fmd["receitas"]["por_mes"],
            lambda x: x,
        ),
        (
            "despesas",
            {d["label"]: d["data"] for d in blk["despesa_datasets"]},
            fmd["despesas"]["por_mes"],
            cat_despesa,
        ),
    )


def _x3_serie(serie: list, e4: dict, c: str, labels: list, sec: str) -> tuple:
    """Uma categoria contra o E4. Mes fora do E4 nao entra — nem como celula nem
    como divergencia (era assim que 647 'divergencias' de rotulo nasciam no `U3`)."""
    total, div = 0, []
    for i, lbl in enumerate(labels):
        mes = mes_do_label(lbl)
        if mes not in e4:
            continue
        total += 1
        a, b = _cents(serie[i]) or 0, _cents(e4[mes].get(c, 0)) or 0
        if a != b:
            div.append((sec, c, mes, a, b))
    return total, div


def _x3_celulas(vm_ds: dict, e4: dict, norm, labels: list, sec: str) -> tuple:
    total, div = 0, []
    for c_lbl, serie in vm_ds.items():
        t, d = _x3_serie(serie, e4, norm(c_lbl), labels, sec)
        total, div = total + t, div + d
    return total, div


def _x3_escalar_linha(sec: str, vm_ds: dict, publicado: dict, norm, n_janela: int) -> None:
    # `despesas_por_categoria` e `por_fonte_detalhado` sao agregados da JANELA
    # de `janela_meses` (12m), nao do periodo completo. Comparar contra a soma
    # da serie inteira (44 meses) produzia 11 divergencias que eram do
    # instrumento — medido no `U4`, com `Arvo` casando 1,0 e `Kiwify` 359x.
    soma = {norm(c): sum(_cents(x) or 0 for x in v[-n_janela:]) for c, v in vm_ds.items()}
    pub = {norm(c): _cents(v) or 0 for c, v in publicado.items()}
    difs = [
        (c, soma.get(c, 0), pub.get(c, 0))
        for c in sorted(set(soma) & set(pub))
        if soma.get(c, 0) != pub.get(c, 0)
    ]
    so_serie = sorted(set(soma) - set(pub))
    print(
        f"  {sec}: comparadas={len(set(soma) & set(pub))} divergentes={len(difs)} "
        f"· so-na-serie={so_serie or '—'} (janela={n_janela}m)"
    )
    for c, a, b in difs[:12]:
        print(f"    DIV {c!r}: Σserie_{n_janela}m={a} publicado={b} delta={a - b}")


def _x3_escalar_pares(vm: dict, blk: dict, n_janela: int) -> tuple:
    # Janelas DIFERENTES lado a lado em `fluxo_caixa`, sem nada no nome que as
    # distinga: `despesas_por_categoria` e periodo completo (enricher:363);
    # `por_fonte_detalhado` e a janela de `janela_meses` (:579). Medido no `U4`.
    return (
        (
            "despesas",
            {d["label"]: d["data"] for d in blk["despesa_datasets"]},
            vm["fluxo_caixa"]["despesas_por_categoria"],
            cat_despesa,
            len(blk["labels"]),
        ),
        (
            "receitas",
            {d["label"]: d["data"] for d in blk["receita_datasets"]},
            vm["fluxo_caixa"]["por_fonte_detalhado"],
            lambda x: x,
            n_janela,
        ),
    )


def _x3_escalar(vm: dict, blk: dict) -> None:
    n_janela = int(vm["fluxo_caixa"].get("janela_meses_agregado") or 12)
    print(f"### escalar: Σ ultimos {n_janela}m da serie vs total publicado no card")
    for sec, vm_ds, publicado, norm, janela in _x3_escalar_pares(vm, blk, n_janela):
        _x3_escalar_linha(sec, vm_ds, publicado, norm, janela)


def _x3_categorias(sec: str, vm_ds: dict, e4: dict, norm) -> None:
    e4_cats = {c for m in e4.values() for c in m}
    vm_cats = {norm(c) for c in vm_ds}
    print(
        f"### {sec}: vm={len(vm_cats)} e4={len(e4_cats)} "
        f"· so-vm={sorted(vm_cats - e4_cats) or '—'} · so-e4={sorted(e4_cats - vm_cats) or '—'}"
    )


def _x3_cabecalho(labels: list, meses_vm: list, fmd: dict, intersec: list) -> None:
    print("## X3 — serie vetorial view-model vs fluxo_mensal_detalhado (cents, tol-zero)")
    print(f"labels view-model: {len(labels)} · meses_ordenados E4: {len(fmd['meses_ordenados'])}")
    print(
        f"meses no E4 e FORA da janela do view-model: "
        f"{[m for m in fmd['meses_ordenados'] if m not in meses_vm]}  (corte — LC5-08)"
    )
    print(f"intersecao de meses: {len(intersec)}/{len(meses_vm)}\n")


def x3(ws: str, run: str, vm_path: str) -> None:
    _t, SyncSessionLocal, _r, _d, _l = _db()
    vm = json.load(open(vm_path))
    with SyncSessionLocal() as s:
        fmd = e4_do_run(s, ws, run)["fluxo_mensal_detalhado"]
    blk = vm["fluxo_caixa"]["receita_despesa_mensal_detalhado"]
    labels = blk["labels"]
    meses_vm = [mes_do_label(x) for x in labels]
    intersec = [m for m in meses_vm if m in set(fmd["meses_ordenados"])]
    _x3_cabecalho(labels, meses_vm, fmd, intersec)
    total, div, esperado = 0, [], 0
    for sec, vm_ds, e4, norm in _x3_specs(blk, fmd):
        _x3_categorias(sec, vm_ds, e4, norm)
        esperado += len(vm_ds) * len(intersec)
        t, d = _x3_celulas(vm_ds, e4, norm, labels, sec)
        total, div = total + t, div + d
    for sec, c, mes, a, b in div[:20]:
        print(f"  DIV {sec}/{c}/{mes}: vm={a} e4={b} delta={a - b}")
    _x3_escalar(vm, blk)
    veredito("X3", total, esperado, len(div))


def _x3b_canais(pay3: list) -> dict:
    canais: dict[str, dict[str, int]] = {}
    for p in pay3:
        for canal, v in (p.get("remocoes") or {}).items():
            acc = canais.setdefault(canal, {"count": 0, "valor_cents": 0})
            acc["count"] += v.get("count", 0) or 0
            acc["valor_cents"] += v.get("valor_cents", 0) or 0
    return canais


def _x3b_relatorio(pay3: list, canais: dict, cons: dict, cdc: int) -> None:
    print("## X3b — consolidacao declarada (E4 do run) vs executada (E3 do run)")
    print(f"grupos E3 do run: {len(pay3)}")
    for canal, v in sorted(canais.items()):
        print(f"  canal {canal}: count={v['count']} valor_cents={v['valor_cents']}")
    print(f"\nE4 consolidacao.count = {cons.get('count')} · Σ E3 collapse.count = {cdc}")
    print(
        f"E4 declara {len(cons.get('meses', []))} meses; `remocoes` do E3 NAO tem quebra por "
        f"mes ⇒ perna mensal NAO-VERIFICAVEL com o contrato atual"
    )


def x3b(ws: str, run: str) -> None:
    _t, SyncSessionLocal, _rows, _dec, _latest = _db()
    with SyncSessionLocal() as s:
        fmd = e4_do_run(s, ws, run)["fluxo_mensal_detalhado"]
        l3 = _latest(_rows(s, ws, ("reconcile_transactions",), run_id=run))
        pay3 = [_dec(r.content_json) for r in l3.values()]
    cons = fmd["consolidacao_cross_documento"]
    canais = _x3b_canais(pay3)
    cdc = canais.get("cross_document_collapse", {}).get("count", 0)
    _x3b_relatorio(pay3, canais, cons, cdc)
    veredito(
        "X3b escalar",
        len(pay3),
        len(pay3),
        int((cons.get("count") or 0) != cdc),
        nota=f"delta={(cons.get('count') or 0) - cdc}",
    )
