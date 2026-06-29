---
id: ADR-300
type: adr
title: "Red lines do parecer: 4ª camada de validação determinística (conselho defensável)"
status: Proposto
phase: "A22 · F3 launch-trust"
date: "2026-06-26"
relates_to:
  - "[[ADR-202]]"
  - "[[ADR-279]]"
  - "[[ADR-292]]"
  - "[[ADR-295]]"
  - "[[ADR-296]]"
  - "[[ADR-081]]"
supersedes: []
superseded_by: []
aliases: ["ADR 300", "red lines", "parecer defensável", "guardrail de conselho"]
tags:
  - type/adr
  - status/proposto
  - area/llm
  - area/seguranca
  - phase/a22
---

# ADR-300 — Red lines do parecer (4ª camada de validação)

**Status:** Proposto (A22 · F3 launch-trust) • **Data:** 2026-06-26 •
**Relaciona** [[ADR-202]] (schema do parecer), [[ADR-279]]/[[ADR-295]]/[[ADR-296]]
(citação verificada + enforcement), [[ADR-081]] (determinístico decide). Co-design
`financial-planner` + `prompt-engineer` (mecânica) 2026-06-26. Implementação na
lane [[A22.l2]] (= F3-O1 de [[PLAN-launch-trust]]).

## Contexto

