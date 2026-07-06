---
id: A28.l6
type: lane
title: "proteção patrimonial ativada: apólices extraídas fluem para compute_protecao + pontos_urgentes condicional"
sprint: A28
plan: PLAN-report-trust
status: shipped
ship_pr: 783
ship_date: "2026-07-06"
priority: P1
branch_slug: protecao-apolices-flow
adrs:
  - "[[ADR-240]]"
  - "[[ADR-239]]"
parallel_with:
  - "[[A28.l5]]"
  - "[[A28.l7]]"
  - "[[A28.l8]]"
tags:
  - type/lane
  - sprint/a28
  - status/shipped
  - priority/p1
  - area/pipeline
  - breaking/schema
---

# A28.l6 — `protecao-apolices-flow` (Onda 1 · Should · reescopo data-engineer)

## Problema

3 apólices foram extraídas em `extract_comprovantes_bens` no dogfood
`72883bde`, mas o relatório afirma "**nenhuma apólice identificada**". O
parecer E6 gastou sua sugestão P0 pedindo `$.protecao_patrimonial.apolices` —
dado que o pipeline **já extraiu** mas nunca entregou ao E5.

Raízes (investigação data-engineer 2026-07-03):

1. O balde E4 `seguros` é **placeholder hardcoded** — `serialize_e4_artifacts`
   grava `{"dados": []}` incondicionalmente, sem nunca consultar apólices. Não
   é pipe quebrado; o contrato nunca existiu.
2. O texto "nenhuma apólice identificada" vem de `pontos_urgentes_analyzer.py`
   que emite o item de seguro **incondicionalmente** ("não há como inferir hoje
   — sempre adiciona"). Popular o balde não muda o relatório sem tornar o item
   condicional.
3. O consumidor canônico já existe e é **dead code**: `ProtecaoInput.apolices`
   + `compute_protecao` ([[ADR-240]], pilar S_PROTECAO/AUVP) e
   `apolice_reconciliation.reconcile_apolice_bens` ([[ADR-239]] D3) não têm
   caller de produção.

## Escopo

1. **Wire `extract_comprovantes_bens` → `compute_protecao`** (ativa ADR-240):
   apólices extraídas alimentam `ProtecaoInput`; `protecao_patrimonial` passa a
   existir no payload E5 (o schema `protecao_patrimonial.schema.json` já
   existe). Reconciliação apólice→bem via `reconcile_apolice_bens` (ADR-239 D3).
2. **`pontos_urgentes` condicional:** o item "Contratar seguro de vida e
   invalidez" diferencia cobertura por tipo — apólices auto/residencial vigentes
   ≠ seguro de vida; a copy nunca afirma "nenhuma apólice identificada" quando
   há apólice vigente de qualquer tipo.
3. **Balde E4 `seguros` como substrato do E6** (secundário): popular com as
   apólices para o exec-context do parecer; adicionar branch explícito de
   `seguros` ao `e4_unified.schema.json` (hoje cairia no branch genérico de
   `dados`) com bump de versão do contrato.
4. **Dependentes no exec-context:** projetar `irpf_kpis.dependentes` no
   manifest do parecer (par com [[A28.l11]] — quem tocar o manifest primeiro
   leva; coordenar para não duplicar).

## Critério de aceite

- Teste: `compute_protecao` recebe as 3 apólices (fixture sintética PII-zero) e
  produz flags de proteção; `protecao_patrimonial` presente no payload E5.
- `pontos_urgentes` não emite "nenhuma apólice identificada" quando há apólice
  vigente; item de seguro de vida continua quando só há auto/residencial (copy
  diferenciada).
- Rebaseline de `backend/tests/snapshots/dogfood_view_model.json` (pina o texto
  hardcoded atual) com diff explicado.
- `e4_unified.schema.json` com branch `seguros` explícito; validação schema do
  hook pós-write verde em modo atual.
- Parecer re-gerado não lista `$.protecao_patrimonial.apolices` em
  `campos_faltantes` (o dado agora existe).

## Notas

- Sem migration Alembic (contrato de artefato, não de DB).
- Co-design `financial-planner` na regra de cobertura mínima (o que conta como
  "protegido") se a lane for além de presença/vigência — MVP é presença.

## Owner

Agente da lane; co-design `data-engineer` (contrato E4/schema) feito 2026-07-03.
