---
id: F11.1
type: lane
title: "Mental model: “vida financeira” × “relatório deste mês”"
sprint: F11
status: shipped
priority: P1
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f11
  - status/shipped
  - priority/p1
---


# F11.1 — Mental model: “vida financeira” × “relatório deste mês”


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.1a | **Arquitetura de informação:** `/plano`, metas, tarefas e cofre de contexto = eixo **estratégico**; Documentos → Pipeline → Relatório = eixo **operacional do período**. Revisar labels do nav, títulos de página e breadcrumbs para não misturar os dois. | P1 | 6h | ✅ Nav agrupado (Plano de vida / Fechamento do período / Conta) em `AppShell.tsx` |
| F11.1b | **Empty states e CTAs:** primeiro uso empurra “gerar primeiro relatório”; usuário com relatório já pode ver CTA secundário para “ajustar metas / plano”. Sem dead-end em `/dashboard` ou `/reports`. | P1 | 4h | ✅ Links secundários para `/plano` em empty states de Dashboard e Relatórios; copy do dashboard empty ajustada |
| F11.1c | **Copy guidelines** curtas no `docs/` ou comentário de design: quando falar “mês”, “período”, “projeção” vs “patrimônio alvo”. | P2 | 2h | ✅ [COPY_GUIDELINES.md](../../../reference/COPY_GUIDELINES.md) |
