---
id: CHG-2026-05-21-DOCS-ADR-238-PROPOSTO
type: changelog-entry
date: "2026-05-21"
sprint: A17
lane: "[[A17.l1]]"
adrs: ["[[ADR-238]]"]
summary: |
  docs(adr-238): Proposto — Ingestão de Informes de Rendimentos anuais
  avulsos (PGBL/VGBL, financeiro PF/PJ, proventos) como fonte fiscal
  primária paralela ao E1.6. Sprint A17 reservada com 4 lanes (L1-L4).
tags:
  - type/changelog-entry
  - sprint/a17
  - status/proposto
  - area/pipeline
  - area/methodology
  - area/persistence
  - area/report
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
---

# docs(adr-238): Proposto — Informes anuais avulsos (Sprint A17 reservada)

PR docs-only que registra [[ADR-238]] como `Proposto` e reserva a Sprint A17 com 4 lanes (L1-L4) para implementação. Nenhum código de runtime ainda.

## Origem

Sessão dogfood 2026-05-21 com 14 PDFs reais (BrasilPrev 2025, Itaú, Santander, Caixa, Nubank, PicPay, C6 PF, C6 PJ, Stone PJ, XP Investimentos, XP Proventos, Itaúsa, Einstein) revelou que ~12 caem em `.other` silencioso ou são mal-classificados como `irpf` (rota errada — `extract_irpf_full` espera declaração completa, não informe avulso).

Co-design `financial-planner` + `data-engineer` em paralelo consolidou 5 tipos canônicos, padrão arquitetural unificado, ordem de rampup, guardrails de produto. Decisões fechadas pelo owner em 4 perguntas (precedência fonte, granularidade stage, ordem ondas, encaixe sprint).

## O que entra neste PR

- `docs/adr/238-ingestao-informes-rendimentos-anuais-avulsos.md` — ADR canônica completa (D1-D9 + Gates + Implementação + Não-objetivos + Riscos + Alternativas).
- `docs/sprint/A17/_README.md` — MOC da sprint com 4 lanes.
- `docs/sprint/A17/lanes/A17.L{1,2,3,4}-*.md` — 4 lanes com critério de aceite por onda.
- `docs/sprint/A17/tracks/a17-l1-previdencia-privada.md` — track operacional completo (6 fases P1-P6).
- `docs/sprint/A17/tracks/a17-l{2,3,4}-*.md` — esqueletos `ready` (refináveis no pickup).
- Este changelog entry.

## Decisões canônicas

| # | Tema | Decisão |
|---|---|---|
| D1 | Tipos canônicos | 5: `previdencia_privada`, `financeiro_pj`, `financeiro_pf`, `proventos_acoes`, `aluguel_imobiliaria` |
| D2 | Schema | Base polimórfico com Discriminated Union; sub-schemas por tipo |
| D3 | Stage | Único `extract_informes_anuais` com `artifact_key` por kind |
| D4 | Precedência | Declaração entregue vence informe; warning de divergência em E5 efêmero |
| D5 | Analyzer | `FiscalAnalyzer` polimórfico sobre `FiscalSource`; `InformeQuery` service |
| D6 | Rampup | L1 previdência → L2 PJ (sinergia ADR-236) → L3 PF → L4 proventos |
| D7 | Catálogo | Migration Alembic: enum `category` +3 valores; coluna `tax_regime`; seeds |
| D8 | Guardrails | 3 lugares: footnote KPI, badge upload, system prompt E6 |
| D9 | Goldens | Sintéticos anonimizados; eval real fora do git |

## Próximo passo

Lane [[A17.l1]] (`open`) é pickup-ready após este PR mergear. PRs de implementação começam quando agente puxar L1.
