---
id: PLAN-report-trust
type: plan
title: Report Trust — o relatório não pode afirmar precisão que os dados não sustentam
status: in_progress
created_at: 2026-07-03
last_review: 2026-08-03
sprint_origem: A28
sprint_atual: A40
sprints_envolvidas: [A28, A40]
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-191]]"
  - "[[ADR-240]]"
  - "[[ADR-186]]"
  - "[[ADR-357]]"
  - "[[ADR-358]]"
tags:
  - type/plan
  - status/in-progress
  - area/e5
  - area/pipeline
  - area/frontend
  - area/llm
---

# Report Trust — o relatório não pode afirmar precisão que os dados não sustentam

> **Origem:** revisão completa do relatório dogfood `72883bde` (2026-07-03) —
> parecer do orquestrador + `financial-planner` + `product-designer`, seguido de
> co-design de sprint com `product-manager` + `information-architect` +
> `data-engineer` + `prompt-engineer`. Owner (CEO) priorizou explicitamente os
> P0 de fórmula/consistência e pediu sprint corrente.

## Tese

O relatório dogfood afirma completude e precisão que os dados não sustentam:
duas violações de fórmula canônica ([FORMULAS.md](../../reference/FORMULAS.md)
§Reserva · [[ADR-191]]), duas contradições cross-seção (PGBL com recomendações
opostas; duas bases de mensalização 2× diferentes sem rótulo), 23% das despesas
sem categoria, dados extraídos que não fluem (3 apólices presas no
`extract_comprovantes_bens` com balde E4 `seguros` vazio e `compute_protecao`
de [[ADR-240]] dead code), e apresentação sem sinalização agregada de qualidade.

**Três recomendações do relatório atual, se seguidas, PIORAM a situação do
cliente:** desacelerar aporte por TRS fictícia de 22,63% a.a. (dividendos da
própria PJ no numerador, só imóveis no denominador); desmobilizar carteira
produtiva por reserva "Excessiva" de 31,6 meses (numerador = todo o investível);
cortar gasto errado por rótulo Cerbasi "Gastador" (97,5% presente) sobre despesa
opaca — no mesmo relatório que celebra 28% de poupança. Para um produto
fiduciário em dogfood com critério de saída "refinar até perfeito antes de
abrir", isso bloqueia a saída do dogfood.

## Frentes

1. **Conformidade de fórmula (E5)** — reserva, TRS, PGBL, base de mensalização.
   Duas são bug contra contrato escrito (FORMULAS.md / ADR-191); duas exigem
   ADR `Proposto` (política de base temporal; regra de ano-base PGBL).
2. **Loop de dados (pipeline)** — categorização (`nao_identificado` 23% → <5%
   via Learning Loop [[ADR-186]]), proteção patrimonial (wire apólices →
   `compute_protecao`, ativa [[ADR-240]]), dedup da lista de imóveis excluídos
   ([[ADR-246]] na projeção), higiene de ingestão (períodos 1899/2100, banco
   vazio em keys E3).
3. **Apresentação honesta (frontend + E6)** — banner agregado de qualidade de
   dados, ressalva de fallback no Monte Carlo, formatador de âncoras por tipo,
   guardrails pós-LLM do parecer (confiança sob premissa fallback; filtro
   3-vias de `campos_faltantes`).
4. **Degradação honesta (execução → entregável)** — o run pode falhar; o
   entregável não pode desaparecer sem dizer por quê. Contrato de criticidade
   de stage, enforcement proporcional ao defeito, e o retido declarado na tela.
   Aberta 2026-08-03 pelo incidente do run `2ded7aab` — ver §Frente 4.

## Frente 4 — Degradação honesta (aberta 2026-08-03)

> **Tese:** as frentes 1–3 garantem que o relatório não afirme precisão que os
> dados não sustentam. Esta frente cobre a contrapositiva: o relatório **não foi
> produzido** — e, quando há retenção de conteúdo, **não a declara**.

### Incidente de origem

