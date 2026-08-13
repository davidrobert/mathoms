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
própria cor"). **Os dois primeiros fecharam** no PR
[#1434](https://github.com/davidrobert/mathoms/pull/1434); ficam registrados
porque a medição de origem é o que justifica o gate novo.

**1. ~~Cor semântica como foreground sobre o card liso~~ — fechado (#1434).**
O âmbar (`--semantic-alert` e os alias, mesmo hex) dava **2,06:1** sobre
`--surface-card` e **1,88:1** sobre `--surface-muted` — não há fundo neutro da
paleta onde ele sirva de texto. Eram **14 call-sites** (8 no relatório, 6 em
telas do app), não os 6 que a primeira varredura viu: o gate novo achou o resto.
Dois são **ícone** e reprovavam até o limiar de 3:1 de 1.4.11.
Escolhido `--semantic-alert-on-tint` e não `--report-alert-warning-text`: muda
**só o tema light** (no dark o par é alias da base), é global em vez de escopado
a `[data-report-scope]`, e não mexe na convergência das duas famílias âmbar, que
segue sendo o item 1 do §Deferido.

**2. ~~Opacity modifier no texto~~ — fechado (#1434).**
`text-[var(--surface-muted-foreground)]/70` dava 3,55–3,59:1 nos dois temas
(`ReportToc`, `alocacaoCardParts`); `/80` dava 4,21 no dark. Nos três o alfa era
sinal **secundário** com um primário independente já presente (o apêndice tem
grupo próprio no índice; o "/ alvo" tem o próprio rótulo), então sair não custou
hierarquia. Se a de-ênfase for pedida de volta, a resposta é um token "dim" que
passe AA — aí sim é decisão de design.

Os dois viraram [`dev/check_foreground_contrast.py`](../../../../dev/check_foreground_contrast.py),
irmão do gate de tint: mede contra o fundo **declarado na linha** quando existe
(texto branco em botão sólido é correto e daria 1,00:1 contra o card) e contra os
dois neutros quando não. O conjunto ruim é derivado da paleta; a curadoria fica
no inverso, em 2 listas com checagem de staleness.

**3. O `axe` descarta `results.incomplete` — 65 nós por tema, medidos.**
[`helpers/axe.ts`](../../../../frontend/tests/e2e/helpers/axe.ts) lê só
`results.violations`. O que o axe não consegue decidir cai em `incomplete` e o
gate fica verde por não olhar. **Medido em 2026-08-13** (probe com a fixture
`medium`, chromium, os dois temas — `violations=0` nos dois):

| regra | impacto | nós | motivo dominante |
| --- | --- | --- | --- |
| `color-contrast` | serious | 46 | 22× fundo em gradiente · 16× texto curto demais · 3× só não-texto · 3× nó de imagem · 2× sobreposto |
| `aria-prohibited-attr` | serious | 14 | sem mensagem |
| `aria-valid-attr-value` | critical | 5 | `aria-describedby="_r_a_"` (e 4 irmãos) apontando para ID ausente do DOM |

**As 5 do `aria-valid-attr-value` são benignas — verifiquei depois de afirmar o
contrário.** São `TooltipTrigger` do Base UI em
[`ReportActions.tsx`](../../../../frontend/src/components/report/shell/ReportActions.tsx):
o `TooltipContent` só monta quando o tooltip abre, então o `aria-describedby`
aponta para ID inexistente enquanto fechado. É o desenho da lib, e cada botão
tem `aria-label` explícito ("Ocultar índice", "Imprimir ou salvar PDF") — a
descrição é redundante, não o nome acessível. O `incomplete` aqui está
**correto**. (Duas correções minhas de passagem: a página **tem** 2 elementos com
`shadowRoot`, e são 6 `aria-describedby` pendurados no documento inteiro contra 5
dentro do `[data-report-scope]`.)

Das 46 de contraste, ~22 são fundo em gradiente (incerteza real) e ~22 são ruído
(caractere único, ícone).
*Retomar quando:* virar lane própria. **Não** basta falhar em tudo — as 65 do
retrato de hoje são benignas ou ruído, então ligar o `incomplete` inteiro
nasceria vermelho e seria desligado na mesma semana. O valor está no
**delta**: congelar a contagem por regra e falhar quando ela subir, que é o
sinal de "apareceu caso novo que o axe não consegue decidir". O buraco real é
que hoje esse número não é nem observado.

*Nota de método:* a versão anterior deste item dizia que Playwright não roda
neste worktree. **Falso** — era memória vencida de outra sessão; `node_modules`
é diretório real e o `a11y.@critical.spec.ts` roda em 46s (20 testes, verde). O
que atrapalha é o `webServer` do `playwright.config.ts` com `url` fixo em 3000 e
`reuseExistingServer: !CI`: com um servidor de outro worktree na 3000, o
Playwright **reusa o servidor errado** em silêncio. Use
`PLAYWRIGHT_SKIP_WEB_SERVER=1` + `PLAYWRIGHT_BASE_URL` numa porta livre.

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
