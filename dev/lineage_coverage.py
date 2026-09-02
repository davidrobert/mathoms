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
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
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

#: Origem da fixture dogfood determinística — o chão medido que o CI reproduz sozinho.
ORIGEM_FIXTURE = "fixture"

#: Origem do contrato declarado. É o **piso**: raiz com folha monetária no schema conta como
#: dívida mesmo que nenhum workspace medido a emita hoje. Fecha a cegueira que o roster
#: sozinho tem — ele só enxerga workspace já medido, e `proventos_por_ativo` tem produtor,
#: consumidor e teste e2e vivos com zero informe `proventos_acoes` **neste** workspace
#: (A27.l3 §closeout). Piso declarado e chão medido têm buracos diferentes: o schema não
#: alcança `irpf_kpis`, o roster não alcança workspace não medido. O universo é a união.
ORIGEM_SCHEMA = "schema"

E5_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "schemas" / "e5_analysis.schema.json"
)


def _children(obj: Any, path: str) -> list[tuple[str, Any]]:
    if isinstance(obj, dict):
        return [(f"{path}.{k}" if path else k, v) for k, v in obj.items()]
    if isinstance(obj, list):
        return [(f"{path}[{i}]", v) for i, v in enumerate(obj)]
    return []


#: Dinheiro serializado como string decimal — o E5 publica parte do dinheiro assim
#: (`irpf_kpis.ir_pago_total_brl`, `protecao_patrimonial.premio_total_anual_brl`, este último
#: com o mesmo `pattern` declarado em `protecao_patrimonial.schema.json`). Exigir `int|float`
#: tirava as duas raízes inteiras do denominador: era o mesmo viés otimista que este módulo
#: existe para matar, deslocado de **origem** para **tipo** (A27.l3 §D1).
MONEY_STR = re.compile(r"^-?\d+(\.\d{1,2})?$")


def _is_monetary_leaf(obj: Any, path: str) -> bool:
    if not is_monetary(path):
        return False
    if isinstance(obj, bool):
        return False
    if isinstance(obj, (int, float)):
        return True
    return isinstance(obj, str) and bool(MONEY_STR.match(obj))


def monetary_leaf_paths(payload: Any, path: str = "") -> set[str]:
    """Dot-paths das folhas monetárias do payload (recursivo em dict e list)."""
    children = _children(payload, path)
    if not children:
        return {path} if _is_monetary_leaf(payload, path) else set()
    found: set[str] = set()
    for child_path, value in children:
        found |= monetary_leaf_paths(value, child_path)
    return found


def _deref(node: Any, schema: dict, depth: int = 0) -> Any:
    """Resolve `$ref` interno. Sem isto o walker para na porta de `$defs` e reporta ausência
    que é cegueira dele: `goals`, `reserva_emergencia` e `consumo_consciente` são `$ref` e
    declaram `number` lá dentro (A27.l3 §closeout — o achado que o walker fabricou)."""
    while isinstance(node, dict) and "$ref" in node and depth < 20:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            return node
        cur: Any = schema
        for part in ref[2:].split("/"):
            cur = cur.get(part, {}) if isinstance(cur, dict) else {}
        node, depth = cur, depth + 1
    return node


def _declared_types(node: dict) -> set[str]:
    t = node.get("type")
    if isinstance(t, str):
        return {t}
    return set(t) if isinstance(t, list) else set()


def _declares_money(node: dict) -> bool:
    types = _declared_types(node)
    if types & {"number", "integer"}:
        return True
    return "string" in types and bool(node.get("pattern"))


def _schema_monetary_paths(node: Any, schema: dict, path: str, depth: int = 0) -> set[str]:
    node = _deref(node, schema)
    if not isinstance(node, dict) or depth > 25:
        return set()
    found: set[str] = set()
    for combinator in ("allOf", "anyOf", "oneOf"):
        for sub in node.get(combinator, []):
            found |= _schema_monetary_paths(sub, schema, path, depth + 1)
    if _declares_money(node) and is_monetary(path):
        found.add(path)
    for key, sub in (node.get("properties") or {}).items():
        found |= _schema_monetary_paths(sub, schema, f"{path}.{key}" if path else key, depth + 1)
    if isinstance(node.get("items"), dict):
        found |= _schema_monetary_paths(node["items"], schema, f"{path}[]", depth + 1)
    extra = node.get("additionalProperties")
    if isinstance(extra, dict):
        found |= _schema_monetary_paths(extra, schema, f"{path}.*", depth + 1)
    return found


def schema_monetary_roots(path: Path = E5_SCHEMA_PATH) -> frozenset[str]:
    """Piso declarado: raízes do contrato E5 com ≥1 folha monetária."""
    schema = json.loads(path.read_text(encoding="utf-8"))
    leaves = _schema_monetary_paths(schema, schema, "")
    return frozenset({_root_of(p) for p in leaves} - {LINEAGE_BLOCK})


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


def _hoje() -> str:
    return date.today().isoformat()


class RosterEncolheria(ValueError):
    """A observação retiraria raiz do universo — encolher é decisão, não efeito colateral."""


