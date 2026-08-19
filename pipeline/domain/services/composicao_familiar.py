"""Cadastro civil do domicílio projetado no E5 (PE-3 · r7).

Domínio distinto de ``$.irpf_kpis.dependentes``, que é a contagem FISCAL do
ano-base declarado. Sem o lado civil, o parecer emitia os dois fatos da mesma
família sem reconciliar — um risco Crítico com confiança alta apoiado em
dependentes menores e, onze itens abaixo, uma oportunidade fiscal com confiança
baixa "dependendo da composição familiar real".

PII é garantia estrutural deste módulo, não de sanitizer a jusante: o
``_scrub_node`` do contexto troca nome por papel e rasga CPF/CNPJ, mas uma data
ISO passa intacta — não há padrão de data de nascimento. Por isso a derivação
mora aqui e o sub-schema E5 fecha com ``additionalProperties: false``.
"""

from __future__ import annotations

from typing import Any, Iterable

FONTE = "cadastro_familia"

FAIXAS_ETARIAS = ("0-17", "18-21", "22-24", "25-59", "60+", "desconhecida")

# Fronteiras de decisão fiscal, não faixas cosméticas: 18 (maioridade civil),
# 21 (limite de filho/enteado dependente), 24 (limite estendido para ensino
# superior ou técnico) e 60. Base: Lei 9.250/95 art. 35; RIR/2018 art. 71 §1º;
# IN RFB 1.500/2014 art. 90. Irmão/neto/bisneto sob guarda judicial e menor
# pobre reusam os mesmos 21 e 24 — nenhuma banda extra. Trocar um corte é
# breaking no schema E5, então o vocabulário existe só aqui.
_LIMITES = ((18, "0-17"), (22, "18-21"), (25, "22-24"), (60, "25-59"))

PAPEIS = ("titular", "conjuge", "filho", "enteado", "ascendente", "outro_dependente")
_PAPEL_FALLBACK = "outro_dependente"


def _faixa(idade: int | None) -> str:
    """``desconhecida`` é membro do enum por necessidade: sem data de nascimento
    o snapshot devolve ``None``, e omitir o membro o tornaria invisível."""
    if idade is None or idade < 0:
        return "desconhecida"
    for limite, faixa in _LIMITES:
        if idade < limite:
            return faixa
    return "60+"


def _papel_normalizado(parentesco: Any) -> str:
    """Valor fora do vocabulário vira ``outro_dependente``. É requisito de PII e
    não estilo: ``family_members`` é editável pelo dono e carrega texto livre."""
    papel = str(parentesco or "").strip().casefold()
    return papel if papel in PAPEIS else _PAPEL_FALLBACK


def _membro(snapshot: Any) -> dict[str, str]:
    return {
        "papel": _papel_normalizado(snapshot.parentesco),
        "faixa_etaria": _faixa(snapshot.idade),
    }


# ``faixa_ref`` é 31/12 do ano-calendário do IRPF sob reconciliação, não a data
# do run: quem completou 22 (ou 25) entre 1º de janeiro e o dia do run apareceria
# fora da faixa que decidiu a elegibilidade do ano declarado (ADR-397 D3).
def build_composicao_familiar(snapshots: Iterable[Any], *, faixa_ref: str) -> dict[str, Any] | None:
    """Papel + faixa etária cortada em ``faixa_ref``. ``None`` sem membros."""
    membros = [_membro(s) for s in snapshots]
    if not membros:
        return None
    # A ordem decide quem sobrevive ao ``max_chars`` do bloco no exec context: o
    # corte é no fim, e a ordem de PAPEIS deixa por último justamente ascendente
    # e outro_dependente, que não sustentam achado de subdeclaração. Ordenação
    # estável — dentro do mesmo papel vale a ordem do cadastro.
    membros.sort(key=lambda m: PAPEIS.index(m["papel"]))
    return {"faixa_ref": faixa_ref, "fonte": FONTE, "membros": membros}


__all__ = ["FAIXAS_ETARIAS", "FONTE", "PAPEIS", "build_composicao_familiar"]
