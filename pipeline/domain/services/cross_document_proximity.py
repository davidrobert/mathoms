"""Classe D±1 ([[A40.l102]]) — grupos que só não colapsam porque a data difere.

Passada PRÓPRIA, sobre a MESMA lista pré-poda do colapsador, e deliberadamente sem
alvo. O par medido no dogfood cai no vão entre dois mecanismos com cegueiras
complementares: `ReconciliationService.is_duplicate` tolera ±3 dias mas exige
descrição idêntica; `CrossDocumentCollapser` normaliza a descrição
(`_ROUTING_SUFFIX_RE`) e é day-exact. Nenhum dos dois vê "mesmo valor, mesma
descrição normalizada, 1 dia de diferença, documentos-fonte distintos" — e o que
não vira candidato nunca ganha `blocked_reason`, logo não é sequer CONTÁVEL.

Produzir o número é o passo que falta; remover não é, enquanto não houver teste
positivo por candidato (a cadeia de saldo repara ou não repara a quebra). Módulo
separado do colapsador para que a classe não possa alcançar o caminho de corte por
descuido — e porque os dois juntos passavam de 500 linhas.

Puro, sem I/O.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Iterable

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Transaction
from pipeline.domain.services.cross_document_collapse_types import ProximityCandidate
from pipeline.domain.services.cross_document_keys import (
    PROVENANCE_FIELDS,
    collapse_key,
    field_values,
    provenance,
)

__all__ = ["proximity_candidates"]


# ── Classe D±1 ([[A40.l102]]) ────────────────────────────────────────────────────
# Passada PRÓPRIA, sobre a MESMA lista pré-poda, e deliberadamente sem alvo. O par
# medido no dogfood cai no vão entre dois mecanismos com cegueiras complementares:
# `is_duplicate` tolera ±3 dias mas exige descrição idêntica; este colapsador
# normaliza a descrição (`_ROUTING_SUFFIX_RE`) mas é day-exact. Nenhum dos dois vê
# "mesmo valor, mesma descrição normalizada, 1 dia de diferença, documentos-fonte
# distintos" — e o que não vira candidato nunca ganha `blocked_reason`, logo não é
# sequer CONTÁVEL. Produzir o número é o passo que falta; remover não é, enquanto
# não houver teste positivo por candidato (a cadeia de saldo repara ou não repara).
def _date_free_key(tx: Transaction, stmt: BankStatement) -> tuple:
    """`_collapse_key` menos a data — o eixo em que a classe D±1 se define."""
    _data, cents, moeda, direction, descricao = collapse_key(tx, stmt)
    return (cents, moeda, direction, descricao)


_DatedRow = tuple[_date, BankStatement, Transaction]


# Encadear é deliberado: 26→27→28 é UM grupo, não dois pares sobrepostos. Emitir
# pares tornaria a mesma row membro de dois candidatos e o total deixaria de somar
# rows — para um número cuja função é dimensionar risco, contar duas vezes é pior
# que agrupar de mais.
def _clusters_por_proximidade(rows: list[_DatedRow], max_delta: int) -> list[list[_DatedRow]]:
    """Parte a lista onde o gap entre datas CONSECUTIVAS passa de ``max_delta``."""
    ordenadas = sorted(rows, key=lambda r: r[0])
    clusters: list[list[_DatedRow]] = [[ordenadas[0]]]
    for anterior, atual in zip(ordenadas, ordenadas[1:]):
        if (atual[0] - anterior[0]).days <= max_delta:
            clusters[-1].append(atual)
        else:
            clusters.append([atual])
    return clusters


# Total por construção (`default=0`): com uma data só não há par, e 0 é a
# resposta honesta. Levantar `ValueError` num caminho que só o chamador atual
# evita transforma um filtro semântico em pré-condição implícita — quem mexer
# no filtro amanhã leva um crash em vez de um número errado, e o crash chega
# longe daqui.
def _delta_maximo(datas: tuple[str, ...]) -> int:
    """Maior gap entre datas consecutivas distintas do grupo, em dias."""
    dias = [_date.fromisoformat(d) for d in datas]
    return max(((b - a).days for a, b in zip(dias, dias[1:])), default=0)


def _proximity_candidate(key: tuple, cluster: list[_DatedRow]) -> ProximityCandidate | None:
    """``None`` quando o cluster não é da classe — data única ou uma só proveniência."""
    datas = tuple(sorted({d.isoformat() for d, _s, _t in cluster}))
    if len(datas) < 2:
        return None  # data única é assunto da passada principal, não desta
    provenances = {provenance(s) for _d, s, _t in cluster}
    if len(provenances) < 2:
        return None  # repetição intra-proveniência é a classe da [[A42.l5]]
    return ProximityCandidate(
        mes=datas[0][:7],
        valor_cents=int(key[0]),
        moeda=str(key[1]),
        direction=str(key[2]),
        datas=datas,
        delta_dias=_delta_maximo(datas),
        n_rows=len(cluster),
        n_provenances=len(provenances),
        divergence="+".join(n for n in PROVENANCE_FIELDS if len(field_values(provenances, n)) > 1),
    )


def proximity_candidates(
    statements: Iterable[BankStatement], max_delta: int
) -> tuple[ProximityCandidate, ...]:
    """Grupos D±1 da lista inteira, em ordem determinística."""
    index: dict[tuple, list[_DatedRow]] = {}
    for stmt in statements:
        for tx in stmt.transactions:
            key = _date_free_key(tx, stmt)
            if not str(key[3]):
                continue  # descrição vazia: mesma cláusula que reprova na passada principal
            index.setdefault(key, []).append((tx.date, stmt, tx))
    achados = [
        candidato
        for key, rows in index.items()
        for cluster in _clusters_por_proximidade(rows, max_delta)
        if (candidato := _proximity_candidate(key, cluster)) is not None
    ]
    return tuple(sorted(achados, key=lambda c: (c.datas, c.valor_cents, c.moeda, c.direction)))
