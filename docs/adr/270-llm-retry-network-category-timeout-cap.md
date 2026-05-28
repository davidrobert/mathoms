---
id: ADR-270
type: adr
title: "Retry de LLM calls — categoria network + cap de timeout"
status: Proposto
phase: A17.llm-retry
date: "2026-05-28"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-110]]"
supersedes: []
superseded_by: []
aliases:
  - "LLM network retry"
  - "Timeout cap LiteLLM"
tags:
  - area/pipeline
  - area/llm
  - phase/a17
  - status/proposto
  - type/adr
---

# ADR-270 — Retry de LLM calls: categoria `network` + cap de timeout

**Status:** Proposto · **Data:** 2026-05-28 · **Relaciona** [[ADR-081]] (regex→LLM→needs_review), [[ADR-110]] (logging estruturado `mathoms.*`).

## Contexto

Em 2026-05-24 o run `a12887b7-0a78-454e-b777-145f5792c273` do workspace `1b9f2cf5-...` falhou em `extract_baseline` (E1.5) após **9h42min** de execução (13:01:52 → 22:44:09). Erro raiz na exception final do `LLMService.call`:

```
LLM call failed after 4 attempts (623842ms):
litellm.InternalServerError: AnthropicException -
  [Errno 8] nodename nor servname provided, or not known.
```

`[Errno 8]` no Darwin é `EAI_NONAME` de `getaddrinfo()` — falha de resolução DNS para `api.anthropic.com`. O host (dev macOS) teve indisponibilidade de DNS local transiente. A chamada **nunca alcançou a Anthropic** — falha 100% client-side de rede.

Comportamento atual de `pipeline/llm/litellm_client.py` (linhas 344-468):

1. `LLMService.call` faz até `max_retries+1 = 4` tentativas.
2. `_classify_error` retorna `LLMErrorType.provider_error` para DNS errors (default catch-all). É `retryable`, ok.
3. `_BACKOFF_DELAYS = [2.0, 4.0, 8.0]` → 14s totais entre as 4 tentativas.
4. **Cada tentativa durou ~155s** (623842ms / 4 ≈ 156s). Causa: o Anthropic SDK (sob LiteLLM) faz retries **internos** (`max_retries=2` default + connect timeout ~25s no Darwin), que **compõem** com nosso retry externo. Nada cappia esse tempo.
5. `extract_baseline` processa N documentos IRPF; cada doc dispara uma ou mais LLM calls. N × 4 × 155s = horas. Aqui: ~9h42min.

Problemas concretos:

- **Wall-clock catastrófico**: 9h42min para falhar é regressão de UX inaceitável. O usuário pensou que estava processando; estava aguardando DNS.
- **Sem cap de timeout** por chamada: ficamos à mercê do default do SDK encadeado.
- **Sem distinção de "rede local" vs "provider error"**: dashboard/alerting trata Anthropic 5xx, rate limit e DNS local idênticos.
- **Backoff curto demais para outage de rede**: DNS down típico volta em 30-120s; 14s não cobre.

## Decisão

Três cortes — classificação extraída para `pipeline/llm/error_classification.py` (SRP + manter `litellm_client.py` ≤500 linhas), retry loop continua em `pipeline/llm/litellm_client.py`:

### 1. Cap de timeout + desabilitar retry interno do LiteLLM/Anthropic SDK

Passar `timeout=120` e `num_retries=0` explícitos no `_client.chat.completions.create(...)`.

- `timeout=120s` cobre p95 de prompts grandes legítimos (IRPF full ~50k tokens input → 45-90s observados). Não é apertado demais; não é frouxo demais.
- `num_retries=0` no LiteLLM impede retries internos do Anthropic SDK. **Nós** controlamos retries via outer loop — fonte única, comportamento previsível, observável.

### 2. Nova categoria `LLMErrorType.network` distinta de `provider_error`/`timeout`

Justificativa: as três têm **runbooks diferentes**.

- `provider_error` (5xx, transient HTTP) → escalar pra Anthropic / trocar provider via LiteLLM router.
- `timeout` → request demasiado grande / connection slow → tunar prompt / split.
- `network` → DNS/conn refused/network unreachable → checar host/VPN/resolver.

Custo: 1 enum + 1 backoff list. Ganho: alerting + drift detection separáveis em `mathoms.llm.*` ([[ADR-110]]).

