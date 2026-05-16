---
id: ADR-168
type: adr
title: "Remoção do Modo USA do relatório"
status: Decidido
phase: "A8.4 PR4"
date: "2026-05-06"
relates_to: []
supersedes: ["[[ADR-117]]", "[[ADR-123]]"]
superseded_by: []
aliases: ["ADR 168"]
tags:
  - area/frontend
  - area/report
  - area/testing
  - status/decidido
  - type/adr
size_lines: 45
---

# ADR-168 — Remoção do Modo USA do relatório

**Status:** Decidido (A8.4 PR4) • **Data:** 2026-05-06 • **Supersedes parcialmente** [ADR-117](#adr-117--report-premium-ui-baseline-paridade-com-exemplo_de_relatoriohtml), [ADR-123](#adr-123--notas-t6-e-kanban-t3-persistidos-no-backend) • **Conclui agenda** [ADR-151](#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces).

**Contexto:** O relatório premium tinha **3 modos** historicamente: Estratégico (universal), Tático (curto prazo, removido em ADR-151) e USA (mudança internacional + Green Card EB2-NIW + NCLEX RN — específico do cliente piloto). Modo USA tinha 4 seções (U1 Mudança EUA F1/F2 · U2 Green Card EB2-NIW · U3 NCLEX Roadmap · U4 Simulação Mariana Sem Trabalhar) acopladas a artefatos de prototipagem família-específica (cônjuge enfermeira, processo EB2-NIW, F1/F2). ADR-151 (2026-04-26) já estabeleceu doutrina ao remover Tático: **modos opcionais sem cliente real são lastro** — manter abstração de modo custa em superfície de teste, layout YAML, components React, branches de roteamento e visual snapshots, sem benefício enquanto não há segundo cliente que justifique generalização. Modo USA tem o mesmo perfil de risco e idade.

A regra de domínio "cenário cônjuge sem trabalhar" sobrevive como **capability genérica** (ADR-166 + ADR-167) — chart `cenarios_conjuge` no S3 + bloco APP_C "Cenários de Estresse". Não há nada universal em U1-U4 que justifique manter Modo USA inteiro como abstração.

**Decisão:** Remover Modo USA inteiro do relatório. ReportMode reduz de `'estrategico' | 'usa'` para literal único `'estrategico'`. Toggle de modo permanece como ponto de extensão (mode único hoje, futuro modo internacional generalizado quando segundo cliente justificar — recriar custa ~2-3 dias).

**Alternativas avaliadas (senior-cto, A8.4 / 2026-05-06):**

- (a) Generalizar para "Modo Internacional" (U1 vira "Mudança Internacional Custos") — **YAGNI premium**. Sem segundo cliente real, abstração prematura: Portugal D7? EB-5? Bali nômade? Não dá para validar a forma certa.
- (b) Caminho do meio: deletar U2-U4, manter U1 generalizado — ainda especulativo.
- (c) **Deletar tudo** ✅ — replicar quando cliente real aparecer; ADR-151 já provou que essa é a doutrina correta.

**Consequências:**

- ✅ ReportMode reduzido a 1 valor (`'estrategico'`); ~600 LOC removidos (UsaSections.tsx, tests, snapshots, refs).
- ✅ Cenário "cônjuge sem trabalhar" sobrevive em S3 + APP_C (ADR-166 chave universal + ADR-167 gate).
- ✅ Visual snapshots USA-only (8 baselines U1-U4 × {light, dark}) deletados; CI mais rápido.
- ✅ Test suites E2E (`usaSections.test.tsx`, `sections.snapshots.visual.spec.ts` USA describe, `a11y.@critical.spec.ts` USA describe) deletados/simplificados.
- ⚠️ Recriar Modo Internacional quando segundo cliente justificar custa ~2-3 dias. Aceitável dada a cadência ADR-151.
- ❌ Workspaces que tinham configurado Modo USA via `?mode=usa` deep-link agora caem para Estratégico. Não há cliente em produção nessa condição.

**Critério de aceite (PR4):**

- `grep -ri "U1MudancaEua\|U2GreenCard\|U3Nclex\|U4Simulacao\|selectSections('usa')\|mode === 'usa'" frontend/src/` → 0 hits.
- `frontend/src/components/report/ReportModeContext.tsx::VALID_MODES` reduzido a 1 valor.
- Codegen `python3 dev/codegen_report_layout.py` regenera sem `usa.sections`.
- `pytest backend/tests` verde; `vitest` verde no CI.

**Follow-ups:**

1. Strings/copy USA-related em `config/methodology.md`, `config/report_spec.md`, comentários em código — limpeza final em PR5 (A8.4).
2. Quando segundo cliente internacional aparecer, abrir nova ADR para "Modo Internacional" generalizado, com requisitos validados pelo cliente (não especulação).

> **Nota (2026-05-06):** narrativas órfãs (`custo_fase_f1f2`, `f1f2_visto`,
> `sobra_mensal_f1f2`, `mariana_eua`, `nclex_*`) ainda referenciadas em
> `summaries_narrator.py`, `charts_narrator.py`, `perfil_familia_narrator.py`,
> `e5n_narrativas.py` serão limpas em **Sprint A10 lane A10.1** (cleanup
> débito ADR-168). Plano canônico:
> [archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §2.3](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md).