def _merge(
    mapa: Mapping[str, tuple[str, ...]],
    roots: frozenset[str],
    origem: str,
    *,
    permitir_encolher: bool,
) -> dict[str, tuple[str, ...]]:
    """Acrescenta ``origem`` às raízes medidas; só a retira sob autorização explícita.

    Retirar por default era o vazamento medido em A27.l3 §D2: re-observar o **mesmo rótulo**
    com um payload mais pobre encolhia o universo e **subia** a cobertura, com a suíte verde
    nos dois sentidos (17→18→17, 29,4%→27,8%→29,4%). Encolhimento parcial passava mudo, e a
    direção otimista era justamente a que passava.
    """
    perdidas = sorted(r for r, origens in mapa.items() if origem in origens and r not in roots)
    if perdidas and not permitir_encolher:
        raise RosterEncolheria(
            f"a observação de `{origem}` retiraria {perdidas} do universo — o denominador "
            f"cairia de {len(mapa)} para {len(mapa) - len(perdidas)} e a cobertura SUBIRIA. "
            "Se a raiz deixou mesmo de publicar dinheiro, repita com `--permitir-encolher` "
            "(CLI) ou `MATHOMS_UPDATE_LINEAGE_COVERAGE=encolher` (rebaseline)."
        )
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
    #: Data da última observação por origem. O roster envelhece **sempre** para o lado
    #: otimista — raiz nova só-produção não entra sozinha —, e sem data ninguém sabe quão
    #: velho é o chão medido (A27.l3 §D3).
    observado_em: Mapping[str, str] = field(default_factory=dict)

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

    def observing(
        self, origem: str, coverage: LineageCoverage, *, permitir_encolher: bool = False
    ) -> Roster:
        """Roster com a observação de ``origem`` incorporada. Não encolhe sem autorização."""
        return Roster(
            universo=_merge(
                self.universo, coverage.monetary_roots, origem, permitir_encolher=permitir_encolher
            ),
            cobertos=_merge(
                self.cobertos, coverage.covered_roots, origem, permitir_encolher=permitir_encolher
            ),
            observado_em={**self.observado_em, origem: _hoje()},
        )

    def with_schema(self, *, permitir_encolher: bool = False) -> Roster:
        """Incorpora o piso declarado pelo contrato E5 como a origem ``schema``."""
        roots = schema_monetary_roots()
        return Roster(
            universo=_merge(
                self.universo, roots, ORIGEM_SCHEMA, permitir_encolher=permitir_encolher
            ),
            cobertos=self.cobertos,
            observado_em={**self.observado_em, ORIGEM_SCHEMA: _hoje()},
        )

    @classmethod
    def load(cls, path: Path = ROSTER_PATH) -> Roster:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            universo={r: tuple(o) for r, o in raw["universo"].items()},
            cobertos={r: tuple(o) for r, o in raw["cobertos"].items()},
            observado_em=dict(raw.get("observado_em") or {}),
        )

    def dump(self, path: Path = ROSTER_PATH) -> None:
        payload = {
            "_doc": (
                "Roster de cobertura de lineage (ADR-281 · A27.l3). Cada raiz monetária guarda "
                "as ORIGENS em que foi observada; o número publicado é sobre o universo "
                "inteiro, nunca sobre uma origem só. `schema` é o piso declarado pelo contrato "
                "E5, `fixture` o chão que o CI reproduz, `producao:<run8>` uma observação "
                "datada. O universo nunca encolhe sem autorização explícita. Rebaseline de "
                "fixture+schema: MATHOMS_UPDATE_LINEAGE_COVERAGE=1 pytest "
                "tests/test_lineage_coverage.py. Observação de produção: python3 "
                "dev/lineage_coverage.py <payload.json> --origem producao:<run8> --update"
            ),
            "cobertura_publicada": {
                "numerador": self.numerador,
                "denominador": self.denominador,
                "ratio_pct": round(self.ratio * 100, 1),
                "origens": list(self.origens),
            },
            "observado_em": dict(sorted(self.observado_em.items())),
            "universo": {r: list(o) for r, o in sorted(self.universo.items())},
            "cobertos": {r: list(o) for r, o in sorted(self.cobertos.items())},
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _report(origem: str, coverage: LineageCoverage, roster: Roster) -> list[str]:
    """Imprime as duas medidas lado a lado e devolve as raízes fora do roster."""
    fora = sorted(roster.outside(coverage.monetary_roots))
    print(f"payload  ({origem}): {coverage.format_summary()}")
    print(f"roster   publicado: {roster.format_summary()}")
    for rotulo, quando in sorted(roster.observado_em.items()):
        print(f"  observado em {quando} · {rotulo}")
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
    p.add_argument(
        "--permitir-encolher",
        action="store_true",
        help="autoriza a observação a RETIRAR raiz do universo (sobe a cobertura)",
    )
    return p


def _cli(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    coverage = measure_coverage(json.loads(args.payload.read_text(encoding="utf-8")))
    roster = Roster.load()
    fora = _report(args.origem, coverage, roster)
    if not args.update:
        return _verdict(fora)
    try:
        novo = roster.observing(
            args.origem, coverage, permitir_encolher=args.permitir_encolher
        ).with_schema(permitir_encolher=args.permitir_encolher)
    except RosterEncolheria as exc:
        print(f"Reprovado: {exc}", file=sys.stderr)
        return 1
    novo.dump()
    print(f"roster atualizado: {novo.format_summary()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
