---
id: A42.l13
type: lane
title: "Proveniência do executor: qual código computou este run"
sprint: A42
status: open
priority: P1
branch_slug: a42-l13-proveniencia-do-executor-do-run
adrs:
  - "[[ADR-362]]"
  - "[[ADR-363]]"
  - "[[ADR-343]]"
depends_on: []
tags:
  - type/lane
  - sprint/a42
  - status/open
  - priority/p1
  - area/ci
  - area/pipeline
  - area/infra
---

# A42.l13 — `proveniencia-do-executor-do-run`

> **Origem:** pedido do dono em 2026-08-05 — "após rodar o pipeline do dogfood e
> executar a `report-review`, não consigo identificar sobre qual versão do
> repositório o relatório foi executado; e se houve avanços na `main` entre a
> execução e o fim da review, algo que apareceu no resultado pode já ter sido
> corrigido". Desenho fechado por painel de especialistas (recon → 7 pareceres →
> 3 céticos adversariais → síntese), com o parecer de schema colhido depois e
> **derrubando 4 das 8 decisões** da primeira síntese.

## Problema

Nenhum registro liga um relatório ao código que o produziu. Três relógios, um
registrado e no lugar errado:

1. o commit que **computou** o relatório (o run) — nunca registrado;
2. o commit no início da review — registrado, mas é provenance da **captura de
   screenshot**, coletada quando a review começa (dias depois do run, se o
   `report_id` for histórico);
3. o commit no fechamento da síntese — nunca registrado.

Duas colunas mortas provam que o problema não é falta de espaço, é falta de
contrato: `pipeline_runs.config_snapshot` (writer só em test builder, **0 de 109
rows**) e `pipeline_artifacts.schema_version` (writer real, **zero leitores**).

Em produção é pior: o `Dockerfile` não assa SHA, **nenhum dos 11 workflows faz
build de imagem**, e o container não tem `.git` — **incidente não é atribuível a
release**.

Esta lane pertence à A42 pela cláusula 3 do §Critério de admissão: é
**instrumento de certificação**. O §r4 do [[PIPELINE-REVIEWS-active]] declara um
`tip` no cabeçalho enquanto o parágrafo abaixo documenta que o run correu num
worker ~38 commits à frente — mesma classe de falso-verde da tese da sprint, na
camada do harness.

## Decisão

Ver [[ADR-362]] (o quê e onde) e [[ADR-363]] (de onde vem o valor). O núcleo:

- **`executor_revision`**, não `code_version` — o nome não pode vender
  reprodutibilidade que o sistema não tem (mediu-se mesmo SHA → output
  diferente, e SHA diferente → output idêntico, por cache de LLM).
- **Grão de stage** em `pipeline_stage_logs`, coluna `String(48)` nullable,
  escrita **só nos 2 INSERTs**. Não em `pipeline_runs` (mente no resume, porque
  `_mark_run_started` roda 2× por run), não em `output_summary` (sobrescrito por
  atribuição total em 3 pontos), não em `pipeline_artifacts` (desnormalização de
  10,5× e upsert in-place apagaria histórico).
- **Frase de escopo gerada**, nunca escrita à mão: afirmar "este run computou
  E3→E5 neste código" é **falso** sob `base_run_id`/`from_stage`, e afirmar
  escopo errado com autoridade é pior que não afirmar.
- **Cláusula de honestidade** exibida junto de toda superfície que mostre a
  revisão (as 5 entradas que movem número monetário com zero commits).

## Fases

| Fase | Entrega | Valor imediato | Migration? |
|---|---|---|---|
| **F0** | Coluna + write nos 2 INSERTs + `dev/build_info.py --export` no launch (Makefile) e `${{ github.sha }}` no CI | Todo stage passa a declarar quem o executou. Nenhum run novo nasce inatribuível | **sim**, 1 (`ADD COLUMN NULL`, catalog-only) |
| **F1** | Leitor: frase de escopo derivada dos stage logs + `run_meta.md` em prosa + `executor_revision` em todo log record + `service.version` no OTel + `/health` com campo **novo** | O dono lê no arquivo que já abre. `/health` para de mentir | não |
| **F2** | Preflight lê a revisão do **processo vivo** vs HEAD e avisa antes do run; `_upstream_source_runs` em `detail`; leitor de `SCHEMA_VERSION` | **Impede** o incidente do worker stale em vez de detectá-lo depois | não |
| **F3** | Owner-gated — ver §Deferido da [[ADR-363]] | Incidente em prod atribuível a release | não |

