---
id: TRACK-report-v1-polish
type: track
title: "Track Report Premium v1 polish — resíduo F13 do Report Premium"
sprint: A11
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a11
  - status/consumed
---

# Track Report Premium v1 polish — resíduo F13 do Report Premium

> **Lane ID:** `report-v1-polish`
> **Branch prefix:** `agent/report-v1-polish/<yyyyMMdd-HHmm>`
> **Depende de:** `adr-129-e6-kill` ✅ (fatia 6/6 mergeada — sem isso, RUNBOOK e ARCHITECTURE descreveriam estado obsoleto)
> **Paralelo com:** `report-a11y-finalize` (independente — esta lane é docs/checklist; a outra é código + CI). Output do `report-a11y-finalize` enriquece o smoke humano desta lane se chegar antes.
> **Conflita com:** qualquer agente editando `CLAUDE.md`, `docs/reference/ARCHITECTURE.md` (§10), `docs/reference/RUNBOOK.md`, `docs/reference/SMOKE_TEST.md`, `docs/CHANGELOG.md`. Pre-flight obrigatório (ver CLAUDE.md §"Hotspots de documentação").
> **Sprint:** Report Premium UI · resíduo Fase 13
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:**
> - [BACKLOG.md — pickup table](../BACKLOG.md#lanes-abertas-agora--pickup-table) (linha `report-v1-polish`)
> - [plan/REPORT_PREMIUM/_README.md §12](../plan/REPORT_PREMIUM/_README.md) (Fase 13 original — itens não absorvidos pela ADR-129)
> - [BACKLOG.md — tabela Report Premium UI](../BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml) (10 fases ✅ + 11/12/13 redirecionadas)

> **Objetivo (1 frase):** consolidar o "anúncio de v1" do Report Premium —
> smoke test humano dedicado, milestone no CHANGELOG, ARCHITECTURE/RUNBOOK
> alinhados com o estado pós-[ADR-129](../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side),
> CLAUDE.md apontando para o plano — fechando os 5 itens da Fase 13 do
> [PLAN §12](../plan/REPORT_PREMIUM/_README.md) que não foram absorvidos pela
> remoção do `e6_render.py`.

---

## Por que esta lane agora

A `adr-129-e6-kill` removeu o renderer HTML server-side (5500+ LOC) e
atualizou docs **diretamente afetados** (CLAUDE.md §Design System,
ARCHITECTURE.md tabela de stages, ROADMAP). Mas o **anúncio de v1** do
Report Premium em si — "10 fases entregues, paridade visual com o
exemplo, único renderer agora" — nunca foi escrito como milestone:

- **CHANGELOG** tem 10+ entradas por fase (F0 → F10), sem o "v1 de
  Report Premium" consolidado.
- **ARCHITECTURE.md §10** ainda descreve a estrutura `frontend/src/`
  pré-Fase 4 (sem `components/report/{ui,charts,sections,shell,kpi,
  cards,utils}` decomposto).
- **RUNBOOK** não tem seção sobre debug da rota `/reports/[id]` (onde
  localStorage de notas/kanban vive, como regerar PDF, como diagnosticar
  shell que não monta).
- **SMOKE_TEST.md** §5.1 cobre print/PDF (F11.3), mas não cobre os
  modos `estrategico`/`tatico`/`usa` que existem desde F4, nem dark/
  light em todas as seções.
- **CLAUDE.md** §"Onde procurar contexto" tem entrada para
  `plan/REPORT_PREMIUM/_README.md` em uma única linha — acessível, mas não
  destaca que é o doc canônico do shell pós-Fase 10.

Fechar essa lane = "Report Premium v1 oficialmente entregue". Sem isso,
um agente novo lendo o repo ainda vê pistas obsoletas (e6_render
referenciado em RUNBOOK, ARCHITECTURE com tree antigo).

---

## ⚠️ Pre-flight obrigatório (CLAUDE.md §Hotspots)

Esta lane toca **5 hotspots de documentação simultaneamente**. Antes de
**qualquer** edit:

```bash
git fetch origin
git log -10 --oneline origin/main -- CLAUDE.md docs/reference/ARCHITECTURE.md \
  docs/reference/RUNBOOK.md docs/reference/SMOKE_TEST.md docs/CHANGELOG.md docs/BACKLOG.md
```

Se algum desses foi tocado nas últimas **30 minutos** por outro autor,
**pause** e anuncie no chat: "report-v1-polish vai editar CLAUDE.md +
ARCHITECTURE + RUNBOOK + SMOKE + CHANGELOG por ~Y min — confirmando
janela exclusiva". Espere 2 min, então execute em **commits atômicos
por hotspot** (não 1 commit gigante misturando 5 arquivos), com push
imediato após cada commit. Sequência sugerida:

1. CHANGELOG (mais auto-contido).
2. ARCHITECTURE §10 (atualização de tree).
3. RUNBOOK (seção nova).
4. SMOKE_TEST.md (seção nova).
5. CLAUDE.md (1 linha).
6. BACKLOG (✅ na lane + checkpoint atualizado).

Cada commit independente; rebase + push entre eles.

---

## Regras inegociáveis

- **Docs-only.** Zero edit em `frontend/src/`, `backend/`, `pipeline/`,
  `scripts/`. Se descobrir bug de runtime no caminho, **flag em
  `_scratch/notes/report-v1-polish-followups.md`** e segue — não
  conserta nesta lane.
- **CHANGELOG entrada de v1 é narrativa, não exaustiva.** Não duplique
  os 10+ commits por fase (eles já estão lá). É 1 parágrafo de "o que é
  Report Premium v1, o que ele entrega, link para PLAN".
- **Nada de revisar conteúdo do PLAN.** Se PLAN está desatualizado em
  alguma seção (Delta antigo, Fase 11 não removida fisicamente),
  abre follow-up. PLAN é fonte de verdade para esta lane, não objeto
  de edit.
- **Smoke humano em PT-BR.** Mathoms é PT-BR-first; checklist precisa
  ser legível por dono não-técnico revisando o relatório.
- **Sem CPF, valores reais, nomes de família real** em nenhum exemplo
  do RUNBOOK ou SMOKE_TEST.

---

## Entregas

### 1. CHANGELOG — milestone "Report Premium UI v1"

**Arquivo:** `docs/CHANGELOG.md`

Entrada nova em `[Unreleased]` ou seção dedicada do dia:

```markdown
### Report Premium UI v1 (2026-04-XX)

Marco: shell React `/reports/[id]` atinge paridade visual com
[`EXEMPLO_DE_RELATORIO.html`](../../../plan/REPORT_PREMIUM/EXEMPLO_DE_RELATORIO.html) e se torna
o **único renderer** do relatório.

- **10 fases entregues** (F0–F10) entre 2026-04-XX e 2026-04-XX, do
  discovery aos apêndices A–E. Detalhe por fase: ver tabela em
  [plan/REPORT_PREMIUM/_README.md §X](plan/REPORT_PREMIUM/_README.md) ou em
  [BACKLOG.md › Report Premium UI](BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml).
- **Renderer HTML server-side descontinuado** via
  [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side):
  React é único renderer; PDF via Playwright é único export server-side.
  Aposentadoria executada na lane `adr-129-e6-kill`.
- **Resíduos abertos:**
  [`report-a11y-finalize`](BACKLOG.md#lanes-abertas-agora--pickup-table) (gate axe-core/Lighthouse) e
  esta lane (`report-v1-polish`).

ADRs relacionadas: ADR-076, ADR-117, ADR-118 ... ADR-124 (superseded),
ADR-129. Commits principais por fase: ver tabela em BACKLOG.
```

Confira datas exatas via `git log` antes de fixar.

### 2. ARCHITECTURE §10 — tree atualizado

**Arquivo:** `docs/reference/ARCHITECTURE.md`

Localizar §10 (estrutura de diretórios). Atualizar bloco
`frontend/src/components/report/` para refletir tree real pós-Fase 10.
Comando para baseline:

```bash
tree -L 2 frontend/src/components/report/  # ou Glob: "frontend/src/components/report/**/*.{tsx,ts}"
```

Adicionar 1 parágrafo curto: "shell decomposto em primitivos
(`ui/`), Chart.js wrappers (`charts/`), seções por modo
(`sections/`), shell composicional (`shell/`), KPIs reutilizáveis
(`kpi/`), cards comuns (`cards/`), utilitários (`utils/`). Provider
de modo: `ReportModeProvider` (dinâmico) +
`StaticReportModeProvider` (SSR/standalone — ver
[ADR-124 §Onda 11.1](DECISIONS.md#adr-124-scriptse6_renderpy-aposentado-em-favor-de-ssr-standalone-do-next))".

### 3. RUNBOOK — seção "Debug da rota `/reports/[id]`"

**Arquivo:** `docs/reference/RUNBOOK.md`

Seção nova (ordem sugerida: depois de "Pipeline troubleshooting",
antes de "DB ops"). Conteúdo:

- **Como abrir o relatório em dev** — porta 3000, fluxo de auth, fixture
  ou workspace seed.
- **localStorage do shell:** chaves usadas (notas, kanban, modo, tema),
  como inspecionar e limpar via DevTools, como resetar para baseline.
- **Regerar PDF via Playwright** — endpoint `/v1/.../reports/.../pdf`,
  como acionar manualmente, onde o PDF é cacheado, como invalidar.
- **Shell que não monta** — diagnose: bundle errors, hidratação,
  `useReportData` retornando null, contrato `ReportAnalysisData`
  quebrado pós-pipeline.
- **Modo errado na URL** (`?mode=tatico` etc.) — fallback documentado
  em `ReportModeProvider`.
- **Print não funciona** — `?print=1` setando `data-print-route`,
  `@page` em CSS, troubleshooting de quebra de página.

### 4. SMOKE_TEST — seção dedicada Report Premium

**Arquivo:** `docs/reference/SMOKE_TEST.md` (ou `SMOKE_TEST_HUMAN.md`, o que for
canônico hoje — confira)

Seção nova (cerca de 15-20 itens). Estrutura sugerida:

```markdown
## §X — Report Premium UI smoke (humano)

Pré-condição: workspace com pelo menos 1 relatório gerado (run completa
até E5).

### X.1 Modos
- [ ] `/reports/<id>?mode=estrategico` carrega seções S1–S10 visíveis
- [ ] `/reports/<id>?mode=tatico` carrega seções T1–T6 visíveis
- [ ] `/reports/<id>?mode=usa` carrega seções U1–U4 visíveis
- [ ] Toggle de modo no header preserva hash (#S3) — abrir em #S3,
      trocar modo, hash continua

### X.2 Tema
- [ ] Light/dark toggle persiste após reload
- [ ] Print mode (`?print=1`) usa light forçado

### X.3 Print/PDF
- [ ] Quebra de página em S5 (gráfico não corta)
- [ ] Cabeçalho de família aparece em todas as páginas
- [ ] PDF Playwright sai em A4, hero ocupa 1ª página

### X.4 Colaboração
- [ ] Notas em S1 persistem no localStorage; recarregar mantém
- [ ] Kanban em T6 permite mover card entre colunas
- [ ] Limpar localStorage zera notas+kanban; relatório carrega normal

### X.5 Lineage
- [ ] `ReportSourceStrip` mostra "Consolidado de N documentos"
      coerente com workspace
- [ ] Apêndice A lista runs do pipeline com timestamps
```

Itens exatos calibrados pelo dono — defaults acima são partida.

### 5. CLAUDE.md — destacar PLAN do Report Premium

**Arquivo:** `CLAUDE.md`

Localizar tabela "Onde procurar contexto adicional". Conferir se a
linha apontando para `plan/REPORT_PREMIUM/_README.md` existe (mais provável
que sim — adicionada em fase recente). Se sim, **não duplique**;
ajuste a descrição para refletir que é o doc canônico do shell v1.
Se não existir, adicionar:

```markdown
| Plano de execução — Report Premium UI v1 (paridade React com EXEMPLO_DE_RELATORIO.html, 10 fases ✅) | [docs/plan/REPORT_PREMIUM/_README.md](docs/plan/REPORT_PREMIUM/_README.md) |
```

### 6. BACKLOG — fechar a lane

**Arquivo:** `docs/BACKLOG.md`

- Marca a lane `report-v1-polish` como ✅ na pickup table com link para
  o commit final.
- Atualiza o "Checkpoint de saída" da seção "Report Premium UI" para
  refletir v1 entregue.
- Confere se [PRODUCT.md batch2.5](#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes)
  pode ser fechada agora ou se ainda depende de output desta lane.

---

## Gate de saída

Esta lane é docs-only — não exige CI verde de pytest/npm. Mas exige:

1. `pre-commit run --all-files` verde (PII, paths proibidos, commit
   msg validator) **em cada commit**.
2. Os 5 hotspots editados em **commits atômicos separados**, push
   imediato após cada um.
3. **Revisão visual em PR (ou self-review)** dos 5 docs editados —
   especialmente RUNBOOK, que é prosa nova (não diff de tabela).
4. Smoke humano (item 4) testado pelo dono **uma vez** — para validar
   que os ~15 itens são realistas (não checklist teórico).

**Conclusão da lane:** todos os commits em `origin/main`, lane marcada
✅ no BACKLOG, anunciado no chat: "Report Premium UI v1 oficialmente
entregue (commits `<hashes>`)".

---

## Estimativa

1.5–2 dias de trabalho ativo:

- Item 1 (CHANGELOG): 0.5 dia (caçar datas/commits + redação)
- Item 2 (ARCHITECTURE): 0.25 dia (tree + parágrafo)
- Item 3 (RUNBOOK): 0.5 dia (seção nova, ~80 linhas)
- Item 4 (SMOKE_TEST): 0.25 dia (estrutura + ~15 itens)
- Item 5 (CLAUDE.md): 5 min
- Item 6 (BACKLOG): 0.25 dia (cuidadoso por causa dos hotspots)

**Commits esperados:** exatamente 6 (1 por hotspot + BACKLOG separado),
todos com prefixo `docs(...)`. Push após cada um.

---

## Anti-escopo (não fazer aqui)

- **Editar PLAN do Report Premium.** Se descobrir desatualização,
  abrir follow-up; PLAN é input desta lane, não output.
- **Adicionar features.** "Seria legal documentar X feature de Y" —
  não. Documente o que existe.
- **Refactor de doc não-relacionada** ("vi que tenancy.md também
  tinha...") — fora de escopo. Esta lane fecha resíduo F13, não é
  doc sweep.
- **Edit em SMOKE_TEST.md fora da seção nova.** Não toque §1–§4
  existentes.
- **Recriar conteúdo da `adr-129-e6-kill`.** Aquela lane já anunciou a
  remoção; esta lane referencia, não duplica.
- **Aguardar `report-a11y-finalize`** — ele é paralelo. Se chegar antes,
  cite no smoke (item 4); se não chegar, deixe placeholder explícito
  ("automatizado por axe-core gate quando `report-a11y-finalize`
  fechar — checklist humano provisório").
