---
id: ADR-372
type: adr
title: "Texto sobre tint da própria cor usa o par `-on-tint`, e o gate mede em vez de proibir a forma"
status: Decidido
date: "2026-08-08"
relates_to: ["[[ADR-076]]", "[[ADR-117]]", "[[ADR-143]]", "[[ADR-236]]"]
tags:
  - type/adr
  - status/decidido
  - area/frontend
  - area/design-system
  - area/a11y
---

# ADR-372 — Par `-on-tint` para texto sobre tint da própria cor

## Contexto

O relatório usa um padrão recorrente de badge/faixa: o fundo é um tint da cor
semântica (`color-mix(... var(--X) N%, ...)`) e o texto é a **mesma** `var(--X)`.
Lê-se bem no editor e é errado por construção — o texto compõe contra a própria
cor clareada, então quanto mais forte o tint, pior o contraste.

Medição de 2026-08-08 sobre `tokens.css`, tint de 15% sobre `--surface-card`:

| cor | light | dark |
| --- | --- | --- |
| `--semantic-gain` | 4,09:1 ✗ | 6,05:1 |
| `--semantic-alert` | **1,86:1** ✗ | 6,21:1 |
| `--semantic-loss` | 5,01:1 | 4,36:1 ✗ |

**14 de 18 instâncias do padrão reprovavam** WCAG AA (4,5:1) em pelo menos um
tema. O caso `alert` a 1,86:1 é texto quase invisível. Nenhum gate pegava:

- o `axe` varria **só light**, e `loss` passa em light — inspecionar o tema
  claro concluía "loss está ok";
- `--semantic-gain`/`alert` reprovam em light, mas o pior deles vivia num branch
  (`fator_r_faixa: "anexo_v"`) que a fixture `medium` não monta. Gate que passa
  por **ausência do caso** não é gate.

A profundidade do tint é o discriminante: os rótulos de `S_parecer` usam 6% e
passam; os cards usam 15% e reprovam. Não é "a cor está errada" — é "esta cor
não serve como texto sobre ela mesma nesta profundidade".

## Decisão

**D1 — Toda cor usada como texto sobre tint de si mesma ganha um par
`--X-on-tint`.** A correção é sempre na cor do **texto**, nunca afrouxando o
tint: o tint carrega o significado visual (severidade), o texto carrega a
legibilidade. Cada par difere da base em **exatamente um tema** — o que reprova
— para não mexer no que já está bom.

| token | light | dark | difere em |
| --- | --- | --- | --- |
| `--semantic-gain-on-tint` | `#166534` | = base | light |
| `--semantic-alert-on-tint` | `#984C11` | = base | light |
| `--semantic-loss-on-tint` | = base | `#FDA4AF` | dark |
| `--brand-warning-on-tint` | `#984C11` | = base | light |
| `--brand-secondary-on-tint` | `#345E77` | `#CBD5E1` | ambos |
| `--surface-muted-foreground-on-tint` | = base | `#CBD5E1` | dark |

**D2 — O gate MEDE o par, não proíbe a forma.**
[`dev/check_tint_contrast.py`](../../dev/check_tint_contrast.py) extrai
`(cor de texto, cor de tint, %)` de cada `className` e calcula o contraste nos
dois temas.

Proibir a forma foi considerado e recusado: reprovaria tint de 8-10%, que passa
com folga (um call-site dava 5,45/4,74), e — pior — deixaria passar par de
tokens **diferentes** que contrasta mal, porque a regra olharia o nome e não a
cor. Medindo, token novo, percentual novo ou valor novo de tema entram no
cálculo sozinhos, sem editar allowlist.

Isso não é teórico: o gate por medição achou **4 call-sites** que a varredura
manual por `--semantic-*` perdeu, todos usando tokens de `brand`/`surface`
(`--brand-warning` a 1,82:1, `--brand-secondary` a 3,81:1).

