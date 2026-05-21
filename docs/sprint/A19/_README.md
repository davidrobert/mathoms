---
id: MOC-sprint-a19
type: moc
title: "Sprint A19 — Card S_PROTECAO (4º pilar AUVP Proteção Patrimonial)"
aliases: ["A19", "Sprint A19"]
sprint_status: candidate
---

# Sprint A19 — Card S_PROTECAO no relatório

> **Status:** `candidate` — sprint reservada para começar quando A18 (CRLV + Apólice + FIPE) fechar. ADR canônica [[ADR-240]] mergeada como `Proposto`; PR de implementação começa quando L1 for puxada.

## Resumo

Sprint dedicada ao **card S_PROTECAO no relatório nativo React como 4º pilar AUVP (Proteção Patrimonial)**, posicionado **entre S2 (Reserva) e S4 (Patrimônio)** seguindo ordem AUVP. 4 KPIs V1, 3 subgrupos visuais, linguagem CRC, gap qualitativo de seguros ausentes.

Pré-requisito: Sprint A18 ([[ADR-239]]) entrega ingestão de comprovantes de bem + apólices + FIPE refresh. Sem isso, card S_PROTECAO não tem dado.

[[ADR-240]] decidiu **posicionamento AUVP-coerente**, **4 KPIs canônicos** (G prêmio total hero, B % renda em prêmios ancorado Cerbasi, F seguros ausentes qualitativo, C gap de cobertura por bem auto-V1), **card único com 3 subgrupos visuais** (Bens/Pessoas/PJ), **status de vigência por apólice**, e **cross-link com S8 Previdência**.

## Escopo

### L1 — Card S_PROTECAO no relatório React — 4 PRs sequenciais (~6-8d eng)

Lane única que entrega:

- **P1** — Schema `protecao_patrimonial.schema.json` + bloco `protecao_patrimonial` no E5 `analise_financeira`. Fórmulas registradas em `FORMULAS.md`. Hook validação [[ADR-212]].
- **P2** — `ProtecaoAnalyzer` em `pipeline/domain/services/protecao_analyzer.py` calcula 4 KPIs (G, B, F, C). Goldens determinísticos.
- **P3** — Codegen `report_layout.yaml` ([[ADR-076]]) com seção S_PROTECAO posicionada entre S2 e S4. Reposicionamento de cards existentes ordem AUVP.
- **P4** — Componente React `<S_ProtecaoSection/>` + 3 subgrupos (Bens/Pessoas/PJ) + status vigência por apólice + multi-corretor metadata neutra + cross-link S8. UI review CRC.

## Lanes

- [[A19.l1]] (`open`) — L1: Card S_PROTECAO completo. Lane única na sprint.

## Pré-requisitos

- [[ADR-240]] mergeada em `main` como `Proposto`.
- **Sprint A18 inteira entregue** (L1 CRLV + L2 apólice + L3 FIPE em `main`).
- Goldens E2E da A18 verde — sem dado de apólice ingerida, card S_PROTECAO não tem o que renderizar.

## Bloqueios externos

Nenhum. Tudo é UI/produto interno ao Mathoms.

## Não-objetivos

- Vida / saúde / acidentes pessoais funcional V1 — placeholder com copy "Não há apólices identificadas neste subgrupo".
- Empresarial PJ — V2.
- Valor de reconstrução residencial — V2.
- Franquia / LMI ratio — V2.
- Bônus em risco — V2.
- Sinistro / indenização — V2.
- Mesma seguradora multi-corretor warning — V2.
- Recomendação de produto específico (zero tolerance — viola CRC).

## Follow-ups potenciais (post-A19)

- **FU-1 · KPI A (% patrimônio coberto)** — reavaliar com denominador filtrado (só patrimônio segurável).
- **FU-2 · KPI E (bônus em risco)** — quando histórico de renovação modelado.
- **FU-3 · Subgrupo Pessoas (Vida/Saúde/AP)** funcional — schema preparado, ativar UI.
- **FU-4 · Subgrupo PJ** — co-design [[ADR-236]] BusinessProfile.
- **FU-5 · Card S8 Previdência absorve componente de proteção** — cross-link bidirecional formalizado.
