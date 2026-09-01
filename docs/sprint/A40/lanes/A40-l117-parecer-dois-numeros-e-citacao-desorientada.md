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
adrs: ["[[ADR-199]]"]
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

Não é "nome vindo da prosa" genérico. É drift de contrato, medido:

- O manifest projeta {`S1`,`S2`,`S3`,`S7`,`S8`,`S9`,`S10`,`plano_de_acao`}.
- O enum `SectionId` (`pipeline/llm/schemas/parecer_planejador.py:49`, cópia à mão,
  duplicada em `backend/app/schemas/dto/planner_review/response.py:29`) oferece **4 a
  mais**: `S4`, `S_IRPF_RENDA`, `S_IRPF_OTIMIZACAO`, `S_parecer` — seções que o exec
  context **nunca popula**.
- Uso real: **13 de 33 itens (39%)** citam uma dessas 4, incluindo **5 de 11 riscos**.
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
