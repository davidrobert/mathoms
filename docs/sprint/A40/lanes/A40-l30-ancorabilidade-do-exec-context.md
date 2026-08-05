---
id: A40.l30
type: lane
title: "Ancorabilidade do exec context: o invariante que o #1004 furou sem nenhum teste vermelho"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l30-ancorabilidade-do-exec-context
adrs:
  - "[[ADR-341]]"
  - "[[ADR-296]]"
  - "[[ADR-358]]"
depends_on: []
parallel_with:
  - "[[A40.l17]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/backend
  - area/pipeline
  - area/llm
---

# A40.l30 — `ancorabilidade-do-exec-context`

> **Instrumento, US$ 0, sem geração nova.** É a causa que a [[A40.l16]] deixou
> viva ao remover o amplificador — mas **não** é "regressão do gerador", e o nome
> importa porque roteia o trabalho. Co-design `prompt-engineer` 2026-08-03: o
> nome anterior convidava a reescrever persona e a não medir nada.
>
> **Amarra de precedência:** a [[A40.l8]] **não mergeia sem o item 2** desta lane
> — ela projeta `context_section` no corpo orçado, que é exatamente a mutação que
> passou verde em #1004. Mesmo precedente instrumento-antes-de-mutação que o
> §Ondas declara para [[A40.l1]] → [[A40.l2]].

## Problema

