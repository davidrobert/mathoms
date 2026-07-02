---
id: ADR-304
type: adr
title: "KR1 do parecer — pureza monetária da prosa: fix de prompt + doutrina de enforcement"
status: Decidido
phase: "A27"
date: "2026-07-02"
relates_to:
  - "[[ADR-296]]"
  - "[[ADR-295]]"
  - "[[ADR-081]]"
supersedes: []
superseded_by: []
aliases: ["ADR 304", "KR1 prose purity", "R22 pureza monetaria"]
tags:
  - type/adr
  - status/decidido
  - area/llm
  - phase/a27
---

# ADR-304 — KR1 do parecer: pureza monetária da prosa (fix de prompt + doutrina de enforcement)

**Status:** Decidido (A27) • **Data:** 2026-07-02 • **Relaciona** [[ADR-296]] (citação
determinística — o contrato "zero R$ na prosa"), [[ADR-295]] (enforcement per-item da
citação), [[ADR-081]] (regex→LLM→needs_review).

## Contexto

O **KR1 da A27** exige `number_in_prose_violation == 0`: o LLM do parecer nunca deve escrever
valor monetário na prosa (a [[ADR-296]] fez o LLM emitir âncoras e o pipeline renderizar o
valor da folha E5). Eval de 2026-07-01 (120 gerações, holdout sintético PII-zero n=24×5)
media **61 instâncias de R$ na prosa em 38/120 runs (32%)**, mediana 0.

Diagnóstico (co-design `prompt-engineer` 2026-07-02) achou a raiz: **o prompt se
contradizia.** `config/agents/planner_persona.md:119` mandava o `diagnostico_geral` "citar
2-3 números materiais já no body" — instrução literal de escrever R$ na prosa no campo de
100% de cobertura. R17 (premissa-base "na mesma frase") induzia o valor-base monetário
inline em raciocínios de percentual (ex.: "renda tributável de R$ 720.000"). E a regra
ADR-296 estava enquadrada como "regra de citação", não como invariante de prosa.

## Decisão

### 1. Fix de prompt (config-only, bump persona 1.0.0→1.1.0 · yaml 1.5→1.6)

- `diagnostico_geral`: referencia dimensões pelo **conceito** + âncora; nunca R$ inline.
- **R17 reconciliado:** premissa-base = taxa/percentual/prazo (permitidos na prosa); valor
  monetário-base → âncora, nunca inline.
- **R22 (nova):** invariante categórico de pureza monetária — nenhum campo textual pode
  conter valor em R$ (nem "720 mil reais", nem por extenso), **inclusive** como premissa de
  cálculo. Percentuais/taxas/múltiplos/prazos permitidos. + few-shot negativo↔positivo do
  caso "valor-base em cálculo".
- Detector estendido (`parecer_evidencia._REAIS_RE`): pega valor **sem** prefixo R$ ("720
  mil reais", "720.000 reais", "3 milhões de reais") — o LLM podia driblar o `R$`.

**Resultado (eval 2026-07-02, mesmo holdout, detector robusto):** R$ na prosa **61→7
(↓88%)**, mediana 0, densidade de âncoras **12→14 (KR2 melhorou** — valores viraram âncora),
conformidade 100%, per-parecer violações 0.

### 2. Doutrina: `==0` estrito é enforcement, não prompt

O resíduo de 7 é **cauda estocástica** (5 runs/120 = 4,2%, espalhados por 5 fixtures × 1,
todos os estratos) — não um padrão fixável. Atingir `==0` estrito por prompt num gerador
estocástico é irrealista; cada rodada custa ~US$26 e não converge. **O caminho canônico
para o KR1==0 estrito é uma camada de enforcement** (pós-processa a prosa → strip/reescreve
ou `needs_review`), espelhando exatamente como a citação chegou a "0 errado publicado" via
enforcement per-item ([[ADR-295]]) e render determinístico ([[ADR-296]]). **Princípio:
prompt para qualidade, enforcement para garantia.**

### 3. Timing: shipar o fix agora, adiar o enforcement

O fix de prompt (ganho de 88% + KR2 melhor) é bancado já. O enforcement **não** se constrói
agora: o KR1 não está no caminho crítico (A27 só promove quando a A26 fechar) e o eval de
tráfego real (l2 do plano LAUNCH_TRUST / A26.l2) vem de qualquer forma — o resíduo em dados
reais pode ser diferente. **Follow-up:** construir o enforcement de pureza monetária
(análogo à [[ADR-295]]) quando a A27 for promovida + validar contra tráfego real.

## Alternativas rejeitadas

- **Iterar o prompt até 0** — teto estocástico (~4%); diminishing returns + US$26/rodada
  sem convergência garantida.
- **Construir o enforcement agora** — perfeccionismo prematuro num KR fora do caminho
  crítico; melhor validar o resíduo em tráfego real antes.

## Consequências

- **Positivas:** −88% de R$ na prosa; densidade de citação subiu; contradição do prompt
  removida; detector robusto a "mil reais"/extenso. Doutrina de enforcement documentada.
- **Custo:** KR1 não fecha `==0` estrito por ora (7/120, mediana 0) — depende do enforcement
  (follow-up) + tráfego real.
- **Gate:** eval owner-gated; `number_in_prose_median == 0` mantido; `densidade ≥ piso 5`
  (mediana 14).
