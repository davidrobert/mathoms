---
id: A40.l32
type: lane
title: "Proveniência do executor: qual código computou este run"
sprint: A40
status: open
priority: P1
branch_slug: a40-l32-proveniencia-do-executor-do-run
adrs:
  - "[[ADR-362]]"
  - "[[ADR-363]]"
  - "[[ADR-343]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/ci
  - area/pipeline
  - area/infra
---

# A40.l32 — `proveniencia-do-executor-do-run`

> **Promovida da [[A42]] por decisão do dono em 2026-08-05**, reparentada
> (`sprint: A40` + `git mv`) pela porta de nível-lane do §Gatilho de promoção da
> A42 — precedente exato da [[A40.l24]], que nasceu `A41.l1`. Não reabre a
> cláusula 2 do §Critério de admissão da A40: aquela governa achado **novo sem
> dono**; esta lane já nasceu escrita, com ADR exigida e dono.

> ✅ **F3 fechada em 2026-08-08 — PRs #1291 e #1297**, com uma regressão pelo
> meio. A F3 shipou `executor_revision` dentro do dict `checks` do `/health` sem
> pô-lo no set `informational` que o agregado ignora: o valor é um sha de 12
> chars ou `None`, nunca a string `"ok"`, então `status` virou `"degraded"` em
> **toda** chamada — inclusive com Redis, Celery e DB sadios, e no CI via
> `MATHOMS_BUILD_SHA: ${{ github.sha }}`. Blast radius zero (os healthchecks do
> compose usam `curl -fsS`, e ninguém lê `status`), mas era fail-open no único
> sinal sumarizante do endpoint. Corrigido no #1291, com emenda datada na
> [[ADR-363]] declarando a revisão informacional para efeito do agregado.
>
> O #1297 fechou a lacuna que deixou a regressão invisível — **nenhum teste
> asseria `status == "ok"`** — e, ao cobrir o payload pelo caminho HTTP, achou um
> segundo defeito preexistente: `redis_cache` era emitido (quando
> `REDIS_CACHE_URL != REDIS_URL`) sem estar declarado no `HealthResponse`.
> `extra="allow"` **não filtra**, então o campo viajava ao cliente sem existir no
> OpenAPI, e é agregado em `status` — quem visse `degraded` não achava a causa em
> campo nenhum do contrato. Declarado + snapshot regenerado.

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

**Correção de premissa, 2026-08-05 (dono):** a versão inicial desta lane dizia
que "em produção é pior — incidente não é atribuível a release". **Não existe
produção**: o projeto roda só na máquina do dono, em dogfood e desenvolvimento.
O escopo é o **loop local**, exatamente como o dono descreveu. Emendas nas
[[ADR-362]] e [[ADR-363]].

A lane nasceu na [[A42]] pela cláusula 3 do §Critério de admissão daquela sprint
(**instrumento de certificação**) e foi promovida para a A40 por decisão do dono. O §r4 do [[PIPELINE-REVIEWS-active]] declara um
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

Reordenadas em 2026-08-05 após a correção de premissa: **o preflight subiu para a
primeira onda** porque o incidente que ele impede é local, já aconteceu (worker
stale invalidou uma rodada de 74 achados) e ele **não depende de migration**.

| Fase | Entrega | Valor imediato | Migration? |
|---|---|---|---|
| **F0** | `dev/build_info.py --export` nos targets nativos do Makefile + `${{ github.sha }}` no CI + linha de boot do worker + **preflight** (revisão do processo vivo vs HEAD, avisa) | **Impede** o worker stale antes do run, em vez de descobri-lo na síntese. Nenhum schema tocado | **não** |
| **F1** | Coluna `executor_revision` em `pipeline_stage_logs` + write nos 2 INSERTs | Nenhum run novo nasce inatribuível. Não deixar lagar: ~53 runs/30 dias e backfill proibido | **sim**, 1 (`ADD COLUMN NULL`) |
| **F2** | Leitor: frase de escopo derivada dos stage logs + `run_meta.md` em prosa + `executor_revision` em todo log record | **A dor literal do dono** — ele lê no arquivo que já abre | não |
| **F3** | `/health` com campo novo (`Optional[str]`) e `version` de volta a `settings.API_VERSION` | Corrige defeito de tipo **latente**; sem pressa, não há healthcheck rodando | não |
| — | ~~Prod: env na plataforma, fail-fast de boot, label OCI, OTel~~ | **Não aplicável até existir deploy** — ver [[ADR-363]] §Emenda | — |

