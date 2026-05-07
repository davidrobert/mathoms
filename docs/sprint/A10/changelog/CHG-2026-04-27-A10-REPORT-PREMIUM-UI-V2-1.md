---
id: CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-1
type: changelog-entry
date: "2026-04-27"
sprint: A10
adrs: ["[[ADR-093]]", "[[ADR-129]]"]
commits: ["2ae9dcd", "2b8b144"]
summary: |
  Report Premium UI v2.D.1.1 + v2.9.1 — copy review entregue pelo product-designer ✅ (2026-04-27). - **Report Premium UI v2.D.1.1 + v2.9.1 — copy review entregue pelo product-designer ✅ (2026-04-27):** Cenário B fechou os dois débitos editoriais abertos durante a saída do v2.
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Premium UI v2.D.1.1 + v2.9.1 — copy review entregue pelo product-designer ✅ (2026-04-27)

- **Report Premium UI v2.D.1.1 + v2.9.1 — copy review entregue pelo product-designer ✅ (2026-04-27):**
  Cenário B fechou os dois débitos editoriais abertos durante a saída do v2.
  **v2.D.1.1 (`2ae9dcd`):** `SnapshotChangelogBuilder` ganha `SECTION_POLARITY`
  classificando S1/S2/S3/T2 como `asset` e T5 como `expense`. Verbos sem viés
  (`avançou/recuou` para asset, `subiu/recuou` para expense) substituem
  `cresceu/caiu`; cauda temporal "no mês" reduz repetição em listas. Cópia de
  zero ajustada (`passou a registrar`, `antes sem valor`, `zerou neste relatório`,
  `segue sem valor registrado`). 5 goldens atualizados + 1 cenário novo
  (`test_cenario_9_expense_polarity_t5_usa_subiu`) trava regressão de viés em
  despesa. **v2.9.1 (`2b8b144`):** `config/prompts/section_summaries.yaml` salta
  para `version: "1.1"`. System prompt reescrito com persona Mathoms ancorada em
  COPY_GUIDELINES (Perini/Cerbasi/AUVP), regras anti-hallucination explícitas
  (proibida projeção sem payload, comparação externa, inferência causal,
  promessa de retorno) e anti-padrões de tom (sem exclamação/gamificação/
  alarmismo). 13 user_prompts ganham contexto editorial específico, ângulo
  narrativo claro e thresholds explícitos para `tone`. Labels alinhadas a
  `report_layout.yaml`; correções de divergência: T3 `Tributação tática` →
  `Checklist de Tarefas` e T5 `Cenários e simulações` → `Próximos Passos`. Sem
  mudança de schema (`SectionSummaryOutput` intacto). Toggle prod
  `MATHOMS_LLM_SECTION_SUMMARIES` permanece OFF até QA editorial humano em
  workspace dogfood (escopo do dono do produto). Follow-up v3: hash-de-prompt
  na cache key.

Trabalho em andamento: execução da **[ADR-093](DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a)** (rename de stages F9) +
preparação para **F7 (Produção + LGPD + Ops)**.
**[ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side)**
(descontinuação do renderer HTML server-side) — concluída em 2026-04-25.
