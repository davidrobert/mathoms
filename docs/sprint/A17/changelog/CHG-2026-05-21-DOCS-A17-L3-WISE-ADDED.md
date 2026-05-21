---
id: CHG-2026-05-21-DOCS-A17-L3-WISE-ADDED
type: changelog-entry
date: "2026-05-21"
sprint: A17
lane: "[[A17.l3]]"
adrs: ["[[ADR-238]]"]
summary: |
  docs(a17-l3): adiciona Wise (conta multi-moeda no exterior) ao escopo
  da onda L3 financeiro PF — schema modela campo `moeda` + pegadinhas
  fiscais específicas (código RFB 62, PTAX 31/12, variação cambial =
  GCAP, juros = carnê-leão, CBE BACEN > USD 1MM).
tags:
  - type/changelog-entry
  - sprint/a17
  - status/proposto
  - area/pipeline
  - area/methodology
  - methodology/auvp
---

# docs(a17-l3): adiciona Wise ao escopo (multi-moeda, conta exterior)

PR docs-only complementar a [#396](https://github.com/davidrobert/mathoms/pull/396) (que reservou Sprint A17 com 14 PDFs do batch). Owner anexou 15º informe (Wise 2025) na sessão de revisão pós-merge — Wise é caso de `financeiro_pf` com nuance forte (conta multi-moeda no exterior).

## O que muda

- **[[ADR-238]] §Contexto** — batch atualizado de 14 → 15 PDFs (Wise incluído na lista).
- **[[ADR-238]] §D1 tabela** — `financeiro_pf` cobre agora também Wise; schema modela campo `moeda` (BRL default, USD/EUR/GBP).
- **[[ADR-238]] §D1 nota explicativa** — adicionadas 4 pegadinhas fiscais de conta no exterior:
  - Código RFB **62** (distinto de 41 doméstico)
  - Conversão PTAX 31/12 via [[ADR-135]] `market_rates`
  - Variação cambial = ganho de capital ME (DARF GCAP 15%) — **NÃO** isento
  - Juros em ME = carnê-leão (código 13)
  - CBE BACEN > USD 1MM = warning em E5 (fora do escopo Mathoms)
- **[[A17.l3]] lane** — título + objetivo + PDFs do batch (7 → 8) + critério de aceite (8+ PDFs) + nova seção "Pegadinhas Wise / conta no exterior".
- **[[TRACK-a17-l3-financeiro-pf]]** — briefing expandido, decisões fechadas incluem pegadinhas Wise, plano de fases ganha P5 (validações fiscais ME).
- **[`docs/sprint/A17/_README.md`](../_README.md)** — diagnóstico (14 → 15 PDFs), descrição L3 cita Wise explicitamente.

## Por que não criar tipo novo

Wise é PF (mesmo titular físico), com layout estruturalmente similar aos 4 quadros RFB. Criar `financeiro_exterior` separado fragmentaria sem ganho — a complexidade está em campo `moeda` + 5 regras fiscais documentadas, não em estrutura de schema diferente. Decisão alinhada a [[ADR-238]] D1: "não vale fragmentar por instituição quando layout é o mesmo".

## Impacto em outras lanes

- L1 (previdência), L2 (PJ), L4 (proventos) — sem mudança.
- ADR-238 status permanece `Proposto`.
- Sprint A17 status permanece `candidate`.

## Próximo passo

Quando L3 for puxada, agente implementa schema com `moeda` desde o P1; regras fiscais ME entram em P5 do track.
