---
id: A43.l7
type: lane
title: "Plugin e skill universal mínimos para ChatGPT e Codex"
sprint: A43
plan: PLAN-competitive-pierre
status: planned
priority: P1
branch_slug: a43-l7-plugin-e-skill-universal
depends_on: ["[[A43.l4]]", "[[A43.l5]]"]
adrs: ["[[ADR-207]]", "[[ADR-319]]"]
tags: [type/lane, sprint/a43, status/planned, priority/p1, area/ai-platform, area/product]
---

# A43.l7 — Plugin e skill universal

> **Origem:** [[A43]] · [[PLAN-competitive-pierre]].

## Decisão

Criar plugin mínimo com `.codex-plugin/plugin.json`, referência ao MCP e skill dos
três jobs. O skill é instrução pública de uso, não cópia de metodologia, prompt ou
regra. Distribuição é privada/repo marketplace ou developer mode; listing/UI ficam fora.

## Critério de aceite

- Manifest/paths/metadata válidos e mesma identidade estável nas duas superfícies.
- Instalação limpa funciona no ChatGPT e no Codex por documento versionado.
- Skill define trigger, workflows, fontes/`as_of`, limites e recusas; zero rules,
  prompt de produção, metodologista ou dado real.
- Starter prompts cobrem os jobs sem prometer aconselhamento genérico.
- Tool descriptions não espelham nomes internos; scan [[ADR-207]]/[[ADR-319]] passa.
- Desinstalar/desabilitar não remove conta, grant ou dados.
