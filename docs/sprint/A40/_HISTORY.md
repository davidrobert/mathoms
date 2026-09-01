---
id: MOC-a40-historico
type: moc
title: "Sprint A40 — histórico: o que foi decidido, medido e encerrado"
aliases: ["A40 histórico"]
date: "2026-08-14"
---

# Sprint A40 — histórico

> **Registro fechado, separado do `_README` em 2026-08-14.** Cada seção aqui é
> pendência **resolvida**, entrega **feita**, painel **encerrado** ou snapshot
> **datado** que o próprio texto manda não reescrever. Nada aqui governa
> decisão de hoje — o que governa ficou em [`_README`](_README.md).
>
> **Por que separar:** o `_README` saiu de 195 linhas (2026-07-30) para 1692
> (2026-08-13), 8,7x em 14 dias, e virou ~40k tokens que toda pergunta sobre a
> sprint pagava inteiros. A política de append-only ("não o reescreva") é certa
> para auditoria e cara para contexto; separar preserva as duas — o histórico
> continua íntegro e some do caminho de quem só quer saber o que fazer agora.
>
> **Não apague, não reescreva.** Snapshot datado que alguém "atualiza" deixa de
> ser evidência.

## Estado da Onda 1 (2026-08-03) — o que shipou e o que a Onda 0 não invalida

Três lanes da Onda 1 estão em `main`, entregues **antes** da Onda 0 existir
(ela nasceu em 2026-08-03, do incidente `2ded7aab`):

