---
id: A37.l1
type: lane
title: "Parecer enxerga o relatório inteiro: contrato de exec context (dupla truncação) + redação de identificadores"
sprint: A37
status: shipped
priority: P0
branch_slug: a37-l1-parecer-exec-context
adrs: ["[[ADR-341]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/shipped
  - priority/p0
  - area/llm
  - area/pipeline
---

# A37.l1 — `parecer-exec-context` (A: PE-01+DE-02+PE-09+PE-08 · DE-06 · OBS-1 · FIN-02b)

> **P0 e causa-raiz da sprint.** O parecer LLM está cego para ~metade do E5
> por **duas camadas cumulativas de truncação** — medido no artefato E5 real
> do run `6659d62c` (corpo destilado 15.560 bytes). Consertar só uma camada
> **não** restaura o dado.

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

1. **Cap global:** `max_exec_context_bytes: 8192`
   (`config/prompts/parecer_planejador.yaml:454`) corta o corpo em
   `backend/app/services/parecer_distiller.py:215-217`. Seções 7–10 do
   manifest (`previdencia_irpf`, `riscos_protecao`, `sintese`,
   `plano_acao_atual`) ficam **100% fora**; o corte cai no meio da seção 6.
2. **Truncação por bloco:** `_render_scalar`
   (`parecer_distiller.py:107`) aplica `_short(limit=300)` ao dump de cada
   bloco `format: scalar`; o fix R3.3 (#987) só wireou `_flatten_leaves` em
   `_render_field` (key_value). 10 blocos scalar truncam (ex.:
   `$.fluxo_caixa` 14.938 chars; `$.protecao_patrimonial` 1.050 com
   `apolices_vigentes` começando no char 322 → 100% cortado).
3. **Hints competem com dados:** linhas `_hint:_` somam 4.224 bytes no corpo
   pré-cap (2.287 dentro da janela entregue). Retirá-las **sozinho não basta**:
   corpo sem hints = 11.336 bytes > 8.192.
4. **Sem recovery:** tool trace do run tem 8 chamadas, todas `get_e5_jsonpath`;
   **zero** `get_e5_section`, apesar do marcador de truncação e do enum
   disponível. O modelo declara ausência em vez de recuperar.

**Dano observado:** parecer sugere explorar dedução de previdência quando o E5
informa `previdencia_pgbl.limite_pgbl_anual=0` ("teto atingido"; o hint FP-04
que proíbe isso vive na seção 7 truncada — fixes v1.7–v1.9 estão inertes) e
emite risco de "ausência de dados sobre proteção patrimonial" com 3 apólices e
`gap_qualitativo` presentes no E5. Cobre também **FIN-02b** (com a seção 7
visível, o parecer distingue alíquota efetiva de marginal para previdência).

**Acoplamento de PII (DE-06) — pré-requisito, mesmo trem:** o sanitizer
(`backend/app/services/parecer_context_sanitizer.py:73` →
`pipeline/observability/pii_patterns.py`) rediz nomes e CPF/CNPJ **com
máscara**, mas não nº de apólice (dígitos com espaços, presente no E5 em
`apolices_vigentes[].apolice_numero`) nem dígitos longos sem máscara. O vetor
já existe hoje via `get_e5_section("protecao_patrimonial")` (devolve a seção
inteira, sem truncação). **Destravar a seção sem redigir identificadores é
regressão de PII.**

## Entregas (2 PRs sequenciais)

1. **PR-1 (W0): ADR `Proposto`** — contrato do exec context do parecer:
   budget de bytes (proposta: ≥ ~16KB, custo ~+US$0,01–0,02/parecer), formato
   por bloco (blocos densos saem de `scalar` cru para `key_value`/resumo
   declarado no manifest — **não** aplicar flatten cru a `fluxo_caixa`/
   `consumo_consciente`, 15–17K chars), posição dos hints (fora do corpo
   capped, como o citation catalog), regra de recovery via `get_e5_section` no
   system prompt, redação de identificadores estruturais no sanitizer, **e
   política de prioridade/eviction determinística por seção, declarada no
   manifest** — subir o cap sozinho só move o penhasco quando o E5 crescer;
   eviction no boundary de seção é o que fecha a causa-raiz.
2. **PR-2a (W1): sanitizer/redação de identificadores** — independente e
   shippável **primeiro** (defesa em profundidade vale antes do fix de budget).
   Redação **por chave declarada** (`apolice_numero` e demais campos
   identificadores do E5) ou por formato específico — **não** regex genérica de
   "dígitos ≥7" sobre strings livres (over-redigiria CEP/referências/valores em
   prosa sem que o eval flagre).
3. **PR-2b (W1): distiller + manifest bump 2.0 + hints fora do corpo + regra de
   recovery no system prompt + re-baseline do eval golden.** Pré-condição: o
   vocabulário de sentinelas está coordenado com [[A37.l4]] (a seção restaurada
   não pode renderizar `"N/D"` como dado — o distiller hoje só pula `None`).
   Incluir OBS-1: clarificar semântica do contador de `tool_iterations` (trace
   registrou 8 com `max_tool_iterations: 6`; 3 eram cache_hit).

## Critério de aceite (binário)

- Distiller sobre o E5 do run `6659d62c` (ou run fresco) entrega **10/10
  seções**; probes `limite_pgbl`, `apolices_vigentes`, `gap_qualitativo`
  **presentes** no contexto final.
- Campos identificadores declarados (ex.: nº de apólice) **redigidos** no
  contexto E nas respostas de `get_e5_section`/`get_e5_jsonpath` (regressão no
  caminho das tools) — com guard de over-redação: prosa monetária/CEP intactos.
- Probes de tool-behavior no run de aceite: distribuição de tool-calls e
  `tokens_in` dentro dos caps (`max_tool_iterations`, `max_total_input_tokens`)
  — a instrução de recovery não pode inflar chamadas.
- Eval golden re-baselinado com **N≥3 execuções e banda explícita** (o resíduo
  determinístico em temperatura baixa já foi medido como material — single-run
  "sem mismatch" não é gate); run real: parecer sem
  sugestão de dedução de previdência com limite=0 e sem "ausência de dados de
  proteção" (KR-A).
- Teste de regressão do distiller: corpo com N seções → todas presentes até o
  budget; truncação, se houver, é **por prioridade declarada**, nunca silenciosa
  no meio de seção; probes **field-level** nos blocos densos re-formatados
  (`fluxo_caixa`, `consumo_consciente`) — resumo curado é vetor novo de
  truncação silenciosa; contagem de seção não basta.

## Risco / rollback

Conteúdo do parecer muda por design (risco Médio) — mitigado pelo re-baseline
golden na mesma lane. Rollback: revert do PR-2 restaura manifest 1.9 (o cap
antigo volta). Custo/latência re-medidos no run de aceite (banda: parecer
≤ ~180s, ≤ ~US$0,30). **Owner-gated:** o eval golden real depende de chave e
orçamento habilitados pelo owner; fallback de aceite = golden mockado +
medição in-process do distiller, com o eval real agendado na janela do owner.
