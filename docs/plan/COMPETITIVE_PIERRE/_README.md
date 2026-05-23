---
id: PLAN-competitive-pierre
type: plan
title: Resposta competitiva — Pierre + ChatGPT Finance (recon, MCP, chat, memories, reposicionamento)
status: draft
sprint_origem: A11
sprint_atual: A11
sprints_envolvidas: [A11]
created_at: "2026-05-08"
last_review: "2026-05-23"
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-183]]"
  - "[[ADR-262]]"
  - "[[ADR-263]]"
  - "[[ADR-264]]"
tags:
  - type/plan
  - status/draft
  - area/strategy
  - area/competitive
  - area/openfinance
  - area/ai-platform
  - methodology/build-vs-buy
---

# Resposta competitiva — Pierre + ChatGPT Finance (recon, MCP, chat, memories, reposicionamento)

> **Origem:** análise CEO 2026-05-08 após mapeamento factual de [Pierre Finance](https://lp.pierre.finance/) (CloudWalk, lançado 2025-07; 165k usuários; R$ 800 mi AUM). **Expansão 2026-05-23:** segunda frente competitiva — [OpenAI ChatGPT Personal Finance](https://openai.com/index/personal-finance-chatgpt/) (preview Pro tier US, mai/2026; Plaid + Hiro acquisition; "financial memories" persistentes). Pierre + ChatGPT atacam vetores adjacentes mas distintos — este plano responde a ambos sem fragmentar entregáveis.
>
> **Audiência:** orquestrador `senior-cto` + delegação a `build-vs-buy`, `product-manager`, `product-designer`, `financial-planner`, `gtm-strategist` por fase.
>
> **Status do plano:** `draft` (ainda sem ADR Proposto materializada — Fase 1 abre a ADR de competitor analysis; cada fase subsequente abre a sua antes do PR de implementação, conforme [CLAUDE.md §"Política operacional — ADR Proposto antes de PR P0/P1"](../../../CLAUDE.md)).
>
> **NÃO está em escopo:** a decisão **build vs buy do agregador OFB B2B** (Pluggy / Belvo / Klavi / DIY) — esse é plano e ADR separados, decidido em pista paralela. Razão: a decisão do agregador depende de variáveis comerciais (pricing por consent ativo, CAC, AUM) que independem da resposta a Pierre/ChatGPT, e bundlear as duas decisões aumenta acoplamento sem ganho.

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

### 1.4 Segunda frente: ChatGPT Personal Finance (OpenAI, mai/2026)

> **ChatGPT é *assistente conversacional financeiro genérico* (US-only hoje, premium). Pierre e Mathoms colidirão antes; ChatGPT colide depois — mas pavimenta expectativa de UX para o mercado todo.** Não responder a este vetor agora é deixar a janela de mindshare conversacional aberta.

**Onde ChatGPT é forte (diagnóstico factual):**

1. **Memória financeira persistente** ("Financial memories") — usuário diz "estou economizando para casa em 5 anos", ChatGPT propaga para todas as conversas. UX simples, gravita engajamento.
2. **Conexão Plaid 12.000+ instituições** com onboarding fricção-zero — mesma jugular do Pierre no Brasil (OFB).
3. **Reasoning sobre contexto financeiro real** com GPT-5.5 — interpretação livre de qualquer pergunta, não apenas intents pré-definidos.
4. **Distribuição via base ChatGPT existente** — não precisa adquirir usuário; só ativar feature em quem já paga Pro.
5. **Roadmap declarado:** Intuit/TurboTax (impostos US) + odds de crédito — sinaliza ambição de cobrir patrimônio + fiscal + crédito em uma só superfície.

**Onde ChatGPT é raso (nosso moat real, mantido vs ChatGPT):**

1. **US-only** — Plaid não opera no Brasil; LGPD + Open Finance brasileiro adicionam 12-24 meses de gap regulatório. Janela de execução real.
2. **Sem fiscal brasileiro** — sem IRPF parser ([[ADR-157]]), sem `fiscal_parameters` BRL versionado ([[ADR-135]]), sem PGBL/lucro presumido. Intuit cobre US, não Brasil.
3. **Single-user** — sem `family_members`, sem `cenarios_conjuge` ([[ADR-166]]/[[ADR-167]]). "Financial memories" é por conta, não por núcleo familiar.
4. **Sem metodologia codificada** — chat genérico raciocina caso-a-caso; sem Perini/Cerbasi/AUVP rules-as-code ([[ADR-143]]). Aconselhamento é estatisticamente plausível, não metodologicamente ancorado.
5. **Sem relatório editorial entregável** — output é conversa, não documento. Planejador/contador/sucessão precisam de PDF; ChatGPT não entrega.
6. **Sem plano de ação event-sourced** — não há `Decision` aggregate ([[ADR-136]]); recomendações são efêmeras, não auditáveis, não evoluem com supersedure formal.
7. **Sem ativos fora do escopo Plaid** — fundo exclusivo, FII distribuição parcial, conta no exterior, holding patrimonial. Mesmo gap do Pierre.

### 1.5 Por que ChatGPT **não** ameaça Mathoms no curto prazo (12-18 meses)

| Restrição ChatGPT 2026-05 | Implicação |
|---|---|
| US-only, Plaid-dependent | Sem produto BR até resolverem Open Finance + LGPD + parceria local (Belvo/Pluggy). Janela ≥ 12-18 meses. |
| Pro tier US$200/mês | Pricing premium global; no Brasil, conversão R$ ~1.000/mês seria proibitivo mesmo para HENRY. Plus tier (US$20) ainda sem timeline. |
| Sem persona financeira pública | "ChatGPT genérico" comunica genérico. Mathoms comunica "advisor metodológico brasileiro" — categoria distinta. |
| Memória textual, não estruturada | Memórias são livre-forma; não há aggregate de Goals/Decisions com supersedure. Não auditável. |
| Sem entregável fora do chat | Sem PDF, sem dashboard partilhável com cônjuge/contador. Reativo, não consultivo. |

### 1.6 Pierre vs ChatGPT — vetores ortogonais, resposta convergente

Pierre e ChatGPT atacam **vetores diferentes** (consumer mass-market BR vs premium global generalista), mas as ações de resposta do Mathoms **convergem**: chat sobre relatório, financial memories como superfície UX, posicionamento metodológico explícito, MCP server soberano. **Por isso unificamos no mesmo plano** em vez de criar `COMPETITIVE_CHATGPT/` paralelo — fragmentação de plano teria duplicado entregáveis sem ganho.

---

## 2. Premissas que governam o plano

P1. **Open Finance está virando commodity em 18-24 meses** — fase de investimentos OFB é roadmap declarado do BCB para 2026-2027. Janela atual de diferenciação por *coleta* é finita. Diferenciação durável = *insight*, *plano*, *execução*.

P2. **MCP virou superfície de competição em 2025/2026.** Pierre escolheu a narrativa "Alexa das finanças" e ganhou first-mover no slot AI-nativo. Cada mês sem MCP server próprio é mês de mindshare cedido ao Cursor/Claude Code/Windsurf default.

P3. **Mathoms já investiu pesado em layer de insight.** 175+ ADRs, regras-as-code Perini/Cerbasi/AUVP, IF projector, score, plano de ação event-sourced, IRPF parser, conjuge. Não construiríamos do zero hoje em <12 meses. **É moat real, não folclore.**

P4. **Segmento alvo do Mathoms (HENRY R$ 200k+ patrimônio) suporta pricing > R$ 99/mês** se a sinalização de seriedade for clara. Free tier é veneno para esse segmento — inflado de usuários sub-economic gera CAC alto, churn alto, ruído na vox-do-cliente.

P5. **CloudWalk vai apertar.** Se Pierre mostrar tração 2026, CloudWalk injeta capital, contrata sales B2B, e fecha parcerias com bancos. Janela de execução = 12-18 meses.

P6. **A jugular do Pierre é cônjuge/sucessão.** Casal HENRY com filhos não cabe em chat single-user. Quem dobra cônjuge + sucessão + holding patrimonial primeiro pega esse segmento. Nosso schema já comporta — falta exploração de produto.

P7. **ChatGPT Finance eleva a expectativa de mercado para chat conversacional sobre dados financeiros próprios.** O segmento HENRY brasileiro vai passar a esperar essa UX em qualquer produto que se proponha "advisor". Não responder = ser percebido como "ferramenta antiga". Janela: ~12 meses até ChatGPT chegar ao BR (Plus tier + Open Finance integration). **Fase 3 (chat sobre relatório) sai de "nice-to-have" e vira gate de credibilidade.**

P8. **"Financial memories" é primitiva de UX, não primitiva de dados — para nós.** ChatGPT inventou a *superfície* (card editável "isto sabemos sobre você"); o Mathoms já tem a *substância* (`Goal`, `Decision`, `family_members`, workspace settings). Lançar a superfície custa 1-2 sprints; ignorá-la deixa o usuário pensando que ChatGPT "lembra mais" só porque mostra.

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

### Fase 2 — Mathoms-as-MCP (candidate pós-A19, ~3 sprints)

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

### Fase 3 — Chat conversacional + Financial Memories sobre relatório (candidate A20+, ~3 sprints) — **prioridade elevada por P7/P8**

**Goal:** fechar gap de UX vs Pierre conversacional **e vs ChatGPT Finance** sem virar nenhum dos dois — chat é **focado e metodológico** (responde sobre *o seu* plano patrimonial, não sobre o mundo); memories é **superfície explícita** sobre Goals/Decisions/Workspace já existentes (não nova primitiva de dados). Camadas complementares ao relatório, não substitutas.

> **Calibração de sprint 2026-05-23 (PM):** sprint atual é **A17 `current`** (Ingestão de Informes Anuais, ADR-238); A18+A19 já `candidate` (CRLV/apólices/FIPE em A18, S_PROTECAO em A19); A11/A12/A13 estão `paused`. Fase 3 entra como **candidate A20** (próxima slot disponível pós-A19), condicional ao gate de saída A19 e ao fechamento de 3.A com taxonomy aprovada. Promoção antecipada (escorrega para A18/A19) só se sinal de alarme §6 disparar (parceria OpenAI-Belvo, competidor BR memories first-mover).
>
> **Mudança 2026-05-23 vs versão original:** Fase 3 era "chat sobre relatório" único. Com o lançamento do ChatGPT Personal Finance (mai/2026), `Financial Memories` virou expectativa de UX. Adicionada sub-fase **3.E — Financial Memories surface** como entregável irmão. Razão: ambos consomem o mesmo substrato (`Goal` + `Decision` + workspace settings + family); separar duplicaria descoberta UX e RAG store.
>
> **3.A pode começar AGORA** — discovery (UX + taxonomy) é async ao trabalho de eng A17/A18, com owners distintos (`product-designer` + `financial-planner`). Não consome capacity de eng atual. Sinal verde do PM dado em 2026-05-23.

**Sub-fases:**

| Sub | Escopo | Duração | ADR |
|---|---|---|---|
| 3.A | Discovery — UX research (`product-designer`) + intent inventory (`financial-planner`): quais perguntas o user faz no relatório hoje? Onde abandona? Qual a curva de profundidade? **Inclui:** mapeamento do que o user espera ver em "memória financeira" (analogia ChatGPT Memories). | 1 semana | — |
| 3.B | Spike de design — RAG over E5 JSON + Decision aggregate + Suggestions + Goal + workspace settings, com guardrails metodológicos (resposta cita ADR/regra). Decisão: ChatGPT-style (livre) vs structured-prompt (slots). | 1 semana | abrir `chat-over-report-architecture` Proposto |
| 3.C | MVP chat — chat-side em `/reports/[id]` (drawer ou painel fixo), 5 intents iniciais (saldo, alocação, score, próximo passo, simulação simples), latência < 3s p50. | 2 semanas | herda 3.B |
| 3.D | Cost ceiling + telemetria — depende de [ADR-173 LLM budget hard-stop](../../adr/173-llm-budget-hard-stop-llmcalllog-populada-universal.md) (em W3 do PLATFORM_REVIEW). Métricas: intents resolvidos vs não-resolvidos, custo médio/conversa, opt-out rate. | 1 semana | herda [ADR-173] |
| 3.E | **Financial Memories surface (NOVO 2026-05-23)** — view consolidada read-first em `/workspace/memories`: "Isto sabemos sobre você" projetando `Goal` ([[ADR-073]]) + `Decision` ativas ([[ADR-136]]) + `family_members` + workspace lifestyle settings + IRPF metadata ([[ADR-157]]). Edit inline → escreve no aggregate canônico (Goal/Decision API), nunca em store paralelo. CTA primário: alimentar Fase 3.C chat com contexto explícito do user. | 2 semanas | abrir `financial-memories-surface` Proposto (leve — escopo UX projection, não nova primitiva) |

**Owner:** `financial-planner` (intent + memories taxonomy) + `product-designer` (UX 3.A + 3.E) + `senior-cto` (arquitetura RAG + projection store) + `sre-devops` (cost ceiling).

**Dependência hard:** [ADR-173 LLM budget hard-stop](../../adr/173-llm-budget-hard-stop-llmcalllog-populada-universal.md) precisa estar mergeado antes de chat (3.C) ir live em produção. **3.E (memories surface) NÃO depende de [ADR-173]** — é UX puro sobre aggregates existentes; pode ir live em paralelo a 3.A/3.B.

**Decisões abertas que entram na ADR 3.B (chat):**

1. **Escopo de ação:** chat só lê (read-only) ou pode propor Decision/Task draft para approval? Recomendação inicial: **propor draft, nunca executar** — usuário sempre confirma.
2. **Citação de fonte:** toda resposta cita o nó do relatório / ADR de origem? Recomendação inicial: **sim** — diferenciação metodológica vs Pierre genérico **e vs ChatGPT genérico**.
3. **Histórico de conversa:** persiste por workspace? Por user? Cross-device? Recomendação inicial: **persiste por workspace, encriptado** (uso futuro: aprender padrões do cliente; consumir rationale em revisões trimestrais).
4. **Multi-agent estilo Pierre (Albert/Marie/Galileu)?** Recomendação inicial: **não** — Mathoms é metodológico, não multi-personalidade. Um único copiloto especialista é mais credível para o segmento HENRY.

**Decisões abertas que entram na ADR 3.E (memories):**

1. **Edição de memória deleta evento histórico?** Não. Edit no `Goal` cria nova revisão; supersede do `Decision` segue [[ADR-136]]. Memória mostra estado atual + link "ver histórico" para auditoria.
2. **Memórias derivadas (inferidas pelo pipeline) vs declaradas (digitadas pelo user)?** Distinção visual obrigatória — derivadas têm origem rastreada (E5 analyzer); declaradas têm campo `source: user_declared`. Sem misturar.
3. **Memória pode existir fora de Goal/Decision/Workspace?** **Não** no MVP — força ancoragem em aggregate canônico. Se virar bottleneck, abrir `WorkspaceFact` aggregate em v2 (sem fazer agora).
4. **Compartilhamento com cônjuge no mesmo workspace?** **Sim por default** — multi-tenant já implica visão compartilhada. Diferenciador chave vs ChatGPT single-user.

**Pré-requisitos arquiteturais (consolidado 2026-05-23 — designer + planner convergiram):**

Antes de abrir ADR `financial-memories-surface`, **3 ADRs Proposto** precisam estar mergeadas (todas leves, escopo ≤120 linhas cada):

| ADR pré-requisito | Origem | Razão |
|---|---|---|
| `decision-source-column` | designer (pergunta de bloqueio) | Sem `source: user_declared \| user_confirmed \| system_derived` em `Decision`, ação "Confirmar derivada → declarada" vira escrita opaca; quebra audit log. Investigar se já existe; senão adicionar coluna. |
| `goal-reserva-emergencia-schema` | planner (F11 + INV1) | Hoje `reserva_emergencia` é threshold em `goals.json` rules-as-code ([[ADR-177]]), não `Goal` por workspace. Sem schema próprio, F11 não tem onde aterrissar. Impõe `meses_alvo ∈ [3, 18]`, default 6. |
| `goal-meta-objetivo-schema` | planner (F13) | Metas estruturadas (casa, educação, intercâmbio, aposentadoria do cônjuge) hoje viram `Decision` ou nada. Schema genérico com `tipo`, `custo_brl`, `data_alvo`, `prioridade`. |

**NÃO abrir** `WorkspaceFact` aggregate v2 no MVP — abstração prematura. Confirmado por planner; só revisitar se aparecer fato sem casa canônica.

**Discovery completo** (taxonomia 16 fatos × 7 categorias, INV1-5 metodológicos, 3 mockups, research questions 3.A, decisões UX D1-D5, anti-patterns):
[assets/3e-discovery-2026-05-23.md](assets/3e-discovery-2026-05-23.md)

**Critério de saída Fase 3 (refinado por PM 2026-05-23):**

- **Chat (3.C+3.D):** live em `/reports/[id]`, ≥ 5 intents resolvidos com ≥ 80% precisão, custo médio < R$ 0,30/conversa, opt-in explícito do user, sem regressão de SLA.
- **Memories (3.E):** live em `/workspace/memories` com:
  - **KR primário (utilidade percebida):** ≥ 60% dos workspaces que **abrem** a view editam ≥ 1 memória declarada na mesma sessão. Mede utilidade, não pressão de adoção.
  - **KR secundário (invariante arquitetural):** ≥ 90% das edições resolvem para aggregate canônico (Goal/Decision/family/workspace) em audit log; 0 escritas em store paralelo.
  - **Health metric (anti-Goodhart):** tempo médio entre signup e primeira interação ≤ 7 dias entre quem abre o produto 2+ vezes. Detecta descoberta orgânica vs forçada por CTA.
  - Distinção visual derivada↔declarada validada por ≥ 5 dogfood users.

> **Mudança vs versão anterior:** KR "≥ 80% workspaces ativos com ≥ 1 memória declarada em 30 dias" foi removido — base dogfood pequena tornaria denominador instável e induziria badgering (anti-padrão metodológico). Substituído pelos 3 KRs acima.

**Leading indicators (≤ 14 dias pós-launch, instrumentar antes do launch):**

1. **Open-rate da rota `/workspace/memories` ao 7º dia** entre quem abriu relatório no período (target inicial: ≥ 35% — exploração orgânica sem CTA agressivo).
2. **Edit-to-open ratio** (edições/aberturas únicas da view; target: ≥ 0,4) — distingue "olhei e fechei" de "achei útil".

Evento de telemetria obrigatório antes do launch: `memory_view_open`, `memory_edit_submit`, `memory_edit_target` (qual aggregate sofreu escrita), `memory_origin_confirmed` (derivada → declarada).

**Risco principal Fase 3:**
- **Chat:** virar muleta para usuário não ler o relatório → cai leitura profunda → cai engajamento metodológico. Mitigação: telemetria de leitura do relatório como guard-rail; se cair >20%, A/B desliga chat.
- **Memories:** virar "rascunho paralelo" desconectado dos aggregates (forma sem substância). Mitigação: edit inline obrigatoriamente escreve no aggregate canônico via API existente; gate de teste de integração em CI.
- **Coordenação cross-sprint:** A18 (`candidate`, ADR-239) introduz CRLV/apólices/FIPE — gera memórias derivadas novas no E5 (cobertura, valor de mercado). Se 3.E lançar antes de A18 estabilizar, taxonomia derivada pode mudar. **Gate:** 3.E não merge antes de A18 done. A19 (`candidate`, S_PROTECAO) projeta estado patrimonial no relatório — risco de duplicar narrativa "isto sabemos sobre você". **Coordenar com `information-architect` antes do PR de 3.E** para evitar duplicidade UX.

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
                   ├─→ Fase 3 (chat+memories) ─┼─→ Fase 4 (GTM, sub 4.B+)
                   └─→ Fase 4.A (pesquisa)  ──┘

Fase 4.A pode rodar em paralelo com 1, 2, 3.
Fase 4.B+ deve esperar 2 e 3 (pelo menos beta) para a narrativa não furar.
Sub-fase 3.E (memories) pode ir live antes de 3.C/3.D (não depende de ADR-173).
```

- **Fase 1** habilita 2, 3, 4 com dado factual.
- **Fase 2 e 3** rodam em paralelo (owners distintos), competindo por capacidade de eng.
- **Fase 3.E (memories)** é o caminho mais rápido para responder ao ChatGPT em UX percebida — destravar primeiro dentro da Fase 3.
- **Fase 4.A** roda em paralelo desde dia 1 (não depende de eng).
- **Fase 4.B-F** publica depois de Fase 2 ou 3 visíveis (mesmo beta) para narrativa ter prova.

---

## 4-bis. Mapeamento pillar→moat: como [[ADR-183]] defende contra ChatGPT Finance

Os 4 pilares já decididos em [[ADR-183]] (P1 casal, P2 método, P3 patrimônio+fiscal, P4 plano evolutivo) **defendem estruturalmente contra ChatGPT** — não precisam ser refeitos. Esta subseção é o mapeamento explícito (sem modificar a ADR; só evidencia robustez dual-frente).

> **Pedido CEO 2026-05-23:** "destacar 3 moats que ChatGPT não tem". Resposta abaixo: 3 moats principais (P1/P2/P3) + 1 bonus (P4). ADR-183 já está `Proposto` em #141; nenhuma mudança de pillar exigida — apenas evidência de leitura dupla.

| Pilar ADR-183 | Capability | Moat vs Pierre | Moat vs ChatGPT Finance |
|---|---|---|---|
| **P1 — Patrimônio do casal** | `cenarios_conjuge_analyzer` + `family_members` ([[ADR-166]]/[[ADR-167]]) | Pierre é single-user. Casal HENRY com filhos não cabe. | **ChatGPT Memories é per-conta, não per-família.** Não há "patrimônio do casal" — cada cônjuge teria que ter conta separada, sem cruzamento estruturado. Mathoms é multi-tenant nativo. **Moat #3** vs ChatGPT. |
| **P2 — Método estruturado** | rules-as-code Perini/Cerbasi/AUVP ([[ADR-143]]) + `equilibrio_cerbasi_analyzer` + `financial_score_calculator` + `config/scoring.json` | Pierre categoriza genericamente, sem rules-as-code. | **ChatGPT é LLM genérico raciocinando caso-a-caso.** Aconselhamento é estatisticamente plausível, não metodologicamente ancorado em obra brasileira. Resposta varia entre conversas; Mathoms produz score 0-1000 reproducível auditado por threshold. **Moat #2** vs ChatGPT. |
| **P3 — Patrimônio inteiro, fiscal incluso** | `irpf_analyzer` + `e16_irpf_full.schema.json` + `fiscal_parameters` BRL versionado ([[ADR-135]]/[[ADR-157]]) + `passive_income_calculator` | Pierre não tem IRPF. | **ChatGPT cobre Intuit/TurboTax (US).** IRPF brasileiro tem alíquotas progressivas, lucro presumido, PGBL/VGBL polimórfico ([[ADR-238]]), come-cotas, isenções específicas (FII, prefixados). Mathoms tem 24+ meses de domain logic fiscal BR codificado. **Moat #1** vs ChatGPT (regulatório + domain depth). |
| **P4 — Plano de ação que evolui** | `Decision` aggregate event-sourced ([[ADR-136]]) + supersedure + `suggestion_generator` + `PlanoDeAcao` section | Pierre tem alertas, não plano. | **ChatGPT Memories é textual e mutável sem auditoria.** Não há aggregate, não há supersedure formal, não há rastreabilidade temporal. Mathoms grava "decidi X em 2026-04-12, supersedido por Y em 2026-05-01 com razão Z". Auditável para planejador/contador/sucessão. **Moat bonus** vs ChatGPT. |

**Implicação para Fase 4.B (landing):** os 4 pilares já comunicam dupla diferenciação. **Não criar novo pilar "Anti-ChatGPT" — diluiria mensagem.** Refinement de copy em PR-C (`product-designer` + `gtm-strategist`) pode adicionar **uma frase por pilar** explicitando "diferente de assistente genérico" sem nomear ChatGPT diretamente. Comparativo factual público com ChatGPT — se vier — é PR de refresh em 4.E, junto com Pierre.

**O que NÃO entra como pilar (mantido de [[ADR-183]] §"Anti-personas"):**

- "Chat conversacional sobre suas finanças" como hero → continua anti-persona (curioso AI-nativo). Chat é capability, não hero. Mathoms vende plano metodológico, não novelty AI.
- "Memória que evolui com você" como pilar isolado → memories é superfície de P4 (plano evolutivo), não pilar independente.

### 4-bis.2. Sub-headlines revisadas dos 4 pilares (gtm-strategist 2026-05-23)

Refinement de copy literal para PR-C de [[ADR-183]] — uma frase por pilar fazendo diferenciação implícita vs **assistente AI genérico**, sem nomear ChatGPT/Pierre, respeitando §13 COPY_GUIDELINES. Pillars de [[ADR-183]] não mudam; ADR-183 permanece `Proposto`.

| Pilar | Sub-headline final (≤18 palavras) | Posição visual |
|---|---|---|
| **P1 hero** | "Patrimônio do casal, decidido a quatro mãos no mesmo workspace — não duas contas isoladas que se conversam." | sub-headline abaixo do nome do pilar |
| **P2** | "Aconselhamento ancorado em metodologia consagrada de planejamento patrimonial brasileiro — reprodutível, não recalculado a cada conversa." | sub-headline abaixo do nome do pilar |
| **P3** | "Patrimônio inteiro, com o lado fiscal brasileiro embutido — não só o que entra e sai da conta." | **sub-headline (versão leve)** — a frase técnica "IRPF completo, PGBL/VGBL e lucro presumido inclusos" vai como **primeiro bullet de evidência** dentro do bloco P3 (valida ICP HENRY familiarizado sem abrir bloco com jargão) |
| **P4** | "Cada decisão registrada com data, motivo e revisão — plano que evolui com auditoria, não conselho efêmero." | sub-headline abaixo do nome do pilar |

**Auditoria §13 COPY_GUIDELINES + `check_sigilo_terms`:**
- P1: passa. "Patrimônio do casal" + "decidido a quatro mãos" são verbatim §13.2.
- P2: passa. "Metodologia consagrada de planejamento patrimonial brasileiro" é verbatim §13.2.
- P3: passa. Termos técnicos neutros ("lucro presumido", "alíquotas progressivas", "PGBL/VGBL") OK.
- P4: passa. "Supersedida" foi removida (jargão ADR-136) → traduzida em "data, motivo e revisão" user-facing.

**Risco de comoditização (12-24 meses):**

| Pilar | Sobrevive ChatGPT-BR (Plus tier + Belvo/Pluggy)? | Refresh ano 2 |
|---|---|---|
| P1 | **Forte (24+m).** Multi-tenant familiar é estrutural — não copiável em 1 sprint pela OpenAI (depende de modelo de conta + LGPD + Open Finance multi-titular). Moat real. | Nenhum. Pode reforçar com "auditada juntos". |
| P2 | **Média.** "Reprodutível, não recalculado" é claim que ChatGPT pode contestar com "Memory + system prompt fixo". Diferenciação real está em **rules-as-code** ([[ADR-143]]). | Refresh: citar "regras codificadas e versionadas" se ChatGPT escalar persona financeira. |
| P3 | **Forte (12-18m), depois pressionado.** IRPF é moat regulatório duro. Se OpenAI integrar com player BR (improvável <18m), pressiona. | Refresh: destacar "PGBL/VGBL polimórfico + come-cotas + isenções FII" — domínio que escala por tempo de codificação, não compute. |
| P4 | **Fraca em prosa, forte em prova.** "Memories evoluem" é exatamente o que OpenAI vai comunicar. Auditabilidade é o diferencial real — já capturado na frase revisada ("data, motivo e revisão"). Mas precisa de **prova visível** (3.E live) antes da landing publicar. | Sincronizar PR-D landing com 3.E launch para P4 ter prova factual. |

**Sinal verde para PR-C avançar** — 4 frases auditadas, ordem visual definida (P3 como sub-headline leve + bullet técnico), nenhuma nova ADR exigida. Coordenação: reviewer da lane A11.w5 (paused) valida vocabulário canônico antes de PR-C ir para review (sequência operacional já em [[ADR-183]] §"Sequência operacional pós-merge").

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

**Fase 3 (chat + memories):**
- Chat: ≥ 70% intents resolvidos sem fallback, custo médio < R$ 0,30/conversa, ≥ 40% dos relatórios abertos no trimestre tiveram ≥ 1 interação chat, opt-out < 15%.
- Memories: ≥ 80% workspaces ativos com ≥ 1 memória declarada em 30 dias, edit→aggregate sem corrupção (audit log limpo), ≥ 5 dogfood users validam clareza derivada↔declarada.

**Fase 4 (GTM):** ≥ 30% signups vindos de canal pago/conteúdo, CAC payback < 6m, NPS HENRY > 60, ≥ 3 parcerias CFP/contador.

**Sinais de alarme (revisar plano):**

*Pierre / mercado brasileiro:*
- Pierre lança feature de cônjuge/sucessão → Fase 4 deve acelerar 4.B com "casal" como hero ainda mais cedo.
- BCB acelera fase de investimentos OFB para Q3 2026 → janela de parser fechando, agregador entra como P0 (fora deste plano, mas contexto).
- CloudWalk anuncia M&A com banco/seguradora → Pierre ganha distribuição de cliente premium; reposicionar Fase 4 para enterprise/family-office mais cedo.

*ChatGPT Finance / mercado global:*
- **OpenAI anuncia parceria com Belvo/Pluggy** ou expansão Plaid-Brasil → janela ChatGPT-BR fechando de 18 para 6-9 meses. Acelerar 3.E (memories) e 3.C (chat) em sprint paralela; soft launch da landing 4.B com pillar P3 (fiscal) reforçado.
- **OpenAI libera Personal Finance no Plus tier (US$20)** → comoditização de pricing premium. Reavaliar pricing 4.C: tier base do Mathoms pode precisar reforçar **profundidade horizontal** (P3) e **vertical** (P4) na percepção, não só preço.
- **ChatGPT integra agente CFP/contador via persona/GPT custom público** → ameaça de "persona metodológica DIY". Resposta: acelerar conteúdo metodológico 4.D + parcerias 4.F antes que mercado pondere "configurei meu GPT, não preciso de Mathoms".
- **Pierre ou competidor BR lança "ChatGPT-like memories" antes do Mathoms** → 3.E vira urgência P0. Mitigação preventiva: 3.E é a sub-fase mais barata de Fase 3 (sem dependência [ADR-173], sem novo aggregate); priorizar entrega em ≤ 4 semanas a partir do go.

---

## 7. Não-objetivos (escopo explicitamente excluído)

1. **Decisão build vs buy do agregador OFB B2B** (Pluggy / Belvo / Klavi / DIY). Plano e ADR separados, ortogonais. Razão: variáveis comerciais distintas (pricing por consent, CAC, AUM) e não condicionado à resposta a Pierre/ChatGPT.
2. **Replicar multi-agent estilo Albert/Marie/Galileu** (recomendação inicial — confirmação na ADR 3.B). Mathoms é um copiloto especialista único, não suite de personalidades. Sinalização de seriedade.
3. **Free tier R$ 0** (recomendação inicial CEO em 4.C). Atrai segmento sub-economic.
4. **Comparativo público agressivo / atacante a Pierre ou ChatGPT.** Apenas comparativo factual respeitoso baseado em capabilities documentadas (Pierre: docs.pierre.finance; ChatGPT Finance: openai.com/index/personal-finance-chatgpt).
5. **Integrar API do Pierre como agregador** (já invalidado em §1.3 — single-tenant, float, sem webhooks).
6. **Competir com ChatGPT em chat conversacional genérico sobre dados financeiros.** Não-objetivo explícito (P7+P8): Mathoms é chat **focado e metodológico sobre o seu plano**, com guardrails e citação de fonte. Generalidade conversacional (perguntar sobre fundos, ações, macro) é território onde ChatGPT vence por reasoning bruto — não vale entrar.
7. **Construir "Mathoms GPT" / persona pública em ChatGPT Store / Custom GPTs.** Não-objetivo: expõe método codificado sem captura de valor; usuário fica em superfície OpenAI. Estratégia inversa = MCP server soberano (Fase 2) onde o user vem ao Mathoms.

---

## 8. Tracks (existentes + a criar)

### 8.1 Já criados

- [docs/sprint/A11/tracks/competitor-pierre-poc.md](../../sprint/A11/tracks/competitor-pierre-poc.md) — Fase 1 spike, status `ready`.
- [docs/sprint/A11/tracks/gtm-landing-copy-rewrite.md](../../sprint/A11/tracks/gtm-landing-copy-rewrite.md) — Fase 4.B operational skeleton, status `ready`. Ancorado em [[ADR-183]] (PR-A); este é o PR-B da sequência operacional. PR-C (copy literal pelo `product-designer`) e PR-D (publicação) seguem em sessões próprias.

### 8.2 A criar (por fase, conforme avanço)

| Track sugerido | Fase | Quando criar | Owner |
|---|---|---|---|
| `mathoms-mcp-design.md` | 2.A | após Fase 1 fechar | `senior-cto` |
| `mathoms-mcp-mvp-readonly.md` | 2.B | após ADR 2.A mergeada | `senior-cto` + `sre-devops` |
| `mathoms-mcp-distribution.md` | 2.C | em paralelo a 2.B | `build-vs-buy` (registry choice) |
| `chat-report-discovery.md` | 3.A (chat + memories taxonomy unificadas) | **criar agora** — output 3.A inicial em [assets/3e-discovery-2026-05-23.md](assets/3e-discovery-2026-05-23.md); falta validação de 3-5 dogfood interviews | `product-designer` + `financial-planner` |
| `chat-report-spike.md` | 3.B | após 3.A fechar | `senior-cto` + `financial-planner` |
| `chat-report-mvp.md` | 3.C | após ADR 3.B mergeada e [ADR-173] live | `senior-cto` |
| `decision-source-column.md` | 3.E pré-req #1 | após 3.A fechar; investigar Decision aggregate hoje | `senior-cto` |
| `goal-reserva-emergencia-schema.md` | 3.E pré-req #2 | após 3.A fechar; paralelo a `decision-source-column` | `financial-planner` + `senior-cto` |
| `goal-meta-objetivo-schema.md` | 3.E pré-req #3 | após 3.A fechar; paralelo a `decision-source-column` | `financial-planner` + `senior-cto` |
| ~~`financial-memories-surface.md`~~ | 3.E | **aguarda 3.A + 3 ADRs pré-req mergeadas** (PM 2026-05-23: não criar ainda) — materializar quando A20 abrir | `product-designer` + `senior-cto` |
| `gtm-segment-research.md` | 4.A | desde dia 1 (paralelo) | CEO + `product-manager` |
| ~~`gtm-landing-copy-rewrite.md`~~ | 4.B | ✅ criado (ver §8.1) — soft launch viável imediato sem comparativo + chat hero conforme [[ADR-183]] §"Dependências de gate" | CEO + `product-designer` |
| `gtm-pricing-repositioning.md` | 4.C | após 4.A | CEO + `product-manager` |

Nomenclatura segue padrão atual (`docs/sprint/<X>/tracks/<slug>.md` com frontmatter `note-track`). IDs serão definidos quando o track for materializado.

---

## 9. Atualizações deste documento

- **2026-05-08:** plano criado em `draft`. Fase 1 track materializado. Fases 2-4 descritas em alto nível, esperando dossiê da Fase 1 para refinar.
- **2026-05-08:** Fase 4.B PR-A → [[ADR-183]] mergeada como `Proposto` (#141). Fase 4.B PR-B → [`gtm-landing-copy-rewrite.md`](../../sprint/A11/tracks/gtm-landing-copy-rewrite.md) materializado em `status: ready`. Confirmado em [[ADR-183]] §"Dependências de gate" que soft launch P1+P2+P3+P4 é viável imediatamente — gate Fase 2/3 beta aplica-se apenas a comparativo (4.E) e narrativa AI conversacional. Próximos: PR-C (copy literal — `product-designer`), PR-D (publicação — CEO + designer), PR-E (flip ADR-183 para `Decidido`).
- **2026-05-23:** segunda frente competitiva incorporada — OpenAI ChatGPT Personal Finance (preview Pro tier US, mai/2026). Mudanças:
  - Título e frontmatter atualizados (mantém `id: PLAN-competitive-pierre` por compat de wikilinks); tag `area/ai-platform` adicionada.
  - **§1.4-1.6 novos:** tese estratégica dual (Pierre vs ChatGPT como vetores ortogonais com resposta convergente); diagnóstico factual ChatGPT; janela de 12-18 meses por restrição US-only/Plaid.
  - **§2 P7+P8 novos:** ChatGPT eleva expectativa de chat conversacional (P7); financial memories é primitiva de UX, não de dados (P8).
  - **§3 Fase 3:** prioridade elevada (gate de credibilidade, não nice-to-have); **sub-fase 3.E nova** (Financial Memories surface) projetando `Goal` + `Decision` + `family_members` + workspace settings em view consolidada; 3.E não depende de [ADR-173], pode ir live em paralelo a 3.A/3.B.
  - **§4-bis novo:** mapeamento explícito dos 4 pilares de [[ADR-183]] como moats vs ChatGPT (3 principais P1/P2/P3 + bonus P4); confirma que ADR-183 não precisa ser refeita — pillars são robustos dual-frente.
  - **§6:** sinais de alarme ChatGPT-specific (parceria Belvo/Pluggy, liberação Plus tier, persona/Custom GPT, memories first-mover concorrente BR).
  - **§7 não-objetivos 6+7 novos:** explicitar que não competimos com ChatGPT em chat genérico nem construímos "Mathoms GPT" na ChatGPT Store.
  - **§8 tracks:** `financial-memories-surface.md` adicionado.
  - **§10 referências externas:** OpenAI + matérias secundárias.

  **NÃO mudou:** [[ADR-183]] (pillars permanecem); Fases 1, 2, 4 (objetivos e sub-fases inalterados); decisão de manter pasta `COMPETITIVE_PIERRE/` (compat de wikilinks).

  **Próximas ações imediatas:**
  1. Invocar `product-manager` para sprint placement da sub-fase 3.E (proposta: A12 ou A13 conforme capacidade).
  2. Invocar `product-designer` + `financial-planner` em paralelo para 3.A discovery expandido (chat + memories taxonomy).
  3. Invocar `gtm-strategist` para PR-C de [[ADR-183]] — refinement de copy com "uma frase por pilar" diferenciando vs assistente AI genérico (sem nomear ChatGPT diretamente, sem alterar pillars).
- **2026-05-23 (segunda rodada — 4 especialistas em paralelo):** outputs consolidados.
  - **`product-manager`** trouxe correção factual crítica: sprint atual é **A17** (não A11/A12); A11/A12/A13 `paused`; A18/A19 `candidate` com ADRs Proposto. Reclassificou 3.E como `candidate` A20 condicional ao gate de A19 e fechamento de 3.A. KR original ("≥ 80% workspaces com 1 memória declarada em 30d") substituído por 3 KRs (utilidade percebida + invariante arquitetural + health metric anti-Goodhart) e 2 leading indicators ≤14d. Coordenação cross-sprint adicionada (A18 derivadas novas, A19 risco de duplicar narrativa "isto sabemos sobre você" — exige `information-architect`).
  - **`product-designer`** entregou discovery completo de 3.E: 8 research questions, diagrama de fluxo (3 entry points), 3 mockups baixa-fidelidade (tela principal + edit inline + estado vazio), decisões D1-D5 (rota dedicada `/workspace/memories`; lista única + glyph + procedência; CTA "Revisar derivadas" no empty; audit trail leve sem notif ativa MVP; fixar-pro-chat fica em 3.C). 3 anti-patterns. Pergunta de bloqueio levantada: `Decision.source` field — convergiu com gap arquitetural do planner.
  - **`financial-planner`** entregou taxonomia de 16 fatos em 7 categorias; 5 invariantes metodológicos (INV1-5) que devem virar testes de regressão; 6 anti-padrões (palpite macro, sentimento de mercado, tickers, performance histórica, comparação com terceiros, duplicação de Decision); **GAP arquitetural identificado** — 2 `goal_type` faltam (`reserva_emergencia`, `meta_objetivo`); recomendação contra `WorkspaceFact` v2 (abstração prematura).
  - **`gtm-strategist`** auditou e refinou 4 sub-headlines (P1-P4) contra §13 COPY_GUIDELINES + check_sigilo_terms; P3 reposicionado como sub-headline leve + bullet técnico (não jargão de abertura); risco de comoditização ano 2 mapeado (P1 forte 24m+, P2 média refresh, P3 forte 12-18m, P4 precisa prova de 3.E); sinal verde para PR-C avançar.

  **Decisões senior-cto pós-rodada (1 rodada, anti-loop):**
  - **3 ADRs pré-requisito de 3.E** adicionadas a §3 Fase 3: `decision-source-column`, `goal-reserva-emergencia-schema`, `goal-meta-objetivo-schema`. Sem essas mergeadas, ADR `financial-memories-surface` não abre.
  - **NÃO abrir** `WorkspaceFact` v2 (confirmado planner).
  - **NÃO alterar** [[ADR-183]] (4 pillars permanecem; refinement vive em PR-C).
  - **3.A track** vira `chat-report-discovery.md` unificado (chat + memories taxonomy) — economia de 1 track.
  - **Sprint placement 3.E:** `candidate` A20 (não A12/A13 obsoletos); 3.A começa agora async ao trabalho de A17/A18.
  - **Artefato preservado:** [assets/3e-discovery-2026-05-23.md](assets/3e-discovery-2026-05-23.md) consolida discovery completo (mockups, taxonomia, invariantes, research questions, pré-requisitos).

  **Próximas ações imediatas (próxima sessão):**
  1. `senior-cto` ou `product-manager` materializa `chat-report-discovery.md` em `docs/sprint/A17/tracks/` (ou nova pasta `_unscheduled/` se A17 não acomodar). Owner: `product-designer` + `financial-planner` para 3-5 dogfood interviews validando research questions §6 do asset.
  2. `senior-cto` abre `decision-source-column` ADR Proposto investigando schema atual.
  3. `financial-planner` + `senior-cto` abrem `goal-reserva-emergencia-schema` + `goal-meta-objetivo-schema` ADRs Proposto em paralelo.
  4. PR-C de [[ADR-183]] avança com `product-designer` escrevendo copy literal contra 4 sub-headlines auditadas.

Próxima revisão prevista: após dogfood interviews da 3.A (estimado ≤2 semanas) **ou** ao lançamento do ChatGPT Personal Finance para Plus tier — o que vier primeiro. Atualizar `last_review` + `status: in_progress` + `adrs_canonical` quando a primeira ADR mergear.

---

## 10. Referências

### Internas

- [Análise CEO 2026-05-08 (origem deste plano)](../../sprint/A11/tracks/competitor-pierre-poc.md) — track Fase 1
- [PLATFORM_REVIEW](../PLATFORM_REVIEW/_README.md) — sprint A11, ADR-173 LLM budget hard-stop é dependência da Fase 3
- [CLAUDE.md §"Política operacional — ADR Proposto antes de PR P0/P1"](../../../CLAUDE.md) — protocolo de ADR Proposto
- [docs/reference/ARCHITECTURE.md](../../reference/ARCHITECTURE.md) — domain glossary, stages, layers
- [ADR-073 Goals como entidade versionada](../../adr/073-goals-como-entidade-versionada-nao-config-estatico.md) — substrato de memórias declaradas
- [ADR-090 Decimal Money](../../adr/090-decimal-money.md) — invariante de moeda
- [ADR-111 Stateless rigoroso](../../adr/111-stateless-rigoroso-padrao-e-gate-empirico-a6f6.md) — invariante de runtime
- [ADR-136 Decision aggregate event-sourced](../../adr/136-decision-aggregate-event-sourced-com-supersede.md) — substrato de memórias de decisão
- [ADR-141 Goal alocação alvo v2](../../adr/141-goal-alocacao-alvo-schema-v2-7-classes-auvp.md) — F9/INV5 das memórias
- [ADR-143 Methodology as Code](../../adr/143-docsmethodology-e-rules-as-code-sprint-a76.md) — moat metodológico
- [ADR-157 Schema IRPF completo](../../adr/157-schema-irpf-completo-stage-extract-irpf-full.md) — F14 das memórias + moat P3 vs ChatGPT
- [ADR-173 LLM Budget Hard-Stop](../../adr/173-llm-budget-hard-stop-llmcalllog-populada-universal.md) — dependência Fase 3.C/3.D (NÃO 3.E)
- [ADR-175 Prompt Injection Defense](../../adr/175-prompt-injection-defense-em-camadas-sanitize.md) — base para Fase 2.D
- [ADR-177 Thresholds metodológicos](../../adr/177-thresholds-e-referencias-metodologicas-como.md) — F11/INV1 ancoragem
- [ADR-178 Risk aggregate workspace-scoped](../../adr/178-risk-aggregate-workspace-scoped.md) — F6/F15 das memórias
- [ADR-183 Landing positioning pillars](../../adr/183-landing-positioning-pillars-2026.md) — pillars dual-frente (Pierre + ChatGPT)
- **[Asset discovery 3.E 2026-05-23](assets/3e-discovery-2026-05-23.md)** — taxonomia + INV1-5 + mockups + research questions consolidados (output de 4 especialistas)

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

### Externas (ChatGPT Personal Finance / contexto)

- [OpenAI — A new personal finance experience in ChatGPT (anúncio oficial, mai/2026)](https://openai.com/index/personal-finance-chatgpt/)
- [TechCrunch — OpenAI launches ChatGPT for personal finance (Plaid integration, Hiro acquisition)](https://techcrunch.com/2026/05/15/openai-launches-chatgpt-for-personal-finance-will-let-you-connect-bank-accounts/)
- [American Banker — Personal finance tools for ChatGPT Pro users](https://www.americanbanker.com/news/openai-launches-personal-finance-tools-for-chatgpt-pro-users)
- [MacRumors — ChatGPT financial accounts for budgeting](https://www.macrumors.com/2026/05/15/chatgpt-personal-finance/)
- [9to5Mac — New personal finance features for ChatGPT customers](https://9to5mac.com/2026/05/15/openai-just-released-new-personal-finance-features-for-chatgpt-customers/)
