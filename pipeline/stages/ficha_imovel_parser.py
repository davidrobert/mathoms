"""Âncora da ficha de imóvel: lê os campos rotulados do IRPF e casa cada ficha com o seu item do E1.5a ([[ADR-440]])."""

# Extração pura ([[ADR-280]]): devolve o valor CRU de cada campo, sem canonicalizar. A
# normalização é do enricher, que passa os valores pelos mesmos extractors do
# `endereco_canonicalizer` — dois normalizadores seriam duas funções de identidade.

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

ANCORA_VERSAO = "1.0.0"

# Espelha os `maxLength` de `e15_baseline_extract.schema.json` (paridade em teste). É
# sentinela de janela que vazou para o campo vizinho: o campo acima do limite é descartado.
LIMITE_POR_CAMPO: dict[str, int] = {
    "logradouro": 80,
    "numero": 10,
    "complemento": 60,
    "matricula": 30,
    "inscricao_municipal": 40,
}

_SECAO_BENS = re.compile(r"DECLARA[ÇC][ÃA]O\s+DE\s+BENS\s+E\s+DIREITOS", re.I)
_SECAO_DIVIDAS = re.compile(r"D[ÍI]VIDAS\s+E\s+[ÔO]NUS\s+REAIS", re.I)
_ROTULO_LOGRADOURO = re.compile(r"\bLogradouro\s*:", re.I)
_ROTULO_IPTU = re.compile(r"\bInscri[çc][ãa]o\s+Municipal\s*\(IPTU\)\s*:", re.I)
# Primeira linha de cada bem: grupo e código antes da discriminação ("01 11 APARTAMENTO …").
_INICIO_DE_BEM = re.compile(r"^[ \t]*\d{2}[ \t]+\d{2}[ \t]+\S", re.M)
# O valor de um campo vai até o próximo rótulo da MESMA linha: a ficha impressa põe dois ou
# três pares rótulo:valor por linha ("Logradouro: … Nº: …", "Comp.: … Bairro: …").
_ROTULOS_DA_FICHA = re.compile(
    r"(?P<rotulo>\bInscri[çc][ãa]o\s+Municipal\s*\(IPTU\)|\bLogradouro|\bN[º°o]|\bComp\."
    r"|\bBairro|\bMunic[íi]pio|\bUF|\bCEP|\b[ÁA]rea\s+Total|\bData\s+de\s+Aquisi[çc][ãa]o"
    r"|\bRegistrado\s+no\s+Cart[óo]rio|\bNome\s+Cart[óo]rio|\bMatr[íi]cula)\s*:",
    re.I,
)
_CAMPO_POR_ROTULO = {
    "inscricao municipal (iptu)": "inscricao_municipal",
    "logradouro": "logradouro",
    "no": "numero",
    "comp.": "complemento",
    "matricula": "matricula",
}


@dataclass(frozen=True)
class FichaImovel:
    """Uma ficha com rótulo de endereço: a janela do bem (só para o join) e os campos crus."""

    janela: str
    campos: dict[str, str]


@dataclass(frozen=True)
class Ancoragem:
    """Resultado do join de um documento — contagens sem PII para a razão de revisão."""

    ancoras: dict[int, dict]
    fichas: int
    ambiguas: int
    sem_ficha: int
    descartados: int


def _sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()


def _secao_de_bens(texto: str) -> str:
    inicio = _SECAO_BENS.search(texto)
    if inicio is None:
        return ""
    fim = _SECAO_DIVIDAS.search(texto, inicio.end())
    return texto[inicio.start() : fim.start() if fim else len(texto)]


def _limpo(valor: str) -> str:
    return re.sub(r"\s+", " ", valor).strip(" \t:;,")


def _campo_do_rotulo(rotulo: str) -> str | None:
    normalizado = re.sub(r"\s+", " ", _sem_acento(rotulo)).replace("º", "o").replace("°", "o")
    return _CAMPO_POR_ROTULO.get(normalizado)


def _campos_da_linha(linha: str) -> dict[str, str]:
    marcas = list(_ROTULOS_DA_FICHA.finditer(linha))
    campos = {}
    for atual, proxima in zip(marcas, [*marcas[1:], None]):
        nome = _campo_do_rotulo(atual.group("rotulo"))
        valor = _limpo(linha[atual.end() : proxima.start() if proxima else len(linha)])
        if nome and valor:
            campos[nome] = valor
    return campos


