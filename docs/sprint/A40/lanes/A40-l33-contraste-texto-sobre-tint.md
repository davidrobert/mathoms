---
id: A40.l33
type: lane
title: "Contraste de texto sobre tint da própria cor: fecha a classe e gateia por medição"
sprint: A40
status: in_progress
priority: P1
branch_slug: a40-l33-contraste-texto-sobre-tint
adrs:
  - "[[ADR-372]]"
  - "[[ADR-076]]"
  - "[[ADR-117]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/frontend
  - area/design-system
  - area/a11y
---

# A40.l33 — `contraste-texto-sobre-tint`

## Problema

O fix do badge Fator-R (S8) abriu a suspeita de que o padrão "texto na cor `--X`
sobre tint da mesma `--X`" reprovava WCAG AA em mais lugares. A varredura
confirmou, com escala maior que a hipótese inicial: **14 de 18 instâncias
reprovavam** em pelo menos um tema, e a que motivou a lane (`loss` a 4,36:1 no
dark) era a **mais branda** — o pior caso era âmbar a **1,86:1**, texto quase
invisível, em 5 call-sites.

Dois gates existiam e nenhum pegava: o `axe` varria só light (e `loss` passa em
light), e o pior par vivia num branch que a fixture `medium` não monta.

## Escopo

