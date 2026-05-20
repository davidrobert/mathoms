---
id: MOC-sprint-a15
type: moc
title: "Sprint A15 — FU-3 Imóvel financiado (Debt aggregate + valor_mercado override)"
aliases: ["A15", "Sprint A15"]
---

# Sprint A15 — FU-3 Imóvel financiado (origem 2026-05-19)

> **Status:** planejada (sem `sprint_status` no frontmatter — sprint
> futura, não ativa enquanto A12 ocupa `candidate`). Quando A12 fechar e
> A15 virar próxima, editar este frontmatter para
> `sprint_status: candidate` antes de regenerar índices.

## Resumo

Sprint **dedicada** ao último follow-up out-of-scope do Sprint A12
([[ADR-215]] §Follow-ups · "imóvel financiado: `valor_mercado` ≠
`valor_irpf` + linkagem `saldo_financiamento` ao `property_id`").

**Plano canônico:** [docs/plan/IMOVEL_FINANCIADO/_README.md](../../plan/IMOVEL_FINANCIADO/_README.md) — 5 ondas sequenciais (~10d eng).

**ADR canônica:** [[ADR-227]] (Proposto — A15) — agregado `Debt`
persistido + `property_market_value` versionada + líquido econômico em
`investivel_efetivo`, bruto preservado em cat_2.

**Co-design:** 2026-05-19 com `financial-planner` + `senior-cto` +
`data-engineer` + `product-designer` em paralelo (4 agentes,
single-message N-Agent calls). Síntese consumida em ADR-227 D1-D6 +
alternativas A-G + riscos.

## Por que esta sprint existe

Sprint A12 fechou FU-1 (default conservador `imoveis_no_if=false` ·
[[ADR-223]]) e FU-2 (`asset_catalog` + `lastro_moeda` · [[ADR-224]]).
FU-3 ficou registrado como débito explícito em ADR-215 §Riscos:

> Imóvel financiado com saldo devedor distorce patrimônio bruto. Fora
> do escopo desta ADR. Follow-up: `valor_mercado` + linkagem
> `saldo_financiamento` ao passivo correspondente. ADR futuro.

Auditoria 2026-05-19 confirmou dois bugs silenciosos em produção:

1. **Bug 1 — Patrimônio bruto defasado** ([`patrimonio_calculator.py:_split_imoveis`](../../../pipeline/domain/services/patrimonio_calculator.py))
   usa `valor_brl` IRPF (custo histórico). Apto declarado R$ 800k em
   2018, R$ 1,2M hoje, R$ 300k saldo devedor → relatório mostra 800k
   bruto. Patrimônio LÍQUIDO real é ~900k mas usuário vê 800k "limpo".
2. **Bug 2 — IF mal-calibrado** quando `imoveis_no_if=true` E cat_2 é
   locado: `investivel_efetivo` usa `valor_irpf` no numerador, mas
   yield real é sobre `valor_mercado`. Capital econômico (1,2M − 300k =
   900k líquido) ≠ IRPF (800k). `progresso_if` matematicamente errado.

Não cabe em sprint compartilhada — escopo de ~10d eng atravessa schema
DB + pipeline + backend API + frontend, com co-design fechado em ADR
dedicada.

## Achado de auditoria que mudou o escopo

**Backend não tinha agregado `Debt`** — passivo vivia apenas como
`total_dividas` agregado em `baseline_patrimonial` (extraído de IRPF).
[`EndividamentoAnalyzer`](../../../pipeline/domain/services/endividamento_analyzer.py)
gera `DividaItem` em runtime no E5 com descrição hardcoded
`f"Financiamento imobiliário ({nome})"`, **sem persistir em DB**. FU-3
**cria o agregado Debt do zero** (decisão consciente: modelar todas as
classes de passivo agora — CDC, consignado, cartão rotativo,
financiamento imobiliário, outros — pavimentando futuro sem ADR
adicional). Briefing original assumia "adicionar FK em modelo
existente"; auditoria mostrou que não havia modelo.

## Ondas / lanes ready

| # | Onda | Lane | Agent | Estimativa |
|---|---|---|---|---|
| 1 | Schema + repos + models | [a15-fu3-onda1-schema](tracks/a15-fu3-onda1-schema.md) | `data-engineer` | ~2d |
| 2 | Backfill `total_dividas` → Debt | [a15-fu3-onda2-backfill](tracks/a15-fu3-onda2-backfill.md) | `data-engineer` | ~1d |
| 3 | Calculator + resolver puro | [a15-fu3-onda3-calculator](tracks/a15-fu3-onda3-calculator.md) | `senior-cto` + `data-engineer` | ~3d |
| 4 | API endpoints + OpenAPI | [a15-fu3-onda4-api](tracks/a15-fu3-onda4-api.md) | `senior-cto` | ~1.5d |
| 5 | Frontend: form, batch review, drill-down | [a15-fu3-onda5-frontend](tracks/a15-fu3-onda5-frontend.md) | `product-designer` | ~2.5d |

**Total:** ~10d eng. Coordenação entre ondas em [PLAN-imovel-financiado §Coordenação](../../plan/IMOVEL_FINANCIADO/_README.md). Paralelismo possível em Onda 3 + 4 (calc e API independentes do schema mergeado).

## Invariantes não-negociáveis

1. **`saldo_devedor_cents BIGINT`** ([[ADR-090]]) — proibido `float`.
2. **`ON DELETE RESTRICT`** em `Debt.property_id` — órfão silencioso é
   classe inteira de bug em fintech.
3. **`needs_review=true`** em rows de migration — toda Debt extraída do
   baseline IRPF exige confirmação humana antes de afetar
   `investivel_efetivo`.
4. **Heurística nunca atribui Debt a property** — apenas user-driven.
5. **TTL sem fallback automático** — após 12m, banner persistente;
   sistema mantém valor declarado até user atualizar (anti-padrão
   "KPI muda sem aviso" — [[ADR-223]] §Riscos).
6. **`PatrimonioCalculator` puro** — recebe `RealEstateValuationContext`
   pré-carregado via `PatrimonioInputs`; nenhum I/O ou cache in-memory
   ([[ADR-111]]).
7. **Per-property vence agregado IRPF** quando ambos existem; warning
   de domínio tipado ([[ADR-097]] D1) quando ratio >1.1.
8. **Patrimônio bruto na tabela preserva invariante** "categoria =
   ativo bruto, passivo = bucket separado"; líquido apenas em
   `investivel_efetivo`.

## Pickup — antes de pegar lane

1. `git fetch origin` está atualizado.
2. Veja worktrees ativos: `git worktree list`.
3. Veja branches `agent/*` recentes: `git for-each-ref --sort=-committerdate refs/remotes/origin/agent/`.
4. Lane com slug em uso (worktree OU branch <24h): **não duplique**.
5. Slug das lanes desta sprint: prefixo `a15-fu3-`.
6. **Confirmar dependências:** ondas têm dependência sequencial.
   Onda 1 (schema) é gate. Onda 3 depende de Onda 1 + 2. Onda 5 depende
   de Onda 4. Pickup respeita ordem.

## Definition of Done

Esta sprint fecha quando:

- ☐ Tracks 1-5 mergeados em `main` com CI verde (CLAUDE.md §"Concluído").
- ☐ [[ADR-227]] flippada `Proposto → Decidido (A15)` em PR de cleanup
  pós-implementação.
- ☐ Workspace dogfood `5@5.com` migrado + batch review concluído.
- ☐ Goldens E5 atualizados commitados.
- ☐ Snapshot OpenAPI atualizado.
- ☐ `docs/reference/DB_SCHEMA_REFERENCE.md` regenerado.
- ☐ Changelog entries em `docs/sprint/A15/changelog/`.
- ☐ Plano canônico arquivado em `docs/archive/IMOVEL_FINANCIADO-YYYY-MM-DD.md`.
- ☐ Smoke test humano em [docs/reference/SMOKE_TEST_HUMAN.md](../../reference/SMOKE_TEST_HUMAN.md)
  atualizado se fluxo novo de declaração entrou no scope.

## Telemetria pós-deploy

- `mathoms.real_estate.valor_mercado.declarations_count` — declarações por workspace.
- `mathoms.real_estate.debt.link_to_property_rate` — % de Debt com
  `property_id NOT NULL`.
- `mathoms.real_estate.kpi_delta_pre_post_cutover` — `Δ` em patrimônio
  bruto + `investivel_efetivo` por workspace na primeira semana.

## Sprints anteriores e contexto

- **A12** (candidate, em fechamento) — categorization learning loop +
  follow-ups A11 + bank account disambiguation (ADR-226). FU-1 + FU-2
  do A12 entregues.
- **A11** (current) — Platform review execution.

Detalhe por sprint: [docs/_MOC/SPRINTS-active.md](../../_MOC/SPRINTS-active.md).

## Referências

- [[ADR-227]] — decisão canônica.
- [[ADR-215]] §Follow-ups — origem do FU-3.
- [[ADR-216]] §D6 — trilho `valor_imovel_origem` (entregue, agora
  populado).
- [[ADR-142]] — invariante anti-dupla-contagem em IF.
- [[ADR-222]] / [[ADR-223]] — toggle per-workspace + default conservador.
- [[ADR-225]] — `codigo_rfb` invariante; `Debt.property_id` referencia
  UUID interno de `PropertyIdentity`.
- Plano canônico: [docs/plan/IMOVEL_FINANCIADO/_README.md](../../plan/IMOVEL_FINANCIADO/_README.md).
- Sprint anterior relacionada: [Sprint A12](../A12/_README.md) (FU-1 + FU-2).
