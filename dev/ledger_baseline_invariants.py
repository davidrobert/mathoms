#!/usr/bin/env python3
"""Invariantes de SAÍDA do baldes patrimonial (LC06 · A42.l3) — a P0 nº 1 da rubrica.

A rubrica declarava o dedup patrimonial ([[ADR-271]]/[[ADR-246]]) coberto, mas o único
check que rodava era `investment_double_count` sobre o balde E4 `investimentos` — origem
E2, 18 posições. O eixo cross-year/cross-declarante vive em `investimentos_consolidados`
do E1.5c (49 entradas), que viaja **dentro** do balde `patrimonio` e nunca foi lido:
população e vetor diferentes, P0 nº 1 nunca exercitada em r1–r4.

Estes checks leem **só o payload publicado**. Reimportar os módulos de dedup seria
tautologia — o check passaria porque usa o mesmo código que deveria auditar.

Cada invariante declara a própria **partição de julgabilidade**: quantos itens ele
consegue julgar, e por que os demais ficam de fora. Invariante que não discrimina nada
neste corpus sai `não-verificável` com o motivo, nunca `conservado` — um `P ∨ ¬P` que
sempre passa é o modo de falha que a [[A42.l16]] mediu no CV18.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.golden_diff import to_cents
from dev.ledger_verdicts import CONSERVADO, NAO_VERIFICAVEL, PERDA_SILENCIOSA

_LISTAS = ("investimentos_consolidados", "imoveis_consolidados", "veiculos_consolidados")


@dataclass(frozen=True)
class InvariantResult:
    """Veredito de um invariante + a partição que o torna (ou não) julgável."""

    id: str
    verdict: str
    detail: str
    julgaveis: int = 0
    total: int = 0

    @property
    def linha(self) -> str:
        return (
            f"- `{self.id}`: **{self.verdict}** — {self.detail} "
            f"(julgável em {self.julgaveis}/{self.total} itens)"
        )


def _ok(ident: str, detail: str, part: tuple[int, int]) -> InvariantResult:
    return InvariantResult(ident, CONSERVADO, detail, *part)


def _p0(ident: str, detail: str, part: tuple[int, int]) -> InvariantResult:
    return InvariantResult(ident, PERDA_SILENCIOSA, detail, *part)


def _nv(ident: str, detail: str, part: tuple[int, int] = (0, 0)) -> InvariantResult:
    """Fábrica de `não-verificável`. Existe para que a partição (julgáveis, total) viaje
    SEMPRE junto do veredito — número sem denominador é o que deixou a P0 nº 1 parecer
    coberta."""
    return InvariantResult(ident, NAO_VERIFICAVEL, detail, *part)


def _itens(baseline: dict) -> list[dict]:
    return [i for lista in _LISTAS for i in (baseline.get(lista) or []) if isinstance(i, dict)]


def _anos(item: dict) -> dict:
    valores = item.get("valores_31_12")
    return valores if isinstance(valores, dict) else {}


def _soma_no_ano(itens: list[dict], ano: str) -> int:
    return sum(to_cents(_anos(i).get(ano) or 0) for i in itens)


def _soma_todos_anos(itens: list[dict]) -> int:
    return sum(to_cents(v or 0) for i in itens for v in _anos(i).values())


def _total_bens(baseline: dict, ano: str) -> int | None:
    bloco = (baseline.get("patrimonio_por_ano") or {}).get(ano)
    if not isinstance(bloco, dict) or bloco.get("total_bens") is None:
        return None
    return to_cents(bloco["total_bens"])


def pat_1(baseline: dict) -> InvariantResult:
    """PAT-1 — a contribuição de um item é ``valores_31_12[max(ano)]``, nunca Σ anos."""
    itens = _itens(baseline)
    anos = sorted({a for i in itens for a in _anos(i)})
    multi = [i for i in itens if len(_anos(i)) > 1]
    if len(anos) < 2 or not multi:
        return _nv(
            "PAT-1",
            "corpus com <2 anos ou nenhum item multi-ano: max-ano e Σ-anos COINCIDEM, "
            "e o invariante não discriminaria nada",
            (0, len(itens)),
        )
    return _pat_1_verdict(baseline, itens, anos[-1], len(multi))


def _pat_1_verdict(baseline: dict, itens: list[dict], ano: str, julgaveis: int) -> InvariantResult:
    total = _total_bens(baseline, ano)
    no_ano, todos = _soma_no_ano(itens, ano), _soma_todos_anos(itens)
    part = (julgaveis, len(itens))
    if total is None:
        return _nv("PAT-1", f"sem `patrimonio_por_ano[{ano}].total_bens`", part)
    if total == no_ano:
        return _ok("PAT-1", f"total_bens[{ano}] fecha com Σ max-ano ({no_ano} cents)", part)
    if total == todos:
        somou = f"total_bens[{ano}] == Σ de TODOS os anos ({todos} cents) e não Σ max-ano "
        return _p0("PAT-1", somou + f"({no_ano}) — o agregado somou os anos", part)
    fora = f"total_bens[{ano}]={total} não fecha com Σ max-ano ({no_ano}) nem com Σ todos "
    return _nv("PAT-1", fora + f"os anos ({todos}) — o total inclui categorias de fora", part)


def _id_unico(itens: list[dict], campo: str, ident: str) -> InvariantResult:
    """Identidade declarada não pode aparecer em duas linhas vivas ([[ADR-271]])."""
    com_id = [i for i in itens if i.get(campo)]
    vistos: dict[str, int] = {}
    for i in com_id:
        vistos[i[campo]] = vistos.get(i[campo], 0) + 1
    repetidos = sorted(k for k, n in vistos.items() if n > 1)
    part = (len(com_id), len(itens))
    if not com_id:
        return _nv(ident, f"nenhum item declara `{campo}`", (0, len(itens)))
    if repetidos:
        return _p0(ident, f"{len(repetidos)} `{campo}` em 2+ linhas vivas (dupla-contagem)", part)
    return _ok(ident, f"{len(vistos)} `{campo}` distintos, nenhum repetido", part)


def _codeclarado_e_uniao(itens: list[dict], campo: str, ident: str) -> InvariantResult:
    """Item co-declarado é UMA linha com `proprietarios` união, não 2 linhas (ADR-246)."""
    com_id = [i for i in itens if i.get(campo)]
    por_id: dict[str, set] = {}
    for i in com_id:
        por_id.setdefault(i[campo], set()).add(str(i.get("proprietario") or ""))
    partidos = sorted(k for k, donos in por_id.items() if len(donos) > 1)
    part = (len(com_id), len(itens))
    if not com_id:
        return _nv(ident, f"nenhum item declara `{campo}`", (0, len(itens)))
    if partidos:
        return _p0(
            ident,
            f"{len(partidos)} identidade(s) partida(s) por declarante — co-declaração "
            f"virou 2 linhas em vez de união em `proprietarios` (ADR-246)",
            part,
        )
    return _ok(ident, "nenhuma identidade partida por declarante", part)


def mem_1(baseline: dict) -> InvariantResult:
    """MEM-1 — todo `proprietario` citado por um item existe em `membros`."""
    itens = _itens(baseline)
    membros = {str(m.get("nome") or m) for m in (baseline.get("membros") or [])}
    citados = {str(i.get("proprietario")) for i in itens if i.get("proprietario")}
    part = (len(citados), len(itens))
    if not membros or not citados:
        return _nv("MEM-1", "sem `membros` ou nenhum item cita proprietário", (0, len(itens)))
    orfaos = sorted(citados - membros)
    if orfaos:
        return _p0("MEM-1", f"{len(orfaos)} proprietário(s) sem entrada em `membros`", part)
    return _ok("MEM-1", f"{len(citados)} proprietário(s) resolvem em `membros`", part)


def baseline_invariants(baseline) -> list[InvariantResult]:
    """Os 6 invariantes da P0 nº 1, sobre o payload PUBLICADO do balde `patrimonio`."""
    if not isinstance(baseline, dict):
        return [_nv("PAT-1", "balde `patrimonio` ausente/ilegível")]
    inv = baseline.get("investimentos_consolidados") or []
    imo = baseline.get("imoveis_consolidados") or []
    return [
        pat_1(baseline),
        _id_unico(inv, "investment_id", "INV-1"),
        _codeclarado_e_uniao(inv, "investment_id", "INV-2"),
        _id_unico(imo, "property_id", "IMO-1"),
        _codeclarado_e_uniao(imo, "property_id", "IMO-2"),
        mem_1(baseline),
    ]


_TITULO = "## P0 nº 1 — invariantes patrimoniais (saída, [[ADR-271]]/[[ADR-246]])"


def fmt_baseline_invariants(resultados: list[InvariantResult]) -> list[str]:
    """Bloco PII-safe: só ids de invariante, contagens e vereditos."""
    julgados = sum(1 for r in resultados if r.verdict != NAO_VERIFICAVEL)
    return [
        _TITULO,
        "",
        f"- exercitados: **{julgados}/{len(resultados)}** (o resto declara por que não julga)",
        *[r.linha for r in resultados],
    ]
