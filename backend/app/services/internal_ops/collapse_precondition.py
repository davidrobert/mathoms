"""Pré-condição do enforce de colapso cross-documento ([[A40.l2]] D1 · [[ADR-354]]).

READ-ONLY. Responde uma pergunta: **algum override ativo ancora numa row que o
colapsador removeria?** Enquanto a resposta for sim, o enforce não pode ligar — a
remoção órfanaria a categorização manual do usuário.

O join **não é por igualdade de hash**. Duas razões medidas em 2026-08-05:

1. ``transaction_overrides.transaction_hash`` é **namespace de versão mista** (row
   pré-cutover carrega ``_hash_v1``, pós-cutover ``_hash_v2``), então interseção
   contra um conjunto v2 dá vazio **por incompatibilidade de versão**, não por corpus.
2. O subsistema de override tem **hasher próprio, sem** o gate ``_has_discriminants``
   do item E4 — logo row de perna LLM (titular vazio) **pode** ancorar override em v2,
   com hash degenerado. Gate construído sobre "a perna LLM não tem âncora v2" nasce
   cego na classe exata que o enforce apaga.

Em vez disso, o backend recompõe o ``gate_digest`` (direction-free, provenance-free)
das **colunas de snapshot da [[ADR-282]]** e cruza com o que o pipeline emite. Imune a
versão de hash, imune ao gate de discriminantes, sem PII cruzando o boundary.

**Descoberta por digest, adjudicação por hash.** O digest acima é
``(data, cents, moeda, descricao_norm)`` — as duas pernas do mesmo evento o compartilham
**por definição de candidato**, e re-ancorar no sobrevivente não muda nenhum dos quatro
componentes. Um predicado que só olhasse o digest seria **inalcançável por construção**:
o override seguiria ``hit`` para sempre e a única saída seria quarentenar, que a
[[ADR-364]] §2 proíbe como forma de quitação. Então o digest **descobre** o override em
risco e o ``survivor_hash`` **adjudica**: quem já ancora a row que sobrevive não órfãna.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.internal_ops.results import OpResult
from pipeline.domain.services.cross_document_collapser import gate_key_digest

_ACTION = "override.collapse_precondition"
# `tx_data` é `String(10)`, largura que acomoda `YYYY-MM-DD` E `DD/MM/YYYY` igualmente —
# o tipo não discrimina, então a forma é contada, não presumida.
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class PreconditionReport:
    """Contagens PII-free — vai para ``pipeline_stage_logs.output_summary`` e para o `OpResult`."""

    overrides_ativos: int = 0
    alvos_do_colapsador: int = 0
    hits: int = 0
    hits_ancora_indecidivel: int = 0
    quarentenados_atingidos: int = 0
    # Ativos sem snapshot utilizável: o gate NÃO consegue julgá-los. Contá-los à parte
    # é o que separa "corpus limpo" de "não consegui olhar" — sem isso um workspace
    # cujos overrides não têm snapshot devolvia `hits=0 ⇒ liberado`.
    sem_snapshot: int = 0
    tx_data_nao_iso: int = 0
    # Vivacidade do join: dos que TÊM snapshot, quantos casam alguma row do E3. Se
    # esta fração é ~0, `hits=0` é vácuo — o join nunca casa, não há segurança.
    snapshot_casa_corpus: int = 0
    # Rows do E3 observadas. `0` significa "não olhei", e é o que separa corpus limpo de
    # medição ausente: `evaluate(db, ws, [], frozenset())` devolvia `liberado` e assim um
    # run com a flag de measure DESLIGADA autorizava o flip destrutivo.
    corpus_observado: int = 0
    # Overrides que o digest descobriu em alvo mas o hash absolveu — já ancoram a row
    # sobrevivente. Contado à parte porque é a escapatória que torna o gate alcançável, e
    # no corpus dogfood ela é exercitada por ZERO overrides (medido 2026-08-07).
    absolvidos_por_sobrevivente: int = 0

    @property
    def medido(self) -> bool:
        """O colapsador de fato observou o corpus deste run."""
        return self.corpus_observado > 0

    @property
    def com_snapshot(self) -> int:
        """Ativos que o gate consegue julgar."""
        return self.overrides_ativos - self.sem_snapshot

    # Universal, não existencial: sob `> 0`, com 5 ativos e 1 casando, esse único match
    # certificaria vivacidade e os 4 que o join não vê entrariam no `hits == 0` como corpus
    # limpo. Medido no dogfood em 2026-08-07: 4 de 5 casam ⇒ a forma universal REPROVA hoje,
    # e o 1 que não casa é exatamente o override que o gate não sabe julgar.
    @property
    def vivacidade_universal(self) -> bool:
        """Todo override julgável casou alguma row do corpus deste run."""
        return self.snapshot_casa_corpus == self.com_snapshot

    def clausulas_reprovadas(self) -> tuple[str, ...]:
        """Cláusulas que reprovaram — fonte ÚNICA do predicado e da mensagem de erro."""
        # Derivar `liberado` daqui impede o modo de falha de manter duas listas: cláusula
        # nova entra no predicado e na prosa no mesmo edit, ou em nenhum dos dois.
        reprovadas = []
        if not self.medido:
            reprovadas.append("nao_medido")
        if self.hits:
            reprovadas.append(f"hits={self.hits}")
        if self.sem_snapshot:
            reprovadas.append(f"sem_snapshot={self.sem_snapshot}")
        if self.tx_data_nao_iso:
            reprovadas.append(f"tx_data_nao_iso={self.tx_data_nao_iso}")
        if not self.vivacidade_universal:
            reprovadas.append(f"vivacidade={self.snapshot_casa_corpus}/{self.com_snapshot}")
        return tuple(reprovadas)

    @property
    def liberado(self) -> bool:
        """``True`` ⇒ as cinco cláusulas passam. Cumulativo, nunca só ``hits == 0``."""
        return not self.clausulas_reprovadas()

    def as_details(self) -> dict:
        return {
            "overrides_ativos": self.overrides_ativos,
            "alvos_do_colapsador": self.alvos_do_colapsador,
            "hits": self.hits,
            "hits_ancora_indecidivel": self.hits_ancora_indecidivel,
            "quarentenados_atingidos": self.quarentenados_atingidos,
            "sem_snapshot": self.sem_snapshot,
            "tx_data_nao_iso": self.tx_data_nao_iso,
            "snapshot_casa_corpus": self.snapshot_casa_corpus,
            "corpus_observado": self.corpus_observado,
            "absolvidos_por_sobrevivente": self.absolvidos_por_sobrevivente,
            "medido": self.medido,
            "liberado": self.liberado,
            "clausulas_reprovadas": list(self.clausulas_reprovadas()),
        }


def _override_gate_digest(override: TransactionOverride) -> str | None:
    """Digest do override pelas colunas de snapshot; ``None`` se o snapshot falta."""
    if not override.tx_data or override.tx_valor_cents is None:
        return None
    return gate_key_digest(
        data_iso=override.tx_data,
        valor_cents=override.tx_valor_cents,
        moeda=override.tx_moeda or "",
        descricao=override.tx_descricao,
    )


def _sem_ancora_v2(override: TransactionOverride) -> bool:
    """Sem âncora v2 utilizável — `hash_version=1` conta, mesmo com hash preenchido."""
    # `natural_key_hash is None` sozinho é proxy errado: row com hash preenchido em
    # `hash_version=1` é v1 disfarçada e igualmente indecidível.
    return override.natural_key_hash is None or (override.hash_version or 0) < 2


def _ancora_indecidivel(override: TransactionOverride) -> bool:
    """Sem âncora v2 E sem snapshot — não dá para decidir, então bloqueia."""
    # Fail-closed deliberado: a polaridade de um gate que BLOQUEIA é sobre-detectar.
    # Over-match é adjudicável à mão em poucas rows; under-match é override órfão em
    # produção, que apaga categorização manual sem sinal.
    return _sem_ancora_v2(override) and _override_gate_digest(override) is None


def _ativos(db: Session, workspace_id: str) -> list[TransactionOverride]:
    """Overrides que o read-path ainda resolve — quarentenado é inerte por `orphaned_at`."""
    stmt = select(TransactionOverride).where(
        TransactionOverride.workspace_id == workspace_id,
        TransactionOverride.orphaned_at.is_(None),
        TransactionOverride.deleted_at.is_(None),
    )
    return list(db.execute(stmt).scalars())


def _quarentenados_atingidos(
    db: Session, workspace_id: str, alvos: dict[str, frozenset[str]]
) -> int:
    """Contagem informativa — quarentenado DEVE seguir inerte, nunca bloquear."""
    # Só por digest, deliberadamente sem a adjudicação por hash: o número existe para
    # dizer "o colapso toca dado que já foi quarentenado", e absolver por sobrevivente
    # o tornaria menos informativo sem tornar nada mais seguro (ele nunca bloqueia).
    stmt = select(TransactionOverride).where(
        TransactionOverride.workspace_id == workspace_id,
        TransactionOverride.orphaned_at.is_not(None),
    )
    return sum(1 for o in db.execute(stmt).scalars() if _override_gate_digest(o) in alvos)


def _alvos(collapse_candidates) -> dict[str, frozenset[str]]:
    """``gate_digest`` colapsável → hashes que SOBREVIVEM ao colapso daquela chave."""
    # Acesso por ATRIBUTO, nunca `getattr(..., default)`: com default, qualquer rename em
    # `CollapseCandidate` fazia `alvos = ∅ ⇒ hits = 0 ⇒ liberado=True` **em silêncio** —
    # o gate aprovava o flip destrutivo porque deixou de saber ler o candidato.
    # `AttributeError` alto é a polaridade certa (precedente [[ADR-359]]).
    alvos: dict[str, set[str]] = {}
    for c in collapse_candidates:
        if not (c.collapsible and c.gate_digest):
            continue
        # `survivor_hash` vazio = "não há sobrevivente eleito" — nunca absolve ninguém.
        alvos.setdefault(c.gate_digest, set()).update(h for h in (c.survivor_hash,) if h)
    return {digest: frozenset(hashes) for digest, hashes in alvos.items()}


def _atingido(override: TransactionOverride, alvos: dict[str, frozenset[str]]) -> bool:
    """Descoberto por digest e NÃO absolvido pelo hash do sobrevivente."""
    return _override_gate_digest(override) in alvos and not _absolvido(override, alvos)


def _absolvido(override: TransactionOverride, alvos: dict[str, frozenset[str]]) -> bool:
    """Já ancora a row que sobrevive ⇒ o colapso não o órfãna."""
    # Exige âncora v2 genuína: `hash_version=1` é v1 disfarçada, e absolver por coincidência
    # de string num namespace de versão mista seria under-match — override órfão em produção.
    if _sem_ancora_v2(override):
        return False
    return override.natural_key_hash in alvos.get(
        _override_gate_digest(override) or "", frozenset()
    )


def _build_report(
    db: Session, workspace_id: str, alvos: dict[str, frozenset[str]], corpus: frozenset[str]
) -> PreconditionReport:
    ativos = _ativos(db, workspace_id)
    indecidiveis = [o for o in ativos if _ancora_indecidivel(o)]
    casados = [o for o in ativos if _atingido(o, alvos)]
    com_snapshot = [o for o in ativos if _override_gate_digest(o) is not None]
    return PreconditionReport(
        overrides_ativos=len(ativos),
        alvos_do_colapsador=len(alvos),
        hits=len({o.id for o in casados} | {o.id for o in indecidiveis}),
        hits_ancora_indecidivel=len(indecidiveis),
        quarentenados_atingidos=_quarentenados_atingidos(db, workspace_id, alvos),
        sem_snapshot=len(ativos) - len(com_snapshot),
        tx_data_nao_iso=sum(1 for o in ativos if o.tx_data and not _ISO.fullmatch(o.tx_data)),
        snapshot_casa_corpus=sum(1 for o in com_snapshot if _override_gate_digest(o) in corpus),
        corpus_observado=len(corpus),
        absolvidos_por_sobrevivente=sum(1 for o in ativos if _absolvido(o, alvos)),
    )


def evaluate(
    db: Session, workspace_id: str, collapse_candidates, corpus_digests
) -> tuple[OpResult, PreconditionReport]:
    """Avalia a pré-condição. Read-only: não escreve, não commita, não muta override."""
    # `corpus_digests` são os gate_digest de TODAS as rows do E3 (não só as colapsáveis):
    # medem a VIVACIDADE do join E provam que a medição ocorreu. SEM default de propósito —
    # com `frozenset()` implícito, chamador que esquecesse o argumento certificava vivacidade
    # vazia e o predicado liberava o flip.
    report = _build_report(db, workspace_id, _alvos(collapse_candidates), frozenset(corpus_digests))
    if report.liberado:
        return OpResult(ok=True, details=report.as_details()), report
    erro = (
        f"enforce bloqueado — {', '.join(report.clausulas_reprovadas())} "
        "(re-ancore, quarentene, complete o snapshot ou re-rode a medição)"
    )
    return OpResult(ok=False, error=erro, details=report.as_details()), report
