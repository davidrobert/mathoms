"""Dois valores para a mesma grandeza na mesma seção reprovam o ITEM (A40.l120).

Medido no run `40d1af2a`: a prosa da S1 dizia que a renda fixa era **90,25%** enquanto a
métrica carimbada dizia **94,39%** — 4,15 pp lado a lado, sem nada reconciliando. O
detector monetário existente (``parecer_prose_money``) é ancorado em ``R$`` por construção
e não vê percentual; e ele mede PRESENÇA, não divergência.

**A tolerância não é escolhida — é derivada da precisão que o modelo escreveu.** É a
semântica que ``MoneyToken.half_step_cents`` projeta e nunca exerceu: "94%" declara meio
ponto de folga, "90,25%" declara meio centésimo. Assim arredondamento legítimo ("cerca de
90%") passa **porque o modelo declarou a precisão**, e número contraditório reprova. Zero
absoluto reprovaria boa escrita que a persona pede; banda fixa em pp seria doutrina
inventada, que é o que a [[ADR-419]] proíbe.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterator, Mapping, Optional, Sequence

# Número seguido de `%`. Captura a grafia para derivar a precisão — é ela, e não uma
# constante, que vira a tolerância.
_PCT_RE = re.compile(r"(\d{1,3}(?:[.,]\d{1,3})?)\s*%")

# Unidades cujo valor a prosa escreve como percentual. `meses`, `ano` e `ratio_0_1` ficam
# FORA: comparar meio-passo de pp contra "6 meses" ou contra o ano de IF fabrica falso
# positivo, e `protecao_custo_premio` guarda razão 0–1 — o erro de 100× que a
# `kpi_orfaos_dominio` já documenta.
_UNIDADES_EM_PONTO_PERCENTUAL = frozenset({"pct", "pct_aa"})

# Atribuição: o percentual tem de estar na MESMA CLÁUSULA da menção da grandeza, e só o
# mais próximo dela conta. Sem isso o gate dispara em todo percentual de um campo que
# mencione o termo — medido no run `40d1af2a`: 11 disparos, dos quais 7 eram outra coisa
# (as demais linhas da tabela de classes, e um LIMIAR de meta lido como afirmação).
#
# A janela é medida, não escolhida: no corpus, verdadeiro-positivo cai em **13-37** chars
# da menção e falso-positivo em **48-307**. O corte a 40 fica dentro do vão, e o vão é o
# que justifica o número — se ele fechar, o critério é revisto, não o número afrouxado.
_JANELA_MESMA_CLAUSULA = 40
_FIM_DE_CLAUSULA = re.compile(r"[.;·]")


# Termo canônico da grandeza, por chave. Não é vocabulário livre: cada termo tem de ser
# SUBSTRING do `rotulo` do catálogo (gateado em teste), então renomear a grandeza lá quebra
# aqui em vez de deixar o gate silenciosamente sem alcance. Só entram unidades em ponto
# percentual — as outras três estão fora por construção, não por esquecimento.
TERMOS_POR_METRICA: Mapping[str, tuple[str, ...]] = {
    "alocacao_renda_fixa": ("renda fixa",),
    "concentracao_imobiliaria": ("concentração imobiliária",),
    "exposicao_cambial": ("exposição cambial",),
    "taxa_endividamento": ("endividamento",),
    "taxa_poupanca_recorrente": ("poupança recorrente",),
    "despesas_nao_categorizadas": ("despesas não identificadas",),
    "aliquota_efetiva_ir": ("alíquota efetiva",),
    "renda_passiva_cobertura": ("renda passiva",),
    "if_progresso": ("independência financeira",),
    "imobilizacao_patrimonial": ("imobilização patrimonial",),
    "carteira_trs": ("rentabilidade da carteira",),
}


@dataclass(frozen=True)
class Divergencia:
    """PII-safe: nomeia a grandeza e a seção, nunca o texto da prosa."""

    metrica_key: str
    section_id: str
    campo: str
    valor_prosa: str
    valor_carimbado: str
    spread: str


def _normaliza(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def _meio_passo(grafia: str) -> Decimal:
    """Meia unidade da última casa escrita: "94" → 0,5 · "90,25" → 0,005."""
    _inteiro, _sep, decimais = grafia.replace(".", ",").partition(",")
    return Decimal(5) / (Decimal(10) ** (len(decimais) + 1))


def _percentuais(texto: str) -> Iterator[tuple[Decimal, str]]:
    for grafia in _PCT_RE.findall(texto):
        yield Decimal(grafia.replace(".", ",").replace(",", ".")), grafia


def _valor_carimbado(valor_atual: Optional[str] = None) -> Optional[Decimal]:
    if not valor_atual:
        return None
    achado = _PCT_RE.search(valor_atual)
    if not achado:
        return None
    return Decimal(achado.group(1).replace(".", ",").replace(",", "."))


def divergencias_de_item(
    *,
    campos: Mapping[str, Optional[str]],
    section_id: str,
    metricas: Sequence,
    kpi_targets: Mapping[str, Mapping],
    termos: Mapping[str, Sequence[str]] = TERMOS_POR_METRICA,
) -> list[Divergencia]:
    """Percentual da prosa que contradiz métrica carimbada da MESMA seção."""
    # Atribuição conservadora de propósito: falso negativo é aceitável, falso positivo
    # mata o gate por ruído.
    fora: list[Divergencia] = []
    for metrica in metricas:
        alvo = _carimbo_comparavel(metrica, section_id, kpi_targets)
        if alvo is not None:
            chaves = termos.get(metrica.metrica_key) or ()
            fora.extend(_confronta(campos, metrica, alvo, chaves, section_id))
    return fora


def _carimbo_comparavel(metrica, section_id: str, kpi_targets: Mapping) -> Optional[Decimal]:
    """A unidade vem do CATÁLOGO, não do output do LLM — `Metrica` não a carrega."""
    if metrica.section_id != section_id:
        return None
    alvo = kpi_targets.get(metrica.metrica_key) or {}
    if alvo.get("unidade") not in _UNIDADES_EM_PONTO_PERCENTUAL:
        return None
    return _valor_carimbado(getattr(metrica, "valor_atual", None))


def _confronta(campos, metrica, alvo: Decimal, chaves, section_id: str):
    for campo, texto in campos.items():
        achado = _percentual_atribuivel(texto, chaves) if texto else None
        if achado is None:
            continue
        valor, grafia = achado
        if abs(valor - alvo) <= _meio_passo(grafia):
            continue
        yield Divergencia(
            metrica_key=metrica.metrica_key,
            section_id=section_id,
            campo=campo,
            valor_prosa=grafia,
            valor_carimbado=str(alvo),
            spread=str(abs(valor - alvo)),
        )


def _percentual_atribuivel(texto: str, chaves: Sequence[str]) -> Optional[tuple[Decimal, str]]:
    """O percentual mais próximo da menção, na mesma cláusula. `None` = nada atribuível."""
    normalizado = _normaliza(texto)
    mencoes = [normalizado.find(_normaliza(c)) for c in chaves]
    mencoes = [m for m in mencoes if m >= 0]
    if not mencoes:
        return None
    candidatos = [
        (min(abs(m.start() - pos) for pos in mencoes), m)
        for m in _PCT_RE.finditer(texto)
        if _mesma_clausula(texto, m, mencoes)
    ]
    if not candidatos:
        return None
    distancia, achado = min(candidatos, key=lambda par: par[0])
    if distancia > _JANELA_MESMA_CLAUSULA:
        return None
    grafia = achado.group(1)
    return Decimal(grafia.replace(".", ",").replace(",", ".")), grafia


def _mesma_clausula(texto: str, achado: re.Match, mencoes: Sequence[int]) -> bool:
    for pos in mencoes:
        ini, fim = sorted((pos, achado.start()))
        if not _FIM_DE_CLAUSULA.search(texto, ini, fim):
            return True
    return False


_CAMPOS_DE_PROSA = ("descricao", "evidencia", "acao", "impacto_qualitativo", "titulo")


def _campos(item) -> dict:
    return {c: getattr(item, c, None) for c in _CAMPOS_DE_PROSA}


def divergencias_do_output(output, kpi_targets: Mapping[str, Mapping]) -> list[Divergencia]:
    """Varre riscos, sugestões e pontos fortes contra as métricas carimbadas."""
    fora: list[Divergencia] = []
    for campo in ("riscos", "pontos_fortes", *_HORIZONTES):
        for item in getattr(output, campo, None) or []:
            fora.extend(
                divergencias_de_item(
                    campos=_campos(item),
                    section_id=item.section_id,
                    metricas=output.metricas,
                    kpi_targets=kpi_targets,
                )
            )
    return fora


def rebaixa_por_divergencia(output, kpi_targets: Mapping[str, Mapping]):
    """``(output, divergências)`` — rebaixa o ITEM, nunca reprova o parecer inteiro."""
    # Reask está fechado ([[ADR-292]]: 4 reasks/geração, ~243s), e derrubar o parecer por
    # um percentual contraditório trocaria um número errado por nenhum parecer.
    encontradas = divergencias_do_output(output, kpi_targets)
    if not encontradas:
        return output, []
    marcados = {(d.section_id, d.metrica_key) for d in encontradas}
    update = {
        campo: [_rebaixa(i, marcados) for i in getattr(output, campo, None) or []]
        for campo in ("riscos", *_HORIZONTES)
    }
    return output.model_copy(update=update), encontradas


def _rebaixa(item, marcados):
    if item.confianca != "alta":
        return item
    if not any(sec == item.section_id for sec, _ in marcados):
        return item
    campos = {"confianca": "media"}
    if hasattr(item, "impacto_estimado"):
        campos["impacto_estimado"] = None
    return item.model_copy(update=campos)


_HORIZONTES = ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")

__all__ = [
    "Divergencia",
    "TERMOS_POR_METRICA",
    "divergencias_de_item",
    "divergencias_do_output",
    "rebaixa_por_divergencia",
]