Detecção em `_classify_error` usa **duas camadas** (SDK pode mudar wrapping):

1. **Strict — `isinstance` sobre `exc.__cause__` / `exc.__context__`**: `socket.gaierror`, `ConnectionError`, `ConnectionRefusedError`, `ConnectionResetError` da stdlib.
2. **Fallback — string match** sobre `str(exc).lower()`: `"nodename"`, `"servname"`, `"name or service not known"`, `"name resolution"`, `"errno 8"`, `"connection refused"`, `"network is unreachable"`, `"dns"`.

### 3. Backoff network-specific

`_BACKOFF_DELAYS_NETWORK = [30.0, 60.0, 120.0]` (vs `[2.0, 4.0, 8.0]` para outros retryable).

Worst case 4 attempts × 120s timeout + 30+60+120s = 210s sleep + ~480s timeouts = **~12min** (vs ~10h observados). Em outage curto (≤30s) que limpa, 2ª tentativa pega verde.

## Trade-offs

- **`timeout=120s` pode mascarar prompts genuinamente lentos** (>120s). Mitigação: log de sucesso passa a incluir `attempt_succeeded_on` e `duration_ms` por attempt; alerta SRE sobre p95 > 100s antes de chegar no teto.
- **`num_retries=0` no LiteLLM remove safety net de retries para 429/5xx** internamente. Mitigação: rate limit e provider_error já estão em `_RETRYABLE_ERRORS` no outer loop; comportamento end-to-end mantido — confirmado por teste com `RateLimitError` mockado.
- **`isinstance(__cause__, socket.gaierror)` é frágil** se LiteLLM mudar wrapping. Mitigação: fallback string match cobre o caso.
- **`network` adiciona complexidade**: 3 categorias retryable (`network`, `rate_limit`, `provider_error`) em vez de 2. Aceito: dashboards/runbooks separáveis valem.

## Alternativas consideradas

1. **Apenas string match (sem isinstance)**: rejeitado — frágil a mudanças de mensagem upstream.
2. **Apenas isinstance (sem fallback string)**: rejeitado — SDKs reembrulham exceptions e `__cause__` nem sempre é preservado.
3. **Classificar DNS como `timeout` e reusar backoff de `timeout`**: rejeitado — alerting confunde "rede local" com "request grande".
4. **`timeout=60s`**: rejeitado — observado p95 de IRPF full 45-90s; 60s vira regressão em prompts grandes legítimos.
5. **Partial success em `extract_baseline`** (continuar stage mesmo se 1 doc falha): escopo separado — muda invariante atomic-or-fail do stage. ADR própria se virar prioridade.
6. **Mover `timeout`/backoff para `LLMConfig` (config DB)**: YAGNI — nenhum workspace pediu tunar por workspace; constantes de módulo cobrem 6+ meses. Migrar quando primeiro pedido aparecer.

## Consequências

- Falhas de DNS detectadas em ≤12min (vs ~10h).
- Logs estruturados permitem alerta separado para "rede do host degradada" vs "Anthropic em pane".
- Stage `extract_baseline` continua atomic-or-fail nesta ADR; melhoria de partial success fica para ADR futura se necessária.
- Sem mudança em prompt, schema, model, temperature, seed: zero risco a eval golden.

## Critério de aceite

- `_classify_error(socket.gaierror(...))` retorna `LLMErrorType.network` (teste unit).
- `_classify_error(litellm.InternalServerError("...nodename..."))` retorna `LLMErrorType.network` via fallback string match (teste unit).
- Backoff network usa `[30, 60, 120]` e não `[2, 4, 8]` (teste unit verifica sequence de `time.sleep`).
- Rate limit 429 continua retryable e usa backoff curto (teste de regressão).
- `_client.chat.completions.create(...)` recebe `timeout=120` e `num_retries=0` (assert em mock).
- Goldens `pytest tests -q -k "baseline or irpf"` sem delta — fix mexe só em network boundary, não em prompts.

## Follow-ups

- Telemetria: emitir `mathoms.llm.error_type` como dimension no logger estruturado quando call falha definitivamente. Escopo de Sprint A17.observability se prioritário.
- Avaliar partial success em stages LLM-heavy (`extract_baseline`, `extract_irpf_full`, `analyze_finances`). ADR `Proposto` separada se virar prioridade.
- Migrar `timeout`/backoff para `LLMConfig` (DB) quando primeiro workspace pedir tunagem custom.