Run `2ded7aab` (workspace dogfood premium, 2026-07-31) marcado `failed` após
25m23s e US$ 1,5655. Os 17 stages anteriores passaram; o E5 fechou com artifact
de 123.498 bytes — **o relatório era derivável e não foi derivado**. Causa: o
guardrail `number_in_prose` (LLM digitou valor em R$ na prosa, **além** de emitir
a âncora) escalou para `needs_review` porque o item era severidade Crítica/Alta →
stage devolveu `success: False` → `_finalize_pipeline_outcome` pulou
`_run_post_processing` → zero linha em `reports`, e também zero lineage edge
([[ADR-279]]) e zero sync de status E2.

**Não é caso isolado.** Nos 9 últimos runs, `riscos_count` publicado =
12 − `items_dropped`, exato: **8 de 9 runs apagaram silenciosamente 1–4
conselhos** cuja citação estava verificada (`evidencia_failed: 0` em todos). E a
perda propaga a jusante: item dropado nunca vira `Suggestion` → nunca chega ao
Inbox de `/acao` → nunca vira Task/Decision ([[ADR-136]]). Como o defeito é
estocástico, o mesmo risco **pisca entre relatórios** sem explicação.

### Por que isto bloqueia o gate de saída do dogfood

O §Gate de saída exige **2 re-runs completos consecutivos**. Um run `failed` não
é re-run completo — e com 89% dos runs afetados o contador **não pode iniciar**.
O custo de não fazer não é US$ 1,5655 × N: é o beta não abrir.

### Conflito de ADR que autorizava o enforcement

[[ADR-296]] §Re-eval holdout (`Decidido`, owner-gated, 2026-06-20) julgou esta
questão e rejeitou os três remédios: *"Strip quebraria a prosa; drop perderia
item bom — então é **budget monitorado** (mediana 0 = maioria limpa), não
invariante `==0`"*. [[ADR-304]] §2 estabeleceu a doutrina oposta 12 dias depois
**sem `supersedes` nem emenda**, e §3 condicionou o enforcement a duas
pré-condições: *"quando a A27 for promovida"* + *"validar contra tráfego real"*.
A A27 segue `candidate`; o tráfego real **reprova** (89% vs 4,2% projetado). O
PR #875 violou as pré-condições da própria ADR que o autorizava.

Três medições mostram que o gate mirou o alvo errado:

- **Sub-citação é fail-open.** Item com `ancoras: []` não gera entry no
  verificador. O run tinha `ancoras_total: 6` contra mediana 11 ([[ADR-296]]) e
  14 ([[ADR-304]]): foi destruído por 3 itens que **citaram**, enquanto os que
  não citaram passariam. É **RV2-10** (ex-RV07), aberto, owner `prompt-engineer`.
- **O detector mede menos do que alega.** Inspeciona 3 campos de prosa dos 8+
  que a R22 cobre; `_MONEY_RE` exige `R$` e `_REAIS_RE` exige "reais", então
  **"US$ 50 mil" passa livre** num workspace com contas em USD.
- **A calibração está inflada na fonte.** `money_tokens_total` conta *matches*,
  não valores distintos (duplo-match dos dois regexes + 2 campos por risco) — o
  "61→7" da [[ADR-304]] mediu com régua inflada.

