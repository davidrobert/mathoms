---
id: ADR-371
type: adr
title: "O grafo de FK é a fonte única da deleção: lista manual de tabelas-filhas é proibida sem gate"
status: Decidido
date: "2026-08-08"
relates_to: ["[[ADR-212]]", "[[ADR-131]]", "[[ADR-116]]", "[[ADR-275]]", "[[ADR-362]]"]
tags:
  - type/adr
  - status/decidido
  - area/db
  - area/internal-ops
---

# ADR-371 — O grafo de FK é a fonte única da deleção

## Contexto

Em 2026-08-08 o DB de dogfood tinha **48 violações de integridade referencial**
(`PRAGMA foreign_key_check`), todas concentradas em três tabelas:

| tabela | coluna | violações |
| --- | --- | --- |
| `reports` | `pipeline_run_id` | 16 |
| `reports` | `analysis_artifact_id` | 10 |
| `planner_review_metadata` | `pipeline_artifact_id` / `pipeline_run_id` | 21 |
| `pipeline_run_costs` | `pipeline_run_id` | 1 |

A origem é um expurgo em **2026-05-15 ~11:48**, que apagou a subárvore de
`pipeline_runs` de forma completa e consistente — `documents`,
`pipeline_runs`, `pipeline_stage_logs`, `stage_reviews` e `pipeline_artifacts`
têm todos o mesmo corte, e `pipeline_artifacts.id = 1` datado de 11:49:58
prova que a tabela foi zerada e o contador de rowid reiniciou. O expurgo
**esqueceu três tabelas**.

Duas consequências, de gravidades diferentes:

1. **FK pendurada** (16 rows). `reports.pipeline_run_id` mantém um valor cujo
   run não existe. Degrada razoavelmente por acidente: `outcome_for_report`
   usa `.get(rid, unknown)` e cai em `unknown`; `_resolve_run_id` devolve um
   valor truthy e não dispara `report_not_found`, caindo no código de ausência
   conservador.

2. **FK apontando para o alvo errado** (21 rows) — pior, e não detectável por
   `foreign_key_check`. Como `pipeline_artifacts.id` é rowid alias do SQLite
   **sem `AUTOINCREMENT`**, os inteiros liberados foram reemitidos a artefatos
   novos. Em todos os 21 casos o artefato apontado tem `created_at`
   **posterior** ao relatório — de dias a semanas. `GET /reports/{id}/data`
   servia payload E2-faturas / E2-extratos / E3 / E1.5a / E4 com **HTTP 200**,
   num produto financeiro.

A condição que permitiu tudo isso: `backend/app/core/database.py` deixava
`PRAGMA foreign_keys` **OFF** de propósito, com um comentário afirmando que
ligar "expõe FK violations históricas em fixtures de teste" — sem dizer
quantas. SQLite ignora todo `ON DELETE` sem o pragma, então as FKs declaradas
nos models eram **decorativas**, e cada rotina de deleção passou a reemular o
grafo de FK à mão. `purge_documents._delete_pipeline_data` documentava a
prática explicitamente: *"DELETEs explícitos — não dependemos de PRAGMA
foreign_keys do SQLite"*.

Havia **três emulações manuais divergentes** em produção:

- `artifact_prune.referenced_artifact_ids` — a única correta; excluía do
  conjunto prunável tudo que report / publicação / parecer referenciam.
- `pipeline_reset.reset_workspace_from_stage` — nenhuma guarda. Deletava por
  `(workspace_id, stage)` sem escopo de run, apagando o E5 de **todos** os
  runs históricos do workspace.
- `purge_reports` — nenhuma guarda, no artefato do relatório purgado.

## Decisão

**D1 — `PRAGMA foreign_keys=ON` no engine SQLite.** Medido antes de decidir:
**19 testes de 9400** quebravam — 15 em `backend/tests`, 4 em `tests/` — todos
fabricando referência inexistente (`Report` sem `PipelineRun`,
`reviewed_by="user-1"` sem usuário, `review_reason` sem workspace, store de
artifact sem run, CLI com `--run-id` sintético). São os testes que ficavam mais
honestos, não o pragma que ficava caro. Prod é Postgres, onde a FK sempre foi
enforçada — o pragma fecha a divergência dev↔prod, não introduz regra nova.

> Nota de método: os 4 de `tests/` só apareceram no CI. Localmente eles já
> falhavam por outro motivo (ruído de SQL echo no stdout, com `DEBUG=True`
> default), e a falha nova ficou escondida atrás da antiga. A verificação
> "isso pré-existe em `main`?" feita com `git stash` deu falso-negativo porque
> o pragma já estava **commitado** — stash não desfaz commit. Medir contra
> `origin/main` exige `git checkout origin/main -- <arquivo>`.

