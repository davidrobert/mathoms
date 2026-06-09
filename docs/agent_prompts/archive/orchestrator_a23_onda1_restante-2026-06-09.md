# Orquestração — A23 Data Lineage · Onda 1 (3 lanes restantes)

> Instância do [_TEMPLATE_orchestrator.md](_TEMPLATE_orchestrator.md) para fechar a
> **Onda 1 (F1 — contrato aditivo)** do plano [DATA_LINEAGE](../plan/DATA_LINEAGE/_README.md).
> Sucede [`orchestrator_a23_onda1_lanes.md`](orchestrator_a23_onda1_lanes.md): A23.l1/l2/l3,
> A23.l4 (override-hash/D6, slices 1–3) e A23.l5 (`dl-f1-data-source`) **já estão em `main`**.
> Restam 3 lanes: `dl-f1-amount-decimal` (B5), `dl-f1-extract-check` ([[ADR-280]]),
> `dl-f1-migration-runbook` (G-e + FK DB deferido da A23.l5).
>
> **Uso:** copie o bloco abaixo no início da sessão. O orquestrador respeita as
> convenções de [CLAUDE.md](../../CLAUDE.md) e delega aos especialistas de
> [`.claude/agents/`](../../.claude/agents/).
>
> **Quando arquivar:** quando as 3 lanes estiverem `shipped` em `main`. Mover para
> [`archive/`](archive/) com data.

---

