---
id: A28.l9
type: lane
title: "banner agregado de qualidade de dados no relatório + ressalva de fallback no Monte Carlo"
sprint: A28
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: report-data-quality-banner
adrs: []
depends_on:
  - "[[A28.l4]]"
parallel_with:
  - "[[A28.l10]]"
  - "[[A28.l11]]"
tags:
  - type/lane
  - sprint/a28
  - status/in-progress
  - priority/p1
  - area/frontend
---

# A28.l9 — `report-data-quality-banner` (Onda 2 · Should · merge após Onda 0)

## Problema

O relatório afirma completude que os dados não sustentam: o hero entrega score
7,2 e PL sem ressalva, enquanto os sinais de degradação existem mas ficam
**escondidos dentro de cards individuais** (`<details>` de imóveis excluídos,
itálico cinza no `motivo_sem_cone`, badge "Parcial" preso no card de
premissas). Não há visão agregada de "quão confiável é este relatório". Casos
do dogfood `72883bde`: R$ 401k não classificado (23%), 13 documentos
needs_review, **10/10 premissas econômicas em fallback com o Monte Carlo
exibindo probabilidade precisa (31%) sem ressalva**, 11 imóveis fora do módulo
de yield, "Perfil tributário incompleto", e `ReportPremissasBlock` vazando
`JSON.stringify` cru no relatório.

## Escopo

Spec do product-designer (revisão 2026-07-03):

1. **`ReportDataQualityBanner`** — componente novo em `ReportShell`, entre
   `ExecutiveSummarySection` e a primeira seção. Reusa `<Alert
   severity="warning">` existente (padrão `DefasagemWarningBanner`). Consolida
   sinais que **já existem no DTO**: despesas não classificadas >10% (valor +
   % + CTA reclassificação), documentos needs_review (CTA
   `/documents?filter=needs_review`), premissas de mercado em fallback, imóveis
   com classificação pendente (CTA Configurações). Cada linha com CTA de
   resolução ("erros resolvem" — COPY_GUIDELINES). Colapsa para barra fina
   quando tudo limpo.
2. **Propagar `premissas_economicas.status` para S7** (`IFMonteCarloBlock`):
   quando `parcial`/`indisponivel`, `<Alert severity="warning">` acima do cone
   — "Projeção baseada em premissas de mercado padrão, não calibradas à sua
   carteira; trate as probabilidades como referência". **Nunca** renderizar
   probabilidade precisa sobre fallback sem ressalva.
3. **Remover `JSON.stringify`** do `ReportPremissasBlock` — renderizar snapshot
   como tabela legível ou remover.
4. **Rótulo de janela em valor mensalizado** (consome o rótulo criado pela
   [[A28.l4]]): padrão `InfoTooltip` (como `TrsEfetivaStat`) — "média 40m" vs
   "últimos 12m"; nunca duas mensalizações sem rótulo.
5. **Tratamento visual de `nao_identificado`** no `DespesasDoughnutChart`:
   fora da paleta categórica (cinza neutro/hachura), datalabel sempre visível,
   conclusão condicional promovida a `<Alert>` inline persistente quando >10%.
6. A11y dos sinais de degradação: ícone + `role`/`aria-label`, não só
   cor/itálico.

## Critério de aceite

- **Teste de honestidade:** leitor que vê só hero + banner responde "quão
  confiável é este relatório?" sem abrir `<details>` — verificado com a fixture
  do payload dogfood com todos os degrades ativos.
- Nenhuma probabilidade/projeção renderizada sobre premissa
  `parcial`/`indisponivel` sem `<Alert>` adjacente (fixture de premissas
  fallback).
- `rg 'JSON.stringify' frontend/src/components/report/` → zero em contexto
  user-facing.
- `nao_identificado > 10%` dispara sinal persistente (fixture dogfood).
- Banner colapsado (barra fina) quando não há sinais — sem ruído para relatório
  saudável.
- Regressão visual (Playwright snapshot) da fixture com degrades ativos;
  `cd frontend && npm test -- --run` verde; `tsc --noEmit` local (PR-CI não
  roda typecheck).

## Notas

- **Skeleton em paralelo, merge após Onda 0** — o banner consome números que
  l1/l2/l4 corrigem; mergear antes gera retrabalho de snapshot.
- Curadoria de pontos fortes/alertas é da [[A28.l10]] (server-side +
  defensivo) — este banner não maquia dado contraditório; se duas seções
  discordam, o fix é a montante (Onda 0).

## Owner

Agente da lane; spec `product-designer` feita 2026-07-03 (revisão de origem).
