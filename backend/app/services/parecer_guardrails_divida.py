"""Guardrails pós-LLM de dívida e auto-contradição do parecer (FP-4 · revisão r7).

Mesmo contrato dos demais guardrails: coerce/mutação pós-validação, nunca ``raise``,
nunca ``needs_review``, zero custo LLM, zero reask (ADR-292/294).

Mora fora de ``parecer_pos_llm_guardrails`` porque aquele módulo já encostava no teto
de 500 linhas; os helpers de piso compartilhados continuam lá.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

from backend.app.services.parecer_pos_llm_guardrails import (
    aplicar_piso_pontos_fortes,
    ascii_fold,
)
from backend.app.services.parecer_red_lines import taxa_declarada
from pipeline.llm.schemas.parecer_planejador import (
    CampoFaltante,
    ParecerPlanejadorOutput,
    Sugestao,
)

logger = logging.getLogger("mathoms.llm.parecer_planejador")

_SUGESTAO_HORIZONS = ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")

# ----------------------------------------------------------------------
# (4) Dívida de taxa desconhecida — piso de prescrição (FP-4 D3-A)
# ----------------------------------------------------------------------

# Pede o nome CANÔNICO (RV6-15 / #1573): o pedido alimenta a expansão do manifest, e
# apontar para a chave aposentada mandaria o próximo leitor procurar no lugar errado.
_TAXA_PATH = "$.endividamento.dividas[{i}].taxa_juros_aa"
_MOTIVO_TAXA = (
    "Custo da dívida ausente no E5: sem a taxa não se sustenta prescrever aporte "
    "(que a supõe barata) nem prescrever quitação (que a supõe cara)."
)
_CAMPOS_FALTANTES_CAP = 20  # espelha ParecerPlanejadorOutput

# As DUAS direções ficam proibidas com taxa nula. O piso NÃO olha o TIPO da dívida:
# `descricao` é fabricada pelo produtor (`f"Financiamento imobiliário ({nome})"`), e piso
# sobre rótulo inventado é prescrição sobre invenção. A exceção real que isso protege é
# SFH/MCMV/consórcio contemplado com taxa abaixo da Selic — quitar dívida barata é erro.
_QUITACAO_LEMMAS = (
    "quitar",
    "quitacao",
    "amortizar",
    "amortizacao",
    "antecipar parcela",
    "antecipar as parcelas",
    "abater saldo",
    "liquidar a divida",
    "liquidar o financiamento",
)
# Braço oposto — argumenta CONTRA quitar, logo afirma que a dívida é barata.
# "renegociar" fica fora dos dois: é o movimento de DESCOBERTA da taxa, o único
# conselho que o desconhecimento não contradiz.
_MANTER_DIVIDA_LEMMAS = (
    "em vez de quitar",
    "em vez de amortizar",
    "ao inves de quitar",
    "ao inves de amortizar",
    "nao quitar",
    "nao amortizar",
    "nao antecipar",
    "manter o financiamento",
    "manter a divida",
    "carregar a divida",
    "preservar o financiamento",
)


def _taxa_desconhecida(divida: Any) -> bool:
    """Taxa utilizável é número positivo; `bool` é subclasse de `int` e não conta."""
    if not isinstance(divida, Mapping):
        return False
    taxa = taxa_declarada(divida)
    return isinstance(taxa, bool) or not isinstance(taxa, (int, float)) or taxa <= 0


def _saldo_vivo(divida: Any) -> bool:
    saldo = divida.get("saldo_devedor") if isinstance(divida, Mapping) else None
    return isinstance(saldo, (int, float)) and not isinstance(saldo, bool) and saldo > 0


def _indices_taxa_desconhecida(e5_data: Mapping[str, Any]) -> list[int]:
    dividas = (e5_data.get("endividamento") or {}).get("dividas") or []
    return [i for i, d in enumerate(dividas) if _saldo_vivo(d) and _taxa_desconhecida(d)]


def _campos_injetaveis(output: ParecerPlanejadorOutput, indices: list[int]) -> list[CampoFaltante]:
    """Pedidos de taxa ainda não presentes, respeitando o cap do campo."""
    atuais = output.campos_faltantes_pediria_se_iterasse or []
    ja_pedidos = {c.field_path for c in atuais}
    livre = max(0, _CAMPOS_FALTANTES_CAP - len(atuais))
    novos = [_TAXA_PATH.format(i=i) for i in indices]
    return [
        CampoFaltante(field_path=path, motivo=_MOTIVO_TAXA)
        for path in novos[:livre]
        if path not in ja_pedidos
    ]


def _toma_partido_sobre_divida(sug: Sugestao) -> bool:
    acao = ascii_fold(sug.acao)
    return any(lemma in acao for lemma in _QUITACAO_LEMMAS + _MANTER_DIVIDA_LEMMAS)


def _sem_prescricao_de_divida(output: ParecerPlanejadorOutput) -> tuple[dict[str, list], int]:
    update: dict[str, list] = {}
    removidas = 0
    for horizon in _SUGESTAO_HORIZONS:
        antes = getattr(output, horizon)
        depois = [s for s in antes if not _toma_partido_sobre_divida(s)]
        removidas += len(antes) - len(depois)
        update[horizon] = depois
    return update, removidas


def _telemetria_divida(removidas: int, injetados: list[CampoFaltante]) -> dict:
    return {
        "prescricao_divida_removida": removidas,
        "taxa_divida_injetada_paths": [c.field_path for c in injetados],
    }


def piso_prescricao_divida(
    output: ParecerPlanejadorOutput, e5_data: Mapping[str, Any], workspace_id: str
) -> tuple[ParecerPlanejadorOutput, dict]:
    """Taxa nula ⇒ prescrição sobre a dívida "não se aplica", e o parecer pede a taxa."""
    indices = _indices_taxa_desconhecida(e5_data)
    if not indices:
        return output, _telemetria_divida(0, [])
    update, removidas = _sem_prescricao_de_divida(output)
    injetados = _campos_injetaveis(output, indices)
    telemetria = _telemetria_divida(removidas, injetados)
    if not (removidas or injetados):
        return output, telemetria
    if injetados:
        atuais = output.campos_faltantes_pediria_se_iterasse or []
        update["campos_faltantes_pediria_se_iterasse"] = [*atuais, *injetados]
    logger.warning(
        "parecer_piso_prescricao_divida", extra={"workspace_id": workspace_id, **telemetria}
    )
    return output.model_copy(update=update), telemetria


# ----------------------------------------------------------------------
# (5) Auto-contradição ponto forte × risco (FP-4 D3-B)
# ----------------------------------------------------------------------

_RESSALVA_CONTRADICAO = (
    "Ressalva: este tema também consta como risco nesta edição — leia os dois em conjunto."
)
_LIQUIDEZ_EXCESSIVA = "excessiva"
# S1, não S4. O manifest projeta seções alinhadas a S1/S2/S3/S7/S8/S9/S10 — **S4 nunca** —,
# e o bloco de reserva (`saude_balanco`) é `aligned_with_layout: "S1"`. Armado em S4, este
# guardrail só dispararia se o modelo errasse o rótulo: medido no golden, o sinal do E5 está
# VIVO (`avaliacao_liquidity == "Excessiva"`) e ele nunca disparou. A [[ADR-412]] §Emenda E3
# apoia-se nele para NÃO suprimir `avaliacao_liquidity` — o argumento dependia de um
# mecanismo que provavelmente nunca rodou.
_SECAO_LIQUIDEZ = "S1"
_TEMA_LIQUIDEZ = "Liquidez"


# R1 NÃO remove — medido e refutado no r7. O par (section_id, tema_canonico) é um BALDE,
# não identidade de assunto: casou 2/5 pontos fortes, e um é falso-positivo (S2 +
# "Equilíbrio presente-futuro" aproxima "taxa de poupança alta" de "gasto com saúde alto"
# — mesmo balde, assuntos distintos). Remover ali derrubaria o ponto forte mais sólido do
# parecer; casar só por `section_id` é pior: 4/5. Identidade de assunto exigiria âncora
# estrutural, e `PontoForte` é da classe PROSA-SEM-ÂNCORA (sem campo `ancoras` — ver
# `parecer_evidencia._iter_prose_only_items`). Fica como contagem para o r8.
def _pares_secao_tema_colididos(output: ParecerPlanejadorOutput) -> int:
    """R1 rebaixada a telemetria: pontos fortes cujo (seção, tema) também é risco."""
    marcados = {(r.section_id, r.tema_canonico) for r in output.riscos}
    return sum(
        1
        for p in output.pontos_fortes
        if p.section_id is not None
        and p.tema_canonico is not None
        and (p.section_id, p.tema_canonico) in marcados
    )


def _liquidez_excessiva(e5_data: Mapping[str, Any]) -> bool:
    reserva = e5_data.get("reserva_emergencia") or {}
    return str(reserva.get("avaliacao_liquidity") or "").strip().lower() == _LIQUIDEZ_EXCESSIVA


def _pontos_de_liquidez(output: ParecerPlanejadorOutput) -> set[int]:
    return {
        i
        for i, p in enumerate(output.pontos_fortes)
        if p.section_id == _SECAO_LIQUIDEZ and p.tema_canonico == _TEMA_LIQUIDEZ
    }


# O desfecho é R2: o sinal vem do E5 (`avaliacao_liquidity == "Excessiva"`), não da
# co-ocorrência de baldes no próprio parecer. Elogiar a reserva enquanto o E5 a declara
# superdimensionada é contradição sobre o MESMO objeto medido — não sobre um balde.
def neutralize_autocontradicao(
    output: ParecerPlanejadorOutput, e5_data: Mapping[str, Any], workspace_id: str
) -> tuple[ParecerPlanejadorOutput, dict]:
    """Remove ponto forte de liquidez que o E5 contradiz (reserva excessiva)."""
    alvos = _pontos_de_liquidez(output) if _liquidez_excessiva(e5_data) else set()
    pontos, removidos, ressalvados = aplicar_piso_pontos_fortes(
        list(output.pontos_fortes), sorted(alvos), _RESSALVA_CONTRADICAO
    )
    telemetria = {
        "autocontradicao_removidos": removidos,
        "autocontradicao_ressalvados": ressalvados,
        "autocontradicao_pares_secao_tema": _pares_secao_tema_colididos(output),
    }
    if not alvos:
        return output, telemetria
    logger.warning(
        "parecer_autocontradicao_ponto_forte",
        extra={"workspace_id": workspace_id, **telemetria},
    )
    return output.model_copy(update={"pontos_fortes": pontos}), telemetria


__all__ = [
    "neutralize_autocontradicao",
    "piso_prescricao_divida",
]
