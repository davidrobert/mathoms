"""Anexa `property_id` UUID estável a imóveis do baseline consolidado (ADR-215 P2)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from itertools import combinations
from typing import TYPE_CHECKING, Optional

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.services.ancora_imovel_identidade import (
    chaves_da_ancora,
    comparar_unidades,
    e_chave_de_unidade,
    subcodigos_divergem,
    unidade_da_ancora,
    unidade_da_row,
)
from pipeline.domain.services.baseline_item_classifier import (
    ClassificationAuthority,
    subcodigo_imovel_rfb,
)
from pipeline.domain.services.endereco_canonicalizer import canonicalize
from pipeline.domain.services.titular_key_normalizer import normalize_titular_key
from pipeline.domain.types.property_identity import PropertyIdentityRecord, PropertyLookupKey

if TYPE_CHECKING:
    from pipeline.domain.types.config import FamilyMembersConfig
    from pipeline.ports import PropertyIdentityResolver


def enrich_imoveis_with_property_ids(
    consolidated: dict,
    resolver: "PropertyIdentityResolver",
    workspace_id: str,
    family_members: Optional["FamilyMembersConfig"] = None,
) -> dict:
    """Anexa `property_id`, `endereco_canonical`, `low_confidence` (ADR-215 P2)."""
    # ADR-215 fix-B3: family_members opcional permite normalizar
    # titular_key cross-IRPF (LLM extrai mariana_ribeiro_andrade vs
    # mariana_andrade_silva para a mesma pessoa). Quando ausente,
    # comportamento legado preservado.
    imoveis = consolidated.get("imoveis_consolidados", [])
    planos = [_triar(entry, family_members, resolver, workspace_id) for entry in imoveis]
    _resolver_ancorados([p for p in planos if p is not None], resolver, workspace_id)
    descartar_ancoras(consolidated)
    return consolidated


def _triar(
    entry: dict,
    # Ausente no CLI legado e em teste sem DB: titular_key segue cru (fix-B3).
    family_members: Optional["FamilyMembersConfig"],
    resolver,
    workspace_id: str,
) -> Optional["_Plano"]:
    """Item legado resolvido na hora; item ancorado volta para o plano em duas fases."""
    if not _eixo_atestado_por_fato(entry):
        _mark_eixo_por_hint(entry)
        return None
    lookup = _lookup_or_mark(entry, family_members)
    if lookup is None:
        return None
    if chaves_da_ancora(entry.get("ancora_imovel") or {}):
        return _Plano(entry, lookup)
    _resolver_pela_descricao(entry, lookup, resolver, workspace_id)
    return None


# [[ADR-440]] D3: matrícula e inscrição são quasi-identificadores, e o gate de PII da
# [[ADR-435]] casa rótulo+número na mesma string — não veria valor solto. A âncora serve
# só para montar a chave e sai do item antes de dedup, E5, view-model ou parecer.
def descartar_ancoras(consolidated: dict) -> None:
    """Remove `ancora_imovel` de todo imóvel; idempotente, e roda mesmo sem resolver."""
    for entry in consolidated.get("imoveis_consolidados") or []:
        entry.pop("ancora_imovel", None)


def _resolver_pela_descricao(entry: dict, lookup: PropertyLookupKey, resolver, workspace_id: str):
    """Item sem âncora: exatamente o caminho de antes da [[ADR-440]] (D5)."""
    record = resolver.match_or_create(
        workspace_id=workspace_id,
        lookup=lookup,
        first_seen_year=int(entry.get("ano_referencia") or 0),
        descricao_sample=entry.get("descricao") or "",
    )
    _apply_record(entry, record, lookup.endereco_canonical)


@dataclass
class _Plano:
    """Item ancorado no plano read-only, antes de cunhar ([[ADR-440]] D6/D7)."""

    entry: dict
    lookup: PropertyLookupKey
    escolhida: Optional[PropertyIdentityRecord] = None
    provada: bool = False
    perdedoras: tuple[str, ...] = ()
    motivo: Optional[str] = None

    @property
    def chaves(self) -> list[str]:
        return chaves_da_ancora(self.entry["ancora_imovel"])

    @property
    def unidade(self):
        return unidade_da_ancora(self.entry["ancora_imovel"])

    @property
    def descricao(self) -> str:
        return self.entry.get("descricao") or ""


@dataclass(frozen=True)
class _Candidata:
    record: PropertyIdentityRecord
    comparacao: Optional[bool]
    provada: bool
    vetada: bool


def _resolver_ancorados(planos: list[_Plano], resolver, workspace_id: str) -> None:
    """Plano read-only, posse por unidade e só então o mint: `_insert_row` commita na hora."""
    for plano in planos:
        _planejar(plano, resolver, workspace_id)
    for grupo in _grupos_por_row(planos):
        _decidir_posse(grupo)
    cunhados: dict[tuple[str, str], PropertyIdentityRecord] = {}
    for plano in planos:
        _executar(plano, planos, resolver, workspace_id, cunhados)


def _candidata(plano: _Plano, record: PropertyIdentityRecord) -> _Candidata:
    unidade_da_row_gravada = unidade_da_row(
        record.endereco_canonical or "", record.descricao_sample or ""
    )
    comparacao = comparar_unidades(plano.unidade, unidade_da_row_gravada)
    vetada = comparacao is False or subcodigos_divergem(plano.lookup.codigo_rfb, record.codigo_rfb)
    provada = comparacao is True or (record.descricao_sample or "") == plano.descricao
    return _Candidata(record=record, comparacao=comparacao, provada=provada, vetada=vetada)


def _candidatas(plano: _Plano, resolver, workspace_id: str) -> list[_Candidata]:
    vistas: dict[str, _Candidata] = {}
    for chave in plano.chaves:
        lookup = replace(plano.lookup, endereco_canonical=chave)
        record = resolver.match(workspace_id, lookup, plano.descricao)
        if record is not None and record.property_id not in vistas:
            vistas[record.property_id] = _candidata(plano, record)
    return list(vistas.values())


# Provada por unidade vence a só de endereço; no empate, a mais antiga — o first-write-wins
# que o resolver já aplica dentro de uma chave, estendido entre chaves.
def _prioridade(candidata: _Candidata) -> tuple:
    criada = candidata.record.created_at
    return (not candidata.provada, criada is None, criada.isoformat() if criada else "")


def _planejar(plano: _Plano, resolver, workspace_id: str) -> None:
    admissiveis = [c for c in _candidatas(plano, resolver, workspace_id) if not c.vetada]
    if not admissiveis:
        return
    ordem = sorted(admissiveis, key=lambda c: (*_prioridade(c), c.record.property_id))
    plano.escolhida, plano.provada = ordem[0].record, ordem[0].provada
    plano.perdedoras = tuple(c.record.property_id for c in ordem[1:])


def _grupos_por_row(planos: list[_Plano]) -> list[list[_Plano]]:
    grupos: dict[str, list[_Plano]] = defaultdict(list)
    for plano in planos:
        if plano.escolhida is not None:
            grupos[plano.escolhida.property_id].append(plano)
    return list(grupos.values())


def _ha_conflito(planos: list[_Plano]) -> bool:
    pares = combinations(planos, 2)
    return any(comparar_unidades(a.unidade, b.unidade) is False for a, b in pares)


# Mesma row, unidades que divergem: dois apartamentos do mesmo prédio que o via+nº juntou.
# Fica a partição que prova posse; sem prova, ninguém anexa — palpite de identidade some
# patrimônio no merge ([[ADR-392]]). Mesma unidade é o mesmo imóvel em anos diferentes.
def _decidir_posse(grupo: list[_Plano]) -> None:
    if not _ha_conflito(grupo):
        return
    donos = [p for p in grupo if p.provada]
    if not donos or _ha_conflito(donos):
        for plano in grupo:
            plano.escolhida, plano.motivo = None, "sem_posse"
        return
    for plano in grupo:
        if not plano.provada and _ha_conflito([plano, *donos]):
            plano.escolhida, plano.motivo = None, "posse_recusada"


def _via_univoca(plano: _Plano, via: str, planos: list[_Plano]) -> bool:
    outros = [o for o in planos if o is not plano and via in o.chaves]
    return all(comparar_unidades(plano.unidade, o.unidade) is not False for o in outros)


# Em via+nº a unidade recusada recolidiria com a dona a cada run; e imóvel novo cunha em
# via+nº quando ela é unívoca no run, porque apólice e informe de aluguel leem o canonical
# como endereço.
def _chave_de_mint(plano: _Plano, planos: list[_Plano]) -> Optional[str]:
    unidade = next((c for c in plano.chaves if e_chave_de_unidade(c)), None)
    via = next((c for c in plano.chaves if not e_chave_de_unidade(c)), None)
    if plano.motivo is None and via and _via_univoca(plano, via, planos):
        return via
    return unidade


# O plano já provou que nenhuma chave casa sem veto: cunhar por `match_or_create` re-rodaria
# a cascata, e o loose (que ignora o sub-código) devolveria a row que o veto recusou. O mapa
# do run é o que faz o mesmo imóvel em dois anos cair numa row só.
def _cunhar(plano: _Plano, chave: str, resolver, workspace_id: str, cunhados: dict):
    marca = (plano.lookup.codigo_rfb, chave)
    if marca not in cunhados:
        cunhados[marca] = resolver.create(
            workspace_id=workspace_id,
            lookup=replace(plano.lookup, endereco_canonical=chave),
            first_seen_year=int(plano.entry.get("ano_referencia") or 0),
            descricao_sample=plano.descricao,
        )
    return cunhados[marca]


def _executar(plano: _Plano, planos: list[_Plano], resolver, workspace_id: str, cunhados) -> None:
    if plano.escolhida is not None:
        _apply_record(plano.entry, plano.escolhida, plano.escolhida.endereco_canonical)
        _marcar_split(plano, planos)
        return
    chave = None if plano.motivo == "sem_posse" else _chave_de_mint(plano, planos)
    if chave is None:
        _marcar_sem_posse(plano.entry)
        return
    _apply_record(plano.entry, _cunhar(plano, chave, resolver, workspace_id, cunhados), chave)
    if plano.motivo == "posse_recusada":
        _razao_de_identidade(plano.entry, ReviewReasonCode.domain_property_identity_posse_recusada)


def _lookup_or_mark(
    entry: dict,
    # Ausente no CLI legado e em teste sem DB: titular_key segue cru (fix-B3).
    family_members: Optional["FamilyMembersConfig"],
) -> Optional[PropertyLookupKey]:
    """Chave de identidade do item, ou None com o item já marcado para revisão."""
    raw_titular = (entry.get("proprietario") or "").strip().lower()
    titular_key = normalize_titular_key(raw_titular, family_members)
    codigo_cru = (entry.get("codigo_rfb") or "").strip()
    if not titular_key or not codigo_cru:
        _mark_uncanonical(entry, None)
        return None
    codigo_rfb = subcodigo_imovel_rfb(codigo_cru)
    if codigo_rfb is None:
        _mark_codigo_invalido(entry, codigo_cru)
        return None
    return PropertyLookupKey(titular_key, codigo_rfb, canonicalize(entry.get("descricao") or ""))


# [[ADR-398]]: mintar é ato durável com CTA de rótulo — só o degrau de FATO da
# [[ADR-394]] D1 o autoriza. O eixo ATIVO só sai de `secao` ou de `hint`
# (`sinal` nunca promove a ativo, e o catálogo refina subtipo, nunca eixo), então
# a ausência de fato aqui significa exatamente "quem decidiu foi o rótulo do LLM".
_AUTORIDADE_DE_FATO = frozenset(
    {ClassificationAuthority.SECAO.value, ClassificationAuthority.CATALOGO.value}
)


# `secao` é OPCIONAL no contrato do E1.5a e 766 artefatos históricos não a
# carregam. Exigir o fato onde ele nunca existiu não fecharia o eixo: apagaria a
# identidade de todo imóvel do corpus antigo. A precondição vale onde a
# declaração provou saber emitir `secao` ([[ADR-398]] D2).
def _eixo_atestado_por_fato(entry: dict) -> bool:
    """Fato decidiu o eixo — ou a declaração de origem nunca ofereceu o fato."""
    if str(entry.get("eixo_autoridade") or "") in _AUTORIDADE_DE_FATO:
        return True
    return not entry.get("secao_disponivel")


def _mark_eixo_por_hint(entry: dict) -> None:
    """Sem fato de eixo não há identidade — nem `endereco_canonical`, que é chave de dedup."""
    entry["property_id"] = None
    entry["endereco_canonical"] = None
    entry["low_confidence"] = True
    entry["needs_review"] = True
    reasons = entry.setdefault("review_reasons", [])
    reasons.append(
        ReviewReason(
            code=ReviewReasonCode.domain_property_identity_eixo_por_hint,
            stage="consolidate_baseline",
            artifact_key="baseline_patrimonial",
            document_id=None,
            offending_value=f"eixo_autoridade={entry.get('eixo_autoridade') or 'ausente'}",
            expected="eixo ativo atestado por secao ou catalogo",
            message="identity not minted: axis decided by hint, not by fact",
        ).to_dict()
    )


def _mark_codigo_invalido(entry: dict, codigo_cru: str) -> None:
    """Sem sub-código de imóvel não há chave — nem `endereco_canonical`, que é chave de dedup."""
    entry["property_id"] = None
    entry["endereco_canonical"] = None
    entry["low_confidence"] = True
    entry["needs_review"] = True
    entry.setdefault("review_reasons", []).append(
        ReviewReason(
            code=ReviewReasonCode.domain_property_identity_codigo_invalido,
            stage="consolidate_baseline",
            artifact_key="baseline_patrimonial",
            document_id=None,
            offending_value=f"codigo_rfb={codigo_cru!r}",
            expected="sub-código de imóvel: 'CC' ou '01-CC'",
            message="identity not minted: codigo_rfb is not an imóvel sub-code",
        ).to_dict()
    )


def _apply_record(entry: dict, record, endereco_canonical: str | None) -> None:
    if record is None:
        _mark_uncanonical(entry, endereco_canonical)
        return
    entry["property_id"] = record.property_id
    entry["endereco_canonical"] = record.endereco_canonical
    entry["low_confidence"] = record.low_confidence
    # `low_confidence` sem razão é sinal que nenhum consumidor enxerga — e aqui ele
    # significa "identidade não canonicalizada", que é a chave de dedup cross-IRPF
    # ([[ADR-246]]): item que não canonicaliza ganha `property_id` novo a cada ano.
    # Paridade com `_mark_uncanonical`, que já emite o mesmo code.
    if record.low_confidence:
        _append_uncanonical_reason(entry, record.endereco_canonical)


def _mark_uncanonical(entry: dict, endereco_canonical: str | None) -> None:
    entry["property_id"] = None
    entry["endereco_canonical"] = endereco_canonical
    entry["low_confidence"] = True
    _append_uncanonical_reason(entry, endereco_canonical)


def _ja_tem_razao(reasons: list) -> bool:
    code = ReviewReasonCode.domain_property_identity_uncanonical.value
    return any(r.get("code") == code for r in reasons if isinstance(r, dict))


def _append_uncanonical_reason(entry: dict, endereco_canonical: str | None) -> None:
    """Marca revisão + razão. Único produtor da razão, para os 3 sítios não divergirem."""
    entry["needs_review"] = True
    reasons = entry.setdefault("review_reasons", [])
    if _ja_tem_razao(reasons):
        return
    reasons.append(
        ReviewReason(
            code=ReviewReasonCode.domain_property_identity_uncanonical,
            stage="consolidate_baseline",
            artifact_key="baseline_patrimonial",
            document_id=None,
            offending_value="endereco_canonical=None",
            expected="canonical or unique (titular, codigo_rfb)",
            message="identity not minted without endereco_canonical",
        ).to_dict()
    )


_TEXTOS_DA_RAZAO = {
    "domain.property_identity_posse_recusada": (
        "unidade da ficha diverge da dona da row",
        "unit differs from the row owner: minted its own identity at unit level",
    ),
    "domain.property_identity_sem_posse": (
        "uma partição de unidade provando posse da row",
        "identity not attached nor minted: no unit proves ownership of the shared row",
    ),
    "domain.property_identity_split": (
        "uma row viva por imóvel",
        "distinct live rows matched the same property; the best-proven won, the rest go to sweep",
    ),
}


def _razao_de_identidade(entry: dict, code: ReviewReasonCode, offending: str = "") -> None:
    """Razão PII-zero do enricher ancorado: só UUIDs e contagens no `offending_value`."""
    esperado, mensagem = _TEXTOS_DA_RAZAO[code.value]
    entry["needs_review"] = True
    entry.setdefault("review_reasons", []).append(
        ReviewReason(
            code=code,
            stage="consolidate_baseline",
            artifact_key="baseline_patrimonial",
            document_id=None,
            offending_value=offending or code.value,
            expected=esperado,
            message=mensagem,
        ).to_dict()
    )


def _marcar_sem_posse(entry: dict) -> None:
    """Sem posse provável não há chave — nem `endereco_canonical`, que o dedup usaria."""
    entry["property_id"] = None
    entry["endereco_canonical"] = None
    entry["low_confidence"] = True
    _razao_de_identidade(entry, ReviewReasonCode.domain_property_identity_sem_posse)


def _marcar_split(plano: _Plano, planos: list[_Plano]) -> None:
    reivindicadas = {p.escolhida.property_id for p in planos if p.escolhida is not None}
    soltas = [pid for pid in plano.perdedoras if pid not in reivindicadas]
    if soltas:
        offending = "property_ids=" + ",".join(soltas)
        _razao_de_identidade(
            plano.entry, ReviewReasonCode.domain_property_identity_split, offending
        )


__all__ = ["descartar_ancoras", "enrich_imoveis_with_property_ids"]