**D3 — Alias resolve antes de comparar.** `--semantic-warning`/`alert`,
`danger`/`loss` e `success`/`gain` são o mesmo hex. Sem normalizar,
`bg: warning` + `text: warning` sairia do conjunto medido por "tokens
diferentes" e o gate ficaria verde **por não olhar** — o modo de falha caro,
porque o teste do repo-real continuaria passando.

**D4 — O que o pareamento não alcança é NOMEADO, não inferido.** O gate pareia
dentro de **um** `className`. Ficam de fora duas famílias: ícone colorido cujo
`text-[…]` vive num elemento filho (1.4.11, limiar 3:1) e par montado por
`style` inline com `bg`/`fg` em linhas separadas de um object literal. Entram em
`NAMED_PAIRS`, com **checagem de staleness**: entrada cujo call-site trocou de
token falha, em vez de medir fantasma.

## Consequências

**O gate estático e a varredura `axe` não se substituem — e provaram isso um no
outro.** O `axe` em dark achou `BADGE_COLOR` de `alocacaoCardParts.tsx` (4,44:1),
invisível ao gate por ser `style` inline em linhas separadas. Na direção oposta,
o gate cobre branch que fixture nenhuma monta. Manter os dois é deliberado.

**A varredura de página inteira do `axe` passou a rodar nos dois temas**; as
por-seção seguem em light. Custo: +1 teste em vez de +15, com o mesmo alcance —
a página contém o DOM de todas as seções e o `axe` reporta o seletor do ofensor.
Perde-se a localização por seção no vermelho. Detalhe e limites em
[A11Y_CHECKLIST](../plan/REPORT_PREMIUM/A11Y_CHECKLIST.md).

**Duplicação de valor aceita.** `--brand-warning-on-tint` repete os hex de
`--semantic-alert-on-tint`, porque `--brand-warning` e `--semantic-alert` já são
nomes independentes para a mesma cor — duplicação que precede esta ADR. Expressar
o par como `var(--semantic-alert-on-tint)` exigiria resolver indireção `var()`
no gate e nos dois testes de token. Fica para quando houver segundo motivo.

**Os valores de D1 são AA (4,5:1), e há uma decisão AAA em aberto sobre eles.**
A [[ADR-236]] pede "UI A11y AAA" para o `<CascataFiscalCard/>`; a emenda de
2026-08-08 daquela ADR mediu e registrou que o critério **nunca foi verificado**
(o helper do `axe` monta `withTags` até `wcag21aa`, então a regra de 7:1 não
roda) e que os 4 pares do badge Fator-R passam AA e reprovam AAA (5,60–6,21:1).
Uma das duas saídas propostas lá é **recalibrar os tokens `-on-tint` para ≥ 7:1**
— o que mudaria D1 desta ADR e alcançaria os 18 call-sites, não só aquele card.
Enquanto a decisão não sai (dono: `product-designer`), o limiar canônico do par
`-on-tint` é **AA**, e é isso que os três mecanismos medem.

**Custo por call-site novo:** quem escrever badge com tint precisa lembrar do
par. Mitigado por três caminhos — a regra no §Design System do `CLAUDE.md`, a
mensagem de erro do gate (que nomeia o token a usar) e o comentário no
call-site. É o padrão de [[ADR-143]]: a regra vive junto do enforcer.

## Alternativas consideradas

- **Escurecer/clarear a cor base.** Rejeitada: a base também é usada como
  fundo sólido, borda e cor de série de gráfico, onde já está calibrada.
  Mudá-la para servir a um uso quebra os outros.
- **Afrouxar o tint (15% → 6%).** Rejeitada: o tint codifica severidade; achatar
  todos para 6% apaga a diferença visual entre "atenção" e "crítico" para
  resolver um problema que é do texto.
- **Regra ESLint proibindo o par.** Rejeitada em D2 — proíbe forma segura e não
  detecta par inseguro de tokens diferentes.
- **Só corrigir `loss` no dark** (o achado que abriu a varredura). Rejeitada
  depois de medir: seria fechar a instância mais branda e deixar 1,86:1 de pé.