E o KR1 que motivou tudo é definido **sobre o holdout** (A27 §KRs: *"== 0 sobre
todas as gerações do holdout"*). Enforcement em produção não move KR de eval
sintético: erro de categoria.

### Invariante reformulado

O sistema **já publica número autorado pelo LLM** — `ImpactoEstimado.valor_estimado_brl`,
com `caveat` obrigatório e gate `confianca == "alta"`. Logo o invariante não é
"zero dígito na prosa", é:

> **Todo número que o leitor vê tem procedência declarada: âncora (verificada)
> ou estimativa (com caveat).**

Número digitado na prosa é um terceiro canal, **sem rótulo** — dano de
**clareza**, não de **correção**. Clareza se conserta no prompt e no renderer,
nunca deletando conselho. A doutrina certa já existe no repo: [[ADR-294]]/A28.l11
— guardrails que *"rebaixam/removem, nunca `needs_review`"*.

### Ondas

| Onda | Lane | Escopo | Prio |
| --- | --- | --- | --- |
| 0 — parar a sangria | [[A40.l16]] | `number_in_prose` fora de `_HARD_LAYERS` + emenda [[ADR-304]] + [[ADR-358]] `Proposto` | **P0** |
| 0 | [[A40.l17]] | Custo e cache no caminho `needs_review` | P1 |
| 1 — o contrato | [[A40.l18]] | Criticidade de stage + `partial_failure` alcançável ([[ADR-357]]) | **P0** |
| 1 | [[A40.l19]] | Migration do drift de enum (4 valores) | P1 + gate de deploy |
| 1 | [[A40.l20]] | `PlannerReview` representa "gerado e retido" | **P0** |
| 2 — a superfície | [[A40.l21]] | Leitores tolerantes a `partial_failure` (reader-first) | P0 |
| 2 | [[A40.l22]] | Estados de degradação no relatório + PDF | P1 |

**Ordem reader-first (não acoplar PRs).** Os 5 read sites de `partial_failure`
no frontend são **código morto hoje** (o status existe no union type e no
`format.ts`, mas nenhum writer o emite). Corrigi-los primeiro é PR coeso, de
risco zero e inalcançável em produção; só então [[A40.l18]] flippa o emissor.
Mesma disciplina expand/contract que o repo aplica a evolução de enum. Amarra:
se o writer escorregar >1 sprint, **reverta o leitor** — é dead code pelos
nossos critérios.

**[[A40.l20]] depende da *decisão*, não do *merge*, de [[A40.l18]]** — o
vocabulário de status é fixado pela [[ADR-357]] `Proposto`; implementar contra a
ADR permite mergear em paralelo.

### KRs

- **KR-0 · O entregável não se perde.** Todo run com artifact E5 válido produz
  linha em `reports`. Zero exceções, medido sobre 100% dos runs pós-[[A40.l18]].
  É o único KR que mede o que o incidente custou.
- **KR-1 · Conservação de conselho.** `emitidos − publicados == declarados na
  tela`; resíduo **não** declarado = 0. Não use `publicado == emitido`: retenção
  legítima (`pairing_mismatch` alta, sigilo) tem de continuar possível, e um `==`
  eterno só se mantém verde enfraquecendo enforcement legítimo. Medido em 2 runs
  reais — mesmo N do §Gate de saída, os mesmos runs pontuam nos dois.
- **KR-2 · Nenhum run morre por add-on.** 0 runs `failed` cujo conjunto de
  stages falhados ⊆ `{degradable}`. O peso está no **teste de injeção nos 3
  membros vivos** (`review_finances_holistic`, `generate_narratives`,
  `validate_cross`). Não é medível antes de [[A40.l18]] — ela cria o rótulo.
- **KR-3 · Honestidade renderizada.** Fixture com `items_dropped > 0` e fixture
  com parecer ausente ⇒ sinal assertado em 4 superfícies: seção, banner de
  qualidade, `/pipeline`, e **PDF via `pdftotext`**. O PDF é obrigatório: é a
  única superfície que sai do produto e chega a terceiros que não podem
  perguntar nada.

**Tripwire T1.** Se `items_dropped > 0` em >30% dos 5 primeiros runs pós-onda 0,
a resposta deixa de ser UI e escala para **RV2-10** + cobertura do catálogo de
citação (owner `prompt-engineer`); o banner shipa e é declarado insuficiente.

**Guardrail G1 ([[ADR-358]]).** Nenhuma camada de enforcement entra em caminho de
produção sem (a) ADR própria, (b) budget de produção declarado e medido em
tráfego real, (c) KR definido no mesmo plano onde o enforcement age. Sem G1, a
[[A40.l16]] é revertida pelo mesmo raciocínio que a produziu — a [[ADR-304]]
continuaria dizendo que "o caminho canônico é enforcement".

**Guardrail G2 (herdado, A40 §Decisões nº 5).** PR que altera número exibido
declara o sinal do delta e `dev/golden_diff.py` confere. A [[A40.l16]] declara
`riscos_count ↑`.

### Fora de escopo, com gatilho de descorte nomeado

- **Painel cru em `ops.mathoms.ai`** — cortado. Reach=1, e a audiência já tem
  substituto equivalente que já usou (a query de DB que produziu a série de 9
  runs). Descorta quando o beta abrir (audiência ≥5) **ou** T1 disparar.
- **Dead-letter do output retido** — P2, onda 3, por **gatilho** e não por data:
  ativa quando alguém re-propõe enforcement **ou** T1 dispara. Re-escopado para
  evidência **estruturada** da retenção (índice, camada, severidade, contadores,
  hash), nunca a prosa — retenção de texto não-vetado é a pior classe (alta
  sensibilidade, baixa revisão, prazo indefinido). Forma do artefato →
  `data-engineer` + `information-architect`.
- **Correção do detector R22** (8 campos, USD, valores distintos) — P2, e é
  **pré-condição de qualquer re-proposta de enforcement**.
- **Marcador na lista `/reports`** — P2. Com ~2 relatórios/mês a lista não é
  superfície de descoberta; o usuário chega por toast/redirect ou link direto.

### Nota honesta sobre "solução de longo prazo"

Para a [[A40.l16]] a solução de longo prazo **não é a reversão** — é o gerador
(**RV2-10** + cobertura do catálogo de citação), porque um guardrail de pureza de
prosa que dispara sobre *sintoma de âncora ausente* age na variável errada. A
reversão é correção **de instrumento**: devolve `number_in_prose` de enforcement
de produção para budget monitorado, que é onde a [[ADR-296]] já o havia posto.
Isto não é desistir da pureza de prosa — a §1 da [[ADR-304]] (fix de prompt,
88% de redução real) **permanece vigente e não é tocada**.

## Sinergia com [[PLAN-data-lineage]] (A26 `paused`)

Cada iteração desta frente re-gera o parecer E6 → produz as **≥20 gerações
reais** que destravam [[A26.l2]] (flip strict do `evidencia_path`) e exercita o
override v2 ([[A26.l4]]). Corrigir os inputs (TRS, reserva, mensalização)
**antes** de flipar o strict evita travar pareceres em massa por dados ruins.
A A26 retoma quando os gates de tráfego fecharem — esta frente é a máquina que
gera esse tráfego.

## Janelas

- **A28** ([sprint/A28/_README.md](../../sprint/A28/_README.md)) — 11 lanes em
  3 ondas: Onda 0 (fórmula, Must) → Onda 1 (dados) ∥ Onda 2 (apresentação,
  com trava de merge pós-Onda 0). Detalhe de corte e gates no MOC da sprint.
- Follow-ups candidatos a A29+ (fora do escopo A28): poda estrutural de
  `PropertyIdentity` órfãs (migration + backfill), saída do dogfood
  (gate de abertura), fuzzy dedup de investimentos cross-IRPF.

## Critério de done do plano

Re-run dogfood completo sem: violação de fórmula canônica, contradição
cross-seção, categoria dominante sem rótulo, dado extraído ausente do relatório,
projeção precisa sobre premissa fallback sem ressalva — verificado por goldens
+ testes de invariante + teste de honestidade de UX (ver KRs da A28).

### Gate de saída do dogfood (operacionalizado 2026-07-06)

> Antecipa o follow-up "gate de abertura" (antes reservado a A29): "refinar até
> perfeito" é insaturável (risco R6 de PHASES.md) — sem condição de parada
> binária, a iteração não termina e o beta nunca abre. Revisão
> `product-manager` 2026-07-06; precedente de forma: PHASES.md R9.

O dogfood pode encerrar (abrindo caminho para beta) quando:

- [ ] **2 re-runs completos consecutivos** (pipeline E0→E6 + parecer + revisão
  do owner) com **zero** ocorrência nas 5 classes acima; *N=2 é default
  proposto — owner pode recalibrar antes do primeiro re-run contar*.
- [ ] Nenhum item novo P0/P1 aberto pela revisão do owner nesses 2 re-runs
  (achados P2 viram backlog de A29+, não resetam o contador).
- [ ] Gates de owner da A28 executados (`G-owner-reclassify` +
  `G-owner-label`), para que os re-runs contem sobre dados curados.

Resposta que este gate habilita: "posso abrir o beta?" vira sim/não
verificável, não juízo de "está perfeito".
