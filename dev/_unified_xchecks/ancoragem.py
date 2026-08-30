"""X4 — ancoragem dos literais do parecer · sonda LC06 — denominadores de identidade."""

from __future__ import annotations

import collections
import json
import re

from dev._unified_xchecks.base import _cents, _db, e4_do_run, veredito


def _walk_numbers(o, path="", out=None):
    out = [] if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            _walk_numbers(v, f"{path}.{k}", out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _walk_numbers(v, f"{path}[{i}]", out)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        out.append((path, o))
    return out


def _literais(par: dict) -> list[tuple]:
    texto = json.dumps(par, ensure_ascii=False)
    achados = []
    for lit in re.findall(r"R\$\s?([\d.]+,\d{2}|[\d.]+)", texto):
        c = _cents(lit.replace(".", "").replace(",", "."))
        if c is not None:
            achados.append((lit, c))
    return achados


def x4(ws: str, run: str, parecer_path: str, vm_path: str) -> None:
    par, vm = json.load(open(parecer_path)), json.load(open(vm_path))
    universo = {c for _p, v in _walk_numbers(vm) if (c := _cents(v)) is not None}
    achados = _literais(par)
    orfaos = [a for a in achados if a[1] not in universo]
    print("## X4 — literais monetarios do parecer ancorados no E5 do mesmo run")
    print(f"universo de cents no view-model: {len(universo)}")
    print(f"literais R$ no parecer: {len(achados)} · orfaos: {len(orfaos)}")
    for _lit, c in orfaos[:20]:
        print(f"  ORFAO cents={c}")
    veredito(
        "X4",
        len(achados),
        len(achados),
        len(orfaos),
        nota="(literal monetario NAO e copiado para o git — so a contagem)",
    )


def _denominadores(itens: list, idkey: str) -> dict | None:
    """D1..D4. `None` quando o produtor nao emite `idkey` — sonda INAPLICAVEL,
    jamais lida como 'sem colisao' (§10 `U2` item 1)."""
    chaves = {k for it in itens if isinstance(it, dict) for k in it}
    if itens and idkey not in chaves:
        return None
    ids = [it.get(idkey) for it in itens if isinstance(it, dict)]
    nn = [i for i in ids if i not in (None, "")]
    warns: collections.Counter = collections.Counter()
    for it in itens:
        w = it.get("_dedup_warning") if isinstance(it, dict) else None
        if w:
            warns[w if isinstance(w, str) else json.dumps(w)[:40]] += 1
    return {
        "d1": len(itens),
        "d2": sum(1 for i in ids if i in (None, "")),
        "d3": len(nn) - len(set(nn)),
        "warns": warns,
    }


def _leitura(m: dict) -> str:
    if m["d1"] == 0:
        return "vazia"
    if m["d2"]:
        return "**NAO-VERIFICAVEL** (fail-closed: D2>0)"
    return "**CANDIDATO** (vai ao cetico)" if m["d3"] else "sem colisao de id"


def _linha_sonda(nome: str, itens: list, idkey: str) -> None:
    m = _denominadores(itens, idkey)
    if m is None:
        print(f"| `{nome}` | {len(itens)} | — | — | — | **SONDA INAPLICAVEL**: `{idkey}` ausente |")
        return
    d4 = sum(m["warns"].values())
    print(f"| `{nome}` | {m['d1']} | {m['d2']} | {m['d3']} | {d4} | {_leitura(m)} |")
    if m["warns"]:
        print(f"|   ↳ censo D4 | | | | {dict(m['warns'])} | reportavel direto |")


def sonda(ws: str, run: str) -> None:
    _t, SyncSessionLocal, _r, _d, _l = _db()
    with SyncSessionLocal() as s:
        pat = e4_do_run(s, ws, run)["patrimonio"]
    print("## Sonda da P0 no 1 (LC06) — denominadores primeiro, fail-closed\n")
    print(
        "| populacao | D1 itens | D2 id nulo | D3 len−len(set id) | D4 _dedup_warning | leitura |"
    )
    print("|---|---|---|---|---|---|")
    for nome, idkey in (
        ("investimentos_consolidados", "investment_id"),
        ("imoveis_consolidados", "property_id"),
        ("veiculos_consolidados", "veiculo_id"),
    ):
        _linha_sonda(nome, pat.get(nome) or [], idkey)
