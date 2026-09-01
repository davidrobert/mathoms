"""Primitivas compartilhadas: conversao, veredito e acesso pinado no run."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path


def _cents(v) -> int | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return int((Decimal(str(v)) * 100).quantize(Decimal("1")))
    except Exception:
        return None


def _rotulo(n_comparado: int, n_esperado: int, divergentes: int, n_falsificavel: int) -> str:
    if n_comparado == 0:
        return "INAPLICAVEL ⛔ — comparacao vazia nao e veredito."
    if n_comparado < n_esperado:
        return "INAPLICAVEL ⛔ — cobertura parcial nao e veredito."
    if n_falsificavel == 0:
        return "INAPLICAVEL ⛔ — nenhum elemento da populacao podia exibir a falha."
    return f"DIVERGE ⚠️ {divergentes}" if divergentes else "FECHA ✅"


def _cobertura(n_falsificavel: int, n_comparado: int) -> str:
    """Fracao da populacao examinada que podia REPROVAR. `FECHA` sobre 10% nao
    e o mesmo fato que `FECHA` sobre 100%, e a linha tem de deixar isso visivel."""
    if n_comparado <= 0:
        return "—"
    return f"{100.0 * n_falsificavel / n_comparado:.0f}%"


def veredito(
    nome: str,
    n_comparado: int,
    n_esperado: int,
    divergentes: int,
    *,
    n_falsificavel: int,
    nota: str = "",
) -> None:
    """Guarda anti-vacuo do FORMATO de saida — §10 do `U2` item 2, + `LC9-04/05/10`.

    Tres denominadores, nao dois. O par `(n_comparado, n_esperado)` responde
    *cobertura*; ele nao responde *poder*. No `U5` o `X4` publicou
    `FECHA ✅ n=10/10` sobre uma populacao em que **9 de 10** literais sao
    carimbados pelo backend a partir do MESMO payload que o check rele — orfao
    impossivel por construcao. Cobertura cheia, poder discriminante 1/10.
    `n_falsificavel` e a contagem de elementos que PODIAM reprovar; zero ⇒
    `INAPLICAVEL`, jamais ✅. Keyword-only de proposito: o autor do check tem de
    responder a pergunta, e parametro opcional e como esta guarda ficaria inerte.
    """
    # Nenhum check imprime ✅ sem publicar os TRES numeros na MESMA linha.
    par = (
        f"n_comparado={n_comparado} n_esperado={n_esperado} "
        f"n_falsificavel={n_falsificavel} ({_cobertura(n_falsificavel, n_comparado)} do examinado)"
    )
    rotulo = _rotulo(n_comparado, n_esperado, divergentes, n_falsificavel)
    print(f"\n**{nome}: {rotulo} — {par}.** {nota}")


def _db():
    """Imports pesados ficam locais: `veredito`/`_cents` sao puros e testaveis
    sem arrastar engine, settings e Fernet para dentro da suite."""
    from sqlalchemy import text

    from backend.app.core.database import SyncSessionLocal
    from dev.certify_ledger_local import _artifact_rows, _decrypt, _latest_by_canonical

    return text, SyncSessionLocal, _artifact_rows, _decrypt, _latest_by_canonical


def procedencia(modulo: str) -> None:
    """Imprime o DB resolvido ANTES de qualquer numero."""
    # `_PROJECT_ROOT` deriva da localizacao do modulo, nao do cwd: rodar de dentro
    # de um worktree aponta para o `mathoms.db` VAZIO dele e mede o nada em
    # silencio. Medido no `U4`.
    from backend.app.core.config import settings

    print(f"<!-- db={settings.sync_database_url} · modulo={Path(modulo).resolve()} -->")


def e4_do_run(s, ws: str, run: str) -> dict[str, dict]:
    """Baldes E4 PINADOS no run — sem o pin compara-se o E4 de outro run."""
    _t, _S, _rows, _dec, _latest = _db()
    latest = _latest(_rows(s, ws, ("categorize_transactions",), run_id=run))
    return {k: _dec(r.content_json) for (_st, k), r in latest.items()}


def mes_do_label(lbl: str) -> str:
    """view-model rotula `YY/MM`; o E4 usa `YYYY-MM`. Sem esta traducao a
    intersecao e VAZIA e o check reporta 100% de divergencia que e dele."""
    aa, _, mm = lbl.partition("/")
    return f"20{aa}-{mm}"


def cat_despesa(lbl: str) -> str:
    """`Das Simples` -> `das_simples` (o dataset titula; o E4 usa snake_case)."""
    return lbl.strip().lower().replace(" ", "_")
