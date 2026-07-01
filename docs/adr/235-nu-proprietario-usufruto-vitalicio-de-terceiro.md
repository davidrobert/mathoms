---
id: ADR-235
type: adr
title: "Classificação `nu_proprietario`: imóvel em nu-propriedade com usufruto vitalício de terceiro"
status: Decidido
phase: A16
date: "2026-05-20"
decided_at: "2026-05-20"
relates_to:
  - "[[ADR-142]]"
  - "[[ADR-143]]"
  - "[[ADR-145]]"
  - "[[ADR-186]]"
  - "[[ADR-188]]"
  - "[[ADR-199]]"
  - "[[ADR-215]]"
  - "[[ADR-216]]"
  - "[[ADR-225]]"
  - "[[ADR-227]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 235"
  - "nu-propriedade"
  - "usufruto vitalício"
  - "nu_proprietario classification"
tags:
  - area/methodology
  - area/persistence
  - area/pipeline
  - area/backend
  - area/report
  - methodology/cerbasi
  - methodology/perini
  - phase/a16
  - status/decidido
  - type/adr
---

## Contexto

[[ADR-215]] fixou o enum `classification` para imóveis com 6 valores: `residencia_principal | uso_pessoal | locado | comercial | especulacao | desconhecido`. O enum modela **uso econômico** (gera caixa? uso próprio? terreno improdutivo?) e governa três decisões críticas: (1) filtro de cap rate em [[ADR-216]] (`INVESTMENT_CLASSIFICATIONS = locado, comercial, especulacao`), (2) inclusão em `investivel_efetivo` em [[ADR-142]] (`_CLASSIFICATIONS_GERADORAS = locado, comercial` quando toggle on), (3) split cat_1/cat_2 em [[ADR-145]].

**Caso real observado (workspace dogfood `98432212-…`, 2026-05-20):** cliente é **nu-proprietário** de imóvel cujo antigo dono detém **usufruto vitalício gratuito** — usufrutuário mora sem pagar aluguel, e o cliente consolida propriedade plena ao falecimento. Hoje: zero fluxo, ilíquido por contrato civil até evento biológico, no IRPF pelo custo da nu-propriedade (deságio de 30-60% sobre valor pleno conforme expectativa de vida do usufrutuário, tabela AT-2000).

Nenhum dos 6 valores captura fielmente:

- `uso_pessoal` (a aproximação atual) — neutraliza corretamente em cap rate e IF, **mas** agrupa com "casa de praia onde filho mora" e apaga três sinais distintos: **liquidez** (uso_pessoal pode vender pleno; nu-propriedade só vende com deságio), **sucessão** (se nu-proprietário falece antes do usufrutuário, herdeiros recebem nu-propriedade onerada + ITCMD sobre nu-propriedade), e **expectativa de fluxo futuro** (vai virar gerador em horizonte estocástico).
- `especulacao` — terreno improdutivo aguardando valorização; nu-propriedade tem uso de terceiro, não é especulativa.
- `locado` / `comercial` — não há fluxo para o cliente.

**Frequência esperada na base** (estimativa qualitativa do `financial-planner`): caudal moderado — 5–15% dos workspaces em ICP de wealth-tech BR (família com patrimônio diversificado e planejamento sucessório ativo). Casos típicos: (a) compra com reserva de usufruto para pai/mãe (sucessório reverso), (b) recebimento por doação com reserva de usufruto do doador, (c) compra de imóvel onerado de terceiro. Não é caudal raro.

**Razão de abrir ADR ([[ADR-188]] policy "ADR Proposto antes de PR P0/P1"):** mudança em invariante crítico — extensão do enum `classification` toca CHECK constraints (2 tabelas), filtros em adapter, classifier, type TS, dropdown UI, prompt do parecer E6 ([[ADR-199]]). Sem ADR, vira dead code drift entre camadas.

## Decisão

Adicionar **`nu_proprietario`** ao enum `classification` em [[ADR-215]]:

```
classification ∈ {
  residencia_principal,
  uso_pessoal,
  locado,
  comercial,
  especulacao,
  nu_proprietario,          # NOVO — nu-propriedade com usufruto vitalício de terceiro
  desconhecido,
}
```

**Semântica:** ativo no patrimônio do cliente, com ônus civil (usufruto vitalício de terceiro), zero fluxo de caixa hoje, ilíquido até evento futuro condicional. Comporta-se como `uso_pessoal` em todos os filtros computacionais (não-gerador, fora de cap rate, fora de `investivel_efetivo`), **mas é entidade semântica distinta** para fins de relatório, parecer LLM e diagnóstico de liquidez.

