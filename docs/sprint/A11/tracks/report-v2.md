---
id: TRACK-report-v2
type: track
title: "Track Report Premium UI v2 — meta-prompt + roadmap de execução"
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

# Track Report Premium UI v2 — meta-prompt + roadmap de execução

> **Lane ID família:** `report-v2-*` (cada lane tem seu sub-slug)
> **Branch prefix:** `agent/report-v2-<lane>/<yyyyMMdd-HHmm>`
> **Depende de:** Report Premium UI v1 ✅ (10 fases + lanes residuais
> `adr-129-e6-kill`, `report-a11y-finalize`, `report-v1-polish` todas em `main`)
> **Sprint:** Report Premium UI · pós-v1
> **Índice de prompts:** [README.md](../../../../README.md)
> **Fonte de verdade:**
> - [BACKLOG.md — Report Premium UI v2 roadmap](../../../BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml)
> - [plan/REPORT_PREMIUM/_README.md §17 v2 roadmap](../../../plan/REPORT_PREMIUM/_README.md)
> - Auditoria 2026-04-25 (origem do escopo): `_scratch/REPORT_PREMIUM_v2_audit.md`
>   ou recompor via §1 deste prompt.

> **Objetivo (1 frase):** fechar inconsistências e débitos detectados na
> auditoria pós-v1 do Report Premium UI **e** entregar features
> reconhecidas como v2 (DnD real, comparisons/changelog, LLM
> section_summaries, PDF visual diff), em ondas paraleláveis sem
> reabrir o shell entregue na v1.

---

## 1. Por que esta lane existe

A v1 entregou paridade visual com `EXEMPLO_DE_RELATORIO.html` em 10
fases. A auditoria 2026-04-25 confirmou todas as fases ✅ em `main`,
mas catalogou:

- **3 inconsistências** entre BACKLOG/PLAN e código real
  (`comparisons`/`changelog` prometidos `enabled:false` mas ausentes
  do YAML; baselines visuais Linux pendentes de trigger; T2 Aportes
  marcado entregue mas é stub).
- **3 débitos** declarados pelo próprio BACKLOG como adiados
  conscientes (DnD real Kanban, LLM section_summaries em E5,
  comparisons/changelog v2).
- **3 lacunas** que o plano original não enumerou (S5/S6 nunca
  mencionados, score como `as ScoreData` casting, PDF visual diff
  Playwright).

Cada item virou uma lane v2.X com prompt curto. Este meta-prompt
**organiza ondas, paralelização e dependências** para que múltiplos
agentes trabalhem simultaneamente sem colisão.

---

## 2. Ondas + paralelização (resposta canônica)

```
ONDA v2.A — fixes consistência (P0/P1, ~½ dia cada, paraleláveis)
   ├── v2.1  comparisons/changelog placeholders no YAML        [solo]
   ├── v2.2  baselines visuais Linux trigger + commit          [solo]
   └── v2.3  S5/S6 esclarecimento (auditoria + decisão)        [solo]

                          ↓  (v2.A merge antes de v2.B)

ONDA v2.B — débitos visíveis (P1, paraleláveis com cuidado de tipos)
   ├── v2.4  T2 Aportes seção real (precisa decisão de produto) [prompt dedicado]
   ├── v2.5  score como campo top-level no DTO                  [conflita com v2.4]
   └── v2.6  cards/ legacy: deprecate ou migrar                 [solo]

                          ↓  (v2.B merge antes de v2.C)

ONDA v2.C — features reconhecidas v2 (P2, mistas)
   ├── v2.7   DnD real Kanban (@dnd-kit/core)                   [solo]
   ├── v2.9   LLM-driven section_summaries em E5                [solo, requer ADR]
   └── v2.10  PDF visual diff em Playwright                     [solo]

ONDA v2.D — enabler estrutural (sequencial, destrava v2.8)
   ├── v2.D.1 SnapshotChangelogBuilder em pipeline/domain/      [requer ADR]
   └── v2.8   ativar comparisons + changelog no YAML + render   [depende v2.1 + v2.D.1]
```

