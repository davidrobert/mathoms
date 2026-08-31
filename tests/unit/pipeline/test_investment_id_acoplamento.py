"""Critério 4 da [[A42.l15]] — o catálogo de instituições não entra na derivação do `investment_id`."""

# Ancora a [[ADR-400]] na IDENTIDADE, e o alvo é a re-proposta, não o código de hoje.
#
# A ADR-400 §Decisão 1 tirou `instituicao` da entrada do classificador porque sua forma
# canônica é "propriedade de outro subsistema" — um renome lá reclassificava ativo aqui
# "sem diff, sem revisão e sem sinal". A extensão para a chave de identidade é a fortiori:
# identidade é superfície mais durável que classificação. A rota que a A42.l15 mediu e
# rejeitou (canonicalizar `instituicao` pelo catálogo) rende +4,0pp e VOLTA a ser proposta
# na próxima rodada com a mesma medição — é para ela que este gate existe.
#
# LIMITES DECLARADOS. O fecho é estático sobre a árvore de `import`: pega import direto,
# aliasado (`import x as y`) e diferido dentro de função (o repo usa os três). NÃO pega
# `importlib.import_module` com nome montado em runtime nem acesso via `getattr` sobre um
# módulo já importado. A segunda rota — catálogo INJETADO como parâmetro, sem import
# nenhum — é o que o teste de aridade cobre; sem ele o gate seria cego ao bypass.

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

from pipeline.domain.services.investimentos_dedup import _identity_key

_RAIZ = Path(__file__).resolve().parents[3]
_SEMENTE = "pipeline.domain.services.investimentos_dedup"
_PADRAO_CATALOGO = re.compile(r"institution_catalog|institution_resolver|seguradora_resolver")

# Âncoras anti-vacuidade: se um renome fizer o padrão parar de casar, o gate reprova em vez
# de passar sobre conjunto vazio — "gate verde e cego é pior que gate ausente".
_ANCORAS = ("pipeline.llm.institution_catalog", "pipeline.domain.services.seguradora_resolver")


def _modulo_para_path(modulo: str) -> Path | None:
    caminho = _RAIZ / (modulo.replace(".", "/") + ".py")
    return caminho if caminho.exists() else None


def _nomes_importados(no: ast.AST) -> set[str]:
    if isinstance(no, ast.ImportFrom):
        return {no.module} if no.module else set()
    if isinstance(no, ast.Import):
        return {nome.name for nome in no.names}
    return set()


def _imports_de(caminho: Path) -> set[str]:
    """Import direto, aliasado E diferido dentro de função — `ast.walk` vê a árvore toda."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    return {nome for no in ast.walk(arvore) for nome in _nomes_importados(no)}


def _vizinhos(modulo: str) -> set[str]:
    caminho = _modulo_para_path(modulo)
    if caminho is None:
        return set()
    return {i for i in _imports_de(caminho) if i.startswith(("pipeline.", "backend.", "scripts."))}


def _fecho_transitivo(semente: str) -> set[str]:
    visto: set[str] = set()
    fila = [semente]
    while fila:
        modulo = fila.pop()
        if modulo in visto:
            continue
        visto.add(modulo)
        fila.extend(_vizinhos(modulo) - visto)
    return visto


def _modulos_do_repo() -> set[str]:
    bases = (_RAIZ / "pipeline", _RAIZ / "backend/app")
    return {
        c.relative_to(_RAIZ).with_suffix("").as_posix().replace("/", ".")
        for base in bases
        for c in base.rglob("*.py")
    }


def _universo_de_catalogo() -> set[str]:
    """Descoberto do repo, não escrito à mão — módulo de catálogo novo já nasce coberto."""
    return {m for m in _modulos_do_repo() if _PADRAO_CATALOGO.search(m)}


def test_o_universo_de_catalogo_nao_e_vazio() -> None:
    """Sem esta asserção o gate passaria sobre conjunto vazio depois de um renome."""
    universo = _universo_de_catalogo()
    faltando = set(_ANCORAS) - universo
    assert faltando == set(), (
        f"âncoras de catálogo sumiram do repo: {faltando} — o padrão "
        f"{_PADRAO_CATALOGO.pattern!r} parou de casar e o gate viraria vácuo. "
        f"Renomeou o catálogo? Atualize `_PADRAO_CATALOGO`/`_ANCORAS` junto."
    )


def test_fecho_da_derivacao_nao_alcanca_o_catalogo() -> None:
    """Fecho TRANSITIVO, não import direto — o acoplamento entraria por um helper."""
    ofensores = _fecho_transitivo(_SEMENTE) & _universo_de_catalogo()
    assert ofensores == set(), (
        f"o catálogo de instituições entrou na derivação de `investment_id`: {ofensores}. "
        f"A ADR-400 §1 veda: a forma canônica de `instituicao` é propriedade de outro "
        f"subsistema, e um renome lá moveria o hash sem diff nem revisão."
    )


def test_identity_key_nao_aceita_fonte_externa_injetada() -> None:
    """A rota que o fecho de import NÃO vê: o catálogo passado como parâmetro."""
    parametros = list(inspect.signature(_identity_key).parameters)
    assert parametros == ["entry"], (
        f"`_identity_key` ganhou entrada além do próprio item: {parametros}. Toda fonte "
        f"nova na identidade precisa de revisão explícita contra a ADR-400 §1."
    )
