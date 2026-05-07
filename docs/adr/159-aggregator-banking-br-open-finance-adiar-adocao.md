---
id: ADR-159
type: adr
title: "Aggregator banking BR (Open Finance) — adiar adoção até gatilhos materializarem"
status: Roadmap
date: "2026-05-04"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 159"]
tags:
  - area/multitenancy
  - area/persistence
  - area/pipeline
  - status/roadmap
  - type/adr
size_lines: 71
---

# ADR-159 — Aggregator banking BR (Open Finance) — adiar adoção até gatilhos materializarem

**Status:** Roadmap • **Data:** 2026-05-04

**Contexto:** Mathoms ingere extratos/faturas hoje via upload manual de PDF + 14 parsers determinísticos em `scripts/e2/banks/` + fallback E2-llm (Anthropic). UX exige que o usuário baixe o PDF do app do banco, frequência mensal por instituição. Cliente típico alta-renda tem 3+ bancos + corretora + 2-3 cartões. Investigação build-vs-buy 2026-05-04 (5 providers BR) avaliou substituir/complementar PDFs por aggregator Open Finance.

**Decisão (Roadmap):** Adiar adoção. PDFs continuam canônicos. Pluggy fica como **1ª escolha pré-aprovada** quando gatilhos materializarem; Belvo como 2ª. Klavi/Iniciador/certificação BACEN direta descartados pré-monetização.

**Comparativo dos providers (snapshot 2026-05-04):**

| Provider | Free tier | Prod mínimo | Coverage top-6 + invest | KYC | Tipo | Veredito |
|---|---|---|---|---|---|---|
| Pluggy | Trial 14d, 20 contas; API key dev em volume baixo (não-oficial) | R$2.500/mês (Basic) | Itaú, Bradesco, Santander, Nubank, BB, Caixa, Inter, **BTG, XP, Rico, Genial** | Email p/ trial | Híbrido regulado + scraping | 1ª escolha quando ativar |
| Belvo | Sandbox 25 links | US$1.000/mês (~R$5.500) | Top-6 só | Email sandbox; PJ prod | Híbrido | Plan B; sandbox BR "externally managed"; Belvo cortou time BR 2023-2024 |
| Klavi | Não documentado | Vendas-led | Regulado puro | PJ + contrato | Open Finance regulado | Inviável pré-PJ + ROI |
| Iniciador | Não documentado | Vendas-led | Regulado puro (ITP) | PJ + contrato | Open Finance regulado | Idem |
| BACEN direto | n/a | R$ centenas de mil + 6-12 meses cert. | n/a | Certificação BACEN | Open Finance regulado | Fora de escala MVP |

