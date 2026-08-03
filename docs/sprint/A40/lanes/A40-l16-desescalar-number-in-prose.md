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

> Onda 0 da A40 (§Frente 4 de [[PLAN-report-trust]]). **Se uma só coisa shipar, é
> esta:** destrava o relatório *e* devolve 1–4 conselhos/run à cadeia
> `Suggestion → Inbox /acao → Task/Decision` ([[ADR-136]]).

## Problema

`number_in_prose` está em `_HARD_LAYERS`
([`parecer_strict_enforcement.py:21`](../../../../backend/app/services/parecer_strict_enforcement.py)),
herdando a máquina drop/escalada da [[ADR-295]]. Consequência medida sob o
prompt vigente 2.2.0 (n=8 runs, 2026-07-22→07-31): **7 runs apagaram 1–4
conselhos** (16 itens) e **1 escalou** para `needs_review` → `success: False` →
run `failed` → zero linha em `reports` (25m23s, US$ 1,5655). São duas perdas de
natureza distinta; não somar. Tabela completa dos 19 runs da janela do contador:
[[ADR-304]] §Emenda 2026-08-03.

Em todos os runs `evidencia_failed: 0` — toda âncora **presente** resolveu certo
(item com `ancoras: []` não gera entry: fail-open, RV2-10). O defeito era o
número ter sido **digitado** na prosa em vez de vir renderizado da âncora.

**A premissa da [[ADR-295]] não transfere, por motivo estrutural.**
`number_in_prose` é **detector de presença, não de divergência**: o gatilho é
`if money_tokens:` e nada compara o token da prosa com
`ancoras[].valor_renderizado` (`MoneyToken.half_step_cents` é resíduo da era
`value_mismatch`, sem consumidor vivo). A camada portanto tem **zero informação
sobre correção**, enquanto a [[ADR-295]] escalou porque *"silenciar risco crítico
≡ emitir número errado"* — pressupõe sinal de erro. Escalar um entregável sobre
um sinal que não sabe se o número está certo é injustificável em qualquer volume
([[ADR-358]] §Decisão 1). Reverter **não perde capacidade de detecção**; perde um
proxy cego.

**A doutrina nunca foi coerente entre os dois planos, e isso é on-git:** o
`_HARD_LAYERS` do *eval* (`tests/test_parecer_evidencia_llm_eval.py`) tem 3
entradas e nunca incluiu a camada; o de *produção* tinha 4. O PR #875 adicionou o
enforcement em produção e **não** no instrumento que define o KR. A reversão
**restaura** a consistência ([[ADR-358]] §2).

