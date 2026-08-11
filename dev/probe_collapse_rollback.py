"""Ensaio de rollback do enforce de colapso — eixo (4) do §Critério de saída da [[A40.l2]].

A §Não-decisão da [[ADR-364]] recusa rollout percentual com o argumento de que *"o undo
existe (flag off + re-run reconstrói o artefato E3)"*. **Undo nunca executado é premissa, não
propriedade** — este probe executa e mede.

Roda três vezes o MESMO corpus real (payloads E2/baseline lidos do DB), variando só o
enforce, sobre `InMemoryArtifactStore`:

    OFF → A    ·    ON → B    ·    OFF → C

e afirma `C == A` byte-a-byte nos campos que o colapso pode mover, mais `B != A` (senão o
ensaio provaria a reconstrução de um corte que nunca houve).

Zero-write: nada toca o DB. A leitura da flag NÃO é exercitada aqui — ela tem gate próprio
em `tests/unit/pipeline/test_collapse_shadow.py` (AST + comportamental) e em
`backend/tests/test_collapse_enforce_write_path.py`. Este probe mede o artefato.

Uso:

    python3 dev/probe_collapse_rollback.py <email|uuid>

Exit 0 = undo provado · 1 = undo NÃO reconstrói · 2 = INDETERMINADO (corpus sem corte).
PII-safe: só contagens, chaves de artefato e digests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_DEV = _REPO_ROOT / "dev"
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

# Campos que o colapso pode mover. Comparar o payload inteiro faria o ensaio falhar por
# ruído (timestamps, ordem de chave irrelevante) e esconderia o sinal.
_CAMPOS = ("transacoes", "remocoes", "saldo_final", "total_creditos", "total_debitos")


def _adapter(ctx, *, enforce: bool):
    from pipeline.domain.services.cross_document_collapse_types import OverrideRetentionGuard
    from pipeline.domain.services.cross_document_collapser import CrossDocumentCollapser
    from scripts.reconcile_transactions import _e3_build_adapter

    return _e3_build_adapter(
        ctx,
        cross_document_collapser=CrossDocumentCollapser(
            retention_guard=OverrideRetentionGuard.sem_overrides()
        ),
        collapse_enforce=enforce,
    )


def _uma_passada(session, ws: str, *, enforce: bool) -> dict:
    """`{artifact_key: {campo: valor}}` de um run completo do E3 sobre o corpus real."""
    import certify_ledger_local as harness

    from pipeline.artifact_store import InMemoryArtifactStore
    from scripts.reconcile_transactions import _e3_run_reconciliation

    store = InMemoryArtifactStore()
    harness._seed_store(
        store,
        harness._latest_payloads(session, ws, harness._E2_STAGES),
        harness._latest_payloads(session, ws, harness._BASELINE_STAGES),
    )
    ctx = harness._build_context(session, ws, None, store)
    adapter, canon = _adapter(ctx, enforce=enforce)
    _e3_run_reconciliation(adapter, store, canon)
    return {
        key: {campo: store.read("E3", key).get(campo) for campo in _CAMPOS}
        for key in sorted(store.list_keys("E3"))
    }


def _fingerprint(artefatos: dict) -> str:
    return json.dumps(artefatos, sort_keys=True, default=str)


def _txs(artefatos: dict) -> int:
    return sum(len(a.get("transacoes") or []) for a in artefatos.values())


def _cortes(artefatos: dict) -> int:
    return sum(
        ((a.get("remocoes") or {}).get("cross_document_collapse") or {}).get("count", 0)
        for a in artefatos.values()
    )


def _divergencias(a: dict, c: dict) -> list[str]:
    """Chaves em que o rollback NÃO reproduziu o estado original."""
    if set(a) != set(c):
        return [f"conjunto de artefatos difere: {sorted(set(a) ^ set(c))}"]
    return [
        f"{key}.{campo}"
        for key in sorted(a)
        for campo in _CAMPOS
        if _fingerprint(a[key][campo]) != _fingerprint(c[key][campo])
    ]


def _linha(rotulo: str, artefatos: dict) -> str:
    return (
        f"{rotulo} → artefatos={len(artefatos)} "
        f"txs={_txs(artefatos)} cortes={_cortes(artefatos)}"
    )


# "0 → 0 → 0" com `C == A` provaria a reconstrução de um corte inexistente. O eixo pede o undo
# de uma remoção REAL, então corpus sem corte é INDETERMINADO, nunca verde.
def _indeterminado(antes: dict, com: dict) -> str | None:
    if _cortes(com) == 0:
        return "o enforce não cortou nada neste corpus"
    if _fingerprint(com) == _fingerprint(antes):
        return "ON produziu artefato idêntico a OFF"
    return None


def _emitir(antes: dict, com: dict, depois: dict) -> int:
    print(_linha("OFF ", antes))
    print(_linha("ON  ", com))
    print(_linha("OFF'", depois))

    incerto = _indeterminado(antes, com)
    if incerto:
        print(f"VEREDITO: INDETERMINADO — {incerto}")
        return 2

    divergencias = _divergencias(antes, depois)
    if divergencias:
        print(f"VEREDITO: undo NÃO reconstrói — {len(divergencias)} campo(s) divergem")
        for d in divergencias[:10]:
            print(f"  {d}")
        return 1
    print(f"VEREDITO: undo RECONSTRÓI o E3 ({_cortes(com)} row(s) cortadas e devolvidas)")
    return 0


def main() -> int:
    import certify_ledger_local as harness
    import resolve_ledger

    from backend.app.core.database import SyncSessionLocal

    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    with SyncSessionLocal() as session:
        ws = resolve_ledger._resolve_id(session, sys.argv[1])
        if ws is None:
            print(f"workspace não resolvido: {sys.argv[1]}")
            return 2
        antes = _uma_passada(session, ws, enforce=False)
        com = _uma_passada(session, ws, enforce=True)
        depois = _uma_passada(session, ws, enforce=False)
    _ = harness  # o import valida que o harness está disponível antes das três passadas
    return _emitir(antes, com, depois)


if __name__ == "__main__":
    raise SystemExit(main())
