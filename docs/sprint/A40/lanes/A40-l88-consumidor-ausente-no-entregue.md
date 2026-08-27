---
id: A40.l88
type: lane
title: "Consumidor ausente no entregue: o produto emite a ressalva, a seção e o aviso — e nenhum dos três chega ao leitor"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1755
ship_date: "2026-08-27"
priority: P0
branch_slug: a40-l88-consumidor-ausente-no-entregue
owner: product-designer
depends_on: []
adrs:
  - "[[ADR-416]]"
  - "[[ADR-129]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/frontend
  - area/report
---

# A40.l88 — `consumidor-ausente-no-entregue` (RR5-01, RR5-03, RR5-04)

> **Origem:** rodada unificada **U1** 2026-08-26 ([[ADR-416]]) ·
> [[REPORT-REVIEWS-active]] §r5 — **RR5-01** (Crítico, P0), **RR5-03** (Crítico, P0),
> **RR5-04** (Alto, P0). Cru + síntese: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

> **Admissão na A40** (a sprint não admite lane nova desde 2026-08-03): os três são **P0
> que alcança o usuário** e nenhum tem dono de arquivo em lane viva. Linha retro-registrada
> em §Fora do sprint. Precedentes: [[A40.l46]], [[A40.l87]].

> **Não muta E5 nem E3.** É render puro — **não zera o contador de 2 re-runs** da
> [[A40.l2]]. Por isso é a onda 1: mergeia a qualquer momento da janela.

## ✅ Entregue em 2026-08-27 — os quatro itens, e a premissa que caiu no caminho

> **Todos os três achados fechados.** O gate do item 1 existe, mordeu, e mordeu
> **a própria lane**: reprovou a primeira tentativa de conserto do RR5-04.

| Item | O que entrou |
|---|---|
| **1 · gate** | `dev/check_emitter_without_reader.py` + 12 testes. Três direções, mesma polaridade: campo do parecer sem renderer, `<ReportSection>` sem dispatch, custom property de CSS sem `var()`. Registrado no pre-commit no commit que zerou as violações |
| **2 · RR5-01** | `ParecerNotasMetodologicas`, antes dos achados. Tier free vê o contador — `FREE_TIER_LIMITS.notas = 0`, e sem ele o silêncio seria o mesmo, só que por política |
| **3 · RR5-04** | Expand vira estado React sobre classe; print revela; legenda volta a "Mostrando N de M" **só enquanto a lista está partida na tela** |
| **4 · RR5-03** | `S_PROTECAO` no `MIGRATED_SECTIONS` + `case` + `enabled: true` + entrada de nav, com o `temCoberturaContratada` que faltava |

### A refutação do §"O que a medição já descartou" era falsa

O §escopo afirmava que o `return null` da `:18` respondia à objeção da [[A40.l7]].
**Não respondia.** `readProtecaoPatrimonial` é guarda de **shape**, e
`compute_protecao` devolve o bloco **completo** para workspace sem apólice —
medido em 2026-08-27: 11 chaves, `premio_total_anual_brl: "0.00"`, `saude`
acesa. Ligar sem predicado publicaria "Seguros — Cobertura Contratada" zerada,
com veredito "Atenção", para todo cliente sem apólice.

A [[A40.l7]] estava **certa no mérito**; errou só o campo que citou
(`protection_bundle`, que é da S9, não `protecao_patrimonial`). O flip foi
autorizado pelo dono em 2026-08-27 **com** o predicado de vazio.

O cenário (b) do spec da A19 (`s_protecao_section.test.tsx`) só cobria payload
de shape quebrado (`{}` e `undefined`) — o caso que a produção entrega não tinha
teste, e foi essa lacuna que sustentou a crença por dois meses.

### O gate reprovou a própria lane

A 1ª tentativa do RR5-04 trocou `<details>` por `<ul hidden>` e o spec de print
reprovou nos três engines. `[hidden]` é `display: none !important` **na folha da
UA**, e `!important` de UA vence `!important` de autor: nenhum `@media print`
o revela. Era a MESMA classe do defeito original (`--details-open` inerte), uma
camada abaixo. O colapso virou `hidden print:flex` — o idioma que o próprio hook
`hidden-md-on-paper` nomeia.

