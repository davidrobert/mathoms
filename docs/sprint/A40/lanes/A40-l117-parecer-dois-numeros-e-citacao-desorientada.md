---
id: A40.l117
type: lane
title: "O parecer publica dois números para a mesma coisa, cita a seção errada em 4 de 11 riscos, e o prompt se contradiz sobre ter ferramentas"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l117-parecer-dois-numeros-e-citacao-desorientada
owner: prompt-engineer
depends_on: []
adrs: ["[[ADR-199]]", "[[ADR-203]]", "[[ADR-341]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/backend]
---

# A40.l117 — `parecer-dois-numeros-e-citacao-desorientada`

> **Origem:** `RR9-08` + `RR9-11` + `RR9-14` da rodada unificada **U5**
> ([[PIPELINE-REVIEWS-active]] §r13). Três sintomas com a mesma raiz: **prosa autoral do
> modelo não passa por invariante**.

## Os três sintomas

1. **Dois valores para "renda fixa na carteira" na mesma seção**, com **4,15 pp** de
   spread: um autoral do modelo, o outro carimbado pela máquina. Nada reconcilia porque
   `parecer_prose_money.py:16` declara que **percentuais ficam fora** do invariante —
   medido: **27 percentuais em 47 campos de prosa, 0 sob invariante**.
2. **4 de 11 riscos citam a seção errada:** dois riscos de **proteção** citam a seção de
   imóveis (existe seção de seguros dedicada), o de **sucessão** cita a seção de renda do
   IRPF (existe seção de riscos e sucessão), e o de rentabilidade cita a de carga
   tributária. **REFUTADO** na mesma medição: a alegação de "âncora morta" — as **27
   citações resolvem, 27 de 27**. O link funciona; o destino é que está errado.
3. **O prompt se contradiz sobre `tools`:** a linha 441 do YAML convida o modelo a chamar
   `get_e5_section`; a **179 do mesmo arquivo** afirma que ele não tem ferramentas. O
   convite morto é **injetado no corpo sob budget** e é a causa proximal dos 3
   `campos_faltantes`.

## Por que os três juntos

O eixo é o mesmo: **o que o modelo escreve não é confrontado com o que a máquina sabe**.
Percentual fora do invariante, seção escolhida por prosa em vez de mapa declarado, e
ferramenta prometida sem existir são três formas de a autoria do modelo passar sem gate.

## Medição que fecha o mecanismo de (2)

Ler como o campo de seção do risco é atribuído no manifest. Se vem do LLM em vez de um mapa
declarado, é a classe *"nome vindo da prosa, não do produtor"*.

## Critério de aceite

1. Percentual em prosa entra no invariante monetário (ou a exclusão é decidida por ADR com
   o custo escrito — hoje ela está num comentário).
2. `section_id` do risco vem de **mapa declarado** por tema, não da prosa.
3. O convite a `tools` sai do prompt **ou** as ferramentas passam a existir; as duas linhas
   do YAML não podem discordar.
4. Gate de coerência: dois valores para a mesma grandeza na mesma seção reprova.

## Medição de abertura (2026-09-01) — o enunciado procede em 3 de 3, e erra em 2 de 4 critérios

Payload real do run `40d1af2a` (o mesmo da **U5**), decifrado do DB de dogfood. Nenhum
valor monetário reproduzido; só percentuais, nomes de campo e contagens.

### O que CONFIRMA

| Afirmação do enunciado | Medido | Veredito |
|---|---|---|
| dois valores para renda fixa na S1, **4,15 pp** | prosa **90,25%** (3×: `descricao`, `evidencia`, `impacto_qualitativo`) vs carimbo `alocacao_renda_fixa.valor_atual` = **94,4%** | ✅ exato |
| **27 percentuais** de prosa, **0** sob invariante | 27 tokens em 19 campos; `parecer_prose_money.py:16` é ancorado em `R$` por construção | ✅ |
| as **27 citações resolvem, 27 de 27** (refutação da "âncora morta") | reconfirmado | ✅ |
| o modelo **não tem** `tools` | `LLMService.call` (`pipeline/llm/litellm_client.py:133`) não tem parâmetro `tools`; as 19 entradas de `_meta.tool_trace` são **todas** `get_e5_jsonpath` pós-LLM | ✅ |

### O que o enunciado erra

1. **`campos_faltantes` são 8, não 3.** O **3** é o subconjunto atribuível: rodei a eviction
   real (cortou `plano_acao_atual`, `investimentos`, `independencia_financeira`) e
   **exatamente 3 dos 8** caem em seção evictada. Os outros 5 vêm de seções **mantidas** —
   4 deles são `$.endividamento.dividas[N].taxa_juros_aa`, o mesmo conceito 4×.
2. **A linha 441 é o convite MENOS importante — e é o único que NÃO está sob budget.**
   Hints são anexados **depois** do cap (`parecer_distiller.py:484-492`). O convite que
   está mesmo no corpo orçado é outro: `_eviction_marker` (`parecer_distiller.py:273`)
   injeta `" Recupere os dados via get_e5_section: {keys}."`. São **5** superfícies
   model-facing prometendo ferramenta, e as duas maiores o enunciado não nomeia: a regra
   **§3 "Tool use (drill-down)"** inteira do system prompt
   (`pipeline/llm/prompts/parecer_planejador.py:49-63`) e o heading literal
   **`## Tools disponíveis`** do user prompt (`:228-232`).
3. **Critério 1 é inerte como escrito.** "Percentual entra no invariante monetário" não
   pega o spread: `number_in_prose` é **telemetria**, não invariante ([[ADR-304]] §Emenda
   2026-08-03), e `MoneyToken.cents` é resíduo **sem consumidor** — não existe comparador
   prosa ↔ âncora em lugar nenhum do repo. Entrar nesse conjunto só incrementaria um
   contador de presença. O que pega o defeito é o critério 4.
4. **Critério 2 está REFUTADO.** `tema_canonico → section_id` **não é função** no output
   real: `Custo tributário` → {`S_IRPF_OTIMIZACAO`, `S_IRPF_RENDA`} e `Diagnóstico de
   dados` → {`S2`, `S_IRPF_RENDA`}, e nos dois casos **os dois destinos são legítimos**.
   Mapa por tema forçaria um e rotularia errado o outro.

### O mecanismo real do sintoma 2 — vocabulário sem produtor

> ⚠️ **Esta subseção está PARCIALMENTE REFUTADA pelo painel — leia o §Arbitragem antes de
> citá-la.** O enquadramento "drift de contrato" pressupõe *proveniência*, e a semântica
> decidida é *navegação*: sob ela, `S4` num risco de imóvel é **certo**, e os números
> abaixo não são contagem de erro. O conjunto de defeito são os **4 riscos misroteados**,
> não os 13 itens. Os fatos medidos seguem válidos; a leitura deles é que mudou.

Não é "nome vindo da prosa" genérico. Medido:

- O manifest projeta {`S1`,`S2`,`S3`,`S7`,`S8`,`S9`,`S10`,`plano_de_acao`}.
- O enum `SectionId` (`pipeline/llm/schemas/parecer_planejador.py:49`, cópia à mão,
  duplicada em `backend/app/schemas/dto/planner_review/response.py:29`) oferece **4 a
  mais**: `S4`, `S_IRPF_RENDA`, `S_IRPF_OTIMIZACAO`, `S_parecer` — seções que o exec
  context **nunca popula**.
- Uso real: **13 de 33 itens** citam uma dessas 4, incluindo **5 de 11 riscos**. (Sob
  navegação isto **não é** contagem de erro — ver o aviso acima.)
- `dev/check_planner_manifest_coverage.py` **já avisa** exatamente sobre
  `S4`/`S_IRPF_RENDA`/`S_IRPF_OTIMIZACAO`/`S_PROTECAO` — é WARNING, sai `exit 0`, e não
  está conectado ao enum.
- `S9` ("Riscos e Sucessão — Lacunas de Proteção") foi **mantida** no contexto e recebeu
  **0 de 11** riscos; os 2 de proteção foram para `S4`.
- `S_PROTECAO` está fora do vocabulário **por decisão** (`pipeline/domain/types/suggestion.py:74`):
  sem renderer de callout, ampliar o enum criaria *emissor sem leitor* — a classe que a
  [[A40.l88]] fechou.
- No mesmo arquivo do enum, o irmão `MetricaKey` é **derivado** do catálogo, com o
  comentário "enum copiado envelhece calado". O `SectionId` é a exceção não declarada.

**Tensão que ninguém declarou:** `section_id` significa *proveniência* (de onde veio o
dado) ou *navegação* (o que o leitor deve abrir)? O teste
`TestSectionIdVocabulary::test_vocabulario_do_dominio_nao_deriva_do_layout` ancora o
vocabulário no **layout** (navegação); o dado disponível ancora no **manifest**
(proveniência). Hoje o modelo escolhe livre e o output mistura as duas leituras. Derivar
da âncora é viável (**25 de 26** raízes E5 → exatamente 1 seção; só `investimentos` é
ambígua {`S1`,`S3`}), mas só faz sentido sob a leitura de proveniência.

> Há folga para consertar por projeção em vez de por corte: a eviction ocorreu com
> **42,9% do orçamento de tokens ocioso** (`PV13-17` da mesma rodada), cap 16.384 bytes.

## Painel de 4 especialistas (2026-09-01) — três premissas MINHAS caíram

`financial-planner` + `product-designer` + `prompt-engineer` + `data-engineer`, em paralelo,
com as medições acima no brief. Corrigiram-me em três pontos, e cada correção é verificável.

### O que o painel refutou em mim

1. **`section_id` NÃO é citação clicável.** Eu escrevi "citação"; medi depois de ser
   corrigido: `ParecerRisksTable.tsx:295` renderiza `§{risco.section_id} · {tema}` — **texto
   puro**, sem `<a href>`, nos quatro sítios (`ParecerMetricasTable.tsx:130`,
   `ParecerMovimentoCard.tsx:147`, `PontosFortesList.tsx:57`). O "27 de 27 resolvem" prova
   que o id **nomeia uma seção existente**, não que exista link. O leitor recebe o literal
   `§S4` — jargão interno em superfície user-facing.
2. **Minha medição "25 de 26 raízes → 1 seção" era circular.** Medi contra
   `aligned_with_layout`, que é escalar por schema (`docs/_schemas/note-planner.schema.json`)
   — ambiguidade é **irrepresentável por construção**. Medi que a declaração é função porque
   o schema a obriga a ser. A relação real é muitos-para-muitos (`irpf_kpis` → {S8,
   S_IRPF_RENDA, S_IRPF_OTIMIZACAO}; `protecao_patrimonial` → {S9, S_PROTECAO}).
3. **Eram 7 superfícies model-facing, não 5** — e o bloco `tools:` do YAML **não é uma
   delas** (o modelo nunca vê o YAML; ele tem 3 consumidores server-side e apagá-lo derruba
   um gate). As 3 que faltavam estão na **persona**, que é o original de que o system prompt
   é cópia: `config/agents/planner_persona.md:136` (R1), `:176` (R21), `:198`, e sobretudo
   **`:207`** — que condiciona `campos_faltantes[]` a um `found:false` inalcançável.

### Sintoma 1 — RESOLVIDO: o spread é a Previdência, não a base

Rodei o discriminador que o `financial-planner` pediu. **Hipótese A (denominador) REFUTADA:**

| `categoria` | `pct` | `pct_carteira_financeira` |
|---|---|---|
| Renda Fixa | 35,36 | **90,25** |
| Previdência | 1,62 | **4,14** |
| Caixa | 0,0 | **0,0** |

`Caixa = 0` ⇒ `carteira_financeira ≡ carteira_liquida` neste corpus, e a base **não** explica
nada. `90,25 + 4,14 = 94,39` = o carimbo (`goals.alocacao_alvo.derived.renda_fixa_atual_pct`
= **94,39**) ao centésimo. **O spread de 4,15 pp É a linha Previdência.**

Logo o defeito é **conceitual e não declarado**: `alocacao_alvo_deviation.py:18`
(`_BUCKET_TO_COMPARABLE`) decide que **toda** previdência é renda fixa. PGBL/VGBL é
*wrapper*, não classe — o fundo subjacente pode ser multimercado ou ações. O `rotulo`
diz só "Alocação em renda fixa (carteira líquida)" e **não declara** que dobra previdência
dentro. O modelo leu a linha `Renda Fixa` da tabela (a única projetada) e acertou o que
lhe foi dado.

Agravante medido pelo `financial-planner` e confirmado: **`$.goals` é projetado num único
lugar** (`parecer_planejador.yaml:742`, seção `plano_acao_atual`, `eviction_priority: 10`)
— e essa seção **foi evictada neste run**. O modelo nunca recebeu 94,39. Não havia como
reconciliar. **É defeito de projeção, e a ordem do conserto importa:** projetar → corrigir
o hint da linha 357 → só então gatear. Gate antes da projeção reprova o insolúvel e o
remédio vira reask storm ([[ADR-292]]).

### Sintoma 3 — rota fechada, sem conflito no painel

`prompt-engineer` mediu que o objetivo da [[ADR-341]] §D5 (*"não declarar ausência do que
existe"*) **já está entregue**, determinístico e sobre universo maior, pelo filtro 3-vias de
`parecer_pos_llm_guardrails.py:266-280`. A tool responderia estritamente menos e mais tarde
⇒ implementar as tools é **reimplementar pior no lado não-determinístico**. Caminho: cortar
as 7 superfícies, preservar o bloco `tools:` (relabel), trocar a "Recovery obrigatório" por
regra **declarativa** (o modelo *registra* o conceito em vez de *buscá-lo*), emendar a
[[ADR-341]] revogando D5 e a [[ADR-203]] registrando que o transporte nunca existiu.

⚠️ **Não haverá critério de contagem de `campos_faltantes`.** Os 4
`$.endividamento.dividas[N].taxa_juros_aa` são a [[ADR-206]] **funcionando** — o campo
existe no E5 (`e5_analysis.schema.json:934,969`) e tem **zero** ocorrências no manifest.
Cortar a promessa de tool **não prevê** que o contador caia; prever isso seria otimizar a
métrica contra a regra de calibração.

### Sintoma 2 — os dois especialistas DIVERGEM, e a divergência é a decisão da lane

Convergem em três pontos, todos contra o enunciado e contra mim:

- **Proveniência já tem carrier próprio e correto** (`ancoras[].path` + `evidencia`, folha a
  folha, [[ADR-296]]). `section_id` sob leitura de proveniência publicaria uma **segunda**
  resposta, mais grossa, à mesma pergunta.
- **Encolher o enum é caro pelo caminho da LEITURA**, não por migration: `section_id` é
  `String(32)` sem CHECK, mas `planner_review_tier_filter.py:102` constrói o DTO a partir do
  **artefato armazenado** e `response.py:29` o tipa com o mesmo `Literal` ⇒ `ValidationError`
  em `GET /planner-review` para todo parecer histórico (13 de 33 itens só neste run).
- **`SuggestionCalloutInline` está montado em 2 de 12 seções** (`S2FluxoCaixaSection.tsx:74`,
  `S7IndependenciaSection.tsx:74`) — os dois acharam isso independentemente. Logo a
  justificativa escrita em `pipeline/domain/types/suggestion.py:70` para barrar
  `S_PROTECAO` (*"emissor sem leitor"*) é **falsa para 10 dos 12 ids**. Deixá-la em pé faz a
  próxima lane herdar premissa errada.

**Achado crítico que nenhum de nós tinha:** `section_id` errado **desarma um guardrail**.
`parecer_pos_llm_guardrails.py:178` — `if item.section_id != _MC_SECTION: return False`.
Risco dependente de Monte Carlo rotulado S1/S3 em vez de S7 **escapa do rebaixamento de
confiança**, calado. Não é rótulo: é roteamento. Some-se a `parecer_finalization.py:57`, onde
`section_id` compõe o `thesis_key` que sustenta a janela de respeito ao descarte
([[ADR-290]] B4) — mudar o campo **ressuscita sugestão descartada**.

| | `product-designer` | `data-engineer` |
|---|---|---|
| Semântica | **navegação** ("destino de leitura") | **navegação** (idem) |
| Quem autora | **a máquina** — `section_id` sai do schema exposto ao modelo (`SkipJsonSchema`, precedente `Metrica.nome/valor_atual`) | **o modelo** — mas recebendo o id no payload |
| Mapa | objeto **novo** `(tema_canonico, prefixo de âncora)` → destino; **não** derivar de `aligned_with_layout`, que é proveniência e mandaria imóvel para S1 | injetar `[section_id: SN]` no cabeçalho de seção (`parecer_distiller.py:221`) + split 1:1 do manifest; ~240 de 16.384 bytes |
| Precedente | campo preenchido pela máquina já existe no mesmo schema | [[ADR-399]]: *"quando o número existe no payload, o modelo copia"* — e *"instrução não é gate"* |
| Gate | rejeita o meu: gate de proveniência **baniria S4 para risco de imóvel**, que é o destino certo | rebaixa (não repara — [[ADR-153]] §D1 torna `section_id` imutável) item que cite seção fora do conjunto **mantido pós-eviction** |

Sobre `S_PROTECAO` os dois convergem em **não** trazer agora, por razões diferentes e
compatíveis: o eixo do layout já está declarado (2.5 = o que está **contratado**; S9 = o que
**falta**), e *risco é, por definição, lacuna* ⇒ destino S9 sempre.

> **Escalado ao `senior-cto`** pelo anti-loop do CLAUDE.md: dois especialistas, ambos bem
> fundamentados, incompatíveis no **autor** do campo. Não é objeção a ajustar em 1 rodada —
> é bifurcação de arquitetura (quem escreve um campo que roteia guardrail e compõe chave de
> identidade).

## Arbitragem do `senior-cto` (2026-09-01) — decidido e fechado

Escalado pelo anti-loop. Ele **decidiu**, e corrigiu mais uma premissa minha.

### A correção: "13 de 33" não é contagem de erro

`test_vocabulario_do_dominio_nao_deriva_do_layout`
(`tests/unit/pipeline/test_suggestion_rules.py:322`) assere `VALID_SECTION_IDS ==
_enabled_layout_section_ids() - SECOES_SEM_ANCORA`: o enum **é** derivado-checado do layout
— é vocabulário de **navegação**, e está **correto**. Logo `S4` num risco de imóvel é o
comportamento certo, ainda que o dado de imóvel só venha projetado sob `patrimonio`/
`investimentos`. **O conjunto de defeito são os 4 riscos misroteados**, não 13 itens.
Escrever "13 de 33 errados" no closeout plantaria premissa falsa na próxima lane. O
`SectionId` **não** é drift de vocabulário — minha subseção acima carrega o aviso.

### Decisões (todas fechadas)

1. **A máquina autora `section_id`** — `product-designer` vence, mas **não** pelo
   argumento dele. Vence porque o remédio do `data-engineer` **re-ancora na função
   errada**, e isso é falsificável com dado que já temos: injetar `[section_id: SN]` no
   header ensina o modelo a copiar o id da seção que **projetou** o dado — proveniência.
   Para os 2 riscos de proteção isso daria S9 (acerto); para um risco de imóvel daria
   S1/S3, porque imóveis só existem no manifest dentro de `patrimonio` e `investimentos`,
   e o destino de leitura é S4. **A injeção troca uma classe de erro por outra.** A
   [[ADR-399]] não é violada — ela simplesmente **não se aplica** a um campo cuja resposta
   correta não está no exec context.
2. **O mapa é total por ORDEM DE RESOLUÇÃO**, não por chave composta — e é isto que
   dissolve o "não é função" que refutou o critério 2: ele refuta um mapa keyed em `tema`
   **sozinho**, não o mapa. Cascata: (i) tema de destino único (só `Proteção` → `S9`);
   (ii) longest-prefix da raiz da âncora — é aqui que `Custo tributário` e `Diagnóstico de
   dados` se desambiguam; (iii) tema → default; (iv) `S_parecer` como default seguro. O
   campo continua **required** (`planner_review_tier_filter.py:102` faz `raw["section_id"]`
   sem `.get`).
3. **O guard de Monte Carlo para de conjungir `section_id`**
   (`parecer_pos_llm_guardrails.py:176-180`): vira `âncora_MC ∨ (lemma_MC ∧ destino ==
   S7)`. Predicado de roteamento tem de ser re-justificado quando o campo muda de
   significado — deixar a conjunção seria decidir por omissão.
4. **Um PR, sem janela**, com o raio medido antes do merge: `thesis_key` move uma vez, e o
   dano só atinge linha `Descartada` dentro de 90d. A guarda é por `dedup_key`
   (`ws|ancora|acao` — **não** contém `section_id`, logo é imune).
5. **Três PRs.** O **sintoma 1 sai desta lane** (é o único que move número publicado e
   exige rebaseline de golden + veredito de domínio); sintomas 2 e 3 ficam, em PRs
   próprios.
6. **ADR `Proposto`**, decisão de uma linha: *`section_id` é destino de leitura derivado
   pela máquina, sai do JSON Schema exposto via `SkipJsonSchema` e é estampado no pós-LLM
   por cascata determinística; o vocabulário permanece o do layout e não encolhe.*

### Sonda de não-inércia — exigida ANTES de escrever o fix

Implementar **só** o resolver (função pura), aplicar aos 33 itens, e mandar as
**discordâncias** — só elas, sem dizer qual lado é a máquina — a `financial-planner` +
`product-designer` para veredito **cego**. Aprova se corrigir os ≥4 misroutes **e**
introduzir 0 destino julgado errado **e** 0 hits no passo 4. Reprovou? A injeção do
`data-engineer` volta a ser o caminho e a lane registra a refutação. *"É o que separa
'decidi' de 'apostei'."*

### Limpeza obrigatória (duas afirmações falsas em pé)

- `pipeline/domain/types/suggestion.py:68-73` — *"emissor sem leitor"* é **falso para 10 de
  12 ids** (`SuggestionCalloutInline` está montado só em `S2FluxoCaixaSection.tsx:74` e
  `S7IndependenciaSection.tsx:74`). Reescrever pelo motivo verdadeiro: o eixo do layout
  (2.5 = contratado, S9 = lacuna).
- `dev/check_planner_manifest_coverage.py` — o WARNING sobre S4/`S_IRPF_*`/`S_PROTECAO`
  trata como drift o que, sob navegação, é **esperado**. Vira declaração explícita.

Fora de escopo declarado: transformar `§S4` em `<a href>` (depende de scroll-spy, que
nunca funcionou neste relatório). O payoff barato é renderizar o **título** em vez do id
nos 4 sítios — o mapa já existe em `frontend/src/generated/report-layout.ts`.

## Sonda de não-inércia (2026-09-01) — a cascata, COMO ESPECIFICADA, está refutada

Rodei a sonda que o `senior-cto` exigiu antes do fix: resolver puro, sem tocar schema nem
guardrail, aplicado aos 33 itens do run `40d1af2a`. Ela fez exatamente o que existia para
fazer — **falsificou o desenho**.

### Resultado

| Medida | Valor |
|---|---|
| itens com `section_id` | 33 |
| passo 1 (tema exclusivo) / 2 (âncora) / 3 (tema default) / **4 (fallback)** | 5 / 9 / 19 / **0** ✅ |
| discordâncias com o emitido | **27 de 33 (82%)** |
| **itens com ≥1 âncora** | **9 de 33 (27%)** |

O passo 4 é 0 — a totalidade se sustenta. O resto não.

### Por que está refutada: o discriminador não existe para metade dos tipos

O passo 2 — *longest-prefix da raiz da âncora* — é o que desambigua `Custo tributário` e
`Diagnóstico de dados`, os dois temas que a medição de abertura mostrou serem
many-to-many. Mas ele **só pode disparar em 9 dos 33 itens**, e a razão não é do corpus, é
do **schema**:

```
Risco        ancoras? True
Sugestao     ancoras? True
PontoForte   ancoras? False   <-- o campo NÃO EXISTE
Metrica      ancoras? False   <-- o campo NÃO EXISTE
```

Para `ponto_forte` e `metrica` o passo 2 é **estruturalmente inalcançável**. A cascata
degenera em `tema → default` para **73%** dos itens — que é precisamente o mapa
many-to-one que o critério 2 original já tinha sido refutado por ser. O desenho não
resolve o problema para os tipos onde o discriminador não existe; ele o *move*.

### O que isto NÃO refuta

A **Decisão 1** segue de pé: a máquina autorar continua certo, e o argumento que a
sustenta (injetar o id ensina proveniência, e mandaria risco de imóvel para S1) não
depende da cascata. O que cai é a **forma** do produtor determinístico.

### Rotas que sobram, para o veredito cego decidir

1. **Dar âncora a `PontoForte` e `Metrica`** — o passo 2 volta a ser universal, mas é
   mudança de schema de saída do LLM (mais caro que a lane inteira) e `Metrica` já carrega
   `metrica_key` de vocabulário fechado, que talvez sirva de discriminador **melhor** que
   âncora: `alocacao_renda_fixa` nomeia a grandeza sem ambiguidade.
2. **Discriminador por tipo**: âncora para `Risco`/`Sugestao`, `metrica_key` para
   `Metrica`, e `PontoForte` sem discriminador (aceita o default do tema).
3. **Aceitar o default do tema** e medir quanto erro isso custa — 27 discordâncias num
   corpus onde o modelo às vezes acerta (o risco de `Liquidez` ancorado em
   `$.reserva_emergencia.total_liquida` foi para **S3**, e o mapa diz **S1**; qual serve o
   leitor não é óbvio).

> **Próximo passo, e é bloqueante:** veredito **cego** de `financial-planner` +
> `product-designer` sobre as discordâncias — sem dizer qual lado é a máquina —, e escolha
> entre as rotas 1–3. A tabela está em
> `_scratch`/`sonda_section_id.py` (off-git, reprodutível em ~5s, US$ 0).

## Veredito cego — domínio (2026-09-01)

### Antes do resultado: dois defeitos da MINHA sonda

1. **Cegueira parcialmente comprometida.** O prompt saiu com o placeholder `$(TABELA)`
   literal; para achar a tabela o painelista leu esta lane, que descreve o mecanismo da
   cascata. Ele **declarou** isso e não atribuiu lados. O veredito vale, mas a cegueira é
   fraca — a re-rodada precisa de agente que não tenha lido a lane.
2. **Inventei um título de seção.** Escrevi o dicionário `id → título` **à mão** e pus
   `S8 = "Previdência e IRPF"`. O layout diz **"Carga Tributária PJ — Regime e Base
   Dedutível"** ([[A40.l34]] moveu teto/capacidade PGBL para a `S_IRPF_OTIMIZACAO`).
   Contaminou os itens 2 e 24 para os **dois** painelistas. É a patologia *"cópia à mão
   envelhece calado"* — a mesma que esta lane investiga — cometida pela sonda que a
   investiga. Conferi os 12: 1 erro material (S8) + 1 truncamento inócuo
   (`plano_de_acao`). A sonda passou a **derivar** os títulos do `report_layout.yaml`.
3. A tabela também **não expunha `metrica_key`**, e por isso os itens 21/22/23 chegaram
   indistinguíveis (três `Alocação` idênticos). Corrigido.

### O resultado: nenhum dos dois produtores está uniformemente certo

**A em 13, B em 12, nenhum dos dois em 2.** Sob o critério do `senior-cto` ("corrige os
≥4 misroutes **e** introduz 0 destino julgado errado"), **qualquer que seja o lado
determinístico, ele reprova** — porque nos itens 5, 12 e 26 a resposta certa **não está
entre as oferecidas**. Não é falha do resolver: é falha do **vocabulário e dos defaults**,
e é consertável antes de re-rodar.

### O achado que destrava o desenho: falta o `tipo` do item

O discriminador que resolve os dois temas many-to-many não é a âncora — é o **tipo**, que
já está no payload de graça. É o eixo que o layout **já declara** (contratado × lacuna),
generalizado para **estado × alavanca**:

| tema | `metrica` (fato medido) | `risco`/`sugestao` (alavanca) |
|---|---|---|
| `Custo tributário` | `S_IRPF_RENDA` | `S_IRPF_OTIMIZACAO` |
| `Proteção` | `S_PROTECAO` (contratado) | `S9` (lacuna) |
| `Diagnóstico de dados` | `S2` | `S2` |

⚠️ **Corolário que corrige o painel anterior:** a regra *"risco é, por definição, lacuna ⇒
S9 sempre"* é certa para `risco`/`sugestao` e é **erro de categoria** aplicada a `metrica`.
`protecao_custo_premio` (prêmio pago sobre cobertura **contratada**) não é lacuna. Enquanto
`S_PROTECAO` estiver fora do vocabulário, **toda métrica de proteção é obrigada a mentir**.

### `metrica_key` é discriminador melhor que âncora — e o mapa não deve ir direto à seção

A âncora nomeia **onde o dado mora**; a `metrica_key` nomeia a **grandeza**. Destino de
leitura é função da grandeza — por isso a âncora precisa de exceção para imóvel
(`$.investimentos.total_imoveis_investimento` → **S4**, não S3) e a `metrica_key` não
precisa de exceção nenhuma.

E o mapa deve ser **`metrica_key → card_id`**, resolvendo `card_id → section_id` pelo
layout. Razão empírica e **já ocorrida**: a [[A40.l34]] *moveu* teto/capacidade PGBL da S8
para a `S_IRPF_OTIMIZACAO`. Um mapa direto para `section_id` teria envelhecido calado
naquele PR. Mapa para `card_id` quebra **ruidosamente** quando o card some, e segue certo
quando o card muda de seção.

### Cards que ancoram os destinos (medidos no layout, não inferidos)

`reserva_emergencia` → **S1** · `exposicao_cambial` → **S1** · `endividamento` → **S1** ·
`alocacao_atual_vs_alvo` → **S3** · `equilibrio_cerbasi` → **S2** · `despesas_doughnut` →
**S2** · chart `renda_passiva` → **S7** · `real_estate_yield` → **S4**.

Consequência: `reserva_cobertura_meses` → S1 (não S3) e `exposicao_cambial` → S1 (não S3)
— dois destinos que eu havia autorado errado na 1ª versão do mapa.

### `ponto_forte` aceita default de tema — por custo de erro, não por concessão

Ele **não roteia guardrail nenhum**: o guard de Monte Carlo
(`parecer_pos_llm_guardrails.py:178`) e o `thesis_key` (`parecer_finalization.py:57`) tocam
`risco`/`sugestao`. Misrotear elogio custa um clique; misrotear risco desarma um
rebaixamento de confiança calado. **O rigor do discriminador calibra-se pelo custo do erro
por tipo.**

### Precondições antes de re-rodar a sonda

1. Admitir `S_PROTECAO` no vocabulário **restrito a `metrica`/`ponto_forte`** — senão o
   item 26 é insolúvel por construção. (A justificativa "emissor sem leitor" já foi medida
   como falsa para 10 de 12 ids, e o eixo verdadeiro não barra métrica.)
2. `Diagnóstico de dados` → **S2** como default declarado. Enquanto for `S_parecer`, o
   produtor publica **destino nulo** — manda o leitor para a seção que ele já está lendo.

**Critério de aceite da re-rodada:** (a) os 4 misroutes de proteção viram S9; (b) nenhuma
**métrica** de proteção cai em S9; (c) nenhum item cai em `S_parecer` exceto fallback
contado; (d) nenhum item de `Alocação` com âncora imobiliária cai em S3; (e) o mapa é
derivado de `card_id`, provado por teste que **quebra se um card mudar de seção**.

## Veredito cego — UX (2026-09-01) · **a minha conclusão sobre a sonda está REFUTADA**

> ⚠️ **Correção à §Sonda de não-inércia acima.** Eu escrevi que a cascata estava refutada
> porque o discriminador só alcança 27% dos itens. **Medi a variável errada:** o passo da
> âncora não precisa alcançar *todos* os itens — precisa alcançar os itens **em que o
> default do tema erra**. Verifiquei a alegação do painel nos meus próprios dados e ela se
> sustenta: o default do tema erra em **3 itens (3, 7, 15)**, e **os três têm âncora**. Os
> 12 itens sem âncora nenhuma são justamente os que o tema resolve sozinho.
>
> **"A âncora não falta onde faz falta. A degeneração de 73% é o mapa funcionando, não
> falhando."** A §Sonda fica como está, com este aviso — snapshot datado não se reescreve.

### Placar independente

**12 A · 12 B · 1 "outro" · 2 mal-postas.** O embaralhamento segurou: **nenhuma coluna
vence por coluna**. Somado ao painel de domínio (13/12/2), os dois concordam no essencial:
*quem ganhar esta lane ganha por regra, não por lado.*

Os dois painéis também acharam **independentemente** o meu erro do título da S8.

### Rotas 1 e 3 caem por medição

- **Rota 1 (dar âncora a `PontoForte`/`Metrica`) — refutada.** Nos 10 itens desses dois
  tipos julgados com confiança, o default do tema acerta **10 de 10**. Pagar mudança de
  schema de saída do LLM — mais caro que a lane inteira — por **zero acerto medido**.
- **Rota 3 (só default de tema) — reprovada** pelo critério que o próprio `senior-cto`
  escreveu: introduz **≥3 destinos errados** (manda imóvel de investimento e exposição
  cambial para a carteira financeira).

### Rota 2, com a ORDEM INVERTIDA e três emendas

O desenho original tratava âncora como discriminador universal e tema como fallback. Os
dados dizem o contrário:

1. **Tema é a chave primária** — 6 dos 9 temas têm destino único e correto. Resolve e para.
2. **Âncora é desempate**, só para os temas que não são função (`Alocação`, `Custo
   tributário`).
3. **O prefixo tem de ir até o CAMPO, não até a raiz.** `$.investimentos.total_imoveis_investimento`
   → S1 e `$.investimentos.total_financeiro` → S3 **compartilham a raiz** `investimentos` —
   exatamente a raiz que a medição de abertura já sabia ser ambígua `{S1,S3}`. Com prefixo
   até o campo, os 5 itens ancorados de `Alocação` resolvem **5/5**.
4. **`Custo tributário` desempata por TIPO** (nenhum dos dois itens tem âncora).
5. **`Diagnóstico de dados` não recebe destino.** Guarda `S_parecer` (o campo segue
   `required`) e o **render suprime** a citação quando o destino é a própria seção que
   hospeda o item. *"Auto-ponteiro não é destino; é ruído"* — e hoje passa despercebido só
   porque o leitor vê `§S_parecer` e não decodifica.

### A divergência real entre os dois painéis — e ela decide a ordem da cascata

**Item 2** (`Renda passiva`, âncora `$.investimentos.total_financeiro`): domínio diz **S3**
(pela âncora); UX diz **S7** (pelo tema — o chart `renda_passiva` mora na S7). É
precisamente o caso que separa *âncora-primeiro* de *tema-primeiro*, e a UX o usa como
prova: **âncora-primeiro erraria o item 2**.

Atenuante que registro contra o painel de domínio: o par que ofereci ali era `S8 × S3`, e o
`S8` estava contaminado pelo **meu** título falso. O domínio escolheu "o menos absurdo dos
dois"; a UX rejeitou os dois e nomeou o S7. Na §mal-postas o domínio diz que a disputa
honesta é **S3 × S7** — ou seja, ele nunca chegou a comparar com o destino certo.

Divergências menores, ambas com a regra a declarar: **item 8** (`Custo tributário` de
risco: domínio → `S_IRPF_OTIMIZACAO`, UX → `S_IRPF_RENDA`, com baixa confiança declarada e
aceite de voto vencido *desde que a regra seja estável*) e **item 26** (métrica de
`Proteção`: domínio → `S_PROTECAO`, UX → S9).

### Estável-errado > ocasionalmente-certo — e a ressalva que fecha

O ponteiro é **mobília de navegação**: seu valor é ser *aprendível*. Erro estável é
auditável e cabe num gate; erro intermitente é infalsificável e **contamina a evidência ao
lado** — o `§destino` fica encostado nas âncoras de proveniência, que são confiáveis, num
produto cuja proposição é "os números vêm do seu dado". E aqui a instabilidade não é
cosmética: `section_id` roteia o rebaixamento de confiança e compõe `thesis_key`.

**A ressalva:** estável-errado só vale quando o destino errado **não é ativamente
enganoso**. `S4` num risco de seguro *é* enganoso — nomeia um assunto real e errado.
`S_parecer` num diagnóstico é inútil, não enganoso. Por isso o fallback terminal deve ser o
auto-ponteiro **com supressão no render**: o modo de falha aceitável é *não dizer nada*,
nunca *dizer outra coisa*.

### Ordem de entrega — dois PRs, e a inversa é proibida

1. **PR 1 — resolver + supressão de auto-ponteiro.** O destino fica **certo** antes de
   ficar legível.
2. **PR 2 — título em vez de `§S4`** nos 4 sítios, lendo de
   `frontend/src/generated/report-layout.ts`; `shortLabel` quando existir, e `"Ver em:"` no
   lugar de `§` (que é convenção jurídica, não de navegação).

Nunca a inversa: renderizar o título hoje publicaria *"Real Estate — Imóveis e Renda
Passiva"* em cima de um risco de seguro de vida, e *"Parecer do Planejador"* dentro do
Parecer do Planejador, em 13 de 33 itens. **Hoje isso passa; com título, é uma denúncia
impressa.**


<!-- Sem `ship_pr`: o campo declara que a LANE foi entregue, e só 1 dos 3 sintomas saiu.
     O gate `lane-transition` reprova `ship_pr` com `status: open`, e está certo — a
     entrega parcial se registra na prosa abaixo, não no frontmatter. -->

## Entrega parcial — sintoma 3 MERGEADO ([#1966](https://github.com/davidrobert/mathoms/pull/1966), `24a375eb`, 2026-09-02)

**A lane segue `open`**, e o que resta é o **sintoma 2**.

### Saiu no #1966

As **7** superfícies model-facing pararam de prometer ferramenta que o transporte não
expõe. [[ADR-341]] §D5 **revogada** (o objetivo dela já era entregue por `_classify_campo`,
determinístico e sobre universo maior) e [[ADR-203]] emendada (D1/D2/D4 decidiram um
transporte que nunca chegou ao código). O bloco `tools:` do YAML **ficou** — não é
model-facing, tem 6 consumidores server-side, e apagá-lo derrubaria dois gates. Gate novo:
`tests/dev/test_prompt_capability_parity.py`, bicondicional, com os 4 canais provados por
**mutação do produtor** e asserção de precondição contra vacuidade no canal de eviction.

Versões no mesmo PR (`PROMPT_VERSION` 2.5.0 · persona 1.2.0 · manifest 2.19.0) porque as
três compõem `compute_cache_key` — separá-las cobraria a frota **três vezes** pela mesma
correção. Budget reconferido pelo tripwire: **−1,58%**.

### O que fica, e por que não foi junto

O **destino de citação**. Decidido (a máquina autora; o mapa deriva do layout via
`card_id`), mas **bloqueado por três precondições** nomeadas acima:

1. admitir `S_PROTECAO` restrito a `metrica`/`ponto_forte` — sem isso o caso da métrica de
   proteção é **insolúvel por construção**;
2. declarar `Diagnóstico de dados` → **S2** — enquanto for `S_parecer`, o produtor publica
   **auto-ponteiro**, que manda o leitor para a seção que ele já está lendo;
3. **resolver a divergência de ORDEM da cascata** (tema-primeiro × âncora-primeiro) — o
   item que a decidiria foi contaminado pelo título falso da S8 que eu digitei, então o
   painel de domínio nunca comparou com o destino certo. Precisa de rodada nova, com agente
   que **não** tenha lido esta lane.

O sintoma 1 saiu para a [[A40.l120]] (renumerada duas vezes: `l118` e `l119` foram tomadas
por outras lanes enquanto o #1966 esperava na fila de merge).
