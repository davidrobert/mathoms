---
id: ADR-300
type: adr
title: "Red lines do parecer: 4ª camada de validação determinística (conselho defensável)"
status: Decidido
phase: "A22.l2 · F3 launch-trust"
date: "2026-06-26"
relates_to:
  - "[[ADR-202]]"
  - "[[ADR-279]]"
  - "[[ADR-292]]"
  - "[[ADR-295]]"
  - "[[ADR-296]]"
  - "[[ADR-081]]"
  - "[[ADR-301]]"
supersedes: []
superseded_by: []
aliases: ["ADR 300", "red lines", "parecer defensável", "guardrail de conselho"]
tags:
  - type/adr
  - status/decidido
  - area/llm
  - area/seguranca
  - phase/a22
---

# ADR-300 — Red lines do parecer (4ª camada de validação)

**Status:** Decidido (A22.l2 · F3 launch-trust) • **Data:** 2026-06-26 •
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
§13 ("persona é 1ª linha; validador é defesa"). **Entregue nesta lane: só a
validação (garantia).** O prompt-side (REGRA 14 + bump `PROMPT_VERSION → 2.1.0`)
é follow-up owner-gated — ver §Follow-ups.

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

## Reconciliação dos predicados (resolvida — A22.l2)

Os campos reais do E5 são mais pobres que o co-design supôs; predicados
reconciliados (financial-planner 2026-06-26) e ancorados em campos verificados.
Implementação em `backend/app/services/parecer_red_lines.py` + eval determinístico
`tests/test_parecer_red_lines.py` (14 envenenadas + 7 limpas + gate de completude):

- **RL-1/RL-6** ancoram em `reserva_emergencia.cobertura_meses < 6` **ou**
  `avaliacao_liquidity == "Insuficiente"` (não existe `meta_meses`); NaN-safe.
- **RL-2 best-effort:** `endividamento.dividas[].taxa_juros` é string "N/D" por
  default → ramo hard só dispara quando a taxa parseável > 1,5% a.m.; senão proxy
  `ratios.taxa_endividamento_pct ≥ 40` vira **warning** (não bloqueia financiamento
  barato). Follow-up: extrair `taxa_mensal` numérica no `endividamento_analyzer`.
- **RL-7 só sinal estruturado:** `real_estate.concentracao_pct > 40` /
  `real_estate.alertas` (tema inequívoco). `pontos_urgentes` é texto livre, sem
  tema mapeável deterministicamente → **fora do hard-block** (follow-up: tag de
  tema por item de urgência).
- **RL-4 ticker é o caminho vivo;** match de instituição nominada exige injetar o
  `institution_catalog` (param `institutions`, hoje vazio) → follow-up.

## Calibração pós-dogfood (RED_LINES_VERSION 1.1 · 2026-06-30)

Primeiro eval LLM real (60 gerações) expôs dois falsos-positivos em massa (~97%
`needs_review` — quebraria o flip strict da [[A26]]l2). Corrigidos (RED_LINES_VERSION
`1.0`→`1.1`, invalida cache):

- **RL3** checava a palavra-de-garantia isolada; restaurada a spec (garantia **+
  objeto-de-retorno** em proximidade). FP real: "folga … **garante** capacidade de
  aporte", FGC "fundo **garant**idor".
- **RL1** bloqueava planejamento de arcabouço (definir política/alocação-alvo — núcleo
  AUVP) como se fosse deploy. Calibração (financial-planner): execução inequívoca
  sempre bloqueia; verbo ambíguo (`investir/alocar em`) só em P0/P1; planejamento puro
  não bloqueia.
- Bug latente: `avaliacao_liquidity == "Insuficiente"` (case) vs dado `"insuficiente"` —
  normalizado.

## Calibração 1.2 — RL1 rebalanceamento ≠ deploy (RED_LINES_VERSION 1.2 · 2026-06-30)

