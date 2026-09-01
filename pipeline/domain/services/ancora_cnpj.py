"""Âncora de identidade de investimento — o CNPJ lido do documento ([[ADR-271]] §147).

A raiz (8 primeiros dígitos) identifica a instituição e **sobrevive a rename de
descrição**, que é a classe de instabilidade que a [[A42.l15]] mediu: 37,68% de
estabilidade do `investment_id` entre extrações do mesmo documento.

Duas fontes, nesta ordem, e a segunda é o que dispensa política de era: o campo
`cnpj_emissor` que o E1.5 passou a emitir em `PROMPT_VERSION` 1.4.0, e — quando ele
não existe — o CNPJ que **já está no texto** da `descricao`. As duas dão a mesma raiz,
então item de era antiga e item de era nova colidem no mesmo hash e o bump não deixa
o corpus órfão (a re-extração automática está fora de escopo pela [[ADR-311]] D3).

Ler CNPJ declarado **não é** persistir palpite: a [[ADR-271]] §140 rejeitou identidade
fuzzy-derivada, e aqui não há fuzz — é um padrão exato de 14 dígitos, computado no
momento da chave e nunca gravado como identidade. E o catálogo não entra: a chave usa a
raiz do DOCUMENTO, nunca o code do `institution_catalog`, senão um renome lá moveria o
hash ([[ADR-400]] §1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# `(?<!\d)`/`(?!\d)` impedem casar 14 dígitos DENTRO de um número maior; os separadores
# são opcionais porque a transcrição do IRPF ora mascara, ora não.
_CNPJ_NO_TEXTO = re.compile(
    r"(?<!\d)(\d{2})[.\s]?(\d{3})[.\s]?(\d{3})[/\s]?(\d{4})[-\s]?(\d{2})(?!\d)"
)
_NAO_DIGITO = re.compile(r"\D")
TAMANHO_RAIZ = 8


def raiz_de_cnpj(cnpj: str | None) -> str | None:
    """14 dígitos → a raiz de 8 que identifica a instituição; qualquer outra coisa → ``None``."""
    if not cnpj:
        return None
    digitos = _NAO_DIGITO.sub("", str(cnpj))
    return digitos[:TAMANHO_RAIZ] if len(digitos) == 14 else None


def raiz_no_texto(texto: str | None) -> str | None:
    """Primeira raiz de CNPJ que aparece no texto livre; ``None`` quando não há."""
    achado = _CNPJ_NO_TEXTO.search(texto or "")
    return "".join(achado.groups())[:TAMANHO_RAIZ] if achado else None


def ancora_da_entrada(entrada: dict) -> str | None:
    """Raiz do CNPJ da entrada: campo declarado ⊳ texto da descrição; ``None`` = sem âncora."""
    return raiz_de_cnpj(entrada.get("cnpj_emissor")) or raiz_no_texto(entrada.get("descricao"))


@dataclass(frozen=True)
class CoberturaAncora:
    """Quantos itens alcançaram cada degrau — publicado, não em voo ([[ADR-406]])."""

    # A cobertura VAI para o artefato porque perna forte sem produtor é inerte e
    # invisível: `dividas_dedup.numero_contrato` nasceu assim e ninguém viu por meses
    # ([[A40.l88]]). Um número publicado em 0% é o sinal que faltava.
    total: int = 0
    com_ancora: int = 0
    por_descricao: int = 0
    sem_identidade: int = 0

    @property
    def pct_ancora(self) -> float:
        return round(100.0 * self.com_ancora / self.total, 2) if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "com_ancora": self.com_ancora,
            "por_descricao": self.por_descricao,
            "sem_identidade": self.sem_identidade,
            "pct_ancora": self.pct_ancora,
        }


def medir_cobertura(entradas: list[dict] | None) -> CoberturaAncora:
    """Conta os degraus sobre as entradas ANTES do dedup — o denominador é o item, não o grupo."""
    itens = entradas or []
    com = sum(1 for e in itens if ancora_da_entrada(e))
    sem_desc = sum(
        1 for e in itens if not ancora_da_entrada(e) and not (e.get("descricao") or "").strip()
    )
    return CoberturaAncora(
        total=len(itens),
        com_ancora=com,
        por_descricao=len(itens) - com - sem_desc,
        sem_identidade=sem_desc,
    )
