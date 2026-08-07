---
id: A40.l28
type: lane
title: "Idade-meta do cone é output do modelo, não pergunta da família — e o rótulo do percentil aponta para dois lados"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l28-idade-meta-e-rotulo-do-cone
adrs:
  - "[[ADR-361]]"
  - "[[ADR-237]]"
  - "[[ADR-219]]"
depends_on: []
parallel_with:
  - "[[A40.l25]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l28 — `idade-meta-e-rotulo-do-cone`

> **Residual de contrato da [[ADR-361]] (#1162), itens 1 e 2 do §Deferimento.**
> A [[A40.l25]] pegou o item 5 (faixa de 5 pp) e o residual da [[ADR-360]]; estes
> dois ficaram sem destino. São contrato/payload — não dependem de brief de
> design, ao contrário da [[A40.l29]].
>
>
> Entra na A40 pela **KR-E** (honestidade da recomendação): as duas faces são
> números que dizem medir uma coisa e medem outra.

## Problema

### 1. `prob_if_ate_idade_meta` mede o modelo contra si mesmo

`e5_analyzer_adapter.py` chama `run_monte_carlo_if(..., idade_meta_if=
if_projection.idade_titular_if)` — a idade-meta é a **saída do projetor
determinístico**, não um alvo que a família declarou. Como
`horizonte_meta = idade_meta_if − idade_titular_atual` é exatamente o prazo
determinístico, a métrica publicada é:

> P(o Monte Carlo bate a data que o card determinístico logo acima imprimiu).

E como `mu_log = log(1+r) − ½σ²`, a mediana simulada fica **estruturalmente**
atrás do determinístico. Medição feita no co-design da [[ADR-361]], oito planos
deliberadamente distintos (PV de R$ 300 k a R$ 5 M, meta de R$ 2 M a R$ 20 M,
aporte de R$ 2 k a R$ 30 k):

| PV | meta | aporte/mês | prazo det. | `prob` publicada |
|---|---|---|---|---|
| 500 k | 3 M | 5 k | 18,3a | 41,2% |
| 500 k | 3 M | 15 k | 9,6a | 31,1% |
| 1,5 M | 5 M | 8 k | 14,3a | 42,5% |
| 2 M | 4 M | 3 k | 11,2a | 45,9% |
| 300 k | 10 M | 20 k | 21,6a | 37,8% |
| 5 M | 8 M | 10 k | 6,9a | 38,5% |
| 800 k | 2 M | 2 k | 13,5a | 42,8% |
| 4 M | 20 M | 30 k | 18,0a | 44,1% |

**Amplitude de 14,8 pp entre planos radicalmente diferentes.** É praticamente
constante de modelo, não métrica do cliente — e é publicada como
"~44% de chance de {titular} alcançá-la até os {idade} anos".

A [[ADR-361]] §Deferimento item 1 registrou isto como **maior que o defeito que
ela corrigiu**. Não existe campo de idade-meta em
`goals.independencia_financeira` (só `if_meta`, `trs_pct`,
`taxa_retirada_segura_pct`, `retorno_real_anual_pct`) — é campo novo.

### 2. `p10` significa o oposto de `p10` no mesmo payload

- `p10_ano_if` = percentil 10 do **tempo** = o décimo mais rápido = **favorável**
- `caminho_p10` = percentil 10 do **patrimônio** = o décimo mais pobre = **adverso**

Mesmo sufixo, orientação oposta, mesmo bloco. A legenda do gráfico já diz
"P10 — cenário adverso" enquanto o campo de ano ao lado quer dizer o contrário.
A [[ADR-361]] deixou o rename fora de propósito, para não misturar mudança de
contrato com correção estatística — mas o v3.0 circulando com o rótulo ambíguo
fica mais caro de desfazer a cada consumidor novo.

## Escopo

1. **`idade_meta_if` vira input** em `goals.independencia_financeira` (default
   65, editável), com migração de leitura no adapter. Enquanto não houver valor
   declarado, a **única probabilidade honesta é `prob_if_ate_horizonte`** (já
   publicada pela [[ADR-361]]) — `prob_if_ate_idade_meta` não sai.
2. **Rename** `p10_ano_if`/`p90_ano_if` → `ano_if_cenario_favoravel` /
   `ano_if_cenario_adverso` (e as flags de censura junto), com `mc_version`
   bumpado. Toca payload, `config/schemas/e5_analysis.schema.json`, tipos TS,
   catálogo de citação do parecer e snapshot do dogfood.

## Co-design obrigatório antes de codar — **FEITO 2026-08-07**

> ✅ **`financial-planner` + `data-engineer` executados. O co-design REFUTOU a premissa
> do item 1 e o §Critério de aceite; as duas decisões abaixo são do dono (2026-08-07).**
> Implementação **não** começou — esta seção é o insumo para quem pegar a lane.

### O item 1 partia de premissa falsa: o alvo declarado JÁ EXISTE

A lane afirma *"não existe campo de idade-meta … é campo novo"*. Verdade sobre o
**nome**, falso sobre a **substância** — medido contra `origin/main`:

- `horizonte_anos` é **`required`** em `config/schemas/goal.if.schema.json` — e é o **v1
  que está em produção**. (`goal.if.v2.schema.json` diz de si: *"Schema CANDIDATO v2
  (ADR-140 — roadmap, não em produção)"*. **Não editar o v2** — insinua adoção e reabre
  a ADR-140.)
- O wizard **já pergunta**: `plano/meta-if/wizard/page.tsx:375`, manchete do Step 3 é
  literalmente *"Em quantos anos você quer chegar lá?"*, com `canAdvance` exigindo o campo.
- O campo é **truncado no boundary**: `_serialize_if_goal`
  (`backend/app/services/pipeline/pipeline_adapter.py:201-214`) copia 5 campos de `inputs`
  e **não** copia `horizonte_anos`; `IFGoalSection` (`pipeline/domain/goals_bundle.py:19-30`)
  não o tem. Não é campo inexistente — é campo **descartado**.
- `IFProjector._solve_prazo` **não usa** `horizonte_anos` (resolve `n` do aporte real). O
  produto já tem os dois lados da tesoura — **prazo declarado** (compromisso) e **prazo
  realista** (capacidade) — e nunca os comparou.

**Decisão do dono: derivar de `horizonte_anos`. Sem campo novo, sem default 65.**
`horizonte_anos` é a primária. Dois campos criariam dois alvos temporais que precisam
concordar — quando divergirem, o relatório escolhe um e o card exibe o outro, que é a
classe de defeito que esta lane existe para matar.

**Ancorar em ano absoluto, não na data do relatório:** `horizonte_anos` é relativo ao
momento em que foi respondido. Declarar "15 anos" em 2026 e reler em 2030 significaria
2045 quando a família quis dizer 2041. Use `Goal.effective_from` (existe,
`backend/app/models/goal.py:60`, sem migration):
`ano_meta_declarado = effective_from.year + horizonte_anos`.

**65 é âncora do INSS** (elegibilidade a benefício público, reforma 2019) — ortogonal a
*"meu patrimônio sustenta meu custo"*. Cravá-lo importa a premissa previdenciária para
dentro da métrica que existe justamente para não depender dela. E empiricamente erra: para
o ICP (titular 40-50) colaria a `prob` no teto (~85-95%), trocando uma constante de modelo
em 40% por outra em 90%. **"Idade-meta de IF" não é conceito de nenhuma das três metodologias de
referência** (§13 — ver `config/agents/`), nem de `config/methodology.md`.

**Casal: a pergunta desaparece.** O alvo é da **família**, em anos; as idades são exibição
derivada, uma por membro (`IFProjection` já tem `idade_titular_if`/`idade_conjuge_if`).
"A família só é independente quando ambos podem parar" já está dentro da **meta** (`if_meta`
deriva da renda passiva que cobre o custo familiar) — pôr também na data conta duas vezes.
Aposentadoria escalonada é cenário de estresse, e o instrumento existe (`CenariosConjugeAnalyzer`,
ADR-167).

**Dois gates de honestidade:** `is_template = true` ⇒ `prob` **não sai** (`motivo`: prazo
ainda não declarado — Goal semeado no onboarding não declarou nada); e a copy **nomeia o
dono da data** (*"o prazo que você declarou em ‹mês/ano›"*), porque hoje
`projecao_if_narrator.py:36` diz "de chance de {titular} alcançá-la até os {idade} anos",
sujeito ambíguo que o usuário lê como nosso.

### O §Critério de aceite era insatisfazível — substituído

**A amplitude vem da FOLGA, não da fonte.** `folga = prazo_declarado − prazo_determinístico`.
Os 8 planos da tabela do §Problema têm **todos folga zero** — é por isso que a grade é plana,
e continuaria plana **com qualquer fonte de idade-meta**. Com `folga = +7` a `prob` vai a
~85-90%; com `−5`, a ~5%.

**Decisão do dono — substitui *"≥6 planos, amplitude > 30 pp"*:** grade que varia
**folga** ∈ {−5, −2, 0, +3, +7, +12} com PV/meta/aporte fixos em ≥2 perfis. Invariante duro:
`prob` **monótona não-decrescente em folga**; amplitude **> 40 pp** de −5 a +12. E **pinar
`folga = 0 ⇒ prob ∈ [0,30; 0,50]`**, documentando o atraso estrutural do log-normal
(`mu_log = log(1+r) − ½σ²`) como propriedade conhecida em vez de acidente.

### Três estados novos que o payload tem de declarar

1. **`is_template`** ⇒ ausência + `motivo`.
2. **Prazo declarado vencido** (Goal versionado permite "3 anos" em 2022 ⇒ alvo 2025 ⇒
   `prazo_declarado_anos <= 0`): `prob = 0` é aritmeticamente correto e **inútil** — emitir
   ausência + `motivo`, pelo raciocínio do D8 da [[ADR-361]].
3. **Declarado > janela simulada**: `horizonte_anos` aceita até 50, a simulação tem janela
   40 — hoje devolveria silenciosamente `prob == prob_if_ate_horizonte`. **Clampar com
   flag** (`prazo_declarado_truncado`), não estender a janela: estender muda a base da
   censura da ADR-361 e o tamanho de `caminho_*`.

### Colisão de nome — mesma classe do defeito p10/p90 desta lane

`horizonte` passaria a ter **três** significados: janela de simulação (40a,
`MonteCarloIFResult.horizonte_anos`), `prob_if_ate_horizonte` (sucesso nessa janela,
ADR-361) e o prazo declarado. Renomear no mesmo lote/`mc_version`:
`horizonte_simulado_anos` / `prob_if_ate_horizonte_simulado` vs `prazo_declarado_anos` /
`prob_if_ate_prazo_declarado`. **`prob_if_ate_idade_meta` tem de ser RENOMEADA, não
reaproveitada** — a chave sobreviveria com semântica invertida (de modelo-contra-si para
compromisso-contra-capacidade), e leitor que compara payloads por chave não vê o `mc_version`.

### Item 2 (rename do cone) — contrato decidido pelo `data-engineer`

- **`mc_version` → "4.0"**, com ADR sucessora `Proposto` antes do PR (o comentário em
  `if_monte_carlo.py:91` exige sucessora). Custo incremental **zero**: `rg mc_version
  backend/app` = 0 hits, não entra em chave de cache nem dispara recompute, e
  `DEFAULT_SECTION_VALUE_PATHS` do changelog **não** mapeia o cone. **Declarar no schema e
  na ADR: "4.0 = 3.0 com chaves renomeadas; valores idênticos e comparáveis a 3.0"** — sem
  isso o próximo arqueólogo assume que o número mudou (a descrição atual do schema diz que
  `p50_ano_if` não é comparável entre 2.0 e 3.0).
- **Renomear os TRÊS anos**, não só p10/p90: deixar `p50_ano_if` no meio de
  `ano_if_cenario_favoravel`/`_adverso` recria a confusão dentro da família
  (`ano_if_cenario_central`). E **não renomear `caminho_p10/p50/p90`** — ali `p10` =
  patrimônio mais baixo = adverso, exatamente o que a legenda já diz.
- **Compat de leitura (b), chaveado por `mc_version`, em UM site.** O único read site de
  produção é `scripts/generate_narratives.py:728-730`; o S7 lê `caminho_*` e `goals.ano_if`,
  **não** `p*_ano_if`. Compat é obrigatório porque
  `narrativas/projecao_if_narrator.py:63` faz **acesso duro** `M['mc_p50_ano_if']` —
  artefato stale + re-run parcial de `generate_narratives` dá **KeyError e derruba o
  stage**, não campo vazio. Backfill está **descartado**: `pipeline_artifacts` é o registro
  do que de fato rodou (substrato de ADR-362/lineage), e reescrevê-lo falsifica relatório já
  entregue. No schema, renomear `properties` **e `required`** no mesmo commit — o bloco não
  tem `additionalProperties: false` e a validação é write-only (hook pós-write, ADR-212).
- **Gatilho de remoção do compat MENSURÁVEL, não calendário:** zero artefatos
  `analyze_finances` alcançáveis (latest-per-workspace + fallbacks ADR-241/ADR-291) com
  `mc_version < "4.0"`. Janela datada sem contador é dívida eterna.

### 🚨 `max_chars: 380` do manifest ESTOURA com o rename

`config/prompts/parecer_planejador.yaml:344` tem `max_chars: 380` para `$.if_monte_carlo`,
calibrado pela ADR-361 (*"medido: 320 com cone, 369 com o cone suprimido"*). O rename infla
**+97 chars** (`p10_ano_if`→24 = +14; `p90`→+12; `p50`→+12; `p10_censurado`→
`ano_if_cenario_favoravel_censurado` = +21; `p90` = +19; `p50` = +19) ⇒ **~466 > 380**. O
distiller corta prefixalmente e `backend/tests/test_parecer_exec_context_mc_budget.py` falha
com *"caiu fora do corte de max_chars — o LLM lê o cone sem ele"*. **Remedir** (não estimar)
nos dois piores casos e bumpar — o que bumpa `version` do manifest (hoje `2.0.2`), que
**entra** na chave de cache via `manifest_version`. Nome mais longo é custo **permanente**
de contexto do parecer, num bloco com `eviction_priority: 8`.

### Gates que a lane dispara sem mencionar

- `dev/check_planner_manifest_coverage.py` — cruza `dev/snapshots/e5_schema_hash.txt`;
  **qualquer** edit no `e5_analysis.schema.json` dá drift. Rodar `--update-snapshot`.
- `backend/tests/test_parecer_exec_context_mc_budget.py` (o do `max_chars`).
- `backend/tests/test_report_view_model_snapshot.py` (`MATHOMS_UPDATE_SNAPSHOT=1`) +
  invariante `monetary_fields ⊆ snapshot`.
- `make update-openapi-snapshot` — **só** se o DTO `IFGoalInputs` mudar.
- `frontend/tests/e2e/fixtures/reports/degraded.json` — fixture `@critical`; stale = verde falso.
- Cluster de narrativas: `test_e5n_projecao_if_censura`, `test_e5n_narrativas_coerentes`,
  `test_e5n_anti_hardcode`, `test_e5n_delivery_contract`.
- **Restrição de naming por `dev/golden_diff.py`:** `p10_ano_if` passava por
  `_NON_MONETARY_SUFFIXES`; `ano_if_cenario_favoravel` passa por `_NON_MONETARY_PREFIXES`
  (`ano_`) — **por sorte**. Nome que não comece com `ano_` nem termine em `_ano_if` cai em
  monetário-por-default e o diff reporta `delta_cents` fantasma.
- **Custo de frota:** 1 re-geração completa de parecer por workspace no próximo run (o
  rename move o hash do E5, e o cache do parecer é `sha256(json.dumps(e5_data))`). Confirmar
  folga no hard-stop de budget da [[ADR-173]] antes de mergear. Este custo é o argumento
  para **um** PR de contrato em vez de dois: cada PR que mova o hash cobra a frota de novo.

### Ressalvas de escopo (do `financial-planner`, não bloqueiam)

- **Não shipar o escalar como manchete sozinho.** O par legível é ano-a-ano na unidade que o
  usuário escolheu: *"você declarou 15 anos; no ritmo atual o plano fecha em 22"*. A
  probabilidade **qualifica**, não é a notícia. Manchete é [[A40.l29]] + `product-designer`.
- **`prob ≈ 95%` não é boa notícia neutra** — pode significar meta subdimensionada ou que a
  família pode parar antes. Copy que só celebra perde a segunda leitura.
- **σ fixo (11%) limita o peso da copy** (lente de alocação, [[A40.l25]]): enquanto σ não vier da alocação
  declarada, a `prob` é condicional a uma carteira que o produto assume, não que a família
  tem. Evitar verbo de certeza.
- Slider **não** é outra métrica — é a mesma CDF re-parametrizada, dados já em
  `primeiro_true`. Métrica genuinamente melhor seria a **inversa** ("aporte para 80% de
  confiança na sua data"), que é premium e merece lane própria.

## Critério de aceite

- Nenhuma superfície publica probabilidade medida contra alvo derivado do próprio modelo.
  **Travar por AST no call-site do stage**, não por asserção sobre o valor — um refactor
  que reintroduza a derivação tem de falhar.
- ~~Grade de ≥6 planos, amplitude > 30 pp~~ — **insatisfazível, substituída** (ver
  §Co-design): grade que varia **folga** ∈ {−5,−2,0,+3,+7,+12}, `prob` monótona
  não-decrescente em folga, amplitude **> 40 pp**, e `folga = 0 ⇒ prob ∈ [0,30; 0,50]`.
- Proveniência publicada: payload carrega `prazo_declarado_anos` + `declarado_em`; `prob` é
  `null` com `motivo` nos três casos (`is_template`, prazo vencido, prazo > janela — este
  com flag de truncamento).
- Ambiguidade zero: nenhuma chave `horizonte`/`prazo` sem qualificador
  `simulado`/`declarado`; grep de `prob_if_ate_idade_meta` = 0 fora de compat de leitura.
- Nenhum campo do payload usa `p10`/`p90` como rótulo user-visible ou de
  contrato; grep de `p10_ano_if` retorna 0 fora de compat de leitura.
- `mc_version` bumpado e a mudança entra na nota de recalibração pendente no
  dono (§Entregas fora de lane).
- Verificação renderizada da S7 (§Débito de método desta sprint) — a lane não
  fecha sobre inferência de código.

## Fora de escopo

- Faixa de 5 pp na probabilidade e `sigma` por perfil — [[A40.l25]].
- Ramos faltantes do `_solve_prazo` — [[A40.l26]].
- Aposentar o ano do MC como manchete, inverter o eixo para "quanto", componente
  de faixa na UI — [[A40.l29]] (dependem de brief de `product-designer`).
