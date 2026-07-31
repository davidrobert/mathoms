#!/usr/bin/env python3
"""Duplicação ENTRE grupos-fonte do E4 (camada B, [[ADR-354]]) — reporta, não dedupa.

O render do bloco vive em ``dev.ledger_cross_group_render`` (teto de 500 linhas do
CLAUDE.md); a detecção não importa o render, então a dependência é um DAG."""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from decimal import InvalidOperation
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Direction vem do BALDE, não do item E4: o ``abs`` da despesa destrói o sinal (mesma
# regra do read-path em backend/app/services/transaction_service.py:51-54). UM mapping
# serve de filtro de balde E de fonte de direction — não podem driftar.
_TX_BUCKET_DIRECTION: dict[str, str] = {"despesas": "debit", "receitas": "credit"}
_PROVENANCE_FIELDS: tuple[str, str, str] = ("banco", "titular", "tipo_conta")
# Vocabulário fechado (institution_catalog / doc-types): os VALORES podem sair, e o
# MESMO relatório já os imprime na unit de grupo E3. ``titular`` nunca — só fill-state.
_CLOSED_VOCAB_FIELDS: tuple[str, str] = ("banco", "tipo_conta")
_SHAPE_FIELDS: tuple[str, ...] = (*_CLOSED_VOCAB_FIELDS, "titular")
_EMPTY_VALUE = "(vazio)"
_PREENCHIDO, _PARCIAL, _VAZIO = "preenchido", "parcial", "vazio"
_FILL_STATES: tuple[str, ...] = (_PREENCHIDO, _PARCIAL, _VAZIO)
# Shapes declarados legítimos, no eixo de VALOR (ver ``_explained_shape``). VAZIO por
# decisão (A40.l1). Entrada nova exige ADR/decisão citada + fixture que prove a classe
# + diff no PR, e passa por ``validate_explained``. Por OCORRÊNCIA é proibida (Goodhart).
EXPLAINED_DIVERGENCE: frozenset[str] = frozenset()
# Carrier 1 da [[ADR-354]] é QUALQUER divergência de ``tipo_conta`` entre as pernas — mais
# largo que o par variante que motivou a ADR ('extrato' vs 'extratoconta'): distinguir
# variante-de-vocabulário de tipo REALMENTE distinto exige o alias-map versionado da
# [[A40.l2]]. Sob [[ADR-342]] o instrumento erra para SOBRE-detecção. Carrier 2 é
# assimetria de fill. Os dois entram na definição ÚNICA de ``carrier_signatures``.
_VOCAB_CARRIER_FIELD = "tipo_conta"
# Sufixos curtos: o valor de ``carriers=`` fica ao lado de campos ``key=value`` no render,
# então não pode embutir ``=``, espaço nem ``+``. A glosa longa sai uma vez, no render.
_CARRIER_1, _CARRIER_2 = "c1", "c2"


def _tag_fields(tag: str) -> frozenset[str]:
    """Nomes de campo de uma tag ``a+b`` (``divergence`` / ``parciais``)."""
    return frozenset(tag.split("+")) if tag else frozenset()


def carrier_signatures(divergentes: frozenset[str], parciais: frozenset[str]) -> tuple[str, ...]:
    """Assinaturas de carrier [[ADR-354]] presentes — definição ÚNICA, consumida pela
    partição do relatório E pelo validador de whitelist."""
    # Duas leituras divergentes de "carrier" no mesmo módulo (partição só via fill
    # parcial, validador também via tipo_conta) deixavam o carrier 1 fora da partição.
    fill = tuple(f"{name}:{_CARRIER_2}" for name in sorted(parciais))
    if _VOCAB_CARRIER_FIELD not in divergentes:
        return fill
    return fill + (f"{_VOCAB_CARRIER_FIELD}:{_CARRIER_1}",)


@dataclass(frozen=True)
class CrossGroupCollision:
    """Chave provenance-free viva em ≥2 proveniências ([[ADR-354]]), agregável e sem PII de pessoa."""

    key_digest: str
    mes: str
    valor_cents: int
    moeda: str
    direction: str
    n_rows: int
    n_provenances: int
    divergence: str
    parciais: str
    vazios_totais: str
    explained_shape: str
    descricao_vazia: bool
    whitelisted: bool

    @property
    def excess_cents(self) -> int:
        """Excesso CROSS-GRUPO: P proveniências entregando o mesmo evento ⇒ P−1 duplicatas."""
        return (self.n_provenances - 1) * self.valor_cents

    @property
    def carriers(self) -> tuple[str, ...]:
        """Assinaturas de carrier [[ADR-354]] nesta ocorrência — MESMA definição da whitelist."""
        return carrier_signatures(_tag_fields(self.divergence), _tag_fields(self.parciais))

    @property
    def defect_shaped(self) -> bool:
        """Carrier-shaped: assimetria de fill OU QUALQUER divergência de ``tipo_conta``."""
        return bool(self.carriers)

    @property
    def shape(self) -> str:
        """Classe diagnóstica em nomes de campo — eixo do histograma de triagem."""
        return (
            f"div={self.divergence or 'nenhum'} parciais={self.parciais or 'nenhum'} "
            f"vazio-total={self.vazios_totais or 'nenhum'}"
        )


@dataclass
class CrossGroupSummary:
    """Detector cross-grupo ([[ADR-354]]) JÁ PARTICIONADO — não existe campo com o total."""

    numerador: list = field(default_factory=list)
    explicadas: list = field(default_factory=list)
    coverage: dict = field(default_factory=dict)
    nao_varrido: dict = field(default_factory=dict)
    explained_shapes: tuple[str, ...] = ()


def _dados_dict(payload: object) -> dict | None:
    """``dados`` do balde quando LEGÍVEL — fonte única do predicado de legibilidade."""
    dados = payload.get("dados") if isinstance(payload, dict) else None
    return dados if isinstance(dados, dict) else None


def _bucket_rows(payload: object) -> Iterator[dict]:
    """Rows dict de um balde; degrada para vazio no ilegível (degradação NOMEADA na cobertura)."""
    for rows in (_dados_dict(payload) or {}).values():
        yield from [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _tx_rows(buckets_e4: dict) -> Iterator[tuple[str, dict]]:
    """(direction, row) dos baldes com grão transacional — ``direction`` vem do BALDE."""
    for bucket, direction in _TX_BUCKET_DIRECTION.items():
        for row in _bucket_rows(buckets_e4.get(bucket)):
            yield direction, row


def _row_cents(row: dict) -> int | None:
    """Magnitude em cents pela MESMA função do hash K4 (``InvalidOperation`` ⊄ ``ValueError``)."""
    from pipeline.domain.services._tx_identity import decimal_cents

    try:
        return decimal_cents(row.get("valor"))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _row_moeda(row: dict) -> str:
    return (row.get("moeda") or "").strip().upper()  # espelha build_hash_inputs


def _unkeyable_reason(row: dict) -> str | None:
    """Razão declarada da exclusão da chave, ``None`` se chaveável (fonte ÚNICA do predicado)."""
    # Piso aqui derruba o numerador SEM quebrar a identidade de cobertura (que é
    # auto-consistente); quem trava é `test_so_valor_exatamente_zero_e_excluido_por_valor`.
    cents = _row_cents(row)
    if cents is None:
        return "valor_nao_monetario"
    if cents == 0:
        return "valor_zero"
    return None if str(row.get("data") or "") else "sem_data"


def _cross_group_key(direction: str, row: dict) -> tuple | None:
    """Chave provenance-free ([[ADR-354]] §Decisão); ``None`` na row não-chaveável."""
    from pipeline.domain.services._tx_identity import normalize_descricao

    if _unkeyable_reason(row) is not None:
        return None
    data, cents = str(row.get("data")), _row_cents(row)
    return (data, cents, _row_moeda(row), direction, normalize_descricao(row.get("descricao")))


def _row_provenance(row: dict) -> tuple[str, str, str]:
    """Tripla de proveniência normalizada — constante por CONTA no E4, não por tx."""
    from pipeline.domain.services._tx_identity import (
        normalize_banco,
        normalize_tipo_conta,
        normalize_titular,
    )

    return (
        normalize_banco(row.get("banco")),
        normalize_titular(row.get("titular")),
        normalize_tipo_conta(row.get("tipo_conta")),
    )


def _field_values(provenances: set[tuple[str, str, str]], name: str) -> set[str]:
    return {p[_PROVENANCE_FIELDS.index(name)] for p in provenances}


def _fill_state(values: set[str]) -> str:
    """Fill-state do campo entre as pernas: ``parcial`` é a assinatura do carrier [[ADR-354]]."""
    vazio = any(not v for v in values)
    cheio = any(v for v in values)
    if vazio and cheio:
        return _PARCIAL
    return _VAZIO if vazio else _PREENCHIDO


def _fill_states(provenances: set[tuple[str, str, str]]) -> dict[str, str]:
    return {name: _fill_state(_field_values(provenances, name)) for name in _PROVENANCE_FIELDS}


def _divergence_tag(provenances: set[tuple[str, str, str]]) -> str:
    """Campos com >1 valor entre as pernas, em nomes (nunca valores — PII)."""
    return "+".join(n for n in _PROVENANCE_FIELDS if len(_field_values(provenances, n)) > 1)


def _partial_tag(states: dict[str, str]) -> str:
    """Campos ``parcial`` (divergentes por construção) — a assimetria NO eixo divergente."""
    return "+".join(n for n in _PROVENANCE_FIELDS if states[n] == _PARCIAL)


def _empty_all_tag(states: dict[str, str]) -> str:
    """Campos vazios em TODAS as pernas — contexto simétrico, nunca defeito."""
    return "+".join(n for n in _PROVENANCE_FIELDS if states[n] == _VAZIO)


def _explained_shape(provenances: set[tuple[str, str, str]], states: dict[str, str]) -> str:
    """Eixo ÚNICO de whitelist: VALORES de vocabulário fechado + fill-state de ``titular``."""
    vocab = [
        f"{n}=" + "~".join(sorted(v or _EMPTY_VALUE for v in _field_values(provenances, n)))
        for n in _CLOSED_VOCAB_FIELDS
    ]
    return "|".join([*vocab, f"titular={states['titular']}"])


def _parse_shape(entry: str) -> dict[str, str]:
    """Segmentos ``campo=payload`` na ordem canônica; malformado é erro, não warning."""
    segs = [s.split("=", 1) for s in entry.split("|")]
    canonical = all(len(s) == 2 for s in segs) and [s[0] for s in segs] == list(_SHAPE_FIELDS)
    if not canonical:
        esperado = "|".join(f"{f}=<v>" for f in _SHAPE_FIELDS)
        raise ValueError(f"shape de whitelist malformado (esperado {esperado}): {entry!r}")
    return {name: payload for name, payload in segs}


def _shape_divergentes(fields: dict[str, str]) -> frozenset[str]:
    """Campos de vocabulário com >1 valor no shape declarado (``~`` separa os valores)."""
    return frozenset(n for n in _CLOSED_VOCAB_FIELDS if len(fields[n].split("~")) > 1)


def _shape_parciais(fields: dict[str, str]) -> frozenset[str]:
    """Campos fill-ASSIMÉTRICOS no shape: ``titular=parcial`` e sentinela de vazio ao lado
    de valor real — que é a MESMA assimetria, escrita em valores."""
    parciais = {"titular"} if fields["titular"] == _PARCIAL else set()
    for name in _CLOSED_VOCAB_FIELDS:
        values = fields[name].split("~")
        if _EMPTY_VALUE in values and len(values) > 1:
            parciais.add(name)
    return frozenset(parciais)


def _validate_entry(entry: str) -> None:
    """Rejeita assinatura de carrier ([[ADR-354]], definição ÚNICA) + vazio em TODAS as pernas."""
    fields = _parse_shape(entry)
    if fields["titular"] not in _FILL_STATES:
        raise ValueError(f"fill-state de titular desconhecido em {entry!r}: {fields['titular']!r}")
    carriers = carrier_signatures(_shape_divergentes(fields), _shape_parciais(fields))
    if carriers:
        raise ValueError(
            f"whitelist com assinatura de carrier ADR-354 ({'+'.join(carriers)}; "
            f"c1=tipo_conta divergente, c2=campo de proveniência parcial): {entry!r}"
        )
    for name in _CLOSED_VOCAB_FIELDS:
        if fields[name] == _EMPTY_VALUE:
            raise ValueError(f"whitelist com sentinela de vazio em {name}: {entry!r}")


def validate_explained(explained: frozenset[str]) -> None:
    """Torna o carrier INALCANÇÁVEL pela whitelist por construção — erro, não warning."""
    # Residual no doc da lane: divergência de VALOR em ``banco`` com as 2 pernas cheias é
    # aceita (coincidência cross-instituição), então quem cobre esse resto é o ratchet.
    for entry in sorted(explained):
        _validate_entry(entry)


def _key_digest(key: tuple) -> str:
    """Digest opaco e estável entre runs — junta a ocorrência ao baseline off-git."""
    return hashlib.sha256("|".join(str(p) for p in key).encode("utf-8")).hexdigest()[:8]


def _group_by_key(buckets_e4: dict) -> dict[tuple, list[dict]]:
    """UM mapa para os DOIS baldes — é o que faz ``direction`` discriminar de verdade."""
    groups: dict[tuple, list[dict]] = {}
    for direction, row in _tx_rows(buckets_e4):
        key = _cross_group_key(direction, row)
        if key is not None:
            groups.setdefault(key, []).append(row)
    return groups


def _collision(key: tuple, rows: list[dict], explained: frozenset[str]) -> CrossGroupCollision:
    provenances = {_row_provenance(r) for r in rows}
    states = _fill_states(provenances)
    shape = _explained_shape(provenances, states)
    data, cents, moeda, direction, descricao = key
    return CrossGroupCollision(
        key_digest=_key_digest(key),
        mes=data[:7],
        valor_cents=cents,
        moeda=moeda,
        direction=direction,
        n_rows=len(rows),
        n_provenances=len(provenances),
        divergence=_divergence_tag(provenances),
        parciais=_partial_tag(states),
        vazios_totais=_empty_all_tag(states),
        explained_shape=shape,
        descricao_vazia=not descricao,
        whitelisted=shape in explained,
    )


def cross_group_double_count(
    buckets_e4: dict, *, explained: frozenset[str] = EXPLAINED_DIVERGENCE
) -> list[CrossGroupCollision]:
    """Chaves provenance-free vivas em ≥2 triplas de proveniência ([[ADR-354]]) — os limites
    de SOBRE/SUB-detecção e os canais de massa não-varrida estão no doc da lane A40.l1."""
    validate_explained(explained)
    hits = [
        _collision(key, rows, explained)
        for key, rows in _group_by_key(buckets_e4).items()
        if len({_row_provenance(r) for r in rows}) > 1
    ]
    return sorted(hits, key=lambda c: (-c.excess_cents, c.key_digest))


def cross_group_numerator(hits: list[CrossGroupCollision]) -> list[CrossGroupCollision]:
    """Numerador do KR-B: ocorrências NÃO explicadas (anti-Goodhart em um só lugar)."""
    return [c for c in hits if not c.whitelisted]


def cross_group_explained(hits: list[CrossGroupCollision]) -> list[CrossGroupCollision]:
    """Ocorrências whitelisted — linha SEPARADA, nunca somadas ao numerador."""
    return [c for c in hits if c.whitelisted]


def _assert_explicadas_declaradas(explicadas: list, explained: frozenset[str]) -> None:
    """Toda ocorrência na linha ``explicadas`` TEM shape na whitelist declarada."""
    # Sem esta invariante, uma rota alternativa de whitelist (``whitelisted = shape in
    # explained or <predicado novo>``) esvazia o numerador para dentro de ``explicadas``
    # sem tocar em ``explained`` — com as 3 identidades fechando e cobertura OK.
    fora = sorted({c.explained_shape for c in explicadas} - set(explained))
    if fora:
        raise ValueError(
            f"ocorrência em explicadas com shape FORA da whitelist declarada "
            f"(rota alternativa de whitelist, [[ADR-354]] anti-Goodhart): {fora}"
        )


def cross_group_unkeyable(buckets_e4: dict) -> dict[str, int]:
    """Rows dos baldes transacionais EXCLUÍDAS da chave, por razão declarada (ADR-342)."""
    out = {"sem_data": 0, "valor_zero": 0, "valor_nao_monetario": 0}
    for _direction, row in _tx_rows(buckets_e4):
        reason = _unkeyable_reason(row)
        if reason is not None:
            out[reason] += 1
    return out


def _declared_tx(buckets_e4: dict) -> int:
    """Σ ``total_transacoes`` DECLARADO — campo que o detector NÃO lê, logo cobertura externa."""
    return sum(
        int(p.get("total_transacoes", 0))
        for p in (buckets_e4.get(b) for b in _TX_BUCKET_DIRECTION)
        if isinstance(p, dict)
    )


def _illegible_buckets(buckets_e4: dict) -> tuple[str, ...]:
    """Baldes transacionais ausentes ou com ``dados`` não-dict — degradação NOMEADA."""
    return tuple(b for b in _TX_BUCKET_DIRECTION if _dados_dict(buckets_e4.get(b)) is None)


def _coverage_counts(buckets_e4: dict) -> dict:
    """Os 9 denominadores; ``provenance_triples`` == 1 ⇒ o critério "≥2 triplas" é vacuoso."""
    rows = list(_tx_rows(buckets_e4))
    groups = _group_by_key(buckets_e4)
    multiprov = [g for g in groups.values() if len({_row_provenance(r) for r in g}) > 1]
    return {
        "rows_scanned": len(rows),
        "declared_tx": _declared_tx(buckets_e4),
        "buckets_ilegiveis": _illegible_buckets(buckets_e4),
        "rows_keyed": sum(len(g) for g in groups.values()),
        "keys_distinct": len(groups),
        "keys_multirow": sum(1 for g in groups.values() if len(g) > 1),
        "keys_multiprov": len(multiprov),
        "provenance_triples": len({_row_provenance(r) for _d, r in rows}),
        "keyed_sem_descricao": sum(len(g) for k, g in groups.items() if not k[4]),
        "unkeyable": cross_group_unkeyable(buckets_e4),
    }


def _coverage_ok(cov: dict) -> bool:
    """As 3 identidades fecham, nenhum balde ilegível e ≥2 triplas — 0 falsificável por aritmética."""
    interna = cov["rows_scanned"] - cov["rows_keyed"] == sum(cov["unkeyable"].values())
    externa = cov["rows_scanned"] == cov["declared_tx"]
    return bool(
        interna
        and externa
        and cov["particao_fecha"]
        and not cov["buckets_ilegiveis"]
        and cov["provenance_triples"] >= 2
    )


def cross_group_coverage(buckets_e4: dict, *, particionadas: int) -> dict:
    """Denominadores: sem eles "0 por corpus limpo" e "0 por detector cego" são byte-idênticos."""
    # ``particionadas`` é OBRIGATÓRIO de propósito: com default a 3ª identidade vira
    # tautologia (particionadas := keys_multiprov) e um filtro dentro do numerador fica
    # invisível. Quem não sabe quantas saíram particionadas não pode afirmar cobertura.
    cov = _coverage_counts(buckets_e4)
    cov["particionadas"] = particionadas
    cov["particao_fecha"] = cov["keys_multiprov"] == cov["particionadas"]
    return {**cov, "coverage_ok": _coverage_ok(cov)}


def cross_group_summary(
    buckets_e4: dict,
    transferencias_count: int = 0,
    *,
    explained: frozenset[str] = EXPLAINED_DIVERGENCE,
) -> CrossGroupSummary:
    """Deriva e PARTICIONA o detector [[ADR-354]], fechando a 3ª identidade de cobertura."""
    hits = cross_group_double_count(buckets_e4, explained=explained)
    numerador, explicadas = cross_group_numerator(hits), cross_group_explained(hits)
    _assert_explicadas_declaradas(explicadas, explained)
    return CrossGroupSummary(
        numerador=numerador,
        explicadas=explicadas,
        coverage=cross_group_coverage(buckets_e4, particionadas=len(numerador) + len(explicadas)),
        nao_varrido={"transferencias": int(transferencias_count)},
        explained_shapes=tuple(sorted(explained)),
    )
