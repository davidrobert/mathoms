---
id: ADR-263
type: adr
title: "Goal type RESERVA_EMERGENCIA — schema versionado por workspace ancorado em INV1 (Fase 3.E pré-req)"
status: Proposto
phase: A17.competitive-pierre-3e-prereq
date: "2026-05-23"
relates_to:
  - "[[ADR-073]]"
  - "[[ADR-143]]"
  - "[[ADR-177]]"
  - "[[PLAN-competitive-pierre]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 263"
  - "Goal reserva emergencia"
tags:
  - area/domain
  - area/methodology
  - area/persistence
  - status/proposto
  - type/adr
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
---

# ADR-263 — Goal type RESERVA_EMERGENCIA

**Status:** Proposto • **Data:** 2026-05-23 • **Relaciona** [[ADR-073]] (Goal versionado), [[ADR-143]] (methodology = code), [[ADR-177]] (thresholds metodológicos), [[PLAN-competitive-pierre]] (Fase 3.E F11 + INV1).

## Contexto

Sub-fase **3.E — Financial Memories surface** ([[PLAN-competitive-pierre]] §3) requer que F11 (reserva de emergência alvo, meses de despesa essencial) tenha **aggregate canônico** onde aterrissar. O discovery do `financial-planner` ([asset 3e-discovery-2026-05-23.md §2 INV1](../plan/COMPETITIVE_PIERRE/assets/3e-discovery-2026-05-23.md)) deixou claro:

> **INV1 — Reserva de emergência sempre ancorada em fórmula.** F11 nunca aceita valor solto (ex.: "R$ 50k de reserva"). Sempre exige `meses_alvo × despesa_essencial_mensal_brl` (último derivado de E5). Schema deve impor `meses_alvo ≥ 3` (mínimo metodológico) e `≤ 18` (acima vira hoarding). Default: 6 meses.

### Estado atual

`backend/app/models/goal.py:29-36` declara:

```python
VALID_GOAL_TYPES: frozenset[str] = frozenset({
    "INDEPENDENCIA_FINANCEIRA",
    "APORTE_MENSAL",
    "DOLARIZACAO",
    "ALOCACAO_ALVO",
})
```

`RESERVA_EMERGENCIA` **não existe** como `goal_type`. A reserva de emergência hoje vive em:

1. **`config/goals.json` rules-as-code** ([[ADR-177]]) — threshold metodológico global (ex.: 6 meses default).
2. **E5 derived** — `analise_financeira.reserva_emergencia.meses_atuais` calculado de `despesa_essencial_mensal_brl × patrimonio_liquido_acessivel`.

Falta a camada intermediária: **alvo declarado por workspace** (3-18 meses, default 6) que sobrescreve o default global e habilita memória declarada na surface 3.E.

### Por que não usar `config/goals.json` puro

`config/goals.json` é global rules-as-code (uma fonte de verdade por instância Mathoms). Workspaces diferentes têm contextos diferentes:

- HENRY estável CLT pode optar por 6 meses (default).
- HENRY PJ com renda variável pode querer 12 meses (mais conservador).
- HENRY com 2 fontes de renda independentes pode optar por 3 meses (mínimo metodológico).

`config/goals.json` não comporta override por workspace. Goals aggregate sim ([[ADR-073]] §"versionado por workspace, imutável, edição cria nova revisão").

## Decisão

Adicionar `RESERVA_EMERGENCIA` ao `VALID_GOAL_TYPES`, com schema JSON co-localizado em `config/schemas/goal.reserva_emergencia.schema.json`. Goal segue contratos existentes do aggregate ([[ADR-073]] — versionado, imutável, edit cria nova revisão, único vigente por `(workspace_id, type)`).

