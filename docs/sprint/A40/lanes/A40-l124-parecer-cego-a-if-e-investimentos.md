---
id: A40.l124
type: lane
title: "O parecer não vê independência financeira nem investimentos desde agosto: o corpo pede ~20 KB contra 16 KB, a eviction é muda e o teste que a vigia mede 40% do tamanho real"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 2173
ship_date: "2026-10-09"
priority: P1
branch_slug: parecer-exec-context-orcamento
owner: prompt-engineer
depends_on: []
adrs: ["[[ADR-341]]", "[[ADR-340]]"]
tags: [type/lane, sprint/a40, status/shipped, priority/p1, area/llm]
---

# A40.l124 — `parecer-exec-context-orcamento`

> **Origem:** item 2 do §Deferimento da [[A40.l123]] (PR #2117) e `PV13-17` de
> [[PIPELINE-REVIEWS-active]] §r13, que ficou "sem lane" apontando para a ADR errada.
> Co-design 2026-10-09 com `prompt-engineer`, `product-manager` e `data-engineer`: uma
> rodada de ajuste, nenhuma objeção bloqueante. **Fora da cláusula de reinício** da A40
> (não muta E3/E5 — só a projeção para o E6), mas **dentro** da definição de re-run
> completo: ver a nota de 2026-10-09 no §Gate de saída do [[MOC-sprint-a40]].

## O defeito, medido

O corpo do exec context do parecer é orçado em `max_exec_context_bytes` (16384) e, excedido,
perde **seções inteiras** por `eviction_priority` ([[ADR-341]] D2). Medido no E5 do run
`40d1af2a` com o caminho de produção (`sanitize_e5_for_parecer` antes de destilar), só bytes
e ids de seção, versão do manifest de cada run sobre o E5 do próprio run:

| run | data | manifest | demanda do corpo (B) | evictadas |
|---|---|---|---|---|
| `ee124571` | 08-11 | 2.0.4 | 16059 | — (folga de 2%) |
| `33514dc4` | 08-18 | 2.0.5 | 15904 | — |
| `c97b97c2` | 08-26 | 2.3.0 | 18696 | `plano_acao_atual`, `investimentos` |
| `79a61e33` | 08-29 | 2.7.0 | 19544 | + `independencia_financeira` |
| `40d1af2a` | 09-01 | 2.18.0 | 19497 | idem |
| — | — | 2.21.0 (#2117) | 19912 | idem |

**O efeito no output é um experimento natural.** Em `planner_field_requests`, o parecer passa a
pedir como "faltante" exatamente o que foi evictado: `$.investimentos.alocacao_alvo` aparece a
partir de 08-26, `$.if_monte_carlo` e `$.passive_income` a partir de 08-29, e antes de 08-26
nenhum. No run `40d1af2a`, 3 dos 4 pedidos têm raiz em seção evictada. Os `narrative_hints`
dessas seções seguiam anexados fora do orçamento, orientando sobre dado ausente do corpo.

**Por que ninguém viu em seis semanas — três camadas:**

1. **Muda.** O marcador de eviction só existia dentro do prompt; orchestrator e stage não
   publicavam bytes nem seções. Medir exigia decifrar o E5 à mão.
2. **Instrumento falso-verde.** `test_all_sections_present_with_dense_payload` afirma 10/10
   seções sobre `make_dogfood_like_e5()`, que renderiza 8048 B — **40%** do corpo real, com 7
   blocos rendendo 0 B. Estruturalmente incapaz de exibir a eviction (cláusula 2 da §6.1 do
   runbook ⇒ P1).
3. **Registro com ponteiro errado.** O `PV13-17` atribuía a seleção à "Fase 2 da [[ADR-349]]"
   — que é o re-route de `classify_by_llm` pelo `LLMService`. E o "42,9% do orçamento de tokens
   ocioso" mede contra `max_total_input_tokens: 50000`, que é parseado e **não tem consumidor**:
   o corte era do orçamento de bytes, subdimensionado, não de seleção.

**A próxima seção da fila é `ratios`**, com ~130–330 B de folga. Ela hospeda o input da RL7
`block` (`parecer_red_lines.py::_severidade_exigida_concentracao`): evictá-la trocaria
degradação por parecer retido.

## Decisão

| peça | decisão |
|---|---|
| Telemetria | `ExecContextBudget` medido do MESMO plano de eviction que montou o corpo (bytes pedidos/enviados, por seção, evictadas em ordem, corte degenerado, hints e catálogo). Evento `parecer_planejador_exec_context` antes da chamada, WARNING sob eviction. Persistido no status do stage ⇒ `pipeline_stage_logs.output_summary` (texto claro) nos dois desfechos — **não** no `_meta`, que é cifrado (`data-engineer`). Cache hit lê do envelope; recomputar descreveria um corpo que o modelo não viu, porque o distiller não compõe a chave |
| Leitor | X8 da rodada unificada: seções fora do corpo + folga < 15%. Ausente ⇒ INAPLICAVEL, nunca verde |
| Orçamento | cap 16384 → 24576, pela regra de folga da [[ADR-341]] §Emenda 2026-10-09 |
| `top_ativos` | `max_rows` 15 → 5, título nomeando o corte do produtor (lista até 15), e o cabeçalho de tabela passa a dizer "top N de M" |
| Catálogo | `citation_catalog.max_bytes` 2600 → 3400 (joelho re-medido, protocolo da A40.l83) |

**Os dois knobs não são enxugamento: são o preço de devolver as seções.** Medido no E5 real com
o cap novo: com 15 linhas de `top_ativos`, ancoráveis caem de 33/36 (91,7%) para 33/50 (66,0%)
— o catálogo fica preso pelo próprio orçamento — e o teto é 80% em qualquer orçamento, porque o
catálogo pega só as 5 maiores de cada lista. Com 5 linhas e 3400 B: **40/41 (97,6%)**, demanda
18787 B, folga 23,6%. Sem eles a lane fecharia a eviction e reabriria a classe da A40.l83.

## Critério de aceite — itens 1 a 5 batidos em 2026-10-09 (#2173)

1. ✅ Com eviction forçada, o orçamento publicado nomeia as mesmas seções que o marcador enviado
   ao modelo, e remover a escrita reprova: **7 mutações do produtor** pegam (stage sem a escrita,
   resultado sem o orçamento, envelope lido ou gravado sem ele, evento sempre INFO, ids fora de
   ordem, corte degenerado não declarado).
2. ✅ X8 com os três desfechos provados — e **3 mutações do leitor** pegam. No run `40d1af2a`
   (anterior à telemetria) ele sai `INAPLICAVEL`, como deve.
3. ✅ Medição in-process no E5 do run `40d1af2a`, sanitizado, com o manifest 2.23.0: **10/10
   seções** (eram 7/10), folga **23,3%**, ancoráveis **40/41 — 97,6%** (eram 33/36), catálogo
   44 de 60 entradas em 3340 B. Sem corte degenerado.
4. ✅ O teste "10/10" declara que mede o mecanismo; o aceite da [[A40.l85]] passa a incluir bytes.
5. ✅ Emenda datada da [[ADR-341]]: D1 vira regra de folga; D7 publica a eviction.
6. PR #2173 mergeado em `main` com CI verde — único PR da lane (o plano de dois PRs caiu quando o
   #2117 mergeou antes).

**Predição registrada antes da regeneração (observação, não gate — a §Emenda 2026-09-01 da
[[ADR-341]] veta contar `campos_faltantes` como critério):** no primeiro parecer gerado com o
manifest 2.23.0, `evicted_section_ids == []` e zero pedidos com raiz em `$.investimentos`,
`$.if_monte_carlo`, `$.passive_income`, `$.cenarios_conjuge` ou `$.goals`, contados por **raiz
de path em todos os `reason`** — a persistência hoje troca o rótulo de `out_of_catalog` (item 5
abaixo) sem perder a linha. Os pedidos de `taxa_juros_aa` **não** devem cair. Se a predição
falhar: N=3, owner-gated.

## Deferimento datado — 2026-10-09

1. **Gate de CI com corpus calibrado** → [[A40.l85]] (aceite emendado nesta data). Bytes
   congelados num snapshot testariam uma constante; o corpus de cardinalidade real, não.
2. **Input de red line `block` em seção de prioridade baixa** (RL7 lê `ratios`, p7): mover o
   escalar de concentração e gatear "todo path lido por red line `block` mora em prioridade
   ≤ 4". Dono `prompt-engineer` + `financial-planner`. Retomada: X8-folga < 15% ou qualquer
   eviction de `ratios`. Com 24 KB e 5 linhas, `ratios` só sai acima de ~27 KB de demanda.
3. **`max_total_input_tokens` sem consumidor:** alarme pós-call sobre `tokens_in` real. Dono
   `prompt-engineer`. Retomada: próxima mudança de system prompt ou de persona.
4. **Contador OTLP, card em `/admin/metrics` e alerta de produção (< 10%)**. Dono `sre-devops` +
   `data-engineer`. Retomada: primeiro workspace fora do dogfood.
5. **`field_request_out_of_catalog` nunca chega a `planner_field_requests`:**
   `_partition_campos` mantém a entrada no array e no audit, e `_persist_field_requests`
   deduplica por path com o array primeiro. Tarefa própria.
6. **RL7 tem três réguas:** REGRA 14 do system prompt (60/40), validador (75/50) e hint do
   manifest (50/75). Tarefa própria; dono `prompt-engineer` + `financial-planner`. ✅ Entregue
   no #2211 (2026-10-09): régua única pela [[ADR-340]] §Emenda 2026-10-09, manifest 2.22.0 —
   por isso esta lane sai na 2.23.0.
7. **Blocos `key_value` sem teto de folhas** (`$.ratios`, `$.protecao_patrimonial`) crescem com
   o dado sem ninguém mexer no manifest. `max_leaves` por bloco é DSL nova ([[ADR-200]]). Dono
   `prompt-engineer` + `information-architect`. Retomada: X8-folga < 15%.