**Regras de paralelização:**

| Par | Pode rodar simultâneo? | Motivo |
|-----|------------------------|--------|
| v2.1 ↔ v2.2 | ✅ Sim | YAML/BACKLOG vs CI workflow — zero overlap |
| v2.1 ↔ v2.3 | ⚠ Coordenar | Ambas tocam `BACKLOG.md` e `plan/REPORT_PREMIUM/_README.md` — usar protocolo de hotspot do CLAUDE.md (commits atômicos + push imediato) |
| v2.2 ↔ v2.3 | ✅ Sim | Independentes |
| v2.4 ↔ v2.5 | ❌ Não | Ambas mexem em `frontend/src/types/report-analysis.ts` e potencialmente nas mesmas seções — fazer v2.5 antes destrava v2.4 |
| v2.4 ↔ v2.6 | ✅ Sim | Sections vs cards/ — disjuntos |
| v2.5 ↔ v2.6 | ✅ Sim | Types vs cards/ — disjuntos |
| v2.7 ↔ v2.9 ↔ v2.10 | ✅ Sim | Kanban.tsx vs pipeline/E5 vs frontend/tests/e2e — disjuntos |
| v2.8 ↔ qualquer | ❌ Não | Espera v2.1 (placeholder no YAML) E v2.D.1 (builder) |
| v2.D.1 ↔ Onda C | ✅ Sim | Pipeline puro, não toca shell |

**Caminho crítico mínimo (1 agente serial):** v2.1 → v2.D.1 → v2.8.
Tudo o mais é otimização paralela.

**Caminho crítico paralelo (3 agentes):** Onda A em paralelo (~1 dia)
→ Onda B em paralelo (~2 dias) → Onda C+D em paralelo (~3 dias). Total
~6 dias úteis vs ~12 dias serial.

---

## 3. Catálogo de lanes (escopo + arquivos por lane)

### v2.1 — Placeholder `comparisons` + `changelog` no YAML

**Branch:** `agent/report-v2-yaml-placeholders/<ts>`
**Esforço:** S (≤2h)
**Prio:** P0 (cumprir promessa BACKLOG)

**Problema:** [BACKLOG.md:1391-1393](../../../BACKLOG.md) diz que `comparisons` e
`changelog` "foram declarados `enabled: false` no YAML" — `grep` retorna
zero matches em `config/report_layout.yaml`.

**Entrega:**
1. Adicionar em [config/report_layout.yaml](../../../../config/report_layout.yaml)
   nas seções relevantes (S1/S2/S3 + T2/T3/T5 candidatos óbvios) os blocos:
   ```yaml
   - id: "comparisons_<seção>"
     enabled: false
     deferred_until: "v2.D.1 SnapshotChangelogBuilder"
   - id: "changelog_<seção>"
     enabled: false
     deferred_until: "v2.D.1 SnapshotChangelogBuilder"
   ```
2. Rodar `python3 dev/codegen_report_layout.py` e comitar
   `frontend/src/generated/report-layout.ts` +
   `backend/app/generated/report_layout.py` no mesmo commit.
3. Confirmar que `MIGRATED_SECTIONS` no [ReportShell.tsx:78](../../../../frontend/src/components/report/ReportShell.tsx)
   ignora itens `enabled:false` (não renderiza).
4. Atualizar BACKLOG removendo a frase "declarados `enabled: false`" se
   ainda houver inconsistência.

**Gate:** `npm run build` + `pytest backend/tests -q` verde + grep
agora encontra os blocos.

---

### v2.2 — Trigger baselines visuais Linux

**Branch:** `agent/report-v2-visual-baselines/<ts>`
**Esforço:** S (≤4h, maior parte é review humano dos PNGs)
**Prio:** P0 (gate empírico de a11y depende disso)

