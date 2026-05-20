---
id: ADR-228
type: adr
title: "Operational gates pós-A11: closure code-complete da sprint + drills diferidos para go-live"
status: Proposto
phase: A11
date: "2026-05-20"
relates_to:
  - "[[ADR-170]]"
  - "[[ADR-171]]"
  - "[[ADR-172]]"
  - "[[ADR-173]]"
  - "[[ADR-174]]"
  - "[[ADR-175]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 228"
  - "A11 closure"
  - "code-complete closure"
  - "operational gates"
tags:
  - area/ops
  - area/process
  - phase/a11
  - status/proposto
  - type/adr
---

# ADR-228 — Operational gates pós-A11: closure code-complete + drills diferidos

## Contexto

Sprint A11 (Platform Review Execution) contém 32 tasks distribuídas em 6
waves. ~85% das tasks pendentes são puro código + teste + ADR — fecham
em `main` com CI verde sem depender de plataforma rodando em produção
pública. Mas 5 tasks têm **passo operacional** que só é genuinamente
validável em ambiente real (não localhost, não staging com dados sintéticos):

| Task | O que código faz | O que só drill real prova |
|---|---|---|
| **W3-T02** | Adapter Resend + endpoints verify/reset + templates | SPF/DKIM/DMARC nos DNS de `mathoms.ai`; email chegando em provedor real (Gmail/Outlook/iCloud) sem cair em spam |
| **W4-T01** | Script `backup_postgres.sh` + `r2_adapter.py` + cron | `pg_dump` real → R2 (eu-central) → `restore_drill.sh` reconstroi DB e 5 queries-canário batem; RPO/RTO medidos |
| **W4-T02** | Workflow GHCR + Coolify webhook + smoke curl | Webhook dispara em push pra `main`, imagem SHA-pinned sobe, `/health` responde 200, rollback automático testado em falha sintética |
| **W4-T03** | Sentry SDK em backend + frontend + Celery + ErrorBoundary | Erro real (canário intencional) chega no projeto Sentry EU; PII strip funcionou; alert rule disparou no Slack |
| **W4-T05** | UptimeRobot + Instatus + Sentry burn-rate rules | Drill de incidente: pager dispara, status page atualiza, postmortem rascunhado dentro de SLA |

Sem prod pública (cutover `dev.mathoms.ai` → `app./api.mathoms.ai`
pendente), drills acima ficam pendentes sine die. Duas opções de
fechamento:

1. **Aguardar go-live** — encerramento A11 atrelado a wall-clock de prod.
   Trava 32 tasks em `in_progress` por semanas/meses; cria pressão pra
   pular gates ("já tá tudo verde, fecha logo"); mistura débito real
   (5 drills) com débito nominal (27 tasks já em `main`).
2. **Fechar code-complete + rastrear drills separado** — sprint fecha
   quando 32 PRs estão em `main` + ADRs 170-175 `Decidido`; drills
   viram compromisso explícito numa ADR própria, com prazo atrelado ao
   go-live (não ao calendário).

Opção (1) é o anti-padrão "definition of done escorrega quando o
contexto aperta". Opção (2) preserva honestidade sem travar progresso —
**desde que** o débito operacional seja rastreável e nominalmente
atribuído, não "esperança de não esquecer".

## Decisão

**Fechar A11 em modo code-complete** assim que as 32 tasks estiverem
em `main` com CI verde e ADRs 170-175 em `Decidido (Sprint A11.W<N>)`.
Os 5 gates operacionais ficam rastreados nesta ADR e **não bloqueiam o
encerramento da sprint**.

### D1 — Definition of Done revisada

Sprint A11 fecha quando:

1. 32 tasks PLATFORM_REVIEW em `main` (checkbox ✅ no Index do PLAN).
2. Demais lanes A11 (cat-overrides-ux, report-publication, planner-review
   atos relevantes) em `main`.
3. ADRs 170-175 com `status: Decidido (Sprint A11.W<N>)` — flippadas no
   merge do PR correspondente.
4. Coverage gaps E0/E1.5c/E7-crossval/E7-apply explicitamente revisados
   ou adiados via ADR para A12+.
5. Plano arquivado via `git mv docs/plan/PLATFORM_REVIEW/_README.md
   docs/archive/PLATFORM_REVIEW_PLAN-YYYY-MM-DD.md` + entrada em
   `docs/archive/README.md`.
6. `sprint_status: shipped` no MOC.

**Drills operacionais (D2) não entram nessa lista** — são gate de
go-live, não de A11.

### D2 — Gates operacionais explícitos

| Gate | Task origem | Owner | Evidence esperada |
|---|---|---|---|
| **G1 — Email real entregando** | W3-T02 | sre-devops | Print de email-verify chegando em 3 provedores (Gmail, Outlook, iCloud) sem spam folder; SPF/DKIM/DMARC pass; log Resend dashboard |
| **G2 — Restore drill real** | W4-T01 | sre-devops | Log de `restore_drill.sh` reconstruindo DB de snapshot R2; 5 queries-canário com row counts esperados; RPO/RTO medidos e anexados em `docs/reference/runbooks/disaster_recovery.md` (criado pelo PR de W4-T01) |
| **G3 — Coolify deploy real** | W4-T02 | sre-devops | Push em `main` dispara webhook; imagem SHA-pinned sobe; `/health` 200; rollback automático provado com falha sintética intencional (PR de teste + revert) |
| **G4 — Sentry capturando produção** | W4-T03 | sre-devops | Erro canário intencional (`raise RuntimeError("sentry-canary")` em endpoint protegido) chega no projeto Sentry EU com PII strippado; alert dispara em Slack |
| **G5 — Drill incidente full-chain** | W4-T05 | sre-devops | UptimeRobot detecta down sintético; Instatus atualiza status; oncall recebe page; postmortem rascunho em até 24h; runbook §incidentes ratificado |

