---
id: CHG-2026-05-22-A19-L1-PROTECAO-SHIPPED
type: changelog-entry
date: "2026-05-22"
sprint: A19
lane: "[[A19.l1]]"
adrs: ["[[ADR-240]]"]
summary: |
  feat(adr-240): A19 L1 (card S_PROTECAO — 4º pilar AUVP Proteção Patrimonial)
  entregue em 4 PRs sequenciais (#430, #432, #435, #436). ADR-240 flippada
  Proposto → Decidido (Sprint A19 L1). Schema + analyzer + codegen +
  componente React + extensão E6-parecer + telemetria entregues.
tags:
  - type/changelog-entry
  - sprint/a19
  - status/shipped
  - status/decidido
  - area/report
  - area/methodology
  - methodology/auvp
  - methodology/cerbasi
  - methodology/perini
---

# feat(adr-240): A19 L1 card S_PROTECAO (4º pilar AUVP) shipped

## Sumário

Lane [[A19.l1]] entregue em 4 PRs squash-mergeados sequencialmente em `main` (todos com CI verde). Sprint A19 inteira fechada (lane única).

- **P1** [#430](https://github.com/davidrobert/mathoms/pull/430) — `protecao_patrimonial.schema.json` + 4 fórmulas em `FORMULAS.md` (gate G2) + `ProtecaoAnalyzer` puro (KPIs G/B/C/F) + 20 testes cobrindo 3 cenários G6.
- **P2** [#432](https://github.com/davidrobert/mathoms/pull/432) — `config/report_layout.yaml` ganha seção S_PROTECAO + codegen TS/Pydantic regenerado. Section `enabled: false` até P3 (evita break visual).
- **P3** [#435](https://github.com/davidrobert/mathoms/pull/435) — componente React `S_ProtecaoSection.tsx` + 4 sub-componentes (KPI Hero, Gap Veículos, Gap Qualitativo, Apólices) + tipos TS + 17 testes Vitest.
- **P4** [#436](https://github.com/davidrobert/mathoms/pull/436) — extensão E6-parecer (instrução D10 — proteção patrimonial com regras CRC) + bump `PROMPT_VERSION` 1.1.0→1.2.0 + telemetria `mathoms.relatorio.protecao_rendered` (LGPD-safe) + flip ADR-240 → Decidido + lane shipped.

## ADR

[[ADR-240]] flippada `Proposto → Decidido (Sprint A19 L1)`. Seção `## Entrega — L1 (S_PROTECAO V1)` adicionada com 4 PRs + padrão arquitetural validado + débito conhecido (P3.1 E2E, P2.1 reordenação S3↔S4, V2 vida/saúde funcional).

## Padrão arquitetural validado

- **Domain analyzer puro** (`protecao_analyzer.py`) + **schema JSON** validado em DBArtifactStore.write + **codegen TS/Pydantic** (ADR-076) + **componente React modular** (1 section + 4 sub-componentes) + **telemetria server-side** (emitida no analyzer, não no React).
- **Discriminated Union no payload** antecipa V2 (vida/saúde/rc_familiar/rd_profissional/ap) sem migration breaking.
- **CRC strict** em copy de UI + instrução D10 no parecer LLM (sem prescritivo; sem recomendação de produto).
- **Empty states + degradação graceful** — section retorna null sem dados; sub-componentes têm placeholders próprios.

## Gates ADR-240

| Gate | Status |
|------|--------|
| G1 — ADR-239 entregue antes de A19 | ✅ A18 L1 + L2 shipped; L3 P1+P2 shipped |
| G2 — Fórmulas registradas antes do code | ✅ FORMULAS.md em P1 |
| G3 — Codegen verde | ✅ P2 |
| G4 — Schema validation hook | ✅ P1 (integrado em DBArtifactStore.write) |
| G5 — Degradação graceful sem family_members | ✅ flag_vida=False silencioso |
| G6 — 3 cenários golden | ✅ 20 testes pipeline + 17 Vitest |
| G7 — UI review CRC | ✅ §13 sigilo passou pre-commit |
| G8 — E6-parecer narrativa | ✅ P4 instrução D10 + PROMPT_VERSION bumpado |

## Próximo

Sprint A19 fechada. **Débitos rastreados** (sub-tasks):

- **P3.1** — E2E `@critical` Playwright em `frontend/e2e/protecao.spec.ts` (3 cenários G6).
- **P2.1** — Reorderação S3↔S4 para ordem AUVP completa (visual review explícito).
- **A19 V2** (futuro, condicional) — card vida/saúde funcional + integração com dependentes IRPF E1.6 + Card PJ proteção empresarial (depende ADR-236 BusinessProfile).

A18 L3 (FIPE refresh) tem P1+P2 shipped; P3 hook E5 que enfileira refresh em cache miss é opcional — fica como débito até evidência de necessidade.
