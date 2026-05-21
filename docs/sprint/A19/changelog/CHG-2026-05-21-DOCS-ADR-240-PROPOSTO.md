---
id: CHG-2026-05-21-DOCS-ADR-240-PROPOSTO
type: changelog-entry
date: "2026-05-21"
sprint: A19
lane: "[[A19.l1]]"
adrs: ["[[ADR-240]]"]
summary: |
  docs(adr-240): Proposto — Card S_PROTECAO no relatório como 4º pilar AUVP
  (Proteção Patrimonial). Posicionado entre S2 (Reserva) e S4 (Patrimônio).
  Sprint A19 reservada com 1 lane (depende de A18 inteira em main).
tags:
  - type/changelog-entry
  - sprint/a19
  - status/proposto
  - area/report
  - area/methodology
  - methodology/auvp
  - methodology/cerbasi
---

# docs(adr-240): Proposto — Card S_PROTECAO 4º pilar AUVP (Sprint A19)

PR docs-only complementar a [[ADR-239]] (Sprint A18). Registra [[ADR-240]] como `Proposto` e reserva Sprint A19 com 1 lane (card S_PROTECAO no relatório). Nenhum código de runtime ainda.

## Origem

Co-design `financial-planner` (2026-05-21) consolidou KPIs, faixas de sinal, copy CRC, gating heurístico para seguros ausentes, e posicionamento AUVP-coerente. Owner comprometeu A19 explicitamente como next-sprint após A18.

AUVP tem 4 pilares formais (Reserva → Proteção → Patrimônio → Renda). Mathoms hoje cobre 3 e omite o segundo — **incoerência metodológica** que A19 corrige.

## Decisões canônicas

| # | Tema | Decisão |
|---|---|---|
| D1 | Posicionamento | Card S_PROTECAO entre S2 (Reserva) e S4 (Patrimônio), seguindo ordem AUVP |
| D2 | KPIs V1 | G (prêmio total hero), B (% renda em prêmios), F (seguros ausentes qualitativo), C (gap cobertura por bem auto-V1) |
| D3 | Faixas + copy | Faixas Cerbasi (1-5%); copy CRC ("considere", "vale avaliar"); zero verbo prescritivo |
| D4 | Subgrupos | Card único com 3 subgrupos visuais: Bens / Pessoas (V2) / PJ (V2) |
| D5 | Status vigência | vigente / vencendo em 30d / vencida — sinal visual por linha |
| D6 | Multi-corretor | Neutro com nota (não warning V1); detecção mesma-seguradora-multi-corretor V2 |
| D7 | Cross-link S8 | Nota textual: previdência tem componente de proteção para beneficiários |
| D8 | Schema E5 | Bloco `protecao_patrimonial` em `analise_financeira`; validação hook [[ADR-212]] |
| D9 | Fórmulas | Registrar em `FORMULAS.md` antes de implementar (gate G2) |

## KPIs descartados V1 (V2 condicional)

- **A — % patrimônio coberto** — denominador problemático (investimentos não são "seguráveis")
- **D — Multi-corretor warning** — vira nota neutra; flag real é "mesma seguradora multi-corretor" (perde bônus)
- **E — Bônus em risco** — exige modelar histórico de renovação inter-seguradora

## O que entra neste PR

- [docs/adr/240-card-protecao-patrimonial-pilar-auvp.md](../../../adr/240-card-protecao-patrimonial-pilar-auvp.md) — ADR canônica
- `docs/sprint/A19/_README.md` — MOC da sprint com 1 lane
- `docs/sprint/A19/lanes/A19-l1-card-protecao.md` — lane única
- `docs/sprint/A19/tracks/a19-l1-card-protecao.md` — track operacional completo (4 fases P1-P4)
- Este changelog entry

## Próximo passo

Lane [[A19.l1]] (`open`) pickup-ready **somente após Sprint A18 inteira em `main`** (L1 CRLV + L2 apólice + L3 FIPE). Sem dado de apólice ingerida, card não tem o que renderizar.
