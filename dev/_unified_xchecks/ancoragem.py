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


_RS = re.compile(r"R\$\s?([\d.]+,\d{2}|[\d.]+)")

# Horizontes que carregam `ancoras[]` — a superficie que `stamp_ancora_values`
# sobrescreve no pos-LLM (ADR-296). Fechado de proposito: horizonte novo com
# ancora e invisivel aqui e voltaria a inflar o denominador em silencio, entao a
# paridade com o produtor e gateada em teste.
_HORIZONTES_COM_ANCORA = (
    "riscos",
    "sugestoes_execucao",
    "sugestoes_taticas",
    "sugestoes_estrategicas",
)


def _walk_literais(o, path="", out=None) -> list[tuple[str, int]]:
    """Toda ocorrencia `R$` do parecer, com o path CONCRETO dentro do documento.

    Por OCORRENCIA, nunca por valor: o mesmo numero aparece carimbado numa ancora
    e reescrito na prosa, e subtrair por valor apagaria justamente a copia autoral.
    """
    out = [] if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            _walk_literais(v, f"{path}.{k}", out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _walk_literais(v, f"{path}[{i}]", out)
    elif isinstance(o, str):
        for lit in _RS.findall(o):
            c = _cents(lit.replace(".", "").replace(",", "."))
            if c is not None:
                out.append((path, c))
    return out


def _resolvedor(vm: dict):
    """`path -> bool` pelo MESMO resolvedor que o backend usa para carimbar.

    Oraculo unico de proposito: a pergunta e *"o estampador teria sobrescrito
    este campo?"*, e so o resolvedor dele responde. `None` quando o manifesto ou
    o drill nao carregam — instrumento cego NAO classifica, e a alternativa
    (chutar `autoral`) publicaria DIVERGE fabricado.
    """
    try:
        from backend.app.services.parecer_manifest import load_manifest
        from pipeline.llm.tools.planner_drill_down import PlannerDrillDown

        whitelist = frozenset(load_manifest().tools_section_whitelist or ())
        drill = PlannerDrillDown(vm, whitelist, {})
    except Exception:
        return None
    return lambda p: drill.get_e5_jsonpath(p).found


def _paths_carimbados(par: dict, resolve) -> set[str]:
    """Paths de `valor_renderizado` que o backend sobrescreveu NESTE run.

    `_resolve_ancora` so escreve quando `result.found`; ancora cujo path nao
    resolve mantem o numero que o MODELO emitiu (`valor_renderizado` nao e
    `SkipJsonSchema`, ao contrario de `Metrica.nome/target`) — essa e autoral e
    tem de continuar no denominador.
    """
    carimbados = set()
    for h in _HORIZONTES_COM_ANCORA:
        for i, item in enumerate(par.get(h) or []):
            if not isinstance(item, dict):
                continue
            for j, ancora in enumerate(item.get("ancoras") or []):
                caminho = (ancora or {}).get("path")
                if caminho and resolve(caminho):
                    carimbados.add(f".{h}[{i}].ancoras[{j}].valor_renderizado")
    return carimbados


def _x4_cego(n_ocorrencias: int) -> None:
    print("  instrumento CEGO: manifesto/drill nao carregaram — nada classificado")
    veredito(
        "X4",
        0,
        n_ocorrencias,
        0,
        n_falsificavel=0,
        nota="sem o resolvedor do estampador nao ha como separar carimbado de autoral",
    )


def x4(ws: str, run: str, parecer_path: str, vm_path: str) -> None:
    """Literal monetario AUTORAL do modelo ancorado no E5 do mesmo run.

    `LC9-04`: a versao anterior media os 10 literais do parecer e publicava
    `FECHA ✅ n=10/10`. Nove deles vivem em `ancoras[].valor_renderizado`, que
    `stamp_ancora_values` preenche copiando `path -> valor` do MESMO payload que
    este check rele — orfao impossivel por construcao. A superficie autoral era
    **n=1**, e o verde media o carimbo do backend contra ele mesmo.
    """
    par, vm = json.load(open(parecer_path)), json.load(open(vm_path))
    universo = {c for _p, v in _walk_numbers(vm) if (c := _cents(v)) is not None}
    ocorrencias = _walk_literais(par)
    print("## X4 — literais monetarios AUTORAIS do parecer ancorados no E5 do mesmo run")
    print(f"universo de cents no view-model: {len(universo)}")
    resolve = _resolvedor(vm)
    if resolve is None:
        _x4_cego(len(ocorrencias))
        return
    carimbados = _paths_carimbados(par, resolve)
    autorais = [(p, c) for p, c in ocorrencias if p not in carimbados]
    orfaos = [(p, c) for p, c in autorais if c not in universo]
    print(
        f"ocorrencias R$ no parecer: {len(ocorrencias)} · carimbadas pelo backend: "
        f"{len(ocorrencias) - len(autorais)} · AUTORAIS: {len(autorais)} · orfaos: {len(orfaos)}"
    )
    for caminho, _c in autorais:
        print(f"  autoral em `{caminho}`")
    for caminho, c in orfaos[:20]:
        print(f"  ORFAO cents={c} em `{caminho}`")
    veredito(
        "X4",
        len(ocorrencias),
        len(ocorrencias),
        len(orfaos),
        n_falsificavel=len(autorais),
        nota=(
            "so a prosa autoral pode reprovar; ancora com path que resolve e copia do "
            "proprio payload (ADR-296). Cobertura: `R$` explicito — prosa monetaria por "
            "extenso ('350 mil') fica fora e nao esta contada. "
            "(literal monetario NAO e copiado para o git — so a contagem)"
        ),
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
