---
id: ADR-180
type: adr
title: "`goals.json` cutover final via `StageConfig.config_store` extendido"
status: Decidido
phase: "Sprint A10.6"
date: "2026-05-06"
relates_to: ["[[ADR-088]]", "[[ADR-089]]", "[[ADR-101]]", "[[ADR-134]]"]
supersedes: ["[[ADR-077]]"]
superseded_by: []
aliases: ["ADR 180"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 54
---

# ADR-180 — `goals.json` cutover final via `StageConfig.config_store` extendido

**Status:** Decidido (Sprint A10.6) • **Data:** 2026-05-06 • **Data de decisão:** 2026-05-07 • **Supersedes** [ADR-077](#adr-077--pipeline-adapter-como-contrato-de-cutover-cli--web) §"Contrato de cutover" (checkbox "100% dos campos lidos pelo E5/E5.N/E6") • **Relaciona** [ADR-088](#adr-088--stageconfig-configuração-imutável-por-parâmetro), [ADR-089](#adr-089--pipelinedomain-camada-de-domínio-isolada-de-io), [ADR-101](#adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e), [ADR-134](#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend). **Origem:** Sprint A10 W0 — [archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §3.1-3.2](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md).

**Contexto:** F8.4 (2026-04-15) arquivou `config/goals.json` em `_archive/pre-f8-cutover-2026-04-15/`, mas [`pipeline_task.py::_materialize_adapter_configs`](../../backend/app/tasks/pipeline_task.py:56) passou a **materializar `goals.json` em runtime** dentro de `tenant_root/config/` para que E5/E5.N continuassem lendo via filesystem. O DB virou bridge, não fonte primária. ADR-077 §"Contrato de cutover" tem checkbox aberto há 7 meses sobre "100% dos campos lidos por E5/E5.N/E6". Esta sprint fecha.

A ADR-134 (Sprint A7.0) entregou `WorkspaceContext.config_overrides` lendo via `DBConfigStore` — padrão estabelecido. A pergunta é: estender o `ConfigStore` Protocol existente, ou criar `AnalyzerInputs` por stage? Plano canônico decidiu pelo primeiro: consistência com ADR-134, mínima cirurgia (vs. 11 sites em E5 + 2 em E5.N + 4 em domain services), `pipeline/**` continua sem importar `fastapi`/`celery`/`sqlalchemy` (boundary check ADR-101 R5 verde).

**Decisão:** Estender `ConfigStore` Protocol com método `get_goals_bundle(workspace_id) -> GoalsBundle`, onde `GoalsBundle` é `TypedDict` com chaves tipadas resolvidas. Shape proposto (refinado durante implementação na lane A10.6):

```python
class GoalsBundle(TypedDict):
    aporte: AporteGoalInputs
    if_meta: IFGoalInputs
    dolarizacao: DolarizacaoGoalInputs
    alocacao: AlocacaoGoalInputs
    seguros: SegurosGoalInputs            # A10.6 (Goal type SEGUROS, sem ADR — sub-1h)
    decisoes_top5: list[DecisionProjection]  # A10.5 (projeção do Decision aggregate)
    riscos_top: list[RiskProjection]      # A10.5 (projeção do Risk aggregate ADR-178)
```

`pipeline_adapter.build_goals_payload_sync` (existente) é refatorado para retornar `GoalsBundle` ao invés de dict legacy-shaped. `_materialize_adapter_configs` em `pipeline_task.py:56-99` é **deletado**. `_load_goals()` em `scripts/e5_analyze.py:166` e `scripts/e5n_narrativas.py:105` deletados. `goals.json` físico **nunca mais escrito em filesystem**.

`pipeline/**` continua sem importar `fastapi`/`celery`/`sqlalchemy` — bundle é dict tipado simples; adapter (em `backend/app/services/`) faz a montagem.

**Alternativas consideradas:**

1. **`AnalyzerInputs` por stage (DTO específico de cada analyzer)** — refatora 11 sites em E5 + 2 em E5.N + 4 em domain services. Alto custo, ganho marginal (DTOs locais são já value objects ADR-089). Rejeitada.
2. **Manter `_materialize_adapter_configs` mas escrever em diretório efêmero (tmpfs)** — não resolve débito ADR-077; apenas esconde; bridge perpetuado.
3. **Estender `ConfigStore.get_goals_bundle` (escolhida)** — consistência com ADR-134; mínima cirurgia; bundle tipado pode evoluir incrementalmente; boundary check verde.
4. **Endpoint REST `/v1/workspaces/{id}/goals_bundle` chamado por subprocess do pipeline** — adiciona round-trip HTTP em path crítico; complexidade desnecessária dado que pipeline já recebe `WorkspaceContext` via `StageConfig`.

**Trade-offs explícitos:**

- **Ganho:** débito ADR-077 fechado; `goals.json` físico nunca mais escrito; pipeline lê tipado; `GoalsBundle` evolui via PR (vs. dict shape implícito); tenancy correta (sem materialização de Andrade-Silva para outros workspaces).
- **Custo:** lane A10.6 estimada em 1.5d; goldens E5/E5.N podem regredir byte-a-byte se `pipeline_adapter.build_goals_payload_sync` mudar shape de algum subdict (mitigação: PR de paridade rigorosa; PR de reset dedicado se mudança for justificada).
- **Risco:** ordem de cleanup importa — A10.6 deve mergear depois de A10.1+A10.2+A10.3+A10.4 para o bundle não ter chaves residuais ou ausentes.

**Critério de aceite:**

- [ ] `ConfigStore` Protocol com método `get_goals_bundle(workspace_id) -> GoalsBundle` (TypedDict tipado).
- [ ] `pipeline_adapter.build_goals_payload_sync` retorna `GoalsBundle`, não dict legacy-shaped.
- [ ] `_materialize_adapter_configs` em `pipeline_task.py` **deletado**.
- [ ] `_load_goals()` em `scripts/e5_analyze.py` e `scripts/e5n_narrativas.py` **deletados**.
- [ ] `grep -r "goals.json" backend/app/tasks/` retorna zero hits.
- [ ] `dev/check_pipeline_boundaries.py` verde (pipeline não importa `fastapi`/`celery`/`sqlalchemy`).
- [ ] Novo gate empírico `tests/test_e5_pipeline_no_filesystem_goals.py` afirma que `e5_analyze` + `e5n_narrativas` rodam sem `goals.json` em filesystem.
- [ ] Goldens E5/E5.N verdes byte-a-byte em ciclo Andrade-Silva pós-cutover (PR de reset dedicado se diff justificado).
- [ ] ADR-077 §"Contrato de cutover" — checkbox "100% dos campos lidos pelo E5/E5.N/E6" marcado ✅ quando ADR-180 vira `Decidido`.
- [ ] **Cleanup de dados** — rows `Goal` órfãs (`type ∉ VALID_GOAL_TYPES`, ex.: `PLANNING_CONTEXT`) com `effective_to IS NULL` em workspaces seedados pré-A10.6 fechadas via migration `d2c3d4e5f6a7_adr180_close_orphan_goal_types` (follow-up de [commit 0053d15](https://github.com/davidrobert/mathoms/commit/0053d15)). Filtros defensivos em `premissas_snapshot.build_premissas_snapshot_sync` e `MetasVigentesCard` mitigam até a migration rodar em prod.

**Plano de implementação:** [docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §3.1-3.2](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) (lane A10.6).
