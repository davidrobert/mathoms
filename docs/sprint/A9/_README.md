---
id: MOC-sprint-a9
type: moc
title: Sprint A9 — Multi-front improvements
aliases: ["A9", "Sprint A9"]
sprint_status: done
---

# Sprint A9 — Multi-front improvements (2026-05-05)

> **Status:** done — 11 frentes paralelas fechadas em 1 dia (PRs #46–#56 + #60).

## Resumo

Estabilizar qualidade cross-cutting (stage names, calculators, testes E2E, DB legacy tables, content_classifier monolith) enquanto avança UX (Onda 9 design system mobile), simulação estocástica de IF (N3 Monte Carlo), compat migratória (F9.3 Alembic) e LGPD self-service (portabilidade + eliminação).

**Avanço LGPD:** advance delivery LGPD Art. 18 V+VI (Bloco 0.6 P2/P3) — adiantou parte de F7B.7+7B.8.

**Notas de coordenação:**
- B2 absorvido em B1 (dispatcher stub test rename era trivial).
- B4 (visual regression S1) foi parte do trabalho de baseline visual da Onda 9 — rastreado em entradas existentes do BACKLOG.
- N3 Monte Carlo não tem ADR formal ainda — candidato a ADR-165 na próxima sessão de review financeiro.
- F9.4 destravada após A1 (F9.3) mergear.

## Lanes

Ver [lanes.md](lanes.md) (tabela histórica) ou [`lanes/`](lanes/).

## Waves

> Sprint sem ondas paralelas formais — todas as 11 frentes correram em paralelo no mesmo dia (2026-05-05). Ver [waves.md](waves.md) para registro mínimo.
