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
