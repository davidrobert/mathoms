---
id: A36.l2
type: lane
title: "Redação de PII no forward de stderr do subprocess Python no executor Go"
sprint: A36
status: planned
priority: P2
branch_slug: a36-l2-stderr-pii-redaction
adrs: ["[[ADR-323]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a36
  - status/planned
  - priority/p2
  - area/seguranca
  - area/observability
---

# A36.l2 — `stderr-pii-redaction` (SEC-09)

> **Reframe (revisão 2026-07-10):** **P2**, `candidate` não confirmado, atrás do
> fallback `InProcess` (não é hot path). Duas correções da revisão: (1) o passo
> de **confirmação é branch-first** — sem PII, fecha como `low` com a evidência,
> não compromete esforço de fix a um vetor não validado; (2) a **defesa
> load-bearing é o backstop Go, não a sanitização Python** — mensagens de
> terceiros (traceback de pandas/lib de PDF) carregam o valor cru e você não
> reescreve a mensagem de toda dependência. O Go intercepta 100% do stream.

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

1. **Spike de confirmação (branch-first, ~30min):** rodar um stage com input que
   force erro de parsing e inspecionar o `stderr` capturado — há valor de PII?
   - **Sem PII** → fechar como `low`/hardening com o artefato de evidência. Fim.
   - **Com PII** → seguir para 2/3 (e subir de tier).
2. **Backstop Go (defesa primária — fazer mesmo antes de confirmar):** o
   `stderr` do subprocess acopla **dois** canais — (a) o payload JSON estruturado
   do `StageResult` de erro (controlado, sanitizável, que se **quer** logar em
   falha) e (b) o forward free-form linha-a-linha (logs/prints legados,
   tracebacks de terceiros — o canal de PII). **Separar os streams:** o executor
   Go extrai o JSON do `StageResult` e loga em `Info`/`Error`; o forward free-form
   vai para `Debug`. **Não** rebaixar tudo para Debug em bloco (esconderia o
   diagnóstico de falha junto com o lixo). Instrumentar agora é barato; o
   executor Go é arquitetura-alvo ([[ADR-323]]) e retrofit sob carga é mais caro.
3. **Complemento Python (caso controlado):** mensagens de erro *próprias* não
   interpolam valores crus — `field=saldo`, nunca o valor (reusar
   `pipeline/llm/prompts/_sanitization.py`). **Não é exaustível** (não cobre
   exceptions de terceiros) — por isso é complemento, não a defesa principal.

## Critérios de aceite

- **Spike:** artefato de evidência anexado (com/sem PII no `stderr`) — decide o tier.
- **Se confirmado:** execução com erro real de extração **não** deixa PII no log
  estruturado do serviço Go; o JSON do `StageResult` **continua** visível em
  `Info`/`Error` (não perdeu sinal de diagnóstico); o free-form vai para `Debug`.
- A defesa load-bearing é o backstop Go (separação de streams); o Python é
  complemento do caso controlado.

**Esforço:** S. **Origem:** auditoria r4 (SEC-09; levantado como coupling pela
lente de qualidade).
