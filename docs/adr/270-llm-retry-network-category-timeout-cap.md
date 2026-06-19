---
id: ADR-270
type: adr
title: "Retry de LLM calls — categoria network + cap de timeout"
status: Decidido
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
  - status/decidido
  - type/adr
---

# ADR-270 — Retry de LLM calls: categoria `network` + cap de timeout

**Status:** Decidido · **Data:** 2026-05-28 · **Relaciona** [[ADR-081]] (regex→LLM→needs_review), [[ADR-110]] (logging estruturado `mathoms.*`).

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

## Emenda 2026-06-12 — timeout base por call-site + escalada em retry (incidente parecer)

**Gatilho:** run `ae06c5e1-2ad1-446b-aa25-f7302ec538db` (workspace `1b9f2cf5-...`) falhou em
`review_finances_holistic` após 494s: 4 tentativas, **todas** `litellm.Timeout` exatamente no
cap de 120s. Dois minutos antes, no mesmo worker, chamada ao mesmo modelo (`claude-sonnet-4-6`,
2k tokens out) completou em 25,7s — rede e provider OK. A migração de modelo ([[ADR-289]],
EOL do `claude-sonnet-4-20250514`) empurrou a latência do parecer (16k
`max_tokens`, output típico 4-5k tokens, antes 58-66s) para além dos 120s. A premissa do §1
("120s cobre p95 de prompts grandes 45-90s") envelheceu para esse call-site — e o retry,
reusando o mesmo cap, falhava **deterministicamente**: 494s queimados sem chance de sucesso.

**Decisão (revisa §1 e §3):**

1. **`LLM_CALL_TIMEOUT_S=120` deixa de ser cap fixo e vira timeout base.**
   `LLMService.call` ganha `timeout_s: float | None` (default 120s). Call-site com geração
   sabidamente longa declara seu budget — mesmo padrão de `max_tokens`. O parecer passa
   `timeout_s=240` (`ParecerOrchestratorConfig.llm_timeout_s`).
2. **Escalada em retry para `error_type=timeout`:** a tentativa seguinte a um timeout dobra o
   cap, com teto `LLM_TIMEOUT_ESCALATION_CEILING_S=600`. Tentativa 1 mantém o base — o
   fast-fail contra DNS hang do §1 fica preservado. Demais error_types não escalam.
3. **Teto de tentativas para timeout: `LLM_TIMEOUT_MAX_ATTEMPTS=2`** (1 base + 1 escalada),
   independente do `max_retries` global. Se dobrar o budget não resolveu, o problema não é
   budget — insistir só inflaria o pior caso (4 tentativas escalonadas ≈ 22min de stage preso).
4. **Telemetria:** logs `LLM call START` e `attempt failed` incluem `timeout_s` efetivo da
   tentativa — drift de latência por stage visível sem eval novo.

Pior caso do parecer: 240s + backoff 2s + 480s ≈ **12min** (vs 494s falhando sempre); o caso
observado no incidente teria sucedido **na 1ª tentativa** com base 240s.

**Decisão complementar — `validation` sai do outer loop (mesma data):** com o
timeout resolvido, a re-execução expôs a camada seguinte: `string_too_long`
quase determinístico (modelo novo mais verboso que os `max_length` do schema).
O outer loop re-tentava validation **fresco** 3× a temp 0.1 — reproduzindo o
mesmo erro a ~140s/tentativa. Revisão:

5. **Reask interno do Instructor sobe de 1 → 2** (`max_retries=2` no
   `create`): re-pergunta COM o erro de validação no contexto — único retry
   que muda o resultado em validation.
6. **`validation` deixa de consumir o outer loop**: esgotado o reask interno,
   `LLMValidationError` → needs_review direto. Outer loop fica reservado a
   transientes (timeout/network/rate_limit/provider_error).
7. Causa proximal tratada no prompt (1.5.0: limites de concisão por campo,
   margem ~15% sob o schema) — schema `max_length` inalterado (contrato de
   renderer; truncation silenciosa rejeitada). Cache: ver emenda [[ADR-199]]
   (`prompt_version` na chave).

**Critério de aceite da emenda:** testes em `tests/test_litellm_client_retry.py`
(escalada, teto 600s, cap de 2 tentativas, não-escalada de provider_error,
validation = 1 chamada externa, reask interno 2) +
`tests/test_parecer_orchestrator.py::test_llm_call_uses_parecer_timeout_base`.

**Follow-ups (débito):** (a) caracterizar p95 real do parecer com
`claude-sonnet-4-6` (5-10 execuções) para validar se 240s é o base correto;
(b) smoke eval de comprimento de campos prosa vs `max_length` como gate de
cutover de modelo — [[ADR-289]] trocou o modelo sem eval real e esta classe de
regressão é invisível ao CI mockado.

## Follow-ups

- Telemetria: emitir `mathoms.llm.error_type` como dimension no logger estruturado quando call falha definitivamente. Escopo de Sprint A17.observability se prioritário.
- Avaliar partial success em stages LLM-heavy (`extract_baseline`, `extract_irpf_full`, `analyze_finances`). ADR `Proposto` separada se virar prioridade.
- Migrar `timeout`/backoff para `LLMConfig` (DB) quando primeiro workspace pedir tunagem custom.
