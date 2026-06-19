---
id: ADR-298
type: adr
title: "Ratchet de estilo: metas decrescentes via save-baseline manual + correção da distribuição de dívida (resposta audit r2)"
status: Decidido
phase: "audit-r2 · item 6"
date: "2026-06-18"
relates_to:
  - "[[ADR-114]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 298"
  - "ratchet metas decrescentes"
tags:
  - area/quality
  - area/ci
  - status/decidido
  - type/adr
size_lines: 60
---

# ADR-298 — Ratchet de estilo: metas decrescentes + distribuição de dívida

**Status:** Decidido (audit-r2 · item 6) • **Data:** 2026-06-18 • **Relaciona** [[ADR-114]] (enforcement do ratchet de estilo)

> Rastreado em [[AUDITS-active]] §r2.

## Contexto

A auditoria r2 (`repo-audit-mathoms.ai-2026-06-11-r2`) levantou três pontos de qualidade que, na validação contra o código, ou não são acionáveis ou estavam factualmente errados. Este ADR registra o veredito de forma durável para evitar re-litígio em auditorias futuras.

1. **Queda de nota Qualidade/Arquitetura 4→3.** A r1 julgou sob `claude-fable-5`, a r2 sob `claude-opus-4-8`. A baseline de estilo (`dev/code_style_baseline.json`) e o objeto avaliado não mudaram materialmente entre as duas execuções — a queda é **recalibração de avaliador**, não regressão de código. Uma nota que muda só porque o juiz mudou não é um achado de engenharia acionável.
2. **"Backend limpo, dívida no pipeline legado."** Factualmente incorreto.
3. **Ratchet "congela, não retira" (sem metas decrescentes).** O mecanismo já decresce; faltava registrar a política.

## Decisão

### D1. Política de metas decrescentes do ratchet ([[ADR-114]])

O ratchet (`dev/check_code_style_regression.py`) **já decresce**, por design: após um sweep que reduz ofensores, roda-se `--save-baseline` (com a árvore git limpa) para congelar o novo piso. O gate avisa quando um count caiu abaixo da baseline ("melhoria; sugere atualizar").

**Auto-tightening (baixar a baseline automaticamente a cada run) é rejeitado:** um count transitoriamente baixo (ex.: arquivo temporariamente removido, branch parcial) viraria piso permanente e quebraria um restore legítimo depois. O passo manual após um sweep real é a guarda contra falso-piso. Mantém-se manual.

Exemplo aplicado nesta resposta: o detector P7 ([[ADR-114]]) foi refinado (isenta docstring de módulo) e a baseline congelada 990→527 — decréscimo deliberado via `--save-baseline`.

### D2. Correção da distribuição de dívida

Medição direta (funções > 20 linhas, ADR-114 P1, excluindo testes) no commit desta nota:

| Bucket | God-functions de produção |
|---|---|
| `backend/app/` | **291** |
| `pipeline/` | 168 |
| `scripts/` | 139 |

`backend/app/` carrega a **maior fatia isolada** de funções-longas de produção — `backend/app/tasks/pipeline_task.py` (~1370 linhas) é o 2º maior arquivo do repo. A narrativa da auditoria ("backend limpo; dívida concentrada no pipeline legado") é **refutada**. Priorização de refactor por essa narrativa investiria no lugar errado.

## Consequências

- ✅ Auditorias futuras herdam o veredito sobre a "queda 4→3" (ruído de avaliador) sem re-investigar.
- ✅ Decisão de onde investir decomposição de god-files passa a usar dado medido (backend ≈ pipeline+scripts em peso), não a narrativa.
- ✅ Política do ratchet documentada: decréscimo manual via `--save-baseline` após sweep; auto-tightening rejeitado com rationale.
- ⚠️ Os números de distribuição são um snapshot; recompute com o script ad-hoc em §D2 se precisar do valor corrente.
