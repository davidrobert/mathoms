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
# SEM `section_id` no match — A40.l116. O alvo já esteve em S4 e em S1; medido sobre 14 runs
# do mesmo corpus, o modelo rotula o item de liquidez com **S3 (9 runs) ou S4 (5)**, e com
# **S1 em zero**. `section_id` não é propriedade do objeto: é rótulo re-sorteado a cada run,
# então nenhum literal sobrevive — e derivar do layout é a PIOR escolha, porque o bloco da
# reserva (`saude_balanco`) é `aligned_with_layout: "S1"`, o valor 0/14. O que identifica o
# objeto é `tema_canonico` + o sinal do E5. O #1800 (A40.l80) trocou S4→S1 por acreditar que
# "seção que o manifest não projeta é seção que o modelo não rotula": refutado na mesma
# medição — o modelo emite S4, S_parecer, S_IRPF_RENDA e S_IRPF_OTIMIZACAO, nenhuma projetada.
_TEMA_LIQUIDEZ = "Liquidez"
_FONTE_E5 = "e5_reserva_excessiva"
_FONTE_RISCO = "risco_de_liquidez"


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
    return {i for i, p in enumerate(output.pontos_fortes) if p.tema_canonico == _TEMA_LIQUIDEZ}


def _risco_de_liquidez(output: ParecerPlanejadorOutput) -> bool:
    """Braço elogio × alerta: o parecer se contradiz sem depender do E5 falar."""
    return any(r.tema_canonico == _TEMA_LIQUIDEZ for r in output.riscos)


def _fonte_da_contradicao(
    output: ParecerPlanejadorOutput, e5_data: Mapping[str, Any]
) -> str | None:
    """Qual árbitro viu a contradição — o E5 tem precedência sobre o próprio parecer."""
    if _liquidez_excessiva(e5_data):
        return _FONTE_E5
    return _FONTE_RISCO if _risco_de_liquidez(output) else None


# `tema_canonico` é OPCIONAL em `PontoForte` (obrigatório em `Risco`), então um elogio à
# reserva com o campo nulo escapa dos dois braços. Medido: 0 em 64 pontos fortes de 14 runs
# — buraco de CONTRATO, não observado. Fica contado até haver caso; torná-lo obrigatório no
# schema agora empurraria o output para reask, e o custo disso já foi pago na [[ADR-292]].
def _pontos_sem_tema(output: ParecerPlanejadorOutput) -> int:
    return sum(1 for p in output.pontos_fortes if p.tema_canonico is None)


def _telemetria_autocontradicao(
    output: ParecerPlanejadorOutput, fonte: str | None, removidos: int, ressalvados: int
) -> dict:
    return {
        "autocontradicao_removidos": removidos,
        "autocontradicao_ressalvados": ressalvados,
        "autocontradicao_pares_secao_tema": _pares_secao_tema_colididos(output),
        "autocontradicao_fonte": fonte,
        "autocontradicao_tema_ausente": _pontos_sem_tema(output) if fonte else 0,
    }


# Dois braços, ambos ancorados no ASSUNTO (`tema_canonico`), nunca no balde `(seção, tema)`.
# O que os separa é QUEM arbitra, e é isso que decide o desfecho de cada um:
#   (a) o E5 declara a reserva excessiva — árbitro determinístico, contradição sobre o MESMO
#       objeto medido (R2) ⇒ REMOVE (o piso de 3 degrada para ressalva quando amarra);
#   (b) o próprio parecer levanta a liquidez como risco — árbitro é o LLM julgando o LLM
#       ⇒ RESSALVA, nunca remove. Foi deletar sobre rótulo do modelo que derrubou a R1 no
#       r7, e escopar a "Liquidez" estreita o balde sem mudar a natureza do sinal. Pior: (b)
#       só dispara quando o E5 CALA, isto é, quando a reserva não é excessiva — exatamente
#       onde o elogio tem mais chance de ser sobre outro objeto (carteira líquida, ausência
#       de imobilizado). A ressalva é verdadeira nos dois mundos e custa zero; a deleção
#       custaria o ponto forte mais sólido no mundo falso-positivo.
# Medido no corpus, (b) é redundante — o E5 disse "Excessiva" em 10/10 runs; ele existe para
# fechar o buraco em que o E5 não diz.
def neutralize_autocontradicao(
    output: ParecerPlanejadorOutput, e5_data: Mapping[str, Any], workspace_id: str
) -> tuple[ParecerPlanejadorOutput, dict]:
    """Neutraliza ponto forte de liquidez que o E5 ou o próprio parecer contradiz."""
    fonte = _fonte_da_contradicao(output, e5_data)
    alvos = _pontos_de_liquidez(output) if fonte else set()
    pontos, removidos, ressalvados = aplicar_piso_pontos_fortes(
        list(output.pontos_fortes),
        sorted(alvos),
        _RESSALVA_CONTRADICAO,
        remover=fonte == _FONTE_E5,
    )
    telemetria = _telemetria_autocontradicao(output, fonte, removidos, ressalvados)
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