**Por que a coluna não é a F0 e continua sem lagar:** o preflight entrega valor
sem tocar schema, então vai antes por ser mais barato e mais urgente. Mas a
restrição do `data-engineer` segue de pé — **cada dia sem a coluna produz runs
permanentemente inatribuíveis** (backfill fabrica dado), então F0 e F1 são a
mesma onda, não fases distantes.

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
  faltando. **E `status` continua `"ok"`** — com a env setada também. *Mutação
  que mata:* tirar `executor_revision` de `informational`. **Corrigido em
  2026-08-08 (era o ponto cego que deixou a regressão passar):** o critério
  mandava medir o **campo** e calava sobre o **agregado**, então a F3 satisfez o
  critério e degradou o endpoint em toda chamada. Campo cujo valor saudável não
  é literalmente `"ok"` pertence a `informational`; quem reimplementar esta fase
  medindo só o valor de `executor_revision` reintroduz o defeito.
- **Contrato do payload fecha nas duas direções.** Todo campo que `health()`
  emite está declarado no `HealthResponse`, e todo campo declarado é emitido por
  algum ramo. *Mutação que mata:* emitir check novo sem declarar (`extra="allow"`
  não filtra — ele vaza ao cliente fora do OpenAPI) ou declarar campo que ramo
  nenhum produz. Medir a 2ª direção em `response.json()` **não funciona**: o
  `response_model` materializa o default de todo campo declarado, então o payload
  HTTP traz `campo: null` mesmo sem o endpoint emitir — a fonte é o dict de
  `health()`.
- **Escopo não mente.** Run com `from_stage` ⇒ o entregável nomeia os stages
  herdados e o run de origem. *Mutação:* hardcodar `full`.
- **Delta de jobs de CI = zero.**
- **Preflight (F0) morde.** Lançar o worker num commit, mover a árvore, disparar
  o run ⇒ o preflight **avisa** antes de executar. *Mutação:* comparar o run
  passado em vez do processo vivo ⇒ não avisa (era o desenho original, e ele não
  diz nada sobre quem vai executar).

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
- **Tudo que depende de deploy** — env na plataforma, `${MATHOMS_BUILD_SHA:?}`,
  fail-fast de produção, label OCI, tag imutável, `service.version` no OTel
  (opt-in e sem coletor local). Re-entra quando houver deploy; **não está na
  fila de ninguém**.
- **Superfície do cliente.** Nada de SHA no relatório da família nem na faixa de
  auditoria: há drift de 4 vias pré-existente ali, herdado e não criado aqui.
- **Página de runs no console ops.** Já é o item IA-2 do [[PLAN-internal-admin]].
- **Coluna em `pipeline_runs`, tabela `run_executions`, backfill, bump de
  `SCHEMA_VERSION`, coluna per-artefato.** Rejeitados com medição na
  [[ADR-362]] §Alternativas rejeitadas.

## Prioridade: base honesta

P1 herdado da abertura. Com a correção de premissa, a perna de produção da
justificativa **desaparece** — o que sustenta P1 é o custo local medido: o
worker stale invalidou uma rodada inteira de review (74 achados), e a F0 custa
zero API. Um `product-manager` pode legitimamente rebaixar para P2; a lane
declara a base em vez de herdar o número.

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
