---
id: ADR-282
type: adr
title: "Identidade de TransactionOverride unificada no natural_key v2 (fecha D6 da A23.l3)"
status: Decidido
phase: "A23 · pré-passo-2 B4"
date: "2026-06-08"
relates_to:
  - "[[ADR-278]]"
  - "[[ADR-255]]"
  - "[[ADR-090]]"
  - "[[ADR-186]]"
  - "[[ADR-188]]"
  - "[[ADR-212]]"
supersedes: []
superseded_by: []
aliases: ["ADR 282", "override natural_key", "D6 third hash"]
tags:
  - type/adr
  - status/proposto
  - area/data-lineage
  - area/backend
  - area/persistence
---

# ADR-282 — Identidade de `TransactionOverride` unificada no `natural_key` v2

**Status:** Decidido (A23 · pré-passo-2 B4) • **Data:** 2026-06-08 • **Relaciona**
[[ADR-278]] (B3/B4, §D6), [[ADR-255]], [[ADR-090]], [[ADR-186]], [[ADR-188]], [[ADR-212]].

> Estende [[ADR-278]] (não a reabre) para o subsistema de override/learning. Fecha a
> dívida cross-stack **D6** registrada na lane [[A23.l3]]. Co-design `data-engineer` +
> `senior-cto` registrado em 2026-06-08.

## Contexto

Existem **três** funções de identidade de transação no sistema:

1. `_hash_v1` / `compute_transaction_hash` (`pipeline/domain/services/_tx_identity.py`) —
   K4 do pipeline **congelado**: SHA-256[:16], `cents_int(abs(valor))` sem moeda/direction,
   ingere `float`. Normaliza banco/titular/tipo_conta/descricao.
2. `_hash_v2` / `compute_natural_key(HashInputs)` — promovido a **campo de contrato E2**
   pela [[A23.l3]] (B3): cents int via `Decimal(str(v)).quantize(...)`, **+moeda +direction**,
   normalização completa (inclui strip de sufixo PIX, [[ADR-255]]). Emitido no write-path E2;
   **ainda não consumido** por E4 (D4 — nullable; o **passo 2** de B4 fará E4 consumir v2).
3. `generate_transaction_hash` (`backend/app/services/transaction_service.py:17`) — **terceiro
   hash**, estruturalmente **pior que o próprio v1**: `f"{data}|{descricao}|{valor}|{banco}|{titular}"`,
   SHA-256 **full** (64 hex), `valor` string crua, **sem `tipo_conta`** e **sem nenhuma
   normalização**.

`generate_transaction_hash` é o **único** hash do subsistema de override/learning e é
**computado sobre o output E4** (pós-dedup E3, pós-categorização — a linha que o usuário
vê e corrige), não sobre o E2:

- override manual (`create_override.py`) casa `TransactionItem.transaction_hash` (de
  `load_transactions` sobre o artefato E4);
- apply retroativo de regra (`_apply_engine`) usa o mesmo `TransactionItem.transaction_hash`;
- learning loop pós-E4 (`categorization_learning_loop._tx_hash`) recomputa de
  `ClassifiedTransaction`.

Persiste em `transaction_overrides.transaction_hash` (`String(64)`, UK
`(workspace_id, transaction_hash)`). **A linha de override armazena só o hash + categorias +
`source`/`rule_id` — NÃO armazena os campos-fonte** (`data/banco/titular/tipo_conta/valor/
moeda/descricao`). É exatamente por isso que a dívida D6 existe: a linha não é re-hasheável
sem replay do E4.

### Reenquadramento do D6 (o framing da lane era impreciso)

A lane diz "overrides param de casar com v2". O override **não armazena** o K4 do pipeline,
então o passo 2 não causa colisão *direta*. Os problemas reais:

- **Bug vivo HOJE, independente do passo 2** — `generate_transaction_hash` carrega
  exatamente os defeitos que [[ADR-255]]/[[ADR-278]] corrigiram no K4: sem normalização de
  `descricao` → re-extração de extrato C6 com **drift de sufixo PIX orfaniza silenciosamente
  a categorização manual do usuário** (mesma classe do incidente ADR-255, blast radius pior
  porque some sem warning); `valor` string crua → drift de float-repr; sem `tipo_conta` →
  duas contas do mesmo membro/data/desc/valor colidem num único override.
- **Buraco de lineage** (o ponto de A23) — override com hash ad-hoc não liga de volta ao
  `natural_key` no grafo de lineage forward/reverso.
- **Ripple no passo 2** — quando E4 chavear linhas por v2, o conjunto de `generate_transaction_hash`
  muda (dedup colapsa/separa diferente) → overrides orfanizam **em massa, em silêncio**, no
  instante do flip. É o gênero do incidente "membro identity por CPF".

## Decisão

1. **Unificar a identidade.** O subsistema de override/learning passa a chavear em
   `compute_natural_key(inputs).hash` (**v2**); `generate_transaction_hash` é **deletado**
   após o cutover (não vira shim — manter "por compat" é exatamente como se chegou a três
   hashes).