**Por que a coluna entra na F0 e não depois:** a primeira síntese deferia a
migration para o fim, alegando que só há leitor de dogfood. O parecer de schema
derrubou: são **~53 runs/30 dias**, o backfill é proibido por fabricar dado, e
portanto **cada dia de deferimento produz runs permanentemente inatribuíveis**.
Trocar dado irrecuperável por uma migration nullable sem índice é o trade errado.

## Critério de aceite

Todos por **medição**, com a mutação que os mata anotada:

- **Anti-fabricação (o gate central).** Registrar o SHA, lançar o worker, mover
  a árvore para outro commit, disparar o run ⇒ o stamp é o **do launch**, não o
  HEAD atual. *Mutação que mata:* trocar o resolver por `git rev-parse` em
  runtime.
- **Atribuição de crash.** Stage que entra em `running` e nunca atinge terminal
  carrega a revisão. *Mutação:* mover a escrita para o terminal ⇒ NULL nas rows
  de crash, que são justamente onde a atribuição vale mais.
- **Não-clobber.** Stage que passa por `running` → `completed` preserva a
  revisão. *Mutação:* usar chave em `output_summary` ⇒ apagada pela atribuição
  total.
- **Execução mista real.** Dois stages com revisões diferentes ⇒
  `COUNT(DISTINCT) == 2` e o entregável reporta **as duas**. *Mutação:*
  first-writer-wins ⇒ reporta uma.
- **Largura da coluna.** INSERT com SHA de 40 chars + `-dirty` não estoura.
  *Mutação:* `String(20)` ⇒ `DataError` em Postgres. Marcar como teste de
  Postgres — SQLite não enforça largura e daria verde falso.
- **Degradação sem a env.** Sem `MATHOMS_BUILD_SHA`: processo **sobe**,
  `/health` devolve `null`, nenhum log carrega a chave (ausente, não
  `"unknown"`), e o entregável diz `desconhecido` **em destaque** — nunca linha
  faltando.
- **Escopo não mente.** Run com `from_stage` ⇒ o entregável nomeia os stages
  herdados e o run de origem. *Mutação:* hardcodar `full`.
- **Delta de jobs de CI = zero.**

## Fora desta lane

- **Índice `commits_between` / por arquivo.** Domínio empírico **vazio**: zero
  commits nos 6 arquivos-âncora dos P0/P1 do §r4 ⇒ o instrumento teria produzido
  zero flags na rodada que motivou o pedido. Retomar só com demanda medida (≥3
  achados numa rodada cuja triagem travou por falta de histórico do arquivo).
- **4º estado de triagem `JÁ-CORRIGIDO`.** Os 10 itens fechados do §r4 fecharam
  por **output**, nunca por histórico de commit. Entra **uma linha** em
  `references/rubric.md` tornando explícito o fechamento que já funciona; shape
  de dado novo para mecanismo existente é inflação.
- **Amplificador "zero commits + drift ⇒ severidade sobe".** Dead code medido
  (52, 15 e 24 commits nas 3 janelas reais) e inferência inválida (config em DB
  move número sem commit). Fica `NOTE:` nomeando a dimensão cega.
- **Superfície do cliente.** Nada de SHA no relatório da família nem na faixa de
  auditoria: há drift de 4 vias pré-existente ali, herdado e não criado aqui.
- **Página de runs no console ops.** Já é o item IA-2 do [[PLAN-internal-admin]].
- **Coluna em `pipeline_runs`, tabela `run_executions`, backfill, bump de
  `SCHEMA_VERSION`, coluna per-artefato.** Rejeitados com medição na
  [[ADR-362]] §Alternativas rejeitadas.

## Débito adjacente descoberto (não é escopo, é registro)

- **`pipeline_runs.reprocess_all` é coluna morta** — zero writers de produção
  (só a migration inicial, o seed de dogfood com `False` e o default), 0/109
  rows. Enquanto existir sem writer, leitor futuro produz frase falsa. Ou ganha
  writer, ou `drop_column`.
- **Os scripts sob `.claude/skills/` têm cobertura zero** — importam `backend` no
  topo e nenhuma suíte os alcança. Foi por isso que o helper de duração migrou
  para `dev/` (onde o teste chega) e por isso o fix de escopo por run do parecer
  shipou sem teste unitário. Gap estrutural, maior que esta lane; dono natural é
  a [[A42.l3]].
- **`output_summary` não tem schema declarado** e é sobrescrito por atribuição
  total em 3 pontos. Qualquer chave nova ali precisa ser injetada em
  `result.detail` antes do terminal.