# A coluna do nome do cartório quebra de linha e o PDF intercala a continuação depois do
# número da matrícula ("Matrícula: 12345 DE REGISTRO DE …"): o valor é o 1º token com dígito.
def _matricula(valor: str) -> str | None:
    primeiro = valor.split(" ")[0]
    return primeiro if re.search(r"\d", primeiro) else None


def _campos_da_regiao(regiao: str) -> dict[str, str]:
    campos: dict[str, str] = {}
    for linha in regiao.split("\n"):
        for nome, valor in _campos_da_linha(linha).items():
            campos.setdefault(nome, valor)
    matricula = _matricula(campos.pop("matricula", ""))
    return {**campos, "matricula": matricula} if matricula else campos


def _inicio_dos_campos(secao: str, desde: int, logradouro: int) -> int:
    iptus = [m.start() for m in _ROTULO_IPTU.finditer(secao, desde, logradouro)]
    return iptus[-1] if iptus else max(desde, secao.rfind("\n", desde, logradouro) + 1)


# O limite é o IPTU da PRÓXIMA ficha, que vem antes do `Logradouro` dela: sem isso, o último
# rótulo antes do próximo `Logradouro` é o dela, e a ficha seguinte perde inscrição e janela.
def _fim_dos_campos(secao: str, logradouro: int, ate: int) -> int:
    proximo_iptu = _ROTULO_IPTU.search(secao, logradouro, ate)
    limite = proximo_iptu.start() if proximo_iptu else ate
    ultimos = [m.end() for m in _ROTULOS_DA_FICHA.finditer(secao, logradouro, limite)]
    fim_de_linha = secao.find("\n", ultimos[-1] if ultimos else logradouro, limite)
    return fim_de_linha if fim_de_linha >= 0 else limite


def _inicio_do_bem(secao: str, desde: int, campos: int) -> int:
    inicios = [m.start() for m in _INICIO_DE_BEM.finditer(secao, desde, campos)]
    return inicios[-1] if inicios else desde


def ler_fichas(texto: str) -> list[FichaImovel]:
    """Fichas da seção de Bens e Direitos que trazem o rótulo `Logradouro`, em ordem."""
    secao = _secao_de_bens(texto)
    marcas = [m.start() for m in _ROTULO_LOGRADOURO.finditer(secao)]
    fichas, fim_anterior = [], 0
    for logradouro, proxima in zip(marcas, [*marcas[1:], len(secao)]):
        ini = _inicio_dos_campos(secao, fim_anterior, logradouro)
        fim = _fim_dos_campos(secao, logradouro, proxima)
        janela = secao[_inicio_do_bem(secao, fim_anterior, ini) : ini]
        fichas.append(FichaImovel(janela=janela, campos=_campos_da_regiao(secao[ini:fim])))
        fim_anterior = fim
    return fichas


