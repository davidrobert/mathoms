---
id: ADR-281
type: adr
title: "rule_ref derivado de dict literal + lineage_diff (substrato de debug LLM)"
status: Decidido
phase: "A23 · F0"
date: "2026-06-02"
amended_at: ["2026-08-30", "2026-09-01", "2026-09-02"]
relates_to:
  - "[[ADR-143]]"
  - "[[ADR-111]]"
  - "[[ADR-116]]"
supersedes:
  - "[[ADR-045]]"
superseded_by: []
aliases: ["ADR 281", "rule_ref", "lineage_diff", "lineage debug substrate"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/data-lineage
  - area/llm
---

# ADR-281 — rule_ref derivado de dict literal + lineage_diff (substrato de debug LLM)

**Status:** Decidido (A23 · F0) • **Data:** 2026-06-02 • **Relaciona** [[ADR-143]], [[ADR-111]], [[ADR-116]] • **Supersede** [[ADR-045]].

> Camada D do plano [[PLAN-data-lineage]]. Gate F0 — **resolve B2**. Estende/supersede
> [[ADR-045]] (data lineage via tooltip — drill-down "para futuro"; este é esse futuro).
> Decisão fechada; lanes de implementação conformam.
>
> **Emendada 2026-08-30 ([[A27.l2]]):** o `check_lineage_refs` prometido abaixo é
> **existência pura** — não mede cobertura — e o eval derivava `expected` do próprio
> registro. Ver §Emenda no fim.

**Contexto:** o lineage precisa ser legível por um LLM (agente de debug OU Claude Code no repo) para saltar de "número errado" → "função a corrigir". Exige bridge nó→código refactor-safe e diff de regressão determinístico. A [[ADR-045]] decidiu o tooltip de UI e adiou o drill-down; aqui materializamos o substrato.

**Decisão:**
- **Bridge nó→código:** **dict literal eager** `pipeline/domain/lineage_registry.py` (`{rule_id: "module:qualname", adr}`) — **não** decorator import-side-effect (banido por CLAUDE.md §Dependências; não cabe na exceção [[ADR-111]] (a), que é p/ constantes). Refactor-safe vem do gate `dev/check_lineage_refs.py` (resolve `module:qualname` por import real + ADR existe). Registrar em `STATELESS_AUDIT.md §2` (B2).
- **Renderer LLM:** trace linearizada (passos numerados raiz→folha, inputs como `#N`), teto ~1.5k tokens inline, anomaly-first ordering. Distinto do renderer humano (tooltip [[ADR-045]]).
- **`lineage_diff`** puro/stateless: só nós mudados + `first-divergent-leaf` + propagação anotada.
- **Tools:** `explain_number`/`expand_node`/`trace_source` (cap `max_expand_iterations:6`, whitelist de `field`). Superfície: core de domínio (Claude Code sobre goldens, dia 1); MCP read-only no console interno ([[ADR-116]], `workspace_id` obrigatório, zero mutação) — fase posterior.
- **Eval:** injeção determinística de bug; `localization_accuracy@node ≥ 85%`.

**Consequências:**
- ✅ LLM (Claude Code no repo OU agente de debug) salta de "número errado" → `rule_ref` → função exata. Bridge refactor-safe: o gate `check_lineage_refs` quebra se o `module:qualname` não resolve por import real, então rename sem atualizar o dict é pego no pre-commit.
- ✅ Supersede [[ADR-045]] (bidirecional: `superseded_by` no frontmatter de 045 já aponta para cá): o tooltip vira o **renderer humano**; o renderer LLM linearizado é a face de debug do mesmo grafo.
- ⚠️ **Rejeitado decorator `@lineage_rule`** (import-side-effect banido por CLAUDE.md §Dependências; não cabe na exceção [[ADR-111]] (a), que é p/ *constantes*, não registry populado por side-effect). Dict literal eager registrado em `STATELESS_AUDIT.md §2` como mapping de domínio imutável.
- ⚠️ **MCP prod do debug substrate + índice reverso por `rule_ref` deferidos** (YAGNI) até um agente fechar o loop "número errado → função" sobre goldens (F7). Não construir observability platform antes da pergunta de impacto real.
- ⚠️ Eval de injeção de bug (F7): `localization_accuracy@node ≥ 85%` (regressão >2% bloqueia merge), temp=0/seed/model pinados; o renderer LLM e o `lineage_diff` são `pipeline/domain/services/*` puros/stateless (não importam framework).

## Emenda 2026-08-30 — cobertura medida contra o payload; ground truth do eval sai do registro (A27.l2)

> ⚠️ **O número desta emenda foi corrigido em 2026-09-01** (A27.l3): `5/14 = 35,7%` é a
> cobertura da **fixture dogfood**, não a do E5. O denominador correto é **17** e a
> cobertura é **29,4%** — ver a emenda seguinte antes de citar a tabela abaixo.

**O que a decisão original afirmava:** que `check_lineage_refs` torna o bridge
refactor-safe. **Verdadeiro, e insuficiente** — ele resolve `module:qualname` e checa a
ADR, mas não tem noção de **cobertura**. Somado a um eval cujo `expected_rule_ref` saía de
`LINEAGE_RULE_REFS[rule_id]["ref"]`, acrescentar raiz ao E5 sem entrada no registro não
movia o gate nem a `localization_accuracy@node`: gate que só podia dar verde.

**Medido em 2026-08-30** (fixture dogfood sintética, `tests/pipeline_golden_substrate`):

| Medida | Valor |
| --- | --- |
| Raízes do payload que publicam dinheiro | 14 |
| Raízes com nó em `_lineage.fields` | 5 (`patrimonio`, `fluxo_caixa`, `investimentos`, `reserva_emergencia`, `endividamento`) |
| **Cobertura** | **5/14 = 35,7%** |
| `rule_id` do registro sem nenhum caso de eval | 4 de 8 |
| Refs distintos exercitados pelos 29 casos | 4 (contra 6 no registro; refs são compartilhados entre `rule_id`) |

**Emenda à decisão:**

- **O denominador da cobertura vem do payload publicado, nunca do registro.** Derivá-lo do
  registro devolve 100% por construção. O discriminante de "raiz que deve ter rastro" é
  `golden_diff.is_monetary` (monetário-por-default, [[ADR-090]]) — escolhido por classificar
  campo **sem consultar** o registro, que é o que mantém numerador e denominador
  independentes. Raiz em prosa/metadado fica fora: medir contra as 38 raízes do schema dava
  teto inalcançável, e KR que não pode chegar a 100% é KR que ninguém persegue.
- **O eval não deriva ground truth do registro que avalia.** `cases._EXPECTED_REFS` declara
  os refs por extenso; o cross-check por `rule_id` passa a poder falhar. Ler o registro para
  **fabricar a mutação** (`_swap_rule` — o bug injetado precisa citar enforcer que existe)
  segue legítimo: o que saiu foi o ground truth, não a mutação.
- **Gate compara conjunto, não contagem.** Raiz renomeada ou trocada não passa por
  compensação numérica.

**Enforcers:** `dev/lineage_coverage.py` (medida) · `tests/test_lineage_coverage.py` (gate +
controle positivo: raiz monetária sintética derruba a métrica e reprova, enquanto
`check_lineage_refs` segue verde na mesma mutação) ·
`tests/lineage_eval/test_eval_deterministic.py::test_expected_refs_declarados_batem_com_o_registro`.

**Não muda:** o bridge por dict literal eager, o renderer LLM, o `lineage_diff`, nem o
alvo `localization_accuracy@node ≥ 85%`. A emenda acrescenta a medida que faltava; não
reabre a decisão.

## Emenda 2026-09-01 — o universo da cobertura é um roster de origens, não o payload de uma fonte (A27.l3)

> ⚠️ **As duas justificativas de rejeição do schema, abaixo, são falsas como escritas** —
> retificadas na emenda de 2026-09-02, que também declara `29,4%` como **teto**. A
> decisão (roster, não schema) sobrevive; o motivo é outro.

> **Sinal:** a tabela da emenda de 2026-08-30 publica **5/14 = 35,7%**. O número é o da
> **fixture dogfood**, não o do E5. O denominador correto é **17** e a cobertura é
> **29,4%** — leia esta emenda antes de citar aquela tabela.

**O que a emenda anterior afirmava:** que o denominador vem do payload publicado. Verdadeiro
como *mecanismo* e errado como *sujeito* — o payload medido era o da fixture dogfood, que é
subconjunto **estrito** do que a produção emite. Medido em 2026-09-01 sobre o artefato
`analise_financeira` do run `40d1af2a`: a produção publica dinheiro em **17** raízes contra
**14** na fixture. As 3 a mais (`previdencia_pgbl`, `real_estate`, `tributario`) nunca
aparecem na fixture, que não tem IRPF, imóvel locado nem PJ. O viés era **otimista** e
crescia sozinho: raiz nova entrava na produção sem entrar no denominador.

| Medida (2026-09-01) | Valor |
| --- | --- |
| Raízes monetárias da fixture dogfood | 14 |
| Raízes monetárias do payload de produção (`40d1af2a`) | 17 |
| Raízes com nó em `_lineage.fields` (idêntico nas duas origens) | 5 |
| **Cobertura publicada** | **5/17 = 29,4%** (era 35,7%) |

**Emenda à decisão:**

- **O universo é o roster de origens observadas**, e o número publicado é sobre ele —
  `dev/snapshots/lineage_coverage_baseline.json` guarda cada raiz com as origens em que foi
  medida (`fixture`, `producao:<run8>`). Roster de origem única volta a ser "a cobertura do
  que aquela fonte emite" e é asseverado contra.
- **Raiz monetária medida fora do roster reprova.** No CI sobre a fixture
  (`test_nenhuma_raiz_monetaria_fora_do_roster`); sobre produção pelo CLI
  `dev/lineage_coverage.py <payload> --origem <x>`, que sai com código 1 e nomeia a raiz.
- **O schema E5 foi medido como fonte de universo e rejeitado.** Não é superconjunto da
  produção (não declara `tributario`, que o E5 emite por `additionalProperties: true`) e
  declara `proventos_por_ativo`, que nenhum dos 40 artefatos E5 do DB emite — teto
  inalcançável, o mesmo motivo pelo qual as 38 raízes cruas já haviam sido recusadas.
- **`pontos` e `contagem` saem do monetário-por-default.**
  `narrativas.charts.wise_fiscal_flags.pontos_revisao` é `sum(1 for f in flags if
  f["needs_review"])` e era a **única** folha monetária de `narrativas` — a raiz de prosa
  entrava inteira no denominador. Mesma classe de `n_*`/`prob_*`/`score.*` ([[ADR-217]]).

**Enforcers:** `dev/lineage_coverage.py` (`Roster` + CLI) · `tests/test_lineage_coverage.py`
(gate + `test_o_denominador_publicado_nao_e_o_da_fixture`, o contrafactual que reprova o
desenho anterior).

## Emenda 2026-09-02 — a rejeição do schema estava certa pelo motivo errado, e `29,4%` é teto (closeout da A27.l3)

> **Sinal:** a emenda de 2026-09-01 rejeita o schema E5 como fonte de universo por duas
> pernas. **As duas caíram.** A conclusão não — mas quem citar aquele parágrafo como
> evidência estará citando medição errada.

**Perna (a) — "o schema não é superconjunto da produção; não declara `tributario`".** Falsa
duas vezes. O [#1967](https://github.com/davidrobert/mathoms/pull/1967) declarou a raiz. E o
resíduo (`consumo_consciente`, `goals`, `reserva_emergencia`) era **artefato do walker que
produziu a medição**: ele não resolve `$ref`, e as três são `{"$ref": "#/$defs/..."}` com
`number` declarado lá dentro. Com `$ref` resolvido, o schema-monetário é **18** e **é**
superconjunto das 17 da produção.

**Perna (b) — "declara `proventos_por_ativo`, que nenhum run emite ⇒ teto inalcançável".**
A raiz tem produtor (`e5_analyzer_adapter.py:862` → `fiscal_source.proventos_summaries`),
consumidor (`S3InvestimentosSection.tsx`) e teste e2e vivos. O que há é **zero** informe
`proventos_acoes` em 312 informes **deste** workspace. Tratar "não emitido aqui" como "não
pode ser emitido" é a conflação que a própria A27.l3 atacou, deslocada de *fixture vs.
produção* para *este workspace vs. os workspaces*.

**O motivo que sobrevive, e é outro:** o schema **não alcança `irpf_kpis`** —
`properties.irpf_kpis` declara 5 campos (metadados) sem `additionalProperties: false`, e o E5
emite 20, com todo o dinheiro entre os 15 não declarados. Piso declarado e chão medido têm
buracos **diferentes**: o schema não vê `irpf_kpis`, o roster não vê workspace não medido. O
universo defensável é a **união**, com cada raiz carregando de onde veio — não um dos dois
disfarçado de universo.

**`29,4%` passa a ser teto, não medida.** `_is_monetary_leaf` exige `int|float` e o E5
serializa parte do dinheiro como string decimal (284 folhas no payload medido; `irpf_kpis` e
`protecao_patrimonial` existem no denominador **só** por elas). Piso medido: **5/19 = 26,3%**.
E `Roster.observing` não é monotônico — re-observar o mesmo rótulo com payload mais pobre
encolhe o universo e **sobe** o número, com a suíte verde nos dois sentidos. Ambos em
[[A27.l3]] §Deferimento datado 2026-09-02, dono `data-engineer`.

**Correção de fato menor:** "38 raízes declaradas no schema" (emendas de 2026-08-30 e
2026-09-01) são **39** desde o #1967.
