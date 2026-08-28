---
id: A40.l93
type: lane
title: "Alvo publicado cujo observado o parecer nunca lê, e o comparador que isso mascarava"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
ship_pr: 1796
ship_date: "2026-08-28"
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
  - status/shipped
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

## Entregue — quatro ondas

| onda | o que entrou |
|---|---|
| **1** | `dev/check_prompt_version_bumped.py` passa a cobrir `config/prompts/*.yaml` por **lista declarada** (N2), com igualdade de conjunto sobre o diretório · `_read_upstream` deixa de **falhar aberto** com ref irresolvível · `section_summaries`/`lineage_debug` migram para semver puro · emenda datada à [[ADR-233]] |
| **2** | folha `derived.renda_fixa_atual_pct` em ponto fixo (R2) · `alocacao_renda_fixa` vira **órfã por decisão de domínio** (N1) · `unidade`/`operador` viram enum no schema E5 · `kpi_targets[].limiar` sai do classificador monetário do `golden_diff` |
| **3** | `diagnostico_confianca` no enum de `get_e5_section` + manifest `2.5.0 → 2.6.0` + backfill do changelog de 2.4.0/2.5.0 (R1) |
| **4** | `dev/check_kpi_path_legivel_pelo_parecer.py` (pre-commit) · `_RESOLUCAO_DIVIDA_DECLARADA` **deletada** |

## As seis medições que mudaram o desenho

1. **A rota do N1 no prompt desta lane era `|atual − alvo|` contra 2pp; o
   `financial-planner` a recusou.** `SEVERITY_ALINHADO_MAX_PP` é piso de
   **acionabilidade** — a [[ADR-400]] o reusa literalmente assim — e a [[ADR-141]]
   §Emenda item 10 diz textualmente que "calibração relativa é roadmap pós-dogfood".
   Publicá-lo como `limiar_canonico` promoveria limiar interno a doutrina sem a doutrina
   existir: o modo de falha da [[ADR-399]] com o ator trocado. Adotado **órfão por (b)**,
   que é a forma que `if_progresso`/`if_prazo_ano` já têm.
2. **O painel previu delta de golden `↓`; medido, é `=`.** O dogfood **não tem**
   `goals.alocacao_alvo`, então `derived` nunca é montado, a folha nova não aparece no
   snapshot e a entrada já era órfã. O ramo que esta lane conserta é **inerte no
   workspace medido** — mesmo padrão da [[A40.l91]].
3. **O painel afirmou que `_par` sobrescreve o motivo de domínio por `_SEM_OBSERVADO`.
   Refutado:** [`parecer_finalization.py:296`](../../../../backend/app/services/parecer_finalization.py)
   é `alvo.get("motivo") or _SEM_OBSERVADO` — o motivo do catálogo tem precedência. O que
   se perdia sem o fix do path era o `valor_atual`, não o motivo.
4. **O parecer é chamada SINGLE-SHOT.** `LLMService.call` não tem parâmetro `tools` e
   `_invoke_parecer_llm` não passa nenhum. O bloco `tools:` do manifest é whitelist de
   **resolver server-side**, não capacidade do modelo — o que torna a Onda 3 mais barata
   do que o registro sugeria, e torna falsa a frase "amplia a superfície de leitura do
   modelo".
5. **A fixture do golden exibe os dois estados que fabricariam conformidade:**
   `carteira_liquida_brl: 0.0` (denominador zero) e
   `motivo_supressao: cobertura_incompleta` (supressão declarada da
   [[ADR-394]]/[[ADR-400]]). Sob o `operador="<="` que existia, os dois publicariam
   "conforme". Ambos deixam de ser representáveis com a entrada órfã.
6. **`rf_*` era colisão medida, não estética.** `rf_pos_pct + rf_pre_pct + rf_ipca_pct`
   = **40** em `goals.alocacao_alvo`, um nível acima, contra **44,44** renormalizado em
   `derived` — dois quase-homônimos com valores diferentes é o C14 que a [[A40.l80]]
   pagou. Daí `renda_fixa_atual_pct`.

## Prova de vermelho (a disciplina herdada, exercida)

