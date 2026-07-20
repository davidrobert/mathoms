---
id: A37.l5
type: lane
title: "Fragmento de apólice real do dogfood em prompt versionado — trocar por exemplo sintético"
sprint: A37
status: open
priority: P1
branch_slug: a37-l5-prompt-apolice-exemplo-sintetico
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/open
  - priority/p1
  - area/llm
  - area/seguranca
---

# A37.l5 — `prompt-apolice-exemplo-sintetico` (PII-01)

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

O exemplo hardcoded no prompt de extração de apólice
(`pipeline/llm/prompts/apolice.py:37`) contém um sufixo numérico **idêntico**
ao número de apólice real de um documento do workspace dogfood (verificado
contra os artifacts E2 do run `6659d62c`). Dado de dogfood vazou para arquivo
**commitado** — relevante para o gate de repo público (plano PUBLIC_RELEASE /
A34, camadas de PII).

## Escopo

- Substituir o exemplo por valor **sintético** (formato plausível, sem colisão
  com dado real; seguir o padrão da fixture sintética PII-zero de
  `tests/fixtures/pipeline_golden/`).
- Varredura curta nos demais prompts de `pipeline/llm/prompts/` e
  `config/prompts/` por literais numéricos longos (≥7 dígitos) que possam ter a
  mesma origem — corrigir no mesmo PR ou registrar achado.
- Avaliar histórico git: o valor entrou em commit antigo? Registrar no PR se a
  janela de exposição importa para o rewrite de história já planejado na A34
  (não executar rewrite aqui).

## Critério de aceite

- Nenhum literal do prompt coincide com identificadores dos artifacts do
  dogfood (verificação documentada no PR).
- Gate de PII do pre-commit passa; eval/golden de extração de apólice continua
  verde (o exemplo troca de valor, não de shape).

## Risco

Baixo — mudança de literal em prompt; risco real é drift de extração se o
exemplo mudar de *formato* (manter formato idêntico, só valor).