### Schema canônico (params_json)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://mathoms.ai/schemas/goal.reserva_emergencia.schema.json",
  "title": "Goal RESERVA_EMERGENCIA params",
  "type": "object",
  "required": ["meses_alvo", "fonte_despesa_essencial"],
  "additionalProperties": false,
  "properties": {
    "meses_alvo": {
      "type": "integer",
      "minimum": 3,
      "maximum": 18,
      "description": "Meses de despesa essencial cobertos. Mínimo 3 (chão metodológico), máximo 18 (acima vira hoarding). Default sugerido: 6."
    },
    "fonte_despesa_essencial": {
      "type": "string",
      "enum": ["e5_derived", "user_declared"],
      "description": "Origem do denominador. 'e5_derived' = média de E5.fluxo_mensal_detalhado.essenciais (default); 'user_declared' = valor declarado em params.despesa_essencial_mensal_brl_declared."
    },
    "despesa_essencial_mensal_brl_declared": {
      "type": "string",
      "pattern": "^\\d+(\\.\\d{1,2})?$",
      "description": "Decimal string (ADR-090). Obrigatório se fonte_despesa_essencial = user_declared."
    },
    "rationale": {
      "type": "string",
      "maxLength": 500,
      "description": "Justificativa metodológica opcional (ex.: 'PJ + renda variável → 12 meses por conservadorismo')."
    }
  },
  "allOf": [
    {
      "if": {"properties": {"fonte_despesa_essencial": {"const": "user_declared"}}},
      "then": {"required": ["despesa_essencial_mensal_brl_declared"]}
    }
  ]
}
```

### Schema canônico (derived_json)

Calculado pelo service ao criar/atualizar o Goal, projetando F11 derivado:

```json
{
  "type": "object",
  "required": ["valor_alvo_brl", "valor_atual_brl", "cobertura_meses_atual", "gap_brl"],
  "properties": {
    "valor_alvo_brl": {"type": "string", "pattern": "^\\d+(\\.\\d{1,2})?$"},
    "valor_atual_brl": {"type": "string", "pattern": "^\\d+(\\.\\d{1,2})?$"},
    "cobertura_meses_atual": {"type": "number", "minimum": 0},
    "gap_brl": {"type": "string", "pattern": "^-?\\d+(\\.\\d{1,2})?$"},
    "despesa_essencial_mensal_brl": {"type": "string", "pattern": "^\\d+(\\.\\d{1,2})?$"},
    "source_e5_run_id": {"type": ["string", "null"], "description": "Run id de E5 consumido (null se fonte_despesa_essencial=user_declared)."}
  }
}
```

### Mudanças no código

1. `backend/app/models/goal.py:29-36` — adicionar `"RESERVA_EMERGENCIA"` ao `frozenset`.
2. `backend/app/services/goal_service.py` (ou equivalente) — validar `params_json` contra novo schema; calcular `derived_json` consumindo E5 quando `fonte_despesa_essencial=e5_derived`.
3. `config/schemas/goal.reserva_emergencia.schema.json` (novo).
4. Testes unitários em `backend/tests/services/test_goal_reserva_emergencia.py`.

**Sem migration de DB** — Goal aggregate aceita novo `type` via frozenset ([[ADR-073]]). Schema JSON é validação aplicacional, não constraint de DB.

### Integração com [[ADR-177]] threshold metodológico

`config/goals.json` continua sendo **fallback global** quando workspace não tem Goal RESERVA_EMERGENCIA criado. Resolver canônico:

```python
def resolve_reserva_emergencia_meses(workspace_id: str, session: Session) -> int:
    goal = goal_repo.get_active(workspace_id, "RESERVA_EMERGENCIA", session)
    if goal:
        return goal.params_json["meses_alvo"]
    return get_global_threshold("reserva_emergencia.meses_default", default=6)
```

Padrão idêntico ao resolver `categorization` ([[ADR-137]]) e demais — workspace override sobrepõe global.

## Consequências

### Positivas

- **F11 tem casa canônica** — Memories surface 3.E pode ler `Goal(type=RESERVA_EMERGENCIA)` diretamente sem ad-hoc.
- **INV1 enforçada por schema** — JSON Schema `minimum: 3, maximum: 18` impede valor solto.
- **Versionamento + audit trail** — toda mudança em `meses_alvo` cria nova revisão (ADR-073), apareceu no histórico do edit inline da memory (mockup 2 do designer).
- **Compatível com [[ADR-090]]** — `despesa_essencial_mensal_brl_declared` e `valor_alvo_brl` são decimal strings.
- **Sem migration** — `Goal.type` é String(64); aceita "RESERVA_EMERGENCIA" sem mexer em schema de DB.

### Negativas / trade-offs

- **Mais um goal_type para manter** — service de goals ganha mais um branch de validação. Mitigação: dispatch por dict de validators (já é padrão se ALOCACAO_ALVO está implementado assim).
- **`fonte_despesa_essencial=user_declared` desconecta do pipeline** — user pode declarar despesa essencial irrealista (R$ 1.000/mês quando pipeline calcula R$ 12.000/mês). Mitigação: UI mostra "Você declarou R$ X; calculamos R$ Y dos extratos. Diferença significativa." Decisão final é do user.
- **Default 6 meses é convenção** — não bate exatamente com nenhuma das 3 metodologias canônicas (Perini sugere ~12, Cerbasi 6, AUVP varia). 6 é mediana razoável. Mitigação: rationale no schema permite user justificar valor escolhido.

### Risco assimétrico

- **Schema é interface entre Goal aggregate e Memories surface.** Mudança breaking exige versão v2 (não amend v1). Mitigação: schema dentro de `config/schemas/` segue padrão de versionamento já estabelecido ([[ADR-141]] tem `.v2.schema.json`).
- **`meses_alvo` máximo 18 é opinativo.** Se algum HENRY ultra-conservador quiser 24, schema bloqueia. **Aceito** — hoarding ≥ 18 meses não é metodológico; se demanda recorrente aparecer, abre ADR de relaxamento, não driblar schema.

## Sequência operacional

1. **PR-A (esta ADR):** mergeada como `Proposto`.
2. **PR-B:** schema JSON + frozenset + service + testes. Branch: `agent/adr-263-goal-reserva-emergencia/<ts>`. Owner: `senior-cto` + `financial-planner` (revisão metodológica).
3. **PR-C:** UI de criação/edit em `/workspace/goals` (sem esperar 3.E — Goal é primitivo, surface vem depois).
4. **PR-D:** consumido pelo MVP de 3.E (ADR `financial-memories-surface`) — não materializado nesta ADR.

## Critério de aceite (`Proposto` → `Decidido`)

- [ ] PR-A mergeado (esta ADR).
- [ ] PR-B mergeado: `VALID_GOAL_TYPES` inclui `RESERVA_EMERGENCIA`; schema JSON em `config/schemas/`; service valida params; derived_json calculado de E5 ou declarado.
- [ ] ≥ 5 unit tests cobrindo: schema válido / inválido (meses fora de range), fonte e5_derived com E5 ausente, fonte user_declared sem despesa, edição cria nova revisão.
- [ ] PR-C mergeado: UI permite criar Goal RESERVA_EMERGENCIA.
- [ ] [[ADR-177]] threshold default `reserva_emergencia.meses_default` continua existindo como fallback.

Promoção a `Decidido (Sprint XX.Y)` ocorre quando 3.E MVP consome este Goal type em produção.
