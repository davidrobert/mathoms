"""Taxonomia canônica de classes de ativo no E5 ([[ADR-193]] · [[ADR-400]]).

A classe sai do sinal mais forte disponível e o resultado **declara quem
decidiu**. `instituicao` não entra: a forma canônica dela é propriedade do
`institution_catalog` ([[ADR-137]]/[[ADR-384]]), e renomear lá reclassificava
ativo aqui sem diff, sem revisão e sem sinal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# 8 buckets financeiros + Imóveis Investimento + Outros = 10.
BUCKETS: tuple[str, ...] = (
    "Cripto",
    "Previdência",
    "FIIs",
    "Internacional",
    "Ações BR",
    "Renda Fixa",
    "Fundos",
    "Caixa",
    "Imóveis Investimento",
    "Outros",
)

# Ordem de avaliação: especialização → fallback. Renda Fixa antes de Ações BR
# porque keywords LCI/CDB/RDB/Tesouro são mais específicas que
# "participacao societaria" / "acoes" e devem vencer quando ambas batem.
EVALUATION_ORDER: tuple[str, ...] = (
    "Cripto",
    "Previdência",
    "FIIs",
    "Internacional",
    "Renda Fixa",
    "Ações BR",
    "Fundos",
    "Caixa",
)

_DEFAULT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Cripto": ("cripto", "bitcoin", "ethereum", "binance", "btc", "eth", "hashdex"),
    "Previdência": ("pgbl", "vgbl", "previdencia", "previdência"),
    "FIIs": ("fii", "fiis", "fundo imobiliario", "fundo imobiliário"),
    # `wise`/`bofa`/`bank of america` saíram: são CUSTÓDIA, não classe. A pergunta
    # "quem guarda?" mora em `exposicao_cambial_analyzer._CUSTODIA_ESTRANGEIRA`.
    "Internacional": (
        "usd",
        "dolar",
        "dólar",
        "ivvb",
        "global",
        "moeda estrangeira",
        "exterior",
    ),
    "Ações BR": (
        "acoes",
        "ações",
        "acao",
        "ação",
        "itsa",
        "brkm",
        "petr",
        "etf",
        "participacao societaria",
        "participação societária",
    ),
    "Renda Fixa": (
        "renda fixa",
        "cdb",
        "rdb",
        "lci",
        "lca",
        "tesouro",
        "debenture",
        "debênture",
        "certificado de deposito",
        "cra",
        "cri",
        "poupanca",
        "poupança",
        "cofrinhos",
    ),
    "Fundos": (
        "fic ",
        " fim",
        " fia",
        "fundo de investimento",
        "alaska",
        "constellation",
        "western",
        "safari",
        "dna energy",
    ),
    "Caixa": ("conta corrente", "picpay", "nubank", "saldo em conta", "conta de deposito"),
}

BUCKET_OUTROS = "Outros"

_TICKER_RE = re.compile(r"\b[a-z]{4}11\b")

# `XXXX11` é sufixo compartilhado por FII, ETF, UNIT e BDR — o padrão sozinho não
# prova FII, e decidindo sozinho ele mandava `IVVB11`, `BOVA11`, `HASH11`,
# `BPAC11` e `TAEE11` para FIIs contra sinal explícito. A tabela é deliberadamente
# mínima (só os tickers nomeados no §r7); catálogo geral de instrumentos é o
# degrau 1, fora do escopo desta rodada.
_TICKER_CLASSE: dict[str, str] = {
    "bova11": "Ações BR",
    "bpac11": "Ações BR",
    "taee11": "Ações BR",
    "hash11": "Cripto",
    "hglg11": "FIIs",
}


OUTROS_EXCESSIVO_THRESHOLD_PCT = 5.0


@dataclass(frozen=True)
class OutrosExcessivoWarning:
    """Emitido quando ``Outros`` excede ``threshold_pct`` (ADR-097 D1 · ADR-193)."""

    pct_outros: float
    threshold_pct: float = 5.0

    def format(self) -> str:
        return (
            f"Classificação de investimentos: {self.pct_outros:.1f}% caiu em "
            f"'Outros' (limite: {self.threshold_pct:.0f}%). Revise keywords ou "
            f"descrições — investimentos não-classificados sugerem cobertura "
            f"incompleta da taxonomia."
        )


# O degrau 1 é `tipo`, não `(secao, codigo)`: a M1 mediu `codigo` degenerado em
# 51,8% dos itens (§ADR-400). E ele tem DUAS camadas porque metade do codomínio de
# `tipo` (`renda_fixa`, `acao`, `participacao_societaria`, `fundo_investimento`)
# sai de `_classify_investimento(normalize_grupo(codigo), …)` e herda essa mesma
# degeneração; a outra metade sai do hint sozinho, que é enum fechado de 7.
# Tratar os dois grupos igual repetiria o erro um nível acima.
class AssetAuthority(str, Enum):
    """Qual degrau decidiu a classe — vai no artefato, para o leitor saber a força."""

    # CONCLUSIVO/PRESUNTIVO/SEM_MAPA nascem declarados e **sem produtor**: quem os
    # emite é o degrau 1, que entra no PR2. Membro inalcançável é dívida se
    # ninguém souber que é deliberado — este comentário é o registro.
    CONCLUSIVO = "conclusivo"
    PRESUNTIVO = "presuntivo"
    # A classe veio da PROVENIÊNCIA do item (imóvel é "Imóveis Investimento" por
    # construção), não de degrau nenhum. Nomear evita que `None` signifique ao
    # mesmo tempo "a origem decidiu" e "campo não populado" — a ambiguidade que
    # o RV7-04 denuncia, e que o consumidor do DE-2 teria de destratar.
    ORIGEM = "origem"
    KEYWORD = "keyword"
    TICKER = "ticker"
    SEM_MATCH = "sem_match"
    SEM_HAYSTACK = "sem_haystack"
    SEM_MAPA = "sem_mapa"


# `SEM_MAPA` entra aqui já: `tipo` fora do mapa é ausência de classe, e a
# supressão graduada precisa contá-lo no dia em que o degrau 1 passar a emiti-lo.
_AUTORIDADES_SEM_CLASSE = frozenset(
    {AssetAuthority.SEM_MATCH, AssetAuthority.SEM_HAYSTACK, AssetAuthority.SEM_MAPA}
)


# Só comprimentos: o conteúdo é PII em potencial e nunca entra em warning.
@dataclass(frozen=True)
class AtivoSemHaystackWarning:
    """Item chegou sem `tipo` e sem `descricao` ([[ADR-097]] D1) — bug a montante."""

    tipo_len: int
    descricao_len: int

    def format(self) -> str:
        return (
            f"Classificação de ativo: item sem sinal algum "
            f"(len(tipo)={self.tipo_len}, len(descricao)={self.descricao_len}) — "
            f"violação de contrato do produtor, não incerteza de taxonomia."
        )


@dataclass(frozen=True)
class AssetClassification:
    """Classe + autoridade. `moeda`/`lastro` nascem no shape, populados no degrau 1."""

    classe: str
    autoridade: AssetAuthority
    moeda: str | None = None
    lastro: str | None = None
    warnings: tuple[object, ...] = ()

    @property
    def nao_classificado(self) -> bool:
        return self.autoridade in _AUTORIDADES_SEM_CLASSE


def _normalize_haystack(*parts: str) -> str:
    """Lowercase + separadores `_`/`-` viram espaço (corrige bug raiz tipo `renda_fixa`)."""
    raw = " ".join(p for p in parts if p)
    return raw.lower().replace("_", " ").replace("-", " ")


def _match_bucket(haystack: str, keywords: dict[str, tuple[str, ...]]) -> str | None:
    for bucket in EVALUATION_ORDER:
        for kw in keywords.get(bucket, ()):
            if kw and kw in haystack:
                return bucket
    return None


def _match_ticker(haystack: str) -> str | None:
    """Primeiro `XXXX11` conhecido da tabela; ticker fora dela não decide nada."""
    for ticker in _TICKER_RE.findall(haystack):
        classe = _TICKER_CLASSE.get(ticker)
        if classe is not None:
            return classe
    return None


# Ordem ([[ADR-400]]): keyword explícita → ticker conhecido → sem match. O padrão
# `XXXX11` perde para qualquer sinal textual porque ele não distingue FII de ETF.
def _decide_classe(
    haystack: str, keywords: dict[str, tuple[str, ...]]
) -> tuple[str, AssetAuthority]:
    """Degrau mais forte disponível → (classe, quem decidiu)."""
    if not haystack.strip():
        return BUCKET_OUTROS, AssetAuthority.SEM_HAYSTACK
    bucket = _match_bucket(haystack, keywords)
    if bucket is not None:
        return bucket, AssetAuthority.KEYWORD
    ticker = _match_ticker(haystack)
    if ticker is not None:
        return ticker, AssetAuthority.TICKER
    return BUCKET_OUTROS, AssetAuthority.SEM_MATCH


# `SEM_MATCH` é agregado e escala pelo limiar graduado, nunca por razão por item —
# o cap de cardinalidade da [[ADR-272]] aplicado desde o desenho.
def _warnings_for(autoridade: AssetAuthority, tipo: str, descricao: str) -> list[object]:
    if autoridade is not AssetAuthority.SEM_HAYSTACK:
        return []
    return [AtivoSemHaystackWarning(tipo_len=len(tipo), descricao_len=len(descricao))]


def classify_asset_outcome(
    tipo: str,
    descricao: str = "",
    *,
    keywords: dict[str, tuple[str, ...]] | None = None,
) -> AssetClassification:
    """Classe + autoridade + warnings tipados ([[ADR-400]]). Site único de construção."""
    haystack = _normalize_haystack(tipo, descricao)
    classe, autoridade = _decide_classe(haystack, keywords or _DEFAULT_KEYWORDS)
    return AssetClassification(
        classe=classe,
        autoridade=autoridade,
        warnings=tuple(_warnings_for(autoridade, tipo, descricao)),
    )


def classify_asset(
    tipo: str,
    descricao: str = "",
    *,
    keywords: dict[str, tuple[str, ...]] | None = None,
) -> str:
    """Fachada: só a classe. Quem precisa da autoridade usa ``classify_asset_outcome``."""
    return classify_asset_outcome(tipo, descricao, keywords=keywords).classe


def default_keywords() -> dict[str, tuple[str, ...]]:
    """Cópia imutável das keywords default (8 buckets financeiros)."""
    return {k: tuple(v) for k, v in _DEFAULT_KEYWORDS.items()}


def merge_asset_keywords(scoring: dict | None) -> dict[str, tuple[str, ...]]:
    """Defaults + overrides de ``scoring.json::asset_class_keywords`` por classe."""
    acl = (scoring or {}).get("asset_class_keywords") or {}
    merged: dict[str, tuple[str, ...]] = {}
    for classe, ks in default_keywords().items():
        override = acl.get(classe)
        merged[classe] = tuple(str(k).lower() for k in override) if override else ks
    # Forward-compat: classe nova em scoring.json não precisa estar em defaults.
    for classe, override in acl.items():
        if classe == "_comment" or classe in merged:
            continue
        if isinstance(override, list):
            merged[classe] = tuple(str(k).lower() for k in override)
    return merged