**D2 — O grafo declarado nos models é a única fonte de verdade da deleção.**
Enumerar tabelas-filhas à mão é proibido. `purge_documents` passa a deletar só
o pai e deixar o `ON DELETE` cascatear. A lista manual não é um bug com três
instâncias; é uma **classe** cuja próxima instância nasce com a próxima tabela.

**D3 — `artifact_references.py` é fonte única do que é intocável.**
`REFERENCING_COLUMNS` reúne as quatro colunas que apontam para
`pipeline_artifacts.id`. `pipeline_reset` e `purge_reports` passam a consultá-la
antes de deletar, como `artifact_prune` já fazia. Sem isso, com a FK ligada, o
`RESTRICT` de `report_publications.artifact_id` e `planner_reviews.e5_artifact_id`
**aborta a transação inteira** — o reset ficaria inoperante em vez de destrutivo,
e nenhum dos dois é a semântica pretendida.

**D4 — Guarda por referência, não escopo por run.** Escopar o reset ao run
corrente parece mais cirúrgico e é errado: `_WORKSPACE_SCOPED_STAGES`
([[ADR-241]]) faz E1.x, `extract_irpf_full`, informes e E2-* serem lidos por
fallback workspace-wide. Apagar só as rows de um run deixaria o run seguinte
lendo o artefato de outro — **o reset não resetaria nada**. Já E3/E4/E5 são
run-scoped e recomputam o universo a cada run, então as rows de runs antigos
são inertes para o pipeline e só importam para os relatórios que as referenciam.
O escopo amplo é necessário; a guarda por referência é o recorte certo.

**D5 — Preservar sem avisar é o mesmo erro de apagar sem avisar.**
`artifacts_preserved_referenced` sai na preview, no resultado e no audit.

**D6 — O read-path valida o stage do artefato.** Que `analysis_artifact_id`
aponte para um artefato de análise não é invariante expressável em FK (FK para
subconjunto de rows exigiria trigger ou coluna gerada). O write-path acerta por
construção; o read-path aceitava o que viesse. Passa a exigir
`stage ∈ stage_aliases("analyze_finances")`, com `logger.error` estruturado —
**o 404 é o efeito, o sinal é o log**. Trocar corrupção calada por ausência
calada não seria conserto.

**D7 — Gate de exaustividade.** `dev/check_run_artifact_fk_coverage.py`
(pre-commit) exige que toda FK para `pipeline_runs`/`pipeline_artifacts` esteja
classificada: R1 — FK para artifacts tem que estar em `REFERENCING_COLUMNS`;
R2 — FK precisa declarar `ondelete=`; R3 — coluna que nomeia run/artifact sem
FK precisa de justificativa no allowlist. Deriva de AST, não de
`Base.metadata`: importar os models puxa config e Fernet dentro do hook, e
comparar o metadata consigo mesmo seria auto-referente — ficaria verde durante
todo o drift.

## Alternativas rejeitadas

**Coluna de proveniência imutável em `reports`** (snapshot do run_id/stage).
Rejeitada. [[ADR-362]] §Alternativas já reprovou a forma um nível abaixo, e o
snapshot não sobrevive ao próprio propósito: quando o run é purgado,
`pipeline_stage_logs` vai junto, então guardar a string do run morto permite
dizer "foi o run X" — e X não resolve mais nada. Compraria a capacidade de
distinguir "run purgado" de "nunca teve run": um problema de 1 bit que
`audit_logs` já resolve, ao preço de uma coluna denormalizada permanente.

**Completar a lista manual de `purge_documents`.** Rejeitada: conserta a
instância e preserva a classe. Sem D7, a próxima tabela-filha repete o erro.

**Limpar o DB de dogfood primeiro.** Rejeitada como primeiro passo: apagaria a
evidência antes de existir o instrumento que a detecta. A limpeza é `SET NULL`
(não re-apontar — os E5 originais foram deletados e não há como saber qual era
qual) e vem depois, gated pelo dono.

## Consequências

- Deleção de `PipelineRun` agora cascateia de verdade: `reports.pipeline_run_id`
  vira `NULL` em vez de ficar pendurado, e `ReportRunOutcome.unknown` passa a
  ser alcançado pelo caminho desenhado, não por acidente do `.get`.
- Reset e purge de relatório podem **preservar** artefatos. Operador que
  esperava "apaga tudo" vê a contagem preservada na preview.
- O `.get(rid, unknown)` de `report_run_outcome` **não** pode virar join: é o
  que segura os 16 relatórios de dogfood que ainda carregam run pendurado.
  Comentário no módulo registra isso.
- As 48 rows do DB de dogfood **continuam lá**. Limpeza é owner-gated; o
  diagnóstico e o detector existem, a mutação de dado não foi executada.