O Parecer do Planejador (E6, `review_finances_holistic`) gera **conselho
financeiro** na persona Perini/Cerbasi/AUVP. Hoje tem duas camadas de validação
determinística pós-LLM: `_check_sigilo` (§13, marca) e `_check_evidencia`
(citação rastreável, [[ADR-279]]/[[ADR-295]]). **Nenhuma barra conselho
irresponsável** — citar o número certo (`evidencia`) é ortogonal a dar o conselho
certo. Para um cliente pagante, conselho indefensável (ex.: "saque a reserva de
emergência para buscar rentabilidade") é dano material + passivo jurídico. É o KR7
de [[PLAN-launch-trust]] (F3 — "confio no conselho").

## Decisão

**4ª camada determinística `_check_red_lines(raw, e5_data, config)`**, sobre o
output já parseado (`ParecerPlanejadorOutput`), zero LLM. Sete regras de domínio
invioláveis ("red lines"); ≥1 cruzada → **`needs_review` do parecer inteiro**
(reusa `_needs_review`, L201), nunca drop per-item.

### Por que needs_review global, não drop per-item ([[ADR-295]])

O drop per-item da citação remove o card com número errado e preserva o resto —
defeito **local**. Red line indica que o modelo **raciocinou de forma
irresponsável**; é veredito **global** de segurança sobre a geração. Dropar o item
ofensor mascara o problema e pode publicar conselho perigoso correlacionado.
Evidência = "esse número está certo?" (local). Red line = "esse parecer é seguro
de publicar?" (global). Global → needs_review global.

### Ordem de execução

`LLM → _check_red_lines → _check_sigilo → _check_evidencia → finalize`. Red lines
**primeiro**: é a barreira de maior severidade (segurança > marca > citação) e o
curto-circuito mais barato (não gasta o drill-down do verificador sobre um parecer
já condenado).

### As 7 red lines (conteúdo de domínio — financial-planner)

| ID | Proíbe | Pende para |
|---|---|---|
| RL-1 `RESERVA_ANTES_DE_RISCO` | aporte em risco com reserva abaixo da meta | evitar FN |
| RL-2 `DIVIDA_CARA_PRECEDE_RISCO` | aporte em risco sem priorizar quitação de dívida cara | evitar FN (best-effort — ver §riscos) |
| RL-3 `PROMESSA_DE_RETORNO` | garantir/prometer rentabilidade (risco CVM) | **zero FN** (FP irrestrito ok) |
| RL-4 `ATIVO_ESPECIFICO` | recomendar ticker/fundo/instituição nominada | **zero FN** |
| RL-5 `P0_SEM_FONTE` | sugestão P0 cujo `evidencia_path` resolve nulo/ausente | equilíbrio, leve p/ FP |
| RL-6 `MEXER_EM_RESERVA_OU_PROTECAO` | sacar reserva / cortar seguro essencial por rendimento | evitar FN |
| RL-7 `SEVERIDADE_INCOERENTE` | subdiagnosticar risco que o E5 já sinaliza (hard) / alarmismo (warning) | sub: FN · alarme: FP |

Calibração-mestra (inverte a herança do dedup): em **conselho**, FN (cliente age
sobre conselho ruim) é pior que FP (parecer bom vira needs_review, recuperável) —
exceto compliance (RL-3/RL-4: zero FN). Heurística de verbo é **lista controlada
de lemmas** versionada, não NLP; verbo ambíguo → warning, não block.

### Prompt-side + validation-side (defesa em profundidade)

Red lines entram **também** no system prompt como REGRA 14 (prevenção → menos
needs_review, melhor UX) **e** na validação (garantia). Espelha o padrão sigilo
§13 ("persona é 1ª linha; validador é defesa"). Bump `PROMPT_VERSION → 2.1.0`.

### Versionamento e cache

Nova constante `RED_LINES_VERSION = "1.0"` (contrato de validação, análoga a
`EVIDENCIA_VERIFICATION_VERSION`). Entra no cache key composite (`:rl{...}`) —
parecer cacheado sob `rl1.0` não passou pela red line de `rl1.1`; servir do cache
publicaria conselho não-validado. `_SCHEMA_VERSION` **não** muda (output não ganha
campo).

### Eval determinístico no PR gate (sem `ANTHROPIC_API_KEY`)

Prova que o **enforcement dispara quando deve e silencia quando não deve** — sem
LLM. Por red line: 2 fixtures "envenenadas" (output sintético que viola) + 1
"borderline-limpa" (anti-FP). Gate de completude `test_all_seven_red_lines_have_coverage`
força fixture nova ao adicionar red line. Roda no PR gate (não marcado `llm_eval`).
O eval LLM real (`test_parecer_evidencia_llm_eval.py`, owner-gated) mede a taxa
**emergente** e é ortogonal — não substitui o gate determinístico.

### Observabilidade / drift

`red_lines_summary` no `ParecerGenerationResult` + log PII-free
`mathoms.llm.parecer_planejador.red_line_triggered` (só ids). Decompõe a taxa de
needs_review **por causa** (`{sigilo, evidencia, red_line}`) — sem isso, spike de
red line fica invisível atrás de ruído de evidência. Drift real = não-sobreposição
de IC95 Wilson entre janela recente e baseline, com `prompt_version`/`red_lines_version`/`PARECER_MODEL`
constantes (método do braço diagnóstico do eval).

## Consequências

- **Positivas:** fecha o eixo de confiança "conselho" (KR7); barreira fail-closed
  testada em CI sem custo de LLM; drift de segurança observável.
- **Custo:** +1 camada determinística (latência desprezível); bump de prompt exige
  re-eval LLM owner-gated antes do merge da REGRA 14.
- **Trade-off aceito:** enforcement-only (sem REGRA 14) pode elevar needs_review;
  aceitável — a segurança é binária (bloqueia), o budget de UX (`needs_review`
  ≤15%, [[A26]] §gate) é observado, não bloqueante.

## Riscos / itens abertos (reconciliar antes da impl. dos predicados)

Os campos reais do E5 são **mais pobres** que o co-design assumiu (verificado
2026-06-26 em `reserva_emergencia_calculator.py` / `endividamento_analyzer.py`):

- `reserva_emergencia` expõe `cobertura_meses` + `avaliacao_liquidity`, **não**
  `meses_cobertos_essencial`/`meta_meses`. RL-1/RL-6 ancoram em `cobertura_meses <
  piso` (piso 6 da config de níveis) + `avaliacao_liquidity == "Insuficiente"`.
- `endividamento.dividas[].taxa_juros` é **string "N/D"** por default — não há
  `taxa_mensal` numérico. **RL-2 degrada para best-effort:** só dispara quando a
  taxa é conhecida e parseável > piso; taxa desconhecida → não bloqueia (não
  inventa dado). Documentar o gap como follow-up de extração.
- `reserva_emergencia`/`endividamento`/`dividas` são `{"type":"object/array"}`
  genéricos no schema E5 — predicados leem campos não-validados; **reconciliar
  predicado↔campo real é pré-requisito de implementação** (predicado contra campo
  inexistente = red line silenciosa, o pior modo de falha de camada de segurança).

Esta reconciliação (financial-planner, com os shapes reais) precede a camada
Python; o gate de completude + as fixtures "envenenadas" são a prova empírica de
que cada predicado dispara de fato.
