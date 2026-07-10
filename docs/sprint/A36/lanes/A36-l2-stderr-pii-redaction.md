---
id: A36.l2
type: lane
title: "Redação de PII no forward de stderr do subprocess Python no executor Go"
sprint: A36
status: planned
priority: P1
branch_slug: a36-l2-stderr-pii-redaction
adrs: ["[[ADR-323]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a36
  - status/planned
  - priority/p1
  - area/seguranca
  - area/observability
---

# A36.l2 — `stderr-pii-redaction` (SEC-09)

## Problema

O executor Go repassa o `stderr` do subprocess Python **verbatim** para
`slog.Info`. O lado Python usa o `stderr` para tudo — payload de erro do
`StageResult`, logs, e mensagens de scripts legados. Se uma mensagem de erro
interpolar um valor extraído (descrição de transação, nome de titular, CPF num
`"failed to parse row: ..."`), esse valor vai para o **log estruturado** do
serviço. Log de um serviço que processa PII financeira não pode carregar o dado
(LGPD).

**Status: candidate** — o vetor é plausível mas precisa de confirmação empírica
(depende de o Python de fato emitir PII no stderr em erro).

### Âncoras

- `services/pipeline-service-go/internal/stages/executor.go:200` —
  `logChildStderr` → `slog.Info` (forward verbatim).
- `pipeline/cli_run_stage.py:88` — payload JSON em `stderr`; `:254-258` — swap
  `stdout → stderr` durante a execução (todos os handlers de logging vão p/ stderr).
- `pipeline/orchestrator.py:186-187` — captura `stdout/stderr` de scripts legados.

## Escopo

1. **Confirmar (1º passo):** rodar um stage com input que force erro de parsing
   e inspecionar o `stderr` capturado — há valor de PII? Se **não**, rebaixar
   para `low`/hardening e fechar com a evidência.
2. **Correção primária (Python):** garantir que mensagens de erro não
   interpolem valores crus — logar `field=saldo`, nunca o valor. Reusar o
   padrão de `pipeline/llm/prompts/_sanitization.py` para logs de erro.
3. **Defesa em profundidade (Go):** `logChildStderr` em nível `Debug` (não
   `Info`), ou passar por um filtro de redação antes do `slog`.

## Critérios de aceite

- Uma execução com erro real de extração **não** deixa PII no log estruturado do
  serviço Go (verificado no output do `slog`).
- A correção primária vive no Python (mensagens sem valor cru); o nível/redação
  no Go é backstop, não a única defesa.

**Esforço:** S. **Origem:** auditoria r4 (SEC-09; levantado como coupling pela
lente de qualidade).
