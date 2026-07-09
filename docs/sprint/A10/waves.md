# Sprint A10 — Ondas paralelas (mapa de dependências)

> Bloqueio duro: Onda 1 só destrava após A10.0 mergeada. Onda 2 só após A10.1 + A10.2 mergeadas. Onda 3 só após A10.3 + A10.4 mergeadas. A10.8 depende de TODAS.

```
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 0 — ADRs Propostos (1 lane, BLOQUEANTE)                       ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.0  Batch ADR-177..181 em status "Proposto"                    ║
║         Reusa esqueleto + ToC + gates dev/check_adr_*               ║
╚════════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 1 — Cleanup paralelo (2 lanes simultâneas)                    ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.1  Dead-data + ADR-168 narrativas órfãs                       ║
║          (chaves H: fase_f1f2, mariana_eua, nclex_*,               ║
║           investimentos_blocos, aportes_destinos_detalhados;       ║
║           4 narradores E5.N que consomem custo_fase_f1f2)          ║
║  A10.2  Rules-as-code (ADR-177)                                    ║
║          (7 chaves U/M/O → constantes em módulos + frontend;       ║
║           inclui aporte_match_keywords vivo no backend)            ║
║                                                                    ║
║  Hotspot: backend/app/services/task_progress_service.py            ║
║   (A10.2 migra dashboard.aporte_match_keywords → constante)        ║
╚════════════════════════════════════════════════════════════════════╝
                              │ A10.1 + A10.2 mergeadas
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 2 — Aggregate work (3 lanes simultâneas)                      ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.3  Decision extension (ADR-179)                               ║
║          Alembic + DTO + UI form: impact_1y, impact_10y,           ║
║          horizon, priority                                          ║
║  A10.4  Risk aggregate (ADR-178)                                   ║
║          Model + repo + 6 use cases + UI lista + seed Cerbasi      ║
║          5 riscos universais (morte/invalidez/doença/desemprego/    ║
║          longevidade)                                              ║
║  A10.7  Seed refactor + Workspace.business_profile_json            ║
║          seed_goals_workspace.py (sem família hardcode)            ║
║          tributario → JSON em Workspace                            ║
║                                                                    ║
║  Hotspot: backend/alembic/versions/ — 3 migrations simultâneas     ║
║   resolução: merge migration final ou serializar A10.3→A10.4→A10.7 ║
╚════════════════════════════════════════════════════════════════════╝
                              │ A10.3 + A10.4 + A10.7 mergeadas
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 3 — Pipeline cutover (2 lanes simultâneas)                    ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.5  Top5/Bubble projections                                    ║
║          charts_narrator.py:382 lê Decision/Risk aggregates        ║
║          remove decisoes_prioritarias/top5_decisoes/riscos_*       ║
║          do PLANNING_CONTEXT bag                                   ║
║  A10.6  StageConfig bundle (ADR-180)                               ║
║          GoalsBundle TypedDict + adapter retorno tipado            ║
║          E5/E5.N/conjuge_analyzer leem do bundle                   ║
║          _materialize_adapter_configs DELETADO                     ║
║          _load_goals() DELETADO                                    ║
║                                                                    ║
║  Cross-cutting goldens E5/E5.N — paridade rigorosa byte-a-byte;    ║
║  PR de reset goldens dedicado em A10.5 se Decision aggregate       ║
║  produzir ordenação distinta da bag legada                         ║
╚════════════════════════════════════════════════════════════════════╝
                              │ A10.5 + A10.6 mergeadas
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 4 — Cutover final (1 lane, BLOQUEANTE)                        ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.8  config/goals.json em check_forbidden_paths.py              ║
║          _archive/.../goals.json deletado                          ║
║          ADR-077 checkbox marcado; ADR-180 → Decidido              ║
║          PLANNING_CONTEXT goal type DELETADO de VALID_GOAL_TYPES   ║
║          goals.json.MIGRATED.md substitui o arquivo arquivado      ║
╚════════════════════════════════════════════════════════════════════╝
```

## Coordenação multi-agente A10

- **Pickup checks idênticos** ao Sprint A6/A7: `git worktree list` + `git for-each-ref refs/remotes/origin/agent/`. Lane com prefix `a10-*` em uso = pegue outra.
- **Cross-lane hotspots esperados:**
  - **Onda 1**: `backend/app/scripts/seed_goals_full_andrade_silva.py` (A10.1 deleta chaves H; A10.2 migra rules. Sequenciar: A10.1 mergeia primeiro, A10.2 rebase).
  - **Onda 2**: 3 migrations Alembic simultâneas (A10.3 + A10.4 + A10.7). Solução: merge migration explícita no fim, ou serializar a ordem dentro da onda.
  - **Onda 3**: `pipeline/domain/services/narrativas/charts_narrator.py` (A10.5 reescreve narrador `top5_decisoes`; A10.6 troca leitura de goals_cfg → bundle). Sequenciar A10.5 → A10.6 dentro da onda 3.
- **CTO supervision** segue padrão A7 (4 gates G1/G2/G3/G4).
