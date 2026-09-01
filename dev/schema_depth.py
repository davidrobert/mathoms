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
from functools import lru_cache
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

    # Denominador certo: é onde o item mora. Contar todo nó-objeto inflaria com
    # mapa de chave livre que é livre POR DESENHO (o `dados: {categoria → array}`
    # do `e4_cashflow`), e o número deixaria de discriminar.
    @property
    def terminais(self) -> tuple[NoDeContrato, ...]:
        """Item de `array` ou valor de `additionalProperties`/`patternProperties`."""
        return tuple(n for n in self.nos if n.terminal_de_colecao)

    @property
    def sem_grao(self) -> tuple[str, ...]:
        """Terminais sem `required` — onde `{}` atravessa e `0 erros` não fala do item."""
        return tuple(n.path for n in self.terminais if not n.tem_required)

    @property
    def abertos(self) -> tuple[str, ...]:
        """Terminais sem fecho — publicado, não gateado (ver docstring do módulo)."""
        return tuple(n.path for n in self.terminais if not n.fechado)

    # Schema sem terminal é `True` por VACUIDADE, e isso é correto: não há item
    # por descrever, logo não há grão por medir. Penalizá-lo trocaria falso-verde
    # por falso-vermelho.
    @property
    def declarado(self) -> bool:
        """Todo terminal de coleção exige ao menos uma chave."""
        return not self.sem_grao

    def resumo(self) -> str:
        n = len(self.terminais)
        com_required = n - len(self.sem_grao)
        return f"grão {com_required}/{n} required · {n - len(self.abertos)}/{n} fechados"


@lru_cache(maxsize=None)
def _carregar(nome: str) -> Optional[dict]:
    # Ferramenta de linha de comando, fora do alcance da [[ADR-111]] (que veda
    # cache em `backend/app` e `pipeline`). Sem isto, medir o corpus relê os 36
    # schemas do disco uma vez por nó de cada payload.
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
    _seguir_ref(node, path, vistos, acc, terminal)
    tipos = _tipos(node)
    if "object" in tipos or "properties" in node:
        _percorrer_objeto(node, path, vistos, acc, terminal)
    itens = node.get("items")
    if ("array" in tipos or "items" in node) and isinstance(itens, dict):
        _percorrer(itens, f"{path}[]", vistos, acc, terminal=True)
    _percorrer_combinadores(node, path, vistos, acc, terminal)


def _seguir_ref(node: dict, path: str, vistos: set, acc: list, terminal: bool) -> None:
    # Guarda de ciclo por (arquivo, path): `review_reason` é referenciado de
    # vários pontos e sem isto o percurso não termina.
    ref = node.get("$ref")
    if not (isinstance(ref, str) and ref.endswith(".schema.json")):
        return
    marca = f"{ref}@{path}"
    if marca in vistos:
        return
    vistos.add(marca)
    alvo = _carregar(ref)
    if alvo is not None:
        _percorrer(alvo, path, vistos, acc, terminal)


def _percorrer_objeto(node: dict, path: str, vistos: set, acc: list, terminal: bool) -> None:
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


def _percorrer_combinadores(node: dict, path: str, vistos: set, acc: list, terminal: bool) -> None:
    for sub, sub_path in _sub_combinadores(node, path):
        _percorrer(sub, sub_path, vistos, acc, terminal)


def _sub_combinadores(node: dict, path: str) -> Iterable[tuple[dict, str]]:
    """`allOf`/`anyOf`/`oneOf`/`then`/`else`, achatando a forma-lista e a forma-dict."""
    for comb in _COMBINADORES:
        sub = node.get(comb)
        if isinstance(sub, dict):
            yield sub, f"{path}/{comb}"
        for i, ramo in enumerate(sub if isinstance(sub, list) else ()):
            yield ramo, f"{path}/{comb}[{i}]"


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


# ===========================================================================
# Cobertura por profundidade — a relação schema↔payload, medida no corpus
# ===========================================================================
#
# O fecho e o `required` são propriedades do schema **isolado**: nada no corpus
# pode falsificá-los, e o caminho barato para o verde é fechar sem declarar —
# que sob `strict` aborta o write de todo payload real. Cobertura é a relação
# `emitidas ⊆ declaradas` **por nó**, e é o mesmo predicado da [[ADR-432]] D5 um
# nível abaixo, com o corpus como árbitro.
#
# Só a direção `emitida ⊄ declarada` veta. A direção fantasma (`declarada ⊄
# emitível`) é reportada e nunca veta: vetá-la quebraria a D1 da 432, que declara
# `membros` por **alcance de código**, com 0 ocorrências no corpus.


# `{categoria → lançamentos}` e `patrimonio_por_ano` modelam dado NA CHAVE;
# diferenciar chave contra `properties` ali produz falso-vermelho em massa.
def _mapa_de_chave_livre(node: dict) -> bool:
    """Dicionário chave-dado — a cobertura se avalia no valor, nunca nas chaves."""
    if node.get("properties"):
        return False
    return isinstance(node.get("additionalProperties"), dict) or bool(node.get("patternProperties"))


# Memo por chamada de `medir_cobertura`: o nó é dict (não-hasheável), e dentro de
# uma chamada os objetos ficam vivos, então `id()` é estável. Cache global por
# `id()` seria armadilha — o id se recicla depois do GC.
_MEMO_RAMOS: dict = {}


