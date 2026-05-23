---
id: ADR-264
type: adr
title: "Goal type META_OBJETIVO — schema genérico para metas estruturadas (casa, educação, intercâmbio, aposentadoria do cônjuge) (Fase 3.E pré-req)"
status: Proposto
phase: A17.competitive-pierre-3e-prereq
date: "2026-05-23"
relates_to:
  - "[[ADR-073]]"
  - "[[ADR-136]]"
  - "[[ADR-143]]"
  - "[[PLAN-competitive-pierre]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 264"
  - "Goal meta objetivo"
tags:
  - area/domain
  - area/methodology
  - area/persistence
  - status/proposto
  - type/adr
---

# ADR-264 — Goal type META_OBJETIVO

**Status:** Proposto • **Data:** 2026-05-23 • **Relaciona** [[ADR-073]] (Goal versionado), [[ADR-136]] (Decision event-sourced), [[ADR-143]] (methodology = code), [[PLAN-competitive-pierre]] (Fase 3.E F13).

## Contexto

Sub-fase **3.E — Financial Memories surface** ([[PLAN-competitive-pierre]] §3) inclui F13 da taxonomia do `financial-planner` ([asset 3e-discovery-2026-05-23.md §1](../plan/COMPETITIVE_PIERRE/assets/3e-discovery-2026-05-23.md)):

> **F13 — Metas estruturadas com horizonte e custo** (casa, educação dos filhos, intercâmbio, aposentadoria do cônjuge). Categoria: Metas estruturadas. Origem: declarada. Aggregate: `Goal` tipo `meta_objetivo` (**proposto — não existe hoje**).

### Estado atual

Tipos válidos atuais ([[ADR-073]] + cutover [[ADR-180]]):

- `INDEPENDENCIA_FINANCEIRA` — meta de IF (renda passiva + horizonte + custo de vida alvo).
- `APORTE_MENSAL` — meta de aporte recorrente.
- `DOLARIZACAO` — meta de exposição USD.
- `ALOCACAO_ALVO` — meta de alocação por classes.

**Não há goal_type genérico para metas estruturadas pontuais** (casa, educação, intercâmbio, aposentadoria do cônjuge separada da IF do titular). Hoje essas metas viram:

1. **`Decision` aggregate** ([[ADR-136]]) — funciona se o user "decide pagar X reais por mês para Y", mas `Decision` é ato, não objetivo. Categoria é "decisão de plano de ação", não "memória de meta estruturada".
2. **Nada** — user descreve em conversa/onboarding e some.

Memory surface 3.E precisa exibir card "Comprar apartamento — R$ 800.000 até 2030 — prioridade alta" como **fato declarado canônico**, não nota perdida.

### Por que goal_type genérico (não vários goal_types específicos)

Alternativa rejeitada: criar `GOAL_CASA`, `GOAL_EDUCACAO`, `GOAL_INTERCAMBIO`, `GOAL_APOSENTADORIA_CONJUGE`...

Trade-off:

- **Vários types específicos:** schema preciso, projection por type, validação rígida. Custo: explosão combinatória; cada meta nova exige ADR + schema.
- **Type genérico (META_OBJETIVO) com `categoria` interna:** schema único, projection por categoria, validação parametrizada. Vantagem: extensibilidade sem ADR nova; alinhado com como `Decision.code` funciona (string canônica + enum suave).

Decisão: **genérico com categoria interna**. Convergente com `Decision` aggregate que usa `code` String(16) + categorias suaves (em vez de proliferar tabelas).

## Decisão

Adicionar `META_OBJETIVO` ao `VALID_GOAL_TYPES`, com schema JSON genérico em `config/schemas/goal.meta_objetivo.schema.json`. Schema carrega `categoria` enum estendível (sem enum hard no DB).

