---
id: ADR-068
type: adr
title: "Códigos internos do pipeline nunca vazam na UI"
status: Decidido
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 068"]
tags:
  - type/adr
  - status/decidido
size_lines: 60
---

# ADR-068 — Códigos internos do pipeline nunca vazam na UI

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** O pipeline interno opera em 14+ etapas técnicas (`E0-audit`, `E1.5c`, `E2-llm`, `E3`, `E5.N`, `E7-crossval`, `E7-review`, `E7-apply`, `E6-final`...). Esses códigos faziam sentido para engenharia e operação manual, mas começaram a vazar para a UI:

- Toasts e banners exibiam `"Processando: E3"` ou `"Erro na etapa E1.5c"`
- Botões hardcoded como `"Reprocessar a partir do E3"`
- Texto em `LLMTab` listava `"E1, E1.5, E2-LLM, E7-review"` para o usuário
- `STAGE_DISPLAY_NAMES` (mapa de tradução em `format.ts`) cobria apenas ~70% das etapas; o resto caía no fallback que mostrava o código cru
- Lista vertical de 14 etapas técnicas no `ActiveRunCard` virava ruído cognitivo, não feedback útil

Para um produto fintech B2C cobrando assinatura, expor jargão de pipeline destrói confiança e parece "gambiarra de DevOps".

**Alternativas consideradas:**
- (A) Renomear apenas as strings visíveis sem reagrupar — resolve o vazamento mas mantém 14 itens cognitivamente pesados
- (B) Esconder completamente as etapas individuais — perdemos transparência e capacidade de debug pelo suporte
- (C) **[escolhida]** Tradução completa + reagrupamento em **4 fases narrativas** com **disclosure progressivo** para detalhes técnicos

**Decisão:** Adotar separação rígida entre **camada de observabilidade** (preserva códigos) e **camada de apresentação** (sempre traduzida e agrupada).

### Regras invioláveis

1. **API, WebSocket, banco, logs, telemetria → continuam usando códigos `E*`** (ex: `current_stage="E3"`).
2. **UI, toasts, e-mails, push notifications → nunca exibem códigos `E*`.** Sempre passam por:
   - `stageName(code)` (tradução 1:1) — `format.ts:STAGE_DISPLAY_NAMES`
   - `getPhase(stageOrPhaseId)` (agrupamento em 4 fases) — `pipelinePhases.ts:PIPELINE_PHASES`
3. **Mapa de etapas é exaustivo:** toda etapa que aparece em `current_stage`/`failed_at_stage`/`paused_at_stage`/`stage_logs[].stage` DEVE ter entrada em `STAGE_DISPLAY_NAMES`. Adicionar nova etapa no backend = adicionar entrada no mapa (test `format.test.ts` enumera).
4. **Disclosure progressivo:** etapas técnicas individuais ficam atrás de "Ver detalhes técnicos" (collapsed por default). Quando expandido, cada linha exibe um chip `[E3]` com tooltip "Código interno usado em logs e suporte" — preserva debug sem poluir.
5. **Mensagens de erro centradas em impacto:** `pipelineErrorMessages.ts` mapeia padrões técnicos (timeout, rate limit, password, schema...) → headline + hint user-facing. Stack trace continua disponível via "Ver detalhes do erro".

### Agrupamento em 4 fases narrativas

| # | Fase (UI)                       | Etapas internas                                            | Mensagem ativa                                      |
|---|---------------------------------|------------------------------------------------------------|-----------------------------------------------------|
| 1 | Preparando seus documentos      | E0-audit, E0-route, E0-unlock                              | "Verificando e organizando os arquivos enviados"    |
| 2 | Lendo os dados                  | E1, E1.5, E1.5c, E2, E2-llm, E2-extratos, E2-faturas       | "Extraindo transações, saldos e posições"           |
| 3 | Organizando suas finanças       | E3, E4, E5, E5.N                                           | "Reconciliando, categorizando e calculando patrimônio" |
| 4 | Montando seu relatório          | E6, E6-final, E7-crossval, E7-review, E7-apply             | "Gerando o relatório e revisando consistência"      |

Renderizado como **stepper horizontal de 4 nós** (`PhaseStepper.tsx`) com tooltip educativo por fase. Adicionar nova etapa = adicionar em **uma e apenas uma** fase em `PIPELINE_PHASES`.

**Consequências:**
- ✅ Linguagem coerente e profissional em toda a UI; remove "cara de pipeline interno"
- ✅ Carga cognitiva cai de 14 itens para 4 fases visíveis; detalhes ficam sob demanda
- ✅ Backend, logs e métricas inalterados — debug e observabilidade preservados
- ✅ Adicionar nova etapa exige toque em 2 lugares (mapa + grupo de fase) com lint/teste pegando ausências
- ✅ Mensagens de erro orientam o usuário para o **próximo passo** (ex: "cadastre a senha no Cofre"), não para a stack trace
- ⚠️ Tradução adiciona uma camada que precisa ser mantida sincronizada com o backend
- ⚠️ Para suporte interagir com o usuário, o chip `[E3]` no disclosure técnico precisa estar acessível — documentar em runbook

**Aplicação imediata:**
- `frontend/src/lib/format.ts` — `STAGE_DISPLAY_NAMES` agora exaustivo (19 entradas)
- `frontend/src/lib/pipelinePhases.ts` (novo) — 4 fases + helpers `getPhase`, `phaseOfStage`, `computePhaseStates`
- `frontend/src/lib/pipelineErrorMessages.ts` (novo) — `buildUserFacingError(text, stage)`
- `frontend/src/components/PhaseStepper.tsx` (novo) — stepper horizontal com tooltips
- `frontend/src/app/(app)/pipeline/page.tsx` — `ActiveRunCard` usa stepper + disclosure; `FailedRunCard` usa `buildUserFacingError`
- `frontend/src/app/(app)/config/{LLMTab,PipelineTab}.tsx` — copy reescrito sem códigos
