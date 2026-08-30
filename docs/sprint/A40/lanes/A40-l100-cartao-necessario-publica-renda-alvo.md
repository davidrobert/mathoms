---
id: A40.l100
type: lane
title: "O cartão rotulado NECESSÁRIO publica a renda-alvo, não o aporte que o motor calcula"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1845
ship_date: "2026-08-30"
priority: P0
branch_slug: a40-l100-cartao-necessario-publica-renda-alvo
owner: financial-planner
depends_on: []
adrs:
  - "[[ADR-418]]"
  - "[[ADR-373]]"
tags: [type/lane, sprint/a40, status/shipped, priority/p0, area/frontend, area/financial-planning]
---

# A40.l100 — `cartao-necessario-publica-renda-alvo`

## ✅ Entregue em 2026-08-30 — o defeito procedeu; o remédio prescrito, não

O bloco mentiroso **saiu** do cartão (PR #1845). O enunciado mandava o cartão passar
a ler "o PMT que o motor já calcula" — **esse PMT não existe no relatório**, e a
medição abaixo é o que trocou o remédio.

### O que a medição derrubou do próprio enunciado

| Fato medido | Consequência para o remédio |
|---|---|
| `goals` do E5 tem 18 chaves e **nenhum aporte**. O único produtor de PMT do repo é `goal_service.compute_if_derived` — agregado `Goal`, rota `/plano` | "ler o PMT" exigiria um contrato **Goal→E5 novo**, que não existe |
| `IFProjector` resolve **prazo** a partir do aporte declarado ([[ADR-373]]), nunca o inverso. No dogfood `aporte_mensal_usado = 0` e `prazo_declarado_anos = None` | nenhum PMT é **computável** nesse workspace: faltam os dois inputs |
| As "cinco superfícies" que o enunciado dizia carregar o PMT publicam o aporte **declarado** (`aporte_mensal_usado`, `cenarios_conjuge.premissas.aporte_base`) — ambos `0` aqui | a "cadeia do PMT" no relatório **não existia**; existe na rota `/plano`, fora do documento |

O núcleo do achado, porém, **fica mais forte**: as três superfícies que de fato usam
o rótulo "Aporte mensal necessário" (`/plano/meta-if`, wizard, `IFHeroCard`) leem
`ifMonthlyContributionDisplay` — o PMT real. O cartão do relatório era mesmo o
**único** ponto fora da cadeia.

### Por que o bloco saiu em vez de ser rerrotulado

1. O mesmo número já é publicado **corretamente** pelo `S7Stat`, com o nome certo
   ("a renda-alvo declarada"). Rerrotular produzia duplicata.
2. `if_trs_monthly_value` deriva da meta e está **sempre presente** — sua presença
   incondicional tornava **inalcançável** o estado honesto
   `"Meta de aporte não configurada."`, que é a mensagem acionável e coerente com o
   `motivo_prazo_indefinido` do próprio payload ("você ainda não declarou quanto
   pretende aportar por mês").
3. `investimentos.estrategia_aporte` **não tem produtor** em `scripts/` nem
   `pipeline/` — o `report_spec.md` o descreve saindo do `definitions.md`, morto na
   migração de config → DB. Logo o ramo rico do cartão é morto e o fallback, que
   carregava o defeito, é o **único** que renderiza em qualquer relatório.

### A fixture discriminante, verificada em subconjuntos

Três valores distintos — renda-alvo `333.333` · aporte declarado `20.000` · PMT
`42.111` — em `frontend/tests/components/EstrategiaAporteCard.test.tsx`. Cada
mutante cai por uma assertion **independente**:

| Mutante | Assertion que pega |
|---|---|
| cartão lê a renda-alvo (defeito original, restaurado de `HEAD`) | `not.toContain("333.333")` |
| cartão lê o aporte **declarado** sob rótulo "necessário" | `not.toMatch(/necess[áa]rio/i)` |

### Follow-up registrado (fora do escopo deste PR)

**Nenhuma das 6 fixtures de `frontend/tests/e2e/fixtures/reports/` carrega
`if_trs_monthly_value`** — inclusive a `medium`, declarada "superfície completa".
Por isso a suíte e2e **nunca exercitou** o defeito, e a baseline visual não muda com
o conserto (antes e depois caem no mesmo empty state). É o modo de falha que o
próprio docstring do `report-inventory.@critical.spec.ts` nomeia: *"a fixture não tem
o dado NÃO é justificativa aceitável"*. Enriquecer a `medium` com o bloco `goals`
real do dogfood é trabalho de outra lane.

**Deferido — o cartão ainda não responde "quanto aportar".** Publicar um PMT de
verdade no relatório exige contrato `Goal → E5` (`aporte_necessario_mensal_brl`) e
depende de a família ter declarado horizonte. Não foi aberto ADR: a decisão cabe à
lane que puxar o contrato, e reservar ID aqui violaria a regra de não reservar
número ([[ADR-345]]).


> **Origem:** `F1` da rodada unificada **U3** ([[REPORT-REVIEWS-active]] §r7). Confirmado por
> cético, que **refutou o discriminador da lente** e tornou o achado mais forte.

## O defeito

O cartão rotulado **"APORTE MENSAL NECESSÁRIO"** publica `renda_alvo ÷ 12` — a renda que a
família quer receber na independência —, não o aporte que a atingiria. ~~O motor **já tem** o
PMT correto e ele aparece em cinco superfícies (Projeção, Cone MC, Síntese, a decisão do
plano e o Apêndice C)~~ — **falso, ver §Entregue:** no relatório essas superfícies publicam o
aporte **declarado**; o PMT só existe em `goal_service`, na rota `/plano`. O número do cartão
era, esse sim, o **único ponto do documento fora da cadeia**.

## O que o cético derrubou, e por que isso importa

A lente propôs que o cartão passasse a ler o agregado de aporte declarado. **Errado por
sorte:** neste workspace o goal declarado e o PMT coincidem, então o critério de aceite
"batem" passaria nas **duas** implementações. Um cartão rotulado *necessário* tem de ler o
**PMT**, não a meta declarada.

**Critério de aceite (o da lente não discrimina):** fixture em que o goal declarado ≠ PMT.
Se o cartão exibir o goal, ele lê a coisa errada e o rótulo mente do mesmo jeito.