| gate | caso que reprova | onde está |
|---|---|---|
| ref irresolvível no gate de versão | a MESMA árvore que passa sob `main` reprova sob ref inexistente | `tests/dev/test_check_prompt_version_bumped.py` |
| YAML sem bump / sem `version:` / não declarado | 5 casos, mini-repo git hermético (sem rede, imune a clone raso) | idem |
| `observado_path` ilegível | catálogo de `HEAD` antes do fix, nomeando as 2 chaves com `reason` diferente | transcript no corpo do PR |
| predicado do gate | o path com `[classe=renda_fixa]` que existia | `tests/unit/pipeline/test_kpi_target_catalog.py` |
| isenção de `limiar` no `golden_diff` | comentar a entrada ⇒ vermelho | `tests/test_parecer_metrica_stamping.py` |
| emenda da ADR-233/399 | tirar a data de `amended_at` ⇒ o gate acusa | mutação manual, re-medida |

**Um erro do autor, pego pela própria prova:** a checagem de presença de `version:` nasceu
dentro de `_errors_for`, **atrás** do check de ref — e o comentário ao lado dela afirmava
que ela "sobrevive a clone raso". O transcript mostrou o curto-circuito. Movida para
junto da igualdade de conjunto, que lê só o disco local.

## Follow-ups com dono (nenhum fica sem endereço)

| item | por quê | dono |
|---|---|---|
| **Denominador zero em `comparaveis[].atual_pct`** | carteira líquida ≤ 0 publica `0,0%` no card S3 — ausência disfarçada de medida. A folha nova é cópia fiel disso **de propósito**: consertar só a cópia daria duas respostas para o mesmo fato | `product-designer` + `data-engineer` |
| **`check_lane_counter` não vê a própria tabela** | compara o número declarado contra o **disco**; subdeclarar a metade "nesta tabela" passa calado, e passou (`91 · 90` com 91 no disco e 91 na tabela) | quem mexer na skill `lane-closeout` |
| **`check_golden_rebaseline_isolation` não cobre `backend/tests/snapshots/`** | `_GOLDEN_PREFIX` fixa `tests/fixtures/pipeline_golden/`. **A justificativa que esta linha trazia estava errada em dois eixos, e o closeout a re-mediu:** o número (*"74 de 76 commits desde 2026-05-01"*) foi **relatado, não medido** — em `main` são **76 de 78**; e o denominador é o errado, porque commit de `main` é **squash-merge** e por construção empacota o PR inteiro, o que torna "mistura código" tautológico ali. O gate roda `--commit-range base..HEAD` na **branch do PR** (`ci.yml:676`), onde os commits **não** estão esmagados — foi assim que os dois rebaselines desta lane ficaram isolados. **Quanto custaria estender segue não medido**, e medir exige varrer branches de PR, não `main` | [[A40.l80]] (ressalva herdada) |
| **Atribuição de `prompt_version` no e16** | editar as tabelas RFB muda o prompt sem bumpar `e16_irpf_full.PROMPT_VERSION`. Cache protegido pelo hash da [[ADR-307]]; o defeito é de **atribuição** em `LLMCallLog` | `prompt-engineer` |
| **Tool loop anunciado e não ligado** | o prompt do parecer diz "Cap: 6 iterações" e o orquestrador não passa `tools`. Classe declarado-mas-inerte | `prompt-engineer` |
| **`build_section_summary_cache_key` órfã** | sem chamador, e é a variante **sem** version — duas chaves canônicas para a mesma coisa, uma errada | qualquer um, 1 linha |
| **Divergência `percent2` vs `pct` na mesma folha** | o manifest declara `percent2` para `share_nao_identificado_pct` e `ancora_format_hint()` deriva `pct` pelo nome: `30,70%` vs `30,7%` | `prompt-engineer` |

## Fora de escopo — com rota herdada do §Fecho da l89

| item | rota | dono |
|---|---|---|
| **R3** `metrica_key` duplicada | bug fix ≤30 linhas, PR próprio. Dedupe **subtrativo no finalize, keep-first**, com contador em log estruturado. **Não** `uniqueItems` (as linhas diferem em `frequencia_revisao`/`section_id`), **não** validator hard-fail (reabre a reask storm — [[ADR-292]]/[[ADR-294]]) | `prompt-engineer` decide |
| **R4** polaridade da trilha | já é a [[A40.l92]], aberta | `product-designer` |
| **R5** `clt_estavel` inalcançável + **N3** `clt_unica_fonte` rotulado por ausência de medição | decisão de domínio antes de tocar `scoring.json` — remover config viva sem veredito converte defeito de alcance em decisão de produto tomada por engenharia | `financial-planner` |
| **Checagem doutrina × alvo de alocação declarado** | hoje não existe, e com a D2 valendo para alocação o produto não questiona o plano da família. A camada de sobrevivência é protegida **fora** desta métrica (reserva, canônica; caixa fora do denominador do desvio). Conteúdo do wizard de metas, não deste catálogo | `financial-planner` |
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
