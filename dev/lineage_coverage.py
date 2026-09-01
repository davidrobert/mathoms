#!/usr/bin/env python3
"""Cobertura do grafo de lineage (ADR-281 · A27.l2 · A27.l3): raízes monetárias do E5 com rastro ÷ raízes monetárias do E5.

O denominador sai de **payload medido**, nunca do ``lineage_registry``: derivá-lo do
registro devolve 100% por construção — o vício que esta medida existe para matar (raiz
nova no E5 sem entrada no registro não movia métrica nenhuma, nem o gate, nem a accuracy).
O discriminante de "raiz que deve ter rastro" é ``golden_diff.is_monetary``
(monetário-por-default, ADR-090). O que o qualifica é ser **independente do
``lineage_registry``** — é isso que mantém numerador e denominador independentes — e já ser
o classificador de dot-path que o substrato de golden usa (``golden_diff``, snapshot do
view-model), então reusá-lo não cria uma segunda noção de "monetário" para o mesmo payload.

Raiz em prosa/metadado (``alertas``, ``data_analise``, ``tarefas``) fica fora do denominador
porque não publica dinheiro. Medir contra as 38 raízes declaradas no schema
dava teto inalcançável, e KR que não pode chegar a 100% é KR que ninguém persegue.

**A27.l3 — o universo é um roster de origens, não o que a fixture emite.** A A27.l2 fixou o
denominador no payload da fixture dogfood (**14** raízes) e publicou aquilo como *a*
cobertura. O payload de produção emite **17** (medido em 40 artefatos E5): a fixture é
subconjunto **estrito** — não tem IRPF, imóvel locado nem PJ, então nunca emite
``previdencia_pgbl``, ``real_estate`` e ``tributario``. O viés era **otimista** e crescia
sozinho: raiz nova entrava na produção sem entrar no denominador. O roster
(``dev/snapshots/lineage_coverage_baseline.json``) guarda cada raiz **com as origens em que
foi observada**, e o número publicado é sobre ele — nunca sobre um lado só.

Limite declarado: o roster cobre o que já foi **medido**. Raiz que só apareça num workspace
ainda não medido fica de fora até alguém rodar ``--payload`` sobre aquele artefato — é para
isso que o CLI reprova por raiz-fora-do-roster (o sinal que a A27.l2 não tinha). O schema E5
foi medido como fonte de universo e **rejeitado**: declara monetário em 14 raízes que não
são superconjunto da produção (não declara ``tributario``, que a produção emite por
``additionalProperties: true``) e declara ``proventos_por_ativo``, que **nenhum** dos 40
artefatos emite — teto inalcançável de novo.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dev.golden_diff import is_monetary  # noqa: E402

# O bloco de rastro não entra no denominador: uma raiz não pode ser evidência da
# própria proveniência. Declarado aqui por princípio — hoje `_lineage` serializa
# valor como string e não cairia no predicado de qualquer forma.
LINEAGE_BLOCK = "_lineage"

ROSTER_PATH = (
    Path(__file__).resolve().parents[1] / "dev" / "snapshots" / "lineage_coverage_baseline.json"
)

#: Origem da fixture dogfood determinística — a única que o CI consegue medir sozinho.
ORIGEM_FIXTURE = "fixture"


def _children(obj: Any, path: str) -> list[tuple[str, Any]]:
    if isinstance(obj, dict):
        return [(f"{path}.{k}" if path else k, v) for k, v in obj.items()]
    if isinstance(obj, list):
        return [(f"{path}[{i}]", v) for i, v in enumerate(obj)]
    return []


def _is_monetary_leaf(obj: Any, path: str) -> bool:
    return isinstance(obj, (int, float)) and not isinstance(obj, bool) and is_monetary(path)


def monetary_leaf_paths(payload: Any, path: str = "") -> set[str]:
    """Dot-paths das folhas monetárias do payload (recursivo em dict e list)."""
    children = _children(payload, path)
    if not children:
        return {path} if _is_monetary_leaf(payload, path) else set()
    found: set[str] = set()
    for child_path, value in children:
        found |= monetary_leaf_paths(value, child_path)
    return found


def _root_of(path: str) -> str:
    return path.split(".", 1)[0].split("[", 1)[0]


def payload_monetary_roots(payload: dict) -> frozenset[str]:
    """Denominador: raízes de topo que publicam ≥1 folha monetária."""
    roots = {_root_of(p) for p in monetary_leaf_paths(payload)}
    return frozenset(roots - {LINEAGE_BLOCK})


def lineage_covered_roots(payload: dict) -> frozenset[str]:
    """Numerador: raízes com ≥1 nó declarado em ``_lineage.fields``."""
    fields = payload.get(LINEAGE_BLOCK, {}).get("fields", {})
    return frozenset(_root_of(f) for f in fields)


@dataclass(frozen=True)
class LineageCoverage:
    """Cobertura medida sobre **um** payload E5 concreto."""

    monetary_roots: frozenset[str]
    covered_roots: frozenset[str]

    @property
    def uncovered_roots(self) -> frozenset[str]:
        return self.monetary_roots - self.covered_roots

    @property
    def ratio(self) -> float:
        if not self.monetary_roots:
            return 0.0
        return len(self.monetary_roots & self.covered_roots) / len(self.monetary_roots)

    def format_summary(self) -> str:
        hit = len(self.monetary_roots & self.covered_roots)
        return f"{hit}/{len(self.monetary_roots)} raízes monetárias com rastro ({self.ratio:.1%})"


def measure_coverage(payload: dict) -> LineageCoverage:
    """Cobertura de lineage do payload E5 publicado."""
    return LineageCoverage(
        monetary_roots=payload_monetary_roots(payload),
        covered_roots=lineage_covered_roots(payload),
    )


def _merge(
    mapa: Mapping[str, tuple[str, ...]], roots: frozenset[str], origem: str
) -> dict[str, tuple[str, ...]]:
    """Acrescenta ``origem`` às raízes medidas e a **retira** das que não apareceram nela."""
    novo = {root: tuple(o for o in origens if o != origem) for root, origens in mapa.items()}
    for root in roots:
        novo[root] = tuple(sorted(set(novo.get(root, ())) | {origem}))
    return {root: origens for root, origens in sorted(novo.items()) if origens}


@dataclass(frozen=True)
class Roster:
    """Universo acumulado de raízes monetárias, cada uma com as origens em que foi observada.
    O denominador publicado é este universo, nunca o de uma origem só — a diferença entre "a
    cobertura do E5" e "a cobertura do que a fixture emite", que a A27.l2 conflacionou."""

    universo: Mapping[str, tuple[str, ...]]
    cobertos: Mapping[str, tuple[str, ...]]

    @property
    def roots(self) -> frozenset[str]:
        return frozenset(self.universo)

    @property
    def covered_roots(self) -> frozenset[str]:
        return frozenset(self.cobertos)

    @property
    def origens(self) -> tuple[str, ...]:
        todas = {o for origens in self.universo.values() for o in origens}
        return tuple(sorted(todas))

    def roots_de(self, origem: str) -> frozenset[str]:
        return frozenset(r for r, origens in self.universo.items() if origem in origens)

    def cobertos_de(self, origem: str) -> frozenset[str]:
        return frozenset(r for r, origens in self.cobertos.items() if origem in origens)

    def outside(self, measured_roots: frozenset[str]) -> frozenset[str]:
        """Raízes monetárias medidas que o roster não conhece — o sinal que a A27.l2 não tinha."""
        return measured_roots - self.roots

    @property
    def denominador(self) -> int:
        return len(self.roots)

    @property
    def numerador(self) -> int:
        return len(self.covered_roots & self.roots)

    @property
    def ratio(self) -> float:
        return self.numerador / self.denominador if self.denominador else 0.0

    def format_summary(self) -> str:
        return (
            f"{self.numerador}/{self.denominador} raízes monetárias com rastro "
            f"({self.ratio:.1%}) — universo: {', '.join(self.origens)}"
        )

    def observing(self, origem: str, coverage: LineageCoverage) -> Roster:
        """Roster com a observação de ``origem`` substituída pela medida recém-feita."""
        return Roster(
            universo=_merge(self.universo, coverage.monetary_roots, origem),
            cobertos=_merge(self.cobertos, coverage.covered_roots, origem),
        )

    @classmethod
    def load(cls, path: Path = ROSTER_PATH) -> Roster:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            universo={r: tuple(o) for r, o in raw["universo"].items()},
            cobertos={r: tuple(o) for r, o in raw["cobertos"].items()},
        )

    def dump(self, path: Path = ROSTER_PATH) -> None:
        payload = {
            "_doc": (
                "Roster de cobertura de lineage (ADR-281 · A27.l3). Cada raiz monetária "
                "guarda as ORIGENS em que foi observada; o número publicado é sobre o "
                "universo inteiro, nunca sobre uma origem só. Rebaseline da fixture: "
                "MATHOMS_UPDATE_LINEAGE_COVERAGE=1 pytest tests/test_lineage_coverage.py. "
                "Observação de produção: python3 dev/lineage_coverage.py <payload.json> "
                "--origem producao:<run8> --update"
            ),
            "cobertura_publicada": {
                "numerador": self.numerador,
                "denominador": self.denominador,
                "ratio_pct": round(self.ratio * 100, 1),
                "origens": list(self.origens),
            },
            "universo": {r: list(o) for r, o in sorted(self.universo.items())},
            "cobertos": {r: list(o) for r, o in sorted(self.cobertos.items())},
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _report(origem: str, coverage: LineageCoverage, roster: Roster) -> list[str]:
    """Imprime as duas medidas lado a lado e devolve as raízes fora do roster."""
    fora = sorted(roster.outside(coverage.monetary_roots))
    print(f"payload  ({origem}): {coverage.format_summary()}")
    print(f"roster   publicado: {roster.format_summary()}")
    if fora:
        print(f"raízes monetárias FORA do roster: {fora}")
    return fora


def _verdict(fora: list[str]) -> int:
    if not fora:
        return 0
    print(
        "Reprovado: o universo publicado não cobre o payload medido. Rode com `--update` "
        "para incorporar a observação e republicar o número.",
        file=sys.stderr,
    )
    return 1


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Mede a cobertura de lineage de um payload E5 contra o roster publicado."
    )
    p.add_argument("payload", type=Path, help="JSON do artefato `analise_financeira` decifrado")
    p.add_argument("--origem", required=True, help="rótulo da observação, ex.: `producao:40d1af2a`")
    p.add_argument("--update", action="store_true", help="grava a observação no roster")
    return p


def _cli(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    coverage = measure_coverage(json.loads(args.payload.read_text(encoding="utf-8")))
    roster = Roster.load()
    fora = _report(args.origem, coverage, roster)
    if not args.update:
        return _verdict(fora)
    novo = roster.observing(args.origem, coverage)
    novo.dump()
    print(f"roster atualizado: {novo.format_summary()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
