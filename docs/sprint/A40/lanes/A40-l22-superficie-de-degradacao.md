---
id: A40.l22
type: lane
title: "Superfície de degradação: o relatório declara o que foi retido, inclusive no PDF"
sprint: A40
plan: PLAN-report-trust
status: shipped
priority: P0
branch_slug: a40-l22-superficie-de-degradacao
adrs: []
depends_on:
  - "[[A40.l20]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/frontend
---

# A40.l22 — `superficie-de-degradacao`

> 🔓 **Desbloqueada em 2026-08-06, campo corrigido em 2026-08-07.** O gatilho
> declarado era o **PR1** da [[A40.l20]] — não o PR2 —, e ele mergeou em
> `0301f7a0`/#1250. Esta lane consome **estado e contadores**, que o PR1 entrega,
> e testa por fixture; o wire-up no orquestrador (PR2 da l20) não a gateia.
>
> `open`, não `in_progress`: ninguém a pegou ainda, e `in_progress` a faria
> parecer tomada. ~~O `depends_on` continua apontando para a [[A40.l20]] — que não
> é terminal —, e é a **2ª cláusula** do §Predicado~~ — **desatualizado em
> 2026-08-07**: a [[A40.l20]] virou `shipped` com o merge do PR2 (`039c1b6d`/#1278),
> então o `depends_on` está **terminal** e o `open` passa a valer pela **1ª
> cláusula** do §Predicado do campo `status` do [`_README`](../_README.md). A
> amarra de entrega parcial se extingue: não há mais o que reverter em par.
> Segue **P0** e **bloqueador de fato do beta**.
>
> ➕ **Recebido do PR2 da [[A40.l20]] (2026-08-07) — entra no escopo desta lane.**
> A **copy por código de ausência**. O 404 do parecer passou a discriminar 4
> códigos (`report_not_found` · `not_generated_yet` · `generation_unavailable` ·
> `parecer_artifact_missing`), tipados no snapshot OpenAPI, e o `usePlannerReview`
> **transporta** o código no estado `not_generated` (`code: PlannerReviewAbsenceCode`)
> **sem escolher palavra** — de propósito: a escolha é de produto e é sua. Junte
> com o **free tier**, que já era desta lane e é a outra metade da mesma mentira
> (o stage recusa antes de gerar ⇒ sem row ⇒ 404 ⇒ "ainda não gerado").
>
> ⚠️ **Ficou `blocked` por um dia inteiro depois de desbloqueada** — ninguém flipa
> o campo no merge da dependência, e nesse intervalo a lane sumiu do
> [`SPRINT_CURRENT`](../../../_MOC/_generated/SPRINT_CURRENT.md) justamente quando
> virou pegável. É o caso que o §Delta de 2026-08-06 do `_README` previu, agora
> ocorrido; a [[A40.l18]] sofreu o simétrico (`open` stale pós-merge) no mesmo dia.
>
> ✅ **Entregue em 2026-08-08 — PR único #1277** (`shipped`). 4 superfícies
> declaram a retenção lendo o MESMO contador: nota no hero de `S_parecer` ·
> 3º contador na caption de `ParecerRisksTable` · 1 linha no
> `ReportDataQualityBanner` (título "precisão"→"leitura", zero banner novo) ·
> `HistoryRow` do `/pipeline`. Gate bloqueante em `frontend-checks`
> (`parecer-degradacao.@critical.spec.ts`, superfície de print por
> `emulateMedia`), mais gate de contraste em Vitest e `pdftotext` no job de print.
>
> **`shipped` com resíduo declarado — 2 itens do §Critério de aceite ficam
> abertos, e nenhum deles é fechável dentro desta lane:**
>
> - **A perna de PDF é parcial.** A ressalva do banner chega à camada de texto
>   (assertada por `pdftotext`, verde no CI); a nota da SEÇÃO não, em geometria
>   A4 — e nenhum `<h2>` de seção chega. Causa pré-existente no export, fora
>   desta lane; `test.fixme` nomeado em `print.@critical.spec.ts` marca o ponto
>   de retomada. Ver detalhe no item 2 abaixo.
> - **Teste com humano (n=1)** — owner-gated, não executado.
>
> **Duas medições da execução que o escopo escrito não previa** (detalhe no PR):
>
> 1. **O contador de retenção é escalar do parecer inteiro**, não por bucket:
>    `retention.items_dropped_count` é um número só, e o enforcement remove
>    risco **ou** sugestão. A caption diz *"N itens do parecer retidos na
>    conferência"*, não *"N riscos"* — atribuí-lo ao bucket em cuja caption ele
>    mora afirmaria algo falso quando o item retido foi uma sugestão. Expor o
>    breakdown por bucket exigiria coluna + migration, fora do §Aceite.
> 2. **A perna de PDF do §Critério de aceite é parcial, e a causa é
>    pré-existente.** A ressalva do banner chega à camada de texto do PDF
>    (assertada por `pdftotext`); a nota da SEÇÃO não, em geometria A4 — e
>    nenhum `<h2>` de seção chega (`"Parecer do Planejador"`,
>    `"Síntese Estratégica"`, `"Apêndice"`: 0 ocorrências). Com
>    `paperHeight: 300in` o mesmo run traz a nota, os pontos fortes e o
>    diagnóstico. É defeito do export, não desta lane; o assert fica como
>    `test.fixme` nomeado em `print.@critical.spec.ts`.

> Onda 3 da A40 (§Frente 4 de [[PLAN-report-trust]]). Fatia **premium/add-on** da
> F11.5 — o caminho determinístico dela foi entregue na Sprint B (2026-04-17),
> conforme `docs/reference/PHASES.md`. Estende A28.l9; **não** inventa banner.

## Problema

A seção `S_parecer` trata "não contratado", "gerado e retido" e "free tier" como
um estado só (`not_generated` → 404 → mesma copy), e a copy atual — *"Próximo
relatório premium incluirá o parecer orientativo do planejador"* — **mente** no
caso premium-com-retenção.

E a perda parcial é **indetectável por construção**: ausência de seção inteira é
auto-evidente ao rolar; ausência de 3 de 12 itens numa lista que ninguém contou,
não. Foi isso que fez a perda atravessar 7 runs (16 itens apagados,
2026-07-20 → 07-29) sem detecção — só o run de 2026-07-31, que falhou inteiro e
é auto-evidente, a revelou ([[ADR-304]] §Emenda 2026-08-03).

## Decisão

**Princípio de calibração:** nunca deixe o usuário descobrir a lacuna depois. O
que corrói confiança num relatório patrimonial não é o aviso — é a dúvida
retroativa, que é ilimitada ("quais dos meus 9 relatórios estão completos?").
Nota datada e escopada é limitada. Enquadre a retenção como o controle
funcionando, não como falha.

**Sinal proporcional à invisibilidade**, não à gravidade: o estado "retido
inteiro" é auto-evidente e não precisa de linha no banner; o estado "parcial" é
indetectável e precisa.

**Dois estados novos** (o de free tier já existe):

- **Retido inteiro** — estado explícito com escopo de dano delimitado + CTA de
  regeneração. A delimitação é obrigatória: sem ela o usuário generaliza
  "parecer falhou" → "os números estão errados", que é o dano real.
- **Parcial** — caption estendendo o idioma existente de `ParecerRisksTable`
  (`Mostrando X de Y · N não publicados · +Z no Premium`), mantendo os dois
  contadores **semanticamente separados** (retido = qualidade, ação
  reprocessar; gated = comercial, ação comprar), + 1 linha explicativa no header
  do card, **print-visible, nunca tooltip**.

**Uma linha no `ReportDataQualityBanner` existente** (A28.l9) para o estado
parcial. **Não criar banner novo** — medido em 2026-08-05
(`rg -n 'export function [A-Za-z]*Banner' frontend/src/components/report/`), há
**4**: `ReportDataQualityBanner`, `DefasagemWarningBanner`, `AcumuladoresBanner`,
`MonthClosedBanner`. Reusar um dos 4 é a decisão; o argumento é a enumeração,
não um ordinal. Emenda de uma palavra no título: hoje diz
*"N pendências afetam a **precisão** deste relatório"* — item retido afeta
**completude**, não precisão; use "afetam a **leitura**", palavra que o próprio
componente já usa na barra limpa.

**O PDF é a superfície de maior valor** do conjunto: é a única que **sai do
produto** e chega a terceiros (contador, corretor, banco) que não podem fazer
pergunta de follow-up. Nota em texto no DOM, com `<details>` forçado `[open]`
(padrão de `SParecer.print.css`).

**Fora desta lane:** painel cru em `ops.mathoms.ai` (cortado — ver §Frente 4) e
marcador na lista `/reports` (P2 — com ~2 relatórios/mês a lista não é superfície
de descoberta).

## Critério de aceite

- Os 2 estados novos renderizam; **nenhum** contém `error_detail` cru, `risco[N]`,
  `number_in_prose`, `whitelist_miss`, `stage`, `E5` ou `E6`.
- Estado parcial emite a caption **e** 1 linha no banner existente. Zero banner
  novo criado.
- Título do banner passa de "precisão" para "leitura".
- **KR-3:** sinal assertado em 4 superfícies — seção, banner, `/pipeline`, e
  **PDF via `pdftotext`**.
- Nota é **texto no DOM**, não `title=`/hover (falha 1.4.13 e desaparece no PDF).
- `S_parecer` nos estados novos adicionado a `STRATEGIC_SECTIONS` do
  `a11y.@critical.spec.ts`; axe-core 0 critical/serious, light **e** dark.
- `<md`: a nota vira linha própria; caption com 3 contadores não estoura.
- **Rebaseline explícito** dos snapshots visuais (light+dark × estados novos) — o
  job visual não é bloqueante, então não pode ficar para o próximo agente.
- Teste com humano (n=1): o dono abre um relatório parcial **sem** ter visto o
  `/pipeline` e diz em 1 frase o que falta e o que fazer; e lê o PDF do estado
  retido **sem** concluir que os números das outras seções são suspeitos.

## Escopo herdado da [[A40.l10]] — supressor não-declarado no frontend

Registrado aqui **pelo destino** em 2026-08-06 (a convenção do repo é que handoff
só existe quando a lane de destino o registra; a l10 é o emissor).

| Herdado | O que foi medido na l10 |
|---|---|
| **`dedupeBySemanticKey` descarta itens da lista sem declarar** | `frontend/src/components/report/utils/curadoriaDestaques.ts` colapsa itens por chave semântica derivada de **regex sobre o texto** e é *first-wins*: o item que sobrevive depende da **ordem** de chegada, e o descartado some da tela sem rastro no payload nem na narrativa |

É a mesma classe que esta lane existe para fechar — retenção que o artefato não
declara —, só que **no frontend** e sem nem passar pelo produtor. Duas
consequências que a l22 herda: (a) a contagem que a l10 passou a declarar no
`s10` (recomendações retidas por classe de motivo, [[ADR-365]]) **pode divergir**
do que o card renderiza, porque o dedupe atua depois; (b) qualquer ordenação
futura ([[A40.l10]] PR3) muda **qual** item sobrevive ao dedupe, sem mudar o
payload — logo asserção sobre payload não prova o renderizado.