**Categoria patrimonial:** cat_2 **não-gerador** (alinhado com [[ADR-145]] + [[ADR-142]]). Não cria categoria nova "Patrimônio ilíquido condicional" — eixo extra polui split sem ganho prático.

**Cap rate ([[ADR-216]]):** fora de `INVESTMENT_CLASSIFICATIONS`. Sem aluguel ≠ cap rate zero — é cap rate **indefinido**; não puxa média do portfolio pra baixo.

**`investivel_efetivo` ([[ADR-142]]):** invariante explícito — nu-propriedade **nunca** entra, independente do toggle `imoveis_no_if`. Conservadorismo Perini/Cerbasi: ativo que não pode ser convertido em renda passiva no horizonte do plano não financia IF.

**Sinais que o relatório deve surfaçar** (resgatados da análise do `financial-planner` e movidos para critério de aceite):

1. **Liquidez condicional.** Bucket dedicado "Ilíquido condicional" no breakdown de liquidez — não soma em "ativos disponíveis < 30 dias" nem em "líquido < 12 meses".
2. **Aviso sucessório.** Surfaçar no parecer LLM (E6, [[ADR-199]]) nota: se nu-proprietário tem dependentes, revisar seguro de vida para cobrir ITCMD da consolidação caso ele faleça antes do usufrutuário.
3. **Valor IRPF ≠ valor mercado consolidado.** UI MembersTab + relatório §Imóveis explicitam que `valor_brl` reflete custo da nu-propriedade (descontado), não o valor potencial após consolidação. Captura de `valor_mercado_consolidado` opcional fica em follow-up — mesma estrutura do `property_market_value` de [[ADR-227]].
4. **Concentração total vs renda.** Entra em "concentração imobiliária total" (denominador PL), **não** em "concentração de imóveis de renda".
5. **Parecer LLM (E6) recebe contexto explícito.** Prompt menciona nu-propriedade e instrui a **não** recomendar venda como solução de liquidez (recomendação tecnicamente errada e cara em credibilidade).

## Alternativas consideradas

**(B) Flag ortogonal `has_usufruct_of_third_party: bool` + campo opcional `expected_extinction_year: int | null` em `workspace_property_overrides`, mantendo `uso_pessoal` no enum.**
Rejeitada. Viola SRP do override: `classification` deixaria de ser axis único de decisão, surgindo espaço de estados inválidos (`flag=true ∧ classification=locado`) que exigem CHECK composto + validator no aggregate (padrão de discriminator [[ADR-186]]) — mais superfície de manutenção que (A). `expected_extinction_year` é YAGNI no JTBD atual: cliente não estima óbito do usufrutuário; produto não opera em tábuas atuariais (precisão falsa custa mais que silêncio honesto). **Ressalva do `financial-planner` preservada:** se demanda futura por projeção patrimonial condicional aparecer, ADR sucessora pode adicionar `expected_extinction_year` como campo ortogonal **opcional** sobre o enum estendido — sem recriar o enum nem reabrir esta decisão.

**(C) Não modelar; documentar mapeamento `uso_pessoal` + anotação em `<workspace>/notes/` ([[ADR-143]]).**
Rejeitada. Perde sinal estruturado para o parecer LLM ([[ADR-199]] lê schema, não notes free-text), impossível surfaçar em ratios e relatório, e o caso não é raro (5–15% ICP). Erosão semântica que vira dívida técnica em diagnóstico de liquidez e sucessão.

## Plano de implementação (PR de fechamento)

**Migration Alembic** (`adr235nupropriet1`):
- `up`: drop + recreate CHECK em `workspace_property_overrides.classification` (Postgres não permite editar CHECK in-place; `property_identity` não tem coluna `classification`, só a tabela de overrides). Sem backfill — rows existentes preservadas.
- `down`: pre-down guard valida que nenhuma row tem `nu_proprietario` (raise `RuntimeError` se houver, evita data loss silencioso); recriar CHECK sem o valor novo.

**Call-sites obrigatórios** (todos identificados; nenhum exhaustive switch, comportamento default = "não-investidor"):
- `backend/app/models/property_identity.py:31` — Enum/Literal.
- `pipeline/domain/services/patrimonio_imovel_classifier.py:19` — `CLASSIFICATION_NU_PROPRIETARIO`; **não** entra em `_CLASSIFICATIONS_GERADORAS`.
- `pipeline/domain/services/real_estate_metrics.py:18` — `INVESTMENT_CLASSIFICATIONS` permanece sem `nu_proprietario`.
- `backend/app/services/real_estate_adapter.py:131,156,169` — literais permanecem; nu-propriedade cai no else (`origin="none"`). Teste explícito.
- `frontend/src/lib/api/properties.ts:10` — union type estendida.
- `frontend/src/app/(app)/config/ResidenciaSection.tsx:18` — opção dropdown com label "Nu-propriedade (usufruto vitalício)" + tooltip explicando consolidação futura.

