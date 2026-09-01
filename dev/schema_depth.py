#!/usr/bin/env python3
"""Grão de um contrato JSON-Schema: em que profundidade ele restringe ([[A42.l26]]).

`0 erros` é veredito sobre o que o contrato **olha**. Um schema com
`additionalProperties: false` só na raiz aceita item vazio, campo não previsto e
valor fora de tipo dentro de cada item da coleção — e devolve `0 erros` para os
três. Medir o fecho separa "não há drift" de "não há onde haver drift", que é a
classe de falso-verde da [[A42.l24]].

A unidade é o **nó-objeto** do schema: todo ponto onde um `object` é descrito.
Cada nó é `fechado` quando declara `additionalProperties: false` — a única
construção que faz o contrato detectar chave nova ([[ADR-432]] D4).

`$ref` entre arquivos é seguido (com guarda de ciclo): sem isso, um backstop
`anyOf` de `$ref` — a forma que a [[ADR-427]] D4 instalou no `e4_unified` —
mediria 1 nó aberto e esconderia os contratos reais que ele delega.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

DIR_SCHEMAS = Path(__file__).resolve().parent.parent / "config" / "schemas"

_COMBINADORES = ("allOf", "anyOf", "oneOf", "then", "else")


@dataclass(frozen=True)
class NoDeContrato:
    """Um ponto do schema que descreve um `object`."""

    path: str
    fechado: bool
    tem_required: bool
    terminal_de_colecao: bool

    @property
    def profundidade(self) -> int:
        """Quantos degraus abaixo da raiz — `$` é 0."""
        return self.path.count(".") + self.path.count("[]") + self.path.count("/")


@dataclass(frozen=True)
class Grao:
    """Perfil de fecho de um contrato — o que o veredito publica."""

    nos: tuple[NoDeContrato, ...]

    @property
    def total(self) -> int:
        return len(self.nos)

    @property
    def fechados(self) -> int:
        return sum(1 for n in self.nos if n.fechado)

    @property
    def terminais(self) -> tuple[NoDeContrato, ...]:
        """Nós terminais de coleção — item de `array`, valor de `additionalProperties`/`patternProperties`.

        É onde o item mora, e é o denominador certo. Contar todo nó-objeto
        inflaria com mapas de chave livre que são livres **por desenho** (o
        `dados: {categoria → array}` do `e4_cashflow`), e o número deixaria de
        discriminar.
        """
        return tuple(n for n in self.nos if n.terminal_de_colecao)

    @property
    def sem_grao(self) -> tuple[str, ...]:
        """Terminais sem `required` — onde `{}` atravessa e `0 erros` não fala do item."""
        return tuple(n.path for n in self.terminais if not n.tem_required)

    @property
    def abertos(self) -> tuple[str, ...]:
        """Terminais sem fecho — publicado, não gateado (ver docstring do módulo)."""
        return tuple(n.path for n in self.terminais if not n.fechado)

    @property
    def declarado(self) -> bool:
        """Todo terminal de coleção exige ao menos uma chave.

        Schema sem terminal é `True` por vacuidade **e isso é correto**: não há
        item por descrever, então não há grão por medir. Penalizá-lo trocaria
        falso-verde por falso-vermelho — é o motivo de o predicado ser `required`
        no terminal e não `additionalProperties` em todo nó.
        """
        return not self.sem_grao

    def resumo(self) -> str:
        n = len(self.terminais)
        com_required = n - len(self.sem_grao)
        return f"grão {com_required}/{n} required · {n - len(self.abertos)}/{n} fechados"


def _carregar(nome: str) -> Optional[dict]:
    caminho = DIR_SCHEMAS / nome
    if not caminho.exists():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


def _tipos(node: dict) -> set[str]:
    t = node.get("type")
    return {t} if isinstance(t, str) else set(t or ())


def _filhos_nomeados(node: dict, path: str) -> Iterable[tuple[Any, str]]:
    for chave, sub in (node.get("properties") or {}).items():
        yield sub, f"{path}.{chave}"


def _filhos_de_mapa(node: dict, path: str) -> Iterable[tuple[Any, str]]:
    """Valores de chave livre — o item de um mapa, tão terminal quanto o de um array."""
    ap = node.get("additionalProperties")
    if isinstance(ap, dict):
        yield ap, f"{path}.*"
    for padrao, sub in (node.get("patternProperties") or {}).items():
        yield sub, f"{path}.<{padrao}>"


def _percorrer(
    node: Any, path: str, vistos: set[str], acc: list[NoDeContrato], terminal: bool = False
) -> None:
    if not isinstance(node, dict):
        return
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.endswith(".schema.json"):
        # Guarda de ciclo por (arquivo, path): `review_reason` é referenciado de
        # vários pontos e sem isto o percurso não termina.
        marca = f"{ref}@{path}"
        if marca not in vistos:
            vistos.add(marca)
            alvo = _carregar(ref)
            if alvo is not None:
                _percorrer(alvo, path, vistos, acc, terminal)
    tipos = _tipos(node)
    if "object" in tipos or "properties" in node:
        acc.append(
            NoDeContrato(
                path=path,
                fechado=node.get("additionalProperties") is False,
                tem_required=bool(node.get("required")),
                terminal_de_colecao=terminal,
            )
        )
        for sub, sub_path in _filhos_nomeados(node, path):
            _percorrer(sub, sub_path, vistos, acc)
        for sub, sub_path in _filhos_de_mapa(node, path):
            _percorrer(sub, sub_path, vistos, acc, terminal=True)
    if "array" in tipos or "items" in node:
        itens = node.get("items")
        if isinstance(itens, dict):
            _percorrer(itens, f"{path}[]", vistos, acc, terminal=True)
    for comb in _COMBINADORES:
        sub = node.get(comb)
        if isinstance(sub, dict):
            _percorrer(sub, f"{path}/{comb}", vistos, acc, terminal)
        elif isinstance(sub, list):
            for i, ramo in enumerate(sub):
                _percorrer(ramo, f"{path}/{comb}[{i}]", vistos, acc, terminal)


def medir_grao(schema: dict) -> Grao:
    """Perfil de fecho do schema, seguindo `$ref` entre arquivos."""
    acc: list[NoDeContrato] = []
    _percorrer(schema, "$", set(), acc)
    # Dedup por path: `allOf`/`anyOf` podem descrever o MESMO ponto duas vezes, e
    # contar duas vezes inflaria o denominador sem acrescentar profundidade.
    por_path: dict[str, NoDeContrato] = {}
    for no in acc:
        anterior = por_path.get(no.path)
        if anterior is None or (no.tem_required and not anterior.tem_required):
            por_path[no.path] = no
    return Grao(nos=tuple(por_path[p] for p in sorted(por_path)))


def medir_grao_por_nome(nome: str) -> Optional[Grao]:
    schema = _carregar(nome)
    return None if schema is None else medir_grao(schema)


def main() -> int:
    for caminho in sorted(DIR_SCHEMAS.glob("*.schema.json")):
        g = medir_grao(json.loads(caminho.read_text(encoding="utf-8")))
        marca = "grão declarado" if g.declarado else f"SEM GRÃO: {', '.join(g.sem_grao)}"
        print(f"{caminho.name:<44} {g.resumo():<34}  {marca}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
