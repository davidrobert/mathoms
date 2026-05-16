---
id: ADR-138
type: adr
title: "Protocolo de supervisão CTO para Sprint A7"
status: Decidido
phase: "Sprint A7"
date: "2026-04-26"
relates_to: ["[[ADR-097]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 138"]
tags:
  - area/persistence
  - area/pipeline
  - area/testing
  - status/decidido
  - type/adr
size_lines: 78
---

# ADR-138 — Protocolo de supervisão CTO para Sprint A7

**Status:** Decidido (Sprint A7) • **Data:** 2026-04-26 • **Relaciona**
[ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy),
[ADR-103](#adr-103--teste-manual-como-gate-antes-de-remoção-do-bridge-a6b5--a6-human),
[CONFIG_CUTOVER_PLAN.md §6](../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md).

**Contexto:** Sprint A7 executa cutover de `config/` para DB com **até 4
agentes paralelos** em Onda 2 (A7.1, A7.2a, A7.2b, A7.4) e cadeia
sequencial em Ondas 1, 3, 4. Sprint atravessa: pipeline read-path,
schema DB, application layer, frontend, eventos, séries temporais,
PII removal.

Nenhuma sprint anterior teve essa combinação de:
1. múltiplos agentes paralelos modificando arquivos disjuntos com risco
   de conflito em `BACKLOG`/`CHANGELOG`/`CLAUDE.md` (hotspots);
2. mudanças que **não podem** quebrar smoke E2E entre ondas;
3. bridges (FileConfigStore, materialize_config) com prazo definido.

Sem governança explícita, lanes paralelas vão produzir merge hell e/ou
regressão silenciosa em prod.

[ADR-103](#adr-103--teste-manual-como-gate-antes-de-remoção-do-bridge-a6b5--a6-human) já estabeleceu
"teste humano como gate" para A6 — funcionou para single-lane. Para
multi-lane paralelo, falta protocolo de quem aprova o quê e quando.

Alternativas:

- **(a) Cada agente auto-aprova.** Modelo do A6g. Funciona para sweep
  cosmético; falha em mudança estrutural cross-cutting.
- **(b) Humano (David) revisa cada PR.** Bottleneck garantido em onda
  com 4 lanes paralelas — ele vira fila.
- **(c) Agente `senior-cto` revisa cada PR + humano supervisiona
  wave boundaries.** Distribui carga: CTO faz revisão técnica
  intra-lane; humano valida fechamento de onda.

**Decisão:** Adotar (c) com 4 gates explícitos (G1–G4) descritos em
[CONFIG_CUTOVER_PLAN.md §6](../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md):

| Gate | Quando | Quem | Output |
|---|---|---|---|
| **G1 — ADR draft** | Antes da 1ª linha de código da lane | CTO | ADR Decidido em DECISIONS.md |
| **G2 — Schema review** | Antes da Alembic migration sair do branch | CTO | "Schema OK" em commit/track file |
| **G3 — PR pré-merge** | Quando agente anuncia "branch pronta" | CTO | APROVADO ou BLOQUEADO + checklist |
| **G4 — Wave boundary** | Antes da próxima onda começar | Humano | Smoke E2E verde + atualização BACKLOG |

CTO pode ser:
- **Humano** (David) durante horário de trabalho.
- **Agente `senior-cto`** invocado via `Agent(subagent_type="senior-cto",
  …)` quando humano não está disponível ou sprint roda em modo
  asyncrônico.

Em ambos os casos, sign-off é registrado:
- Em commit trailer `Reviewed-by: <CTO identifier>` para G3;
- Em BACKLOG status (✅ aprovado / 🚧 bloqueado) para G1, G2, G4.

Critérios de aprovação (G3) — checklist em
[CONFIG_CUTOVER_PLAN.md §6.4](../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md).
Bloqueio retorna lista de itens acionáveis; máximo 2 ciclos antes do
humano intervir (§6.5).

**Consequências:**
- ✅ Multi-agente paralelo viável com revisão centralizada que não
  bloqueia humano em fila.
- ✅ ADRs (G1) escritas antes do código; rationale gravado para
  agentes futuros.
- ✅ Wave boundary explícito (G4) impede onda nova começar sem smoke
  verde.
- ⚠️ Custo de coordenação: agente espera review entre G3 e merge.
  Mitigação: enquanto espera, agente pode pegar lane disjunta.
- ⚠️ Agente `senior-cto` precisa do diff completo + plano +
  acceptance gates como contexto. Prompt template em
  [CONFIG_CUTOVER_PLAN.md §6.3](../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md).
- ❌ Não cobre validação empírica em workspace de cliente real —
  smoke é fixture sintético. Aceito porque F7 ainda não fechou; quando
  fechar, gate G4 ganha smoke shadow em workspace piloto.