Entregue nos PRs [#1320](https://github.com/davidrobert/mathoms/pull/1320)
(código + gate) e [#1323](https://github.com/davidrobert/mathoms/pull/1323)
(documentação).

- **6 pares `-on-tint`** em `design-tokens/tokens.json`, cada um diferindo da
  base em exatamente um tema — o que reprova ([[ADR-372]] D1).
- **18 call-sites migrados**, trocando a cor do texto, nunca afrouxando o tint.
- **`dev/check_tint_contrast.py`** — gate que mede em vez de proibir a forma
  (D2), com resolução de alias (D3) e `NAMED_PAIRS` para o que o pareamento por
  `className` não alcança (D4). Roda no pre-commit e no `lint-all`, que está em
  `all-green.needs`.
- **`tests/dev/test_check_tint_contrast.py`** — trava a lógica do gate
  (aritmética WCAG, alias, staleness) independentemente dos call-sites de hoje.
- **Varredura dark** na página inteira do `a11y.@critical.spec.ts`.

## Critério de aceite

- [x] `python3 dev/check_tint_contrast.py` → 0 violações (27 pares medidos)
- [x] Mutação: reverter um call-site para a cor base faz o gate falhar nomeando
      ratio, tema e o par a usar
- [x] `a11y.@critical.spec.ts` verde nos dois temas
- [x] [[ADR-372]] registra a decisão e as alternativas recusadas
- [x] Regra no §Design System do `CLAUDE.md`, onde o próximo agente lê antes de
      escrever componente

## O que a lane provou sobre os gates

Os dois gates de contraste **acharam defeitos um do outro**, e é por isso que os
dois ficam:

- a varredura **dark** achou `BADGE_COLOR` de `alocacaoCardParts.tsx` (4,44:1),
  invisível ao gate estático por ser `style` inline com `bg`/`fg` em linhas
  separadas;
- o gate **por medição** achou 4 call-sites de `brand`/`surface` que a varredura
  manual por `--semantic-*` tinha perdido (1,82:1 e 3,81:1).

Nenhum dos dois fecharia a classe sozinho.

## Ataque — 2026-08-13 · PR [#1432](https://github.com/davidrobert/mathoms/pull/1432)

**A classe não estava fechada.** O gate media **uma sintaxe**; existem três, e as
outras duas escondiam **7 call-sites reprovando AA** — com os mesmos números que
a [[ADR-372]] publicou como sendo *o problema*, inclusive o 1,86:1 do âmbar.

| call-site | par | light | dark |
| --- | --- | --- | --- |
| `ExposicaoCambialCard` `amarelo` / `fallback_classe` | alert sobre 15% alert | **1,86** ✗ | 6,21 |
| `ExposicaoCambialCard` `verde` / `override` | gain(accent) sobre 15% | **4,09** ✗ | 6,05 |
| `ExposicaoCambialCard` `vermelho` | loss sobre 15% loss | 5,00 | **4,36** ✗ |
| `CreateRuleDialog` (app) | alert sobre 5% alert | **1,99** ✗ | 7,85 |
| `CategoryChipDiff` (app) | accent sobre 10% accent | **4,38** ✗ | 6,80 |

Os sete escrevem o tint como `bg-[var(--X)]/15` — o `BG_RE` casava só
`bg-[color-mix(…,transparent)]`. O `axe` também não alcança: `medium.json` não
tem `exposicao_cambial`, então o branch não monta. **É o mesmo modo de falha que
abriu a lane** (o `anexo_v` do Fator-R que a fixture não montava), repetido numa
dimensão que a D2 não tinha considerado — a D2 fecha token, percentual e tema,
e a **sintaxe** é o quarto eixo.

Entregue no PR: 7 call-sites migrados, `--brand-accent-on-tint` (aplicação
mecânica da D1), as três formas em `_tints_in_line`, substrato declarado usado
no lugar do card, `NAMED_PAIRS` validando o **percentual** além do token, e +3
pares pai→filho nomeados. O gate foi de **27 para 37 pares medidos**.

Dois achados de calibragem, sem defeito vivo:

- `EstrategiaAporteCard` estava a **4,51:1** — 0,01 acima do limiar, e nada o
  media (forma com substrato declarado + texto em linha diferente da do tint).
  Migrado para o par e nomeado.
- `color-mix(…, var(--surface-card))` é **opaco**: não compõe com o fundo do
  pai. Medir badge dentro de `.card-variant-*` como se compusesse dá ~0,45 a
  menos, e está errado. Só a forma `transparent` compõe — para essa, os pares
  dentro de card tintado ficam a 4,54–4,55 reais contra os 5,00 que o gate
  reporta. Passa, mas a margem é menor do que o número diz.

## Aberto — 2026-08-13 · dono: David Robert

Três achados do ataque **fora** da classe desta lane (que é "texto sobre tint da
própria cor"). Ficaram fora do PR por exigirem decisão de design, não por
esquecimento.

**1. Cor semântica como foreground sobre o card liso — 6 textos a 2,06:1.**
`AlocacaoAtualVsAlvoCard:163` (11px), `PremissasEconomicasCard:152` (14px),
`StressScenarioCard:126/147/162`, `S7IndependenciaSection:434` (12px) usam
`--semantic-warning`/`--semantic-alert` como cor de texto sobre `--surface-card`.
Reprova 1.4.3 em light por folga larga; em dark passa (8,67). Mais 2 ícones
`aria-hidden` a 1,85–2,06 (`AcoesMitigacaoCard:61`, `alocacaoCardParts:112`) —
isentos de 1.4.11 por serem decorativos, mas abaixo do 3:1 que esta lane aplica
a ícones que nomeou.
*Decisão pendente:* qual âmbar legível usar — `--semantic-alert-on-tint`
(`#984C11`, ~6,9:1 sobre branco) ou `--report-alert-warning-text` (`#B45309`).
As duas famílias já são duplicadas e a convergência é o item 1 do §Deferido.
Enquanto não sai, `-on-tint` é o único par que existe para os dois.

**2. Opacity modifier no texto — 3 call-sites a 3,55:1.**
`text-[var(--surface-muted-foreground)]/70` dá 3,59 light / 3,55 dark
(`ReportToc:186`, `alocacaoCardParts:318`); `/80` dá 4,54/**4,21** dark
(`ReportToc:149`). O gate não modela alpha no foreground.
*Decisão pendente:* o `/70` existe para de-enfatizar entrada de apêndice no
índice — tirar achata a hierarquia. Ou aceita-se o achatamento, ou nasce um
token "dim" que ainda passe AA.

**3. O `axe` descarta `results.incomplete`.**
[`helpers/axe.ts`](../../../../frontend/tests/e2e/helpers/axe.ts) lê só
`results.violations`. Onde o axe não consegue resolver o fundo, o achado cai em
`incomplete` e o gate fica verde por não olhar. Não foi possível medir quantos
`incomplete` a página produz — Playwright não roda neste worktree
(`node_modules` é symlink e o Turbopack recusa), então o tamanho do buraco é
**desconhecido**, não "pequeno".
*Retomar quando:* alguém rodar o spec num ambiente que execute Playwright;
imprimir a contagem de `incomplete` por regra é o primeiro passo.

## Deferido — 2026-08-08 · dono: David Robert

Três itens saíram do escopo com decisão explícita, não por esquecimento.

**1. Convergir `--report-alert-warning-text` para `--semantic-alert-on-tint`.**
Fora por decisão do dono em 2026-08-08. O S_parecer **passa hoje** (4,81:1 sobre
o tint de 6%; 4,84:1 sobre `--report-alert-warning-bg`), então é margem fina, não
defeito. Os 5 call-sites de card que reprovavam são conjunto **diferente** e já
foram corrigidos sem tocar na calibragem aprovada na [[A40.l22]].
*Retomar quando:* houver mudança visual planejada no S_parecer, ou se o âmbar
aparecer sobre fundo novo — `--surface-muted` dá 4,18:1 com o token atual.
*Nota:* a forma recomendada é aliasar por `var()`, o que exige alargar o
`tokenMap` de `parecerToneContrast.test.ts` (hoje casa só `#[0-9A-Fa-f]{6}`) e
resolver indireção também no gate.

**2. Baselines visuais não regeneradas.** O job `frontend-visual` é opt-in por
label e baseline gerada em macOS não vale contra o runner Linux. A migração
mexe em cor de texto em ~8 seções.
*Retomar quando:* alguém rodar o PR com label `visual`. Referência de custo: no
badge Fator-R o delta foi 699px de 887.184 (0,0008), muito abaixo do
`maxDiffPixelRatio: 0.025` — a baseline sobreviveu. **Meça antes de assumir que
precisa rebaselinar**, e se precisar, gere no runner Linux e **olhe as PNGs**:
baseline commitada sem inspeção congela estado quebrado e o gate vira fail-open.

**3. 24 dos 37 membros de `report_palette` sem consumidor.** A varredura passou
por dois deles (`--report-surface-warning-text`, `--report-badge-yellow-text`) e
a proposta inicial era deletá-los. **Recusado:** `report_palette` é espelho
deliberado do `EXEMPLO_DE_RELATORIO.html` ([[ADR-117]] diz isso na própria
`_description`), e apagar 2 de 24 por acidente de auditoria de contraste
orfanaria `--report-badge-yellow-bg` do seu par e escolheria arbitrariamente
dois membros de famílias simétricas.
*Retomar quando:* houver decisão de política — `report_palette` deve espelhar o
mockup ou refletir o uso? É lane própria, com [[ADR-117]] na mesa. Os outros
dois "mortos" encontrados de passagem: `--report-alert-success-text` e
`--report-gradient-card-feature` (este citado como fundo do `variant="feature"`,
que na verdade resolve para `var(--surface-card)`).
