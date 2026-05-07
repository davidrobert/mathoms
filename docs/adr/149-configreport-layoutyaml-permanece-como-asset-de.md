---
id: ADR-149
type: adr
title: "`config/report_layout.yaml` permanece como asset de produto (Sprint A8.0)"
status: Decidido
phase: "Sprint A8.0"
date: "2026-04-27"
relates_to: ["[[ADR-076]]", "[[ADR-143]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 149"]
tags:
  - area/llm
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 58
---

# ADR-149 — `config/report_layout.yaml` permanece como asset de produto (Sprint A8.0)

**Status:** Decidido (Sprint A8.0) • **Data:** 2026-04-27 • **Relaciona** [ADR-076](#adr-076--design-tokens-unificados-site--relatório), [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76).

**Contexto:** A Sprint A7 (Config DB Cutover) deletou 10 dos 11 arquivos de `config/` migrando-os para DB ou docstrings + ADRs (rules-as-code, A7.6). O 11º arquivo, `config/report_layout.yaml`, **não foi deletado** em A7.5. CTO G4 review do PR #15 marcou isso como trade-off aceito mas pediu formalização via ADR.

A diferença fundamental: enquanto os outros 10 arquivos eram (a) instâncias cliente-específicas (decisions, family_members, etc.) ou (b) regras universais documentadas como markdown paralelo ao código, o `report_layout.yaml` é **um asset de produto que alimenta dois consumidores estruturados**:

1. **Codegen determinístico** (ADR-076 · `dev/codegen_report_layout.py`):
   - YAML → `frontend/src/generated/report-layout.ts` (TypeScript types).
   - YAML → `backend/app/generated/report_layout.py` (Pydantic models).
   - Codegen roda em pre-commit hook + CI (`Report layout codegen (TS/Pydantic) em sync com YAML (ADR-076)`). Mudança no YAML sem rerun do codegen é hard error.

2. **Default global da API config** (`backend/app/services/config_defaults.py::load_global_json` aplicado a `report_layout.yaml`): quando workspace não tem override em `report_layouts` table, o blob global do YAML é servido. Endpoint `GET /api/v1/workspaces/{id}/config/report-layout` retorna o YAML default + override se existir.

Migrar `report_layout.yaml` para fora de `config/` exigiria:

- Reescrever o codegen (`dev/codegen_report_layout.py`) para apontar para o novo path.
- Reescrever o endpoint de defaults (`backend/app/services/config_defaults.py` + `backend/app/api/config.py`).
- Atualizar todas as referências em ADRs (ADR-076 e correlatas).
- Atualizar pre-commit hook + CI para o novo path.
- Documentar onde o YAML "real" vive agora (`docs/`?, `frontend/src/`?, novo `assets/`?, DB seed?).

Alternativas consideradas:

- **(a) Deletar como os outros 10 arquivos.** Custo: trabalho descrito acima. Sem ganho funcional — o YAML é editado apenas por desenvolvedores Mathoms (não pelo cliente final em UI hoje), e seu conteúdo é universal (template do produto, sem dados cliente).
- **(b) Migrar para DB-first** (`report_layouts` table absorve template global + overrides como A7.3 fez para `categorization`). Custo: schema migration + seed + UI editor (decisão de produto adiada explicitamente em A7.0/A7.1 task list — "UI editor de report layout é decisão de produto futura"). Sem demanda atual.
- **(c) Manter `config/report_layout.yaml` como asset de produto.** Bloquear paths individuais em `dev/check_forbidden_paths.py` (Sprint A7 bloqueou os 10 arquivos deletados, NÃO o diretório `config/` inteiro), permitindo `report_layout.yaml` + outros assets legítimos (`config/schemas/`, `config/prompts/`, `config/templates/`, `config/scoring.json`, `config/pipeline.json`) coexistirem.

**Decisão:** Adotar **(c)**.

`config/` permanece como diretório de **assets de produto editáveis por desenvolvedores Mathoms** (não pelo cliente final), distintos de **dados cliente-específicos** (que vivem em DB) e de **regras universais codificadas** (que vivem em docstrings + ADRs). A política de paths proibidos é por arquivo, não por diretório.

Critério para algo poder ficar em `config/`:

1. **Não contém PII nem dados cliente-específicos.** ✅
2. **É consumido por código de produto** (codegen, API defaults, prompts LLM, schemas JSON). ✅
3. **Edição é responsabilidade do time Mathoms**, não do cliente final. ✅
4. **Não há schema DB modelado** que torne o asset redundante (se houver, segue padrão A7.3 catalog/override). ✅

Arquivos atualmente em `config/` que cumprem o critério:

- `report_layout.yaml` — esta ADR.
- `pipeline.json` — parâmetros operacionais do pipeline (workspace overrides em `pipeline_configs` table; default global aqui).
- `scoring.json` — pesos do score financeiro (universal de produto, sem versão cliente; potencialmente migrado em sprint futura se variar por workspace).
- `schemas/*.schema.json` — JSON Schemas de validação de artefatos do pipeline. Universal.
- `prompts/section_summaries.yaml` — prompts LLM versionados (ADR-144). Universal.
- `templates/` — templates editoriais consumidos pelo pipeline. Universal.

**Consequências:**
- ✅ Trade-off A7.5 formalizado — auditor futuro tem ADR para citar em vez de uma nota em PR description.
- ✅ Política de paths proibidos clarificada: bloqueio por arquivo, não por diretório. Permite `config/` evoluir como diretório de assets de produto sem precisar criar novo diretório.
- ✅ Critério explícito: novo asset em `config/` precisa cumprir os 4 itens (não-PII, consumido por código, time Mathoms edita, sem schema DB redundante).
- ⚠️ "Sprint A7 entregou 100% DB-first" tem asterisco: configs **cliente-específicas** estão DB-first; assets de **produto** continuam em `config/`. Documentação refletir isso (CLAUDE.md §Fontes de verdade já distingue corretamente).
- ⚠️ Se demanda futura exigir **cliente edita report_layout em UI**, esta ADR é superseded por nova ADR que migra para DB-first via padrão A7.3 catalog/override.
- ❌ Diretório `config/` sobrevive — perda de simplicidade conceitual ("removemos config/ inteiro" é narrativa mais forte que "removemos 10 dos 11 arquivos"). Aceito.