2º dogfood (inspeção dos 0-âncora) revelou que o "0 âncora" **não era gap de citação** —
eram pareceres **ricos** (9–15 âncoras) **bloqueados pela RL1** → placeholder vazio. E a
RL1 1.1 ainda bloqueava ~80% no temp de produção: as sugestões eram **rebalanceamento /
de-risking / aporte-como-método** (AUVP rebalanceia por aporte; "revisar/reduzir peso de
ações" é de-risking), não deploy de capital novo. Co-design `financial-planner` (5/5 FP) +
`senior-cto` (predicado composicional):

- `_DERISK_REBALANCE` (rebalanc/por aporte/aportes mensais/revisar peso/reduzir/diminuir/
  realocar/redistribuir) **curto-circuita** RL1 antes da avaliação de execução.
- `_EXEC_INEQUIVOCA` perde `"aport"` cru (casava "por **aport**e", método) → só verbo
  conjugado de deploy. Predicado = `exec-conjugado ∧ objeto ∧ ¬(rebalance ∨ redução ∨
  planejamento ∨ pró-reserva)`. Lemma **composicional + âncora-negativa**, sem parser
  (preserva o determinismo zero-LLM do ADR-300; lemma-flat tinha teto de precisão baixo).
- Fixtures anti-FP com as 5 frases reais do dogfood.

## Validade do eval como instrumento (eval-design — itens 2/3 do dogfood)

- **Item 2 (cobertura de citação): DISSOLVIDO.** Pareceres citam rico (9–15 âncoras >> piso
  5); o piso de densidade=5 **está correto, sem ajuste**. Dois reparos de medição
  (PM + senior-cto): (a) a densidade deve **excluir pareceres bloqueados** do denominador
  (senão mais bloqueios reabrem um falso-gap); (b) registrar a densidade observada como
  **baseline de drift** (anti-Goodhart) ao fechar o item.
- **Item 3 (holdout monocultura): MUST antes do flip strict.** Os 10 fixtures têm 100%
  reserva ~1,5 mês — e é **estrutural** (`make_workspace_e5` fixa `cobertura_meses=2.1`;
  `_scale_money` escala um *ratio* como dinheiro — bug). Sem estratificar, o gate de UX
  (`needs_review ≤15%`) é **incomputável**: mede a RL1, não o produto. Critério de aceite
  (data-engineer + financial-planner + PM):
  - estratos de `cobertura_meses` — sub-meta (<3) / borderline (3–6) / saudável (≥6) /
    folgado (>12), ≥2 fixtures cada, **ponderado ao ICP** (alta renda tende a reserva acima
    da média; ~50% saudável), n≥20;
  - **estrato de controle negativo** (saudável) onde RL1 deve disparar **~0%** = métrica de
    *precision* que hoje **não existe** (um eval sem controle negativo só prova recall, é
    cego a FP — foi por isso que RL3/RL1 FP escaparam do gate e só a inspeção humana pegou);
  - variar eixos secundários (dívida cara/concentração/seguro) p/ o número não ser dominado
    por uma red line;
  - corrigir `_scale_money` (parar de escalar o ratio) + a docstring da fixture (afirma
    estratificação que não existe).
- **Gate redefinido (2 números):** recall de RL1 no estrato distressed + **FP-rate no
  estrato saudável**. O budget `needs_review ≤15%` da [[A26]]l2 é **não-binário** (UX, não
  segurança); o gate de **segurança** (zero conselho indefensável publicado) está verde por
  construção (fail-closed) independentemente da taxa.

> **Calibração por domínio, não para passar o holdout.** As red lines foram ajustadas pela
> regra metodológica (rebalancear/de-risking é prudente), não para o número do fixture
> enviesado. Estratificar corrige a **medição**; calibrar corrige a **regra** — ortogonais,
> ambas necessárias. Recomendado **medir em 2 passos** (estratificado+1.1 isola artefato de
> fixture; estratificado+1.2 isola FP de predicado).

## Follow-ups (não bloqueiam o enforcement)

- **Prompt-side (REGRA 14 + bump `PROMPT_VERSION → 2.1.0`):** owner-gated — exige
  re-rodar o eval LLM real (`ANTHROPIC_API_KEY`) comparando 2.0.0 vs 2.1.0 sem
  regressão de citação/densidade/custo. O enforcement determinístico (esta entrega)
  é a **garantia**; o prompt-side é prevenção (reduz `needs_review`).
- Extração de `taxa_mensal` numérica (fortalece RL-2); injeção do
  `institution_catalog` em RL-4; tag de tema em `pontos_urgentes` (amplia RL-7).
