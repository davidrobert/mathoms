"""Payload da nota one-shot de recalibração do bloco de IF (A40.l25 · ADR-360)."""
# Mora no VIEW-MODEL, nunca no artefato E5: a chave de cache do parecer é
# sha256 sobre o payload E5 (ADR-369 §Alternativa A), então um campo novo lá
# cobraria uma re-geração de parecer por workspace da frota inteira para
# publicar um aviso de UI.

from __future__ import annotations

from typing import Any

from pipeline.domain.services.if_monte_carlo_payload import (
    CONE_CHAVES_PRE_4_0,
    MAJOR_DO_RENAME_DO_CONE,
)
from pipeline.domain.services.if_recalibracao import (
    FACETA_ANO_CONE,
    FACETA_PROBABILIDADE_ALVO,
    mc_major,
    resolve_facetas,
)

# Contrato de leitura (gate: dev/check_artifact_read_keys.py) — as chaves lidas do
# payload precisam existir no schema do stage. Declarado, nunca inferido da query.
# `E5` e `analyze_finances` são o mesmo stage (ADR-093).
ARTIFACT_CONTRACT = ("analyze_finances",)
# Modo estrito: este módulo só toca UM bloco do payload, então toda chave literal
# lida aqui é checada contra `properties.if_monte_carlo` — inclusive as lidas de
# parâmetro, que é onde `p50_ano_if` se escondeu do rastreio por variável.
ARTIFACT_CONTRACT_BLOCO = "if_monte_carlo"


def _bloco_if(snapshot) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    bloco = (snapshot.content_json or {}).get("if_monte_carlo")
    return bloco if isinstance(bloco, dict) else None


def _inteiro(valor: Any) -> int | None:
    return valor if isinstance(valor, int) else None


# Ler a chave ANTIGA direto deixou esta nota inerte desde que nasceu (#1356):
# `p50_ano_if` não existe em artefato 4.0+, então o lado ATUAL do par vinha sempre
# `None` e a faceta do ano — o número que motiva a nota inteira — nunca renderizava.
#
# Resolver por lado é obrigatório, não defensivo: o par que a nota compara atravessa
# justamente o bump que renomeou a chave, e o cliente com relatório v1/2.0 na base e
# 4.0+ na tela tem a chave antiga de um lado e a de hoje do outro — é exatamente esse
# par que o ledger manda avisar.
#
# A chave de HOJE fica LITERAL no `.get()` de propósito: é a forma que
# `dev/check_artifact_read_keys.py` enxerga, e foi a ausência dessa cobertura que
# deixou a chave morta passar em review. A do artefato antigo sai do mapa justamente
# porque NÃO está no schema de hoje — gateá-la reprovaria leitura correta.
def _ano_cone(bloco: dict[str, Any] | None) -> int | None:
    """Ano do cenário central; artefato pré-4.0 responde pela chave antiga (ADR-369 D3)."""
    if mc_major(bloco) < MAJOR_DO_RENAME_DO_CONE:
        return _inteiro((bloco or {}).get(CONE_CHAVES_PRE_4_0["ano_if_cenario_central"]))
    return _inteiro((bloco or {}).get("ano_if_cenario_central"))


def _faceta_ano(anterior: dict[str, Any], atual: dict[str, Any]) -> dict[str, Any] | None:
    """Faceta comparável: só renderiza se os dois anos existem E diferem."""
    # Sem movimento visível não há inferência errada a prevenir — publicar
    # "de 2049 para 2049" inventaria uma mudança.
    de, para = _ano_cone(anterior), _ano_cone(atual)
    if de is None or para is None or de == para:
        return None
    return {"faceta": FACETA_ANO_CONE, "ano_anterior": de, "ano_novo": para}


def _faceta_probabilidade(atual: dict[str, Any]) -> dict[str, Any] | None:
    """Faceta incomparável: sem par, e a probabilidade ANTIGA nunca é publicada."""
    if atual.get("prob_if_ate_prazo_declarado") is None:
        return None
    return {
        "faceta": FACETA_PROBABILIDADE_ALVO,
        "prazo_declarado_anos": atual.get("prazo_declarado_anos"),
        "ano_alvo_declarado": atual.get("ano_alvo_declarado"),
    }


def _facetas_renderizaveis(
    nomes: tuple[str, ...], anterior: dict[str, Any], atual: dict[str, Any]
) -> list[dict[str, Any]]:
    """Aplica supressão por faceta: só entra o número que ESTE relatório publica."""
    construtores = {
        FACETA_ANO_CONE: lambda: _faceta_ano(anterior, atual) if atual.get("exibir_cone") else None,
        FACETA_PROBABILIDADE_ALVO: lambda: _faceta_probabilidade(atual),
    }
    return [f for nome in nomes if (f := construtores[nome]()) is not None]


# Falha FECHADA em ausência de evidência: sem relatório anterior, ou com o
# bloco do anterior ilegível, não há os dois lados e afirmar "mudou" seria
# fabricar. `mc_version` AUSENTE dentro de bloco legível é outra coisa — é
# evidência de v1, e dispara.
#
# A diferença entre dois relatórios mistura modelo E dados da família. Quando
# as competências coincidem (re-run do mesmo período) a diferença é limpa e a
# cláusula de atribuição some da copy.
def build_recalibracao_note(prev, curr) -> dict[str, Any] | None:
    """Nota de recalibração para o par (anterior, atual), ou `None` para calar."""
    anterior, atual = _bloco_if(prev), _bloco_if(curr)
    if anterior is None or atual is None:
        return None

    facetas = _facetas_renderizaveis(
        resolve_facetas(mc_major(anterior), mc_major(atual)), anterior, atual
    )
    if not facetas:
        return None

    return {
        "facetas": facetas,
        "periodo_anterior": getattr(prev, "period_yyyymm", None),
        "competencia_mudou": _competencia_mudou(prev, curr),
    }


def _competencia_mudou(prev, curr) -> bool:
    anterior = getattr(prev, "period_yyyymm", None)
    atual = getattr(curr, "period_yyyymm", None)
    return bool(anterior and atual and anterior != atual)
