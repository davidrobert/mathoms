# Sprint A7 — Ondas paralelas (mapa de dependências)

> Bloqueio duro: Onda 2 (A7.1, A7.2a, A7.2b) só destrava após A7.0 mergeada em `main`. A7.3 só após A7.1 mergeada. A7.5 só após A7.1 + A7.2a + A7.2b + A7.3 + A7.4 mergeadas. A7.4 (docs metodologia) NÃO depende de nada — pode rodar em qualquer momento.

```
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 1 — Fundação (1 lane, BLOQUEANTE — sem paralelismo)              ║
╠═══════════════════════════════════════════════════════════════════════╣
║  A7.0  ConfigStore protocol + adapters                                 ║
║   └─ pipeline/ports/config_store.py + 2 adapters                      ║
║   └─ Aceita: zero call-sites migrados; smoke verde                    ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 2 — Cutover paralelizável (até 4 agentes simultâneos)             ║
╠═══════════════════════════════════════════════════════════════════════╣
║  A7.1   Cutover materialize_config → ConfigStore                       ║
║          (pipeline/, scripts/, config_materializer.py)                 ║
║  A7.2a  Decision aggregate + migrator + tela Plano de Ação             ║
║          (backend/app/{models,application/decisions,api},              ║
║           frontend/src/.../sections/PlanoDeAcao)                       ║
║  A7.2b  fiscal_parameters + market_rates tabelas globais               ║
║          (backend/app/models, pipeline/domain/services/...)            ║
║  A7.4   docs/methodology/ — 4 .md movidos (paralelo livre)             ║
║                                                                        ║
║  Hotspot único cross-lane: BACKLOG.md, CHANGELOG.md, CLAUDE.md         ║
║   → protocolo §Hotspots de documentação do CLAUDE.md                  ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │ A7.1 mergeada
                              ▼
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 3 — Catalog/Override (1 lane, depende de A7.1)                    ║
╠═══════════════════════════════════════════════════════════════════════╣
║  A7.3  category_templates + workspace_category_overrides + resolver    ║
║         institution_catalog global (sem override por workspace)        ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │ todas mergeadas
                              ▼
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 4 — Cleanup final (1 lane, BLOQUEANTE)                            ║
╠═══════════════════════════════════════════════════════════════════════╣
║  A7.5  git rm -r config/                                               ║
║         FileConfigStore + materialize_config removidos                 ║
║         dev/check_forbidden_paths.py bloqueia config/*                 ║
╚═══════════════════════════════════════════════════════════════════════╝
```

## Onda 2.5 — Rules-as-code (paralelo a A7.2a/A7.3)

A lane **A7.6** (rules-as-code) entrou fora do diagrama original como onda 2.5: depende apenas de A7.4 ✅ + ADR-143/145/146/147 (G1). Roda em paralelo com A7.2a e A7.3 sem conflito de hotspot.

## Coordenação multi-agente A7

- **Pickup checks idênticos** ao Sprint A6: `git worktree list` + `git for-each-ref refs/remotes/origin/agent/`. Lane com prefix `a7-*` em uso = pegue outra.
- **Cross-lane hotspot esperado em Onda 2:** `pipeline/stage_config.py` (A7.1 + A7.2b ambos tocam). Solução: A7.2b adiciona apenas os métodos `get_fiscal_for_period`/`get_market_rate` no Protocol já criado em A7.0; ambos rebase em `main` antes de push.
- **CTO supervision** segue protocolo CONFIG_CUTOVER_PLAN.md §6. Agente que terminou anuncia "branch pronta para review" em CHANGELOG `[Unreleased]` + atualiza status para 🚧 G3 e **para de mexer** até receber APROVADO/BLOQUEADO.
