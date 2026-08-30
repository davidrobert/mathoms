"""Vereditos por unidade da ledger-certify: um grupo E3 ou um balde E4.

Extraído de ``dev.ledger_certify_core`` em A42.l19, quando o núcleo cruzou as
500 linhas. O seam é natural: aqui mora a **rubrica** (que veredito uma unidade
merece); lá ficam drift, montagem do report e render. Funções puras — sem I/O,
sem DB.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.golden_diff import to_cents
from dev.ledger_conservation import (
    COBERTO_SEM_VALOR,
    CONSERVADO,
    DEDUP_LEGITIMO,
    NAO_VERIFICAVEL,
    PERDA_SILENCIOSA,
)

_TX_BUCKETS = ("despesas", "receitas")


def _first_verdict(checks: list, default: tuple) -> tuple:
    return next(((v, d) for cond, v, d in checks if cond), default)


def _ledger_verdict(fresh: dict, total: int) -> tuple[str, str] | None:
    """ADR-347 — se o artefato declara o ledger (``tx_carregadas`` + ``remocoes``),
    o fechamento (int, tol-zero) PROVA a conservação de contagem; resíduo = P0."""
    remocoes = fresh.get("remocoes")
    carregadas = fresh.get("tx_carregadas")
    if not isinstance(remocoes, dict) or carregadas is None:
        return None
    declared = sum(int(r.get("count", 0)) for r in remocoes.values() if isinstance(r, dict))
    resid = int(carregadas) - total - declared
    if resid == 0:
        return (
            CONSERVADO,
            f"ledger fecha: {carregadas} == {total} + {declared} declaradas (tol-zero)",
        )
    return (
        PERDA_SILENCIOSA,
        f"ledger não fecha: resíduo {resid} não-declarado (carregadas={carregadas})",
    )


def e3_group_verdict(fresh) -> tuple[str, str]:
    """Veredito de um grupo E3: consistência interna (count) + **ledger de contagem
    declarado** (ADR-347) quando presente. 0-tx não sobe a ``conservado``; sem ledger,
    dups>0 fica ``coberto`` (valor removido não provável no artefato)."""
    if not isinstance(fresh, dict) or "transacoes" not in fresh:
        return NAO_VERIFICAVEL, "sem payload E3 legível"
    n_tx = len(fresh.get("transacoes") or [])
    total = int(fresh.get("transacoes_total", 0))
    if n_tx != total:
        return NAO_VERIFICAVEL, f"transacoes_total={total} != len(transacoes)={n_tx}"
    if n_tx == 0:
        return COBERTO_SEM_VALOR, "0 transações — sem checksum de fechamento neste grão"
    ledger = _ledger_verdict(fresh, total)
    if ledger is not None:
        return ledger
    if int(fresh.get("transacoes_duplicadas_removidas", 0)) > 0:
        return COBERTO_SEM_VALOR, "dups>0 sem ledger; valor removido não declarado no artefato"
    return CONSERVADO, "count interno fecha; dups=0 ⇒ valor provável"


def _cat_cents_ok(txns: list, amount) -> bool:
    return sum(to_cents(t.get("valor", 0)) for t in txns) == to_cents(amount)


def _dados_cents_ok(payload: dict) -> bool:
    """Σ cents(dados[cat]) == totais_por_categoria[cat] para todo cat (mirror CV16)."""
    dados = payload.get("dados", {})
    totais = payload.get("totais_por_categoria", {})
    return all(_cat_cents_ok(dados.get(cat, []), amt) for cat, amt in totais.items())


def _tx_bucket_verdict(payload: dict) -> tuple[str, str]:
    total = to_cents(payload.get("total_geral", 0))
    parts = sum(to_cents(v) for v in payload.get("totais_por_categoria", {}).values())
    checks = [
        (total != parts, PERDA_SILENCIOSA, f"Σ categorias {parts} != total_geral {total} cents"),
        (
            not _dados_cents_ok(payload),
            PERDA_SILENCIOSA,
            "Σ tx(dados[cat]) != totais_por_categoria",
        ),
    ]
    return _first_verdict(checks, (CONSERVADO, "balde fecha (categorias + tx em cents)"))


def _investimentos_verdict(payload: dict, collisions: list) -> tuple[str, str]:
    dados = payload.get("dados", [])
    if collisions:
        return PERDA_SILENCIOSA, f"dupla-contagem ADR-271: {len(collisions)} chave(s) viva(s) 2×"
    if not dados:
        return COBERTO_SEM_VALOR, "balde vazio (0 posições)"
    return CONSERVADO, f"{len(dados)} posições; sem duplicata literal nem snapshot cross-período"


# Contêiner contável de cada balde não-transacional, POR CHAVE (A42.l19) — mesmo
# discriminador que o guard de escrita usa: a artifact_key, não o shape. Sondar
# `dados`/`apolices`/`composicao` no payload imprimia "coberto · 0 itens" para
# `patrimonio` e `fluxo_mensal_detalhado`, que não têm nenhum dos três (`composicao`
# é campo do bloco `patrimonio` do E5, não do balde E4). O `or` encadeado ainda
# confundia contêiner VAZIO com contêiner AUSENTE — os dois caíam no `[]` final.
_NON_LEDGER_CONTAINERS: dict[str, tuple[str, ...]] = {
    "patrimonio": ("patrimonio_por_ano", "declarations"),
    "fluxo_mensal_detalhado": ("meses_ordenados",),
    "seguros": ("apolices", "dados"),
    "pontos_milhas": ("dados",),
}


def _non_ledger_verdict(key: str, payload: dict) -> tuple[str, str]:
    """Balde fora do grão transacional: conta o contêiner que a CHAVE declara.

    Shape não reconhecido devolve ``não-verificável``, nunca ``coberto``: dizer
    "coberto · 0 itens" sobre payload que esta função não sabe ler afirma uma
    cobertura que não houve — e era o que acontecia com os 87 itens do
    ``patrimonio`` (A42.l19).
    """
    esperados = _NON_LEDGER_CONTAINERS.get(key, ())
    for nome in esperados:
        conteudo = payload.get(nome)
        if isinstance(conteudo, (list, dict, tuple, str)):
            return (
                COBERTO_SEM_VALOR,
                f"{key}: origem E2/baseline (fora do grão transacional); "
                f"{len(conteudo)} itens em `{nome}`",
            )
    faltando = ", ".join(f"`{n}`" for n in esperados) or "nenhum contêiner conhecido"
    return (
        NAO_VERIFICAVEL,
        f"{key}: shape não reconhecido (esperava {faltando}); cobertura não afirmável",
    )


def e4_bucket_verdict(key: str, payload, collisions: list) -> tuple[str, str]:
    """Um dos 5 vereditos por balde E4 (dispatch por natureza do balde)."""
    if not isinstance(payload, dict):
        return NAO_VERIFICAVEL, "balde ausente/ilegível"
    if key in _TX_BUCKETS:
        return _tx_bucket_verdict(payload)
    if key == "investimentos":
        return _investimentos_verdict(payload, collisions)
    return _non_ledger_verdict(key, payload)
