"""União das evidências de cobertura de seguro (ADR-240 §Emenda 2026-08-08).

Duas fontes descrevem a mesma realidade: apólice **extraída de documento**
(stage ``extract_comprovantes_bens``) e apólice **cadastrada pelo cliente**
(aggregate ``Protection``, ADR-192). Decidir ausência olhando só uma delas
afirma falsamente algo sobre o dado do próprio cliente.

Predicados **existenciais** ("a categoria X está coberta?") são decididos aqui
sobre a união. Agregados **monetários** não são somados: as duas fontes não
compartilham chave de identidade (o cadastro não guarda ``apolice_numero``),
então unir arriscaria dupla-contagem — pior que omissão num KPI de dinheiro.
No lugar da soma, ``categorias_somente_no_cadastro`` deixa o consumidor
declarar o escopo do agregado e suprimir o veredito derivado dele.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Literal, Optional

from pipeline.domain.protection_bundle import ProtectionItem
from pipeline.domain.services.premio_decomposicao import coberturas_pessoa

OrigemCobertura = Literal["documento", "cadastro"]

# Vocabulário canônico = o de ``gap_qualitativo.categoria`` (ADR-240 D3 KPI F).
# Só entram pares em que os dois lados descrevem o MESMO produto. `acidentes`
# (documento) e `invalidez` / `patrimonial` / `rc_profissional` / `sucessorio`
# (cadastro) ficam de fora de propósito: mapeá-los por semelhança faria uma
# apólice de acidentes pessoais silenciar o gap de vida — cobertura fabricada.
_COBERTURA_DOCUMENTO: dict[str, str] = {"vida": "vida", "saude": "saude"}
_CATEGORIA_CADASTRO: dict[str, str] = {"vida": "vida", "saude": "saude"}

_STATUS_CADASTRO_ATIVO = "Ativa"


@dataclass(frozen=True)
class EvidenciaCobertura:
    """Uma categoria coberta, com a fonte que a sustenta."""

    categoria: str
    origem: OrigemCobertura


@dataclass(frozen=True)
class CoberturaConsolidada:
    """Documento ∪ cadastro, com proveniência por categoria."""

    evidencias: tuple[EvidenciaCobertura, ...] = ()
    cadastro_fora_do_vocabulario: frozenset[str] = field(default_factory=frozenset)

    def tem_cobertura(self, categoria: str) -> bool:
        """True quando **qualquer** fonte cobre a categoria."""
        return any(e.categoria == categoria for e in self.evidencias)

    def origens(self, categoria: str) -> frozenset[str]:
        return frozenset(e.origem for e in self.evidencias if e.categoria == categoria)

    def categorias_somente_no_cadastro(self) -> frozenset[str]:
        """Cobertura conhecida que os documentos analisados não contêm."""
        so_cadastro = {
            e.categoria for e in self.evidencias if self.origens(e.categoria) == {"cadastro"}
        }
        return frozenset(so_cadastro | self.cadastro_fora_do_vocabulario)

    def premio_documental_e_completo(self) -> bool:
        """False quando há cobertura fora do escopo somado em KPI G / KPI B."""
        return not self.categorias_somente_no_cadastro()


def _parse_date(value) -> Optional[date]:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and len(value) >= 10:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _categorias_de_documento(apolices_vigentes: Iterable[dict]) -> set[str]:
    return {
        _COBERTURA_DOCUMENTO[tipo]
        for apolice in apolices_vigentes
        for cov in coberturas_pessoa(apolice)
        if (tipo := cov.get("tipo")) in _COBERTURA_DOCUMENTO
    }


def _cobre_em(item: ProtectionItem, ref: date) -> bool:
    """Cadastro ativo e vigente em ``ref`` — apólice vencida não fecha gap."""
    if item.get("status") != _STATUS_CADASTRO_ATIVO:
        return False
    inicio = _parse_date(item.get("starts_at"))
    if inicio is not None and inicio > ref:
        return False
    fim = _parse_date(item.get("ends_at"))
    return fim is None or fim >= ref


def _classifica_cadastro(item: ProtectionItem) -> tuple[Optional[str], str]:
    """``(categoria canônica | None, categoria crua)`` de um item de cadastro."""
    crua = str(item.get("category") or "")
    return _CATEGORIA_CADASTRO.get(crua), crua


def _categorias_de_cadastro(
    itens: Iterable[ProtectionItem], ref: date
) -> tuple[set[str], set[str]]:
    """``(categorias canônicas, categorias ativas fora do vocabulário)``."""
    classificadas = [_classifica_cadastro(i) for i in itens if _cobre_em(i, ref)]
    canonicas = {alvo for alvo, _ in classificadas if alvo is not None}
    fora = {crua for alvo, crua in classificadas if alvo is None and crua}
    return canonicas, fora


def consolidar_cobertura(
    apolices_vigentes: Iterable[dict],
    cadastro: Iterable[ProtectionItem],
    reference_date: date,
) -> CoberturaConsolidada:
    """Consolida as duas fontes de evidência de cobertura."""
    do_documento = _categorias_de_documento(apolices_vigentes)
    do_cadastro, fora = _categorias_de_cadastro(cadastro, reference_date)
    evidencias = tuple(
        EvidenciaCobertura(categoria, origem)
        for origem, categorias in (("documento", do_documento), ("cadastro", do_cadastro))
        for categoria in sorted(categorias)
    )
    return CoberturaConsolidada(
        evidencias=evidencias,
        cadastro_fora_do_vocabulario=frozenset(fora),
    )
