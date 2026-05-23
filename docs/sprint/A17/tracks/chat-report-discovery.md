---
id: TRACK-chat-report-discovery
type: track
title: "Track Chat + Memories Discovery — Fase 3.A COMPETITIVE_PIERRE (3-5 dogfood interviews + taxonomy review)"
sprint: A17
plan: PLAN-competitive-pierre
status: ready
created_at: "2026-05-23"
consumed_at: null
agent_role: "product-designer (primary) + financial-planner (secondary)"
relates_to:
  - "[[PLAN-competitive-pierre]]"
  - "[[ADR-183]]"
tags:
  - type/track
  - sprint/a17
  - status/ready
  - area/discovery
  - area/competitive
  - area/ai-platform
---

# Track Chat + Memories Discovery — Fase 3.A COMPETITIVE_PIERRE

> **Plano canônico:** [[PLAN-competitive-pierre]] §3 Fase 3 sub-fase 3.A
> **Branch prefix:** `agent/chat-report-discovery/<yyyyMMdd-HHmm>` (paths disjuntos — não toca código de produto)
> **Hospedagem em A17:** este track é **async ao trabalho de eng A17** (owners distintos — `product-designer` + `financial-planner` não disputam capacity com A17.l1-l4). Sprint A17 é apenas o folder de hospedagem; track é cross-cutting do plano competitive.
> **Bloqueia:** 3 ADRs pré-requisito de 3.E ([[ADR-262]] memory-confirmation-tracking, [[ADR-263]] goal-reserva-emergencia-schema, [[ADR-264]] goal-meta-objetivo-schema) + abertura de ADR `financial-memories-surface` (3.E) + track `chat-report-spike.md` (3.B)
> **Time-box:** ~2 semanas (1 semana interviews, 1 semana consolidação)
> **Substrato de entrada:** [discovery output 2026-05-23](../../../plan/COMPETITIVE_PIERRE/assets/3e-discovery-2026-05-23.md) (taxonomia 16 fatos + INV1-5 + mockups + research questions já consolidados pelo `senior-cto` consumindo output de 4 especialistas em paralelo)

---

## 1. Goal

Validar com 3-5 usuários reais (dogfood/beta) o discovery inicial de **chat sobre relatório + Financial Memories surface** (Fase 3.A do plano competitivo), produzido em paralelo por `product-designer`, `financial-planner` e `product-manager` na sessão 2026-05-23. Saída esperada: deck final de discovery 3.A com taxonomia validada empiricamente, antes de abrir ADRs de implementação 3.B (chat architecture) e 3.E (memories surface).

**Janela competitiva:** ChatGPT Personal Finance lançou em mai/2026 (US-only, Pro tier) com "Financial memories" persistentes. Janela de captura no Brasil estimada em 12-18 meses (Plaid não opera BR; depende de Belvo/Pluggy + LGPD). Discovery rigoroso agora habilita 3.E pronto para A20.

---

## 2. Escopo

### Já entregue (input pronto)

Documento [assets/3e-discovery-2026-05-23.md](../../../plan/COMPETITIVE_PIERRE/assets/3e-discovery-2026-05-23.md) consolida:

- **§1 Taxonomia 16 fatos × 7 categorias** (financial-planner) — Vida e família, Profissional e renda, Patrimônio e risco, Metas estruturadas, Sucessão e proteção, Fiscal, Lifestyle e custo de vida.
- **§2 Invariantes metodológicos INV1-5** (financial-planner) — reserva ancorada em fórmula, risco declarado nunca derivado, IF tripla coerência, holding/sucessão completa, alocação respeita modo de rebalanceamento.
- **§3 6 anti-padrões** (financial-planner) — palpite macro, sentimento de mercado, tickers, performance histórica, comparação terceiros, duplicação Decision.
- **§4 Decisões UX D1-D5** (product-designer) — rota dedicada `/workspace/memories`; lista única com glyph + procedência; CTA "Revisar derivadas" no empty; audit trail leve sem notif ativa MVP; fixar-pro-chat fica em 3.C.
- **§5 3 mockups baixa-fidelidade** (product-designer) — tela principal, edit inline, estado vazio.
- **§6 8 research questions** (product-designer) — Bloco A mental model · Bloco B confiança derivada vs declarada · Bloco C cônjuge e jornada · Bloco D ligação com chat e abandono.
- **§8 3 ADRs pré-requisito** (senior-cto consolidando) — `memory-confirmation-tracking`, `goal-reserva-emergencia-schema`, `goal-meta-objetivo-schema`.

### A executar neste track