**Problema:** [BACKLOG.md:660](../../../BACKLOG.md) diz que a lane
`report-a11y-finalize` está ✅, mas baselines Linux dos 48 spec tests
[`sections.snapshots.visual.spec.ts`](../../../../frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts)
estão pendentes de trigger manual via `workflow_dispatch`.

**Entrega:**
1. `gh workflow run frontend-visual --ref main -f run_visual=true`
   (ou nome real do workflow — ver [docs/plan/REPORT_PREMIUM/VISUAL_SNAPSHOTS.md](../../../plan/REPORT_PREMIUM/VISUAL_SNAPSHOTS.md)).
2. Baixar artefato com PNGs Linux gerados.
3. Revisar visualmente os 48 PNGs (light + dark × 24 seções) — qualquer
   render quebrado, `npm run test:e2e -- --update-snapshots` local
   **não** resolve; precisa investigar a causa.
4. Commit dedicado `test(visual): commit Linux baselines (24 sections × 2 themes)`
   adicionando os PNGs a `frontend/tests/e2e/reports/__snapshots__/`.
5. Validar empiricamente: PR descartável que muda 1 cor → CI deve
   falhar. Reverter, citar PR no commit final.

**Gate:** PR descartável valida regressão; lane fechada no BACKLOG.

---

### v2.3 — S5/S6 esclarecimento

**Branch:** `agent/report-v2-s5-s6-clarification/<ts>`
**Esforço:** S (≤4h, mais investigação que código)
**Prio:** P1 (não bloqueia mas confunde quem lê o plano)

**Problema:** [plan/REPORT_PREMIUM/_README.md §9.2](../../../plan/REPORT_PREMIUM/_README.md)
lista ordem de migração "S1→S2→S3→**S7**→S4→S8→S9→S10" — pula S5 e S6.
Não há `S5*Section.tsx` nem `S6*Section.tsx`. Status ambíguo.

**Entrega:**
1. Auditoria do `EXEMPLO_DE_RELATORIO.html` — `grep -n 'id="S[0-9]"'`
   ou similar — confirmar quais IDs existem no exemplo.
2. Auditoria do `config/report_layout.yaml` — quais IDs estão
   habilitados na seção `estrategico:`.
3. Decisão (registrar como ADR-13X ou nota em PLAN §17):
   - **(a)** S5/S6 nunca existiram no exemplo — corrigir nomenclatura
     no plano (atualizar §9.2 para refletir que pulou intencionalmente).
   - **(b)** S5/S6 existiam e foram fundidos em S4/S7 — documentar
     mapeamento em PLAN §17 e em comentário no YAML.
   - **(c)** S5/S6 existiam e foram esquecidos — virar lane nova
     `report-v2-s5-s6-implement` (escopo separado, fora desta lane).
4. Atualizar PLAN §9.2 + BACKLOG §Report Premium UI com a decisão.

**Gate:** Decisão documentada; ambiguidade resolvida em ≤2 docs.

---

### v2.4 — T2 Aportes seção real

**Prompt dedicado:** [track_report_v2_t2_aportes.md](report-v2-t2-aportes.md)
**Branch:** `agent/report-v2-t2-aportes/<ts>`
**Esforço:** R (1-2 dias)
**Prio:** P1 (stub marcado entregue é confuso)

Lane com decisão de produto + possível extensão de E5. Ver prompt
dedicado.

---

### v2.5 — `score` como campo top-level no DTO

**Branch:** `agent/report-v2-score-dto/<ts>`
**Esforço:** S (≤4h)
**Prio:** P2

**Problema:** [report-analysis.ts:93-98,187-197](../../../../frontend/src/types/report-analysis.ts)
define `ScoreData` mas `ReportAnalysisData` não expõe campo `score` direto.
Seções fazem `as ScoreData` casting (ex.:
[S10SinteseSection.tsx:22](../../../../frontend/src/components/report/sections/S10SinteseSection.tsx)).
Bypassa `no-explicit-any` mas viola spirit do CLAUDE.md §Tipos.

