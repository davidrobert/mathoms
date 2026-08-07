"""A adjudicação por hash do gate de colapso está viva? ([[A40.l2]] · pré-condição do PR3b).

O gate D1 **descobre** override por `gate_digest` e **adjudica** por `_hash_v2` — o digest é
invariante sob re-ancoragem, o hash não. Isso pressupõe que a âncora dos overrides ativos casa
alguma row do E3, o que precisa ser **medido**, não assumido: "5 overrides julgáveis" significa
"tem snapshot", não "tem âncora que casa row".

Precisa ser re-executado **antes do flip**: "vazio" é propriedade do corpus **e do tempo**
([[ADR-364]] §5), e override nasce continuamente.

Uso (zero-write; não roda pipeline em produção, semeia `InMemoryArtifactStore`):

    python3 dev/probe_collapse_adjudication.py <email|uuid>

Exit 0 = veredito emitido · 2 = INDETERMINADO (instrumento não observou nada).
PII-safe: só contagens e nomes de classe.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_SKILL_SCRIPTS = _REPO_ROOT / ".claude" / "skills" / "ledger-certify" / "scripts"
if str(_SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SKILL_SCRIPTS))

_CLASSES = (
    "casou_sobrevivente",
    "casou_removido",
    "casou_corpus_fora_de_candidato",
    "casou_nada",
    "sem_v2",
)


def _instalar_captura(modulo):
    """Colapsador que REGISTRA os statements que recebe e delega ao real."""
    # `ReconciliationStoreResult` não carrega os statements — só contagens. Capturar onde o
    # colapsador de produção os recebe é a única forma de obtê-los sem segunda derivação;
    # re-parsear o payload E3 seria o instrumento paralelo que a §D5 da lane proíbe.
    real = modulo.CrossDocumentCollapser
    capturados: list = []

    class _Captura(real):
        def measure(self, statements):
            stmts = list(statements)
            capturados.extend(stmts)
            return super().measure(stmts)

    modulo.CrossDocumentCollapser = _Captura
    return real, capturados


def _rederivar(session, ws: str):
    """Statements pré-colapso, pelo caminho real do instrumento (zero-write)."""
    import certify_ledger_local as cli

    import pipeline.domain.services.cross_document_collapser as mod

    real, capturados = _instalar_captura(mod)
    try:
        cli._rederive(session, ws, None)
    finally:
        mod.CrossDocumentCollapser = real
    return capturados


def _hashes_por_papel(statements) -> tuple[set, set]:
    """``(sobreviventes, removidos)`` — `_hash_v2` por papel no colapso."""
    from pipeline.domain.services.cross_document_collapser import _row_hash

    sobrevive, remove = set(), set()
    for rows, keep in _buckets(statements):
        hashes = [_row_hash(tx, stmt) for stmt, tx in rows]
        sobrevive.update(hashes[:keep])
        remove.update(hashes[keep:])
    return sobrevive, remove


def _buckets(statements):
    """``(rows, quantas_sobrevivem)`` por bucket de proveniência de cada candidato."""
    from pipeline.domain.services.cross_document_collapser import _group_by_key

    for group in _group_by_key(statements):
        keep_native, keep_llm = group.keep_split()
        yield group.native_rows, keep_native
        yield group.llm_rows, keep_llm


def _corpus(statements) -> set:
    from pipeline.domain.services.cross_document_collapser import _row_hash

    return {_row_hash(tx, s) for s in statements for tx in s.transactions}


def _ancoras(override) -> tuple:
    return (override.natural_key_hash, override.transaction_hash)


def _classificar(override, sobrevive: set, remove: set, corpus: set) -> str:
    """Classe de adjudicação de UM override — fail-closed: desconhecido não é seguro."""
    if (getattr(override, "hash_version", None) or 0) < 2:
        return "sem_v2"
    ancoras = [h for h in _ancoras(override) if h]
    if any(h in sobrevive for h in ancoras):
        return "casou_sobrevivente"
    if any(h in remove for h in ancoras):
        return "casou_removido"
    if any(h in corpus for h in ancoras):
        return "casou_corpus_fora_de_candidato"
    return "casou_nada"


def _overrides_ativos(session, ws: str) -> list:
    from sqlalchemy import select

    from backend.app.models.transaction_override import TransactionOverride

    stmt = select(TransactionOverride).where(
        TransactionOverride.workspace_id == str(ws),
        TransactionOverride.orphaned_at.is_(None),
    )
    return list(session.execute(stmt).scalars())


def _emitir(classes: Counter, corpus: set, ativos: list) -> int:
    """Veredito — ou `INDETERMINADO`, que é um estado próprio e não um zero."""
    # `0` por "não observei" e `0` por "observei e não achei" são indistinguíveis no número.
    # A 1ª execução deste probe imprimiu MORTA com corpus vazio; publicar aquele zero teria
    # matado um desenho correto.
    if not corpus or not ativos:
        print("VEREDITO: INDETERMINADO — instrumento não observou corpus/overrides")
        return 2
    vivos = classes["casou_sobrevivente"] + classes["casou_removido"]
    em_risco = "SIM" if vivos else "NAO"
    print(f"VEREDITO: join por hash {'VIVO' if _join_vivo(classes) else 'MORTO'}")
    print(f"          override em candidato de colapso: {em_risco} ({vivos})")
    return 0


def _join_vivo(classes: Counter) -> bool:
    """Alguma âncora casa alguma row — separa 'corpus limpo' de 'join morto'."""
    return sum(classes[c] for c in _CLASSES[:3]) > 0


def _medir(session, ws: str) -> int:
    """Mede e emite — separado de ``main`` para caber no limite de corpo."""
    stmts = _rederivar(session, ws)
    sobrevive, remove = _hashes_por_papel(stmts)
    corpus = _corpus(stmts)
    ativos = _overrides_ativos(session, ws)
    print(
        f"statements {len(stmts)} · corpus {len(corpus)} · sobreviventes "
        f"{len(sobrevive)} · removidos {len(remove)} · overrides {len(ativos)}"
    )
    classes = Counter(_classificar(o, sobrevive, remove, corpus) for o in ativos)
    for nome in _CLASSES:
        print(f"  {nome}: {classes[nome]}")
    return _emitir(classes, corpus, ativos)


def main() -> int:
    import resolve_ledger

    from backend.app.core.database import SyncSessionLocal

    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    if not alvo:
        print("uso: python3 dev/probe_collapse_adjudication.py <email|uuid>")
        return 1
    with SyncSessionLocal() as session:
        ws = resolve_ledger._resolve_id(session, alvo)
        if ws is None:
            print(f"workspace não encontrado: {alvo}")
            return 1
        return _medir(session, str(ws))


if __name__ == "__main__":
    raise SystemExit(main())
