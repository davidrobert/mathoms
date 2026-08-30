"""DTOs do colapso cross-documento ([[ADR-354]] §Emenda · [[A40.l2]]).

Extraído de ``cross_document_collapser`` (SRP + limite de 500 linhas): o alvo de
remoção, a remoção declarada por canal e o candidato PII-safe. Sem I/O, sem lógica de
predicado — o service importa daqui e re-exporta para não quebrar call-site.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from pipeline.domain.services._tx_identity import decimal_cents


@dataclass(frozen=True)
class RemovalTarget:
    """Alvo de remoção com **multiplicidade** — hash NÃO endereça row."""

    # As 8 partes de `_hash_v2` são a união da 5-tupla da chave de colapso com a tripla
    # de proveniência, então TODAS as rows de um bucket compartilham o mesmo hash por
    # construção. Emitir lista de hashes fazia 1 hash endereçar N rows: medido em
    # 2026-08-05, alvo declarando 411 rows resolvia 453 — e o excesso eram exatamente
    # os sobreviventes eleitos pela cardinalidade multiset.

    hash: str
    remover: int
    no_bucket: int

    @property
    def hash_desaparece(self) -> bool:
        """``True`` ⇒ nenhuma row com esse hash sobra: override ancorado nele órfãna."""
        return self.remover >= self.no_bucket

    def to_trace_dict(self) -> dict:
        return {"hash": self.hash, "remover": self.remover, "no_bucket": self.no_bucket}


CANAL_COLAPSO = "cross_document_collapse"
_METODO_LLM = "llm"


# Rows de perna LLM em chave de proveniência ÚNICA: hoje sobrevivem porque o índice descarta
# chave com uma só proveniência, e viram alvo no instante em que o documento nativo daquela
# conta é ingerido. É o indicador ANTECEDENTE que `retido_por_override` não dá — aquele só vê
# o dano materializado, e sem este a lane volta a medir 0 e a concluir "vazio" pela terceira vez.
def _strip_identity_suffix(value: str, suffixes: frozenset[str]) -> str:
    """Remove o sufixo de moeda do fim do tipo; nunca reduz o tipo a string vazia."""
    for suffix in sorted(suffixes):
        if value.endswith(suffix) and len(value) > len(suffix):
            return value[: -len(suffix)]
    return value


def _identity_collision(group: frozenset[str], suffixes: frozenset[str]) -> str | None:
    """Tipo cujo sufixo de moeda é o ÚNICO discriminante contra outro membro do grupo."""
    # Cada membro perde o SEU sufixo antes da comparação: strip de um sufixo só
    # sobre o grupo inteiro não vê `...globalusd` vs `...globaleur` (stems ficam
    # distintos em qualquer passada única).
    by_stem: dict[str, str] = {}
    for value in sorted(group):
        stem = _strip_identity_suffix(value, suffixes)
        if stem in by_stem:
            return value
        by_stem[stem] = value
    return None


def conta_perna_llm_orfa(index: dict) -> int:
    """Reservatório de colapso futuro, a partir do índice `chave → proveniência → rows`."""
    return sum(
        len(rows)
        for buckets in index.values()
        if len(buckets) == 1
        for rows in buckets.values()
        if rows and (rows[0][0].extraction_method or "").lower() == _METODO_LLM
    )


@dataclass(frozen=True)
class CollapseRemoval:
    """Remoção declarada por statement — canal ``cross_document_collapse`` ([[ADR-347]])."""

    # `valor_cents` é ASSINADO (débito negativo), como o resto do ledger. NÃO reusar
    # `CollapseCandidate.valor_cents`, que é magnitude (`decimal_cents` faz `abs()`):
    # `_declared_dedup_cents` nunca fecharia contra `val_in − val_out`.
    canal: str
    count: int
    valor_cents: int
    cross_source_count: int
    source: str | None = None
    # `(("YYYY-MM", n), ...)` ordenado — o breakdown que o contador da S2 precisa ([[A40.l2]]
    # §D6). LISTA de pares, nunca escalar nem mapa: `dev/golden_diff.py::is_monetary("meses")`
    # devolve `True` (o sufixo `_meses` exige underscore), então escalar viraria ×100 e num
    # mapa o próprio mês seria a chave. Como lista, o leaf `mes` é string e `to_cents` não se
    # aplica. Vazio no modo sombra: só o enforce remove row.
    meses: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class CollapseMeasurement:
    """Candidatos **+** o corpus contra o qual o gate de override se cruza ([[ADR-364]])."""

    # O corpus é sempre PRÉ-poda, nos dois modos. Derivá-lo depois da remoção perderia
    # exatamente as rows removidas — onde os overrides em risco ancoram —, e a garantia
    # anti-vácuo degradaria no único momento em que ela é load-bearing.

    candidates: tuple = ()
    corpus_gate_digests: frozenset[str] = frozenset()
    corpus_row_hashes: frozenset[str] = frozenset()
    # [[A40.l102]] — classe D±1, medida em passada PRÓPRIA e mantida FORA de
    # `candidates` de propósito: `collapse_precondition`, `_rows_to_drop` e o
    # payload do E3 leem aquele campo, e misturar as duas classes mudaria o gate
    # de enforce e o artefato. Separada, a classe é contável sem mover um byte.
    proximidade_d1: tuple = ()
    # Rows de perna LLM em chave de proveniência única — viram candidato quando o documento
    # nativo daquela conta chegar. Preditor da retenção futura; ver `_group_by_key`.
    reservatorio_llm_sem_gemea: int = 0


CLASSE_PROXIMIDADE_D1 = "proximidade_d1"


@dataclass(frozen=True)
class ProximityCandidate:
    """Grupo cross-proveniência que difere do candidato de colapso **só pela data**.

    Classe PRÓPRIA, e não um `CollapseCandidate` com campos zerados. O candidato de
    colapso elege sobrevivente (`survivor_hash`), conta `removable_rows` e carrega
    `removal_targets`; um objeto dessa forma com os três vazios entraria nas mesmas
    listas que o corte consome, e o dia em que alguém filtrasse por
    `blocked_reason is None` em vez de por `sera_colapsado` o corte alcançaria uma
    classe que nunca foi julgada. Aqui não há alvo **por construção**, não por
    convenção — é o ponto todo da [[A40.l102]]: D±1 é aceitável como classe de
    candidato e inaceitável como critério de remoção enquanto não houver teste
    positivo por candidato (a cadeia de saldo; hoje `saldo_apos` é emitido por 0 dos
    parsers de banco).

    `gate_digest` não existe aqui: o digest do gate de override é por chave, e chave
    inclui a data — um grupo que abrange 2 datas não tem um. Emitir o de uma das
    pernas faria a re-ancoragem apontar para a data errada.
    """

    mes: str
    valor_cents: int
    moeda: str
    direction: str
    # Datas ISO do grupo, ordenadas — o que torna o número auditável linha a linha.
    datas: tuple[str, ...]
    # Maior distância entre datas CONSECUTIVAS do grupo (dias). Nunca > `max_delta`.
    delta_dias: int
    n_rows: int
    n_provenances: int
    divergence: str = ""
    # Fixo: o motivo do bloqueio É a proximidade. Campo (e não constante implícita)
    # para que o consumidor leia a causa do mesmo lugar nas duas classes.
    blocked_reason: str = CLASSE_PROXIMIDADE_D1

    def to_trace_dict(self) -> dict:
        return {
            "mes": self.mes,
            "valor_cents": self.valor_cents,
            "moeda": self.moeda,
            "direction": self.direction,
            "datas": list(self.datas),
            "delta_dias": self.delta_dias,
            "n_rows": self.n_rows,
            "n_provenances": self.n_provenances,
            "divergence": self.divergence,
            "blocked_reason": self.blocked_reason,
        }


def proximity_counts(candidates) -> dict[str, int]:
    """Agregado PII-safe da classe D±1 — contagens e cents, nunca texto nem data."""
    todos = list(candidates)  # materializa ANTES: generator consumido daria candidatos=0
    return {
        "candidatos": len(todos),
        "rows": sum(c.n_rows for c in todos),
        # Cents que um enforce ingênuo removeria: uma row por grupo, a mais recente.
        # É o TAMANHO DO RISCO, não uma remoção planejada — nada aqui tem alvo.
        "cents_em_risco": sum(c.valor_cents * (c.n_rows - 1) for c in todos),
    }


def shadow_counts(candidates) -> dict[str, int]:
    """Agregado PII-safe da sombra (ADR-364) — só contagens e cents, nunca texto."""
    todos = list(candidates)  # materializa ANTES: generator consumido daria candidatos=0
    colapsaveis = [c for c in todos if c.collapsible]
    return {
        "candidatos": len(todos),
        "colapsaveis": len(colapsaveis),
        "rows_removiveis": sum(c.removable_rows for c in colapsaveis),
        "cents_removiveis": sum(c.valor_cents * c.removable_rows for c in colapsaveis),
        "alvo_ambiguo": sum(1 for c in colapsaveis if c.alvo_ambiguo),
    }


@dataclass(frozen=True)
class CollapseCandidate:
    """Ocorrência cross-proveniência, PII-safe (digest + cents + códigos, nunca texto)."""

    key_digest: str
    mes: str
    valor_cents: int
    moeda: str
    direction: str
    n_rows: int
    n_provenances: int
    survivor_cardinality: int
    removable_rows: int
    removal_targets: tuple[RemovalTarget, ...]
    blocked_reason: str | None
    # Digest direction-free para o gate de override (D1) — ver `gate_key_digest`.
    gate_digest: str = ""
    # `_hash_v2` da row que SOBREVIVE ao colapso — alvo da re-ancoragem ([[ADR-364]] §2).
    # Vive no candidato e não no `RemovalTarget` porque é propriedade do GRUPO: sob a D5 há
    # no máximo 1 alvo por candidato, e todas as rows de um bucket compartilham um hash.
    survivor_hash: str = ""
    # Tags em NOMES de campo (nunca valores — PII), na mesma forma que o detector da
    # [[A40.l1]] emite: permitem afirmar a equivalência "colapsável ⇒ carrier-shaped"
    # sem que o pipeline importe `dev/`.
    divergence: str = ""
    parciais: str = ""
    # [[ADR-364]] §Emenda 2026-08-09 — a chave tem override ativo, logo NÃO colapsa neste run.
    # Não é `blocked_reason`: aquele campo é do predicado do colapsador (propriedade do dado),
    # este é estado externo do workspace. Confundi-los faria o gate ler "predicado reprovou"
    # onde houve "usuário corrigiu", e a série do gate perderia a distinção.
    retido_por_override: bool = False
    retido_por_sources: tuple[str, ...] = ()

    @property
    def collapsible(self) -> bool:
        """Colapsável pelo PREDICADO. Retenção é ortogonal — ver `sera_colapsado`."""
        return self.blocked_reason is None and self.removable_rows > 0

    @property
    def sera_colapsado(self) -> bool:
        """O que de fato acontece neste run: colapsável **e** não retido."""
        return self.collapsible and not self.retido_por_override

    @property
    def rows_alcancadas_por_hash(self) -> int:
        """Rows que um consumidor que apaga por CONJUNTO de hash atingiria."""
        return sum(t.no_bucket for t in self.removal_targets)

    @property
    def alvo_ambiguo(self) -> bool:
        """Alvo pede remoção PARCIAL de um bucket — apagar por hash removeria a mais."""
        return self.rows_alcancadas_por_hash != self.removable_rows

    def to_trace_dict(self) -> dict:
        return {
            "key_digest": self.key_digest,
            "gate_digest": self.gate_digest,
            "mes": self.mes,
            "valor_cents": self.valor_cents,
            "moeda": self.moeda,
            "direction": self.direction,
            "n_rows": self.n_rows,
            "n_provenances": self.n_provenances,
            "survivor_cardinality": self.survivor_cardinality,
            "removable_rows": self.removable_rows,
            "removal_targets": [t.to_trace_dict() for t in self.removal_targets],
            "alvo_ambiguo": self.alvo_ambiguo,
            "blocked_reason": self.blocked_reason,
            "retido_por_override": self.retido_por_override,
            "retido_por_sources": list(self.retido_por_sources),
            "divergence": self.divergence,
            "parciais": self.parciais,
        }


# `denied_digests` é DENY-list, não permit-list, porque só ela é computável sem os candidatos:
# eles nascem dentro de `reconcile_via_store`, e o guard tem de existir no construtor para valer
# também em `measure()` (senão o gate pré-flip prediz órfãos que o enforce-com-guard não produz).
# `lido` é o que impede o vazio de significar duas coisas: "li e não há override" e "não consegui
# ler" divergem no que o run deve fazer, e conjunto vazio sozinho não distingue — foi o defeito
# de zero-ambíguo que esta lane já pagou quatro vezes.
@dataclass(frozen=True)
class OverrideRetentionGuard:
    """Digests de override ativo que **não** colapsam ([[ADR-364]] §Emenda 2026-08-09). Dado
    congelado, sem I/O: o produtor vive em `collapse_precondition.from_active_overrides` e é
    injetado no composition root do stage."""

    denied_digests: frozenset[str]
    overrides_ativos: int
    sem_snapshot: int
    denied_por_source: tuple[tuple[str, int], ...]
    lido: bool
    # `denied_por_source` conta OVERRIDES por origem; este mapa liga cada digest às origens
    # que o negaram. São grandezas distintas: vários overrides colidem num digest, e digest
    # negado pode não casar candidato nenhum. O passo (1) da ordem de construção da
    # re-ancoragem ([[ADR-364]] §Emenda 2026-08-09) compara retido[rule] contra
    # retido[manual] — sobre CANDIDATOS retidos, que só este mapa permite atribuir.
    sources_por_digest: tuple[tuple[str, tuple[str, ...]], ...] = ()
    # Override cujo `tx_data` não é ISO produz digest divergente do que o pipeline calcula:
    # a chave dele NÃO é retida e ele é órfãnado em silêncio. Como `sem_snapshot`, é condição
    # de RUN — não se sabe a qual chave pertence ([[ADR-364]] §Emenda 2026-08-10).
    tx_data_nao_iso: int = 0

    @classmethod
    def nao_lido(cls) -> "OverrideRetentionGuard":
        """Store não-DB ou import indisponível — degrada o run para measure-only."""
        return cls(frozenset(), 0, 0, (), lido=False)

    @classmethod
    def sem_overrides(cls) -> "OverrideRetentionGuard":
        """AFIRMA ausência de override (testes, CLI). Diferente de `nao_lido`."""
        return cls(frozenset(), 0, 0, (), lido=True)

    # `sem_snapshot > 0` entra aqui porque `_override_gate_digest` devolve `None` para override
    # sem as colunas da [[ADR-282]], e o read-path AINDA o aplica pelo hash v1: tratá-lo como
    # "não existe override" faria a chave colapsar e a correção morrer. É condição de RUN, não de
    # candidato — por construção não se sabe a qual chave ele pertence.
    @property
    def degradado(self) -> bool:
        """Nada é removido: o alvo da degradação é "retém tudo", nunca "colapsa tudo"."""
        return (not self.lido) or bool(self.sem_snapshot) or bool(self.tx_data_nao_iso)

    def retem(self, gate_digest: str) -> bool:
        """`True` se esta chave tem override ativo e portanto **não** colapsa."""
        return bool(gate_digest) and gate_digest in self.denied_digests

    def sources_de(self, gate_digest: str) -> tuple[str, ...]:
        """Origens (`manual`/`rule`) dos overrides que negam esta chave; vazio se não nega."""
        return dict(self.sources_por_digest).get(gate_digest, ())

    def to_trace_dict(self) -> dict:
        """Contadores PII-free para `output_summary` — COM denominador: zero medido e zero
        não-medido não podem imprimir o mesmo caractere."""
        return {
            "lido": self.lido,
            "degradado": self.degradado,
            "overrides_ativos": self.overrides_ativos,
            "sem_snapshot": self.sem_snapshot,
            "tx_data_nao_iso": self.tx_data_nao_iso,
            "denied_digests": len(self.denied_digests),
            "denied_por_source": dict(self.denied_por_source),
        }


class CorteDivergente(RuntimeError):
    """O que o candidato DECLARA remover não é o que a mutação remove."""


# Compara `removable_rows` contra o total podado — a grandeza que o bug do `keep_split` movia
# (measure declarava 453 enquanto a mutação removia 593, com a suíte verde). NÃO compara
# `key_digest` entre `measure()` e `collapse()`: as duas chamam as mesmas funções puras sobre o
# mesmo objeto, logo são idênticas por identidade — assert que não pode disparar.
def exige_paridade_de_corte(candidates, n_removidas: int) -> None:
    """`Σ removable_rows dos não-retidos == rows efetivamente podadas`, fail-loud."""
    declarado = sum(c.removable_rows for c in candidates if c.sera_colapsado)
    if declarado != n_removidas:
        raise CorteDivergente(
            f"candidatos declaram {declarado} rows removíveis, a poda removeu {n_removidas}"
        )


def _tx_cents_signed(tx) -> int:
    """Cents com SINAL — o ledger grava débito negativo (espelha `_tx_cents`)."""
    return int(decimal_cents(tx.amount.amount) * (-1 if tx.amount.amount < 0 else 1))


# O MÊS entra na chave porque decide o dono da remoção: `output_key` embute o período, então
# arquivo de dois períodos vira dois grupos e sem o mês a mesma remoção é reivindicada pelos dois
# (medido: 6 onde havia 3). `count` e `cents` somam na mesma iteração ⇒ partição exata nos dois.
def _agrega_por_source_e_mes(drop: list) -> dict[tuple[str | None, str], tuple[int, int]]:
    """``{(source, mes): (count, cents_assinado)}`` — uma passada sobre as rows."""
    agg: dict[tuple[str | None, str], list[int]] = {}
    for stmt, tx in drop:
        bucket = agg.setdefault((stmt.source_document, tx.date.strftime("%Y-%m")), [0, 0])
        bucket[0] += 1
        bucket[1] += _tx_cents_signed(tx)
    return {k: (c, v) for k, (c, v) in agg.items()}


def removals_by_source(drop: list) -> tuple[CollapseRemoval, ...]:
    """Uma ``CollapseRemoval`` por par ``(source_document, mês)`` — granularidade que a
    atribuição precisa para ter **dono único** ([[ADR-347]] §Emenda 2026-08-10)."""
    return tuple(
        CollapseRemoval(CANAL_COLAPSO, c, v, cross_source_count=c, source=src, meses=((mes, c),))
        for (src, mes), (c, v) in sorted(
            _agrega_por_source_e_mes(drop).items(), key=lambda kv: (kv[0][0] or "", kv[0][1])
        )
    )


class RetencaoInstavel(RuntimeError):
    """Override criado ENTRE a leitura do guard e o commit do artefato (TOCTOU)."""
