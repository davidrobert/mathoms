---
id: ADR-219
type: adr
title: "Premissas Econômicas — tabela versionada, override por workspace e snapshot no E5"
status: Decidido
phase: A12
date: "2026-05-15"
relates_to:
  - "[[ADR-097]]"
  - "[[ADR-116]]"
  - "[[ADR-134]]"
  - "[[ADR-135]]"
  - "[[ADR-137]]"
  - "[[ADR-143]]"
  - "[[ADR-188]]"
  - "[[ADR-199]]"
  - "[[ADR-212]]"
  - "[[ADR-217]]"
  - "[[ADR-220]]"
supersedes: []
superseded_by: []
aliases: ["ADR 219", "premissas-economicas-versionadas", "economic-assumptions-table"]
tags:
  - area/pipeline
  - area/backend
  - area/methodology
  - methodology/perini
  - methodology/auvp
  - phase/a12
  - status/decidido
  - type/adr
---

## Contexto

APP_B (Premissas Econômicas) é onde toda a **auditabilidade fiduciária**
do relatório aterrissa: sigma do Monte Carlo, retorno esperado por classe
AUVP, IPCA/Selic projetadas. Revisão card-a-card 2026-05-15 detectou:

- `if_monte_carlo.sigma_usado` referenciado no inventário, **ausente do
  E5** (zero ocorrências).
- Não existe tabela canônica de retorno+sigma por classe AUVP.
  [[ADR-135]] `market_rates` cobre **câmbio + indexadores** (CDI, IPCA,
  Selic, USD/BRL), não retorno editorial por classe.
- S7 (Independência Financeira) emite cone p10/p50/p90 sem expor as
  premissas que o geraram → **caixa-preta** num relatório premium B2B2C
  com persona Perini/Cerbasi/AUVP ([[ADR-199]]). Insustentável para
  revisão de planejador CFP®.

Sem decisão escrita, [[ADR-217]] (score, componente `diversificacao_auvp`)
e [[ADR-220]] (parecer, `patrimonio_alvo` IF) calculam sobre números
mágicos. **Esta ADR é fundação para os outros três P0.**

## Decisão

### D1 — Tabela global `economic_assumptions` + override por workspace

Pattern consistente com [[ADR-135]] (`fiscal_parameters`/`market_rates`)
e [[ADR-137]] (`category_template`/`workspace_category_overrides`).
Duas tabelas separadas:

```sql
CREATE TABLE economic_assumptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  effective_from DATE NOT NULL,
  effective_to DATE,
  classe_auvp VARCHAR(40) NOT NULL,        -- FK → economic_asset_class.code (D2)
  retorno_real_esperado_pct_anual NUMERIC(6,3) NOT NULL,
  sigma_anual_pct NUMERIC(6,3) NOT NULL,
  fonte TEXT NOT NULL,
  created_by VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  FOREIGN KEY (classe_auvp) REFERENCES economic_asset_class(code) ON DELETE RESTRICT,
  UNIQUE (classe_auvp, effective_from)
);

CREATE TABLE workspace_economic_assumptions_override (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  classe_auvp VARCHAR(40) NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE,
  retorno_real_esperado_pct_anual NUMERIC(6,3) NOT NULL,
  sigma_anual_pct NUMERIC(6,3) NOT NULL,
  fonte TEXT NOT NULL,
  justificativa TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  FOREIGN KEY (classe_auvp) REFERENCES economic_asset_class(code) ON DELETE RESTRICT,
  UNIQUE (workspace_id, classe_auvp, effective_from)
);
```

Decisão (vs. alternativa "tabela única com `workspace_id NULL = global`"):
manter consistência com [[ADR-135]]/[[ADR-137]] vence — três ADRs já
seguem esse pattern, operador interno aprendeu uma vez. Duplicação de
colunas (`retorno_real`, `sigma`, `fonte`) entre as duas é aceita; padrão
do projeto. Override **exige `justificativa: TEXT NOT NULL`** — eviden­cia
fiduciária por que o workspace foge do default.

### D2 — Lookup table `economic_asset_class` (não CHECK constraint)

PO admitiu na revisão que o enum pode estar incompleto. Lookup table
evita migration cada vez que classe entra/sai:

