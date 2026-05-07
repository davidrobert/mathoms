# Sprint A6 — Ondas paralelas (mapa de dependências)

> Itens dentro da mesma onda rodam em paralelo (agentes disjuntos, branches distintas, zero overlap de arquivos). Onda N só começa quando Onda N-1 convergir em `origin/main`.

```
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 1 — estrutura (2 lanes independentes)                           ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Lane A1: A6g.2 pipeline sweep   (agent/a6g2-pipeline-style/*)       ║
║           └─ 1ª rodada defensiva (Tier 1: e_reset::main,              ║
║             pdf_generator, e0_audit; Tier 2 opc.); Tier 3 em A6g.2b  ║
║  Lane A2: A6g.4 frontend sweep   ✅ fechada 2026-04-22              ║
║           └─ rodadas 1+2+3 mergeadas; T1/T2/T4/T5 zerados em         ║
║             frontend/src/; 6 páginas >500 l decompostas.             ║
║                                                                       ║
║  [A6e Task]  ✅ entregue 2026-04-21 (A6e.7) — 3 sub-agregados        ║
║  [A6e Goal]  ✅ entregue 2026-04-21                                   ║
║  [A6g.1 audit] ✅ entregue — baseline em docs/archive/audits/                ║
║  [A6f.1 pipeline-service] NÃO entra aqui — fica na Onda 2.           ║
║  [A6g.3 backend sweep] prefere pós-A6e.4 (routers finos). Onda 2.    ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │
                              ▼  (após Onda 1 convergir)
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 2 — paralelizável (4 lanes, A6e transversais + infra)           ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Lane B1: A6e.3 + A6e.3b ✅ 2026-04-22 + A6e.4 — use cases + routers ║
║           └─ Transversal: requer todos slices Onda 1 mergeados        ║
║           └─ A6e.3b fechou 3 agregados restantes (ConfigBlob+Task+Doc)║
║  Lane B2: A6e.5 /api/v1/ prefix  ✅ 2026-04-22 (ADR-108)             ║
║  Lane B3: A6f.1 pipeline-service ✅ 2026-04-21 (ADR-112)             ║
║  (A6g.5 tests sweep ✅ 2026-04-21 — fora da Onda)                    ║
║                                                                       ║
║  A6e.events (domain events) prefere vir depois de B1 (use cases).    ║
║  A6g.3 (backend sweep) rodará pós-A6e.4 (B1) — mesclar em Onda 3.    ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │
                              ▼  (após A6e.3/.4/.5 fechados + A6f.1 merged)
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 3 — F7 produção + LGPD (paralelizável dentro)                   ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Lane C1: F7A Docker + Deploy + HTTPS      (infra)                   ║
║  Lane C2: F7B Security + LGPD              (segurança)                ║
║  Lane C3: F7C CI/CD + Observability        (DevOps)                   ║
║  Lane C4: F7E Legal + termos               (jurídico, sem código)    ║
║  Lane C5: A6g.3 backend sweep (pós-A6e.4) + A6g.6 enforcement +      ║
║           A6g.7 Go prep (pós-A6f.1)                                   ║
║  Lane C6: F7F-Local (IA-0) — UI web localhost (principal) +          ║
║           camada de serviço; CLI vira atalho secundário/futuro;      ║
║           sem OAuth; INDEPENDENTE de F7A/B/C (roda em dev/staging)   ║
║           Depois de F7F-Local shell: F7F-Analyst (role analyst,      ║
║           triage/deep-dive/overview/feedback — Perini/Cerbasi/AUVP)  ║
║                                                                       ║
║  F7A precede F7B (HTTPS antes de hardening). F7D (monitoring) e      ║
║  F7F-Remote (console hospedado) vêm após F7A+B+C estabilizarem.      ║
║  F7F-Local NÃO espera Onda 3 convergir.                               ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 4 — dogfood + GA                                                 ║
╠═══════════════════════════════════════════════════════════════════════╣
║  F7D monitoring + dogfood (2 semanas com dados reais)                ║
║  F7F-Remote console interno em ops.mathoms.ai                        ║
║          (OAuth staff, RBAC, /api/internal/*, dashboard 7E.7)        ║
║  GA release                                                           ║
╚═══════════════════════════════════════════════════════════════════════╝
```

## Heurística por perfil de sessão

| Situação | Preferência (se livre) |
| --- | --- |
| Sessão curta, refactor cirúrgico em Python | A6g.2 pipeline → A6e.5 /v1 prefix |
| Sessão curta, familiar com TS/React | A6g.4 frontend |
| Sessão longa (≥3h), greenfield infra | A6g.7 Go prep ou F7A Docker (Onda 3) |
| Sessão longa, foco em backend DDD | A6e.4 ou A6e.events |
| Sessão curta, foco em ops/CS/LGPD | F7F-Local (C6, Onda 3 — independente) |
| F7F-Local shell pronto, quer análise de saúde | F7F-Analyst (C6, Onda 3+) |

## Regras de coordenação (válidas em todas as ondas)

- Uma lane = uma branch `agent/<slug>/<timestamp>`. Nunca 2 agentes na mesma lane (pickup check em CLAUDE.md §Antes de pegar uma task).
- `git fetch origin` a cada ~30min em sessão longa; rebase incremental.
- Hotspots (`CLAUDE.md`, `docs/BACKLOG.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`) — anunciar antes, commit atômico ≤5min.
