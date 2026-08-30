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


def _rotulo(n_comparado: int, n_esperado: int, divergentes: int) -> str:
    if n_comparado == 0:
        return "INAPLICAVEL ⛔ — comparacao vazia nao e veredito."
    if n_comparado < n_esperado:
        return "INAPLICAVEL ⛔ — cobertura parcial nao e veredito."
    return f"DIVERGE ⚠️ {divergentes}" if divergentes else "FECHA ✅"


def veredito(
    nome: str, n_comparado: int, n_esperado: int, divergentes: int, nota: str = ""
) -> None:
    """Guarda anti-vacuo do FORMATO de saida — §10 do `U2`, item 2."""
    # Nenhum check imprime ✅ sem publicar o par `(n_comparado, n_esperado)` na
    # MESMA linha; comparacao vazia sai `INAPLICAVEL`, nunca verde e nunca achado.
    par = f"n_comparado={n_comparado} n_esperado={n_esperado}"
    print(f"\n**{nome}: {_rotulo(n_comparado, n_esperado, divergentes)} — {par}.** {nota}")


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
