---
id: A36.l1
type: lane
title: "Boundary-lint proíbe `backend` + inverter escritas de domínio no pipeline"
sprint: A36
status: planned
priority: P1
branch_slug: a36-l1-boundary-lint-backend
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a36
  - status/planned
  - priority/p1
  - area/pipeline
  - area/ci
---

# A36.l1 — `boundary-lint-backend` (ARQ-02 · ARQ-01)

> **Split (revisão 2026-07-10).** Esta lane empacotava um fix-S (o gate) com um
> refactor-M (inverter 3 sinks). São valor/risco diferentes — separadas em duas
> partes. **Parte A** (gate, **P1**, ~1h) fecha o buraco de regressão hoje;
> **Parte B** (inversão, **P2**, follow-up rastreado) é o refactor. O argumento
> original "tudo numa PR (passo 1 deixa CI vermelho)" **se auto-refuta**: o
> allowlist do passo 2 é precisamente a ferramenta para manter o CI verde. O
> split viola menos a regra do CLAUDE.md (>300 linhas / 3+ camadas → quebrar).

## Problema

A dependência circular `pipeline ↔ backend` sobreviveu **quatro auditorias**
porque o fitness function que deveria guardar a fronteira **não a guarda**:
`dev/check_pipeline_boundaries.py:21` só proíbe `fastapi`, `celery` e
`sqlalchemy` — **não** `backend`. Um `from backend.app.services...` novo num
stage passa **verde** no gate de merge (`.github/workflows/ci.yml:360`). (O gate
é um AST-walk que pega **lazy imports dentro de função** também — os 3 sinks já
usam lazy import e seriam pegos; não há atalho "deixar lazy".)

Sinks de escrita de domínio que hoje importam o backend direto (a inverter):

- `pipeline/stages/extract_comprovantes_bens.py:192` — `vehicle_upsert`
- `pipeline/stages/extract_comprovantes_bens.py:223` — `apolice_reconciliation`
- `pipeline/stages/parecer_planejador.py:171` — `parecer_orchestrator`

Entry-points **legítimos** (allowlist permanente, não refatorar — **cabeiam** o
boundary):

- `pipeline/cli_run_stage.py:99,149,189` — injeta session/otel/hydrated context
- `pipeline/live_progress.py:28,60` — bridge de eventos

O incidente de write-lock em prod (2026-05-22, comentado em
`extract_comprovantes_bens.py:191,221`) já foi mitigado por reuso de
`store.session` ([[ADR-256]]); esta lane fecha a **origem** (a fronteira não
enforçada), não só o sintoma. Por isso a Parte B (inversão) é P2 — a raiz já
está contida; o valor agora é **anti-regressão**.

## Escopo — Parte A · gate + allowlist (P1, ship agora)

1. Adicionar `"backend"` a `FORBIDDEN_ROOTS` em `dev/check_pipeline_boundaries.py`.
2. Introduzir mecanismo de **allowlist por arquivo** (~10 linhas): `cli_run_stage.py`
   e `live_progress.py` como **permanentes** (motivo declarado); os 3 sinks de
   domínio **temporários** com tag `# TODO A36.l1-B invert — tracked`.
   `_violations_in_file` consulta o allowlist.
3. Abrir **ADR `Proposto`** (política CLAUDE.md — escopo arquitetural; tightening
   de [[ADR-089]]): o mecanismo de allowlist + o critério reutilizável
   **"cabeia o boundary → allowlist; cruza de dentro do domínio → inverte"**.
4. Adicionar o gate ao `pre-commit` (falha local antes do push), além do CI.

**Resultado:** CI verde, guarda de regressão **ativa hoje**, sem esperar a Parte B.

## Escopo — Parte B · inversão dos 3 sinks (P2, follow-up rastreado)

1. Inverter cada sink como **port injetada no `WorkspaceContext`** — padrão
   maduro já existente (`PropertySupersessionWriter` [[ADR-324]], família
   `llm_*` hooks): `Optional[Protocol]`, backend injeta o concreto,
   `None` degrada graceful em CLI/teste. O concreto carrega a semântica de
   session ([[ADR-256]]) — não reintroduz a contenção.
2. **`parecer_orchestrator` → inverter, não allowlistar.** É um stage de domínio
   (E6) que **cruza** lateralmente para um serviço backend (arrasta budget hooks
   + cross-provider + telemetria) — mesma classe dos hooks `llm_*` que o
   `WorkspaceContext` já injeta. Allowlistar admitiria a violação que a lane
   existe pra fechar. **Preservar os hooks de budget/telemetria ([[ADR-173]])** na
   inversão — regressão silenciosa aqui é cara.
3. Cada inversão em **PR próprio**, removendo a entrada correspondente do
   allowlist no mesmo PR (invariante: allowlist só **encolhe** pós-Parte A).
4. Flippar a ADR da Parte A para `Decidido` ao concluir.

**Fora de escopo:** refatorar os entry-points legítimos; mexer no mecanismo de
session/UoW (já resolvido em [[ADR-256]]).

## Critérios de aceite

**Parte A:**
- `python3 dev/check_pipeline_boundaries.py` acusa qualquer `from backend...`
  novo em `pipeline/**` (PR de teste que adicione `from backend.app.services import x`
  num stage não-allowlistado **falha** o gate).
- Allowlist exige **motivo declarado por arquivo**; os 3 sinks temporários com
  tag de tracking (força o próximo auditor a vê-los).
- CI verde legítimo (allowlist permanente = só os 2 entry-points + 3 temporários).
- ADR `Proposto` mergeada antes do PR de implementação.

**Parte B (por sink):**
- Golden do stage afetado verde (comprovantes_bens, apólice, parecer).
- Entrada de allowlist correspondente **removida** no mesmo PR.
- Inversão do parecer preserva `llm_call_hooks`/budget/telemetria.

**Esforço:** Parte A = S (~1h); Parte B = M. **Origem:** auditoria r4 (ARQ-02, ARQ-01).
