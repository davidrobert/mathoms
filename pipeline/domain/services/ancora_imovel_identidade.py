"""Chave por nível e unidade a partir da âncora da ficha de imóvel ([[ADR-440]] D5/D6)."""

# via+nº é chave de PRÉDIO: dois apartamentos do mesmo prédio dão a mesma. Quem separa
# unidade é matrícula > inscrição municipal > complemento, comparados no primeiro nível
# com valor nos dois lados — o mesmo critério para a âncora e para a row gravada.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pipeline.domain.services.baseline_item_classifier import subcodigo_imovel_rfb
from pipeline.domain.services.canonical_fuzzy_match import extract_complemento
from pipeline.domain.services.endereco_canonicalizer import canonical_do_nivel
from pipeline.domain.services.imoveis_dedup import SPECIFIC_CODIGOS_RFB

_NIVEIS_DA_UNIDADE = ("matricula", "inscricao", "complemento")


@dataclass(frozen=True)
class Unidade:
    """Discriminador de unidade já normalizado (dígitos da matrícula/inscrição, complemento)."""

    matricula: Optional[str] = None
    inscricao: Optional[str] = None
    complemento: Optional[str] = None


def _rotulado(rotulo: str, valor: object) -> Optional[str]:
    return f"{rotulo} {valor}" if valor else None


def _texto_via(ancora: dict) -> Optional[str]:
    logradouro, numero = ancora.get("logradouro"), ancora.get("numero")
    return f"{logradouro}, {numero}" if logradouro and numero else None


def chaves_da_ancora(ancora: dict) -> list[str]:
    """Uma chave por nível, na ordem da cascata, byte-igual ao que `canonicalize` grava."""
    textos = (
        ("via_numero", _texto_via(ancora)),
        ("mat", _rotulado("matricula", ancora.get("matricula"))),
        ("iptu", _rotulado("iptu", ancora.get("inscricao_municipal"))),
    )
    chaves = [canonical_do_nivel(texto, nivel) for nivel, texto in textos if texto]
    return list(dict.fromkeys(c for c in chaves if c))


def e_chave_de_unidade(chave: str) -> bool:
    return chave.startswith(("mat:", "iptu:"))


def _sem_prefixo(chave: str, prefixo: str) -> Optional[str]:
    return chave[len(prefixo) :] if chave.startswith(prefixo) else None


def _digitos(nivel: str, texto: str) -> Optional[str]:
    return _sem_prefixo(canonical_do_nivel(texto, nivel) or "", f"{nivel}:") if texto else None


def unidade_da_ancora(ancora: dict) -> Unidade:
    return Unidade(
        matricula=_digitos("mat", _rotulado("matricula", ancora.get("matricula")) or ""),
        inscricao=_digitos("iptu", _rotulado("iptu", ancora.get("inscricao_municipal")) or ""),
        complemento=extract_complemento(ancora.get("complemento")),
    )


def unidade_da_row(endereco_canonical: str, descricao_sample: str) -> Unidade:
    """O lado da row: o próprio `mat:`/`iptu:` gravado, ou a amostra lida pelos mesmos extractors."""
    return Unidade(
        matricula=_sem_prefixo(endereco_canonical, "mat:") or _digitos("mat", descricao_sample),
        inscricao=_sem_prefixo(endereco_canonical, "iptu:") or _digitos("iptu", descricao_sample),
        complemento=extract_complemento(descricao_sample),
    )


def comparar_unidades(a: Unidade, b: Unidade) -> Optional[bool]:
    """No 1º nível com valor nos dois lados: True se iguais, False se divergem; None sem nível comum."""
    for campo in _NIVEIS_DA_UNIDADE:
        valor_a, valor_b = getattr(a, campo), getattr(b, campo)
        if valor_a and valor_b:
            return valor_a == valor_b
    return None


def subcodigos_divergem(codigo_a: str, codigo_b: str) -> bool:
    """Casa (12) e apartamento (11) não são o mesmo imóvel, mesmo com o mesmo endereço."""
    a, b = subcodigo_imovel_rfb(codigo_a), subcodigo_imovel_rfb(codigo_b)
    return a != b and a in SPECIFIC_CODIGOS_RFB and b in SPECIFIC_CODIGOS_RFB


__all__ = [
    "Unidade",
    "chaves_da_ancora",
    "comparar_unidades",
    "e_chave_de_unidade",
    "subcodigos_divergem",
    "unidade_da_ancora",
    "unidade_da_row",
]