2. **Identidade canônica do override = a linha E4, recomputada via v2 — NÃO o `natural_key`
   herdado do E2.** O override já vive no E4 (pós-dedup); o `natural_key` do E2 é pré-dedup e,
   sob colapso N→1 do E3, não há candidato canônico ("qual sobrevive?" é política interna de
   dedup). Recomputar v2 dos campos da própria linha E4 é determinístico, estável e **casa por
   construção com o algoritmo que o dedup E3→E4 v2 usará** (a invariante central). Usa os
   adapters D3 da [[ADR-278]] (`inputs_from_classified_tx` para o learning loop; adapter gêmeo
   `inputs_from_transaction_item` para o read-path `load_transactions`), ambos via
   `derive_direction` (D2) — incluindo o gap receita/`tipo` ausente no `TransactionItem`.

3. **Schema — linha de override auto-suficiente.** `transaction_overrides` ganha:
   - `natural_key_hash String(16)` (v2), `hash_version SmallInteger`;
   - **snapshot dos inputs do hash** (`tx_data`, `tx_banco`, `tx_titular`, `tx_tipo_conta`,
     `tx_valor_cents Integer`, `tx_moeda String(3)`, `tx_direction String(6)`, `tx_descricao Text`
     crua, pré-normalização);
   - `orphaned_at DateTime NULL`.

   **Invariante novo:** a linha de override é re-hasheável **sozinha**, sem replay de E4. Isto
   paga a dívida na raiz — a próxima versão (v3) re-hasheia da própria linha e fecha o lineage
   reverso ("este override veio de qual transação/extrato"). O custo (+8 colunas em tabela de
   baixo volume) é ruído; o ganho é estrutural. `transaction_hash` (`String(64)`) é mantido
   durante a janela e **dropado na migration destrutiva final**.

4. **Migração — coluna nova + dual-write + cutover por flag (NÃO in-place + PITR).** PITR é
   rede de **desastre de infra**, não de **bug de mapeamento de dado de usuário**. Sequência:
   - **M1 (DDL online):** `ADD COLUMN` dos campos acima; `CREATE INDEX CONCURRENTLY` em
     `(workspace_id, natural_key_hash) WHERE natural_key_hash IS NOT NULL AND deleted_at IS NULL`.
     Sem reescrever linha. Reversível trivial.
   - **Dual-write:** os 3 write-paths (`create_override`, `_apply_engine`, `learning_loop`)
     gravam ambos os hashes + snapshot. Torna o flip reversível sem perder writes feitos
     **durante** a migração.
   - **Backfill idempotente** (script fora da migration, checkpoint por workspace): replay do
     E4 corrente → recomputa v1 (velho) e v2 (novo) por linha → mapa `{v1: v2}` → preenche
     `natural_key_hash`/snapshot dos overrides com `natural_key_hash IS NULL`. **Modo
     report-only antes de escrever** (dry-run: mapeados / órfãos / colididos, inspecionado por
     humano).
   - **Dual-read transitório no match** (v2 → fallback v1-legado) durante a janela, para não
     quebrar overrides ainda-não-backfillados em runs concorrentes.
   - **Cutover de leitura por feature flag** por workspace (padrão `feature_flags_service.py` —
     registrar DEFAULT no mesmo PR) quando cobertura == 100% (exceto órfãos quarentenados).
   - **M2 (destrutiva, separada, pós-validação em prod):** drop `transaction_hash` + UK velha +
     deletar `generate_transaction_hash`. Único ponto irreversível.

5. **Política de órfão — quarentena, nunca drop, nunca silêncio.** `natural_key_hash IS NULL`
   pós-backfill = órfão (v1 não existe no E4 atual). Marca `orphaned_at`, **não deleta**.
   Read-path ignora; UI **surface** "categorização manual perdeu o vínculo — revisar". Isto
   converte a perda silenciosa de hoje em sinal visível (gancho de produto → follow-up
   `product-designer`).

6. **Política de colisão N-velho→1-novo — precedência determinística, sem perda.** `manual >
   rule`; entre dois `manual`, `created_at` mais recente vence; entre dois `rule`, idem;
   `id` (uuid) é o desempate terminal (chave total — sem flakiness sob `created_at` idêntico). O
   perdedor vira `deleted_at = now()` (soft-delete já existe, [[ADR-188]] §D1) com `notes` de
   auditoria (`"colapsado em <id> durante migração natural_key v2 (ADR-282)"`). Todas as
   colisões no report de dry-run antes do write.

6b. **Política de ambiguidade 1-velho→N-novo — quarentena, nunca palpite (emenda, co-design
   `data-engineer`+`senior-cto` 2026-06-08).** O inverso da colisão: `generate_transaction_hash`
   v1 não tem `tipo_conta` nem moeda/direction, então um único `transaction_hash` legado pode
   resolver para **N** `natural_key` v2 distintos no E4 atual (duas contas do mesmo membro/data/
   desc/valor que o v1 fundia e o v2 separa). Reancorar para um v2 arbitrário propagaria a
   categorização manual para a conta errada (gênero do incidente "membro identity por CPF"). Logo:
   v1 que mapeia para >1 `natural_key` v2 → **`orphaned_at` (quarentena), nunca reancora**.
   Bucket próprio (`ambiguous`) no report e no log.

