---
id: MOC-sprint-a11
type: moc
title: Sprint A11 — Platform review execution
aliases: ["A11", "Sprint A11"]
sprint_status: current
---

# Sprint A11 — Platform review execution (origem 2026-05-06)

> **Status:** in_progress — Wave 1 ✅ entregue (8/8 tasks); Waves 2–6 ☐ aguardam pickup.

## Resumo

Executar os 32 itens consolidados da revisão de plataforma 2026-05-06 — fechar P0 latentes em main (tokens fantasma, regras dormentes, PII em pipeline_artifacts), destravar produção pública (F7B/F7E security + email + backup), e quitar 3 grandes débitos arquiteturais (schemas E5 strict, MLOps universal hooks, F9 cleanup).

**Plano canônico:** [docs/plan/PLATFORM_REVIEW/_README.md](../../plan/PLATFORM_REVIEW/_README.md) — 32 tasks em 6 ondas, 138 findings consolidados, 6 trade-offs CTO registrados, coverage matrix por stage.

**ADRs propostos pela revisão:** ADR-170 (refresh tokens) · ADR-171 (Fernet rotation MultiFernet) · ADR-172 (stuck-runs heartbeat) · ADR-173 (LLM budget hard-stop + LLMCallLog) · ADR-174 (off-site backup R2) · ADR-175 (prompt injection defense) — todos `Proposto` ([entregue em W1-T06](https://github.com/davidrobert/mathoms/pull/92)).

**Especialistas G0:** revisão multi-agente 2026-05-06 (`senior-cto` orquestrador + `data-engineer` + `financial-planner` + `product-designer` + `sre-devops` + `build-vs-buy` em paralelo).

**Princípios não-negociáveis:** (P1) NEXT UP do PLAN.md responde "qual task pegar agora" em <30s — manter atualizado; (P2) ADR `Proposto` antes de PR P0/P1; (P3) coverage gaps explícitos — E0/E1.5c/E7-crossval/E7-apply ficam para próxima revisão (Q3 2026); (P4) decisão CTO em conflito entre agentes registrada em `§Trade-offs registrados` do PLAN.

## Por que esta sprint existe

A revisão multi-agente 2026-05-06 ([PR #92](https://github.com/davidrobert/mathoms/pull/92)) levantou 138 findings que são complementares à Sprint A10 (`goals.json` cutover) — A10 fecha 1 frente específica, A11 ataca o resto da plataforma (security pré-prod, observabilidade, schema hardening, frontend a11y, metodologia financeira). Sem entrada índice no BACKLOG, agente futuro descobriria o trabalho só por arqueologia em `docs/plan/PLATFORM_REVIEW/_README.md`.

**ADR-077 checkbox** (rules-as-code completude) será fechado por Sprint A10, não A11. **A11 destrava após A10 fechar?** Não — sprints são paralelas, owners distintos, coordenação via hotspots compartilhados (DECISIONS.md, CHANGELOG.md, BACKLOG.md, Alembic migrations).

## Lanes

Ver [lanes.md](lanes.md) (tabela histórica) ou [`lanes/`](lanes/). Tracks operacionais em [`tracks/`](tracks/).

## Waves

Mapa de dependências em [waves.md](waves.md) — 6 waves: W1 Hot patches (✅) → W2 Pipeline+DB → W3 Auth+LLM+Email → W4 Production readiness → W5 Frontend+Methodology (paralelo a W6) → W6 Tech debt.

**Esforço total estimado:** ~56 dias trabalho ativo. Wall-clock ~8-10 sprints com 2-3 agentes paralelos por wave.

## Definition of Done

```bash
# Sprint encerrada quando:
# 1. Todas as 32 tasks marcadas ✅ no PLAN.md (Index + cada wave)
# 2. Coverage gaps documentados foram revisados (E0/E1.5c/E7-crossval/E7-apply)
#    OU explicitamente adiados para Sprint A12+ via ADR
# 3. Plano arquivado:
git mv docs/plan/PLATFORM_REVIEW/_README.md docs/archive/PLATFORM_REVIEW_PLAN-YYYY-MM-DD.md
# 4. Esta seção marcada ✅ entregue + entrada em docs/archive/README.md
# 5. Todas as ADRs 170-175 + ADRs novas geradas pelas waves em status `Decidido (Sprint A11.W<N>)`
```

## Coordenação multi-agente A11

- **Pickup checks idênticos** ao Sprint A6/A7/A10. Branches usam prefix `agent/platform-review-w<N>-t<NN>/<timestamp>` (ex.: `agent/platform-review-w2-t01/20260510-0930`).
- **Hotspot principal:** [docs/plan/PLATFORM_REVIEW/_README.md](../../plan/PLATFORM_REVIEW/_README.md) — quando wave fecha, atualizar `frontmatter.ready_tasks` + status na tabela de cada wave + adicionar checkbox ✅ na seção da wave. Manter NEXT UP sincronizado.
- **CTO supervision** segue padrão A7/A10 (4 gates). Wave boundary review obrigatório antes de destravar wave seguinte.
- **Trade-offs registrados:** se discordar de uma decisão CTO em [§Trade-offs registrados do PLAN](../../plan/PLATFORM_REVIEW/_README.md#trade-offs-registrados-decisões-cto), abrir issue antes de implementar conflitando.
