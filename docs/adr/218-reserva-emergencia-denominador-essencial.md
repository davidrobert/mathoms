---
id: ADR-218
type: adr
title: "Reserva de Emergência — denominador essencial, override por workspace e bandas Cerbasi/Perini"
status: Proposto
phase: A12
date: "2026-05-15"
relates_to:
  - "[[ADR-097]]"
  - "[[ADR-134]]"
  - "[[ADR-137]]"
  - "[[ADR-143]]"
  - "[[ADR-188]]"
  - "[[ADR-199]]"
  - "[[ADR-212]]"
  - "[[ADR-217]]"
supersedes: []
superseded_by: []
amended_at: ["2026-07-15"]
aliases: ["ADR 218", "reserva-emergencia-essencial", "denominador-essencial"]
tags:
  - area/report
  - area/pipeline
  - area/methodology
  - methodology/cerbasi
  - methodology/perini
  - methodology/auvp
  - phase/a12
  - status/proposto
  - breaking/schema-e5
  - type/adr
---

> **Emenda 2026-07-15 (FP-02) — ratificação parcial `financial-planner`:** o
> **denominador essencial** (núcleo desta ADR) está **vivo em produção** desde
> A28.l1 (`financial_score_calculator.py` lê `reserva.cobertura_meses =
> reserva_liquida ÷ custo_essencial_mensal`; `scoring.json` já expõe
> `custo_essencial_mensal` + `meses_alvo_por_perfil_renda`). O `financial-planner`
> ratificou essa decisão — deixá-la `Proposto` era gap de governança sobre código
> em produção. O **restante do escopo** (D1/D2 card hero+bandas duplas, D3 tabela
> `category_essentiality_template` + override, D4 rename two-phase, D5-D7
> service/reader) **permanece deferido** à lane coordenada do `score_version 2.0`
> (junto com [[ADR-328]]). Ver [§ Emenda](#emenda-2026-07-15-fp-02--ratificação-parcial-financial-planner) ao final.

## Contexto

Card `S1.reserva_emergencia` ([`ReservaEmergenciaCard.tsx`](../../frontend/src/components/report/cards/ReservaEmergenciaCard.tsx))
hoje calcula `nivel_6_meses` e `nivel_12_meses` sobre **despesa total**
(no workspace 5@5.com: R$ 41,4k/mês → alvo 6m R$ 248k; 12m R$ 497k).
Convergência das três metodologias canônicas (Cerbasi, Perini, AUVP) usa
**custo fixo essencial** como denominador (~R$ 18,5k/mês para essa
família, ≈ 44% do total → alvo 6m R$ 111k; 12m R$ 223k).

O parecer E6 do mesmo relatório mistura denominadores no texto: cita
simultaneamente "1,5 mês de despesa total" e "3,3 meses de despesa
essencial". A leitura crua mostra **inconsistência metodológica visível
ao cliente** — em fintech wealth premium, isso quebra confiança.

Três problemas concretos:

1. Denominador "total" cria alvo desnecessariamente alto (R$ 248k vs.
   R$ 111k para o caso real). Cliente subestima saúde da reserva e
   pode poupar 2× mais que o necessário, sub-alocando aporte para
   investimentos produtivos (oposto da regra Cerbasi "presente saudável,
   sobra para futuro").
2. Nenhuma família é igual. "Moradia + alimentação + saúde + transporte"
   é default Cerbasi, mas casal sem dependentes em SP urbano tem
   essencialidade diferente de família 4 pessoas no interior. **Hoje
   não há override por workspace.**
3. Bandas de meta (Cerbasi 6m vs. Perini 12m) não aparecem visualmente
   no card — usuário não sabe qual é a meta-base, qual é a meta-conforto.

## Decisão

### D1 — KPI hero passa a ser "X meses de despesa essencial"; total permanece auxiliar

Card mostra **dois números**:

- **Hero (protagonista):** `meses_cobertos_essencial` — relação
  `total_liquida / despesa_essencial_mensal`. Variant `critical/warn/success`
  computado sobre este número.
- **Auxiliar (transparência):** `meses_cobertos_total` — relação
  `total_liquida / despesa_total_mensal`. Linha abaixo, font-size menor,
  rotulado "Considerando despesa total (incluindo discricionários)".

Decisão (vs. alternativa "apenas essencial"): expor os dois preserva
auditabilidade e respeita workspaces cuja essencialidade ≈ total (raro
mas existe — frugais extremos). Render degrada limpo: se `despesa_essencial_mensal`
ausente (run antigo), card mostra só `total` com badge "Cálculo legado".

### D2 — Bandas Cerbasi (6m) e Perini (12m) ambas no progress bar

Progress bar do hero exibe **dois marcadores verticais**: linha 6m (label
"Cerbasi mínima") e linha 12m (label "Perini conforto"). Ambos sobre
**denominador essencial**. Variant computado:

- `meses_cobertos_essencial < 6` → `critical` + copy "Abaixo da reserva
  mínima — prioridade absoluta antes de qualquer aporte adicional"
  (Cerbasi).
- `6 ≤ meses_cobertos_essencial < 12` → `warn` + copy "Acima da mínima,
  abaixo da reserva-conforto — meta é destravar IF" (Perini).
- `meses_cobertos_essencial ≥ 12` → `success` + copy "Reserva consolidada
  — aporte excedente vai para classes produtivas".

Decisão (vs. alternativa "uma única banda"): expor ambas evita a falsa
escolha "6 vs. 12" e respeita que a metodologia tem **dois ciclos** —
mínima emergencial e conforto pré-IF. Sem isso, o card vira "6 OU 12" e
o cliente escolhe arbitrariamente.

### D3 — Categorias essenciais configuráveis por workspace via tabela dedicada

Essencialidade é dimensão **ortogonal** à hierarquia de categorização
([[ADR-137]]) e tem ciclo de vida próprio (PO/CFP® ajusta sem mexer em
classificação; auditoria separada; futuro pode evoluir para peso
graduado). Não reusar `category_template` adicionando coluna —
bloat semântico mais migration cascata quando essencialidade ganhar
atributos.

**Tabela nova** `category_essentiality_template`:

```sql
CREATE TABLE category_essentiality_template (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_code VARCHAR(64) NOT NULL,           -- FK → category_template.code
  eh_essencial BOOLEAN NOT NULL,
  peso_essencial NUMERIC(3,2) NOT NULL DEFAULT 1.00,  -- abre porta a "70% saúde, 50% transporte"
  justificativa TEXT,
  effective_from DATE NOT NULL,
  effective_to DATE,
  created_by VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  FOREIGN KEY (category_code) REFERENCES category_template(code) ON DELETE RESTRICT,
  UNIQUE (category_code, effective_from)
);
```

**Override por workspace** segue pattern [[ADR-137]]:

```sql
CREATE TABLE workspace_category_essentiality_override (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  category_code VARCHAR(64) NOT NULL,
  eh_essencial BOOLEAN NOT NULL,
  peso_essencial NUMERIC(3,2) NOT NULL,
  justificativa TEXT,
  effective_from DATE NOT NULL,
  effective_to DATE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  FOREIGN KEY (category_code) REFERENCES category_template(code) ON DELETE RESTRICT,
  UNIQUE (workspace_id, category_code, effective_from)
);
```

Workspace lê via `WorkspaceContext.get_essentiality_catalog(date) →
list[CategoryEssentiality]` que resolve `(template vigente, override
vigente)` no service `essentiality_resolver.py`.

**Default global (seed inicial):**

| `category_code` | `eh_essencial` | `peso_essencial` | Justificativa |
|---|---|---|---|
| `moradia` | true | 1.00 | Cerbasi/AUVP: aluguel + condomínio + IPTU + utilidades. |
| `alimentacao` | true | 0.80 | Cerbasi: 80% da despesa alimentar é supermercado/básico; restos. social entra em discricionário. |
| `saude` | true | 1.00 | Convergência — saúde não é negociável. |
| `transporte` | true | 0.50 | AUVP: 50% transporte é deslocamento ao trabalho; restante é lazer/viagens. |
| `educacao` | true | 1.00 | Cerbasi para famílias com dependentes; PO override para casais sem filhos. |
| `lazer` | false | 0.00 | Discricionário por definição. |
| `viagens` | false | 0.00 | Discricionário. |
| `assinaturas` | false | 0.00 | Discricionário (streaming, ginástica…). |
| `presentes` | false | 0.00 | Discricionário. |
| `nao_identificado` | false | 0.00 | Conservador: incertos não entram. |

Demais categorias do `category_template` default `eh_essencial: false,
peso_essencial: 0`. **`peso_essencial: NUMERIC(3,2)`** abre porta a v2
graduado sem migration de schema — v1 usa 0.00 ou 1.00.

### D4 — Two-phase rename de `nivel_6_meses` → `nivel_6_meses_total` no subschema E5

`reserva_emergencia` subschema bump major (`1.x → 2.0`). Campos novos:

```json
{
  "reserva_emergencia": {
    "version": "2.0",
    "despesa_essencial_mensal": "18581.23",
    "despesa_total_mensal": "41421.00",
    "meses_cobertos_essencial": 6.0,
    "meses_cobertos_total": 2.7,
    "total_liquida": "111487.38",
    "categorias_essenciais_aplicadas": [
      {"code": "moradia", "peso": 1.00, "fonte": "global"},
      {"code": "transporte", "peso": 0.50, "fonte": "workspace_override"}
    ],
    "composicao_liquida": {...},

    "nivel_6_meses_total": 248526.00,
    "nivel_6_meses": 248526.00,
    "nivel_12_meses_total": 497052.00,
    "nivel_12_meses": 497052.00
  }
}
```

**Janela de compat de 1 sprint:** durante a janela, payload emite os
quatro (`nivel_6_meses`, `nivel_6_meses_total`, `nivel_12_meses`,
`nivel_12_meses_total`); renderer aceita ambos. Após cutover, remoção dos
legados (`nivel_6_meses` e `nivel_12_meses` sem sufixo) em PR separado de
limpeza. Justificativa: `nivel_6_meses` sem sufixo é semanticamente
ambíguo após a mudança — em 6 meses ninguém lembra qual denominador era.

### D5 — Service puro em `pipeline/domain/services/reserva_emergencia.py`

```python
@dataclass(frozen=True)
class ReservaEmergenciaInputs:
    despesas_e4: DespesasArtifact            # E4/despesas
    essentiality_catalog: tuple[CategoryEssentiality, ...]  # resolvido pelo WorkspaceContext
    total_liquida: Money                     # de E5 já agregado
    composicao_liquida: tuple[AtivoLiquido, ...]

@dataclass(frozen=True)
class ReservaEmergenciaSnapshot:
    despesa_essencial_mensal: Money
    despesa_total_mensal: Money
    meses_cobertos_essencial: Decimal        # 1 casa
    meses_cobertos_total: Decimal
    total_liquida: Money
    categorias_essenciais_aplicadas: tuple[CategoriaAplicada, ...]
    composicao_liquida: tuple[AtivoLiquido, ...]
```

Service consome `essentiality_catalog` injetado, **não** lê DB
diretamente. Despesa essencial = `sum(despesa_categoria × peso_essencial
para cada categoria em essentiality_catalog se eh_essencial)`. Casas
decimais em `Money` ([[ADR-090]]); warnings tipados ([[ADR-097]]) para
categorias sem mapping.

### D6 — Acessor no WorkspaceContext + STATELESS_AUDIT

```python
class WorkspaceContext:
    def get_essentiality_catalog(self, as_of: date) -> tuple[CategoryEssentiality, ...]:
        """Resolve (template global, override workspace) na data dada."""
        ...
```

Singleton lazy idempotente (caching por `(workspace_id, as_of)`), mesmo
padrão de `get_artifact_store()`. Registrar em
[`docs/reference/STATELESS_AUDIT.md`](../reference/STATELESS_AUDIT.md)
§2 antes do merge da implementação.

### D7 — Schema evolution mode `warn` durante a janela; `strict` após cutover

[[ADR-212]] hook `validate_dict` em `warn` durante a janela de
two-phase rename. Goldens regeneram **apenas** os runs canônicos que
cobrem S1. Flip strict no PR de limpeza (D4) — janela 1 sprint.

**Backfill: recompute on-read** (mesmo pattern de [[ADR-217]] D6). Service
`ReservaEmergenciaReader` lê E5 antigo, computa essencial em memória
usando `essentiality_catalog` vigente na data do run. Sem migration
em massa de `pipeline_artifacts`.

## Custos & Trade-offs

- **Densidade do card.** Dois números (essencial + total) + duas bandas
  (6m + 12m) aumentam densidade visual. Mitigado: hero claro
  protagonista, auxiliar discreto, bandas com labels minimalistas.
- **Tabela nova vs. coluna em `category_template`.** Senior-cto sugeriu
  reuse; PO decidiu por tabela separada (data-engineer). Custo:
  1 tabela + 1 override + 1 service de resolução. Ganho: ciclo de vida
  independente, futuro com peso graduado sem migration de
  `category_template`, auditoria separada.
- **Two-phase rename.** Custo: 1 sprint de janela compat + 1 PR de
  limpeza. Ganho: zero ambiguidade futura.
- **`peso_essencial: NUMERIC(3,2)`.** Permite v2 graduado sem migration.
  v1 usa 0.00 ou 1.00 (boolean efetivo). Custo: marginal (1 coluna),
  ganho: porta aberta declarada.

## Alternativas consideradas

- **Reusar `category_template` com coluna `essential: boolean`** —
  senior-cto. Rejeitada por escolha PO (data-engineer ganha): essencialidade
  é ortogonal à categorização.
- **Despesa essencial em config global, sem override** — simplest, mas
  não respeita variabilidade familiar real (casais sem filhos vs.
  4 pessoas no interior). Rejeitada.
- **Mostrar apenas essencial, ocultar total** — pró: simplicidade. Con:
  perde auditabilidade, e workspaces extremos (essencial ≈ total) ficam
  sem o número "tradicional". Rejeitada.
- **Aditivo sem rename (manter `nivel_6_meses` como "total")** — pró:
  zero janela de compat. Con: ambiguidade eterna ("6 meses do quê?").
  Rejeitada (data-engineer).

## Implementação

PR (escopo amplo, single-shot):

- Migration Alembic `add_category_essentiality_template` (duas tabelas).
- `backend/app/models/category_essentiality.py` (SQLAlchemy) + repos.
- `backend/app/services/essentiality_resolver.py` (resolve global+override
  por data).
- `pipeline/domain/services/reserva_emergencia.py` (service puro).
- `WorkspaceContext.get_essentiality_catalog()` + STATELESS_AUDIT.
- Seed inicial em `dev/seed_category_essentiality.py` (script idempotente,
  **não** na migration).
- Schema E5: bump `reserva_emergencia` para `2.0` com campos novos +
  legados durante a janela.
- `pipeline/stages/e5_analyze.py` — chamar o service.
- `backend/app/services/reserva_emergencia_reader.py` (recompute on-read).
- `ReservaEmergenciaCard.tsx` — hero essencial + auxiliar total + duas
  bandas no progress.
- Console interno (futuro, [[ADR-116]]): CRUD de essencialidade. **Wave
  separada**, não bloqueia v1.
- Golden em `tests/test_e5_golden_execution.py` para o workspace 5@5.com.

**Dependências:**

- Não há bloqueio externo. Esta ADR é fundação para [[ADR-217]]
  (componente reserva do score usa `meses_cobertos_essencial`).

## Critério de aceite

- [ ] Workspace com despesa essencial = 50% da total tem
      `meses_cobertos_essencial = 2 × meses_cobertos_total`.
- [ ] Override por workspace muda `categorias_essenciais_aplicadas` com
      `fonte: workspace_override` correta.
- [ ] Card renderiza duas bandas (6m Cerbasi + 12m Perini) com labels
      visíveis em light e dark.
- [ ] Variant `critical/warn/success` calculado sobre `meses_cobertos_essencial`.
- [ ] Runs E5 antigos sem `despesa_essencial_mensal` renderizam só
      `total` com badge "Cálculo legado".
- [ ] Golden no workspace 5@5.com: `meses_cobertos_essencial ≈ 6.0`
      (R$ 111k / R$ 18,5k).

## Emenda 2026-07-15 (FP-02) — ratificação parcial `financial-planner`

Co-design `financial-planner` (2026-07-15, item FP-02 da onda R2.3) **ratificou
com ajuste (escopo dividido)**:

**Ratificado + vivo (score-side).** O denominador essencial — reserva medida
contra o **custo essencial mensal**, não a despesa total — já é comportamento de
produção (A28.l1): `financial_score_calculator.py` computa
`reserva.cobertura_meses = reserva_liquida ÷ custo_essencial_mensal`, e
`config/scoring.json` define `custo_essencial_mensal.categorias_in/out` +
`meses_alvo_por_perfil_renda` (6/12/18). Esta ADR é o **backing canônico** dessa
regra; a ratificação fecha o gap de governança (regra em produção sob ADR
`Proposto`).

**Reconciliação obrigatória com [[ADR-328]].** Um único ponto: *qual* `meses_alvo`.
O plateau do score (328) e o gatilho `success`/"excedente realocável" do card
(D1/D2 desta ADR) DEVEM referenciar o **mesmo** `meses_alvo_por_perfil_renda`. As
bandas 6m (Cerbasi) / 12m (Perini) ficam como marcadores visuais/educacionais,
mas o veredicto de "consolidada" segue o alvo do perfil — senão card ↔ score ↔
parecer se contradizem (a falha cross-superfície que o dogfood caça).

**Deferido (não flipar como pronto).** D1/D2 (card hero + bandas duplas), D3
(tabela `category_essentiality_template` + override por workspace), D4 (rename
two-phase `nivel_6_meses → _total`), D5-D7 (service/reader) **não** estão
implementados. Ficam na lane coordenada do `score_version 2.0` (com [[ADR-328]]),
que flippa esta ADR para `Decidido` no merge. A tabela `category_essentiality_template`
é refinamento **upstream** do denominador — o score lê `reserva.cobertura_meses` e
herda mudanças transparentemente; **o bump 2.0 não espera a tabela**.

Status permanece `Proposto` até essa lane aterrissar a implementação do card + tabela.
