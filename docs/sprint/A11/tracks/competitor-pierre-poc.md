---
id: TRACK-competitor-pierre-poc
type: track
title: "Track Competitor POC — Pierre Finance API + MCP benchmark"
sprint: A11
status: ready
created_at: "2026-05-08"
consumed_at: null
agent_role: senior-cto + build-vs-buy + product-manager
tags:
  - type/track
  - sprint/a11
  - status/ready
  - area/strategy
  - area/openfinance
  - methodology/build-vs-buy
---

# Track Competitor POC — Pierre Finance API + MCP benchmark

> **Lane ID:** competitor-pierre-poc
> **Branch prefix:** `agent/competitor-pierre-poc/*`
> **Depende de:** —
> **Paralelo com:** qualquer lane (não toca código produtivo)
> **Conflita com:** outra sessão `agent/competitor-pierre-poc/*` ativa
> **Onda:** independente (recon estratégico)
> **Sprint:** A11
> **Time-box:** 2-3 dias (≤16h de eng), ~R$120 de custo de assinatura
> **Owner sugerido:** orquestrador `senior-cto` + delegação a `build-vs-buy` para análise final
> **Fonte de verdade das regras:** [CLAUDE.md](../../../../CLAUDE.md)

---

## 1. Objetivo

Conduzir um **POC de reconhecimento competitivo** sobre [Pierre Finance](https://lp.pierre.finance/) (CloudWalk, lançado 2025-07; 165k usuários; R$ 800 mi AUM) via assinatura paga **Pro (R$ 39/mês)**, exercitando **REST API** e **MCP Server** com a conta pessoal do CEO conectada por Open Finance Brasil. Output: dossiê factual + ADR `Proposto` de competitor analysis + recomendação binária para o roadmap.

**O POC NÃO é tentativa de adotar Pierre como agregador para o Mathoms.** A doc de API ([docs.pierre.finance/api-services/authentication](https://docs.pierre.finance/api-services/authentication)) já invalida esse caminho — uma API key = uma assinatura = um end-user; não há flow programático multi-tenant. O POC é exclusivamente para **medir a barra do concorrente** e **calibrar o roadmap Mathoms**.

---

## 2. Hipóteses a testar

| # | Hipótese | Como falsifica |
|---|----------|----------------|
| H1 | Pierre tem cobertura OFB superior ao que conseguiríamos via parser-only no curto prazo (>10 FIs com 1 clique vs ~6 parsers reais). | Conectar ≥3 contas (1 banco tradicional, 1 digital, 1 cartão) e medir tempo de onboarding e completude de dados (saldo, tx 24m, fatura, investimentos). |
| H2 | A categorização automática do Pierre é genérica e perde contexto patrimonial (Perini/Cerbasi/AUVP). | Comparar 50 transações reais de cada conta categorizadas pelo Pierre vs nossa categorization tree (`category_template` + `workspace_category_overrides`). |
| H3 | Pierre não cobre profundidade que o Mathoms já oferece: cônjuge, IRPF, fundos exclusivos, FIIs sem OFB plena, contas no exterior, plano de ação event-sourced, score patrimonial. | Tentar replicar 5 casos de uso premium (consolidação cônjuge, simulação IF projector, plano fiscal, estresse pré-aposentadoria, alocação por classe). |
| H4 | API do Pierre é **product-led, não dev-led**: pricing acoplado a end-user, sem webhooks, sem multi-tenant, sem investments-detail. | Inventariar OpenAPI ([docs.pierre.finance/api-reference/openapi.json](https://docs.pierre.finance/api-reference/openapi.json)); verificar ausência de webhooks, multi-account ownership, position-level investments. |
| H5 | Pierre-MCP-no-Claude-Code é UX superior a Mathoms-no-app por simetria com AI nativa. Risco: usuários HENRY perderem fricção. | Conectar Pierre MCP no Claude Code via [docs.pierre.finance/editor-integration/claude-code](https://docs.pierre.finance/editor-integration/claude-code); rodar 10 perguntas patrimoniais. Comparar cobertura/precisão das respostas com nosso relatório. |

---

## 3. Plano de execução (3 dias)

### Dia 1 — Setup + assinatura + onboarding

1. CEO assina **Pierre Pro** (R$ 39/mês recorrente) em conta dedicada.
2. Conecta 3 instituições representativas via OFB (sugestão: Itaú + Nubank + BTG/XP). **Não conectar contas com saldo real significativo nem informar dados de cônjuge.**
3. Gera API key em [pierre.finance/api-key](https://pierre.finance/api-key). Armazena em `_scratch/pierre-poc-2026-05-08/.env.local` (gitignored).
4. Aciona `manual-update` para sync forçado e aguarda completude.

### Dia 2 — Inventário da API + comparação com pipeline Mathoms

1. Baixa OpenAPI completo: `curl -sL https://docs.pierre.finance/api-reference/openapi.json -o _scratch/pierre-poc-2026-05-08/openapi.json`.
2. Para cada endpoint relevante (`get-accounts`, `get-balance`, `get-bills`, `get-installments`, `get-transactions`, `get-expensive-categories`, `manual-update`, `get-open-finance-connection-flow`), exporta amostra real anonimizada para `_scratch/pierre-poc-2026-05-08/samples/`. **Aplicar `sed`/script de redação de PII antes de qualquer commit (mas o diretório já é gitignored).**
3. Mapeia shape Pierre vs shape Mathoms:
   - `accountType BANK|CREDIT|INVESTMENT|LOAN` ↔ nosso `institution_catalog` + `category_template`
   - `transactions[].category` ↔ nosso `categorization` (DB) por workspace
   - `creditData` (closingDate, dueDate, minimumPayment) ↔ nosso fatura parser (E2 banks/c6bank etc.)
   - **Money:** Pierre usa `number` (float). Mathoms usa `Decimal/Money` (ADR-090). Documenta drift.
4. Roda H1 (cobertura) + H4 (gaps de API): produz tabela em `_scratch/pierre-poc-2026-05-08/INVENTORY.md`.

### Dia 3 — MCP benchmark + relatório final

1. Conecta Pierre MCP no Claude Code:
   ```json
   { "mcpServers": { "pierre": { "url": "https://pierre.finance/mcp?apiKey=sk-..." } } }
   ```
2. Roda **10 perguntas patrimoniais padronizadas** (lista em §4) tanto no Pierre-MCP quanto no relatório Mathoms (`/reports/[id]`). Anota:
   - Precisão (acerta vs. erra vs. ambíguo)
   - Profundidade (cita metodologia? número certo? cenário?)
   - Latência percebida
3. Cancelar assinatura Pierre antes do fim do mês para evitar cobrança recorrente. Marca em calendário.
4. Escreve **dossiê final** em `_scratch/pierre-poc-2026-05-08/REPORT.md` com:
   - H1-H5 confirmadas/falsificadas com evidência citada
   - 3 a 5 capabilities do Pierre que **deveríamos imitar/responder**
   - 3 a 5 gaps do Pierre que **deveríamos amplificar como diferencial**
   - Recomendação binária: (A) acelerar agregador OFB B2B (Pluggy/Belvo/Klavi/DIY) ou (B) dobrar parser + métodos sem agregador.
5. Abre **ADR `Proposto`** em `docs/adr/NNN-competitor-analysis-pierre.md` (próximo ID disponível) com sumário da decisão recomendada — **não decide build vs buy do agregador aqui**; isso é ADR separada que herda desta.

---

## 4. As 10 perguntas patrimoniais padrão (benchmark)

Para Hipótese H5. Cobre Perini (renda passiva) + Cerbasi (equilíbrio) + AUVP (alocação) + premissas BR (IRPF, INSS, RTB).

1. "Qual é minha taxa de poupança real (líquida) dos últimos 12 meses descontando aportes em previdência?"
2. "Se eu mantiver o ritmo atual, em quantos anos atinjo independência financeira pela regra dos 25× ou 300 (Perini)?"
3. "Onde estou desbalanceado vs alocação alvo (40 RF / 30 RV / 20 FII / 10 USD)?"
4. "Quanto perdi em IR no ano por não ter declarado X compensação de prejuízo em RV?"
5. "Minha reserva de emergência cobre quantos meses do meu padrão atual? Qual é o gap?"
6. "Quanto da minha despesa é fixa, variável e sazonal? Qual o risco se eu perder a renda principal por 3 meses?"
7. "Qual cartão de crédito tem o pior carry-trade (juros pagos vs renda da reserva)?"
8. "Devo amortizar o financiamento imobiliário ou manter aplicado no Tesouro IPCA+?"
9. "Considerando minha idade e dependentes, qual seguro de vida (capital segurado) faz sentido pelo método Cerbasi?"
10. "Liste meus 5 maiores 'Mathoms' (assinaturas/gastos recorrentes que não trazem retorno funcional)."

---

## 5. NÃO-faça

- **NÃO** integrar API do Pierre em código produtivo do Mathoms — invalidado pela arquitetura single-tenant.
- **NÃO** subir API key em git, mesmo gitignored — só em `_scratch/<dir>/.env.local`.
- **NÃO** decidir build-vs-buy do agregador OFB neste track — esse é ADR separada (próximo passo recomendado).
- **NÃO** linkar dados reais do CEO em fixture, exemplo ou commit — `dev/check_forbidden_paths.py` deve continuar verde.
- **NÃO** estender este track para >3 dias — se H1-H5 sair inconclusivo, fecha com "inconclusivo + razão" e escala em ADR; spike é spike.

---

## 6. Critério de aceite

- [ ] Assinatura Pierre Pro ativa, 3 FIs conectadas via OFB, sync confirmado.
- [ ] OpenAPI baixado + inventário em `_scratch/pierre-poc-2026-05-08/INVENTORY.md`.
- [ ] Amostras de 5 endpoints REST + 5 chamadas MCP em `_scratch/.../samples/` (anonimizado, gitignored).
- [ ] Tabela H1-H5 com falsificação/confirmação evidenciada.
- [ ] Benchmark MCP-vs-relatório-Mathoms nas 10 perguntas patrimoniais.
- [ ] Dossiê `REPORT.md` com 3-5 imitar + 3-5 diferenciar + recomendação binária.
- [ ] ADR `Proposto` aberta resumindo a recomendação.
- [ ] Assinatura cancelada antes do próximo ciclo de cobrança.

---

## 7. Próximos tracks (sugeridos, NÃO escopo deste)

A serem abertos **após** o dossiê deste track:

- **`track_aggregator-eval-pluggy-belvo-klavi.md`** — build-vs-buy formal entre [Pluggy](https://www.pluggy.ai/), [Belvo](https://belvo.com/), Klavi e DIY OFB (3-5 dias). Owner: `build-vs-buy` agent. Output: ADR `Decidido`.
- **`track_mathoms-mcp-server.md`** — design do Mathoms-as-MCP (relatório, score, plano, suggestions consultáveis por Claude/ChatGPT externo) (1 semana). Owner: `senior-cto`. Output: ADR + MVP read-only.
- **`track_chat-over-report.md`** — camada chat sobre relatório (financial-planner + product-designer). Output: ADR + mockup.

---

## 8. Referências externas

- [Pierre — landing](https://lp.pierre.finance/) — pricing, positioning
- [docs.pierre.finance — Authentication](https://docs.pierre.finance/api-services/authentication.md) — API key, sub gating
- [docs.pierre.finance — REST API](https://docs.pierre.finance/api-services/rest-api.md) — base URL, endpoints
- [docs.pierre.finance — MCP Server](https://docs.pierre.finance/api-services/mcp-server.md) — auth via apiKey query
- [docs.pierre.finance — MCP Tools](https://docs.pierre.finance/api-reference/mcp/tools.md) — getAccounts, getBalance, getTransactions etc.
- [docs.pierre.finance — Claude Code Integration](https://docs.pierre.finance/editor-integration/claude-code.md) — config para benchmark MCP
- [Exame — Pierre/CloudWalk](https://exame.com/inteligencia-artificial/pierre-assistente-de-ia-para-financas-vira-aposta-da-cloudwalk-para-crescer-no-consumo/) — contexto estratégico CloudWalk
- [Let's Money — Pierre MCP "Alexa das finanças"](https://www.letsmoney.com.br/destaque/pierre-mcp-alexa-financas/) — contexto narrativo