7. **Sequenciamento — gate obrigatório.** Esta migração **DEVE aterrissar antes do passo 2**
   (flip do consumo v2 no dedup E4). Flipar o dedup enquanto o override usa
   `generate_transaction_hash` orfaniza **todo** override existente no instante do flip. Pode
   aterrissar **independente** (corrige bug vivo). O **passo 2 fica bloqueado** até: backfill
   completo + dogfood provando reancoragem ≥ limiar.

8. **Risco de correção de maior peso — quiesce de pipeline no backfill.** O learning loop
   (`source='rule'`) cria overrides **programaticamente** a cada reprocessamento de E4. Se o
   backfill roda sob reprocessamento E4 concorrente, o mapa `{v1: v2}` é computado contra um E4
   que muda sob os pés. O backfill **exige janela de quiesce por workspace** (coordenar o lock
   com `pipeline_reset` / lane `dl-f1-migration-runbook`). Invariante de correção.

## Wire / FE

`transaction_hash` é **opaco** para o FE (recebe string, usa como key, devolve no POST;
`row_id = f"{hash}:{idx}"` só concatena/splita). Trocar o algoritmo (SHA-64 →
v2 SHA-16) **não é breaking de shape de contrato** — não exige dual-read no FE. Adicionar
`hash_version` ao `TransactionOverrideResponse` → rodar `make update-openapi-snapshot`.

## Alternativas rejeitadas

- **Consertar `generate_transaction_hash` isolado** (adicionar normalização/`tipo_conta`) →
  cria um **quarto** hash e mantém o buraco de lineage. Rejeitado.
- **Propagar o `natural_key` do E2 para a linha E4** → acopla a identidade do override à
  política interna de qual-linha-vence do E3; ambíguo sob colapso N→1. Rejeitado (Decisão 2).
- **Backfill in-place + PITR como rede** → PITR força reverter *tudo* (perdendo overrides
  legítimos criados depois) se o mapeamento errar em poucas linhas. Rejeitado (Decisão 4).
- **Manter `generate_transaction_hash` como shim pós-cutover** → é como se chegou a três
  hashes. Rejeitado (Decisão 1).

## Consequências

- **Positivas:** identidade única (dedup pipeline = override = learning = wire); buraco de
  lineage de overrides fechado; corrige bug vivo de orfanização (drift PIX, colisão de conta);
  linha de override auto-suficiente para futuras migrações sem replay.
- **Custo:** +8 colunas + 1 índice + dual-write em 3 call-sites + 1 flag + script de backfill +
  2 migrations + janela de convivência (~1–2 sprints). Justificável: o dado é irrecuperável
  (trabalho cognitivo manual) e a dívida é recorrente (3º hash já provou).
- **Risco residual:** órfãos por re-extração (medidos e reportados, nunca silenciosos);
  exige quiesce de pipeline no backfill.

## Critério de aceite (para o PR de implementação que flippa esta ADR → Decidido)

- `test_override_hash_equals_dedup_hash` — para a mesma linha E4, `natural_key_hash` do override
  == `natural_key.hash` v2 do dedup (invariante central).
- `test_override_backfill_reanchors` — fixture com overrides v1 legados → backfill reancora os
  presentes no E4, **reporta** órfãos; nada dropado.
- `test_backfill_quarantines_ambiguous_v1` — v1 que resolve para >1 `natural_key` v2 → `orphaned_at`,
  não reancora (Decisão 6b).
- `test_dual_read_window` — match casa v2 e v1-legado durante a janela.
- Casos **fatura-estorno** (`valor<0`, `tipo_conta="fatura…"`) e **drift-sufixo-PIX** no
  read-path do backend (não só no `cash_flow_builder`).
- `test_collision_precedence` — `manual > rule`; mais recente vence; perdedor soft-deleted com
  `notes`.
- Log estruturado no backfill `{workspace_id, overrides_total, reanchored, orphaned, ambiguous, collided}`
  (namespace `mathoms.categorization.*`).
- `make update-openapi-snapshot` commitado; `dev/check_pipeline_boundaries.py` verde
  (recompute do backend importa `_tx_identity` de `pipeline/` — domínio puro, OK); migration
  com `pytestmark = pytest.mark.migration`; goldens E3/E4/E5 verdes (D6 não toca dedup —
  só override).
- **Gate de sequenciamento:** passo 2 (flip dedup E4→v2) só após backfill completo + dogfood
  de reancoragem verde.

## Follow-ups (fora desta ADR)

- `product-designer` — estado de UI "override órfão / vínculo perdido".
- `product-manager` — alocação da lane de implementação em sprint (A23 vs A24) e prioridade
  relativa ao passo 2.
- Lane de implementação: 2 migrations + backfill + dual-write + flag + golden de paridade
  (override sobrevive ao flip v1→v2 em fixture sintético PII-zero com drift de sufixo PIX).
