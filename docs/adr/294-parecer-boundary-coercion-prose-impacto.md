---
id: ADR-294
type: adr
title: "Coerção no boundary dos reask triggers remanescentes do parecer (prosa truncável + impacto_estimado drop)"
status: Proposto
phase: "A26 · parecer reliability"
date: "2026-06-17"
relates_to:
  - "[[ADR-292]]"
  - "[[ADR-202]]"
  - "[[ADR-208]]"
  - "[[ADR-270]]"
supersedes: []
superseded_by: []
aliases: ["ADR 294", "parecer prose truncation", "impacto drop coercion"]
tags:
  - type/adr
  - status/proposto
  - area/llm
  - area/pipeline
  - phase/a26
---

# ADR-294 — Coerção no boundary dos reask triggers remanescentes do parecer

**Status:** Proposto (A26 · parecer reliability) • **Data:** 2026-06-17 •
**Emenda** [[ADR-292]] §2 (caps de prosa) • **Relaciona** [[ADR-202]] (schema §D6),
[[ADR-208]] (impacto como gate de feature premium), [[ADR-270]] (timeout/retry LLM).

## Contexto

Novo incidente no workspace `5@5.com` (2026-06-17, run `2d555c7f`):
`review_finances_holistic` falhou em **233.5s** → `needs_review`, mesmo padrão de
reask storm que [[ADR-292]] (#655) deveria ter fechado. Diagnóstico via
`pipeline_stage_logs.output_summary`:

```
Output validation failed after 4 attempts:
- diagnostico_geral: String should have at most 500 characters  (real len=699)
- sugestoes_estrategicas.1: impacto_estimado só permitido com confianca='alta'
- notas_metodologicas.0.conteudo: String should have at most 600  (real len=614)
```

Duas causas distintas, ambas reais:

1. **Worker stale (operacional).** O #655 já subiu `diagnostico_geral` 500→750 e
   `conteudo` 600→780. O processo Celery em execução tinha o schema **antigo
   (500/600)** em memória — não foi reiniciado após o merge. Com o código atual,
   a 2ª geração (610/535 chars) teria **validado**. Fix: restart do worker.

2. **Reask triggers latentes que sobrevivem no código atual.** Mesmo com os caps
   de #655, dois validators ainda dão **hard-fail → reask**:
   - `_ck_impacto_only_if_alta` (`raise` quando `impacto_estimado` presente com
     `confianca != 'alta'`) — **disparou neste run**. Não foi tocado por #655.
   - `max_length=` de prosa — o bump só **moveu o penhasco**: a próxima geração
     que pedir >750 chars volta a stormar (4× ~16k tokens ≈ 233s).

O `claude-sonnet-4-6` em 16k tokens estoura caps de prosa de forma errática entre
gerações. Manter qualquer validator de boundary como `raise` mantém o storm
estruturalmente possível — exatamente o que [[ADR-292]] atacou para `evidencia_path`.

## Decisão

Estender a filosofia "**coerção no boundary > hard-fail que vira reask**"
([[ADR-292]], `_normalize_confianca`) aos dois triggers remanescentes. Sign-off
`prompt-engineer`.

1. **Prosa acima do teto → truncação graciosa, não `raise`.** `BeforeValidator`
   `_truncate_prose_at_cap(cap)` aplicado a todo campo de prosa do LLM
   (`diagnostico_geral`, `descricao`, `acao`, `impacto_qualitativo`, `evidencia`,
   `caveat`, `conteudo`, `titulo`s). Trunca no último fim de frase ≤ cap (fallback:
   limite de palavra; sem reticências). Como `BeforeValidator`, roda **antes** do
   `field_validator` de sigilo/ticker (§13) — a checagem vê o texto já truncado.
   Os **valores de cap permanecem** os de #655; o teto-guia do prompt (~15% abaixo)
   continua sendo a 1ª linha. Invariante: `cap >> min_length` sempre — o corte
   nunca viola o piso.

2. **`impacto_estimado` com `confianca != 'alta'` → drop, não `raise`.**
   `_ck_impacto_only_if_alta` passa a **anular** `impacto_estimado` (`= None`) em
   vez de `raise`. Preserva o invariante [[ADR-202]] §D6 (todo impacto persistido
   tem `confianca='alta'`). **Dropar, não promover `confianca`:** promover mentiria
   sobre a confiança que o modelo atribuiu e [[ADR-208]] usa `'alta'` como gate de
   feature paga — exibir estimativa com confiança fabricada é risco de produto.

3. **Mantêm `raise` (não coercidos):** `_check_no_ticker_no_sigilo` (sigilo §13 /
   ticker — guardrail de compliance [[ADR-207]]; coercer mutilaria texto, é raro) e
   `_ck_p0_cap` (count(P0)≤2 — editorial, raro, 1 reask resolve).

4. **Telemetria PII-safe** (`mathoms.llm.parecer_planejador`): `parecer_prose_truncated`
   (`field`/`original_len`/`cap`, **nunca o texto**) e `parecer_impacto_dropped_low_confianca`
   (`confianca`, **nunca o valor**). Taxa de truncação > ~5-10% dos pareceres = sinal
   de drift de verbosidade do prompt → tunar o prompt, não o cap.

5. **Sem bump de versão.** `schema_version`, `PROMPT_VERSION` e
   `EVIDENCIA_VERIFICATION_VERSION` **inalterados** — coerção é *aliviante* (outputs
   que falhavam passam a validar), não breaking; nenhum consumer downstream quebra
   (renderer já trata `impacto_estimado` Optional; prosa truncada é string válida).
   Cache só guarda gerações que **sucederam** — não há output inválido cacheado para
   re-coercer. Mesmo precedente de [[ADR-292]] (emendou comportamento sem bump).

## Emenda a [[ADR-292]] §2

[[ADR-292]] §2 **rejeitou** truncar prosa ("mutila texto user-facing e mascara
drift de verbosidade") e optou por **só elevar caps**. Esta ADR reverte essa parte
porque o bump isolado não fecha a raiz — apenas adia o storm para o próximo
overflow. As duas objeções originais são endereçadas:

- **"mutila texto":** corte em **fim de frase** (renderer `SParecer/` é flow-based,
  sem altura fixa — [[ADR-292]] §2) preserva sentido; só dispara acima do cap, que
  já é ~15% acima do teto-guia do prompt → evento raro.
- **"mascara drift":** a truncação agora é **observável** (`parecer_prose_truncated`).
  O que ADR-292 temia (drift silencioso) deixa de existir: a métrica é o gatilho
  para tunar o prompt.

## Consequências

- **Reliability:** nenhum validator de prosa/impacto gera reask — geração única no
  lugar de até 4×. Fecha a classe de reask storm (junto com [[ADR-292]] para path).
- **Produto:** sugestão de baixa/média confiança perde a estimativa monetária — mas
  ela não era exibível por [[ADR-202]] §D6 de qualquer modo. Prosa rara é truncada
  na última frase completa.
- **Operacional:** o restart do worker continua necessário para o run que motivou
  esta ADR (caps 500/600 em memória); a coerção previne o **próximo** incidente.

## Fora de escopo

- **Re-eval golden owner-gated contra `sonnet-4-6`** (KR1 A26) — a coerção muda o
  output persistido (truncado/impacto dropado); rebaseline consciente + 2 casos de
  eval novos pertencem à lane de eval (key owner-gated, [[ADR-292]] §Fora de escopo).
- **Guard de deploy que force restart de worker após merge de schema** — o processo
  que deixou o worker rodar código stale é o bug operacional de fundo (fora de código).
