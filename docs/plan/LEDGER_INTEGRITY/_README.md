---
id: PLAN-ledger-integrity
type: plan
title: "Ledger Integrity — conservação do razão (E3/E4) + roteamento dos 5 gaps da certificação"
status: draft
created_at: 2026-07-24
last_review: 2026-07-24
sprint_origem: A39
sprint_atual: A39
sprints_envolvidas: [A39]
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-347]]"
tags:
  - type/plan
  - status/draft
  - area/pipeline
  - area/dados
---

# Ledger Integrity — conservação do razão (E3/E4) + roteamento dos 5 gaps

> **Origem.** Certificação `ledger-certify` ([[ADR-302]]) do ws de dogfood
> `5@5.com` — seção `r2` de [[LEDGER-CERTIFY-active]]. Os 2 achados de hardening da
> **skill** (LC06/LC07) saíram por task separada (fixados em PR #1063). Este plano
> ataca os **5 achados de produto**. **Análise virou plano; nada foi corrigido.**
> Revisado por painel de 4 (data-engineer + senior-cto + product-manager +
> information-architect) — a estrutura abaixo incorpora as objeções bloqueantes.

## O que este plano É (e o que ele ROTEIA) — [[ADR-182]]

O painel foi unânime: os 5 achados **não formam um plano coeso** — são **duas teses**
(conservação vs identidade) com **três donos**. Este plano tem **uma tese —
conservação de contagem do razão E3/E4** — e **owna diretamente** só o que casa com
ela; o resto é **roteado** ao dono existente, com handoff explícito. Assim o plano
fecha como unidade em vez de virar container-de-proximidade que nunca chega a `done`.

| Item | Defeito | Prio | Materialidade | **Dono / rota** | ADR |
|---|---|---|---|---|---|
| **LC-01** (+LC-03) | remoção de tx não-declarada no E3 (356 tx) | **P1** | detector de P0; não perde dado *por si só* | **este plano** (tese) → sprint sucessora "ledger-trust E3/E4" | **[[ADR-347]]** (novo) |
| **LC-02** | dedup de investimento escapa por membro-vazio | **P1** | **confirmado material** (PL inflado; 5-6 díg. em conta grande) | **lane própria**, `depends_on` consolidador da A39.l9 em `main` | co-autoria [[ADR-346]] (step 4b) |
| **LC-03** | 1 tx dropada E3→E4 | P3 | 1 tx | **este plano** (bug standalone) | — |
| **LC-04** | natural_key 11,8% → sticky-override degradado | **P2** | não afeta números do relatório | **onda em [[PLAN-data-lineage]]** (dono de ADR-287 + máquina de re-âncora) | [[ADR-287]] |
| **LC-05** | `membro` = slug de nome pessoal como identidade | P2 | raiz de LC-02 (dimensão membro) | **onda em [[PLAN-data-lineage]]** (tese identidade) | [[ADR-287]] |

**Prioridade ≠ ordem.** LC-02 é o defeito **mais material confirmado**, mas está
**bloqueado por dependência** (mesmo arquivo/ADR da A39.l9 em voo). LC-01 vai
**primeiro por estar desbloqueado**, não por ser o mais grave. Não confundir os eixos.

## Princípios (timeless)

1. **Conservação é o piso, não o teto.** Os piores erros são **sum-preserving**. Uma
   rubrica/gate que só herda conservação dá falso-verde. **Observabilidade de
   remoção/soma é requisito de 1ª classe do E3/E4** — meta-princípio
   *anti-silêncio de transformação* (ver [[ADR-347]]).
2. **Estado intermediário pior-que-hoje = perda silenciosa.** Faseamento obrigatório
   (schema aditivo → produtor → WARN → HARD); nunca gate antes do produtor.
3. **Forward-only, sem backfill** ([[ADR-287]]). Golden de valor que mexa ⇒ rebaseline
   → **pare**.
4. **Não degradar.** `despesas`/`receitas`/`total_por_membro` conservam hoje; diff
   dogfood pré/pós = **zero** é invariante bloqueante de todo PR.
5. **Estágio-alvo = beta fechado** (5 usuários: família + 2-3 convidados — PRODUCT.md
   §5), **não** "beta amplo" (não existe). A relevância vem de precondição de
   confiança + materialidade, não de gate explícito de conservação no §5.

## Decisão de produto registrada — Learning Loop fora do caminho crítico do beta

O Categorization Learning Loop **não** está no caminho crítico do beta fechado
(ausente do PRODUCT.md §5; V2 é pós-tração; gate humano dispensado; atrás de flag
`learning_loop_enabled`). **Decisão:** o flag permanece **OFF no beta** até a
cobertura de `natural_key` ≥90% ser medida no corpus real. Consequência: **LC-04 é a
condição de destravar o flag, não um beta-blocker → P2.** Só vira P1 se o owner
quiser o flag **ON no beta** (para gerar o tráfego que o gating de V2 exige) — e aí
LC-04 aterrissa **antes** de abrir o beta (reversão silenciosa de override é pior que
não ter a feature). Registrar a call em `docs/reference/PRODUCT.md §5`.

---

## Onda A — LC-01: ledger de conservação de contagem no E3 (P1) · dono: este plano

Tese central. Contrato, invariantes, faseamento e alternativas na **[[ADR-347]]**
(`Proposto`, revisada por data-engineer + senior-cto). Resumo executável:

### Diagnóstico corrigido pelo painel
- **356** tx removidas sem declaração (6224 − 2 anachronic − 5724 survivors − 142
  dups = **356**; o "214" do baseline r1 estava errado — dupla-subtração).
- Remoção por **múltiplos canais** não-declarados, dois deles **perda de dado real**:
  `undated_drop` (tx sem data em `from_e2_dict`,
  [`document.py:130-131`](../../../pipeline/domain/models/document.py)) e
  `undated_statement_drop` (data string ruim ⇒ `from_e2_dict` levanta ⇒ `except`
  bare dropa o **statement inteiro**,
  [`e3_reconciler_adapter.py:289-292`](../../../pipeline/domain/services/e3_reconciler_adapter.py)).
  Demais: `intra_statement_dedup`
  ([`reconciliation_service.py:145-155`](../../../pipeline/domain/services/reconciliation_service.py),
  count reportado em lugar nenhum), `cross_file_dedup` (só declara `len>1`),
  `period_skip`, `empty_institution`, `non_tx_type`, e `llm_stub` (**armadilha de
  dupla-contagem** no denominador — excluir).

### Contrato (ver ADR-347 §Decisão)
- **Âncora de medição única:** `tx_carregadas` contado **pré-`undated_drop` e
  pré-anachronic**, **serializado no artefato E3** (self-certifying). Evita a
  dupla-subtração que tornava a igualdade impossível de fechar.
- **`_dedup` context-free** retorna `(kept, count, valor_cents)`; o **caller** tagueia
  o canal (`_reconcile_group`→intra; adapter `:401`→cross — re-wire deste call-site).
- **`DedupRemoval.proven: bool`** (source-ref idêntico, computado no dedup); remoção
  não-provada → `needs_review` **measure-then-emit** (conta a taxa no PR2; só emite
  após dogfood provar falso-positivo).
- **Partição por artefato (tx-level):** `{undated_drop, anachronic,
  intra_statement_dedup, cross_file_dedup}`. **Ledger `exclusions` por run
  (statement-level):** contado em cada skip-site (`len(data["transacoes"])`) e
  projetado em `review_reasons` — **sem tabela nova** ([[ADR-111]]).
- **Igualdade** por artefato + por workspace (agregado **live-only**, respeita
  [[ADR-342]] §Dec-3; nunca soma superseded), int cents tol-zero.

### Faseamento (obrigatório)
- **PR1** — âncora + `DedupRemoval{proven}` + `_dedup` retorna contagem + contagem nos
  skip-sites + campos **aditivo-opcionais** no `e3_reconciled.schema.json`. Sem HARD.
- **PR2** — serializa `remocoes` + `exclusions` (review_reasons) + telemetria
  (`mathoms.*`, só contagens/pct, zero PII) + `needs_review` measure-then-emit. **WARN**.
- **PR3** — flip **HARD tol-zero sobre o resíduo**. Gate = **teste de exaustividade**
  (injeta cada canal, resíduo==0) **e** ≥1 run/sprint com 0 resíduo no dogfood.
  **Sem piso de materialidade** (mascararia o P0).

### Prioridade split (product-manager)
- **PR1+PR2 (observabilidade/WARN/needs_review) = P1** relevante a beta.
- **PR3 (flip HARD) = P2 pós-soak** (não é beta-blocker; precisa de soak WARN limpo).

### Risco / rollback
- Baixo-médio; NÃO muda aritmética de valor (só ADICIONA declaração). Risco no flip
  HARD → WARN→HARD com exaustividade + soak. Campos aditivo-opcionais; rollback =
  reverter PR + downgrade schema; sem backfill.
- **Bônus:** o PR2 **expõe/corrige** os 2 drops silenciosos de data (perda real).

### Aceite
Teste de exaustividade verde (resíduo==0 injetando cada canal); igualdade de
workspace reproduz o 356; agregado live-only não soma superseded; diff dogfood = zero;
goldens E3 verdes. **Decidir agora:** "ledger agregado de workspace" = derivável do
read-path (tx-level) + `review_reasons` (statement-level) — **escopado, não aberto**.

---

## Onda A' — LC-03: 1 tx dropada E3→E4 (P3) · dono: este plano

- `Σtransacoes_total(E3)`=5724 vs `tx_total(_lineage despesas)`=5723; `classified`=5723.
- **Bug puro, standalone, sem ADR.** Localizar entre `TransactionClassifier` e
  `CashFlowBuilder` (candidatos: tx zero-value filtrada, header, data não-parseável)
  + **teste de regressão tol-zero**. Pode ir a qualquer momento.

---

## Onda B — LC-02: dedup de investimento membro-vazio (P1) · rota: lane própria + A39.l9

### Diagnóstico
Chave `(inst_key or f"_src:{cand['_source']}", cand["membro"])`
([`investments_consolidator.py:327`](../../../pipeline/domain/services/investments_consolidator.py));
`membro=""` (binance 2025-03) e `membro=<resolvido>` (2025-12) formam chaves distintas
→ ambos snapshots somam em `total_por_membro` → PL inflado pelo stale.

### Fix (corrigido pelo painel — NÃO é "simétrico ao step 4")
- **Step 4 e 4b são OPOSTOS.** Step 4 (inst-vazia) **alarga** a chave via `_src:`
  (anti-colapso, preserva ambas). 4b (membro-vazio) precisa **colapsar** o snapshot
  stale no irmão resolvido (snapshots temporais do MESMO membro). Aplicar o padrão do
  step 4 daria chave `_src:` distinta e **impediria** o colapso — regressão. 4b =
  **resolução upstream + passo de colapso pós-hoc keyed em `(inst, membro_resolvido)`**.
- **Guard de unicidade (obrigatório):** colapsa **só quando há EXATAMENTE UM** membro
  resolvido naquele `inst`; **0 ou ≥2 → `needs_review`**, nunca colapso (senão joga
  patrimônio na pessoa errada em conta conjunta / dois membros no mesmo broker).
- **Upstream primário:** `MemberNameResolver` é **no-op** quando `membro_raw` é vazio
  ([`investments_consolidator.py:272`](../../../pipeline/domain/services/investments_consolidator.py)).
  O vetor real é **cobertura do `AccountResolver`** (`inst→membro`, `:286`) **ou o
  parser emitindo `membro`** — não MemberNameResolver.
- **Proibido fallback sintético de member-id** (ex.: cair no `artifact_key`): não é
  id estável; sob LC-05 vira lixo na dimensão membro (dívida de re-âncora). Não-atribuído
  genuíno → `needs_review`, **nunca** id inventado.
- **`data_ref` nunca na chave** (mesma proibição do step 4 — regressão de dupla-contagem
  de snapshots).

### Contrato de docs (co-autoria, não emenda)
A [[ADR-346]] é **`Proposto`** e de **outra sessão** (A39.l9, WIP não-commitado).
**Co-autorar "step 4b — membro-vazia" no CORPO da ADR-346** enquanto Proposto —
**sem** `## Emenda` datado, **sem** `amended_at` (maquinaria para ADR `Decidida`).
Adicionar **invariante NOVA** (não estender a #4, que diz "nunca descarta" — o oposto
do que 4b faz): *"membro-vazio colapsa no único irmão resolvido do mesmo inst
(remove o stale) OU preserva + `needs_review` se 0/≥2; `total_por_membro` pré/pós =
zero exceto o stale removido."*

### Sequenciamento (sem escopo-creep na A39.l9)
- **Gate de docs:** a co-autoria na ADR-346 gateia em **ADR-346 estar em `main`**
  (docs-only, rápido) — não no PR2 da l9.
- **Gate de código:** LC-02 = **lane própria**, `depends_on` os PRs da A39.l9 que
  tocam o consolidador estarem em `main` (PR1 #1059 já; aguardar PR2 nullsum-badge).
  Coordenar como hotspot (`investments_consolidator.py`; nunca commit cruzado). **Não
  expandir o DoD da A39.l9** — LC-02 pode shipar **antes** do parser RV (independe dele).

### Aceite
Fixture 2-snapshot `(inst,"")`@antigo + `(inst,resolvido)`@recente → **colapsa**;
fixture 2-membros-mesmo-inst → **needs_review** (não colapsa); `total_por_membro`
pré/pós = zero exceto stale; **go/no-go do fix upstream** (cobrir AccountResolver ou
deferir conscientemente com a rede defensiva como mitigação).

---

## Onda C — LC-04 + LC-05 (identidade) · rota: [[PLAN-data-lineage]]

Tese de **identidade**, não conservação → dono natural é o DATA_LINEAGE (ADR-287 +
máquina de re-âncora de override já existe lá). **O painel corrigiu: são dois PRs
disjuntos, não um.**

### LC-04 — natural_key / titular (P2) · migração hash-changing
- `titular` alimenta ambos os hashes (`_hash_v1` `transaction_hash` e `_hash_v2`
  `natural_key_hash`) em [`_tx_identity.py:222,235`](../../../pipeline/domain/services/_tx_identity.py);
  `_has_discriminants` (`:169-171`) exige banco **E** titular **E** tipo_conta — o 88%
  null é dominado por **titular ausente** ⇒ **fix no E3 populando titular** (nunca CPF
  no hash) é a alavanca.
- **Risco de re-âncora (subestimado — bloqueante):**
  1. Popular titular muda o hash de **toda tx afetada** (não só os 88% novos — o ~12%
     coberto também desloca se a normalização mudar). Escopo do re-anchor = **"input
     de hash mudou"**, não "era null".
  2. **Colisão em `uq_override_ws_hash`** ([`transaction_override.py:29`](../../../backend/app/models/transaction_override.py)):
     dois overrides distintos sob titular-null podem colapsar no mesmo `transaction_hash`
     → `IntegrityError` no meio da migração. **Definir resolução** (merge / keep-latest
     / `needs_review`) — hoje ausente do plano.
  3. **Reusar a máquina existente:** `orphaned_at` (quarentena inerte, filtrada em todo
     read-path, [`_apply_engine.py:79-86`](../../../backend/app/application/categorization/_apply_engine.py));
     update in-place evita dup de `natural_key_hash` (`:224`). Re-anchor = recomputa
     hash → casa item E4 atual? update in-place : `orphaned_at`. **Idempotente +
     collision-safe.**
- **Gate = flag do Learning Loop** (≥90% cobertura sobre tx categorizáveis, medido por
  **telemetria no corpus real**, não fixture), **NÃO** KR do pipeline. Flag OFF até lá.

### LC-05 — `membro` como identidade estável (P2) · separado, sem overrides
- `membro` vive no consolidador de investimentos (`total_por_membro`) — **caminho de
  código disjunto** do `natural_key` de transação. Mudar `membro` **não** muda hash de
  tx ⇒ **PR separado**, não toca overrides. "LC-05 antes de LC-04" **não** é a
  dependência real.
- Fix: identidade de membro por id estável do `family_member` (nunca CPF no hash,
  [[ADR-287]]); resolve a raiz do LC-02 (membro-vazio) na origem.

### Aceite (na DATA_LINEAGE)
LC-04: re-anchor testado contra `TransactionOverride` **real** (SQLite in-mem, nunca
mock) **incluindo caso de colisão**; 0 reversão silenciosa; snapshot de contagem de
órfãos publicado; cobertura ≥90% por telemetria dogfood. LC-05: `total_por_membro`
estável sob mudança de nome; nome nunca é chave.

---

## KRs (reescritos pelo product-manager — output ≠ outcome)

Distinguir **health/guardrail** (diff-zero, suíte verde) ≠ **output** (declarou/cobriu)
≠ **outcome** (valor sob conservação; erro material surfado).

- **KR-1 (outcome — North Star):** **0 erro material silencioso (>piso) alcança
  `patrimonio_liquido`/`despesas`/`receitas` do relatório** no dogfood, instrumentado
  pelo invariante transversal "diff pré/pós = zero" + `valor_cents` por remoção (LC-01 PR2).
- **KR-2 (LC-01, invariante + valor):** 0 remoção de tx não-declarada **E** *"% do
  valor de tx sob conservação auditada (remoções declaradas reconciliam à fonte,
  tol-zero) sobe de ~0 → ≥X%"* — o companheiro de valor impede o gaming por
  **super-declaração** (jogar tudo num balde sem provar duplicata); `needs_review`
  para não-provada está **no texto do KR**.
- **KR-3 (LC-02, outcome + materialidade):** 0 dupla-contagem de investimento
  cross-período por membro-vazio **>piso** chegando ao PL.
- **~~KR natural_key ≥90%~~** — **removido**: é **gate do flag** do Learning Loop
  (aceite de LC-04 na DATA_LINEAGE), não KR deste plano.

## Riscos transversais e não-degradação

1. **Flip HARD prematuro** (LC-01 PR3) → gate de exaustividade + soak WARN, sem piso.
2. **Re-âncora de override** (LC-04) → migração idempotente + collision-safe contra DB
   real; escopo "input de hash mudou".
3. **Concorrência A39.l9** (LC-02) → lane dependente + co-autoria coordenada; nunca
   parallel-edit nem expandir o DoD da l9.
4. **Rebaseline disfarçado** — golden de valor que mexa ⇒ parar ([[ADR-287]]).

## Rastreamento

- **Owna:** LC-01 ([[ADR-347]]) + LC-03. Executa na sprint sucessora ("ledger-trust
  E3/E4"); **não há sprint corrente** (A39 é candidate, fase pesada deferida).
- **Roteia:** LC-02 → lane própria `depends_on` A39.l9-consolidador; LC-04+LC-05 →
  [[PLAN-data-lineage]].
- Achados-fonte: [[LEDGER-CERTIFY-active]] §r2. Cru + instância (PII) off-git em
  `storage/<uuid>/ledger_certify/`. Flippa para `in_progress` quando a 1ª onda abrir lane.
