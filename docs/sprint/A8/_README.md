---
id: MOC-sprint-a8
type: moc
title: Sprint A8 — Continuação multi-tenant
aliases: ["A8", "Sprint A8"]
sprint_status: done
---

# Sprint A8 — Continuação multi-tenant (aberta após A7 fechar 2026-04-27)

> **Status:** done — todas as lanes fechadas (A8.0 + A8.2 IRPF + A8.3 TRS real entregues; A8.4 Cenários de Estresse com PR0 mergeado em curso; A8.1 MileageProgram aggregate ainda planejada como débito). Sprint encerrada para fins de continuidade — débito remanescente migrado para Sprint A11.

## Resumo

Completar a transição mono-cliente → multi-tenant que A7 começou, modelando entidades cliente-específicas que ficaram fora de A7 (workspace notes, mileage programs, programas de cashback, etc.) como agregados DB-first com API + UI; absorver follow-ups que A7 marcou como débito técnico aceito.

**Princípio herdado de A7:** entidades cliente-específicas em DB workspace-scoped, regras universais em código + ADR. `storage/<ws>/notes/` é caminho transitório para conteúdo que ainda não tem schema DB justificado.

**ADRs canônicas:** ADR-149 (formaliza trade-off `config/report_layout.yaml` permanece como asset de produto), ADR-157 (schema IRPF completo, stage `extract_irpf_full`), ADR-164 (carteira de renda + TRS efetiva), ADR-165/166/167 (cenários de estresse — em PR0).

## Lanes

Ver [lanes.md](lanes.md) (tabela histórica) ou [`lanes/`](lanes). Tracks operacionais em [`tracks/`](tracks).

## Waves

> Sprint sem ondas paralelas formais. Ver [waves.md](waves.md) para registro mínimo.

## Lanes adicionais (escopo a fechar)

- Programas de cashback / pontos de cartão de crédito (similar pattern a MileageProgram).
- Notas de planejamento livre (caderno digital workspace-scoped — mais flexível que Decision aggregate).
- Reformulação do modelo de "famílias com >2 membros" (premissa atual: titular + cônjuge fixo — ADR-145 explicita).
- Migração de `config/report_layout.yaml` para outside-`config/` (requer reescrever `dev/codegen_report_layout.py` + `backend/app/services/config_defaults.py` API defaults). Próxima decisão estrutural; provavelmente ADR novo.

## Fontes canônicas

- [docs/plan/CENARIOS_ESTRESSE/_README.md](../../plan/CENARIOS_ESTRESSE/_README.md) — plano A8.4.
- Track IRPF: [`irpf-full-schema.md`](../A11/tracks/irpf-full-schema.md), [`irpf-full-schema-goldens.md`](../A11/tracks/irpf-full-schema-goldens.md), [`irpf-full-schema-ui.md`](../A11/tracks/irpf-full-schema-ui.md).