```
Continue a Onda 1 da sprint A23 (Data Lineage) do Mathoms AI. As lanes já fechadas NÃO
devem ser refeitas; restam 3 lanes irmãs. Fatie em branches/PRs próprios (uma branch por
lane, nunca misture lanes).

## Onde estamos (tudo em origin/main — NÃO refazer, NÃO clobberar)
Sprint atual: A23 — Data Lineage (docs/sprint/A23/_README.md). Plano dono:
docs/plan/DATA_LINEAGE/_README.md. Gate F0 fechado (ADR-278/279/280/281 Decididas).

Onda 1 (F1 — contrato aditivo), SHIPPED:
- A23.l1 (gate F0) · A23.l2 substrato de golden (#552) · A23.l3 natural_key K4 v2 (#553).
- A23.l4 override-hash/D6 (ADR-282) — slices 1–3 (expand) em main (#556/#562/#563).
  Slices 4–5 (cutover + M2 destrutiva) são A24, NÃO desta onda. Gate ADR-282 §7: o passo 2
  da B4 (flip dedup E4→v2) só abre após cutover + dogfood de reancoragem.
- A23.l5 dl-f1-data-source (ADR-278) #564 — tabela `data_source` + coluna
  `pipeline_artifacts.data_source_id` (nullable, indexada) + `SourceRef` em
  pipeline/domain/ports/source.py. Backfill kind='document' na migration adr278datasource.
  ⚠️ DOIS itens foram DEFERIDOS da A23.l5 e são escopo das lanes abaixo:
    (a) FK DB `data_source_id → data_source.id ON DELETE SET NULL` — Postgres-específico
        (NOT VALID + VALIDATE), foi para dl-f1-migration-runbook.
    (b) `SourceAdapter` Protocol — adiado até haver consumidor (F2), NÃO é desta onda.

Alembic head atual: `adr278datasource` (down_revision da próxima migration).

## Leia primeiro (canônico — não confie só neste prompt)
1. CLAUDE.md (raiz) — code style (funções ≤20 linhas; gate dev/check_code_style_regression.py
   é exigente com P1 long-function, P7 docstring multi-parágrafo `\n\n`, P9 nesting>2 — cadeia
   if/elif dentro de for já estoura; achate com dict-dispatch/helper), git/PR, delegação.
2. docs/plan/DATA_LINEAGE/_README.md — §Ondas (tabela Onda 1), §Guard-rails (G1, G-e), blocker B5.
3. docs/adr/278-source-adapter-canonical-contract.md (B5 amount 2-fases; data_source) +
   docs/adr/280-extract-transform-cut-criterion.md (critério Extract|Transform).
4. docs/agent_prompts/orchestrator_a23_onda1_lanes.md — instância anterior (4 lanes; 1 entregue).
5. Espelhe o FORMATO de lane existente: docs/sprint/A23/lanes/A23-l5-data-source.md
   (frontmatter, co-design, escopo, critério). Use ids sequenciais livres (A23.l6/l7/l8).

## As 3 lanes restantes (crie docs/sprint/A23/lanes/A23-l{6,7,8}-*.md espelhando A23.l5)
ORDEM/DEPENDÊNCIAS:

- dl-f1-amount-decimal (B5, paralelo): campo `amount` decimal string (ADR-090) ao lado de
  `valor` em transacoes[] do contrato E2 — ADITIVO ao config/schemas/e2_extract.schema.json
  (ADICIONE; preserve natural_key/direction da A23.l3 e o `valor` existente; NÃO deprecar
  `valor` nesta onda). Sem DDL (amount vive no content_json). Inventário de TODOS os leitores
  de transacoes[].valor (E3 reconciler, cents_int, dedup). Gate de paridade
  Decimal(amount)==Decimal(str(valor)) enquanto coexistem. Co-design: data-engineer
  (inventário de leitores + gate de paridade B5).

- dl-f1-extract-check (ADR-280, paralelo): dev/check_extract_no_domain_imports.py (NOVO) —
  extração (scripts/e2/banks/*, extract_baseline, extract_irpf_full) ∌ imports de
  category_template / *_dedup / ConfigStore. Estende validate_full_order. Rotula
  consolidate_baseline (E1.5c) como Transform. NÃO mover código ainda (de-leak é F2); só
  TRAVA o critério de pureza com o gate. Espelhe dev/check_pipeline_boundaries.py como padrão.
  Co-design: senior-cto (boundary gate).

- dl-f1-migration-runbook (G-e, DEPOIS — consolida o débito da A23.l5): runbook
  docs/reference/runbooks/data_lineage_migrations.md cobrindo as migrations de F1
  (adr282overridenk, adr278datasource, + 2-fases amount/natural_key futuras) com janela PITR
  + rollback por fase. ALÉM do runbook, esta lane MATERIALIZA o FK DB deferido da A23.l5:
  migration que adiciona `data_source_id → data_source.id ON DELETE SET NULL` em Postgres via
  ADD CONSTRAINT ... NOT VALID + VALIDATE CONSTRAINT (coluna nasce toda-NULL → validação
  barata; SQLite no test usa caminho batch/no-op). Asserção CONCURRENTLY/autocommit_block e
  do FK em backend/tests/.../test_alembic_guardrails (ou migration test dedicado com
  pytestmark = pytest.mark.migration). Co-design: sre-devops (runbook/PITR/rollback/NOT VALID)
  + information-architect (forma do runbook) + data-engineer (conteúdo das migrations).

## Inegociáveis
- Dinheiro nunca float (ADR-090); stateless (ADR-111); pipeline/** não importa
  fastapi/celery/sqlalchemy (dev/check_pipeline_boundaries.py). CI VERDE antes do merge.
  Concluído = PR squashed em main com CI verde (docs-only não espera CI).
- ADITIVIDADE (G1): contrato aditivo, NÃO consumir ainda → goldens E3/E4/E5 + view-model
  snapshot (backend/tests/test_report_view_model_snapshot.py) + invariantes de conservação
  (tests/test_e5_conservation_invariants.py) VERDES SEM REBASELINE. Prove com dev/golden_diff.py.
  Atenção: o snapshot do view-model é byte-a-byte — chave NOVA no payload de artefato quebra e
  exige rebaseline (viola G1). Coluna DB nova NÃO é payload (não quebra). Se exigir rebaseline,
  parou — reavalie.
- Migration online segura: ADD COLUMN NULL, índice simples (CONCURRENTLY só no runbook,
  precedente ADR-275/282), FK via NOT VALID+VALIDATE. SQLite/Alembic não faz ADD COLUMN com FK
  fora de batch copy_from — por isso o FK ficou Postgres-only no runbook. Backfill que lê dados
  precisa de guard `if not op.get_context().as_sql:` (offline `--sql` não tem conexão).
  Teste de migration com pytestmark = pytest.mark.migration; model+migration no MESMO PR
  (gate de drift). DB_SCHEMA_REFERENCE regenerado se schema mudar (make update-db-schema-reference
  funciona em worktree desde o fix #565).
- Co-design ANTES de codar (eles revisam SEU design, não redecidem ADR). Múltiplos gatilhos →
  invoque os especialistas em PARALELO (1 mensagem, N Agent calls).

## Antes de começar
- git fetch origin && git worktree list && git for-each-ref --sort=-committerdate
  refs/remotes/origin/agent/ | head  (confirme que ninguém está em
  dl-f1-amount-decimal / dl-f1-extract-check / dl-f1-migration-runbook)
- Crie UMA branch por lane (agent/dl-f1-<slug>/<yyyyMMdd-HHmm>) a partir de origin/main.
- Comece por amount-decimal + extract-check em paralelo (independentes). migration-runbook
  por último (consolida débitos + FK). Anuncie cada operação git. Comece lendo as fontes e
  propondo plano + co-design por lane.
```
