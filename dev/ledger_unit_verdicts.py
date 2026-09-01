"""Vereditos por unidade da ledger-certify: um grupo E3 ou um balde E4.

Extraído de ``dev.ledger_certify_core`` em A42.l19, quando o núcleo cruzou as
500 linhas. O seam é natural: aqui mora a **rubrica** (que veredito uma unidade
merece); lá ficam drift, montagem do report e render. Funções puras — sem I/O,
sem DB.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
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


@dataclass(frozen=True)
class NonLedgerChecker:
    """Checker DECLARADO de um balde fora do grão transacional. Duas coisas, porque
    contar sem dizer de onde o balde vem é o que produziu a glosa falsa da A42.l3:

    - ``containers``: onde contar, POR CHAVE (A42.l19) — mesmo discriminador que o
      guard de escrita usa, a artifact_key e não o shape. Sondar
      `dados`/`apolices`/`composicao` no payload imprimia "coberto · 0 itens" para
      `patrimonio` e `fluxo_mensal_detalhado`, que não têm nenhum dos três.
    - ``proveniencia``: por que a contagem NÃO é prova de conservação NESTE balde. Era
      uma frase única (*"origem E2/baseline (fora do grão transacional)"*) carimbada
      nos quatro, e ela é **factualmente falsa** para `fluxo_mensal_detalhado`.
    """

    containers: tuple[str, ...]
    proveniencia: str


# Registry `{balde → checker}` com default **`não-verificável`** (LC05/LC5-06): balde
# novo sem checker declarado aparece como lacuna, nunca como aprovação.
_NON_LEDGER_CHECKERS: dict[str, NonLedgerChecker] = {
    "patrimonio": NonLedgerChecker(
        ("patrimonio_por_ano", "declarations"),
        "origem baseline/IRPF (E1.5) — fora do grão transacional",
    ),
    "fluxo_mensal_detalhado": NonLedgerChecker(
        ("meses_ordenados",),
        "derivado da MESMA população classificada (`CashFlowBuilder`), não de "
        "E2/baseline — a conservação dele é a de `despesas`+`receitas`, e contar "
        "meses não a prova",
    ),
    "seguros": NonLedgerChecker(
        ("apolices", "dados"),
        "origem E2 (`extract_comprovantes_bens`) — fora do grão transacional",
    ),
    "pontos_milhas": NonLedgerChecker(
        ("dados",),
        "placeholder do legado (sempre regenerado vazio) — 0 itens aqui não é medida",
    ),
}


def _first_container(payload: dict, nomes: tuple[str, ...]) -> tuple[str, int] | None:
    """Primeiro contêiner PRESENTE e o seu tamanho. Contêiner vazio devolve
    ``(nome, 0)``; ausente devolve ``None`` — os dois caíam no mesmo `[]` antes."""
    for nome in nomes:
        conteudo = payload.get(nome)
        if isinstance(conteudo, (list, dict, tuple, str)):
            return nome, len(conteudo)
    return None


def _non_ledger_verdict(key: str, payload: dict) -> tuple[str, str]:
    """Balde fora do grão transacional: conta o contêiner que o CHECKER da chave
    declara, e diz a proveniência **daquele** balde. Chave sem checker, ou shape não
    reconhecido, devolve `não-verificável` e nunca `coberto`: dizer "coberto · 0 itens"
    sobre payload que esta função não sabe ler afirma cobertura que não houve — era o
    caso dos 87 itens do `patrimonio` (A42.l19)."""
    checker = _NON_LEDGER_CHECKERS.get(key)
    if checker is None:
        return NAO_VERIFICAVEL, f"{key}: sem checker declarado no registry; nada afirmável"
    achado = _first_container(payload, checker.containers)
    if achado is None:
        faltando = ", ".join(f"`{n}`" for n in checker.containers)
        return NAO_VERIFICAVEL, f"{key}: shape não reconhecido (esperava {faltando})"
    nome, n = achado
    return COBERTO_SEM_VALOR, f"{key}: {checker.proveniencia}; {n} itens em `{nome}`"


def e4_bucket_verdict(key: str, payload, collisions: list) -> tuple[str, str]:
    """Um dos 5 vereditos por balde E4 (dispatch por natureza do balde)."""
    if not isinstance(payload, dict):
        return NAO_VERIFICAVEL, "balde ausente/ilegível"
    if key in _TX_BUCKETS:
        return _tx_bucket_verdict(payload)
    if key == "investimentos":
        return _investimentos_verdict(payload, collisions)
    return _non_ledger_verdict(key, payload)