A [[A40.l16]] mediu que o enforcement de `number_in_prose` ficou dormente por 11
runs (1/11, densidade de âncoras mediana 9) e saltou a 87,5% em 8 runs após o bump
`PROMPT_VERSION` 2.1.0→2.2.0 (#1004), com densidade **9→5** e tokens monetários em
prosa **0→3,5**. A l16 removeu o amplificador. O que sobrou tinha nome errado.

**O gerador não mudou — o input dele mudou.** Medido no diff de #1004
(`85860f79`): em `pipeline/llm/prompts/parecer_planejador.py` são **14 linhas**, e
são *só* a regra de recovery de eviction + o bump de versão + comentário. Nenhuma
regra de ancoragem foi tocada; a persona não foi tocada. No mesmo commit,
`backend/app/services/parecer_distiller.py` levou **158** linhas e
`config/prompts/parecer_planejador.yaml` **127** — [[ADR-341]] D1-D4: cap
8192→16384, 6→10 seções, blocos densos achatados, `narrative_hints` movidos para
**depois** do corpo.

**O mecanismo, medido in-process sem LLM** (n=24 fixtures do holdout, US$ 0 —
co-design `prompt-engineer`):

| observável | manifest 1.9 (pré-#1004) | manifest 2.0.2 |
|---|---|---|
| corpo do exec context (média) | 3.310 B | 4.425 B |
| **tokens `R$` renderizados no corpo** (média) | **9,0** | **18,0** |
| folhas monetárias citáveis no catálogo | 29 (cap = **30**) | 29 |
| cobertura ancorável (folha R$ visível ∈ catálogo) | 95% | 96% |

O número de valores monetários que o modelo **vê** dobrou e o conjunto
**ancorável** ficou igual — enquanto `_CATALOG_INSTRUCTION`
(`backend/app/services/parecer_citation_catalog.py:70-77`) manda literalmente
*"Conceito ausente daqui → não ancore"*. Digitar o número na prosa é o
comportamento que sobra.

> **Caveat da medição, declarado:** o manifest antigo rodou pelo distiller novo,
> então o delta é da **projeção**, não do code path completo. A direção é robusta;
> a magnitude no corpus real exige o E5 do dogfood — que é leitura local, US$ 0.

**Nenhum teste assere o invariante.** `tests/test_parecer_citation_catalog.py`
prova round-trip, prioridade e cap; `tests/test_parecer_distiller_catalog.py`
prova posição. **Nenhum** prova *"valor R$ renderizado no corpo ⇒ path no
catálogo"*. Foi por isso que #1004 mudou a composição do input com a suíte
inteira verde.

**O eval de US$ 26 não consegue ver este mecanismo.** Medido em
`tests/fixtures/parecer_eval.py`: `janela_12m`, `receita_por_natureza` e
`protecao_patrimonial` têm **0 hits** — três dos blocos que #1004 acrescentou ao
corpo estão ausentes do holdout. E o catálogo tem 29 entradas contra cap 30, logo
inanição de catálogo é **impossível** nesse corpus. Um run hoje responde "os gates
do eval ainda passam?", não "o #1004 causou a queda?".

**A métrica não tem denominador.** `backend/app/services/parecer_evidencia.py`
faz `ancoras_total += len(ancoras)` iterando só `riscos` + 3 horizontes de
sugestão (`_iter_items`). Consequências: item com `ancoras: []` contribui 0 e
**não gera entry** (fail-open — é o que explica `evidencia_failed: 0` nos 19
runs); `metricas[]`, `diagnostico_geral` e `notas_metodologicas[]` não são
iterados; e o detector inspeciona **3 campos dos 8+** que a R22 da persona cobre.
Portanto **`3,5` é piso, não medida** — é textualmente o defeito nº 3 da
[[ADR-358]], vivo. E sem contagem de itens no summary, "densidade" conflacia
*menos âncoras por item* com *menos itens*.

**Confounder não nomeado.** Entre 2.1.0 e 2.2.0 o payload E5 também mudou (#1006
shape de `passive_income`, #1010 bases da [[A37.l9]]), então parte do 9→5 pode ser
drift de payload. `prompt_version` **não** é estratificador suficiente;
`manifest_version` já está no summary de sucesso e resolve de graça.

## Escopo

1. **Denominador (2 campos).** `itens_total` e `itens_sem_ancora` no
   `EvidenciaVerification.summary`. Torna densidade interpretável e é o observável
   que RV2-10/RV2-01 vão precisar — esta lane **contribui** para elas, não depende.
2. **Invariante determinístico — o gate que faltava.** Check sobre o exec context
   **renderizado**: toda folha R$ que o modelo vê tem path no catálogo. Entra em
   **`warn` com baseline medido**; flip a fail só em PR próprio com prova
   red-before-green por mutação (padrão dos 8 ratchets da [[A40.l1]] — 4
   re-confirmados manualmente, ver lá §Fechamento, residual 4). **Não**
   instalar gate hard no mesmo PR que introduz a métrica.
3. **Re-medição retroativa dos 19 runs, US$ 0.**
   `pipeline/stages/parecer_planejador.py` já persiste
   `riscos_count`/`sugestoes_*_count`/`metricas_count` no `output_summary`, e
   `evidencia_verification` já traz `ancoras_total` + `items_dropped`. Densidade
   **por item** é computável hoje ⇒ decompõe o "9→5" em *menos âncoras por item*
   vs *menos itens*, estratificado por `(prompt_version, manifest_version)`.
4. **Dois sinais em `backend/app/services/parecer_drift_monitor.py`:**
   `ancoras_por_item_delta` e `prosa_monetaria_rate_delta`, na banda
   `max(floor, 2·SE)` que já existe. Fonte é
   `pipeline_stage_logs.output_summary` — `LLMCallLog` não carrega os campos
   (`backend/app/models/llm_call_log.py`) e **não** deve ganhar 2 colunas por isso.
5. **Paridade fixture↔manifest:** check que falha quando o manifest projeta bloco
   ausente do holdout. Hoje falharia em 3 — é o que torna o eval cego.
6. **ADR `Proposto`** ("todo valor monetário visível no exec context é ancorável;
   densidade mede-se por item e por delta de versão"), estendendo [[ADR-341]] e
   [[ADR-296]]. Exigida por [[ADR-358]] §Decisão 1 e pelo CLAUDE.md §Política
   operacional. **ID alocado na escrita** — não reservar em prosa (convenção do
   CLAUDE.md; precedente [[ADR-345]]).
7. **Ampliar o inventário de campos do detector** de 3 para os 8+ da R22 **antes**
   de qualquer re-baseline de prosa monetária — senão re-baselina-se um piso.

## Critério de aceite

- `itens_total` + `itens_sem_ancora` no `output_summary`; unit prova que item com
  `ancoras: []` é contado.
- Check de ancorabilidade roda em CI em `warn`, com baseline por corpus
  registrado, e **prova de mutação nos dois sentidos**: acrescentar bloco R$ fora
  do catálogo ⇒ sinal; remover ⇒ limpo.
- Paridade fixture↔manifest **falha hoje** nos 3 blocos ausentes e fica verde
  depois de acrescentá-los à fixture sintética. PII-zero: `rg` de CPF e de
  `R$ n.nnn` em `config/prompts/` e nas fixtures = 0 hits.
- Tabela dos 19 runs por `(prompt_version, manifest_version)` com densidade **por
  item** e `items_dropped`, **com o path off-git anotado** (§Pendência nº 8).
- 2 sinais novos em `parecer_drift_monitor` com `verdict` provado por fixture;
  namespace `mathoms.llm.*` ([[ADR-110]]).
- ADR `Proposto` escrita; gates de doc verdes (`validate_frontmatter`,
  `check_doc_links`, `check_adr_anchors`).
- Suíte verde **sem** rebaseline: `pytest tests -q` + `pytest backend/tests -q`,
  rodados da **raiz** do repo.

## Fora de escopo

- **Mexer no gerador.** É a [[A40.l31]], que não abre antes do item 3 aqui nomear
  o mecanismo.
- **Re-rodar o eval de US$ 26.** Continua owner-gated em
  [`OWNER-GATED-active`](../../../_MOC/OWNER-GATED-active.md) §2, e hoje rodaria
  num corpus sem 3 dos blocos e com catálogo sob o cap. Vira **gate de saída** da
  l31, não de entrada desta.
- **`depends_on: RV2-10`.** A dependência é da *métrica*, não do *fix*, e
  resolve-se declarando o denominador (item 1), não esperando.
- **Matar o `number_in_prose_median == 0` do eval**
  (`tests/test_parecer_evidencia_llm_eval.py:183`) — é o mesmo antipadrão que a
  [[ADR-358]] §Decisão 2 condenou, sobrevivendo no eval, mas trocá-lo exige o
  inventário ampliado (item 7) primeiro. Sai na l31.
- **Re-baselinar `_DENSITY_FLOOR` para 5** (`:39`). É **erro de categoria**, não só
  Goodhart: o piso gateia o holdout **sintético**, onde a [[ADR-296]] §Re-eval
  mediu densidade mediana **11**; o "5" é do **dogfood em produção**. Igualar os
  dois é o defeito nº 2 da [[ADR-358]] (gate medido num plano, aplicado em outro).
  Coincidência numérica.

## Handoff (achados do co-design que não são desta lane)

- **`narrative_hints_global`** (`config/prompts/parecer_planejador.yaml`) é config
  morta: `ManifestData` não tem o campo e `load_manifest` não lê a chave. Não é
  defeito vivo — é **botão que mente**, mesma classe de
  `max_total_input_tokens`/`max_tool_iterations` que o painel roteou para a
  [[A40.l8]]. → **[[A40.l8]]**, owner `prompt-engineer`.
- **Três linhas do [[PLAN-pipeline-review-r2]] estão em drift** (não editadas
  aqui: plano com dono ativo): reserva "ADR-354" em prosa para a RV2-01, mas esse
  ID é da [[A40.l2]] desde #1114; planeja `EVIDENCIA_VERIFICATION_VERSION` 4→5, que
  a l16 já gastou (hoje `"5"`), logo tem de ser 5→6; e o `PROMPT_VERSION`
  2.2.0→2.3.0 da RV2-01 colide com o bump da [[A40.l31]].
- **Custo do harness divergente:** `_COST_CAP_USD = 50.0` e o comentário em
  `tests/test_parecer_evidencia_llm_eval.py:41` dizem *"~US$29/run observado"*
  contra os *"~US$ 26"* da `OWNER-GATED-active` §2. Alinhar ao re-escopar a entrada.