**Entrega:**
1. Adicionar `score?: ScoreFullData` em `ReportAnalysisData`.
2. Garantir backend produz o campo (verificar
   [backend/app/generated/report_layout.py](../../../../backend/app/generated/report_layout.py)
   e/ou pipeline `financial_score_calculator`).
3. Substituir `as ScoreData` por acesso direto em
   `S10SinteseSection.tsx` e qualquer outro callsite.
4. Rodar `pytest backend/tests -q && cd frontend && npm test -- --run`.
5. Atualizar OpenAPI snapshot se mudou contrato:
   `make update-openapi-snapshot`.

**Gate:** Zero `as ScoreData` em `frontend/src/components/report/`;
build + testes verdes.

**Conflito:** Se v2.4 também mexer em `report-analysis.ts`, fazer v2.5
**antes** de v2.4 (ordem: v2.5 → v2.4).

---

### v2.6 — `cards/` legacy: deprecate ou migrar

**Branch:** `agent/report-v2-cards-cleanup/<ts>`
**Esforço:** R (1 dia)
**Prio:** P2

**Problema:** [frontend/src/components/report/cards/](../../../../frontend/src/components/report/cards)
coexiste com `ui/`. Cards lá (`ConsumoConscienteCard`,
`EquilibrioCerbasiCard`, `OrcamentoProspectivoCard` etc.) são pré-Fase 3
e não usam os primitivos `Card/Alert/Badge` de `ui/`. 14 arquivos.

**Entrega:**
1. Auditar quais cards de `cards/` ainda têm consumidores (grep
   `from "../cards"` em sections/).
2. Decisão registrada em ADR ou comentário no PLAN §17:
   - **(a) Migrar** cada card para `ui/` (renomear + atualizar imports).
   - **(b) Deprecar** mantendo como wrappers de `ReportCard` (sem mexer
     em consumidores, baixo risco).
   - **(c) Aceitar legacy** — adicionar comentário em
     `cards/_registry.ts` explicando que é histórico pré-Fase 3 e
     fechar a inconsistência via doc.
3. Executar a opção escolhida.

**Gate:** decisão em `_registry.ts` + opcionalmente migração
mecânica.

**Conflito:** se outra lane editar arquivos em `cards/`, coordenar.

---

### v2.7 — DnD real Kanban (@dnd-kit/core)

**Branch:** `agent/report-v2-kanban-dnd/<ts>`
**Esforço:** R (1-2 dias)
**Prio:** P2

**Problema:** [BACKLOG.md:1385-1387](../../../BACKLOG.md) declara que `@dnd-kit/core`
não foi adicionado; primitivo
`frontend/src/components/report/ui/kanban/` usa
botões "mover para coluna X" em vez de drag-and-drop.

**Entrega:**
1. `cd frontend && npm install @dnd-kit/core@^6 @dnd-kit/sortable@^8`.
2. Refatorar `Kanban.tsx` para usar `<DndContext>` + `<SortableContext>`
   por coluna; manter API `onMove(id, to)` para não quebrar
   `frontend/src/components/report/sections/TaticoSections.tsx`.
3. Manter botões mobile (`<767px`) — DnD não funciona bem em touch sem
   long-press; documentar fallback em comentário.
4. Adicionar testes Vitest unitários + Playwright `@critical` em
   `frontend/tests/e2e/reports/kanban.@critical.spec.ts` cobrindo
   drag-drop entre colunas.
5. Confirmar PATCH `/v1/.../kanban/:id` continua funcionando após
   reorder (server-side `ordem` field).

**Gate:** Suíte E2E `@critical` verde + bundle size <50KB delta.

---

### v2.9 — LLM-driven `section_summaries` em E5

**Branch:** `agent/report-v2-llm-summaries/<ts>`
**Esforço:** O (3-5 dias — primeiro uso de LLM em E5)
**Prio:** P2

**Problema:** [BACKLOG.md:1388-1390](../../../BACKLOG.md) declara que LLM em E5
para `section_summaries` foi "adiado; hoje usamos templates
determinísticos em `deriveSectionSummary`". Plano §0.1 #5 prometia
"Visual + data" — eixo parcialmente abandonado.

