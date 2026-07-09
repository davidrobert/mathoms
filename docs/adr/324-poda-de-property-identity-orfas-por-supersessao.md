---
id: ADR-324
type: adr
title: "Poda de PropertyIdentity órfãs por supersessão reconciliada (soft-delete + re-aponte de override)"
status: Proposto
date: "2026-07-09"
relates_to: ["[[ADR-215]]", "[[ADR-225]]", "[[ADR-246]]", "[[ADR-265]]", "[[ADR-276]]", "[[ADR-282]]"]
tags:
  - type/adr
  - status/proposto
  - area/db
  - area/pipeline
---

# ADR-324 — Poda de PropertyIdentity órfãs por supersessão reconciliada

**Status:** Proposto · **Data:** 2026-07-09

## Contexto

`consolidate_baseline` step 3 persiste 1 row de `property_identity` por
declarante×variação via `match_or_create` (commit eager,
`db_property_identity_resolver.py`). O step 3b roda o dedup ADR-246/265
**só em memória**: `DedupResult.dropped_property_ids`
(`pipeline/domain/services/imoveis_dedup.py`) é calculado e descartado —
o DB nunca é podado. Órfãs (perdedoras de dedup) acumulam a cada run,
aparecem com valor 0 e poluem a projeção de excluídos. A [[A28.l7]]
(#779) dedupou **apenas a projeção** e registrou o débito estrutural:
"soft-delete `superseded_by` > hard delete; migration + backfill
idempotente + re-aponte de FK de `workspace_property_overrides` para o
vencedor; respeitar imutabilidade de `codigo_rfb` ([[ADR-225]])".
Follow-up nomeado do [[PLAN-report-trust]]. Co-design 2026-07-09:
`data-engineer` (veredito incorporado integralmente).

## Decisão

1. **Duas colunas, papéis distintos** (migration aditiva nullable, sem
   backfill na migration): `superseded_at DateTime(tz) NULL` = **estado**
   (predicado único de read-path) e `superseded_by_id String(36)`
   FK→`property_identity.id` **ON DELETE SET NULL** = **linhagem** ao
   vencedor. Deletar um vencedor anula o ponteiro sem ressuscitar a
   perdedora — a lição do bug de quarentena da [[A26.l4]] ([[ADR-282]]
   §5) fica codificada no schema, não só no filtro.
2. **Reconcile, não mark** — port novo e focado (ISP, ADR-089/097 D3)
   `PropertySupersessionWriter.reconcile_supersession(workspace_id,
   winner_by_pid)`, chamado no step 3b com o map completo de
   `resolve_dedup_winner_by_property_id` (função pura). O adapter DB
   **seta** `superseded_*` nas perdedoras correntes **e limpa** nas rows
   que deixaram de ser perdedoras — estado = função pura do dedup
   corrente. IRPF cresce ano a ano e a eleição de vencedor pode flipar
   entre runs; mark-only esconderia o vencedor novo (o bug original,
   invertido). Idempotente: 2 runs consecutivos → zero writes no 2º.
3. **Re-aponte de override com regra de trust** — override da perdedora
   migra para a vencedora com precedência `user_manual` >
   `fuzzy_match_accepted` > `migration_keyword`; empate de trust →
   vencedora prevalece. Conflito com classificações divergentes aplica a
   de maior trust ao override da vencedora **com audit log obrigatório**
   (nunca descarta `user_manual` silenciosamente — mudaria classificação
   econômica e violaria o "zero mudança de valor" da A28.l7). **Ordem de
   statement invariante:** DELETE do override da perdedora **antes** do
   UPDATE da vencedora (o partial-unique de 1 `residencia_principal` por
   workspace é checado por-statement).
4. **Read-path com helper único + teste de inércia** — helper
   compartilhado (`live_property_identities`) com predicado
   `superseded_at IS NULL` nos 4 read-sites de negócio
   (`real_estate_e5_integration`, `property_repository`,
   `apolice_reconciliation_runner`, endpoints). **LGPD export intocado**
   (exporta tudo, LGPD Art. 18). Teste comportamental de inércia
   espelhando `test_override_orphan_quarantine_inert`: row superseded
   ausente nos 4 read-sites E presente no export.
5. **Backfill one-shot dry-run-first** — script idempotente em `dev/`
   (padrão A32.l1) que **re-roda** `resolve_dedup_winner_by_property_id`
   sobre as rows do DB (+ valores do baseline mais recente, só para a
   eleição) e chama o mesmo `reconcile_supersession`. Nunca deriva o
   mapping do artifact E1.5c (snapshot stale/policy antiga → backfill
   não-idempotente). Sem baseline → eleição degrada determinística
   (ano, titular, ordem estável) com log.

## Fora de escopo

- **Órfã sem vencedor** (imóvel que saiu do IRPF em ano posterior): não é
  duplicata — é ativo histórico legítimo; permanece live. Relevância
  temporal é problema distinto (exigiria `last_seen_year`, ADR própria).
- Rows `low_confidence`/`endereco_canonical=None` nunca agrupam
  (`_identity_key` → None) e portanto nunca são superseded — intencional,
  não bug.
- `dev/dedup_property_identity.py` continua como remediação manual de
  duplicatas (hard-delete); o ON DELETE SET NULL o torna seguro contra
  dangling. Convergência para o caminho de supersessão é follow-up.

## Alternativas rejeitadas

- **Hard delete** (padrão `dev/dedup_property_identity.py`): perde trilha
  e cobertura LGPD; lean da A28.l7 é explícito contra.
- **Só `superseded_by_id` self-FK como predicado**: ON DELETE SET NULL
  ressuscitaria perdedoras quando o vencedor é deletado — classe do bug
  A26.l4.
- **Mark-only no step 3b**: não flip-safe (vencedor novo ficaria
  escondido quando a eleição muda entre runs).
- **Backfill derivado do artifact E1.5c**: acopla à policy que gerou o
  snapshot; re-rodar a mesma função pura dos dois lados é a única forma
  de impossibilitar divergência forward↔backfill.
- **`with_loader_criteria` global / DB VIEW**: filtraria LGPD export e
  dev scripts (que devem ver tudo) / briga com `create_all` dos testes.
- **Índice parcial novo**: <50 rows/workspace, todo read-site já filtra
  por `workspace_id` indexado — YAGNI.
- **Status quo (só projeção, A28.l7)**: acúmulo monotônico + todo
  consumidor novo precisa filtrar defensivamente.

## Consequências

- Migration reversível (drop de 2 colunas); rollout sem janela de
  regressão: migration → código (reconcile + filtros) → backfill.
- `DB_SCHEMA_REFERENCE.md` atualizado; teste de migration com
  `pytestmark = pytest.mark.migration` (ADR-210).
- Critério de aceite: teste de flip (run 1 elege A; run 2 com valor
  maior em B → B live, A superseded, override segue B) · idempotência
  (2º run = no-op) · 4 ramos da regra de trust + sub-caso
  `residencia_principal` · inércia nos 4 read-sites + presença no LGPD
  export · golden de valor E5 intocado · backfill `--apply` idempotente.