**ADRs atualizadas no mesmo PR** (extensão, não supersedure): [[ADR-215]] §1 inclui `nu_proprietario`; [[ADR-142]] declara invariante "nu_proprietario nunca em `investivel_efetivo`"; [[ADR-145]] documenta nu-propriedade em cat_2 não-gerador; [[ADR-216]] explicita exclusão do denominador de cap rate. [[ADR-199]] (parecer LLM): prompt + golden + eval atualizados.

## Riscos

- **Schema evolution downstream** ([[ADR-188]]): readers exhaustive (TS `never`, Python `match`) falham hard com valor novo. Auditoria: backend usa whitelist literal `in (...)`, frontend não tem `switch` exhaustive sobre `Classification`. Risco baixo, mas adicionar CI gate `dev/check_classification_exhaustive.py` que falha se algum `switch (classification)` aparecer sem `default`.
- **Rollback inseguro.** Workspace que adotou `nu_proprietario` em produção bloqueia migration `down` (CHECK rejeita). Migration `down` valida pre-down (vide plano) — falha louder em vez de data loss silencioso.
- **LLM/E6 cego ao caso.** Prompt menciona classifications conhecidas; sem update + golden + eval, modelo trata como `desconhecido` e regride recomendações. Item obrigatório no critério de aceite.

## Critério de aceite (PR de Decidido)

1. Migration up/down aplica + reverte limpo em DB de teste; pre-down guard funcional.
2. `nu_proprietario` em `CLASSIFICATION_*` constants (backend + classifier), type TS, dropdown UI.
3. Testes de paridade com `uso_pessoal`: `tests/unit/pipeline/test_split_imoveis_with_overrides.py`, `tests/test_real_estate_metrics.py`, `tests/unit/pipeline/test_patrimonio_calculator.py` cobrem invariantes (fora de geradores, fora de `INVESTMENT_CLASSIFICATIONS`, fora de `investivel_efetivo`).
4. Teste E2E `@critical`: usuário muda classification de imóvel para `nu_proprietario` via UI → relatório reflete cat_2 não-gerador, fora de cap rate, fora de IF.
5. [[ADR-215]] / [[ADR-142]] / [[ADR-145]] / [[ADR-216]] atualizadas no mesmo PR (cross-doc invariants).
6. Prompt + golden + eval do parecer E6 ([[ADR-199]]) atualizados; cliente com nu-propriedade gera recomendação sem "venda este imóvel ocioso".
7. Snapshot OpenAPI regerado (`make update-openapi-snapshot`) — codegen propaga.
8. Entrada no [docs/CHANGELOG.md](../CHANGELOG.md) citando ADR-235.
9. CI gate `dev/check_classification_exhaustive.py` adicionado a [.pre-commit-config.yaml](../../.pre-commit-config.yaml).

## Não-objetivos (escopo explícito)

- `expected_extinction_year`, modelagem de cenário condicional pós-consolidação, alertas de extinção, tábua atuarial AT-2000 / IBGE, simulação de Monte Carlo.
- `valor_mercado_consolidado` separado de `valor_brl` IRPF (cabe em follow-up unificado com [[ADR-227]] §FU-3 — mesma raiz: separar valor histórico/IRPF de valor de mercado livre).
- Sub-bucket "Patrimônio ilíquido condicional" como categoria nova em [[ADR-145]] — rejeitado neste escopo (cat_2 não-gerador absorve).

## Follow-ups (post-Decidido, fora deste PR)

- **FU-1 · `valor_mercado_consolidado` para nu-propriedade.** Estender `property_market_value` ([[ADR-227]]) para captura opcional do valor pleno futuro (user-declared, conservador). Sinaliza salto patrimonial esperado sem prometer precisão atuarial.
- **FU-2 · Aviso de seguro de vida no parecer E6.** Heurística: se workspace tem `classification = nu_proprietario` em ≥1 imóvel e `family_members` indica dependentes, parecer recomenda revisar cobertura para ITCMD da consolidação.
- **FU-3 · Eventual `expected_extinction_year` se demanda materializar.** Critério: ≥10 workspaces solicitando captura. Reabre via ADR sucessora — não esta.