**Pré-requisitos:**
- ADR nova (ADR-13X) — primeiro uso de Anthropic em E5, decidir:
  cache Redis (TTL 24h?), fallback determinístico se LLM falha,
  custo por relatório, qual prompt template em `config/prompts/`.
- Confirma com dono que `section_summaries` precisa de LLM (não só
  templates melhores).

**Entrega:**
1. ADR-13X em [DECISIONS.md](../../../DECISIONS.md).
2. Service novo `pipeline/domain/services/section_summary_generator.py`
   com Pydantic value object config (não `StageConfig` inteiro — ADR-097).
3. Cache key: `(workspace_id, snapshot_hash, section_id)`.
4. Prompt template em `config/prompts/section_summaries.yaml`.
5. Fallback: se LLM falha, usa `deriveSectionSummary` atual (não quebra
   relatório).
6. Golden tests em `tests/test_e5_section_summaries.py` com fakes
   (não bate na API real em CI).
7. Frontend: `conclusionUtils.ts` lê do snapshot se presente, senão
   deriva.

**Gate:** Goldens verdes + ADR mergeada + custo monitorado em
`fin.classification_telemetry`-style logger.

---

### v2.10 — PDF visual diff em Playwright

**Branch:** `agent/report-v2-pdf-visual-diff/<ts>`
**Esforço:** R (1-2 dias)
**Prio:** P2

**Problema:** [plan/REPORT_PREMIUM/_README.md §11.1](../../../plan/REPORT_PREMIUM/_README.md)
detalha `.chart-print-img` (canvas → PNG fallback). Existe
[report-print.css](../../../../frontend/src/components/report/report-print.css)
mas não há Playwright comparando PDF Chrome contra baseline.

**Entrega:**
1. `frontend/tests/e2e/reports/print.@critical.spec.ts` — usa
   CDP `Page.printToPDF()`, salva PDF, compara contra baseline
   `frontend/tests/e2e/reports/__snapshots__/report.print.pdf.png`.
2. Como PDFs binários têm diff barulhento, **renderizar PDF como PNG**
   via `pdf-to-png-converter` ou `pdf-poppler` e comparar PNG —
   tolerância `maxDiffPixels: 500`.
3. Job CI separado `frontend-print-visual` opt-in via label `print`
   (similar a `frontend-visual` da lane a11y).
4. Baselines geradas em primeiro run; commit dedicado.

**Gate:** PR descartável que muda margem `@page` falha CI; reverter +
citar.

---

### v2.D.1 — SnapshotChangelogBuilder (enabler de v2.8)

**Prompt dedicado:** [track_report_v2_changelog_engine.md](report-v2-changelog-engine.md)
**Branch:** `agent/report-v2-changelog-engine/<ts>`
**Esforço:** O (3-5 dias)
**Prio:** P2

Lane domínio-pesado. Ver prompt dedicado.

---

### v2.8 — Ativar `comparisons` + `changelog` no YAML + render

**Branch:** `agent/report-v2-comparisons-changelog-on/<ts>`
**Esforço:** R (1-2 dias)
**Prio:** P2

**Depende de:** v2.1 ✅ (placeholders existem) **E** v2.D.1 ✅
(builder existe e produz dados).

**Entrega:**
1. Flipar `enabled: false → true` nos blocos do YAML criados em v2.1.
2. Codegen → componentes `<ComparisonBlock>` (já existe em
   [ui/ComparisonBlock.tsx](../../../../frontend/src/components/report/ui))
   passa a ter dados.
3. Componente `<ChangelogList>` (já existe em
   [ui/ChangelogList.tsx](../../../../frontend/src/components/report/ui))
   passa a renderizar real.
4. Atualizar BACKLOG marcando débito #3 como ✅.

**Gate:** Snapshot visual: `<ComparisonBlock>` aparece em S1 quando
existe snapshot t-1; senão, hidden gracefully.

---