O gate também nasceu com dois falsos-verdes que a construção mediu:
`gated.notas_metodologicas` (um `GatedCounts`, não o array) e `pkg.version`
**dentro de um comentário**. Sem a exclusão de receptor e o strip de comentário
ele teria nascido verde sobre o defeito.

### Um fix quase reintroduziu a classe que a lane fecha

Ligar a seção quebrou a paridade tripla `VALID_SECTION_IDS` ↔ layout ↔ enum do
parecer. Fechar somando o id nos três ampliaria o vocabulário que a LLM pode
emitir para uma seção **sem renderer de callout** — emissor sem leitor de novo.
`SECOES_SEM_ANCORA` nomeia a diferença, com teste que exige as duas pontas
concordando (habilitada no layout **e** desconhecida do parecer).

### Critério de aceite — o que ficou meio atendido

O bullet *"a seção aparece no ToC e nas âncoras quando há dado, e some quando
não há"* está atendido **no corpo** e **não no índice**: `buildNavGroups` filtra
por `enabled: false`, que é estático, e não por render efetivo. Medido na
fixture esparsa, a âncora morta passa de `{S4, APP_C}` para
`{S4, APP_C, S_PROTECAO}` — classe pré-existente da [[ADR-167]], com um membro
a mais, não classe nova. **Print intacto**: sob `emulateMedia({media:"print"})`
a entrada do ToC mede altura 0 e "Seguros" não aparece no texto do PDF, então
**nenhuma baseline de print muda**. Só a sidebar de tela ganha uma linha.

### Deferimentos datados — 2026-08-27

O heading anterior dizia "follow-ups **com dono**" e não nomeava nenhum: o
closeout pegou os três como trabalho deferido em lane fechada sem rota, que é o
modo pelo qual eles sumiriam. Cada um agora carrega dono e condição de retomada.

1. **Índice runtime-aware** — `buildNavGroups` filtra por `enabled: false`
   estático, não por render efetivo, então seção com hide-when-empty deixa
   âncora morta no ToC. Medido na fixture esparsa: `{S4, APP_C, S_PROTECAO}`.
   **dono: `information-architect`** (é estrutura de ToC/âncora, não visual).
   **Retomada:** quando houver janela de `workflow_dispatch` de rebaseline
   visual — o fix move baseline de tela de todo relatório, e os 3 ids se
   resolvem de uma vez. Classe da [[ADR-167]], anterior a esta lane; o que a
   l88 acrescentou foi o terceiro membro e a medição.
2. **Ressalva atrás de paywall** — `FREE_TIER_LIMITS.notas = 0` esconde do tier
   free exatamente as limitações da análise. **owner-gated**: é política de tier
   ([[ADR-208]] §D2), não render. Esta lane só passou a declarar o contador, que
   é o mínimo para o leitor free saber que existem ressalvas.
   **Retomada:** na próxima revisão de o que o tier free vê.
3. **`content.version` sem leitor** — waived em
   `dev/check_emitter_without_reader.py` (`WAIVED["PARECER_FIELD:version"]`). O
   comentário do DTO afirma um dispatch v1/v2 por `content.version` que nenhum
   renderer faz. **dono: `senior-cto`** — a decisão é se o dispatch deve existir
   ou se o campo sai. **Retomada:** ao tocar o dispatch de `ancoras` (v1 sem
   `ancoras` usa `evidencia_path`), que é o que o comentário descreve. Enquanto
   isso o waiver segura: ele **falha** se o campo ganhar leitor e a linha ficar.

## O fato, medido (2026-08-26)

