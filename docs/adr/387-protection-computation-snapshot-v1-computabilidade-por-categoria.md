---
id: ADR-387
type: adr
title: "ProtectionComputationSnapshotV1 pina insumos ao run e declara computabilidade por categoria"
status: Proposto
phase: A40.l62
date: "2026-08-13"
relates_to:
  - "[[ADR-131]]"
  - "[[ADR-135]]"
  - "[[ADR-187]]"
  - "[[ADR-192]]"
  - "[[ADR-240]]"
  - "[[ADR-365]]"
supersedes: []
superseded_by: []
aliases: ["ADR 387", "ProtectionComputationSnapshotV1", "computabilidade de proteção"]
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/pipeline
  - area/persistence
  - area/report
  - area/financial-planning
  - phase/a40-l62
---

# ADR-387 — `ProtectionComputationSnapshotV1` pina insumos ao run

> Origem: co-design da [[A40.l35]] em 2026-08-13 (`financial-planner` +
> `data-engineer` + `product-designer`, decisão final `senior-cto`). A decisão é
> `Proposto` até a [[A40.l62]] entregar migration, contrato e hash composto.

## Contexto

O `Report` referencia um E5 exato pela [[ADR-131]], mas o adapter de proteção lê
`Protection`, `FamilyMember` e `Workspace` vivos e usa o relógio corrente. Injetar
esse resultado no GET faria um relatório histórico mudar sem novo run, violando
a fotografia imutável da [[ADR-187]].

Os cinco zeros e dois `False` medidos na [[A40.l35]] tampavam uma insuficiência de
contrato: E5 não tem renda ativa líquida mensal canônica nem status/situs EUA;
UF e parâmetros fiscais vigentes também não podem ser inferidos. E1.x antigo não
é recuperável com precisão por run. Ausência não é zero nem prova de inexistência.

## D1 — Snapshot imutável no Report

`Report.protection_snapshot_json` será nullable, sem backfill e sem fallback live.
O `ProtectionComputationSnapshotV1` será criado uma vez junto com o Report e terá:

- `snapshot_version`, `pipeline_run_id`, `analysis_artifact_id`;
- `captured_at`, data da análise e vigências fiscal/metodológica separadas;
- cadastro de apólices/membros/perfil observado na geração;
- inputs em cents/inteiros, estado de disponibilidade e proveniência;
- output do bundle e status por categoria.

Report legado sem snapshot mantém proteção indisponível. `get_report_data` apenas
injeta a fotografia persistida; não consulta cadastro nem relógio.

## D2 — Computabilidade por categoria

Cada categoria declara `computed`, `not_applicable` ou `missing_data`, com lista
de inputs ausentes. Calculator incompleto não roda e não publica gap,
recomendação ou risco. Zero observado continua sendo zero com proveniência.

- **vida:** exige dependente econômico menor confirmado, renda ativa anual e
  dívidas; sem dependente não publica `10× renda`, conforme [[ADR-365]];
- **invalidez:** exige rendas ativa e passiva líquidas mensais da mesma base;
- **sucessório:** exige patrimônio bruto, UF explícita e parâmetro ITCMD vigente;
- **EUA:** exige status/situs, renda, valor e thresholds explícitos; USD não prova
  situs e desconhecido não vira `False`.

## D3 — Pin ao run e hash

E5 é fonte canônica de patrimônio e dívidas; E1.x não é relido por `latest` no
GET. Novos campos de renda e exposição serão produzidos durante o run com ids de
origem. O hash da [[ADR-187]] passa a cobrir E5 + digest canônico do snapshot de
proteção, com versão explícita do algoritmo.

## D4 — Rollout fail-closed

A [[A40.l61]] vem primeiro e elimina defaults perigosos sem expor a S9. A
[[A40.l62]] entrega fontes + snapshot. Só então a [[A40.l35]] injeta o bundle e
executa render/PDF. Uma pré-lane mergeada não satisfaz o aceite da seguinte.

## Alternativas rejeitadas

- **Recalcular no GET:** mistura E5 histórico com cadastro atual.
- **Ler E1.x `latest`:** não prova que o artefato foi consumido pelo run.
- **Aproximar renda ativa:** mistura janelas/bruto/líquido e fabrica precisão.
- **Usar USD como EUA ou UF=SP:** converte indício/ausência em fato fiscal.
- **Mover bundle para E5:** altera cache/hash do parecer por um overlay de UI.

## Consequências

- Migration nullable, schema versionado e novo campo E5 exigem trabalho antes da
  ativação; o custo compra reprodutibilidade e auditabilidade.
- Endpoint live e snapshot do Report passam a ter temporalidades declaradas.
- Nenhum relatório existente ganha bundle retrospectivo por reconstrução.
- Logs expõem apenas ids, versões e statuses; nunca valores, CPF ou apólices.

## Não-objetivos

- Recomendar holding, produto de seguro ou estratégia fiscal individual.
- Deduplicar monetariamente apólice documental e cadastro sem identidade comum.
- Reabrir os thresholds metodológicos dos calculators puros.

## Critério de aceite

- Reload do mesmo Report é byte-idêntico após mutar cadastro e relógio.
- Ausência de qualquer input obrigatório retém apenas a categoria afetada.
- Zero legítimo é distinto de ausência e traz proveniência.
- Gap de invalidez diferente de zero só aparece após contrato E5 líquido canônico.
- UF/parâmetro ausente retém ITCMD; exposição EUA desconhecida não vira `False`.
- Hash de publicação detecta alteração do snapshot composto.
- Schema strict, OpenAPI/view-model snapshot, golden e render/PDF tri-state verdes.