## 4. Regras inegociáveis (todas as lanes v2)

- **Não reabra a v1.** Se uma lane v2 tentar refatorar shell/charts/sections
  além do escopo declarado, **pausar e abrir nova ADR** — o shell é
  intocável fora do que cada lane explicita.
- **Branch `agent/report-v2-<lane>/<ts>`** — sub-slug por lane (não use
  `report-premium` que já foi v1).
- **Pre-flight de hotspot** obrigatório quando tocar `BACKLOG.md`,
  `plan/REPORT_PREMIUM/_README.md`, `CHANGELOG.md`, `DECISIONS.md` (CLAUDE.md
  §Hotspots de documentação).
- **Sem `any`/`Dict[str, Any]`** fora de boundary. Sem `float` em
  dinheiro (ADR-090). Sem `git --force`/`--no-verify`/`--amend`
  pushado (CLAUDE.md §Proibido).
- **Endpoint JSON novo** → `response_model` + `make update-openapi-snapshot`
  (ADR-109).
- **Cada lane fecha com:** commit em `main` + CI verde + entrada no
  BACKLOG marcada ✅ + linha no CHANGELOG.

---

## 5. Pickup protocol (uma sessão por lane)

```bash
git fetch origin

# 1. Worktrees locais (agentes ainda não pusharam)
git worktree list

# 2. Branches remotas v2 (agentes que já pusharam)
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short) %(subject)' \
  refs/remotes/origin/agent/report-v2-* | head -10
```

Se sua lane (`v2.1`, `v2.2`...) aparece em `git worktree list` com path
diferente do seu **OU** em `origin/agent/report-v2-<slug>-*` com
commit <24h, **pegue outra**.

Lanes prontas para pickup hoje: **v2.1, v2.2, v2.3, v2.5, v2.6**
(Onda A inteira + 2 da Onda B).

Lanes bloqueadas até pré-requisito: **v2.4** (depende v2.5 idealmente
mas não obrigatório), **v2.8** (depende v2.1 + v2.D.1), **v2.D.1**
(precisa ADR antes), **v2.9** (precisa ADR antes).

---

## 6. Anti-escopo (não fazer aqui)

- **Reabrir Fases 0-10 da v1.** Tudo entregue está intocável fora do
  escopo de cada lane v2.X.
- **Adicionar features não-listadas.** "Seria legal ter live-edit de
  notas multi-usuário" não entra. Abre ADR + nova lane v3 se
  necessário.
- **Refatorar `e6_render.py`/SSR/HTML standalone.** Morto via
  [ADR-129](../../../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).
- **Mover charts para outra lib** (Recharts/D3). Chart.js está
  pago + funcional.
- **Internacionalizar relatório** — escopo de F12 (i18n), não desta
  lane família.
- **Mexer em F11 Confiança/transparência** — sprint paralelo, não
  cruza com v2.

---

## 7. Estimativa total

| Cenário | Tempo total | Agentes ativos |
|---------|-------------|----------------|
| Serial (1 agente) | ~12 dias úteis | 1 |
| 3 agentes paralelos por onda | ~6 dias úteis | 3 (sincronizam entre ondas) |
| 5+ agentes (otimização máxima) | ~5 dias úteis | 3-5 (limitado pelo caminho crítico v2.D.1 → v2.8) |

Caminho crítico real: **v2.1 (½ dia) → v2.D.1 (5 dias) → v2.8 (1.5 dia)**
= ~7 dias. Tudo o mais é folga paralela.

---

## 8. Saída final do v2 (definição de "feito")

Lane "Report Premium UI v2" considerada ✅ quando **todas** as 9 sub-lanes
(v2.1, v2.2, v2.3, v2.4, v2.5, v2.6, v2.7, v2.8, v2.9, v2.10, v2.D.1)
estão ✅ em `main` ou explicitamente movidas para v3 com ADR
justificando.

CHANGELOG receberá entrada consolidada "Report Premium UI v2 — fixes +
débitos + features deferidas" análoga à da v1.