| # | Entregável | Owner | Duração |
|---|---|---|---|
| T1 | Recrutamento de 3-5 entrevistados conforme perfil §6: 3 HENRY com ≥1 relatório gerado + 1 que abandonou setup + 1 cônjuge não-titular | `product-designer` | 3 dias |
| T2 | Entrevistas 1-1, 30min cada, gravadas (com consentimento), aplicando as 8 research questions §6 do asset | `product-designer` + `financial-planner` (rotativo) | 1 semana |
| T3 | Transcrição + síntese: matriz 8×N (perguntas × entrevistados) com sinais positivos/negativos por decisão (D1-D5) | `product-designer` | 3 dias |
| T4 | Revisão da taxonomia 16 fatos × 7 categorias contra dados das entrevistas — confirma/refuta/expande | `financial-planner` | 2 dias |
| T5 | Deck final de discovery 3.A em `_scratch/chat-memories-discovery-2026-XX/` consolidando T3 + T4 + ajustes nas decisões D1-D5 | `product-designer` + `financial-planner` | 2 dias |
| T6 | Atualização do asset [assets/3e-discovery-2026-05-23.md](../../../plan/COMPETITIVE_PIERRE/assets/3e-discovery-2026-05-23.md) marcando seções "validado empiricamente" vs "hipótese pendente" + commit no plano | `senior-cto` (consolida) | 1 dia |

### Fora de escopo

- **Não codar** chat-side nem `/workspace/memories` — discovery é descoberta, não implementação. Implementação espera 3.C e 3.E (eng A20+).
- **Não escrever** copy literal de UI — escopo do PR-C de [[ADR-183]] (designer separado).
- **Não decidir** arquitetura do RAG (3.B) nem cost ceiling (3.D) — esses dependem do output deste track.

---

## 3. Critérios de aceite

- [ ] 3-5 entrevistas conduzidas, transcritas e sintetizadas (matriz 8×N).
- [ ] Taxonomia 16 fatos revisada pelo `financial-planner`: para cada fato, anotar "confirmado por ≥2 entrevistados" / "refutado por ≥1" / "ausente nas entrevistas".
- [ ] Decisões D1-D5 do designer atualizadas com sinal empírico: por exemplo, D3 (CTA empty state = "Revisar derivadas" vs "Declarar memória") deve ter resposta convergente em ≥3 entrevistas para confirmar; se divergente, A/B test obrigatório em 3.E MVP.
- [ ] Anti-patterns §3 do asset confirmados ou refinados com base nas entrevistas.
- [ ] PR único (`docs(competitive): discovery 3.A validado empiricamente`) atualizando asset com seção "Validação empírica 2026-XX-XX".
- [ ] Deck consolidado em `_scratch/` (gitignored — referência interna; commit só do delta no asset canônico).
- [ ] Plano [[PLAN-competitive-pierre]] §3 marca 3.A como **concluído**, destrava 3.B (chat-report-spike) + 3 ADRs pré-req + 3.E (financial-memories-surface) para próxima sessão de materialização.

---

## 4. Dependências e bloqueios

**Bloqueia:**
- 3.B (`chat-report-spike.md` — RAG architecture) — chat MVP precisa de intents validados.
- 3.E (`financial-memories-surface.md`) — surface precisa de taxonomia validada antes de abrir ADR.
- 3 ADRs pré-requisito ([[ADR-262]], [[ADR-263]], [[ADR-264]]) — podem ser abertas em paralelo a este track (escopo arquitetural independe de entrevistas), mas o **PR de implementação** delas só roda após T6.

**Não bloqueia:**
- Trabalho de A17 (eng L1-L4 ADR-238) — owners distintos.
- A18 / A19 candidate — paths disjuntos.
- PR-C de [[ADR-183]] (copy literal landing) — pode rodar em paralelo, consumindo as 4 sub-headlines já auditadas pelo `gtm-strategist` em 2026-05-23.

---

## 5. Anti-padrões

- **Discovery por survey impessoal** — research questions §6 do asset são designed para entrevista 1-1 com follow-up. Survey perde nuance de Bloco B (confiança em derivada).
- **Validação só com dogfood interno** — recrutar ao menos 1 entrevistado externo (beta user ou prospect HENRY) para sinal sem viés de equipe.
- **Concluir discovery sem revisão do financial-planner em T4** — taxonomia metodológica precisa de leitura especialista; não é puro UX research.

---

## 6. Notas

- **Vocabulário público:** durante entrevistas, **não** nomear Perini/Cerbasi/AUVP nem ChatGPT/Pierre/concorrente. Usar §13.2 [COPY_GUIDELINES](../../../reference/COPY_GUIDELINES.md) ("metodologia consagrada", "assistente AI genérico" se necessário).
- **Privacidade:** transcrições e gravações ficam em `_scratch/` (gitignored). Consentimento por escrito antes de cada entrevista; participantes podem revogar a qualquer momento (LGPD).
- **Pago vs gratuito:** considerar pequeno incentivo (R$ 50-100 voucher) para entrevistados externos — não-dogfood. Decidir com CEO antes de T1.
