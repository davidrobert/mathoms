---
id: A40.l89
type: lane
title: "Wiring do catálogo de alvo: o produtor suprime o limiar por falta de procedência e o parecer o republica"
sprint: A40
plan: PLAN-deterministic-authority
status: in_progress
priority: P0
branch_slug: a40-l89-wiring-do-catalogo-de-alvo
owner: prompt-engineer
depends_on:
  - "[[A40.l91]]"
adrs:
  - "[[ADR-399]]"
  - "[[ADR-416]]"
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/pipeline
  - area/llm
---

# A40.l89 — `wiring-do-catalogo-de-alvo` (RR5-02)

> **Origem:** rodada unificada **U1** 2026-08-26 ([[ADR-416]]) ·
> [[REPORT-REVIEWS-active]] §r5 — **RR5-02** (Crítico, P0).
> Cru + síntese: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

> **Esta lane é a RETOMADA do §Deferimento D3, não um locus novo.** O braço do `target`
> de `PE-2` e de `FP-6` no [[PIPELINE-REVIEWS-active]] §r7 está deferido desde 2026-08-21
> com donos nomeados: o catálogo determinístico mergeou (#1557, [[ADR-399]]) e **não foi
> wired** — produção segue publicando alvo do LLM. Abrir lane com nome próprio forkaria
> uma decisão que já tem endereço. O escopo abaixo executa o que o deferimento escreveu.

> **Muta E5 + prompt ⇒ zera o contador de 2 re-runs** ([[A40.l2]], estendida à l34/l35).
> Serializada atrás da [[A40.l91]] numa janela única de rebaseline.

## O fato, medido (2026-08-26)

Quatro `kpi_targets` têm `procedencia: null` com motivo nomeado — a supressão é deliberada
e documentada:

| KPI | Motivo declarado da supressão |
|---|---|
| taxa de poupança recorrente | duas fontes divergentes para o mesmo limiar |
| progresso rumo à independência | acompanhado pelo cone, não por alvo pontual |
| cobertura de proteção | capital ideal exige inventário confirmado ([[ADR-387]]) |
| carteira TRS | sem alvo canônico ([[ADR-191]]) |

**Três das quatro vazaram.** A tabela "Métricas a observar" renderizada publica alvo para
duas delas, e o plano de ação renderiza uma decisão fixando **alvo pontual** para exatamente
a métrica que o produtor declara sem alvo canônico.

O produtor suprime porque a procedência falta; republicar pela prosa devolve à família a
autoridade que o registro recusou — em três eixos de decisão ao mesmo tempo.

## O que a medição já descartou

- ~~"isto é o mesmo defeito das notas metodológicas e cabe na mesma lane"~~ — **refutado**:
  não compartilha superfície, dono, blast radius nem gate com um `.map()` faltando num
  componente. É produtor + schema + `PROMPT_VERSION` + janela de rebaseline. Tese comum não
  é lane comum.
- ~~"o parecer alucina o alvo"~~ — não. Ele autora um alvo porque **nada** no exec context
  o proíbe: o catálogo existe e não é lido.

## Escopo (executa (a), (b) e (d) do §Deferimento D3 — o (c) já mergeou em #1591)

> **Reescrito em 2026-08-27**, com o item (d) transferido. O texto anterior prometia três
> superfícies e alcançava uma; critério inexequível não adia entrega, **esconde**.

1. **Fecha o canal de emissão.** `metrica_key` vira required com enum fechado; `nome`,
   `valor_atual` e `target` saem do tool schema (`SkipJsonSchema`) e passam a ser
   estampados pelo finalize a partir do `kpi_target_catalog`. Métrica fora do enum não é
   emitível — **não há chave de escape**, e é esse o cap estrutural da [[ADR-399]] D1.
2. **`target` sem procedência ⇒ o item perde o comparador**, e publica `motivo` no lugar
   — a linha sobrevive como observacional.
3. **Read-path subtrativo** nos pareceres persistidos: o `target` só é servido quando o
   artefato traz `metrica_key`. Sem backfill, sem recomputar catálogo, sem mutar artefato
   ([[ADR-204]] §D1). Cobre HTML e PDF pela mesma rota.
4. Bump **atômico** de `PROMPT_VERSION` **e** `_SCHEMA_VERSION` — os dois entram na chave
   de cache e **nenhum dos dois é gateado** para esta mudança.

## Fora de escopo

- Estender o leitor único à **superfície de risco** → [[A40.l90]]. A ordem é forçada: se as
  regras de risco lerem o catálogo antes do parecer, o ponto urgente passa a contradizer o
  alvo ainda autorado pelo LLM na tabela de métricas **do mesmo relatório**. Wiring primeiro.
- A base bruta/líquida da meta de independência → [[A40.l91]], que vai na frente.

### §Deferimento datado 2026-08-27 — o item (d) muda de endereço

**O alvo do plano de ação não vem do LLM.** "Reduzir taxa de retirada para 4,0% ao ano" tem
ocorrência **única** no repo: `pipeline/domain/services/suggestion_rules.py:103`, com a
constante `trs_target_pct = 4.0` em `suggestion_config.py:15`. É **regra determinística** — e
o catálogo declara `carteira_trs` órfã ("sem alvo canônico", [[ADR-191]] §D5). São duas fontes
determinísticas do próprio produto se contradizendo, o que é a tese da [[A40.l90]], não desta
lane. A justificativa de ordem acima diz *qual lane vai primeiro*, não *onde (d) mora*: a
redação original conflatou sequenciamento com propriedade.

Agrava: a linha é **fóssil**. A regra não dispara hoje (`if_pct` 35,76 < 50; `trs` 1,74 < 4,6
— par medido no **run da U1**, `storage/<uuid>/`, off-git; na fixture
`dogfood_view_model.json` a regra também não dispara, mas pela guarda **anterior**, com
`goals.taxa_retirada_efetiva_pct` ausente — re-medido no closeout de 2026-08-27, ver
[[A40.l90]] §Acolhimento);
o 4,0% persiste porque a `Decision` D01 foi aceita em 2026-05-06 e `_top5_decisions_stmt`
projeta sem revalidar. Corrigir o produtor **não apaga a linha já persistida**.

| item | casa | dono | condição de retomada |
|---|---|---|---|
| `trs_target_pct = 4.0` na rota do plano de ação | [[A40.l90]] §Escopo | `financial-planner` | emenda da [[ADR-399]] §D4 no PR1 da l90 |
| prosa `≥ 30%` / `< 20%` no exec context (`pontos_fortes_analyzer.py:121,158`) | [[A40.l90]], mesma emenda | `financial-planner` + `prompt-engineer` | idem |
| `Decision` aceita não revalida contra o run corrente | ciclo de vida de `Decision` | `financial-planner` | próxima lane que toque `Suggestion`/`Decision` |
| seleção do painel: piso determinístico das rompidas | `PLAN-deterministic-authority` §Onda 5 | `financial-planner` + `prompt-engineer` | stamping desta lane em `main` |

> ✅ **Acolhido do lado da l90 em 2026-08-27** — [[A40.l90]] §Escopo 5-6 + §Acolhimento. A
> ocupação que barrou a primeira tentativa (`agent/a40-l90-ataque-p2/…`) era **stale**: o
> único commit da branch é patch-idêntico ao `f91df375` já em `main` (#1767) e o worktree
> estava limpo. Duas correções que o lado que recebe mediu e este lado não: a emenda é da
> **[[ADR-191]] §D6** (a [[ADR-399]] §D4 *renuncia* a estes leitores — não há isenção a
> estreitar), e das duas prosas só a `:121` contradiz o catálogo — a `:158` lê a **mesma
> chave** que `_endividamento` lê, e fica.

**Residual declarado, para o próximo revisor não o achar sozinho:** entre o merge desta lane e
o da l90, o relatório terá linha **sem comparador** para taxa de poupança e, no mesmo
documento, prosa afirmando `≥ 30%`. É contradição menor que a de hoje (alvo fabricado **+**
prosa), mas é contradição.

## Forma canônica

Emenda datada à [[ADR-399]] **não** é necessária: o wiring é exatamente o que a D4 já decide.
Se o escopo exigir mudar o que a D4 isenta, a forma é emenda — e aí a lane é a [[A40.l90]].

## Critério de aceite

> **Reescrito em 2026-08-27** junto com a transferência do item (d) — o critério anterior
> prometia a **prosa** e o **plano de ação**, que esta lane não alcança: nenhum campo de prosa
> carrega `metrica_key`, e o produtor do plano de ação é determinístico.

- Nenhum `target` **nem** `valor_atual` publicado em `metricas[]` sem `metrica_key` no
  vocabulário fechado **e** `procedencia != null` no `kpi_targets` do E5 — no artefato novo,
  no artefato congelado e no PDF (mesma rota).
- O modelo **não pode emitir** `target`: prova por mutação sobre o **tool schema**, não por
  instrução de persona.
- Item órfão publica `motivo` na célula do comparador; **célula vazia reprova** (vazio o leitor
  lê como "não mediram", que é afirmação diferente de "não afirmamos um alvo").
- Todo `observado_path` do catálogo resolve para folha existente no payload do golden, pelo
  **resolver de produção**.
- Delta de golden declarado `↑`/`↓`/`=`; rebaseline silencioso reprova.
- **Cap:** se a condição de retomada do D3 (*"nenhum rebaseline de golden em voo"*) não
  estiver satisfeita quando a janela abrir, esta lane e a [[A40.l90]] caem **juntas** para a
  A43 — não se separam.
- Concluído = PR mergeado em `main` com CI verde.
