"""Gate: o caminho de classificação da E5 não decide classe por `tipo` ([[A40.l82]] · RV8-01).

Metade do codomínio de `_classify_investimento` (`consolidate_baseline.py:711`) é
**default de grupo RFB** — `renda_fixa` do grupo 04, `investimento` do fall-through —
indistinguível de valor derivado de evidência. Quando esse campo chegou ao
classificador, 11 de 61 posições migraram de `Fundos` para `Renda Fixa` com
`autoridade: "keyword"` e zero `review_reason`.

**Este gate fecha a classe, não a instância.** O teste estrutural (`"tipo" not in entry`)
fica como *diagnóstico nomeado* — ele aponta o arquivo do fix, mas fica verde se o campo
voltar sob outro nome. Medido: sob a mutação "o campo volta como `tipo_rfb`", o
comportamental fica vermelho e o estrutural fica verde.

**Condição de retomada (2026-08-25, dono `data-engineer`):** `tipo` volta a ser
autoritativo quando o degrau 1 da [[ADR-400]] existir — isto é, quando o produtor
separar presunção de fato. A condição vive na §Emenda da ADR-400 com dono; não há
relógio aqui de propósito, porque waiver que vence travando o repo é dívida pior que a
que ele cobre.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.domain.services.asset_classifier import classify_asset, default_keywords
from pipeline.domain.services.investimentos_classes_analyzer import (
    InvestimentosClassesAnalyzer,
    InvestimentosClassesConfig,
)
from pipeline.domain.services.patrimonio_resolvers import build_members_from_consolidated
from pipeline.domain.services.patrimonio_types import MemberIdentity
from pipeline.domain.services.top_ativos_analyzer import TopAtivosAnalyzer

_REPO = Path(__file__).resolve().parents[3]
_SCORING = _REPO / "config" / "scoring.json"

#: Par discriminante — a forma exata do RV8-01: `tipo` diz o default do grupo 04,
#: `descricao` diz o instrumento. Se os dois passarem a concordar, o gate perde poder
#: de discriminação e `test_a_mutacao_ainda_e_detectavel` avisa.
_TIPO_MENTIROSO = "renda_fixa"
_DESCRICAO = "FUNDO DE INVESTIMENTO FIC FIM"
_VALOR = 100_000.0

_IDENTITY = MemberIdentity(
    titular_key="david", conjuge_key="", titular_nome="David", conjuge_nome=""
)


def _keywords_de_producao() -> dict:
    """As keywords que de fato rodam: `scoring.json` do repo sobrescreve a classe inteira."""
    from pipeline.domain.services.asset_classifier import merge_asset_keywords

    return merge_asset_keywords(json.loads(_SCORING.read_text(encoding="utf-8")))


@pytest.fixture(params=["default", "producao"])
def keywords(request) -> dict | None:
    """Sem isto o gate certifica um conjunto de keywords que nada consome."""
    return None if request.param == "default" else _keywords_de_producao()


def _baseline(tipo: str) -> dict:
    return {
        "investimentos_consolidados": [
            {
                "descricao": _DESCRICAO,
                "tipo": tipo,
                "proprietario": "david",
                "valores_31_12": {"2025": _VALOR},
            }
        ],
        "imoveis_consolidados": [],
        "veiculos_consolidados": [],
        "dividas": [],
        "patrimonio_por_ano": {"2025": {"total_bens": _VALOR}},
    }


def _bens(tipo: str) -> dict:
    titular, _ = build_members_from_consolidated(_baseline(tipo), _IDENTITY)
    return titular["bens"]


# =============================================================================
# Auto-falseabilidade — sem isto o gate pode ficar verde por vacuidade
# =============================================================================


# Se as keywords mudarem e os dois lados colapsarem, os testes abaixo ficam verdes
# sem medir nada. Falha aqui significa "troque o par", não "o fix quebrou".
def test_a_mutacao_ainda_e_detectavel(keywords):
    """O par discriminante ainda discrimina **no classificador**."""
    assert classify_asset("", _DESCRICAO, keywords=keywords) == "Fundos"
    assert classify_asset(_TIPO_MENTIROSO, _DESCRICAO, keywords=keywords) == "Renda Fixa"


# =============================================================================
# O gate — comportamental, sobre o caminho de produção
# =============================================================================


def test_tabela_de_classes_nao_muda_com_tipo_mentiroso(keywords):
    """Variar só `tipo` no baseline não pode mover a tabela publicada."""
    cfg = InvestimentosClassesConfig(keywords_por_classe=keywords) if keywords else None

    def baldes(tipo: str) -> dict:
        r = InvestimentosClassesAnalyzer(cfg).analyze([_bens(tipo)])
        return {c.categoria: round(c.valor, 2) for c in r.tabela_classes if c.valor}

    assert baldes(_TIPO_MENTIROSO) == baldes("")


def test_a_classe_e_a_da_descricao_nao_a_do_tipo(keywords):
    """Invariância sozinha admitiria os dois lados errados juntos — afirma a direção."""
    cfg = InvestimentosClassesConfig(keywords_por_classe=keywords) if keywords else None
    r = InvestimentosClassesAnalyzer(cfg).analyze([_bens(_TIPO_MENTIROSO)])
    baldes = {c.categoria: round(c.valor, 2) for c in r.tabela_classes if c.valor}

    assert baldes == {"Fundos": _VALOR}
    assert "Renda Fixa" not in baldes


def test_top_ativos_tambem_nao_le_tipo(keywords):
    """Segundo consumidor da mesma entry — o gate cobre os dois, não um."""
    r = TopAtivosAnalyzer().analyze([("David", _bens(_TIPO_MENTIROSO))])
    assert r.top_ativos[0].classe == "Fundos"


# =============================================================================
# Diagnóstico nomeado — NÃO é o gate: fica verde se o campo voltar com outro nome
# =============================================================================


def test_entry_do_split_nao_carrega_tipo():
    """Aponta o arquivo do fix. Fecha a instância, não a classe — ver docstring do módulo."""
    item = _bens(_TIPO_MENTIROSO)["investimentos"][0]
    assert "tipo" not in item


# =============================================================================
# Fonte única das keywords — foi a divergência que quase tornou o fix inerte
# =============================================================================


def test_scoring_do_repo_nao_diverge_do_default():
    """`merge_asset_keywords` deixa `scoring.json` sobrescrever a classe inteira."""
    scoring = json.loads(_SCORING.read_text(encoding="utf-8")).get("asset_class_keywords") or {}
    padrao = default_keywords()

    divergentes = {
        classe: sorted(set(map(str.lower, kws)) - set(padrao.get(classe, ())))
        for classe, kws in scoring.items()
        if isinstance(kws, list) and set(map(str.lower, kws)) - set(padrao.get(classe, ()))
    }
    assert not divergentes, (
        f"`config/scoring.json` acrescenta keyword que o default não tem: {divergentes}. "
        "Duas fontes para a mesma verdade — corte em uma vira no-op na outra."
    )