Sources: [pluggy.ai/en/pricing](https://www.pluggy.ai/en/pricing), [belvo.com/plans-and-pricing](https://belvo.com/plans-and-pricing/), [docs.pluggy.ai/connectors-coverage](https://docs.pluggy.ai/docs/connectors-coverage), [openfinancebrasil.org.br/2022/11/17/custos-do-open-finance](https://openfinancebrasil.org.br/2022/11/17/custos-do-open-finance/).

**Por que adiar agora:**

- **Trial 14 dias é curto** para validar UX completo (conectar conta → sync → reconciliar → relatório → fluxo de erro de re-login do banco). Migrar para prod pago antes do tempo é desperdício.
- **R$2.500/mês Pluggy Basic = 50× o budget** pré-monetização (3 usuários não pagantes).
- **R$5.500/mês Belvo Launch** idem.
- **Klavi/Iniciador vendas-led** + ciclo B2B + PJ + contrato = sem ROI pré-pagantes.
- 14 parsers PDF determinísticos **funcionam** e cobrem o histórico real dos 3 usuários atuais. Substituir lógica testada por dependência de 1 vendor inverte risco.

**Gatilhos para reativar (qualquer um destrava ADR de implementação):**

1. **≥5 workspaces pagantes** (MRR > R$10k justifica Pluggy Basic R$2.500/mês).
2. **≥30 conexões ativas** entre todos workspaces — modo trial/dev vira risco operacional.
3. **Quebra recorrente de parser PDF** (Itaú/Nubank atualiza app; custo de manutenção de parser > custo de aggregator).
4. **Cliente regulado/PJ pesado** que exige Open Finance regulado puro (não scraping) — reavaliar Klavi/Iniciador.
5. **Mudança de pricing/política** de Pluggy ou Belvo — monitor release notes trimestralmente.
6. **Aquisição/funding event** de algum provider que mude estabilidade (histórico: Belvo cortou time BR 2023-2024).

**Plano de adoção quando ativar (5-7 dias dev, mapeado):**

1. **`BankAggregatorClient` Protocol** em `backend/app/services/aggregator/` (não existe ainda) com `PluggyClient` como única implementação inicial. Pipeline `pipeline/stages/extract_*` **não importa Pluggy**.
2. **Output normaliza para schema E2 existente** (`config/schemas/e2.schema.json`). E3/E4/E5 não mudam. Se schema E2 não comportar (ex.: posição em ação vs transação), criar ADR adjacente sobre extensão de schema antes de implementar.
3. **Feature flag `MATHOMS_AGGREGATOR_ENABLED`** (default `False`) + override por workspace `workspaces.aggregator_enabled_override: bool | None` — padrão de `MATHOMS_USE_DB_ARTIFACTS` (ADR-106).
4. **Widget Pluggy Connect** na UI atrás da flag, ligado a 1-2 workspaces de teste antes de rollout.
5. **PDFs permanecem canônicos** — não remover parsers; aggregator é caminho B opcional.
6. **Plano de saída documentado** na ADR de implementação: lista de tabelas DB que armazenam dado de Pluggy, script `dev/export_aggregator_data.py` que cuspe JSON canônico (formato E2-extract), SLA de troca ≤3 dias.
7. **Sem dado real cliente em commit/log/fixture** — sandbox Pluggy tem credenciais teste documentadas; usar essas em fixtures.

**Não fazer (anti-patterns identificados):**

- ❌ **Substituir parsers PDF** quando ativar — destrói lógica determinística testada; amarra produto a 1 vendor. Aggregator é caminho B, PDFs continuam canônicos até aggregator provar 95%+ qualidade comparável.
- ❌ **Pluggy Basic R$2.500/mês agora** — 50× budget sem ROI demonstrado.
- ❌ **Contrato Klavi/Iniciador/Quanto/Celcoin** — ciclo de venda B2B sem ROI.
- ❌ **Certificação BACEN direta** — escala errada de fase (R$ centenas de milhares + 6-12 meses).

**Consequências:**

- ✅ Trabalho de pesquisa preservado — comparativo de 5 providers + URLs com data fica acessível em 6+ meses quando tema voltar.
- ✅ Gatilhos explícitos servem de checklist passivo de reavaliação.
- ✅ Plano de adoção mapeado reduz time-to-decision quando ativar (de "começar do zero" para "executar plano existente").
- ✅ Reversibilidade: ADR é Roadmap; mudar para `Decidido` + adicionar implementação em ADR adjacente quando ativar.
- ⚠️ Pricing dos providers pode mudar — comparativo data-stamped 2026-05-04; reavaliar URLs ao ativar.
- ⚠️ Coverage de bancos muda — Pluggy/Belvo adicionam/quebram conectores frequentemente (especialmente Nubank). Confirmar coverage atual ao ativar.
- ❌ Nenhum dev/produto entregue agora — decisão pura de adiar.

**Follow-ups (quando algum gatilho disparar):**

1. Criar ADR-XXX "Adoção de Pluggy via adapter Protocol" documentando implementação concreta + supersede parcial desta.
2. Re-rodar comparativo de pricing (URLs acima) na data de ativação.
3. Confirmar coverage atual Itaú/Nubank/BTG/XP via Pluggy connectors-coverage doc.
