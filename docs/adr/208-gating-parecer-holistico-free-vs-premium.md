---
id: ADR-208
type: adr
title: "Gating freemium do parecer holístico — Opção B+ (diagnóstico amostra free, plano completo premium)"
status: Decidido
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
relates_to:
  - "[[ADR-153]]"
  - "[[ADR-199]]"
  - "[[ADR-202]]"
  - "[[ADR-204]]"
  - "[[ADR-207]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 208"
  - "Gating freemium parecer"
  - "Premium tier parecer"
tags:
  - area/llm
  - area/business
  - area/frontend
  - phase/a11
  - status/proposto
  - type/adr
---

# ADR-208 — Gating freemium do parecer holístico — Opção B+ (diagnóstico amostra free, plano completo premium)

**Status:** Decidido (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

## Contexto

- Parecer holístico ([[ADR-199]]) é a feature mais cara em LLM cost (~$0.15-$0.24/parecer V1, com cap de circuit breaker em $1 worst-case) e a mais densa em valor percebido — converte "Mathoms gera relatório" em "Mathoms tem um planejador digital". Sem gating, todos os clientes free recebem feature de custo recorrente: insustentável.
- Concorrente direto identificado pelo `gtm-strategist`: **Pierre Finance** (CloudWalk) lança "AI advisor" genérico em ciclos rápidos (6 semanas). Resposta competitiva exige depth-of-service auditável (não velocity matching).
- Plano canônico D-0.4: `gtm-strategist` decidiu **Opção B+**: free recebe diagnóstico + 3 pontos fortes + 1 risco-amostra (severidade máxima) com teaser "+14 riscos no Premium". Premium destrava tudo. Pricing R$ 79-149/mês BYOK (âncora abaixo de 1 sessão CFP). Gate de revisão 60d pós-beta: conversão free→Premium ≥ 8%, NRR ≥ 110%.
- Decisão `gtm-strategist` é o input; esta ADR formaliza arquitetura para enforcement, instrumentação e gate de revisão.

## Alternativas consideradas

1. **Sem gating — todos recebem parecer completo.** Pró: simples; máximo valor percebido por usuário. Contra: custo LLM insustentável; nenhuma diferenciação de valor entre free e premium; difícil monetizar feature mais cara. **Rejeitada** — produto não-viável economicamente.
2. **Opção A — paywall total** (free não recebe parecer). Pró: economia de LLM. Contra: free não vê valor da feature → conversão zero; quebra mental model "produto funcional grátis com upgrade". **Rejeitada.**
3. **Opção B — free recebe parecer truncado** (versão menor mas completa estruturalmente). Pró: visibilidade do valor. Contra: "menor mas completo" não cria desejo claro de upgrade; pode parecer "produto pago é só mais texto" — depreciar percepção. **Rejeitada parcialmente.**
4. **Opção B+ — free recebe diagnóstico + amostra explícita com teaser.** Pró: visibilidade clara de valor (cliente vê "isto é o que tenho"; vê "isto é o que perco"); teaser direto cria urgência de upgrade ("+14 riscos no Premium"); diferenciação evidente. Contra: copy do teaser precisa cuidado (não cheirar a manipulação predatória). **Aceita** — recomendação `gtm-strategist`.
5. **Opção C — free recebe parecer completo mas só 1× por mês; premium ilimitado.** Pró: economia + visibilidade. Contra: cliente confunde "1× por mês" como restrição arbitrária; rate limit é UX ruim para feature de valor. **Rejeitada.**

## Decisão

Adotar **Opção B+** com 4 mudanças mínimas: (D1) filtragem backend antes de serializar; (D2) feature flag no aggregate; (D3) instrumentação de funil; (D4) gate de revisão 60d.

### D1. Backend filtra payload por `workspace.tier` ANTES de serializar

**Crítico:** filtragem **não pode** ser no frontend (cliente "vê e esconde com CSS"). Vazamento de payload completo via DevTools/network = vazamento de valor pago.

- Endpoint `GET /workspaces/{id}/reports/{run_id}/planner-review` lê `workspace.tier` (existing column).
- Repository tem método `to_tier_filtered_dto(tier: Literal["free", "premium"])` que retorna shape diferente:

**Free DTO:**
```jsonc
{
  "tier_at_generation": "free",
  "diagnostico": "Texto curto orientativo",
  "pontos_fortes": [ /* 3 items */ ],
  "riscos_sample": [ /* 1 item — severidade máxima */ ],
  "teaser": {
    "riscos_gated_count": 11,        // 12 totais - 1 mostrado
    "sugestoes_gated_count": 15,
    "metricas_gated_count": 10,
    "cta_text": "Ative o Premium para acessar 11 outros riscos e 15 movimentos sugeridos",
    "cta_link": "/upgrade"
  },
  "items_shown_count": 4,            // 1 diagnóstico + 3 pontos + 1 risco-amostra (para telemetria, no payload)
  "items_gated_count": 36            // soma de tudo escondido
}
```

**Premium DTO:**
```jsonc
{
  "tier_at_generation": "premium",
  "diagnostico": "...",
  "pontos_fortes": [ /* até 5 */ ],
  "riscos": [ /* até 12 */ ],
  "sugestoes_execucao": [ /* até 5 */ ],
  "sugestoes_tatico": [ /* até 5 */ ],
  "sugestoes_estrategico": [ /* até 5 */ ],
  "metricas": [ /* até 10 */ ],
  "notas_metodologicas": [ /* ... */ ],
  "items_shown_count": <total>,
  "items_gated_count": 0
}
```

### D2. Feature flag no aggregate (`tier_at_generation`)

- Aggregate `PlannerReview` ([[ADR-199]]) persiste `tier_at_generation` (`free | premium`) no `_meta` do artifact.
- Stage roda para todos workspaces (free e premium) — produzir só "amostra" não economiza LLM cost (LLM precisa gerar tudo para o tier premium do mesmo workspace virar trivial upgrade depois). Stage produz output completo; filtragem é só no path de serialização.
- **Exceção:** workspace `tier == "free"` desabilita parecer **se** `MATHOMS_PARECER_FREE_GENERATION=false` (env). Default no início do beta: `true` (gera para todos free também — máxima visibilidade do valor). Após gate 60d: revisar se custo justifica desligar para free e dar parecer só "on upgrade".

### D3. Instrumentação de funil

3 campos novos persistidos:
- `tier_at_generation` (snapshot do tier no momento da geração).
- `items_shown_count` (quantos items o usuário viu).
- `items_gated_count` (quantos items ficaram trancados).

Métricas adicionais:
- `cta_upgrade_click_total{tier_at_generation="free"}` — Prometheus counter.
- `upgrade_conversion_after_planner_view` — % usuários free que clicaram "Ativar Premium" dentro de 7 dias após `planner_review_section_open`.
- `recovery_after_upgrade` — % usuários novos premium que reabriram parecer dentro de 24h pós-upgrade.

### D4. Pricing — faixa R$ 79-149/mês BYOK

- **R$ 79/mês** — tier intro (single workspace).
- **R$ 149/mês** — tier full (3 workspaces + features avançadas — escopo de outras ADRs futuras).
- **BYOK (Bring Your Own Key):** cliente fornece API key Anthropic/OpenAI; Mathoms abate cost de LLM da margem. Pricing assume BYOK como path principal; non-BYOK seria +50% (cubrir LLM cost).
- **Âncora:** abaixo de 1 sessão CFP (R$ 300-500/sessão). Mensagem implícita: "Mathoms é uma sessão CFP estendida pelo mês todo, sob custo."
- **Pricing concreto não é decisão desta ADR** — `gtm-strategist` finaliza em ADR separada antes do GA, com input de pesquisa de pricing sensitivity.

### D5. Gate de revisão 60 dias pós-beta

Métricas de aceite para promover do beta para GA Premium:
- **Conversão free→Premium ≥ 8%** em 60 dias de uso ativo (uso ativo = ≥ 3 logins na janela).
- **NRR (Net Revenue Retention) cohort Q3 2026 ≥ 110%** (ou seja, premium permanece e expande).
- **`items_gated_count` médio:** monitora trend, sem target absoluto. Sinal: alto valor "visível mas trancado" deve correlacionar com conversão.

**Se métricas abaixo do threshold:**
- **Revisar gating, não pricing inicial** — recomendação `gtm-strategist`. Pode ser que free está vendo demais (zero urgência) ou de menos (zero valor). Não desça pricing first; ajuste o que mostra primeiro.
- Próxima iteração: A/B test (e.g., free vê 2 riscos vs 1, ou diagnóstico mais curto).

### D6. Defesa competitiva — depth-of-service > velocity

- Não responder à velocity de Pierre Finance (CloudWalk lança rápido, refina depois). Reposicionar:
  - **Pierre:** "AI advisor genérico" — output sem lineage, sem auditabilidade, sem methodology anchors.
  - **Mathoms:** "Planejador digital metodológico-auditável" — parecer rastreia âncora ([[ADR-207]]), supersede chain ([[ADR-204]]), validado por CFPs independentes (gate dogfood).
- Moat: depth-of-service (parecer → Suggestion → Task → Decision rastreável). Pierre teria que reconstruir todo o operating system de recomendações ([[ADR-153]] e adjacentes) para igualar.
- Curadoria visível do glossário de 9 temas canônicos ([[ADR-207]]) validada por CFPs.

### D7. Sigilo §13 mantido em ambos tiers

- Filtragem free/premium **não toca** sigilo §13 ([[ADR-207]]). Free vê `tema_canonico`, premium vê `tema_canonico`. Nenhum dos dois vê `ancora_metodologica`.
- Auditoria interna funciona idêntico (persistência completa no aggregate).

## Consequências

**Positivas:**
- Diferenciação clara free vs premium — valor visível, valor trancado, CTA direto.
- Backend enforça gating — vazamento via DevTools impossível.
- Instrumentação completa para decisão data-driven em 60d.
- Defesa competitiva explícita (não velocity match, reposicionamento).
- Pattern reusável: outras features premium futuras seguem mesmo schema (filtragem backend + instrumentação + gate de revisão).

**Negativas / trade-offs aceitos:**
- Stage roda para free também → LLM cost por usuário free positivo. Mitigação: gate `MATHOMS_PARECER_FREE_GENERATION` permite desligar para free se métrica de conversão não justificar.
- Copy do teaser ("+14 riscos no Premium") pode soar predatório se mal escrito. Mitigação: `product-designer` + `gtm-strategist` co-design no Ato 5.
- Hard caps ([[ADR-202]]) viraram parte da identidade ("3 pontos fortes, 12 riscos, etc.") — bump exige cuidado de produto.
- Pricing final exige ADR separada (decisão fora do escopo desta).

**Riscos mitigados:**
- **Custo LLM insustentável:** gating economiza custo de impressão (UI não força user a ler tudo).
- **Pierre/CloudWalk launch antes (RPN-1):** reposicionamento + depth-of-service moat.
- **Free não converte:** gate 60d + instrumentação → revisão.
- **Vazamento de payload pago:** backend filtra antes de serializar.

## Implementação

- **Track(s) do plano:** T-22 (`planner-gating-tier-filter`).
- **Files touched:**
  - `backend/app/api/planner_review.py` — endpoint com `tier_at_generation` lookup
  - `backend/app/repositories/planner_review.py` — `to_tier_filtered_dto(tier)`
  - `backend/app/services/parecer_orchestrator.py` — `tier_at_generation` no `_meta`
  - `frontend/src/components/report/sections/SParecer*.tsx` — handling do payload tier-aware
  - `frontend/src/components/report/sections/SParecerTeaserUpgrade.tsx` — CTA específico
  - Métricas Prometheus + dashboards (`sre-devops` finaliza)
- **Critério de aceite:**
  - E2E test com `tier=free` valida payload tem `riscos_sample` (1 item), teaser, `items_gated_count > 0`.
  - E2E test com `tier=premium` valida payload completo.
  - Network tab DevTools: free user **não** recebe items completos (regression test).
  - Métricas Prometheus expostas (`cta_upgrade_click_total`, etc.).
- **Gates CI:** `pytest backend/tests/test_planner_review_tier_filter.py`, `npm run test:e2e -- planner-tier-gating`, OpenAPI snapshot.

**Decisão pendente para outros especialistas:**
- **Pricing exato e packaging** (R$ 79 vs 99 vs 149; per-workspace vs per-user) — `gtm-strategist` finaliza em ADR pricing separada antes GA.
- **Copy do teaser** ("+14 riscos no Premium" vs alternativas) — `product-designer` + `gtm-strategist` co-design Ato 5.
- **Decisão `MATHOMS_PARECER_FREE_GENERATION` default** (true = gera para free; false = só on upgrade) — `product-manager` revisa após 30d de instrumentação.
- **Métricas de NRR (Net Revenue Retention)** instrumentadas via sistema de billing — `sre-devops` integra após Stripe/billing definidos.
