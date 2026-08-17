---
id: A40.l49
type: lane
title: "Parecer: rótulo de evidência derivado do root do path, e dois guardrails que não podem disparar"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1487
ship_date: "2026-08-17"
priority: P1
branch_slug: a40-l49-parecer-rotulo-e-guardrails
owner: prompt-engineer
adrs:
  - "[[ADR-296]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/backend
  - area/llm
---

# A40.l49 — `l49-parecer-rotulo-e-guardrails`

> **Aberta em 2026-08-12**, da revisão r4 registrada em [[REPORT-REVIEWS-active]]
> §r4 (report `7a7d7115` sobre run `ee124571`). Dono: `prompt-engineer`.
> Agrupada **por domínio de dono**, não por severidade: os achados aqui precisam
> do mesmo especialista para fechar, e lane com donos distintos não fecha.
>
> ✅ **Entregue em 2026-08-17 pelo PR #1487** (`cb9253eb`). Os três guardrails
> passam a poder falhar: pairing contra `citation_labels` (não o root);
> rebaixamento de MC por S7+lemma; pedido com ano sem cobertura não é
> SPURIOUS. `needs_review_triggered` espelha evidencia/red-line ([[ADR-295]]),
> não o limiar 0,7 da [[ADR-081]] — correção do enunciado original. Emenda
> [[ADR-296]] 2026-08-16. RV5-02 (dependente fantasma) ficou fora.

## Problema

Três defeitos do parecer que a r4 confirmou, unidos por não serem de **prompt** —
são de **verificação**: o que deveria checar o output do LLM está escrito de forma
que não pode falhar.

1. **O rótulo do chip de evidência vem do root do JSONPath**, então campos
   distintos do mesmo bloco recebem rótulo idêntico. Medido: três campos de
   `passive_income` renderizam como "Renda passiva" na mesma página, um deles
   sendo renda **ativa** excluída e outro sendo **patrimônio**. E o cross-check
   exige `rotulo == path[2:].split(".")[0]` — exatamente a identidade que produz o
   erro, então todas as entradas de `evidencia_verification` saem `verified`.
2. **O guardrail que rebaixa confiança sob premissa em fallback tem cobertura
   zero por construção:** exige âncora começando em `$.if_monte_carlo`, e
   **nenhuma** âncora do parecer toca esse bloco. Os itens que de fato dependem do
   MC citam-no em **prosa**, forma que o gate não lê. Correlato na mesma função:
   `needs_review_triggered` é `False` literal, o que contraria o contrato
   [[ADR-081]] (`confidence < 0,7` ⇒ `needs_review`).
3. **O classificador de pedido-de-campo ignora a dimensão ano.** O LLM pediu um
   KPI declarando "para 2025 está indisponível"; o classificador resolveu o path,
   achou o valor do **ano-base anterior**, marcou `SPURIOUS` e **deletou** o pedido
   antes de gravá-lo. Um de quatro pedidos foi destruído acusando o LLM de um gap
   que é do campo.

## Achados cobertos

RV4-11 (Alto) · RV4-14 (Médio, inclui o correlato `needs_review_triggered`) ·
RV4-17 (Médio). Registro: [[REPORT-REVIEWS-active]] §r4.

## Escopo

**PR1 — rótulo por campo, não por bloco.** O rótulo do chip deriva do **leaf** do
path (ou de um mapa explícito campo→rótulo), e o cross-check deixa de comparar o
rótulo com o próprio root. Aceite: fixture com dois campos do mesmo bloco ⇒ dois
rótulos distintos; **mutação que volta ao root derruba o teste**.

**PR2 — os dois guardrails passam a poder falhar.** O rebaixamento por premissa em
fallback deixa de depender de âncora num bloco que ninguém ancora — o sinal tem de
ser o que o item usa de fato. `needs_review_triggered` passa a derivar de estado,
não de literal. Aceite: fixture com premissa em fallback ⇒ `confianca_rebaixada > 0`;
fixture abaixo do limiar ⇒ `needs_review_triggered` verdadeiro.

**PR3 — classificador respeita a dimensão ano.** Pedido cujo motivo nomeia um ano
sem cobertura não é espúrio. Aceite: o pedido do corpus de dogfood sobrevive ao
filtro e chega a `PlannerFieldRequest`.

## Critério de aceite da lane

Nenhum dos três guardrails pode ficar verde por construção: cada um tem um teste
em que ele **falha**. Um guardrail que não sabe falhar não é guardrail — é
decoração, e essa é a classe que une os três achados.

## Não-objetivos com rota declarada

Mexer no prompt, no model ou no seed: nada aqui é de geração, é de verificação
pós-geração. Reescrever a ancorabilidade do exec context — é a [[A40.l30]],
`shipped`.

## Entregue — 2026-08-17

Um PR cobriu os três itens do escopo (#1487 · `cb9253eb`):

1. Mapa `citation_labels` path→`{rotulo_id, label}`; pairing contra o mapa;
   path ausente é fail-open (`unmapped_leaf`). Mutação root-split falha.
2. MC: S7 + lemma na prosa (ou âncora `$.if_monte_carlo`). Tema sozinho não
   rebaixa. `needs_review_triggered` espelha evidencia/red-line.
3. Motivo que nomeia um ano sem cobertura completa no E5 deixa de ser
   SPURIOUS.

Fora: RV5-02 (dependente fantasma).