def _ramos(node: dict) -> list[dict]:
    """O nó mais os ramos de combinador e `$ref`, achatados para união de `properties`."""
    memo = _MEMO_RAMOS.get(id(node))
    if memo is not None:
        return memo
    saida = [node, *_ramos_do_ref(node)]
    for comb in _COMBINADORES:
        saida.extend(_ramos_do_combinador(node.get(comb)))
    _MEMO_RAMOS[id(node)] = saida
    return saida


def _ramos_do_ref(node: dict) -> list[dict]:
    ref = node.get("$ref")
    if not (isinstance(ref, str) and ref.endswith(".schema.json")):
        return []
    alvo = _carregar(ref)
    return _ramos(alvo) if isinstance(alvo, dict) else []


def _ramos_do_combinador(sub: Any) -> list[dict]:
    if isinstance(sub, dict):
        return _ramos(sub)
    if isinstance(sub, list):
        return [r for ramo in sub if isinstance(ramo, dict) for r in _ramos(ramo)]
    return []


# União, não interseção: sob `anyOf` basta UM ramo declarar a chave para o payload
# validar, e interseção fabricaria defeito onde o validador não vê nenhum.
def _declaradas_no_no(node: dict) -> set[str]:
    """União das `properties` do nó e de todo ramo alcançável."""
    return {k for ramo in _ramos(node) for k in (ramo.get("properties") or {})}


# Conta como DEFEITO, não como ausência: tratá-lo como ausência premiaria deletar
# a declaração — apagar `properties` seria o caminho barato para o verde.
def _indeclarado(node: dict) -> bool:
    """`{"type": "object"}` sem `properties` nem mapa — profundidade não medida."""
    return not any(
        ramo.get("properties") or ramo.get("additionalProperties") or ramo.get("patternProperties")
        for ramo in _ramos(node)
    )


def _sub_de_chave(node: dict, chave: str) -> Optional[dict]:
    for ramo in _ramos(node):
        sub = (ramo.get("properties") or {}).get(chave)
        if isinstance(sub, dict):
            return sub
    return None


def _valor_de_mapa(node: dict) -> Optional[dict]:
    for ramo in _ramos(node):
        ap = ramo.get("additionalProperties")
        if isinstance(ap, dict):
            return ap
        por_padrao = [
            v for v in (ramo.get("patternProperties") or {}).values() if isinstance(v, dict)
        ]
        if por_padrao:
            return por_padrao[0]
    return None


def _itens_de(node: dict) -> Optional[dict]:
    for ramo in _ramos(node):
        itens = ramo.get("items")
        if isinstance(itens, dict):
            return itens
    return None


# A distinção entre os dois campos é de SEGURANÇA, não de estética:
#
# - `chaves_fora`: o nó DECLARA `properties` e o payload trouxe chave além delas.
#   Nome de campo é metadado — a [[ADR-284]] já o publica na telemetria de drift —,
#   então listar é seguro, e é o que torna o número acionável.
# - `nos_indeclarados`: o nó é `{"type": "object"}` sem `properties` nem mapa. Ali
#   as chaves do payload SÃO DADO (mês, membro, categoria), e enumerá-las jogaria
#   conteúdo financeiro no stdout — só o path e a contagem saem.
@dataclass
class Cobertura:
    """Nós em que o payload emitiu além do que o contrato declara."""

    chaves_fora: dict[str, set[str]]
    nos_indeclarados: dict[str, int]

    @property
    def completa(self) -> bool:
        return not self.chaves_fora and not self.nos_indeclarados

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.chaves_fora) | set(self.nos_indeclarados)))


def _cobrir(node: Any, valor: Any, path: str, cob: Cobertura) -> None:
    if not isinstance(node, dict):
        return
    if isinstance(valor, list):
        _cobrir_lista(node, valor, path, cob)
        return
    if not isinstance(valor, dict):
        return
    if _mapa_de_chave_livre(node):
        sub = _valor_de_mapa(node)
        for v in valor.values() if sub is not None else ():
            _cobrir(sub, v, f"{path}.*", cob)
        return
    if _indeclarado(node):
        if valor:
            cob.nos_indeclarados[path] = cob.nos_indeclarados.get(path, 0) + 1
        return
    _cobrir_registro(node, valor, path, cob)


def _cobrir_lista(node: dict, valor: list, path: str, cob: "Cobertura") -> None:
    itens = _itens_de(node)
    alvo = f"{path}[]"
    if itens is None:
        # `{"type": "array"}` sem `items`: o contrato não descreve o elemento.
        indeclarados = sum(1 for e in valor if isinstance(e, dict) and e)
        if indeclarados:
            cob.nos_indeclarados[alvo] = cob.nos_indeclarados.get(alvo, 0) + indeclarados
        return
    for elemento in valor:
        _cobrir(itens, elemento, alvo, cob)


def _cobrir_registro(node: dict, valor: dict, path: str, cob: "Cobertura") -> None:
    nao_declaradas = set(valor) - _declaradas_no_no(node)
    if nao_declaradas:
        cob.chaves_fora.setdefault(path, set()).update(nao_declaradas)
    for chave, v in valor.items():
        sub = _sub_de_chave(node, chave)
        if sub is not None:
            _cobrir(sub, v, f"{path}.{chave}", cob)


def medir_cobertura(schema: dict, payload: Any) -> Cobertura:
    """Nós em que o payload emitiu além do que o contrato declara."""
    cob = Cobertura(chaves_fora={}, nos_indeclarados={})
    _MEMO_RAMOS.clear()
    try:
        _cobrir(schema, payload, "$", cob)
    finally:
        _MEMO_RAMOS.clear()
    return cob