**Prazo:** **até 7 dias corridos** após `app.mathoms.ai` começar a
servir tráfego real (cutover `dev.mathoms.ai` → `app.mathoms.ai`).
Janela curta proposital — drill atrasado vira drill esquecido.

### D3 — Closure desta ADR

ADR-228 flippa para `Decidido (Sprint A<N>)` quando os 5 gates estão
✅ evidenciados. Tracking via 5 sub-PRs (um por gate) ou 1 PR consolidado
que atualize esta ADR + runbooks pertinentes.

Se algum gate falhar no drill (ex.: restore drift, Sentry sem capturar,
email em spam), abre incidente + abre ADR específica de remediação —
**não** flippa esta ADR até resolução. Failure mode é normal e esperado;
é exatamente pra isso que drills existem.

## Alternativas consideradas

### (A) Aguardar go-live para fechar A11

Honesto, mas trava 32 tasks code-complete em `in_progress` por semanas
indefinidamente. Cria pressão para pular gates quando wall-clock aperta.
**Descartada:** custo de não fechar a sprint é maior que ganho marginal
de rigor.

### (B) Fechar A11 sem ADR de tracking; drills ficam só em runbook

Mais leve. **Descartada:** runbook não tem dono nominal nem prazo;
débito vira "esperança". CLAUDE.md §"Concluído" exige rastreabilidade
explícita.

### (C) Mover as 5 tasks para Sprint A<N+1> "Production launch"

Funciona, mas reabre escopo: tasks foram codadas em A11; renomear sprint
de origem distorce o changelog. **Descartada:** tasks ficam em A11
(código+ADR), gates ficam em ADR-228 com sprint owner posterior.

## Consequências

**Positivas:**

- ✅ A11 fecha quando trabalho técnico está feito, sem inflar prazo de
  sprint por dependência operacional.
- ✅ Débito operacional fica explícito, com dono, evidência esperada e
  prazo atrelado ao único evento que destrava (go-live).
- ✅ Padrão reutilizável: futuras sprints com componente operacional
  (auth-launch, billing-launch, etc.) podem aplicar mesmo split.

**Negativas:**

- ⚠️ Cria dois conceitos de "feito": code-complete (A11) e
  go-live-validated (ADR-228). Comunicação interna precisa ser clara
  pra não confundir stakeholder ("tá pronto" ambíguo).
- ⚠️ Risco residual: se ADR-228 não fechar dentro do prazo de 7d
  pós-cutover, vira débito esquecido. Mitigado por (a) prazo curto
  proposital, (b) gate de runbook DR exigir restore drill antes de
  considerar prod estável.

**Riscos:**

| Risco | Mitigação |
|---|---|
| Drills viram débito permanente "vamos fazer depois" | Prazo 7d corridos pós-cutover é hard gate; passou disso, abre incidente de processo (não engenharia). |
| Stakeholder lê "A11 fechada" e assume prod validada | Documento de release de A11 (changelog + status update) cita explicitamente que gates operacionais são ADR-228 e seguem rastreio próprio. |
| Algum gate revela bug grande (ex.: PII vazando no Sentry, restore corrompido) pós-A11 fechada | Failure mode esperado; abre ADR de remediação no Sprint corrente; ADR-228 permanece `Proposto` até resolução. |

## Gates desta ADR

- **Doc-only no PR de criação:** sem código, sem migration; apenas
  ADR + ajuste DoD do Sprint A11 _README + sub-checkbox operacional
  nas 5 tasks W3/W4 do PLAN-platform-review.
- **Closure:** PR(s) que evidenciem G1-G5 atualizam esta ADR para
  `Decidido` + linkam evidence (screenshots, logs, runbook updates).

## Referências

- [[ADR-170]] — refresh tokens (W3-T03; **não** está em gate operacional
  porque rotação é validável em CI/staging).
- [[ADR-171]] — Fernet rotation MultiFernet (W3-T04; idem — rotação
  drill é em staging, não exige prod pública).
- [[ADR-172]] — stuck-runs heartbeat (W2-T04; validável em staging).
- [[ADR-173]] — LLM budget hard-stop (W3-T01; validável em staging com
  budget=$0).
- [[ADR-174]] — off-site backup R2 (W4-T01 → **G2**).
- [[ADR-175]] — prompt injection defense (W3-T05; validável via fixtures
  adversariais em CI).
- [Sprint A11 MOC](../sprint/A11/_README.md) — Definition of Done
  ratificada por esta ADR.
- [Plano PLATFORM_REVIEW](../plan/PLATFORM_REVIEW/_README.md) — origem
  das 5 tasks com gate operacional.
- CLAUDE.md §"Concluído" — PR mergeado em `main` (squash) com CI verde
  é o marco; esta ADR formaliza o caso onde "feito" tem dois níveis.