```sql
CREATE TABLE economic_asset_class (
  code VARCHAR(40) PRIMARY KEY,
  label VARCHAR(120) NOT NULL,
  sort_order INTEGER NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  deprecated_at TIMESTAMP,
  description TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

`deprecated_at` desde o dia 1 — futuro vai querer soft-deprecate sem
quebrar histórico. Disciplina de typing recuperada via Pydantic `Literal`
**gerado a partir do DB no boot** (similar a `ConfigStore` [[ADR-134]])
mais teste de regressão "todo `classe_auvp` em uso em `economic_assumptions`
tem linha em `economic_asset_class`".

**Seed inicial** (operador interno via console futuro; v1 via SQL):

| `code` | `label` | `sort_order` |
|---|---|---|
| `rf_pos` | Renda Fixa pós-fixada (CDI, Selic) | 10 |
| `rf_pre` | Renda Fixa prefixada | 20 |
| `rf_inflacao` | Renda Fixa indexada à inflação (IPCA+) | 30 |
| `acoes_br` | Ações Brasil | 40 |
| `acoes_intl` | Ações Internacional | 50 |
| `fii` | Fundos Imobiliários (FII) | 60 |
| `imoveis_diretos` | Imóveis físicos | 70 |
| `caixa` | Caixa / Liquidez | 5 |
| `cambio_usd` | Câmbio USD | 80 |
| `cambio_eur` | Câmbio EUR | 81 |

Cripto, commodities, private equity, debêntures incentivadas — adiciona
em PR sucessor sem migration.

### D3 — Service helper espelhando padrão de [[ADR-135]]

```python
class EconomicAssumptionsService:
    def get_vigentes_em(
        self,
        as_of: date,
        workspace_id: WorkspaceId | None = None,
    ) -> tuple[EconomicAssumption, ...]:
        """Resolve (global ∪ override) na data dada.

        Override workspace > global. Retorna lista consolidada com flag
        `fonte: 'global' | 'workspace_override'` por linha.
        """
