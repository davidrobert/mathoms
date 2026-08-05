---
id: A40.l22
type: lane
title: "Superfície de degradação: o relatório declara o que foi retido, inclusive no PDF"
sprint: A40
plan: PLAN-report-trust
status: blocked
priority: P0
branch_slug: a40-l22-superficie-de-degradacao
adrs: []
depends_on:
  - "[[A40.l20]]"
tags:
  - type/lane
  - sprint/a40
  - status/blocked
  - priority/p0
  - area/frontend
---

# A40.l22 — `superficie-de-degradacao`

> 🚧 **Bloqueada pelo PR1 da [[A40.l20]]** (2026-08-03; gatilho precisado em
> 2026-08-05) — não é pegável até o **contrato** do desfecho gerado-e-retido
> existir no modelo e na API (l20 §Sequência de entrega, PR1). **Não** espera o
> PR2 (wire-up no orquestrador, atrás da [[A40.l18]]): esta lane consome estado e
> contadores, que o PR1 entrega, e testa por fixture. `blocked` e não `open` pelo
> §Predicado do campo `status` do [`_README`](../_README.md): dep pendente, sem
> amarra de entrega parcial. Segue **P0** e **bloqueador de fato do beta**.
>
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