Três superfícies emitidas pelo produtor **não têm consumidor no entregue**. É a mesma
classe em três lugares, e é o defeito da própria **KR-C** ("nº de seções que renderizam ==
nº com narrativa emitida") num array diferente.

| # | O que é emitido | Onde morre |
|---|---|---|
| **RR5-01** | 5 notas metodológicas do parecer | `NotaMetodologica` é declarada em [`planner-review.ts`](../../../../frontend/src/lib/api/planner-review.ts) e referenciada **só** pelo próprio DTO; nenhum componente itera o array. Tier `premium`, sem truncagem no backend |
| **RR5-03** | Seção de proteção patrimonial | [`S_ProtecaoSection.tsx`](../../../../frontend/src/components/report/sections/S_ProtecaoSection.tsx) existe completa e **já tem hide-when-empty** (`return null` na `:18`); `MIGRATED_SECTIONS` não contém a chave e o `switch` não tem o `case`; [`report_layout.yaml`](../../../../config/report_layout.yaml) declara `enabled: false` |
| **RR5-04** | Aviso de que há mais riscos | O PDF mostra o total e lista 5; o disclosure existe na tela e **não** no print. O CSS de print esconde o resumo e tenta abrir o bloco com uma custom property **inerte** — a metade que funciona é a que esconde |

**A nota que mais dói:** uma das cinco declara o diagnóstico patrimonial com confiança
**insuficiente**, num run que pausou com seis avisos retidos. O produto renderiza o
diagnóstico e descarta a ressalva do próprio modelo sobre ele.

## O que a medição já descartou

- ~~"a seção de proteção é feature — ligar exige construir o componente"~~ — **refutado na
  U1**: o componente existe, está completo e tem hide-when-empty. A condição escrita no
  próprio YAML (*"P3 liga quando o componente existir"*) **já está satisfeita**. É registro
  + flag + baselines, não feature.
- ~~"ligar a seção publicaria estado vazio para todo cliente"~~ — **refutado**: era a
  objeção que travou o flip na [[A40.l7]], e o `return null` da `:18` a responde.
- ~~"RR5-01 entrega zero das cinco notas"~~ — **PARCIAL** no cético: uma converge ~100
  caracteres com um risco que **é** renderizado. Quatro de cinco se perdem inteiras.
- ~~"o dano do print CSS é na tela"~~ — a [[A40.l7]] examinou o mesmo arquivo e concluiu o
  inverso. O comentário no componente registra a crença invertida, e **com base nela** a
  legenda foi enfraquecida de "N de M" para só o total. O fix apaga o comentário: preservá-lo
  manteria o cúmplice.

## Escopo

1. **Gate RED antes de qualquer fix** — polaridade inversa de `check_view_model_contract.py`
   (que pega *leitor sem emissor*): este pega **emissor sem leitor** no entregue. Vermelho
   sobre os três achados antes do primeiro conserto.
2. **RR5-01** — iterar `notas_metodologicas` no bloco do parecer. Gate: o smoke E2E assere
   presença de ≥1 nota quando o payload traz ≥1.
3. **RR5-04** — estado real em vez de CSS (bloco aberto sob mídia print, ou lista plana) +
   assert de regressão sobre o aviso de truncagem. Restaurar a legenda "N de M" e **apagar**
   o comentário que afirma o oposto.
4. **RR5-03** — `MIGRATED_SECTIONS` + `case` + `enabled: true` + baselines de print e PDF.
   **Exige sign-off do dono**: reverte decisão escrita da [[A40.l7]].

## Fora de escopo

- O **conteúdo** da ressalva e o limiar que ela cita → [[A40.l89]] (o alvo republicado).
- A regra de risco que deveria ter emitido o ponto urgente → [[A40.l90]].
- Baseline visual regenerada sem inspeção — inspecionar a olho, nunca `--update` cego.

## Sequência de entrega (ordem dura)

`1 → 2 → 3 → 4`. O item 2 vem **antes** do 4 e não é indiferente: publicar uma seção nova
enquanto o produto ainda não consegue enunciar a própria confiança é adicionar superfície
antes de adicionar honestidade. Ressalva primeiro, seção depois.

## Critério de aceite

- O gate do item 1 falha por **mutação nas duas direções**: emissor sem leitor ⇒ vermelho;
  leitor restaurado ⇒ verde.
- As 5 notas aparecem no `report.txt` da captura de render, e o percentual de carteira não
  classificada deixa de ter zero ocorrências no entregue.
- O PDF passa a declarar o truncamento, ou entrega os 12.
- A seção de proteção aparece no ToC e nas âncoras quando há dado, e **some** quando não há.
- Baselines de print inspecionadas a olho, com o diff descrito no PR.
- Concluído = PR mergeado em `main` com CI verde.