def _valor_br(valor: object) -> str | None:
    try:
        centavos = Decimal(str(valor)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    inteiro, fracao = f"{abs(centavos):.2f}".split(".")
    sinal = "-" if centavos < 0 else ""
    return f"{sinal}{int(inteiro):,}".replace(",", ".") + f",{fracao}"


def _contem_valor(janela: str, valor_br: str) -> bool:
    return re.search(rf"(?<![\d.,]){re.escape(valor_br)}(?!\d|,\d)", janela) is not None


def _tokens(texto: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", _sem_acento(texto)) if len(t) >= 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


# Desempate só com margem: o vencedor precisa de pelo menos o dobro do score do segundo.
# Sem margem, duas fichas parecidas elegeriam a vencedora por ruído de tokenização.
def _melhor(scores: dict[int, float]) -> int | None:
    if len(scores) == 1:
        return next(iter(scores))
    ordem = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    (melhor, s1), (_, s2) = ordem[0], ordem[1]
    return melhor if s1 > 0 and s1 >= 2 * s2 else None


def _pares_do_item(i: int, item: dict, fichas: list[FichaImovel]) -> dict[tuple[int, int], float]:
    valor = _valor_br(item.get("valor_brl")) if item.get("secao") != "dividas_onus" else None
    if not valor:
        return {}
    tokens = _tokens(item.get("descricao") or "")
    return {
        (i, f): _jaccard(tokens, _tokens(ficha.janela))
        for f, ficha in enumerate(fichas)
        if _contem_valor(ficha.janela, valor)
    }


def _candidatos(fichas: list[FichaImovel], itens: list[dict]) -> dict[tuple[int, int], float]:
    pares: dict[tuple[int, int], float] = {}
    for i, item in enumerate(itens):
        pares.update(_pares_do_item(i, item, fichas))
    return pares


def _escolhas(pares: dict[tuple[int, int], float], lado: int) -> dict[int, int | None]:
    por_lado: dict[int, dict[int, float]] = {}
    for par, score in pares.items():
        por_lado.setdefault(par[lado], {})[par[1 - lado]] = score
    return {chave: _melhor(scores) for chave, scores in por_lado.items()}


def _ancora(ficha: FichaImovel, join: str) -> tuple[dict | None, int]:
    campos = {k: v for k, v in ficha.campos.items() if len(v) <= LIMITE_POR_CAMPO[k]}
    descartados = len(ficha.campos) - len(campos)
    return ({"join": join, **campos} if campos else None), descartados


def _e_imovel(item: dict) -> bool:
    hint = str(item.get("categoria_hint") or item.get("categoria") or "").lower()
    return hint == "imovel" and item.get("secao") != "dividas_onus"


def _ancoras_dos_aceitos(
    fichas: list[FichaImovel], pares: dict[tuple[int, int], float], aceitos: dict[int, int]
) -> tuple[dict[int, dict], int]:
    ancoras, descartados = {}, 0
    for i, f in aceitos.items():
        unico = sum(1 for p in pares if p[0] == i) == 1 and sum(1 for p in pares if p[1] == f) == 1
        ancora, perdidos = _ancora(fichas[f], "valor" if unico else "valor_tokens")
        descartados += perdidos
        if ancora is not None:
            ancoras[i] = ancora
    return ancoras, descartados


def ancorar(texto: str, itens: list[dict]) -> Ancoragem:
    """Join ficha↔item pelo valor BR exato, desempatado por tokens; ambíguo fica sem âncora."""
    fichas = ler_fichas(texto)
    pares = _candidatos(fichas, itens)
    do_item, da_ficha = _escolhas(pares, 0), _escolhas(pares, 1)
    aceitos = {i: f for i, f in do_item.items() if f is not None and da_ficha.get(f) == i}
    ancoras, descartados = _ancoras_dos_aceitos(fichas, pares, aceitos)
    com_candidata = {i for i, _ in pares}
    sem_ficha = sum(1 for i, it in enumerate(itens) if _e_imovel(it) and i not in com_candidata)
    return Ancoragem(
        ancoras=ancoras,
        fichas=len(fichas),
        ambiguas=len(com_candidata - set(aceitos)),
        sem_ficha=sem_ficha if fichas else 0,
        descartados=descartados,
    )


def aplicar_ancoras(payload: dict, texto: str) -> Ancoragem:
    """Grava `ancora_imovel` nos itens casados e `ancora_versao` na raiz; idempotente."""
    itens = payload.get("itens") or []
    resultado = ancorar(texto, itens)
    for i, item in enumerate(itens):
        item.pop("ancora_imovel", None)
        if i in resultado.ancoras:
            item["ancora_imovel"] = resultado.ancoras[i]
    payload["ancora_versao"] = ANCORA_VERSAO
    return resultado


def assinatura_de_ancoras(payload: dict | None) -> str:
    """O que decide regravar o artefato: versão do parser + âncoras, item a item."""
    itens = (payload or {}).get("itens") or []
    corpo = [(payload or {}).get("ancora_versao"), [it.get("ancora_imovel") for it in itens]]
    return json.dumps(corpo, sort_keys=True, ensure_ascii=False)


__all__ = [
    "ANCORA_VERSAO",
    "LIMITE_POR_CAMPO",
    "Ancoragem",
    "FichaImovel",
    "ancorar",
    "aplicar_ancoras",
    "assinatura_de_ancoras",
    "ler_fichas",
]
