---
id: PLAN-competitive-pierre
type: plan
title: Resposta competitiva a Pierre — recon, MCP, chat, reposicionamento
status: draft
sprint_origem: A11
sprint_atual: A11
sprints_envolvidas: [A11]
created_at: "2026-05-08"
last_review: "2026-05-08"
paused_at: null
pause_reason: null
adrs_canonical: []
tags:
  - type/plan
  - status/draft
  - area/strategy
  - area/competitive
  - area/openfinance
  - methodology/build-vs-buy
---

# Resposta competitiva a Pierre — recon, MCP, chat, reposicionamento

> **Origem:** análise CEO 2026-05-08 após mapeamento factual de [Pierre Finance](https://lp.pierre.finance/) (CloudWalk, lançado 2025-07; 165k usuários; R$ 800 mi AUM).
>
> **Audiência:** orquestrador `senior-cto` + delegação a `build-vs-buy`, `product-manager`, `product-designer`, `financial-planner` por fase.
>
> **Status do plano:** `draft` (ainda sem ADR Proposto materializada — Fase 1 abre a ADR de competitor analysis; cada fase subsequente abre a sua antes do PR de implementação, conforme [CLAUDE.md §"Política operacional — ADR Proposto antes de PR P0/P1"](../../../CLAUDE.md)).
>
> **NÃO está em escopo:** a decisão **build vs buy do agregador OFB B2B** (Pluggy / Belvo / Klavi / DIY) — esse é plano e ADR separados, decidido em pista paralela. Razão: a decisão do agregador depende de variáveis comerciais (pricing por consent ativo, CAC, AUM) que independem da resposta a Pierre, e bundlear as duas decisões aumenta acoplamento sem ganho.

---

## 1. Tese estratégica

> **Pierre é *budgeting copilot* (consumer mass-market). Mathoms é *wealth advisor* (HENRY → wealthy → UHNW). Os produtos vão colidir em 12-18 meses.** Pierre vai adicionar profundidade (planejamento, cônjuge, IRPF) com o backing da CloudWalk; Mathoms precisa adicionar fricção-zero de coleta + UX conversacional + presença em ecossistema AI antes que a colisão chegue.
>
> **Vencemos se fecharmos o gap de UX e ecossistema antes do Pierre fechar o gap de profundidade metodológica.** Esta é a hipótese que o plano executa.

### 1.1 Onde Pierre ganha hoje (diagnóstico factual)

1. **Fricção de onboarding** — OFB + 100+ FIs + WhatsApp = <5min vs nosso parser de docs (12+ uploads, ~30min até primeiro relatório utilizável).
2. **Distribuição CloudWalk** — Infinite Pay merchants, balance sheet, brand awareness consumer.
3. **Multi-agent conversacional** — Albert (daily monitor), Marie (recurring), Galileu (monthly strategy). UX nativa que `/reports/[id]` não tem.
4. **Pierre-as-MCP** — posicionamento "Alexa das finanças" via Cursor / Claude Code / Windsurf. Quem ocupa esse slot na vitrine AI ganha mindshare.
5. **Free tier R$ 0 + tier R$ 39** — fricção de aquisição mínima.

### 1.2 Onde Pierre é raso (nosso moat real)

1. **Sem metodologia codificada** — categorização "genérica", sem Perini/Cerbasi/AUVP rules-as-code (nosso [ADR-143](../../adr/143-docsmethodology-e-rules-as-code-sprint-a76.md)).
2. **Sem profundidade de planejamento** — alertas vs IF projector + cenários + score 0-1000 + plano de ação event-sourced (`Decision` aggregate, [ADR-136](../../adr/136-decision-aggregate-event-sourced-com-supersede.md)).
3. **Single user** — sem cônjuge, sem `family_members`, sem `cenarios_conjuge` formal ([ADR-166](../../adr/166-schema-estavel-cenarios-conjuge-no-payload-e5.md)).
4. **Sem fiscal** — sem IRPF parser, sem `fiscal_parameters` versionado ([ADR-135](../../adr/135-versionamento-temporal-de-series-fiscais-e-cambio.md)), sem PGBL/lucro presumido.
5. **Sem ativos fora do OFB plena** — fundo exclusivo, FII com distribuição parcial, conta no exterior, holding patrimonial. Nosso parser é moat aqui.
6. **Sem QA humano** — não tem stage E7-review nem apparatus de erro/ambiguidade estrutural.
7. **Sem export soberano** — relatório PDF entregável a planejador/contador/sucessão.

### 1.3 Por que Pierre **não** é caminho de agregador para nós

Lendo [docs.pierre.finance](https://docs.pierre.finance/) verbatim:

| Restrição API Pierre | Implicação |
|---|---|
| 1 API key = 1 assinatura = 1 end-user | Não é multi-tenant. Inviável como canal B2B. |
| `get-open-finance-connection-flow` envia fluxo via WhatsApp | Sem callback OAuth programático; onboarding humano. |
| `accountBalance: 1500.50` (number/float) | Viola [ADR-090](../../adr/090-decimal-money.md). Drift de arredondamento garantido. |
| Sem webhooks; só `manual-update` (pull) | Sem real-time. |
| Categorização proprietária | Conflita com `category_template` + `workspace_category_overrides` ([ADR-137](../../adr/137-catalog-override-resolver-para-categorization-e.md)). |
| API/MCP gated por Pro/Premium (R$ 39+/mês por user) | Sem margem se usado como canal B2B. |
| Investments shallow (sem position-level) | Não cobre o que precisamos para alocação. |

**Pierre vende API developer-hobbyist para fidelizar tier pago, não infraestrutura B2B.** O agregador real para Mathoms é decisão paralela (ver §"Não está em escopo").

---

## 2. Premissas que governam o plano

P1. **Open Finance está virando commodity em 18-24 meses** — fase de investimentos OFB é roadmap declarado do BCB para 2026-2027. Janela atual de diferenciação por *coleta* é finita. Diferenciação durável = *insight*, *plano*, *execução*.

P2. **MCP virou superfície de competição em 2025/2026.** Pierre escolheu a narrativa "Alexa das finanças" e ganhou first-mover no slot AI-nativo. Cada mês sem MCP server próprio é mês de mindshare cedido ao Cursor/Claude Code/Windsurf default.

P3. **Mathoms já investiu pesado em layer de insight.** 175+ ADRs, regras-as-code Perini/Cerbasi/AUVP, IF projector, score, plano de ação event-sourced, IRPF parser, conjuge. Não construiríamos do zero hoje em <12 meses. **É moat real, não folclore.**

P4. **Segmento alvo do Mathoms (HENRY R$ 200k+ patrimônio) suporta pricing > R$ 99/mês** se a sinalização de seriedade for clara. Free tier é veneno para esse segmento — inflado de usuários sub-economic gera CAC alto, churn alto, ruído na vox-do-cliente.

P5. **CloudWalk vai apertar.** Se Pierre mostrar tração 2026, CloudWalk injeta capital, contrata sales B2B, e fecha parcerias com bancos. Janela de execução = 12-18 meses.

P6. **A jugular do Pierre é cônjuge/sucessão.** Casal HENRY com filhos não cabe em chat single-user. Quem dobra cônjuge + sucessão + holding patrimonial primeiro pega esse segmento. Nosso schema já comporta — falta exploração de produto.

---

## 3. Fases do plano

Quatro fases. Numeração mantém os "movimentos" originais da análise CEO 2026-05-08 (movimento 2 — agregador — é plano paralelo).

### Fase 1 — Recon & calibração (Sprint A11, 2-3 dias)

**Goal:** medir factualmente a barra do Pierre via assinatura paga; produzir dossiê e ADR de competitor analysis.

**Entregáveis:**

- ✅ **Track criado:** [docs/sprint/A11/tracks/competitor-pierre-poc.md](../../sprint/A11/tracks/competitor-pierre-poc.md) — 8 critérios de aceite, time-box 3 dias, R$ 120.
- ⬜ **Dossiê factual** em `_scratch/pierre-poc-2026-05-08/REPORT.md` com H1-H5 confirmadas/falsificadas.
- ⬜ **Benchmark MCP-vs-relatório** nas 10 perguntas patrimoniais (§4 do track).
- ⬜ **ADR Proposto** `competitor-analysis-pierre` (próximo ID livre) — sumariza recomendações de imitar/diferenciar/ignorar. Não decide arquitetura — calibra fases 2-4.

**Owner:** orquestrador `senior-cto` + delegação a `build-vs-buy` para revisão final do dossiê.

**Critério de saída:** dossiê + ADR mergeados → habilita Fase 2 (MCP) com contexto factual em vez de opinião.

**Risco principal:** dossiê voltar inconclusivo (H1-H5 ambíguos). Mitigação: time-box rígido — fecha com "inconclusivo + razão" em vez de estender. Spike é spike.

### Fase 2 — Mathoms-as-MCP (Sprint A11→A12, ~3 sprints)

**Goal:** posicionar Mathoms como MCP server consultável por AIs externas (Claude/ChatGPT/Cursor). Diferenciação: nosso MCP entrega **insight processado, não dado bruto**. Pierre vende "AI nativa OFB"; Mathoms vende "AI nativa de planejamento".

**Sub-fases:**

| Sub | Escopo | Duração | ADR |
|---|---|---|---|
| 2.A | Spike de design — surface (read-only? action-trigger?), authn (API key vs OAuth), authz (workspace scope), rate-limit, telemetria. Output: doc de design + decisão. | 1 semana | abrir `mathoms-mcp-server-design` Proposto |
| 2.B | MVP read-only: `get_report`, `get_score`, `get_decisions`, `get_suggestions`, `get_balance_sheet`, `query_transactions`. Reusa autenticação + Fernet vault existente. | 2 semanas | herda 2.A |
| 2.C | Distribution — registry público (Anthropic MCP registry, Smithery), instalação Cursor/Claude Code/Windsurf, doc dev pública (Mintlify ou similar). | 1 semana | — |
| 2.D | Telemetria + abuse limits — quem usa, quanto consome, blacklist de prompt injection (referência [ADR-175](../../adr/175-prompt-injection-defense-em-camadas-sanitize.md)). | 1 semana | herda 2.A |

**Owner:** `senior-cto` (design) + delegação a `sre-devops` (rate-limit, abuse) e `build-vs-buy` (registry choice).

**Decisões abertas que entram na ADR 2.A:**

1. **Escopo write?** Read-only MVP é seguro; escopo write (criar Decision, marcar Suggestion accepted) tem implicação de auth + audit. Recomendação inicial: **read-only no MVP, escopo write em Fase 2 v2 após signal de uso**.
2. **Authn:** API key fixa (Pierre-style) vs OAuth flow (mais correto, mais fricção). Recomendação inicial: **API key derivada do JWT do user, scoped ao workspace**, rotacionável; OAuth flow em v2.
3. **Pricing:** parte do tier pago do Mathoms (não cobra extra) ou monetização separada? Recomendação inicial: **incluir no tier pago** — diferenciação, não revenue stream.
4. **Custo LLM downstream:** quem paga o token quando Claude do usuário consulta nosso MCP? Resposta: o usuário paga (o LLM é dele); nós só servimos JSON. Confirma no design.

**Critério de saída Fase 2:** MCP server live em `mcp.mathoms.ai`; ≥ 5 usuários internos rodando contra produção; instalação documentada em ≥ 2 clients (Claude Code + Cursor).

**Risco principal:** registry público + chave assinada vazada → exposição de dados. Mitigação: gate de IP/domain allowlist por workspace + rate-limit agressivo + Fernet vault (já existe) + telemetria de anomalia.

### Fase 3 — Chat conversacional sobre relatório (Sprint A12→A13, ~3 sprints)

**Goal:** fechar gap de UX vs Pierre conversacional sem virar Pierre — chat é **focado e metodológico** (responde sobre *o seu* plano patrimonial, não sobre o mundo). Camada complementar ao relatório, não substituta.

**Sub-fases:**

| Sub | Escopo | Duração | ADR |
|---|---|---|---|
| 3.A | Discovery — UX research (`product-designer`) + intent inventory (`financial-planner`): quais perguntas o user faz no relatório hoje? Onde abandona? Qual a curva de profundidade? | 1 semana | — |
| 3.B | Spike de design — RAG over E5 JSON + Decision aggregate + Suggestions, com guardrails metodológicos (resposta cita ADR/regra). Decisão: ChatGPT-style (livre) vs structured-prompt (slots). | 1 semana | abrir `chat-over-report-architecture` Proposto |
| 3.C | MVP — chat-side em `/reports/[id]` (drawer ou painel fixo), 5 intents iniciais (saldo, alocação, score, próximo passo, simulação simples), latência < 3s p50. | 2 semanas | herda 3.B |
| 3.D | Cost ceiling + telemetria — depende de [ADR-173 LLM budget hard-stop](../../adr/173-llm-budget-hard-stop-llmcalllog-populada-universal.md) (em W3 do PLATFORM_REVIEW). Métricas: intents resolvidos vs não-resolvidos, custo médio/conversa, opt-out rate. | 1 semana | herda [ADR-173] |

**Owner:** `financial-planner` (intent design) + `product-designer` (UX) + `senior-cto` (arquitetura) + `sre-devops` (cost ceiling).

**Dependência hard:** [ADR-173 LLM budget hard-stop](../../adr/173-llm-budget-hard-stop-llmcalllog-populada-universal.md) precisa estar mergeado antes de chat ir live em produção. Bloqueio explícito.

**Decisões abertas que entram na ADR 3.B:**

1. **Escopo de ação:** chat só lê (read-only) ou pode propor Decision/Task draft para approval? Recomendação inicial: **propor draft, nunca executar** — usuário sempre confirma.
2. **Citação de fonte:** toda resposta cita o nó do relatório / ADR de origem? Recomendação inicial: **sim** — diferenciação metodológica vs Pierre genérico.
3. **Histórico de conversa:** persiste por workspace? Por user? Cross-device? Recomendação inicial: **persiste por workspace, encriptado** (uso futuro: aprender padrões do cliente; consumir rationale em revisões trimestrais).
4. **Multi-agent estilo Pierre (Albert/Marie/Galileu)?** Recomendação inicial: **não** — Mathoms é metodológico, não multi-personalidade. Um único copiloto especialista é mais credível para o segmento HENRY.

**Critério de saída Fase 3:** chat live em `/reports/[id]`, ≥ 5 intents resolvidos com ≥ 80% precisão, custo médio < R$ 0,30/conversa, opt-in explícito do user, sem regressão de SLA.

**Risco principal:** chat virar muleta para usuário não ler o relatório → cai a leitura profunda → cai o engajamento metodológico. Mitigação: telemetria de leitura do relatório como guard-rail; se cair >20%, A/B desliga chat.

### Fase 4 — Reposicionamento de marca + GTM (paralelo, ~contínuo, owner CEO)

**Goal:** parar de comunicar Mathoms como "ferramenta de relatórios" ou "ferramenta de planilha 2.0"; comunicar como **advisor digital metodológico** para HENRY brasileiro. Sinalização de seriedade = diferenciação clara de Pierre.

**Sub-fases:**

| Sub | Escopo | Duração | Owner |
|---|---|---|---|
| 4.A | Pesquisa de segmento — entrevistas qualitativas com 10-15 HENRY (R$ 200k+ patrimônio), incluindo 3-5 que já tentaram Pierre/Organizze. Output: deck de personas + ICP refinado. | 2-3 semanas | CEO + `product-manager` |
| 4.B | Reescrita de landing + copy do produto — narrativa "advisor digital metodológico", remoção de comparativos com planilha, ênfase em Perini/Cerbasi/AUVP, conjuge, IRPF, ações premium. | 2 semanas | CEO + `product-designer` |
| 4.C | Pricing repositioning — alinhamento de tiers ao segmento HENRY. Decisão: free tier (canibaliza Pierre), trial 30d (pré-qualifica), ou paywall hard (filtra)? Recomendação inicial: **trial 30d com onboarding humano** + tier base R$ 99-149/mês. | 1 semana de decisão + execução em produto/billing | CEO + `build-vs-buy` (gateway pagamento) |
| 4.D | Conteúdo metodológico — série de artigos/vídeos cobrindo Perini/Cerbasi/AUVP (com permissão devida) e cases brasileiros. Posiciona Mathoms como autoridade pedagógica. | contínuo | CEO + parceiros conteúdo |
| 4.E | SEO + performance no Pierre keyword search — landing comparativo Mathoms-vs-Pierre **factual e respeitoso**, não atacante. Captura queries "Pierre alternativa profunda", "como planejar patrimônio Pierre", etc. | 2-3 semanas | CEO + agência SEO |
| 4.F | Embaixadores e parcerias — planejadores CFP independentes, contadores de PJ alta renda, family offices pequenos. Programa de afiliação ou white-label limitado. | 6-12 meses | CEO + comercial |

**Owner:** CEO direto. Esta fase **não** é eng-driven — é narrativa, posicionamento e canal.

**Decisões abertas:**

1. **Vamos ter free tier?** Recomendação CEO inicial: **não** — free atrai segmento errado. Trial 30d com onboarding humano filtra melhor.
2. **Cônjuge como hero feature** (jugular Pierre, P6)? Recomendação inicial: **sim em 4.B** — destaque na landing como "casal", "patrimônio do casal", "decisões a 4 mãos".
3. **Comparativo público com Pierre?** Risco legal/reputacional. Recomendação inicial: comparativo factual em landing (não ataca, só diferencia), com base em capabilities documentadas em docs.pierre.finance.

**Critério de saída Fase 4 (ano 1):** ≥ 30% dos novos signups vindos de canal pago/conteúdo (não orgânico residual); CAC payback < 6 meses; NPS > 60 no segmento HENRY; ≥ 3 parcerias com CFP ou contador.

**Risco principal:** mover muito rápido para "advisor" sem entregar profundidade ainda perceptível pelo cliente → marketing escreve cheque que produto não paga. Mitigação: 4.B só publica depois de Fase 2 (MCP) e Fase 3 (chat) live, ou pelo menos com beta visível.

---

## 4. Sequenciamento e dependências

```
Fase 1 (recon)  ──┐
                   ├─→ Fase 2 (MCP)        ──┐
                   ├─→ Fase 3 (chat)       ──┼─→ Fase 4 (GTM, sub 4.B+)
                   └─→ Fase 4.A (pesquisa) ──┘

Fase 4.A pode rodar em paralelo com 1, 2, 3.
Fase 4.B+ deve esperar 2 e 3 (pelo menos beta) para a narrativa não furar.
```

- **Fase 1** habilita 2, 3, 4 com dado factual.
- **Fase 2 e 3** rodam em paralelo (owners distintos), competindo por capacidade de eng.
- **Fase 4.A** roda em paralelo desde dia 1 (não depende de eng).
- **Fase 4.B-F** publica depois de Fase 2 ou 3 visíveis (mesmo beta) para narrativa ter prova.

---

## 5. ADRs canonicais a abrir

Pelo protocolo CLAUDE.md "ADR Proposto antes de PR P0/P1", cada fase abre ADR antes do PR de implementação:

| ADR (próximo ID livre) | Slug | Fase | Quando | Responsável |
|---|---|---|---|---|
| ADR-Y1 | `competitor-analysis-pierre` | 1 | ao final do dossiê | `senior-cto` |
| ADR-Y2 | `mathoms-mcp-server-design` | 2.A | antes do PR de MVP | `senior-cto` |
| ADR-Y3 | `chat-over-report-architecture` | 3.B | antes do PR de MVP | `senior-cto` + `financial-planner` |
| ADR-Y4 | `pricing-repositioning-2026` | 4.C | antes da mudança em billing | CEO + `product-manager` |

IDs concretos serão atribuídos no commit que abre cada ADR (próximo livre em [docs/_MOC/_generated/ADR_INDEX.md](../../_MOC/_generated/ADR_INDEX.md) no momento). Ao abrir, atualizar `adrs_canonical` no frontmatter deste plano.

---

## 6. Sinais e KPIs de sucesso

**Fase 1 (recon):** dossiê fechado em ≤ 3 dias, ADR mergeado, ≥ 5 capabilities Pierre catalogadas + ≥ 5 gaps Mathoms vs Pierre quantificados.

**Fase 2 (MCP):** MCP server em `mcp.mathoms.ai` com uptime ≥ 99,5% por 30 dias, ≥ 100 chamadas/dia de ≥ 10 workspaces distintos no fim do trimestre, listing público em registry Anthropic.

**Fase 3 (chat):** ≥ 70% intents resolvidos sem fallback, custo médio < R$ 0,30/conversa, ≥ 40% dos relatórios abertos no trimestre tiveram ≥ 1 interação chat, opt-out < 15%.

**Fase 4 (GTM):** ≥ 30% signups vindos de canal pago/conteúdo, CAC payback < 6m, NPS HENRY > 60, ≥ 3 parcerias CFP/contador.

**Sinais de alarme (revisar plano):**

- Pierre lança feature de cônjuge/sucessão → Fase 4 deve acelerar 4.B com "casal" como hero ainda mais cedo.
- BCB acelera fase de investimentos OFB para Q3 2026 → janela de parser fechando, agregador entra como P0 (fora deste plano, mas contexto).
- CloudWalk anuncia M&A com banco/seguradora → Pierre ganha distribuição de cliente premium; reposicionar Fase 4 para enterprise/family-office mais cedo.

---

## 7. Não-objetivos (escopo explicitamente excluído)

1. **Decisão build vs buy do agregador OFB B2B** (Pluggy / Belvo / Klavi / DIY). Plano e ADR separados, ortogonais. Razão: variáveis comerciais distintas (pricing por consent, CAC, AUM) e não condicionado à resposta a Pierre.
2. **Replicar multi-agent estilo Albert/Marie/Galileu** (recomendação inicial — confirmação na ADR 3.B). Mathoms é um copiloto especialista único, não suite de personalidades. Sinalização de seriedade.
3. **Free tier R$ 0** (recomendação inicial CEO em 4.C). Atrai segmento sub-economic.
4. **Comparativo público agressivo / atacante a Pierre.** Apenas comparativo factual respeitoso baseado em capabilities documentadas.
5. **Integrar API do Pierre como agregador** (já invalidado em §1.3 — single-tenant, float, sem webhooks).

---

## 8. Tracks (existentes + a criar)

### 8.1 Já criados

- [docs/sprint/A11/tracks/competitor-pierre-poc.md](../../sprint/A11/tracks/competitor-pierre-poc.md) — Fase 1 spike, status `ready`.

### 8.2 A criar (por fase, conforme avanço)

| Track sugerido | Fase | Quando criar | Owner |
|---|---|---|---|
| `mathoms-mcp-design.md` | 2.A | após Fase 1 fechar | `senior-cto` |
| `mathoms-mcp-mvp-readonly.md` | 2.B | após ADR 2.A mergeada | `senior-cto` + `sre-devops` |
| `mathoms-mcp-distribution.md` | 2.C | em paralelo a 2.B | `build-vs-buy` (registry choice) |
| `chat-report-discovery.md` | 3.A | em paralelo a 2.A | `product-designer` + `financial-planner` |
| `chat-report-spike.md` | 3.B | após 3.A fechar | `senior-cto` + `financial-planner` |
| `chat-report-mvp.md` | 3.C | após ADR 3.B mergeada e [ADR-173] live | `senior-cto` |
| `gtm-segment-research.md` | 4.A | desde dia 1 (paralelo) | CEO + `product-manager` |
| `gtm-landing-copy-rewrite.md` | 4.B | após Fase 2 ou 3 visíveis (beta) | CEO + `product-designer` |
| `gtm-pricing-repositioning.md` | 4.C | após 4.A | CEO + `product-manager` |

Nomenclatura segue padrão atual (`docs/sprint/<X>/tracks/<slug>.md` com frontmatter `note-track`). IDs serão definidos quando o track for materializado.

---

## 9. Atualizações deste documento

- **2026-05-08:** plano criado em `draft`. Fase 1 track materializado. Fases 2-4 descritas em alto nível, esperando dossiê da Fase 1 para refinar.

Próxima revisão prevista: ao fechamento do dossiê da Fase 1 (estimado até 2026-05-15). Atualizar `last_review` + `status: in_progress` + `adrs_canonical` quando a primeira ADR mergear.

---

## 10. Referências

### Internas

- [Análise CEO 2026-05-08 (origem deste plano)](../../sprint/A11/tracks/competitor-pierre-poc.md) — track Fase 1
- [PLATFORM_REVIEW](../PLATFORM_REVIEW/_README.md) — sprint A11, ADR-173 LLM budget hard-stop é dependência da Fase 3
- [CLAUDE.md §"Política operacional — ADR Proposto antes de PR P0/P1"](../../../CLAUDE.md) — protocolo de ADR Proposto
- [docs/reference/ARCHITECTURE.md](../../reference/ARCHITECTURE.md) — domain glossary, stages, layers
- [ADR-090 Decimal Money](../../adr/090-decimal-money.md) — invariante de moeda
- [ADR-111 Stateless rigoroso](../../adr/111-stateless-rigoroso-padrao-e-gate-empirico-a6f6.md) — invariante de runtime
- [ADR-143 Methodology as Code](../../adr/143-docsmethodology-e-rules-as-code-sprint-a76.md) — moat metodológico
- [ADR-173 LLM Budget Hard-Stop](../../adr/173-llm-budget-hard-stop-llmcalllog-populada-universal.md) — dependência Fase 3
- [ADR-175 Prompt Injection Defense](../../adr/175-prompt-injection-defense-em-camadas-sanitize.md) — base para Fase 2.D

### Externas (Pierre / contexto)

- [Pierre — landing](https://lp.pierre.finance/)
- [docs.pierre.finance — llms.txt](https://docs.pierre.finance/llms.txt)
- [docs.pierre.finance — Authentication](https://docs.pierre.finance/api-services/authentication.md)
- [docs.pierre.finance — REST API](https://docs.pierre.finance/api-services/rest-api.md)
- [docs.pierre.finance — MCP Server](https://docs.pierre.finance/api-services/mcp-server.md)
- [docs.pierre.finance — MCP Tools](https://docs.pierre.finance/api-reference/mcp/tools.md)
- [docs.pierre.finance — Claude Code Integration](https://docs.pierre.finance/editor-integration/claude-code.md)
- [Exame — Pierre/CloudWalk aposta consumer](https://exame.com/inteligencia-artificial/pierre-assistente-de-ia-para-financas-vira-aposta-da-cloudwalk-para-crescer-no-consumo/)
- [Let's Money — Pierre MCP "Alexa das finanças"](https://www.letsmoney.com.br/destaque/pierre-mcp-alexa-financas/)
- [Finsiders — Pierre conversational](https://finsidersbrasil.com.br/conteudo-de-marca/pierre-transforma-gestao-financeira-em-uma-conversa-sem-planilhas-nem-graficos-confusos/)
