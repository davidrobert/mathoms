---
id: MOC-sprint-a18
type: moc
title: "Sprint A18 — Comprovantes de Bem (CRLV) + Apólices polimórficas + FIPE refresh (3 lanes coordenadas)"
aliases: ["A18", "Sprint A18"]
sprint_status: candidate
---

# Sprint A18 — Comprovantes de Bem + Apólices + FIPE

> **Status:** `in_progress` — L1 (CRLV-e) ✅ shipped 2026-05-22. [[ADR-239]] flippada `Decidido (Sprint A18 L1)`. L2 (apólice) e L3 (FIPE) `planned`.

## Resumo

Sprint dedicada a **3 lanes coordenadas que destravam ingestão de comprovantes de bem (CRLV-e), apólices de seguro polimórficas (combinada multi-bem como caso V1), e refresh assíncrono de valor de mercado via BrasilAPI**. Diagnóstico em sessão dogfood 2026-05-21 com 6 PDFs reais (3 CRLV + 3 apólices) revelou que todos caem em `.other` silencioso.

[[ADR-239]] decidiu **tabela canônica `vehicles` (não array livre)**, schema polimórfico `ApolicePayload` com Discriminated Union, FK opcional + reconciliação assíncrona, FIPE refresh via Celery (nunca síncrono), cascata LLM Haiku→Sonnet para apólice combinada, e histórico de apólices imutável temporal.

Sprint A19 ([[ADR-240]]) entrega o **card S_PROTECAO** no relatório como 4º pilar AUVP.

## Escopo

### L1 — Comprovantes de Bem (CRLV-e) — 4 PRs sequenciais (~5d eng)

Lane gateway: cria tabela `vehicles`, classifier de CRLV, parser LLM Haiku, stage `extract_comprovantes_bens`. Valida padrão arquitetural que L2 e L3 reutilizam.

Entrega: migration Alembic `vehicles` + extensão `market_rates.reference_month`; schema `crlv.schema.json`; classifier `crlv_eletronico` (regex DENATRAN/RENAVAM/CRLV); parser LLM Haiku; reconciliação assíncrona com IRPF G02; goldens sintéticos.

### L2 — Apólice de Seguro polimórfica (combinada V1) — 5 PRs (~6d eng)

Lane mais complexa: schema polimórfico com Discriminated Union (3 tipos de bem: veículo/imóvel/pessoa-placeholder-V2). Casca cascata Haiku→Sonnet quando detectar multi-bem. **Apólice combinada Porto Seguro (Toro + residência) é caso V1 obrigatório.**

Entrega: schema `apolice.schema.json` polimórfico + `Cobertura` também discriminated (material/rcfv/vida-V2/saúde-V2/acidentes-V2); classifier `apolice_seguro`; parser LLM Haiku→Sonnet cascade; reconciliação `veiculo_id`/`imovel_id` assíncrona; histórico imutável temporal; catálogo institucional expandido (`insurance_carrier`, `insurance_broker`).

### L3 — FIPE refresh assíncrono via BrasilAPI — 2 PRs (~3d eng)

Lane infraestrutural: estende `market_rates` com `series_type='fipe_vehicle'`, Celery task `refresh_fipe_value`, cron job anual. **Lookup nunca síncrono no upload.**

Entrega: extensão `market_rates`; `FipeLookupClient` (adapter [[ADR-097]]) com Protocol; Celery task; cron job Janeiro/<ano>; cache TTL 30 dias.

## Lanes

- [[A18.l1]] (`shipped` · 2026-05-22) — ✅ L1: CRLV-e. Padrão arquitetural validado em 6 PRs (#388, #391, #412, #414, #416, #418). [[ADR-239]] flippada `Decidido (Sprint A18 L1)`.
- [[A18.l2]] (`shipped` · 2026-05-22) — ✅ L2: Apólice polimórfica (auto/residencial/combinada V1; vida/saúde/acidentes-V2 placeholder). 5 PRs (#419, #420, #422, #424, #425). Discriminated Union 2 níveis + cascata LLM Haiku→Sonnet validados.
- [[A18.l3]] (`shipped` · 2026-05-22) — ✅ L3: FIPE refresh V1 (P1+P2). 2 PRs (#431, #433). Protocol + adapter BrasilAPI + Celery beat anual + cache reader. Débito: hook E5 enfileira refresh em miss (V2 condicional).

## Pré-requisitos

- [[ADR-239]] mergeada em `main` como `Proposto`.
- [[ADR-240]] mergeada em `main` como `Proposto` (Sprint A19, mas decisão tomada conjunta).
- A17 L1 ([[A17.l1]] previdência) idealmente entregue antes de L1 começar — valida padrão de classificação content-first para tipos novos. Não bloqueia tecnicamente.

## Bloqueios externos

Nenhum. BrasilAPI é open-source comunitário (sem auth/contract). FIPE oficial não publica API — toda integração no Brasil é via intermediários.

## Não-objetivos

- Vida / saúde / acidentes pessoais V1 — schema preparado (discriminated union antecipa), implementação V2.
- Empresarial PJ — V2 com [[ADR-236]] cascata fiscal PJ.
- Sinistro / indenização — placeholder no schema V1.
- CRLV histórico (>2 anos) — só último exercício V1.
- Capitalização embutida em seguro — V2 (rendimentos isentos + sorteios).
- Valor de reconstrução residencial — V2 ([[ADR-240]]).
- Franquia/LMI ratio — V2.

## Follow-ups potenciais (post-A18)

- **FU-1 · Vida / saúde / acidentes (V2)** — schema já preparado em [[ADR-239]] D2; quando ICP materializar demanda, lane curta ativa cobertura V2.
- **FU-2 · Empresarial PJ** — co-design `financial-planner` + [[ADR-236]] integração BusinessProfile.
- **FU-3 · Bônus em risco ao renovar** — modelagem de histórico de renovação inter-seguradora.
- **FU-4 · Valor de reconstrução residencial via CUB regional** — substitui LMI nominal incêndio em S_PROTECAO ([[ADR-240]] KPI C residencial).
- **FU-5 · Sinistro / indenização recebida** — integração com [[ADR-238]] (IR sobre indenização).
- **FU-6 · Eval de acurácia LLM** com dataset privado fora do git (mesmo padrão [[ADR-238]] D9).