**A causa raiz é outra lane.** O enforcement mergeou em 2026-07-08 e ficou
dormente por 11 runs (1/11, densidade de âncoras mediana 9). O bump de
`PROMPT_VERSION` 2.1.0→2.2.0 em 2026-07-21 (#1004, exec context) levou a 7/8, com
densidade 9→5 e tokens na prosa 0→3,5. Esta lane remove o **amplificador**; o
**gatilho** (exec context + RV2-10) segue aberto.

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
- **7 testes invertidos/adicionados em 3 arquivos** (a contagem de "3 testes em 1
  arquivo" desta lane estava incompleta): 3 em
  `tests/test_parecer_strict_enforcement.py` + **3 de integração** em
  `tests/test_parecer_evidencia_path.py::TestNumberInProseEhTelemetria` (que
  assertavam drop/escalada pelo caminho do stage) + o pin de versão em
  `TestCacheKeyBump`. Mais 2 testes novos: dedupe com **2 camadas hard** no mesmo
  item (a cobertura que o caso misto deixa de exercitar) e o lock de
  `_HARD_LAYERS`/`_LAYERS` ([[ADR-358]] §Auditável).
- **Budget declarado e medido, não ideal** ([[ADR-358]] §Decisão 2): baseline
  `number_in_prose` = **2,5 itens / 3,5 tokens** por parecer (mediana, n=8,
  prompt 2.2.0), densidade de âncoras mediana 5. Gate = *"não piora vs. baseline
  declarado, por `prompt_version`, janela ≥8 runs"*. **Não** "mediana ≤ 1" — isso
  é ideal, reprova no merge por 2,5× e faz a camada emudecer no 1º vermelho.
- Telemetria não regride: `failures_by_layer.number_in_prose` presente em todo
  run (garantido por `dict.fromkeys(_LAYERS, 0)` + teste de lock). Instrumento:
  `pipeline_stage_logs.output_summary` →
  `evidencia_verification.failures_by_layer.number_in_prose` (**itens**) e
  `.money_tokens_total` (**tokens** — unidades distintas, [[ADR-358]] §3).
- PII-safe verificado por **unit determinístico** sobre
  `NumberInProseWarning.format()` (`R$` ausente da mensagem), não por `rg` sobre
  log de produção: `_call_llm_safe` loga `str(exc)[:200]` no mesmo logger
  `mathoms.llm.parecer_planejador` e um `ValidationError` do Instructor pode ecoar
  prosa com `R$` — o critério por `rg` não é falsificável.
- **G2 (A40 §Decisões nº 5):** sinal declarado `riscos_count ↑`, **com delta
  on-git igual a 0** e duas razões independentes. (a) O golden do parecer é canned:
  3 riscos, **nenhum** com `R$` na prosa (`rg -c 'R\$'
  tests/test_parecer_planejador_golden.py` → 0 hits), logo a camada nunca dispara e
  a contagem não se move. (b) `dev/golden_diff.py` opera sobre **goldens numéricos
  de E5** (`tests/fixtures/pipeline_golden/dogfood/`); esta lane muda apenas
  pós-processamento de E6, fora do alcance da ferramenta — invocá-la aqui não é
  evidência de nada. A prova on-git é a **suíte verde sem rebaseline**
  (`pytest tests -q` + `pytest backend/tests -q`, incluindo o snapshot do
  view-model). `riscos_count ↑` e `items_dropped → 0` são **previsões de tráfego
  real**, confirmáveis só pós-merge.
- Tráfego real, próximos ≥2 runs (**pós-merge, fora do alcance do PR**):
  `items_dropped == 0` **por `number_in_prose`** — as outras 3 camadas hard
  continuam dropando, por decisão desta lane; zero run `failed` com
  `failures_by_layer.number_in_prose > 0`.
- Gates de doc verdes, incluindo `dev/check_adr_amendment_signal.py` com
  `amended_at: ["2026-08-03"]` na [[ADR-304]].

## O que o PR não pode afirmar

- **"Restaura 1–4 conselhos/run"** — é projeção sobre gerador estocástico. O
  medido é: 16 itens perdidos em 7 runs + 1 entregável.
- **"Destrava o gate de saída do dogfood"** — remove **uma** causa de `failed`.
  `needs_review` segue alcançável por red lines ([[ADR-300]]), sigilo §13, falha
  de LLM e `pairing_mismatch` de severidade alta.
- **"O incidente foi desfeito"** — os pareceres já entregues seguem truncados
  (artifact imutável, [[ADR-204]]); a retenção passada só é declarada em
  [[A40.l20]]/[[A40.l22]].
- **"O gerador está intacto"** (justificando não re-rodar o eval) — o gerador
  mudou em 2026-07-21. A forma sustentável: *este PR* não altera o gerador; o
  baseline do eval é **stale** e a re-medição está em
  [`OWNER-GATED-active`](../../../_MOC/OWNER-GATED-active.md) §2.
- **"O budget da [[ADR-296]] está cumprido"** — restaurado sim, cumprido não: 2,5
  itens / 3,5 tokens contra a "mediana 0". O PR sai **fora** do budget que
  restaura, e dizer isso é o que impede a próxima pessoa de re-derivar o
  enforcement do mesmo número.
- **"O bump de cache é precaução teórica"** — o inverso: o write mutilado de
  07-29 vive até 08-05 (TTL 7d) e o hit **suprime** `evidencia_summary`
  (`_hit_result` não popula), então validaria o fix com o artefato do bug. Mas
  também não afirmar que hits ocorreram: `cache_hit` foi 0 nos 19 runs medidos.
- Custo do bump: invalida 100% do cache do parecer → os ≥2 re-runs são cold miss
  (~US$ 1,5 cada, hard-stop [[ADR-173]] vale). Escopo da [[A40.l17]]; declarar no
  PR para não virar surpresa de FinOps.
