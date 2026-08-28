---
id: A40.l93
type: lane
title: "Alvo publicado cujo observado o parecer nunca lê, e o comparador que isso mascarava"
sprint: A40
plan: PLAN-deterministic-authority
status: in_progress
priority: P0
branch_slug: a40-l93-fecho-residuais
owner: data-engineer
depends_on:
  - "[[A40.l89]]"
adrs:
  - "[[ADR-399]]"
  - "[[ADR-233]]"
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/pipeline
  - area/llm
---

# A40.l93 — `fecho-tecnico-dos-residuais`

> **Origem:** §Fecho da [[A40.l89]] (painel de 2026-08-28 · `financial-planner` ·
> `senior-cto` · `data-engineer`). A l89 fechou **com ressalva** porque R1 e R2 não são
> estado de repouso: são KPI publicado cujo observado o parecer **nunca** consegue ler.
> Esta lane executa a rota que aquele painel decidiu. **Não reabre decisão** — executa.

## O fato, medido (2026-08-28, fixture do golden E5)

Duas das 13 chaves de `kpi_targets` publicam alvo cujo `observado_path` é irresolvível
pelo resolver de **produção** (`PlannerDrillDown` com `load_manifest().tools_section_whitelist`):

| chave | `observado_path` | `reason` |
|---|---|---|
| `alocacao_renda_fixa` | `$.goals.alocacao_alvo.derived.comparaveis[classe=renda_fixa].atual_pct` | `path_not_whitelisted` |
| `despesas_nao_categorizadas` | `$.diagnostico_confianca.share_nao_identificado_pct` | `path_not_whitelisted` |

São causas **diferentes** sob o mesmo `reason`: a primeira usa predicado de filtro que o
`_JSONPATH_RE` recusa por desenho; a segunda tem sintaxe válida e raiz fora do enum de
`get_e5_section` — que é a mesma frozenset que serve de `section_whitelist` ao resolver.

**E o que a irresolubilidade mascara.** `_alocacao_renda_fixa` publica `operador="<="`
sobre o par (`atual_pct`, `alvo_pct`) — afirma que **menos** renda fixa que o alvo está
conforme. Na fixture: `atual_pct = 0.0` contra `limiar = 44.44` ⇒ `0.0 <= 44.44` ⇒
**conforme**, com o selo de autoridade do produto, sobre uma carteira que não tem renda
fixa nenhuma. Consertar o path sem consertar o operador **ativa** esse comparador.

## Escopo — quatro ondas, sequenciadas por colisão de arquivo

Ver §Ondas abaixo. A separação não é editorial: a Onda 2 inteira mora nos mesmos dois
arquivos (`kpi_target_catalog.py` + `e5_analysis.schema.json`) e quebrá-la produziria três
rebaselines de snapshot em vez de um.

## Fora de escopo — com rota herdada do §Fecho da l89

| item | rota | dono |
|---|---|---|
| **R3** `metrica_key` duplicada | bug fix ≤30 linhas, PR próprio. Dedupe **subtrativo no finalize, keep-first**, com contador em log estruturado. **Não** `uniqueItems` (as linhas diferem em `frequencia_revisao`/`section_id`), **não** validator hard-fail (reabre a reask storm — [[ADR-292]]/[[ADR-294]]) | `prompt-engineer` decide |
| **R4** polaridade da trilha | já é a [[A40.l92]], aberta | `product-designer` |
| **R5** `clt_estavel` inalcançável + **N3** `clt_unica_fonte` rotulado por ausência de medição | decisão de domínio antes de tocar `scoring.json` — remover config viva sem veredito converte defeito de alcance em decisão de produto tomada por engenharia | `financial-planner` |
| **R6** `Goal(RESERVA_EMERGENCIA)` sem leitor em `pipeline/` | lane própria, **e exige emenda datada à [[ADR-399]] D2 ANTES**: "declarado vence doutrina" está certa para alocação e **errada para reserva**. Regra correta: `limiar = max(declarado, canonico)` | `data-engineer` + `financial-planner` |

## Disciplina herdada (não é opcional)

A l89 mergeou com 4 suítes verdes e 7 defeitos, dois P0. Os três gates que o autor escreveu
para pegar essa classe compartilhavam premissa com o código que checavam.

- **Gate novo entra com prova de vermelho** ([[ADR-210]] §emenda decidida no §Fecho da
  l89): o corpo do PR cola o caso que o gate deve reprovar, **reprovando**.
- **Fixture sai do produtor** — nunca escrita à mão nem via `git show <sha>` (o CI clona
  raso; morre lá e passa aqui).
- **Parametrize pelos tipos que o payload de fato entrega** — `protecao_custo_premio` chega
  como string `"0.005686"`; `aliquota_efetiva_ir` como `"16.37"` ou `"N/D"`.
- **Número citado se re-mede, não se relê.**