### Schema canônico (params_json)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://mathoms.ai/schemas/goal.meta_objetivo.schema.json",
  "title": "Goal META_OBJETIVO params",
  "type": "object",
  "required": ["categoria", "titulo", "custo_brl", "data_alvo", "prioridade"],
  "additionalProperties": false,
  "properties": {
    "categoria": {
      "type": "string",
      "enum": [
        "casa",
        "educacao_filhos",
        "intercambio",
        "aposentadoria_conjuge",
        "carro",
        "viagem_longa",
        "negocio",
        "outro"
      ],
      "description": "Categoria de meta. Enum estendível em ADRs futuras. 'outro' aceita campo livre em titulo."
    },
    "titulo": {
      "type": "string",
      "minLength": 3,
      "maxLength": 120,
      "description": "Descrição user-facing (ex.: 'Apartamento 3 quartos São Paulo', 'Faculdade Helena')."
    },
    "custo_brl": {
      "type": "string",
      "pattern": "^\\d+(\\.\\d{1,2})?$",
      "description": "Custo total alvo em BRL (decimal string, ADR-090)."
    },
    "data_alvo": {
      "type": "string",
      "format": "date",
      "description": "Data alvo de conclusão (YYYY-MM-DD)."
    },
    "prioridade": {
      "type": "string",
      "enum": ["alta", "media", "baixa"],
      "description": "Prioridade declarada pelo casal. Influencia ordenação em cards de plano."
    },
    "prazo_metodologico": {
      "type": "string",
      "enum": ["curto", "medio", "longo"],
      "description": "Curto = ≤2a; médio = 2-7a; longo = >7a. Auto-calculado de data_alvo - hoje se omitido."
    },
    "compartilhada_com_conjuge": {
      "type": "boolean",
      "default": true,
      "description": "Default true (multi-tenant casal). False para meta individual de um cônjuge."
    },
    "rationale": {
      "type": "string",
      "maxLength": 500,
      "description": "Justificativa metodológica opcional."
    },
    "linked_decision_id": {
      "type": ["string", "null"],
      "description": "UUID de Decision (ADR-136) que originou esta meta (ex.: 'aceito Suggestion: planejar aporte para meta')."
    }
  }
}
```

### Schema canônico (derived_json)

Calculado pelo service ao criar/atualizar:

```json
{
  "type": "object",
  "required": ["aporte_mensal_necessario_brl", "anos_restantes", "viabilidade"],
  "properties": {
    "aporte_mensal_necessario_brl": {
      "type": "string",
      "pattern": "^\\d+(\\.\\d{1,2})?$",
      "description": "Aporte mensal para atingir custo_brl em data_alvo, dada premissa de retorno real (default 4% real ao ano para metas de longo prazo, 0% para curtas)."
    },
    "anos_restantes": {"type": "number", "minimum": 0},
    "viabilidade": {
      "type": "string",
      "enum": ["viavel", "exige_revisao", "inviavel"],
      "description": "Comparação aporte_necessario vs Goal.APORTE_MENSAL atual e fluxo livre projetado."
    },
    "conflito_com_metas": {
      "type": "array",
      "items": {"type": "string"},
      "description": "IDs de outras metas META_OBJETIVO ou INDEPENDENCIA_FINANCEIRA cujo aporte conjunto excede capacidade."
    }
  }
}
```

### Mudanças no código

1. `backend/app/models/goal.py:29-36` — adicionar `"META_OBJETIVO"` ao `frozenset`.
2. `backend/app/services/goal_service.py` — validar params; calcular `derived_json` com fórmula de aporte (fv = pv × (1+r)^n; aporte = (fv - pv)/((1+r)^n × n) para r ≠ 0, etc).
3. `config/schemas/goal.meta_objetivo.schema.json` (novo).
4. Testes em `backend/tests/services/test_goal_meta_objetivo.py`.

**Sem migration de DB** — mesmo padrão da ADR-263.

### Múltiplas metas META_OBJETIVO por workspace

Diferente dos outros goal_types (que são únicos vigentes por `(workspace_id, type)`), `META_OBJETIVO` precisa permitir **múltiplas metas simultâneas** (casa + educação + intercâmbio). Solução:

- Manter convenção `Goal.type = "META_OBJETIVO"` única no aggregate.
- Distinguir múltiplas via campo `titulo` + `categoria` em `params_json`.
- Cada meta é uma **revisão própria** do `Goal` aggregate — uma "linha vigente" por meta (não por type).

Isto exige flexibilizar a constraint do repositório `goal_repo.get_active(ws, "META_OBJETIVO")` para retornar **lista**, não singleton. Esta é a única mudança não-trivial além da frozenset; documentar no PR.

Alternativa rejeitada: tabela `workspace_goals_meta` separada. Custo (nova migration, novo repositório, novos endpoints) excede ganho (preserva sigleton de outros types).

## Consequências

### Positivas

- **F13 tem casa canônica** — Memories surface 3.E renderiza "PATRIMÔNIO E METAS" agrupando `Goal(type=META_OBJETIVO)` com cards por categoria.
- **Conflito de metas detectável** — `derived_json.conflito_com_metas` habilita Suggestion automática "sua meta de casa + IF excedem capacidade de aporte; rever horizonte ou custo".
- **Compatível com Decision** — `linked_decision_id` permite rastrear que meta nasceu de aceitar Suggestion específica (mantém event-sourcing limpo).
- **Categoria estendível** — novas categorias (`negocio`, `imovel_locacao`) entram via patch na enum + ADR de domain extension, sem nova goal_type.

### Negativas / trade-offs

- **Múltiplas linhas vigentes por type** quebra invariante atual de Goal aggregate ("único vigente por (workspace_id, type)"). Risco: services existentes que assumem singleton podem quebrar com META_OBJETIVO. Mitigação: code review + testes de regressão em todos os callers de `goal_repo.get_active`.
- **Schema "categoria" é enum suave** — adicionar nova categoria exige patch + redeploy. Aceitável dado que metas estruturadas são finitas e domain-stable.
- **Cálculo de `aporte_mensal_necessario_brl` exige premissa de retorno real.** Default 4% real ao ano é aproximação. Mitigação: documentar default no schema; permitir override via campo `retorno_real_premissa_pct` (futuro v2).

### Risco assimétrico

- **Quebra de singleton.** Mudança em invariante do aggregate exige testes amplos. Se algum service caller assumir `get_active(ws, type) → Goal | None`, e META_OBJETIVO retornar `list[Goal]`, há crash. Mitigação: assinatura específica `goal_repo.list_active(ws, type) → list[Goal]` para META_OBJETIVO; `get_active` mantém singleton para outros types.
- **Categoria "outro" é escape hatch.** Pode virar dump de metas mal categorizadas. Mitigação: telemetria — se >20% das metas viram "outro", abrir ADR de refinamento de categorias.

## Sequência operacional

1. **PR-A (esta ADR):** mergeada como `Proposto`.
2. **PR-B:** schema JSON + frozenset + service + `goal_repo.list_active` + testes. Branch: `agent/adr-264-goal-meta-objetivo/<ts>`. Owner: `senior-cto` + `financial-planner` (validação fórmula de aporte).
3. **PR-C:** UI de criação/edit em `/workspace/goals` (formulário multi-categoria).
4. **PR-D:** consumido pelo MVP de 3.E (ADR `financial-memories-surface`) — não materializado nesta ADR.

## Critério de aceite (`Proposto` → `Decidido`)

- [ ] PR-A mergeado (esta ADR).
- [ ] PR-B mergeado: `VALID_GOAL_TYPES` inclui `META_OBJETIVO`; schema JSON; service valida params e calcula derived; `goal_repo.list_active` retorna lista para META_OBJETIVO.
- [ ] ≥ 6 unit tests cobrindo: criar 3 metas simultâneas no mesmo workspace; categoria válida vs inválida; viabilidade calculada; conflito com IF; data_alvo passada; supersedure (nova revisão da mesma meta).
- [ ] Testes de regressão em todos callers existentes de `goal_repo.get_active` — singleton preservado para INDEPENDENCIA_FINANCEIRA, APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO.
- [ ] PR-C mergeado: UI permite criar/listar/editar metas estruturadas.

Promoção a `Decidido (Sprint XX.Y)` ocorre quando 3.E MVP consome este Goal type em produção com pelo menos 3 metas estruturadas criadas em base dogfood.