| Lane | Commit | O que ficou medido |
|---|---|---|
| [[A40.l1]] | `92a91884` (#1118) | 261 colisões cross-grupo · Σ 81.288.000 cents · baseline congelado off-git · **8 ratchets, 4 re-confirmados manualmente** (4 só com a prova do implementador — ver [[A40.l1]] §Fechamento, residual 4) |
| [[A40.l3]] | `b12aff30` (#1124) | `janela_12m` passa de 0 consumidores a leitura por seletor único; rótulo impresso (tooltip não sai no PDF) |
| [[A40.l4]] | `6c5d9814` (#1139) | precedência de 3 fontes declarada ([[ADR-356]]); 7 → 12 seções entregando parágrafo |


**A precedência da Onda 0 sobre a Onda 1 é real, e não retroage sobre o baseline
da l1.** O argumento da Onda 0 é que medir exige run que completa. Isso vale para
todo gate que dependa de **run com parecer** — inclusive o §Gate de saída do
dogfood de [[PLAN-report-trust]], que não pode iniciar o contador de 2 re-runs
consecutivos antes da [[A40.l16]]. Mas a medição da l1 é
`dev/certify_ledger_local.py`, que é **read-only, sem Celery e sem LLM**: re-deriva
E3+E4 in-process sobre o E2 persistido. O caminho que o incidente quebrou (parecer
→ `needs_review` → `success: False` → zero linha em `reports`) **não participa**
dessa medição. As 261 seguem válidas como baseline de KR-B.

O que **não** foi cumprido nas três: a re-triagem bloqueante da l4 (os 7 achados
inertes verificados contra output renderizado) **rodou 2× e bloqueou nas 2**; a
**3ª passada, pós-remediação final, não rodou** (limite de gasto) e a lane mergeou
assim por decisão do dono. O risco ficou delimitado — s4 entrega sem contagem, s8
sem DAS, s9 suprimido, `s3` desligado depois (#1144) — mas os 3 fixes finais não
foram verificados no render. Cronologia precisa em [[A40.l4]] §Fechamento;
disposição em §Pendências de decisão nº 4 (resolvida 2026-08-05: não-cumprido,
subsumido pelo gate de saída, com o checklist como insumo declarado).

## Entregas fora de lane (2026-08-03)

Trabalho que **shipou dentro da janela desta sprint sem lane própria** — nasceu de
gate/achado, não do backlog dos 33. Registrado aqui porque a §Lanes não o cobre e
sem isso a sprint fecharia dizendo menos do que entregou.

| Entrega | Commit | ADR | O que ficou medido |
|---|---|---|---|
| Determinismo do cone de IF | `35acc75e` (#1156) | **[[ADR-360]]** `Proposto` | Cone era sorteado da entropia do SO (0,7% de diferença entre runs com input idêntico). Seed passa a ser constante de modelo + guard de boundary; `n` 10k→50k (dispersão 2,4%→1,2% a 85 ms); proveniência (`mc_version`/`seed_usado`/`n_simulacoes_usado`) no artefato; schema do bloco fechado. Mediu que **subir `n` não compra reprodutibilidade** (0,2% sobra a 1 M) |
| Sentinela de não-convergência | `7107b956` (#1158) | — | `prazo_anos_realista` não projetável emitia 999, somado à idade virava `idade_meta_usada: 1040` em path citável formatado como "anos". Passa a emitir ausência com motivo. Fecha o item 5 do §Deferimento da [[ADR-360]] |
| Percentil censurado do cone | `790c1c5f` (#1162) | **[[ADR-361]]** | `Pk` do ano de IF saía da base **dos sobreviventes** (otimista, e mais otimista quanto pior o plano) enquanto `prob` usava `n` cheio. Passa a quantil na base cheia com censura declarada por percentil; corrige também o truncamento de `int(np.percentile)`. `mc_version` → `3.0` |

**O que sobra dos três** está na [[A40.l25]], [[A40.l26]], [[A40.l28]] e
[[A40.l29]] — não em §Deferimento de ADR, que é invisível ao `SPRINT_CURRENT`.
**A [[A40.l28]] fechou em 2026-08-07** (#1267/#1268/#1269, [[ADR-369]]): os itens
1 e 2 do §Deferimento da [[ADR-361]] saíram do papel. Sobram a [[A40.l25]]
(faixa de 5 pp, `sigma` por perfil), a [[A40.l26]] (`_solve_prazo`) e a
[[A40.l29]] (manchete/eixo/faixa na UI).

> **Correção de cobertura — 2026-08-03.** A l25 e a l26 cobriam 3 dos 7 itens do
> §Deferimento da [[ADR-361]]: o item 5 (faixa de 5 pp) e o residual da
> [[ADR-360]]. Os outros quatro estavam **descritos e sem destino** — exatamente
> o estado que esta seção existe para impedir. Roteados agora: **l28** leva os
> dois de contrato (idade-meta como input, rename do rótulo) e **l29** leva os
> três editoriais, que a própria l25 declarou fora de escopo por dependerem de
> brief. O item 3 (sentinela 999) tinha sido fechado pelo #1158.

### Órfão de dispatch (gate de paridade Go, não report-trust)

Gatilho distinto dos três acima: rodar `make go-parity` ([[TRACK-f2-cutover]]) com
Redis fora do ar. Registrado na mesma seção porque a natureza é idêntica — shipou
na janela da sprint, sem lane.

| Entrega | Commit | ADR | O que ficou medido |
|---|---|---|---|
| Dispatch falha alto + compensação por caller | `9d30dc2d` (#1154) | **[[ADR-359]]** `Decidido` | `make pipeline-run` com broker fora saía **exit 0** e deixava o run `pending` para sempre, trancando o workspace via `ux_pipeline_runs_ws_active` com "Cancele ou **aguarde**". O fallback em `threading.Thread(daemon=True)` **duplicava execução** (`.delay()` e a escrita de `celery_task_id` no mesmo `try`; `running` não é terminal para `_mark_run_started`). Deletado; compensa quem fez a ação forward (`trigger` marca `failed`, `resume` **reverte** restaurando `paused_at_stage`); `UPDATE` condicional + `rowcount` pareado com a guarda da [[ADR-297]]; `celery_task_id` pré-gerado **antes** do enqueue; cura no ponto de bloqueio (write no Postgres — funciona com Redis fora); 503 + `Retry-After` |
| Gate estático de primitiva non-stateless | `9d30dc2d` (#1154) | emenda **[[ADR-111]]** | `STATELESS_AUDIT` §5 afirmava "`threading.Thread` — nenhum resultado em app code" desde 2026-04-20 e a afirmação era **falsa na data em que foi escrita** (o thread existia desde 2026-04-14). Não houve drift: nada a verificava. `dev/check_stateless_primitives.py` é **AST**, não grep — grep acusa `category_cache.py:3`, cuja docstring *afirma a ausência*, e confunde o `create_task` do agregado Tarefas com `asyncio.create_task` |

**O que sobra** está na [[A40.l27]]. **Consequência para outra lane:** a [[A40.l19]]
passa a ter **dois** consumidores (a [[ADR-357]] §7 e a varredura da l27) — se ela
escorregar, os dois param.

**Lição transferível registrada na emenda da [[ADR-111]]:** afirmação de audit sem
gate é dívida, não garantia. Mesma família do §Débito de método herdado da r3, no
fim deste arquivo.

**Owner-gated destas entregas** (também em [[OWNER-GATED]]): flip da [[ADR-360]] e
da [[ADR-361]] `Proposto` → `Decidido`; **nota one-shot de recalibração** no
primeiro relatório pós-merge (seed + `n` + censura deslocam todo o bloco de IF, e
sem a nota a leitura racional de "IF em 2040" virar 2041 é "meu plano piorou");
**re-rodar o Tier-1** do gate F2 (`make go-parity WS=<dogfood> RUNS=2`) para
confirmar 0 diff residual no controle Py↔Py sem allowlist para o cone.

> **Ampliação da nota one-shot — [[A40.l28]] (2026-08-07), registrada, não
> executada.** A [[ADR-369]] deslocou o bloco de IF uma terceira vez, e desta vez
> a mudança é de **semântica**, não de calibração: a probabilidade deixou de medir
> P(o modelo bater a própria data) e passou a medir P(cumprir o prazo que a
> família declarou). Consequências para a nota especificada em [[ADR-360]] §Nota
> one-shot: (a) o gatilho tem de disparar também para `mc_version` `"3.0"` e
> `"4.0"`, não só ausente/`"2.0"`; (b) o par "ano antigo → ano novo" **não basta**
> — o número da probabilidade muda por motivo diferente do ano, e para muitos
> planos ele vai **cair** (o alvo declarado costuma ser mais curto que o
> determinístico); (c) o elemento 2 da nota ("a variação é sempre no sentido de
> corrigir para mais conservador") **não vale** para esta terceira mudança: aqui a
> probabilidade pode subir ou descer conforme a folga do plano. Sem essa ressalva,
> a nota afirmaria monotonia que a [[ADR-369]] quebra. Escrever a nota continua
> owner-gated; esta entrada existe para que ela não seja escrita com a
> especificação de duas mudanças atrás.

## Decisões do dono — A40.l18 (2026-08-06)

Três perguntas que o painel de co-design da [[A40.l18]] classificou como
não-delegáveis. **Todas respondidas na mesma sessão**, com a recomendação
aceita nos três casos. O detalhe e o mecanismo ficam na lane (§Decisões do
dono); aqui fica o registro de que foram feitas e quando, para que o §Gate de
saída não as reabra por esquecimento.

1. **Honestidade na tela em run degradado — metade negativa agora.** O PR2 da
   l18 suprime o `CleanBar` (que hoje **afirma** "sem pendências que afetem a
   leitura deste relatório", inclusive no PDF); a ressalva positiva fica com a
   [[A40.l22]]. Recusado segurar o PR2 até a l22 — ela depende do PR1 da
   [[A40.l20]] e estouraria a `date_target`, revertendo a [[A40.l21]] já em `main`.
2. **Detecção de degradação — card em `/admin/metrics` + cadência do dono.**
   Sentry fica para a próxima janela (segue OWNER-GATED). Recusado
   explicitamente "só log estruturado".
3. **Tolerância de conservação — follow-up com ADR própria**, fora do PR2. Ver
   [[A40.l18]] §Follow-ups nomeados, item 1: `patrimonio_composicao_diff_pct_max: 5`
   deixa passar R$ 150k–400k não explicados num patrimônio de R$ 3–8M, e os dois
   únicos checks de tolerância zero (CV16/CV17) estão fora do conjunto que pausa.

Estas **não** entram em [[OWNER-GATED]] pelo mesmo critério da §Pendências
abaixo: aquele registro é de gates estratégicos entre planos, e higiene de
sprint diluiria o sinal dele.

## Pendências de decisão (2026-08-03)

Doze perguntas de **higiene interna desta sprint** — **12 resolvidas** (nº 1, nº 7,
nº 9 em 2026-08-03; nº 10 em 2026-08-04 pela [[A42]]; nº 6 e nº 11 em 2026-08-05
pelo #1197; nº 2, 3, 4, 5, 8 e 12 em 2026-08-05 por decisão do dono, delegada e
aplicada nesta passada), **0 abertas**. Deliberadamente **não** entram
em [[OWNER-GATED]]: aquele registro é de gates estratégicos entre planos
(licença, flip de cutover, LGPD), e misturar higiene de sprint diluiria o sinal
dele. Cada item traz o que foi **medido** sobre `origin/main` (`a1e70223`) e
termina em pergunta — nenhuma decisão embutida.

**1. Qual é o predicado do campo `status` de lane?** — ✅ **RESOLVIDA 2026-08-03.**
Predicado escrito e aplicado em §Predicado do campo `status` de lane (2 flips:
l18 e l22 → `blocked`). O diagnóstico abaixo fica como registro do que foi medido.

O campo não deriva de regra declarada e está **anti-correlacionado** com dependência
satisfeita. Medido no frontmatter das 24 lanes:

- **Mesma onda, mesmo `depends_on`, `status` diferente** — [[A40.l2]] (`open`) e
  [[A40.l12]] (`planned`) estão as duas na Onda 2 e dependem as duas só de
  [[A40.l1]], que está `shipped`. Segundo par: [[A40.l14]] (`planned`) e
  [[A40.l23]] (`open`), as duas na Onda 4, as duas sem `depends_on`.
- **8 lanes com todas as deps satisfeitas estão `planned`** (l5, l7, l8, l11, l12,
  l13, l14, l15) enquanto **3 lanes com dep não satisfeita estão `open`** (l18
  depende de l21 `open`; l20 de l18 `open`; l22 de l20 `open`).
- O enum do schema admite `planned` · `open` · `in_progress` · `blocked` ·
  `shipped` · `cancelled`. **`blocked` não é usado por nenhuma das 24.**

`status` significa "dep satisfeita", "onda aberta", "alguém pegou", ou nada
verificável? Se houver predicado, quem o deriva e quando?

**2. A [[A40.l20]] pode abrir PR antes de a [[A40.l18]] mergear?** — ✅
**RESOLVIDA 2026-08-05: sim para o PR1, não para o PR2** — e a prosa é que estava
errada, não o frontmatter. Medido em `backend/app/tasks/pipeline_task.py`: o
desfecho retido do parecer retorna `success: False` (`_needs_review_return`), e
nesse ramo o código (a) rolla a sessão de artifact (`:1329`), (b) só chama
`_persist_planner_review_if_applicable` dentro de `if result.success`
(`:1192-1193`) e (c) grava `failed` + `failed_at_stage` (`:1180-1200`) — as três
são o diff da l18. A dependência **não** é de vocabulário; é de hunk. Logo:
`depends_on` mantido, `parallel_with` **rejeitado**, e a lane passa a declarar
entrega parcial em 2 PRs (l20 §Sequência de entrega). Efeito em cadeia: a
[[A40.l22]] continua `blocked`, mas o gatilho dela passa a ser o **PR1** da l20 —
sem isso a superfície que torna a 6ª classe do gate satisfazível ficaria atrás de
l21→l18→l20→l22 (4 merges) e a `date_target` mataria o único bloqueador de fato
do beta. O diagnóstico abaixo fica como registro do que foi medido.

A prosa afirma que sim em **3 lugares** (`_README` linha da l20 na tabela de lanes ·
`_README` §Ondas ordem interna · [[A40.l20]] blockquote de abertura, e um 4º em
[[PLAN-report-trust]]), sempre na forma "depende da *decisão*, não do *merge*". O
frontmatter da l20 declara `depends_on: ["[[A40.l18]]"]`, que é a única relação de
dependência do schema — `parallel_with` existe e é usado por 6 das 29 ([[A40.l24]] →
[[TRACK-f2-cutover]], [[A40.l25]] → [[A40.l11]], [[A40.l26]] e [[A40.l28]] →
[[A40.l25]], [[A40.l27]] → [[A40.l21]], [[A40.l29]] → [[A40.l25]]+[[A40.l28]]),
mas não expressa "depende da decisão". Qual das duas leituras
vale para quem pega a lane: a prosa ou o frontmatter?

**3. A tabela de evidência da emenda da [[ADR-304]] tem 8 linhas — o denominador 9 é
o quê?** — ✅ **RESOLVIDA 2026-08-05: o denominador 9 estava errado; não existe 9º
run.** A emenda original da [[ADR-304]] (#1142) rotulou a tabela de 8 linhas como
"9 runs consecutivos" e derivou "8/9" e "89%". O #1159 ([[A40.l16]] · Onda 0) **já
tinha reescrito** a emenda com a janela persistida completa (19 runs,
2026-07-10 → 07-31; sob o prompt 2.2.0: 8 runs, 7 afetados = 87,5%, 6 apagaram 15
itens; janela inteira: 7 runs apagando / 16 itens) e corrigido [[ADR-304]],
[[ADR-296]], [[ADR-358]], [[PLAN-report-trust]] §Frente 4 e [[A40.l16]] — a
pendência foi medida contra a versão pré-#1159. Resíduos textuais corrigidos no
#1216: [[A40.l22]] ("durar 9 runs" → 7 runs / 16 itens sem detecção) e
[[PLAN-report-trust]] §Fora de escopo ("série de 9 runs" → 19). **Não** confundir
com o ~89% de violação de citação (32/36, n=3) de [[A26.l1]] — métrica distinta e
correta. O diagnóstico abaixo fica como registro.

Medido na tabela (linhas 127-134 do arquivo da ADR): **8 linhas de dado**; **7 de 8
(87,5%)** têm `number_in_prose` > 0; **6 de 8 (75%)** tiveram item apagado (a linha
de 2026-07-31 é o run que falhou, com `—` na coluna de apagados). E **7 documentos**
afirmam "9 runs" / "8 de 9" / "89%": [[ADR-304]], [[ADR-296]], [[ADR-358]],
[[PLAN-report-trust]], este `_README`, [[A40.l16]] e [[A40.l22]]. O run do incidente
`2ded7aab` **já é** a 1ª linha da tabela. Falta uma 9ª linha que existe e não foi
tabulada, ou o denominador 9 — e os 89% derivados dele — está errado?

**4. A re-triagem bloqueante da [[A40.l4]] conta como critério cumprido?** — ✅
**RESOLVIDA 2026-08-05: não conta.** Verificação não-rodada aceita como cumprida é
exatamente a classe "gate verde medindo a camada errada" que esta sprint existe
para matar — a lane fica registrada como **critério parcialmente cumprido**, sem
reabrir status (`shipped` = PR mergeado, e mergeou). **E não nasce work-item
novo:** os alvos nomeados da 3ª passada já foram decompostos em itens adotados
(contagem de imóveis → [[A40.l6]]; DAS e PD-20 → [[A40.l12]]; rótulo da
[[ADR-306]] → [[A40.l11]], #1197), e o que sobra — "os três fixes da remediação
final se sustentam no output renderizado?" — é **subsumido pelo §Gate de saída e
encerramento**: qualquer remanescente `agora-visível-e-errado` aparece como
ocorrência das 6 classes ou como P0/P1 novo nos 2 re-runs, e as duas cláusulas
travam o gate. **Subsunção só é real com insumo declarado** — ver a linha nova em
§Gate de saída e encerramento; sem ela, "subsumido" seria esperança, não
mecanismo. O diagnóstico abaixo fica como registro.

Cronologia medida e agora escrita na lane: rodou **2×** e **bloqueou nas 2**; a 1ª
achou C29 e C32 `agora-visível-e-errado`; a 2ª achou C32 resolvido e provado por
mutação, C29 ainda errado (o DAS *recolhido* que substituiu a estimativa também era
falso) e **2 contradições novas** (`s4` com 6 imóveis contra 4 na seção; CV9 contando
7 de 7 com o render entregando 6); a **3ª passada, pós-remediação final, não rodou**
(limite de gasto). "Rodou 2×, bloqueou 2×, corrigido, 3ª passada não rodou" satisfaz
o critério de aceite, ou a lane precisa da passada final antes de fechar de fato?

**5. A [[ADR-356]] flippa para `Decidido (A40.l4)` ou fica `Proposto` com o motivo
escrito?** — ✅ **RESOLVIDA 2026-08-05: flip, com emenda datada.** Código em `main`
desde `6c5d9814` (#1139); `Proposto` com código shipado é a classe RV3-04 que esta
sprint cataloga. A emenda registra (a) que o critério de aceite da lane foi
parcialmente cumprido e que o residual é portado pelo §Gate de saída e
encerramento (§Pendência nº 4) e (b) a troca de dono do §Deferimento do `s1`,
l5 → [[A40.l6]] (fecha o "Relacionado" da §Pendência nº 6). O diagnóstico abaixo
fica como registro.

Medido: `status: Proposto` no arquivo; [[A40.l4]] (a lane que a implementa) está
`shipped` em `6c5d9814` (#1139). O CLAUDE.md §"Política operacional" diz que o PR de
implementação flippa a ADR no merge — mas o critério de aceite da lane não foi
integralmente cumprido (nº 4 acima). Flip agora, ou `Proposto` com o motivo do
não-flip registrado no próprio arquivo?

**6. Os 4 residuais que a [[A40.l4]] roteou para "lane própria" ficam na A40?** —
✅ **RESOLVIDA 2026-08-05.** Absorvida pela resolução da Pendência 11 (mesma
triagem, mesmo PR) — ver lá o destino item a item. Resultado: 3 dos 4 adotados em
lanes vivas ([[A40.l6]], [[A40.l12]] ×2); o 4º ("Base da cascata") não tinha dono
vivo nem materialidade medida e saiu da A40 por disposição explícita ([[REPORT-REVIEWS-active]]).
O diagnóstico abaixo fica como registro do que foi medido.

Medido na §Residual da lane — 14 linhas, das quais **4** têm `Dono` = "lane própria":

1. **`s3` contradiz a tabela da própria S3** — 3 categorias no parágrafo, 2 classes
   na tabela (`lane própria (gate financial-planner)`).
2. **`perfil_familia.right` publica `n_imoveis`** — a contagem que o `s4` deixou de
   afirmar; contradição cross-seção com a tabela da S4.
3. **PD-20 — a meta de TRS não é configurável** — `PassiveIncomeConfig.trs_meta_pct`
   nunca é lido pelo `RatiosCalculator`.
4. **Base da cascata** — `receita_bruta = receita_pj_anual` em vez de
   `FinanceiroPJSnapshot.receita_bruta_total_anual` ([[ADR-238]]).

Uma 5ª linha tem disposição distinta ("lane pós-re-medição do balde": reintroduzir
DAS no `s8` e `das_simples` em `despesas_impostos` depois de re-medir o balde com o
matcher de `69a2fad4`). Esses ficam na A40 — e então precisam de lane, contra as 24
atuais — ou viram disposição explícita de não-fazer na §Fora do sprint?

**Relacionado — ✅ RESOLVIDO 2026-08-05:** o `s1` publicando "residência própria
de R$ 0,00" **move** da [[A40.l5]] para a [[A40.l6]]. Critério: classe
zero-como-valor (RV3-27) é escopo declarado da l6; a regra já está decidida em
[[ADR-356]] §D7 e o arquivo é `summaries_narrator.py` (pipeline), disjunto do
entregável da l5 (codegen + gate de contrato de frontend) — o campo tem consumidor
e o zero é genuíno, logo não é leitura órfã. Manter na l5 decidiria a política de
zero-como-valor em dois lugares. Registrado em [[ADR-356]] §Emenda 2026-08-05, no
§Itens adotados da l6 e no §Escopo herdado da l5 (como ponteiro).

**7. Onde mora o tripwire de revert da [[A40.l21]], e quem é o owner?** —
✅ **RESOLVIDA 2026-08-03.** Host = §Gate de saída e encerramento (novo); gatilho =
`date_target` do frontmatter; owner = quem fizer o pickup seguinte após a data. O
diagnóstico abaixo fica como registro.

A amarra "se a [[A40.l18]] escorregar >1 sprint, reverta a [[A40.l21]]" está em **3
lugares de prosa** (`_README` §Ondas · [[A40.l21]] §Decisão · [[PLAN-report-trust]])
e em **nenhum mecanismo**: este `_README` não tem seção própria de gate de saída nem
de DoD — todas as menções a "gate de saída" fora desta seção (tabela de lanes,
§Ondas, §Estado da Onda 1) são ponteiro para [[PLAN-report-trust]] §Gate de saída do
dogfood — e o frontmatter da sprint declara `date: "2026-07-30"` sem data de fim. Sem
data de fim, "escorregar >1 sprint" não é avaliável. Qual artefato hospeda o
tripwire, com que gatilho, e sob qual owner?

**8. Vale acrescentar o path off-git ao lado de cada número medido?** — ✅
**RESOLVIDA 2026-08-05: vira convenção, com host único e escape de ponteiro.** A
regra mora em [[REPORT-REVIEWS-active]] §Convenção de rastreamento, cláusula 5 —
não nesta seção (que morre com a sprint) e não replicada nos 4 MOCs de skill
(cópia em 2 hosts ⇒ migra para ADR). Escopo do retrofit: **apenas os números
listados abaixo**, sem varredura. Aterrissados no #1216: "105/105 grupos" em
[[REPORT-REVIEWS-active]] §r3 (comando + síntese congelada) com ponteiro na
§Tese; "25m23s e US$ 1,5655" em [[PLAN-report-trust]] §Incidente de origem
(query de re-medição); "8 ratchets" em [[A40.l1]] §Fechamento residual 4 (as 8
alavancas coladas do #1118; a partição 4/8 declarada não-re-derivável). O
diagnóstico abaixo fica como registro.

Números que circulam na sprint sem caminho de re-medição para o próximo agente:

- **"261 colisões · Σ 81.288.000 cents"** (§Estado da Onda 1 e [[A40.l2]]) —
  **resolvido 2026-08-05:** o path exato do dump (mascarado) está em [[A40.l1]]
  §Fechamento; antes só havia o destino genérico `storage/<uuid>/certify/`.
- **"105/105 grupos"** (§Tese, [[A40.l1]], [[ADR-354]], [[REPORT-REVIEWS-active]],
  [[SPRINTS-active]]).
- **"25m23s e US$ 1,5655"** do run `2ded7aab` ([[A40.l16]], [[PLAN-report-trust]]).
- **"8 ratchets"** ([[A40.l1]], [[A40.l2]]) — o corpo do #1118 enumera as 8
  alavancas de mutação, mas `tests/unit/pipeline/test_cross_group_ratchet.py`
  tem **26** testes e nenhuma partição de 8: não dá para re-derivar dos nomes de
  teste quais 4 foram re-confirmados manualmente (ver [[A40.l1]] §Fechamento,
  residual 4).

Número sem path força o próximo agente a re-medir do zero ou a confiar. Anexar o
path off-git virá convenção da sprint, ou fica caso a caso?

**9. A precedência não-negociável da Onda 0 bloqueia a [[A40.l9]]?** —
✅ **RESOLVIDA 2026-08-03: não bloqueava**, por três fundamentos medidos, e a
questão morreu duas vezes. (1) `dev/golden_diff.py` é differ puro sobre
`dev/n.py` (stdlib, *"puro/stateless (ADR-111)"*) — sem Celery, sem LLM, sem
DB; não roda nada. (2) Os goldens comparados não vêm de run vivo: as fixtures
de `tests/fixtures/pipeline_golden/dogfood/` são commitadas e o snapshot do
view-model se reproduz *"sem DB"* (rebaseline via `MATHOMS_UPDATE_SNAPSHOT=1`).
(3) De todo modo a Onda 0 completou **antes** de a l9 abrir PR (l16 #1159 +
l17 #1183) — a precedência já não retinha nada. A isenção do §Estado da Onda 1
para a l1 valia para a l9 *a fortiori*: o instrumento da l1 ao menos lê DB; o
da l9 nem isso. A l9 shipou em #1187 + #1188. O diagnóstico abaixo fica como
registro.

A [[A40.l9]] é a única lane da Onda 1 que não shipou (`status: open`, sem
`depends_on`). O §Estado da Onda 1 escreveu a isenção **só para a medição da
[[A40.l1]]** — `dev/certify_ledger_local.py` é read-only, sem Celery e sem LLM. O
critério de aceite da l9 são 3 casos em
`backend/tests/test_tributario_run_scoped_inputs.py` **mais** conferência de delta
`↑` por `dev/golden_diff.py`. A l9 está isenta pelo mesmo argumento da l1, ou o
golden_diff a amarra a um run completo — e portanto à [[A40.l16]]?

**10. A [[A40.l27]] entra na A40 ou é despejada para a [[A41]]?** —
✅ **RESOLVIDA 2026-08-04 pelo §Critério de admissão da [[A42]]**, que declara
fechar esta pendência. A regra geral que faltava está escrita lá em 5 cláusulas
com precedência: destino é **quem já possui o arquivo ou a superfície** (tie-break
primário); a **A40 admite apenas por adoção** depois de 2026-08-03 — nada nasce
lane nova nela, *mesmo sendo P0*, com exceção única e nomeada de P0 que alcança o
usuário, sem dono de arquivo em lane viva, e cuja espera se mede em semanas; a
**A42 admite por camada** (ingestão, razão, contrato de store, instrumento);
**plano temático vivo tem precedência sobre sprint**; e o que não passa recebe
disposição explícita no MOC da skill. Aplicado à pergunta concreta: a l27 fica na
A40, porque `depends_on: l19` já está aqui e nenhuma outra lane viva possui o
arquivo. O diagnóstico abaixo fica como registro.

Aberta pelo critério declarado desta sprint (residual de §Entregas fora de lane +
`depends_on: l19`, que já está aqui). Contra: o gatilho é [[PLAN-go-shell]], não os
33 achados da r3. A favor: o resíduo inclui o **único estado inescapável do
sistema** (órfão em `resuming`: fora do predicado de `fin.detect_stuck_runs`,
`cancel_pipeline_run` recusa, `is_run_active` sempre `True`), e a decisão que o
expõe já está `Decidido` em `main`. A regra vigente do dono (*"nada sai da A40"*,
2026-08-03) foi escrita para escopo **existente** — vale para lane nascida depois?
Se a resposta for A41, mover é uma linha.

**Padrão que emergiu sem ser decidido:** as lanes l24 em diante entraram por
gatilho que **não é** report-trust, cada uma com justificativa própria e nenhuma
com regra comum. Vale declarar um critério de admissão para a próxima sprint, ou
seguir caso a caso?

**Colisão de id de lane, medida nesta sessão:** esta lane foi renumerada **duas
vezes** (l25 → l26 → l27) porque #1167 e #1170 alocaram os ids em paralelo enquanto
o PR estava aberto. É a mesma classe que o CLAUDE.md já documenta para ADR ("nunca
reserve ID; reserve o trabalho") — id de lane também é recurso global monotônico
cuja alocação só é real na escrita. Vale um gate, ou a taxa de colisão é aceitável?

## Decisões do painel (correções incorporadas)

**1. O mecanismo do P0 estava errado — corrigido antes de abrir a lane.**
Três especialistas, independentemente: `normalize_banco` (`_tx_identity.py:75`) já
faz lowercase + strip-accents **antes** do hash, em `_hash_v1` e `_hash_v2`. A
caixa de `banco` **não** fura o `transaction_hash` — fura a chave de grupo. Os
carriers reais são `tipo_conta` (vocabulário `extrato` vs `extratoconta`, que
`normalize_tipo_conta` só lowercaseia) e `titular` vazio. **A duplicação medida não
muda; a causa sim.** Escrita como estava, a lane shiparia um no-op e fecharia
verde. Âncora corrigida no [[REPORT-REVIEWS-active]].

**2. O fix não pode morar na fórmula do hash.** `_hash_v1` está **congelado**
([[ADR-278]] D1) e `_hash_v2` é a chave de dedup **e** de re-ancoragem de override.
Mudar os inputs de v2 órfãna override do usuário — regressão user-facing pior que a
duplicação. Daí a sequência da [[A40.l2]]: **medir → conter → corrigir a montante →
re-ancorar → quarentenar**, sem tocar `_hash_v2`.

**3. Os 7 achados "inertes" eram um evento de embarque de regressão.** Estavam
`não-acionável`, mas são inertes **porque a [[A40.l4]] os bloqueia** — e a l4 é P0
desta sprint. No instante em que fechar, sete defeitos chegam ao usuário de uma vez,
por um PR correto. Reclassificados para `procede-bloqueado · depends_on A40.l4`, com
re-triagem item-a-item como **critério de aceite bloqueante** da l4.

**4. Padrão transversal não registrado: os gates do repo medem produção, não
consumo.** Três instâncias na mesma rodada — RV3-04 (ADR entregue sem registro do
flip), RV3-03 (CV9 verde medindo geração), RV3-13 (campo sem consumidor). É o
invariante violado por trás da metade dos achados, e a razão de a [[A40.l5]]
(codegen + gate de contrato) ser a alavanca estrutural da sprint.

**5. Viés direcional agregado.** Quatro defeitos independentes empurram o relatório
na **mesma direção otimista**: principal como renda recorrente, cobertura na janela
mais lisonjeira, dupla contagem inflando receita, prazo de IF impresso como fato.
Erro aleatório se distribui; erro sistemático numa direção é assinatura de
mecanismo. **Cada PR que altera número exibido declara o sinal esperado do delta**
(`↑`/`↓`/`=`) e `dev/golden_diff.py` confere — divergência entre declarado e medido
bloqueia o merge.

**6. Prioridade invertida, corrigida.** RV3-11 (l9) era P2 abaixo de RV3-07 (P1) que
**depende dele**: o gatilho do CTA que RV3-07 quer construir depende de
`receita_pj_anual > 0`, que RV3-11 zera. Promovido a P1 e ordenado à frente.

**7. Aceitação indevida na revisão original.** Eu havia fechado RV3-31 (duas taxas
de retirada) como refutado, "aceite cumprido nas duas superfícies". O
`financial-planner` mostrou que RV3-31 e RV3-26 se contradizem na mesma tabela: uma
das superfícies lê chave inexistente e cai em **default hardcoded** — o aceite foi
verificado contra uma constante, não contra o payload. Os números coincidem **por
acidente**. RV3-31 vira `procede-fechado-em RV3-26` ([[A40.l5]]).

**8. Os "3 dados que faltam" eram 1.** O `regime` já é derivável de documento
ingerido (`FinanceiroPJSnapshot.regime_declarado` é computado e nunca consultado), e
`dependentes.count = 0` é **observação**, não ausência. Só a taxa da dívida é ask
genuíno. Tratar os três como iguais produziria um wizard perguntando o que o sistema
já sabe — queimando a única janela de atenção do dono no item de menor valor.

## Infra de CI tocada durante a sprint (não são lanes)

Três correções de CI e uma investigação, achadas ao entregar a [[A40.l24]]. Não
têm lane porque não são escopo report-trust e não competem por capacidade — mas
ficam registradas para não virarem mudança órfã de política:

| O que | Estado | Por quê |
|---|---|---|
| `backend-tests` `timeout-minutes` 12 → 20 | ✅ `9b7d330e` (#1157) | A política declarada no job ("2× tempo observado", de maio a ~7:30) erodiu para **1,15×**: medido nos 6 PRs de 2026-08-03, 9m02s–10m21s contra teto de 12. Reprovou o #1157 duas vezes por variância de runner, com diff que não alcança o job. Teto não muda custo de Actions (cobrança é por minuto consumido). |
| Investigação "por que a suíte dobrou" (5-8min em maio → 9-10min) | ✅ `1d16f1b4` (#1160) · adendo 2026-08-03 na [[ADR-210]] | **Era volume, não regressão** — então o bump acima não mascarava nada. Medido em 56 jobs: mediana 6,33 → 7,88 → 9,81 → 9,93min (mai→ago). A suíte foi de **2192 para 3015 testes** (+37,5%, 103 arquivos novos das sprints A34-A40) com custo por teste subindo só **9,6%** (0,157 → 0,172 s). Nada a otimizar: setup do job é ~30s de ~10min, o packing dos 432 arquivos em 4 workers dá desbalanço **1,00×**, arquivo mais pesado 32s contra caminho crítico de 290s, teste mais lento 2,38s. Sharding/`pytest-split` **rejeitado** com a conta (~550 disparos/mês × ~+2min faturados ≈ **+1.100 min/mês** num orçamento a 544%), coerente com §Custo da camada 4. Fecha a §Ganhos vencida (afirmava `≈5min`, de 2026-05-14) |
| Label cosmético fora do caminho de merge | ✅ `76b32d3a` (#1161) · regra na emenda 2026-08-03 da [[ADR-320]] | `Apply size label` era action **Docker** no mesmo job que `Validate PR title`, que é required check: i/o timeout do Docker Hub em `alpine:3.15` bloqueou merge do repo inteiro. **`continue-on-error` não resolveria** — o runner builda a imagem num passo *sintetizado antes* dos passos declarados, que por isso não carrega o atributo; medido no job 91695493843: `Build …→ failure` no step 2 e `Validate PR title → skipped` no step 4. Fix real = tirar Docker do caminho (script `gh` inline). O pin por SHA cobre o código da action, não a base da imagem dela, e o hook `docker-sha-pin` não alcança Dockerfile de terceiro. |

**A erosão volta.** O teto cresce ~+1,2min/mês no ritmo atual, e teto fixo em
número absoluto sempre erode — o que mudou é que a medição agora é embutida
(`--durations=25` no passo, custo zero em minutos) e o gatilho é declarado:
**mediana > 12min** (60% do teto de 20) ⇒ ler a tabela do log antes de mexer no
número, e só bumpar se o crescimento for de volume. Sem isso, o próximo agente
repete a arqueologia que este ciclo custou (rodar a suíte local com
`--junit-xml` + baixar log de um run de maio).

**Dois resíduos desta investigação, nenhum com lane** (não são report-trust e
não competem por capacidade, mas ficariam órfãos):

| Resíduo | Estado | Por quê importa |
|---|---|---|
| Revisão `sre-devops` da mudança de política de CI **não foi feita** | ⏳ **owner-gated** — ver [[OWNER-GATED]] | O CLAUDE.md §Protocolo de delegação lista "Política CI/CD … FinOps" como **gatilho obrigatório** de `sre-devops`. O #1160 mudou política de um job que é required check e escreveu numa ADR a regra de dimensionamento (~2× da mediana), **e mergeou sem essa revisão** — a sessão rodou sob instrução de não invocar subagente sem pedido explícito. Risco baixo no diff (comentário + flag de reporte + adendo de doc; a mudança de teto foi do #1157), mas a **regra de política** entrou sem o especialista. **Mesmo caso no #1161** (2ª sessão, mesma instrução): trocou action de terceiro por script `gh` no job required e escreveu regra de política na emenda da [[ADR-320]] ("Docker action vedada em job required"), também sem `sre-devops`. Decisão do dono: passar retroativo nos dois ou aceitar |
| Mudança em `ci.yml` custa ~5 runs de CI para mergear | 📌 registrado, sem ação | `ci.yml` está em **todos** os path filters (por sanity contra regressão de filtro), então qualquer diff nele dispara a suíte completa; e o ruleset `main-protection` tem `strict_required_status_checks_policy: true`, então cada commit que entra em `main` durante a janela força re-run. Com main recebendo 6 commits em ~1h20 (multi-sessão), o #1160 pagou **5 ciclos completos** para um diff de 24 linhas + doc. Num orçamento a 544%, a lição operacional é **agrupar mudanças de `ci.yml`** num PR só, em janela de main parada — não shipar uma por vez |

> ⚠️ **Generalização medida em 2026-08-08: não é só `ci.yml`.** A linha acima atribui os ~5
> ciclos ao fato de `ci.yml` estar em todos os path filters. Mas a causa raiz é o
> `strict_required_status_checks_policy` contra a **cadência de merge da main**, e ela atinge
> **qualquer PR cujo CI seja mais lento que essa cadência** — sem `ci.yml` no diff. Medido no
> [#1288](https://github.com/davidrobert/mathoms/pull/1288) (E3/E4 + testes, nada de CI):
> `backend-tests` leva **~11min** e a main recebeu merge a cada **~10-15min** (10 commits em
> 2h), então o PR terminou `BEHIND` **3 vezes seguidas** com todos os checks verdes,
> rebase-e-repete sem convergir. Os PRs que ganham a corrida na mesma janela são os
> **docs-only**, que pulam o job de backend.
>
> **A armadilha operacional é o auto-merge parecer resolvido.** `gh pr merge --auto` armado +
> tudo verde lê como "vai mergear sozinho", e o PR fica parado indefinidamente esperando um
> rebase que ninguém faz — o mesmo sintoma que esta sprint já viu em PR "aguardando CI".
> **Como aplicar:** para PR que toca backend em janela de sprint movimentada, ou (a) mergear
> em janela de main parada, ou (b) alguém rebaseia até convergir, ou (c) merge queue — que é
> o único conserto estrutural. Rebasear em laço custa ~11min de CI **pago** por tentativa,
> com odds inalteradas; a partir da 2ª falha, escalar em vez de repetir.

## Achado novo do painel (fora dos 33)

> **Terceiro botão que mente, mesma classe, achado no co-design da [[A40.l30]]
> (2026-08-03):** `narrative_hints_global` em `config/prompts/parecer_planejador.yaml`
> é **config morta** — `ManifestData` não tem o campo e `load_manifest` não lê a
> chave; as regras chegam ao modelo pela persona e pelo `_CATALOG_INSTRUCTION`.
> Não é defeito vivo, é botão sem fio. Entra nesta mesma lane, mesmo owner.

`max_total_input_tokens` e `max_tool_iterations` no manifest do parecer são **teto
declarativo**: parseados e nunca enforçados. Qualquer raciocínio de custo/latência
apoiado neles é infundado — o único teto vivo é `max_exec_context_bytes`. Manter um
teto que não trava é pior que não ter, porque induz revisão a assumir proteção
inexistente. Severidade Médio/P2, owner `prompt-engineer` → entra na [[A40.l8]].

## Achados da construção do harness de captura (2026-07-30)

Ao instrumentar a verificação renderizada, o caminho de produção de PDF revelou
**dois defeitos independentes que quebravam o download do cliente** — ambos com
prova vermelho/verde contra o frontend real, ambos **corrigidos** na mesma passada:

1. **`token_version` não propagava** em `download_pdf.py`. `create_access_token`
   nasce na versão 0; todo usuário que já invalidou sessões está em ≥ 1, então o
   token efêmero era rejeitado com 401 e o endpoint devolvia **HTTP 500**.
2. **Header `Authorization` não passa pelo gate client-side.** O gate de
   `/reports/[id]` lê o token de `localStorage`; `render_pdf` só injetava o header,
   então a página redirecionava para `/login` e o `wait_for_function` estourava —
   **mesmo com token válido**. Confirmado isoladamente: com token válido e sem
   semear `localStorage`, `ready=false`; semeando, `ready=true`.

Regressão coberta por `backend/tests/test_pdf_auth_contract.py`, incluindo um teste
de contrato que falha se alguém renomear a chave de auth no cliente.

**Efeito colateral útil:** o harness confirmou o **RV3-04 por medição** — 31 âncoras
de navegação, 1 sem alvo (`found: false, height: 0`). O achado deixou de ser
inferência de código. A [[A40.l7]] mantém o gate; a ferramenta só observa.

## Débito de método herdado da r3

A própria rodada que originou este sprint registrou 5 furos de processo. Três já
viraram regra na skill `report-review`; dois viram trabalho aqui:

- **Conservação por grupo não detecta duplicação entre grupos** → [[A40.l1]].
- **Ninguém renderizou tela nem PDF** → toda lane de `clareza-ux` desta sprint
  exige **uma passada de verificação renderizada** (navegador ou `pdftotext`) no
  critério de aceite. Sem isso, a lane fecha sobre inferência de código.

## KR-D: de "não fecha" a fecha (2026-08-24)

Painel encerrado, movido de [`_README`](_README.md) no closeout da [[A40.l6]].
Os dois blockquotes ficam **na ordem original e sem reescrita**: o primeiro era
medição correta no instante em que foi feita, e o valor do registro está
justamente em mostrar que ela estava certa **pelo motivo errado**.

> ⚠️ **A KR-D não fecha — o gate existe como função e não tem chamador (medido 2026-08-24).**
> O #1569 entregou o **redator**: `redact_cartorial` está wired em
> `real_estate_metrics_payload.py` e `endividamento_analyzer.py`, e o card parou de
> interpolar `descricao` (`RealEstateYieldCard.tsx:205` usa `imovelDisplayLabel`). Mas
> o **scanner** — `scan_view_model_pii`, o termo que a KR mede — tem **zero** chamadas
> fora do próprio unit test: nada em `.github/`, nada em `.pre-commit-config.yaml`,
> nada em `dev/`, nada em stage. A KR-D exige *"bloqueio no CI"*; scanner sem
> chamador não bloqueia nada. Mesma família da KR-A: a função existir **e** o gate
> rodar são os dois termos do "e". Residual com dono na [[A40.l6]] §Nota datada.

> ✅ **Resolvido 2026-08-24 — a KR-D fecha (#1673).** O blockquote acima **não se
> reescreve**: era medição correta no instante em que foi feita. O que mudou é o
> mundo. A medição também estava **certa pelo motivo errado** — o defeito não era
> "scanner sem chamador", era **scanner varrendo o nome do campo**:
> `endereco_canonical` (= `canonicalize(descricao)`, cascata que devolve
> `mat:<matrícula>`/`iptu:<inscrição>`) era o que o card renderizava, e dar um
> chamador ao gate antigo teria fechado a KR **com a matrícula na tela**.
>
> Estado medido hoje, pelo instrumento que a própria KR nomeia (*"fixture
> sintética com identificador de terceiro + matrícula + endereço ⇒ bloqueio no
> CI"*): `tests/unit/pipeline/test_view_model_pii.py` e
> `tests/test_real_estate_metrics_payload.py` rodam em `Pipeline tests (tests/)`,
> que está em `all-green.needs` — fixture cartorial ⇒ EXIT≠0 ⇒ merge bloqueado.
> Três gates independentes cobrem a classe (payload produzido, lint público com os
> 2 waivers queimados, spec renderizada em DOM + PDF), cada um com prova por
> mutação. Detalhe em [[A40.l6]] §Fecho · [[ADR-337]] §Emenda 2026-08-24.

## Pendências de decisão — itens 11-13 (2026-08-03; item 13 em 2026-08-12)

**11. Os follow-ups sem destino viram lane nesta sprint, ou disposição explícita
de não-fazer?** — ✅ **RESOLVIDA 2026-08-05.** A ancorabilidade do exec context já
tinha ido para [[A40.l30]]+[[A40.l31]] em 2026-08-03. Os **5** que restavam foram
triados pela mesma regra que a A42 já formalizou em `main` (§Critério de admissão,
`ecfa760f` #1193 · `3dbc558b` #1194): **destino é quem já possui o arquivo ou a
superfície** — nenhum nasce lane nova na A40. Resultado, item a item:

| Item | Destino | Por quê |
|---|---|---|
| DAS ausente no `s8`/`despesas_impostos` | **item adotado — [[A40.l12]]** | mesmo arquivo/risco de KPI distorcido por balde incompleto |
| `perfil_familia.right` publica `n_imoveis` desatualizado | **item adotado — [[A40.l6]]** | contradição cross-seção, mesma classe de "zero-como-valor" que a l6 já cobre |
| PD-20 — meta de TRS não configurável | **item adotado — [[A40.l12]]** | mesmo arquivo (`e5_analyzer_adapter.py`) do item 1, risco diferente — **não** agrupado na mesma tarefa (arquivo compartilhado ≠ risco compartilhado) |
| Sufixo de changelog (ADR-148) não renderiza | **fora da A40** — [[PLAN-snapshot-changelog-v3]] §Residual W3 | é resíduo daquele plano (`W3-T05` entregou o default em forma reduzida); o ponteiro "A40.l5" nunca aterrissou no §Escopo da l5 — atribuição sem mecanismo, mesma classe que a emenda da [[ADR-111]] já nomeou |
| Rótulo da [[ADR-306]] — **3** blocos sem rótulo válido (não 2, não 4 — ver correção no §Inventário acima) | **item adotado — [[A40.l11]]** | l11 já é dona de "rótulo de escopo"; deps (l3, l4) já `shipped` |

Nenhum dos 5 justificava lane nova: a cláusula de exceção da A42 (P0 que alcança o
usuário, sem dono vivo, com espera medida em semanas) não se aplica a nenhum —
todos são P1/P2/P3 de superfície. Só a "Base da cascata" (item 4 da Pendência 6,
que este item 11 absorve) não tinha dono vivo **e** não tinha materialidade
medida — saiu da A40 por disposição explícita, registrada em [[REPORT-REVIEWS-active]]
como residual pós-r3: mede o delta entre `receita_pj_anual` e
`receita_bruta_total_anual` no corpus dogfood antes de decidir lane (delta
material) ou `aceito-wontfix` (delta imaterial). "Sem dono vivo + sem
materialidade medida" é o único caso desta lista que qualifica como "esquecimento
evitado por disposição", não por adoção.

**12. Autorreferência em `depends_on`/`parallel_with` vira gate, ou fica no olho
do revisor?** — ✅ **RESOLVIDA 2026-08-05: vira gate, absorvida pela [[A40.l23]]
§Escopo adotado item 1 e entregue antecipadamente no PR #1216** — registro
canônico no arquivo da lane. A [[A40.l27]] entrou em `main` declarando
`depends_on: [[A40.l27]]` e `parallel_with: [[A40.l27]]` — find-replace de
renumeração trocou os wikilinks pelo próprio id. **Duas correções factuais ao
diagnóstico original:** (a) o mecanismo não era "`check_doc_links` pergunta se o
alvo resolve" — aquele gate **nunca vê o frontmatter** (o strip apaga antes de
extrair wikilinks), então aresta para id **inexistente** também passa nos cinco
gates — buraco maior, agora nomeado como item 1b da l23, ainda aberto; (b) o
custo real foi ~34 linhas no estilo do módulo, não ~10 (segue longe do P2 de
500). O gate cobre também `supersedes`/`superseded_by` e alias/anchor; prova de
mutação em `tests/test_doc_graph_gates.py`. Id duplicado (rabo da §Pendência 10)
**já tinha gate** em `check_doc_links` — pinado por teste no mesmo PR; a
renumeração 2× da l27 não foi falha de gate (ele disparou no rebase), é problema
de **alocação**, que o `former_ids` (l23 item 3) audita.

**13. Os índices `docs/_MOC/_generated/` commitados são ponto de contenção
global, e IDs sequenciais colidem sob paralelismo — muda a política, ou
absorve-se o custo?** — aberta 2026-08-12, evidência das execuções da
[[A40.l45]] e desta própria curadoria: **8 renumerações de ID** (ADR
376→377→378→379→381; lane l38→l43→l45; e as lanes de follow-up nasceram
l50→l53) e **8 rebases**, porque todo PR que cria lane/ADR reescreve os mesmos
4 arquivos gerados, e `main` recebe commits mais rápido do que um ciclo de CI
completa. O rabo da §Pendência 12 já nomeou a alocação como problema; isto é a
medição da escala. Opções, sem decisão embutida: (a) gerar os índices **no CI**
em vez de commitá-los (muda [[ADR-182]]); (b) merge driver `ours` +
regeneração obrigatória no pre-commit (mantém o arquivo, mata o conflito);
(c) manter como está e padronizar o custo — alocar ID **depois do último
rebase, imediatamente antes do push**, lendo o teto de `origin/main` **e dos
PRs abertos** (`git ls-tree` + `gh pr list`), nunca do `ls` local. A (c) já é
prática registrada em memória de agente; elevá-la a texto do CLAUDE.md §ADRs
inverte o conselho atual de "abrir PR cedo para reservar o ID", que sob
paralelismo é contraproducente. **Owner-gated**: qualquer opção muda política
de repo.

> **Marcador de fato, 2026-08-24 — a opção (b) não faz o que o texto acima
> supõe.** O texto de 2026-08-12 fica: é o registro da medição da escala. O que
> mudou é conhecimento, não decisão. **Merge driver é client-side**: o
> `update-branch` do trem (`PUT /pulls/{n}/update-branch`) e o squash rodam no
> servidor do GitHub, que não lê `.gitattributes` do repo para driver
> customizado. Medido: `.gitattributes` **não existe** aqui, e o driver `ours`
> exigiria `git config merge.ours.driver true` **por clone** — que o CLAUDE.md
> §Git proíbe ao agente configurar. Logo (b) cobriria só o rebase local de quem
> rodou o config, não o caminho onde a fila trava. Não medi qual fração dos
> conflitos vem de cada caminho.
>
> Metade do custo que esta pendência mede **já foi paga** por outra via: o
> #1674 tirou o contador agregado dos índices, e a colisão que restava nos
> gerados era 3 de 4 arquivos por contador. Sobra o `DOC_STATS.md`, que é 100%
> agregado — não é reformável, só removível. A decisão entre (a), (b), (c) ou
> "fica como está" segue **owner-gated**, agora com o custo de (b) conhecido.

## ⚠️ Pendência de filiação — [[A40.l110]] e [[A40.l111]] (encerrada 2026-09-01) — [[A40.l110]] e [[A40.l111]] (levantada 2026-08-31)

Achado da re-triagem conduzida pelo `product-manager`: as duas **mutam artefato/E5** —
a l110 grava a data corrente no artefato (quebra idempotência do balde patrimonial) e a
l111 tira do somatório um valor que vira `null` — e **nenhuma das duas está nomeada na
cláusula de reinício abaixo**. A lista atual é l2 · l94 · l95 · l96 · l98 · l100 · l101 +
[[A42.l15]] · [[A42.l17]].

**É o mesmo modo de falha que já custou duas emendas tardias** (a l96 em 2026-08-29, a l98
em 2026-08-30): a filiação foi decidida **depois** de a lane existir, e a cláusula teve de
ser reescrita. **Decida a filiação das duas ANTES de iniciar o contador** — se elas
pertencem à cláusula e o contador já tiver começado, um re-run inteiro é desperdiçado.

Não decidi aqui: filiação é do dono, e o critério (*"muta E3/E5 a montante de todo run"*)
exige julgar o alcance de cada uma, não só constatar que tocam E5.

**Nota datada 2026-09-01 (closeout da [[A40.l110]]) — o prazo NÃO venceu, e apareceu um
split-brain.** Três fatos medidos, nenhuma decisão tomada aqui:

1. **A janela continua aberta.** O painel condiciona a decisão ao *início do contador*,
   não ao merge das lanes. O contador está em **0/2** desde a `U4` (2026-08-30), então
   as duas terem chegado a `main` com a filiação em aberto não custou nada. Eu havia
   lido "expirou" no primeiro passe do closeout; o `product-manager` corrigiu, e a
   correção procede.
2. **A [[A40.l111]] se auto-filiou, e a lista não a acompanhou.** A linha dela na tabela
   de lanes afirma *"**entra na cláusula de reinício do contador** (muta E5)"*, mas a
   lista canônica acima nomeia `l2 · l94 · l95 · l96 · l98 · l102 · [[A42.l15]]` — **sem
   a l111**. São duas fontes de verdade sobre a condição que dispara o gate de saída da
   sprint. Custa uma linha e a l111 é terminal (#1917), logo decidir não atrasa nada.
3. **Existe precedente para a classe da [[A40.l110]] ficar FORA.** A [[A42.l18]] e a
   [[A42.l19]] saíram da cláusula acima por serem *"de instrumento de medição e de guard
   de escrita — não deslocam valor publicado"*. A l110 matou 2 campos com **zero leitor
   de produção, medido**, e nenhum número do E5 se move. A assimetria importa: **FORA
   custa nada; DENTRO trava o início do contador** enquanto o PR-B não fechar.

**✅ Resolvida em 2026-09-01 — a filiação foi decidida pelo dono.** A [[A40.l111]]
entra na cláusula, a [[A40.l110]] fica fora, e o split-brain do item 2 se fecha: a
lista canônica acima passa a nomear a l111, como a linha dela na tabela já dizia. O
critério foi aplicado por **medição de snapshot**, não por julgamento de alcance — ver
a §Extensão 2026-09-01 acima para a tabela e a ressalva do golden.

A decisão saiu **antes** de o contador iniciar (0/2), que era exatamente o que esta
pendência pedia. Custo zero nos dois lados: as duas lanes estão terminais ou a um
merge de estar.