```

**Duas queries claras, não SQL único com COALESCE/JOIN.** Volume é
dezenas de linhas — tracing > micro-otimização. Service injetado via
`WorkspaceContext.get_economic_assumptions(as_of)`.

### D4 — Gate de emissão: degrade com `status: indisponivel` por classe

E5 não bloqueia o relatório se faltar premissa. Em vez disso, emite
honestamente:

```json
{
  "premissas_economicas": {
    "status": "parcial",
    "classes": [
      {"classe_auvp": "rf_pos", "retorno_real": 4.5, "sigma": 1.2, "fonte_origem": "global", "effective_from": "2026-01-01"},
      {"classe_auvp": "acoes_br", "retorno_real": 7.0, "sigma": 18.5, "fonte_origem": "workspace_override", "effective_from": "2026-03-15"},
      {"classe_auvp": "cripto", "status": "indisponivel", "razao": "Classe presente na carteira mas sem premissa vigente em 2026-05-15"}
    ],
    "snapshot_at": "2026-05-15T12:08:45Z"
  }
}
```

UI renderiza linhas `indisponivel` como warn explícito (não silencia):
"esta classe não tem premissa vigente — projeção parcial". S7 Monte Carlo
omite a classe ou usa default conservador documentado.

Decisão (vs. alternativa "abortar emissão" ou "usar hard-coded default"):
abortar tem UX terrível em produção; hard-coded silencioso mata
auditabilidade. Status explícito força transparência.

### D5 — Snapshot completo no payload E5

Toda emissão E5 **congela** as premissas aplicadas no payload (no campo
`premissas_economicas.classes` acima). Isso é **load-bearing para
auditoria fiduciária real**: o planejador CFP® precisa saber "que
premissa o relatório de 2026-03 usou", não a vigente hoje. Premissa
muda mensalmente; relatório é imutável após publicação ([[ADR-199]]).

Custo: ~1KB por payload E5 (dezenas de linhas × ~80 bytes). Aceitável.
Ganho: única forma de auditoria fiduciária honesta.

### D6 — Backfill: `(a) não migra runs antigos`

Runs E5 antigos não emitiram premissas econômicas — **não migrar**.
APP_B no renderer mostra "Premissas econômicas não disponíveis para este
run. Refresh o relatório para incluir baseline 2026-05-15." Honesto
historicamente (não havia tabela na época). Alternativa "(b) atribuir
premissa vigente na data do run" é falsa: o run não usou nenhuma premissa
versionada. Rejeitada.

Recompute on-read **não aplica** aqui — premissas são input, não derivado;
sem emissão original, não há o que recomputar. UI degrada limpo.

### D7 — Console interno (CRUD) em wave separada

[[ADR-116]] (Console interno IA-0..IA-4) ainda em desenvolvimento. **UI
do CRUD de assumptions é wave 2, não bloqueante.** Operador edita via
SQL (seed inicial + ajustes) no MVP — RTO de correção alto, mas aceitável
em pré-GA. UI antes de GA.

### D8 — Schema E5 evolution mode `warn`

[[ADR-212]] hook `validate_dict` modo `warn` para `premissas_economicas`
opcional aditivo. Flip strict só quando todos workspaces canônicos têm
run pós-seed. Goldens regeneram apenas para canônicos com Monte Carlo.

## Custos & Trade-offs

- **Governance contínua.** Tabela exige revisão **trimestral** (premissas
  econômicas mudam, especialmente em ambiente macro volátil). Operador
  interno → custo de 4× revisão/ano. Sem isso, baseline envelhece e
  Monte Carlo perde calibragem. Aceito: trimestre é o mínimo defensável
  fiduciariamente.
- **Snapshot no E5 inflando payload.** ~1KB extra por run. Negligível em
  `pipeline_artifacts` (linhas hoje média ~10-100KB). Mantém auditoria.
- **Duas tabelas vs. uma tabela.** Senior-cto sugeriu unificar; PO decidiu
  por duas (consistência com [[ADR-135]]/[[ADR-137]]). Custo: marginal.
- **Lookup table vs. enum CHECK.** Lookup é mais flexível, mas perde
  disciplina de typing. Mitigado por Pydantic `Literal` gerado no boot +
  teste de coerência. Aceito.

## Alternativas consideradas

- **Estender `market_rates` ([[ADR-135]]) com colunas por classe AUVP** —
  mistura preocupações (câmbio + retorno editorial não são iguais).
  Rejeitada.
- **YAML em `config/economic_assumptions.yaml`** — não versionada por
  data; congelaria ao deploy; impossível override por workspace.
  Rejeitada.
- **Constants em Python (`pipeline_common.py`)** — sem audit trail, sem
  override, impossível ajustar sem release. Rejeitada.
- **Tabela única com `workspace_id NULL = global`** — senior-cto.
  Rejeitada por consistência com pattern do projeto.
- **Gate de emissão `bloqueia relatório`** — UX terrível em produção.
  Rejeitada.
- **Gate de emissão `default hard-coded silencioso`** — mata
  auditabilidade que é o propósito desta ADR. Rejeitada.

## Implementação

PR fundacional (wave 1):

- Migration Alembic `add_economic_assumptions` (3 tabelas:
  `economic_asset_class` + `economic_assumptions` +
  `workspace_economic_assumptions_override`).
- `backend/app/models/economic_assumptions.py` (SQLAlchemy) + repos.
- `backend/app/services/economic_assumptions_service.py` — `get_vigentes_em`
  + Pydantic `Literal` gerado no boot.
- Seed inicial em `dev/seed_economic_assumptions.py` (idempotente, com
  checkpoint, executado pós-deploy — **não na migration**).
- `WorkspaceContext.get_economic_assumptions(as_of)` + registro em
  [`docs/reference/STATELESS_AUDIT.md`](../reference/STATELESS_AUDIT.md)
  §2.
- Schema E5: adicionar `premissas_economicas?` opcional aditivo.
- `pipeline/stages/e5_analyze.py` — consumir service + snapshot no
  payload + consumidor de Monte Carlo lê do snapshot (não do DB direto
  durante o cálculo — preserva determinismo de re-run).
- `ApendiceBSection.tsx` — tabela editorial (classe / retorno / sigma /
  fonte / vigente desde).
- Teste empírico: emitir relatório workspace 5@5.com com seed inicial,
  validar que APP_B renderiza tabela e que Monte Carlo (S7) usa as
  premissas snapshotadas.

PR wave 2 (separado, antes de GA):

- Console interno IA-X — CRUD de assumptions com workflow de revisão.

**Dependências:**

- Esta ADR é **fundação para [[ADR-217]] D1 (componente
  `diversificacao_auvp` referencia alocação alvo metodologicamente
  justificada) e [[ADR-220]] D2 (cálculo `patrimonio_alvo` IF)**. Recomendação
  cross-ADR: implementar 219 primeiro, depois 218 (em paralelo), depois
  217, depois 220.

## Critério de aceite

- [ ] `EconomicAssumptionsService.get_vigentes_em(date)` retorna lista
      consolidada com flag `fonte` correta (global vs. override).
- [ ] Override workspace tem precedência sobre global.
- [ ] Lookup `economic_asset_class` permite adicionar classe sem
      migration.
- [ ] Pydantic `Literal` gerado no boot reflete o estado da lookup.
- [ ] E5 emite snapshot completo em `premissas_economicas.classes`.
- [ ] Monte Carlo S7 lê do snapshot do payload, não do DB — re-run
      sobre mesmo run produz mesmas projeções.
- [ ] Classe na carteira sem premissa vigente: payload tem `status:
      indisponivel` + UI renderiza warn.
- [ ] Runs antigos sem `premissas_economicas`: APP_B mostra empty-state
      "Premissas não disponíveis — refresh para baseline atual".
