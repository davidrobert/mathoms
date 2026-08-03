---
id: A40.l16
type: lane
title: "Desescalar number_in_prose: defeito de forma deixa de apagar conselho e de derrubar o run"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l16-desescalar-number-in-prose
adrs:
  - "[[ADR-304]]"
  - "[[ADR-358]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/llm
  - area/backend
---

# A40.l16 — `desescalar-number-in-prose`

> Onda 0 do §Frente 4 de [[PLAN-report-trust]]. **Se uma só coisa shipar, é
> esta:** destrava o relatório *e* devolve 1–4 conselhos/run à cadeia
> `Suggestion → Inbox /acao → Task/Decision` ([[ADR-136]]).

## Problema

`number_in_prose` está em `_HARD_LAYERS`
([`parecer_strict_enforcement.py:21`](../../../../backend/app/services/parecer_strict_enforcement.py)),
herdando a máquina drop/escalada da [[ADR-295]]. Consequência medida em 9 runs:
item de baixa/média severidade com o defeito é **apagado** (8/9 runs, 1–4 itens),
e item Crítica/Alta escala para `needs_review` → `success: False` → run `failed`
→ **zero linha em `reports`** (run `2ded7aab`, 25m23s, US$ 1,5655).

Em todos os runs `evidencia_failed: 0` — as citações estavam corretas. O único
defeito era o número ter sido **digitado** na prosa em vez de vir renderizado da
âncora.

A justificativa da [[ADR-295]] (*"silenciar risco crítico ≡ emitir número
errado"*) pressupõe **número errado sendo emitido**. Aqui a âncora resolveu
certo, então a premissa é falsa e a doutrina não transfere. O próprio código já
classifica a camada como de natureza distinta: *"nem cobertura nem correção de
citação; não entra em `coverage/correctness_failed`"*.

## Decisão

1. **`"number_in_prose"` sai de `_HARD_LAYERS`.** Permanece em `_LAYERS`
   (telemetria) e fora de `coverage_failed`/`correctness_failed`, como já está.
   Restaura [[ADR-296]] §Re-eval holdout: budget monitorado, não invariante `==0`.
2. **`EVIDENCIA_VERIFICATION_VERSION` "4"→"5"**, com comentário citando a
   reversão. Obrigatório: cache sob `ev4` guarda outputs **já mutilados** (itens
   dropados) e um hit serviria a mutilação por até 7 dias.
3. **`PROMPT_VERSION` permanece 2.2.0.** O gerador não muda; bumpar mentiria no
   log e quebraria a comparabilidade com o baseline do eval.
4. **Nenhuma re-rodada do eval de US$ 26.** O eval mede o gerador, que está
   intacto.
5. **Emenda datada em [[ADR-304]]** (§2 e §3 revogadas, §1 mantida) + ponteiro na
   [[ADR-296]] §Re-eval + [[ADR-358]] `Proposto` — sem ela a reversão é
   reversível pelo mesmo raciocínio que a produziu.

**Rejeitados, com motivo registrado:** strip do token ([[ADR-296]]: *"quebraria a
prosa"*); substituir pelo valor da âncora (é o **D1** que [[ADR-296]]
§Alternativas rejeitadas marca "Vetada" — *"verificador vira gerador"* — e a
forma D2-puro é decisão do owner de 2026-06-19); dropar sempre sem escalar
(mantém a perda endêmica); cirurgia mecânica em prosa entregue ao cliente.

## Critério de aceite

- `_HARD_LAYERS` sem `number_in_prose`; `EVIDENCIA_VERIFICATION_VERSION == "5"`;
  `PROMPT_VERSION` inalterado.
- Regressão: `enforce_strict_per_item(out, ["risco:0:number_in_prose"])` com
  risco `Crítica` → `needs_review_reason is None`, `dropped == ()`, item
  preservado. Caso misto com `pairing_mismatch` **continua** dropando 1 item,
  pelo pairing.
- Os 3 testes de `tests/test_parecer_strict_enforcement.py` que assertam o
  comportamento antigo são invertidos.
- Tráfego real, próximos ≥2 runs: `items_dropped == 0` por `number_in_prose`;
  `riscos_count` publicado == emitidos; zero run `failed` com
  `failures_by_layer.number_in_prose > 0`.
- Telemetria não regride: `failures_by_layer.number_in_prose` presente em todo
  run; mediana por run ≤ 1 (budget [[ADR-296]]).
- `rg -n 'R\$ ?[0-9]'` nos logs de `mathoms.llm.parecer_planejador`: zero hits
  (só contagem + camada, padrão PII-safe de `NumberInProseWarning`).
- **G2 (A40 §Decisões nº 5):** PR declara o sinal do delta — `riscos_count ↑` — e
  `dev/golden_diff.py` confere.
- Gates de doc verdes, incluindo `dev/check_adr_amendment_signal.py` com
  `amended_at: ["2026-08-03"]` na [[ADR-304]].
