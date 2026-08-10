---
id: A40.l25
type: lane
title: "Honestidade do cone de IF: precisão de exibição e sigma apresentado como premissa auditada"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l25-honestidade-do-cone-if
adrs:
  - "[[ADR-361]]"
  - "[[ADR-360]]"
  - "[[ADR-219]]"
  - "[[ADR-237]]"
  - "[[ADR-373]]"
depends_on: []
parallel_with:
  - "[[A40.l11]]"
  - "[[A40.l26]]"
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# A40.l25 — `honestidade-do-cone-if`

> **Residual nomeado de duas ADRs, não achado novo.** O que sobra aqui é o que a
> [[ADR-360]] §Deferimento item 1 e a [[ADR-361]] (#1162) §Deferimento item 5
> deixaram explicitamente aberto depois de fecharem determinismo (#1156),
> sentinela de não-convergência (#1158) e censura de percentil (#1162). Sem lane,
> o residual vive só em §Deferimento de ADR — invisível ao `SPRINT_CURRENT`,
> portanto não pescável.
>
> Entra na A40 por casar com a **KR-E** (honestidade da recomendação): as duas
> faces são números que afirmam precisão ou procedência que não têm.

## ✅ Parcial entregue em 2026-08-08 — PR #1338 (`6b1076e7`)

### Itens 2 e 3, sem mover número publicado

Critério de corte usado: **entrou o que corrige procedência; ficou o que muda
número exibido.** Os itens que mexem no valor impresso disparam bump de
`mc_version` + a nota de recalibração, cuja especificação está *duas mudanças
atrás* (o ⚠️ do §Critério de aceite) e depende de `product-designer`.
Entregá-los sem isso publicaria número novo sem o aviso que a [[ADR-360]]
§Nota one-shot torna obrigatório. Lane segue **`in_progress`**.

**Item 2 — cone fora do catálogo de citação, por decisão.** Medido antes:
`build_citation_catalog` produz **0 âncoras** para `caminho_p10/p50/p90` — o
predicado `_is_money_leaf` não casa lista de pares. Era acidente. Agora é
`_NAO_CITAVEL_ESTIMATIVA`, com teste que exercita **o caminho de exclusão**
(não só o resultado), para que tornar a folha citável seja escolha explícita e
não efeito colateral de mexer no predicado.

**Item 3 — `sigma_usado` deixa de insinuar auditoria.** O payload publica
`sigma_procedencia` (`global` | `workspace_override` | `fallback_codigo`), no
padrão `fonte_origem` da [[ADR-219]], **declarado no schema E5** ao lado de
`sigma_usado`. Hoje todo run emite `fallback_codigo`, que é a verdade: o
adapter (`e5_analyzer_adapter.py:603`) não passa `sigma_anual`.

`_SIGMA_POR_PERFIL` **foi deletado** — nunca teve consumidor (confirmado por
varredura, e independentemente por RV4-29 e pela [[ADR-360]] §264), e dead code
que parece configuração sugere parametrização por perfil que não existe.

**Nenhum número publicado mudou.** O snapshot do view-model foi regravado com
diff de **exatamente 1 linha** (o campo novo) — conferido linha a linha antes
de commitar, não regravado às cegas.

**Não entrou:** item 1 inteiro (probabilidade em faixa de 5 pp nas três
superfícies + paridade Py↔TS), a leitura de `sigma_anual` a partir de
`premissas_economicas` — que muda a **largura** do cone —, e a verificação
renderizada da S7. Os três compartilham o mesmo bloqueio: mudam número exibido
e por isso exigem a nota de recalibração re-especificada.

## ✅ Parcial entregue em 2026-08-10 — PR #1356

### A nota de recalibração, que era o bloqueio de TODOS os itens restantes

Critério de corte da parcial anterior mantido — **nenhum número publicado
muda** — mas o que entrou agora é o **pré-requisito** dos que mudam. Todo item
aberto desta lane esbarrava na mesma porta: número novo na tela exige a nota, e
a nota estava especificada duas versões atrás. Com ela em `main`, o item 1
(faixa de 5 pp), o `sigma_anual` de premissa vigente e a §Carga herdada deixam
de estar individualmente bloqueados.

**A spec foi re-especificada com `product-designer`, que achou um 4º defeito
que a lane não previa.** A lane enumerava três ajustes obrigatórios; são
quatro. Registrados como [[ADR-360]] §Emenda 2026-08-10:

| Ajuste | O que mudou |
|---|---|
| (a) gatilho | Deixa de ser **lista de strings de versão** — `ausente/"2.0"` descrevia um mundo em que a corrente era `"3.0"`, e hoje é `"5.0"`. Vira **diff sobre um ledger** que cada major preenche ao nascer, com união no intervalo semiaberto `(anterior, atual]`, então workspace que **pula** versões recebe todas as facetas numa nota só |
| (b) par | Não vale para todo número: o ano tem par (mesma pergunta, mudou o estimador); a probabilidade **não** tem, porque a [[ADR-369]] D2 trocou o **alvo**. O valor antigo dela não entra no payload nem na copy |
| (c) direção | *"Sempre mais conservador"* deixa de valer. A copy declara os **dois sentidos** e nomeia o mecanismo (folga do plano), que é acionável — em vez de declarar direção, que seria falsa |
| **(d) NOVO** | **O par é confundido dado↔modelo.** Entre dois relatórios mudam o modelo **e** os dados da família, e separar exigiria rodar o modelo antigo sobre dados novos — vedado pela [[ADR-360]] D4. Consequência: a nota **nunca** diz *"seu patrimônio não mudou"* (falso em relatório mensal), e a cláusula de atribuição só aparece quando a **competência** muda |

**Onde a nota mora decide o custo.** No **view-model** (`get_report_data`),
nunca no artefato E5: a chave de cache do parecer é `sha256` sobre o payload E5
([[ADR-369]] §Alternativa A), então um campo novo lá cobraria **uma re-geração de
parecer por workspace da frota inteira** para publicar um aviso de UI. A
infraestrutura já existia — `load_snapshot_pair` devolve `(prev, curr)` com
`content_json` e `period_yyyymm`, que é exatamente o insumo.

**Falha fechada.** Sem report anterior, ou com o bloco do anterior **ilegível**,
a nota cala — não há os dois lados e afirmar "mudou" seria fabricar.
`mc_version` **ausente dentro de bloco legível** é o caso oposto: é evidência de
v1, e dispara. É a distinção que um implementador colapsa e não pode.

**Supressão por faceta e por par:** a nota nunca oferece movimento que não está
na tela (`exibir_cone: false` ⇒ ano cala; sem prazo declarado ⇒ probabilidade
cala; ano que não se moveu ⇒ faceta some). Zero facetas ⇒ nenhuma nota, o que
mata o caso `3.0 → 4.0` (rename-only) sem caso especial.

**Prova de mutação (contada):**

| Mutação | Cai |
|---|---|
| tirar `5.0` do ledger (= o bump esquecido) | **3** testes de domínio + **6** de backend |
| falha **aberta**: bloco ilegível passa a disparar como v1 | 2 testes |
| supressão por par some (publicaria "de 2049 para 2049") | 1 teste |

**Nenhum número publicado mudou, e o snapshot do view-model não moveu** — a
nota é injetada na resposta da API, não no artefato E5 que o snapshot captura.

**Não entrou** (e agora sem bloqueio de spec): item 1 (faixa de 5 pp nas três
superfícies + paridade Py↔TS), `sigma_anual` de `premissas_economicas`, a
§Carga herdada da [[A40.l26]], e a **verificação renderizada** de S7 — o
worktree não sobe Playwright (`node_modules` é symlink, o Turbopack recusa),
então o §Débito de método segue **declarado, não contornado**.

## ✅ Parcial entregue em 2026-08-10 (2ª do dia) — PR #1359

### Um defeito que a lane não conhecia, achado ao medir o item 1

Mesmo critério de corte das anteriores — **corrige procedência, não move
número publicado** (exceto os 45 desfechos abaixo, que são correção de
contradição interna, não recalibração).

**As duas superfícies discordavam sobre o mesmo número.** O parágrafo do
narrador (Python, `_fmt_probabilidade`) e a legenda do cone em S7 (TS,
`formatProbability`) publicam o **mesmo campo** — `prob_if_ate_prazo_declarado`
— e declaravam paridade em docstring **sem nunca terem sido comparados**.
Medido no domínio real do estimador (`k/50000`, [[ADR-360]]):

| | |
|---|---|
| desfechos possíveis | 50 001 |
| **divergentes** | **45** (0,09%) |
| exemplo | `k=1250` ⇒ parágrafo diz **2%**, legenda diz **3%** |

A divergência era **unilateral** e o lado errado era o Python: `round()` é
meio-para-**par**; `.toFixed(0)` do JS é meio-para-cima. Corrigido para
meio-para-cima explícito nos dois (`floor(x + 0.5)`, idêntico em IEEE-754).

> ⚠️ **Eu errei o diagnóstico na primeira passada e a mutação me corrigiu.**
> Reverti o lado TS esperando que o gate acusasse; ele **passou** — porque
> `toFixed(0)` já era meio-para-cima. Meu comentário de código chegou a
> culpar o JS, com base num script de medição meu que estava errado. Refiz a
> mutação com uma alteração **plausível** (`floor` sem o `+0.5`) e aí sim
> acusou: 24 499 divergências.

**Gate: hook de pre-commit, sem filtro de path.** `dev/check_probabilidade_parity.py`
roda as duas implementações **reais** (a TS é extraída da fonte e avaliada no
`node`, não reimplementada aqui) sobre os 50 001 desfechos. Sem filtro porque o
par vive nos dois stacks: teste em `tests/` não roda em PR que só toca
`frontend/`, e Vitest não roda em PR que só toca `pipeline/` — só o
`pre-commit --all-files` do job *Lint* cobre as duas direções (precedente: a
§Decisão do dono da [[A40.l5]]). Custo medido: **0,5 s**.

**O gate de paridade sozinho seria insuficiente** — passaria se os dois lados
derivassem juntos para a convenção errada. Por isso a **regra** (meio-para-cima
+ precedência dos guards `<1%`/`>99%`) ganhou teste **nos dois lados**.

| Mutação | Cai |
|---|---|
| narrador volta a `round()` (o defeito original) | 45 divergências |
| card vira meio-para-baixo (`floor` sem `+0.5`) | 24 499 |
| guard `<1%` some de um lado | 499 |
| a função TS é renomeada (gate viraria vácuo) | erro explícito, não silêncio |

### A chave órfã que **eu** criei no #1338

`sigma_procedencia` foi entregue na 1ª parcial para declarar procedência — e
**não tinha nenhum leitor no frontend**. Emitir chave que ninguém lê é a classe
da [[A40.l5]] (KR-A), e eu a criei enquanto fechava outra coisa. Como todo run
emite `fallback_codigo` (o adapter não passa `sigma_anual`), a legenda afirmava
*"volatilidade de 11% a.a."* como se fosse medida da carteira da família, em
**100% dos relatórios**. Agora a frase qualifica: *"(padrão do modelo, não
calibrada à sua carteira)"*.

**Decisão: não reusar o `PremissasFallbackAlert`** — que era a recomendação do
`financial-planner`. Ele é caixa **âmbar de degradação de dado** e, como o
sigma é sempre a constante hoje, dispararia em 100% dos relatórios. Constante
não-calibrada é *default declarado*, não degradação; equiparar as duas produz
fadiga de alarme e diz que o relatório está pior do que está. A microcopy da
ressalva é candidata a revisão do `product-designer` — está registrada aqui,
não silenciada.

## 📐 Co-design `financial-planner` — 2026-08-10: como o sigma vem da premissa

Destrava o item 3. **Decisão: opção A** (`σ_p = Σ wᵢ σᵢ`), pesos da
**alocação-alvo declarada**, abortando para `fallback_codigo` quando qualquer
classe de peso positivo não tiver σ vigente.

O argumento não é "A é mais precisa" — é que **A é limite superior
demonstrável** (`σ_p ≤ Σwᵢσᵢ` vale para qualquer matriz de correlação), logo é
afirmação verdadeira **sem conhecer o insumo que falta**, que é o que a
[[ADR-219]] pede de premissa auditável. A opção B (correlação zero) foi
**refutada por medição**: com os σ do seed vigente, ela devolve ~11,3% para a
carteira agressiva — o mesmo número da constante, ou seja, apaga o risco
exatamente onde ele é real.

| Alvo declarado | A (`Σwσ`) | B (`√Σw²σ²`) | hoje |
|---|---|---|---|
| padrão | **10,8%** | 6,3% | 11% |
| conservador | **1,8%** | 1,2% | 11% |
| agressivo | **17,6%** | 11,3% | 11% |

**O defeito não é o nível, é a invariância:** uma família 80% Tesouro Selic e
uma 90% ações recebem hoje o mesmo cone. O intervalo real é ~2%–18%.

Três especificações que um implementador colapsa e não pode: usar os `inputs`
crus normalizados a 100 **incluindo caixa** (reusar `_normalize_alvo` exclui
caixa e dá 11,9% em vez de 10,8%); `has_alvo: false` ⇒ `fallback_codigo`; e
classe com peso > 0 e `status: indisponivel` ⇒ **abortar**, não renormalizar —
o que **contradiz a [[ADR-219]] D4** e por isso exige emenda datada lá.

**Ganho não-óbvio:** `_lognormal_params` subtrai ½σ²_log para preservar E[r], então
σ carrega *drag de volatilidade* sobre o caminho central — a família
conservadora é hoje penalizada por ~0,5%/ano de volatilidade que não tem, o que
afasta `ano_if_cenario_central` do `prazo_anos_realista` determinístico exibido
**na mesma seção**. Corrigir σ aproxima dois números que hoje se contradizem.

**Não mover μ** (`retorno_real_esperado`) para a tabela: ele alimenta o prazo
determinístico **e** o centro do cone, e trocar a fonte de um sem o outro
dessincroniza dois números da mesma tela. μ é parâmetro do **plano**; σ é
parâmetro de **mercado**.

**Passos restantes** (a ordem é do co-design): (1) ✅ ressalva de fallback —
entregue neste PR; (2) ADR nova `Proposto` com a fórmula + emenda datada na
[[ADR-219]] D4; (3) agregação + campos de auditoria + bump `mc_version` → `"6.0"`,
que só agora é legítimo porque o modelo de fato muda.

**Não entrou:** a faixa de 5 pp. Ela **muda número exibido** e, sozinha, forçaria
um bump de `mc_version` sem mudança de modelo — o que corromperia o significado
do campo (é provenance do **modelo**, não da exibição). Vai junto com a
agregação de σ, sob `6.0`, como o ledger da [[ADR-360]] §Emenda já prevê.

## Problema

Duas faces independentes, mesmo arquivo-alvo (`if_monte_carlo.py` + superfícies
de exibição), por isso uma lane só.

### 1. Precisão de exibição acima da precisão do estimador

O cone é reprodutível desde a [[ADR-360]], mas continua sendo **estimativa**: a
dispersão amostral medida é ~1,2% na série a `n = 50 000` (era 2,4% a 10k), e o
erro-padrão da proporção a `p ≈ 0,3` é ~0,21 pp. Hoje:

- **Probabilidade sai em inteiro** (`_fmt_probabilidade` no Python,
  `formatProbability` no TS) — "31%" contra "cerca de 30%". Ninguém planeja
  diferente entre 31% e 33%; a diferença é entre prometer precisão inexistente e
  comunicar magnitude. A [[ADR-361]] manteve o inteiro **de propósito**, porque
  mudar exige paridade Python↔TS (§Deferimento item 5 dela).
- **As séries do cone não estão declaradas fora do catálogo de citação.** Hoje
  elas não são citáveis por acidente (`_is_money_leaf` não casa lista de pares),
  não por decisão. Se alguém tornar a folha citável, o parecer pode escrever
  "R$ 11.037.269,90" sobre um número com ±1,2%.

### 2. `sigma_usado: 0.11` é constante de código apresentada como premissa

`_SIGMA_POR_PERFIL` (0,07 / 0,11 / 0,15) existe em `if_monte_carlo.py` e é **dead
code**: o adapter E5 nunca passa `sigma_anual` e nunca lê `premissas_economicas`
— apesar de a [[ADR-219]] D5 ter construído a tabela versionada exatamente para
isso. O payload publica `sigma_usado` ao lado de `premissas_economicas` no mesmo
bloco de auditoria, o que insinua procedência que o número não tem.

**Ordem de magnitude:** a largura do cone — sua mensagem inteira — vem desse
`sigma`. Erro de premissa domina o erro amostral que a [[ADR-360]] reduziu de
2,4% para 1,2%. Foi a [[ADR-237]] §E que adiou a parametrização por perfil; o
follow-up nunca aterrissou.

## Escopo

1. Probabilidade em **faixa de 5 pp** ("cerca de 30%") nas três superfícies que a
   publicam — card de S7, narrador determinístico, âncora do parecer — com
   paridade Python↔TS provada por teste. Mantém os guards `<1%` / `>99%`; 0 e 1
   literais seguem exatos.
2. Declarar as séries do cone **fora do catálogo de citação** por decisão
   explícita (não por acidente de predicado), com teste que falha se voltarem.
3. `sigma_anual` passa a vir de `premissas_economicas` quando houver premissa
   vigente; sem ela, o payload **declara o fallback** em vez de publicar a
   constante como se fosse auditada. `_SIGMA_POR_PERFIL` ou ganha consumidor ou
   é deletado — dead code que parece configuração é pior que ausência.
4. **Carregado da [[A40.l26]] em 2026-08-09** — o piso de prazo a aporte zero,
   exibido **dentro da frase** que nomeia a premissa e a alavanca, e a decisão
   simétrica sobre o cone sob PMT = 0. Ver §Carga herdada abaixo.

## Carga herdada da [[A40.l26]] (2026-08-09)

A [[A40.l26]] fechou `shipped` (#1339 · [[ADR-373]]) deixando um §Deferimento
vivo. **Lane `shipped` some do [`SPRINT_CURRENT`](../../../_MOC/_generated/SPRINT_CURRENT.md)**,
então o item ficaria invisível para quem procura trabalho — o modo de falha que
já prendeu 3 follow-ups na [[A40.l18]]. Por isso a carga passa para cá, que está
`in_progress` e visível, em vez de ficar num ponteiro para lane fechada.

O que entra:

- **O piso a aporte zero.** No dogfood, `n = ln(FV/PV)/ln(1+r)` converge em
  **~35 anos** e o produto está calado sobre ele. A [[ADR-373]] D2 decidiu **não**
  publicá-lo sob `prazo_anos_realista` (seria escolher a premissa "você não
  aporta" pela família, e corromperia o par declarado/realista da [[ADR-369]] D2)
  — mas ele deve aparecer **dentro do motivo**, com a premissa explícita e a
  alavanca nomeada na mesma frase. Chaves `prazo_anos_sem_aporte_novo` /
  `ano_if_sem_aporte_novo` existem só para o narrador ler em vez de recalcular,
  e **nunca** mapeiam para `ano_if` nem para o hero KPI. **Nunca a chave sem a
  frase** — `$.goals` vai cru para o LLM do parecer, e chave solta vira "o prazo
  até a IF é de 35 anos".
- **A decisão simétrica sobre o cone.** O Monte Carlo **já publica** sob PMT = 0:
  `prob_if_ate_horizonte_simulado` = 0,58 no dogfood, e só o gate `if_pct < 15%`
  mantém o ano fora da tela. Fechar o lado determinístico e calar sobre este
  deixa o produto inconsistente na direção oposta.
- **Grade de sensibilidade** da premissa de retorno: 5% / 6% / 7% → 41,8 / 35,0
  / 30,2 anos no perfil do dogfood. Publicar a fragilidade como fato, não como
  descoberta futura.
- **Verificação renderizada** de S7 + Apêndice C, pelo débito de método da r3.

**Por que aqui e não numa lane nova:** é o mesmo bloqueio da l25. Os dois mudam
número exibido, e número novo na tela exige a §Nota one-shot de recalibração da
[[ADR-360]] — que cobre cone e prazo de uma vez. Duas lanes publicariam metade
do aviso cada.

## Critério de aceite

- Nenhuma superfície imprime probabilidade do MC com precisão melhor que 5 pp;
  teste de paridade Python↔TS sobre a mesma entrada.
- `build_citation_catalog` não produz âncora para `caminho_p10/p50/p90`, com
  teste que falha se a folha virar citável.
- `sigma_usado` no payload vem acompanhado de procedência (`global` /
  `workspace_override` / `fallback_codigo`), no padrão de `fonte_origem` que a
  [[ADR-219]] já usa em `premissas_economicas.classes[]`.
- `_SIGMA_POR_PERFIL` tem consumidor **ou** não existe mais; gate de dead code
  não regride.
- Verificação renderizada (navegador ou `pdftotext`) da S7 — exigência do
  §Débito de método desta sprint: a lane não fecha sobre inferência de código.
- Se mudar número exibido: `mc_version` bumpa e a mudança entra na nota de
  recalibração — especificada e **autorizada** em [[ADR-360]] §Nota one-shot de
  recalibração (2026-08-05; fecha `OWNER-GATED-active.md` #45). Critério: nota
  in-section em S7 (não rodapé), gatilho por `mc_version` do report anterior do
  workspace (ausente/`"2.0"` ⇒ mostra; sem report anterior ⇒ nunca mostra), par
  ano-antigo→ano-novo explícito, direção sempre "mais conservador" declarada,
  causa em linguagem de cliente ("recalibração do modelo", nunca "sua carteira
  mudou").
  > ⚠️ **A especificação acima está DUAS mudanças atrás — leia antes de escrever
  > a nota.** A [[ADR-369]] (#1268/#1269, 2026-08-07) deslocou o bloco de IF mais
  > duas vezes, e a segunda é de **semântica**, não de calibração. Três ajustes
  > obrigatórios: (a) o gatilho tem de disparar também para `mc_version` `"3.0"`
  > e `"4.0"`, não só ausente/`"2.0"`; (b) o par ano-antigo→ano-novo **não
  > basta** — o número da probabilidade mudou por motivo diferente do ano; (c) a
  > direção **"sempre mais conservador" deixa de valer**: a probabilidade agora
  > mede o prazo declarado e pode **subir ou descer** conforme a folga do plano,
  > então afirmar monotonia seria falso. Registrado também no §Entregas fora de
  > lane do [[A40]]; esta cópia existe porque a implementação é desta lane, e
  > registro no lugar onde a dona não lê é registro invisível.
  >
  > ✅ **Fechado em 2026-08-10 (#1356)** — e eram **quatro** ajustes, não três:
  > o `product-designer` mediu que o par ano-antigo→ano-novo é **confundido
  > dado↔modelo**. Especificação vigente: [[ADR-360]] §Emenda 2026-08-10. Esta
  > lista de três permanece como registro datado do que se sabia; **não é mais
  > a spec**.

## Fora de escopo

- Determinismo do cone — fechado pela [[ADR-360]] (#1156).
- Percentil censurado / truncamento de `int(np.percentile)` — fechados pela
  [[ADR-361]] (#1162).
- Sentinela 999 em `idade_meta_usada` — fechada em #1158.
- Aposentar de vez o ano do MC como manchete: a [[ADR-361]] já resolveu o caso
  em que o ano **não existe** (censura declarada). Reduzir o ano publicado a
  faixa quando ele existe é decisão editorial de S7 e depende de `product-designer`
  — não abre aqui sem brief.
