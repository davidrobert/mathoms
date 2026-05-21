---
id: ADR-227
type: adr
title: "Imóvel financiado: agregado `Debt` persistido + `property_market_value` override; saldo devedor líquido em `investivel_efetivo`, bruto preservado em cat_2"
status: Decidido
phase: A15
date: "2026-05-19"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-109]]"
  - "[[ADR-111]]"
  - "[[ADR-134]]"
  - "[[ADR-142]]"
  - "[[ADR-143]]"
  - "[[ADR-145]]"
  - "[[ADR-157]]"
  - "[[ADR-186]]"
  - "[[ADR-212]]"
  - "[[ADR-215]]"
  - "[[ADR-216]]"
  - "[[ADR-222]]"
  - "[[ADR-223]]"
  - "[[ADR-225]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 227"
  - "imovel financiado"
  - "debt aggregate"
  - "valor mercado property"
  - "FU-3 sprint A12"
tags:
  - area/methodology
  - area/persistence
  - area/pipeline
  - area/backend
  - area/relatorio
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
  - phase/a15
  - status/decidido
  - type/adr
---

> ADR longa (>150 linhas) por design: coordena criação de agregado novo
> (`Debt`), tabela de override de valuação (`property_market_value`),
> mudança em `PatrimonioCalculator` (líquido em `investivel_efetivo`),
> migration de cutover (extração `total_dividas` baseline → rows
> persistidas), endpoints REST + UI, e invariante de produto vs.
> apresentação dual no relatório. Split em ADRs menores produziria peças
> órfãs sem o contrato cruzado.

## Contexto

[[ADR-215]] estabeleceu enum `classification` por imóvel (residencia_principal,
uso_pessoal, locado, comercial, especulacao, desconhecido) via override
em `workspace_property_overrides`. [[ADR-222]] tornou `imoveis_no_if`
per-workspace e [[ADR-223]] flipou o default para `false` (conservador
Perini). [[ADR-216]] canonizou `cap_rate_liquido_pct` como métrica de S4
e fixou em D6 que `valor_mercado_brl` será override via [[ADR-134]] —
*decisão arquitetural sem implementação*.

[[ADR-215]] §Consequências/Follow-ups registrou explicitamente o débito:

> Imóvel financiado com saldo devedor distorce patrimônio bruto. Fora
> do escopo desta ADR. Follow-up: `valor_mercado` + linkagem
> `saldo_financiamento` ao passivo correspondente. ADR futuro.

Esta ADR é esse follow-up — FU-3 do Sprint A12, executado em Sprint A15.

**Dois bugs silenciosos em produção (auditoria 2026-05-19):**

### Bug 1 — Patrimônio bruto defasado mascara alavancagem

[`patrimonio_calculator.py:_split_imoveis`](../../pipeline/domain/services/patrimonio_calculator.py) (linha 257)
usa `imovel_valor(im)` ([`patrimonio_types.py`](../../pipeline/domain/services/patrimonio_types.py)),
que retorna `valor_brl` do baseline — custo histórico IRPF. Apto declarado
R$ 800k em 2018, R$ 1,2M de mercado hoje, R$ 300k saldo devedor → relatório
mostra 800k bruto. Patrimônio LÍQUIDO real é ~900k mas usuário vê 800k
"limpo": [`PatrimonioCalculator._sum_dividas`](../../pipeline/domain/services/patrimonio_calculator.py) (linha 252)
subtrai `total_dividas` agregado por membro (do IRPF), nunca per-property.
Usuário tem falsa segurança de "patrimônio limpo".

### Bug 2 — IF mal-calibrado quando `imoveis_no_if=true` (cat_2 locado)

[`PatrimonioCalculator.calculate`](../../pipeline/domain/services/patrimonio_calculator.py) (linha 160)
linha 214: `cat2_efetivo = imoveis_geradores` (soma de `imovel_valor` =
valor_irpf, 800k). Mas yield real é (aluguel ÷ valor_mercado = 1,2M) —
denominador/numerador desalinhados. Mais: capital econômico investido é
1,2M − 300k saldo devedor = 900k líquido. Numerador 800k IRPF entra em
`investivel_efetivo`, sem nenhum vínculo com passivo do imóvel.
`progresso_if` matematicamente errado.

### Achado de auditoria — Debt aggregate não existe

Hoje `total_dividas` vive APENAS como agregado por membro em
`baseline_patrimonial` (extraído de IRPF E1.5c). [`EndividamentoAnalyzer`](../../pipeline/domain/services/endividamento_analyzer.py) (linha 74)
gera `DividaItem` em runtime no E5 com descrição hardcoded
`f"Financiamento imobiliário ({nome})"`, **sem persistir em DB**. Não há
modelo `Debt`/`Liability`/`Financing` em `backend/app/models/` (auditoria 2026-05-19: 40 modelos, nenhum corresponde).
Para linkar saldo devedor a property específica, FU-3 precisa criar
agregado Debt do zero — não é "adicionar FK em modelo existente".

### Achado de auditoria — trilho `valor_imovel_origem` já existe

[`real_estate_metrics.py`](../../pipeline/domain/services/real_estate_metrics.py) (linha 71)
define `PropertyInput.valor_imovel_origem: Literal["irpf", "mercado"]`
com default `"irpf"`. Plano S4 entregou em 2026-05-15 (PRs #280-#305).
Mas **zero código popula `"mercado"`** — sem tabela, sem coluna, sem UI.
Trilho está pronto; só falta a fonte de dados.

## Decisão

Adotar **seis decisões coordenadas** que substituem `valor_irpf` por
resolução com override de mercado + persistem saldo devedor por property
+ ajustam `investivel_efetivo` para líquido econômico, preservando
patrimônio bruto na composição.

### D1 — Agregado `Debt` persistido em DB (criar do zero)

```sql
CREATE TABLE debt (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  family_member_id UUID NULL REFERENCES family_members(id) ON DELETE SET NULL,
  property_id UUID NULL REFERENCES property_identity(id) ON DELETE RESTRICT,
  tipo VARCHAR(30) NOT NULL,                  -- 'financiamento_imobiliario'|'consignado'|'cdc'|'cartao_rotativo'|'rotativo'|'outro'
  descricao TEXT NULL,
  saldo_devedor_cents BIGINT NOT NULL,        -- ADR-090: int cents, nunca float
  parcela_mensal_cents BIGINT NULL,
  taxa_juros_aa NUMERIC(5,2) NULL,            -- "12.50" = 12,50% a.a.
  prazo_meses_restantes INTEGER NULL,
  data_contratacao DATE NULL,                 -- útil p/ Cerbasi (amortização real)
  source VARCHAR(30) NOT NULL,                -- 'baseline_irpf_migration'|'user_declared'|'open_banking_futuro'
  migration_source_key VARCHAR(64) NULL,      -- p/ idempotência da migration
  needs_review BOOLEAN NOT NULL DEFAULT false,
  percentual_atribuicao_imovel NUMERIC(5,2) NULL,  -- 0-100, default 100% quando property_id; rateio co-propriedade
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  CONSTRAINT chk_debt_tipo CHECK (tipo IN (
    'financiamento_imobiliario','consignado','cdc','cartao_rotativo','rotativo','outro'
  )),
  CONSTRAINT chk_debt_source CHECK (source IN (
    'baseline_irpf_migration','user_declared','open_banking_futuro'
  )),
  CONSTRAINT chk_debt_pct_atribuicao CHECK (
    percentual_atribuicao_imovel IS NULL
    OR (percentual_atribuicao_imovel > 0 AND percentual_atribuicao_imovel <= 100)
  ),
  CONSTRAINT chk_debt_identity CHECK (
    family_member_id IS NOT NULL OR property_id IS NOT NULL OR descricao IS NOT NULL
  )
);

CREATE INDEX idx_debt_workspace ON debt (workspace_id);
CREATE INDEX idx_debt_property ON debt (property_id) WHERE property_id IS NOT NULL;
CREATE UNIQUE INDEX uq_debt_migration_source
  ON debt (workspace_id, migration_source_key)
  WHERE source = 'baseline_irpf_migration';
```

**Justificativa das escolhas:**

- **`property_id` opcional**: CDC/consignado/empréstimo pessoal são Debts
  legítimos sem property. Modelo cobre tudo desde V1.
- **`ON DELETE RESTRICT`** (não `SET NULL` do briefing original):
  consenso `senior-cto` + `data-engineer` — `SET NULL` cria órfão
  silencioso (deleta property, debt vira "dívida solta", `investivel_efetivo`
  infla sem aviso). RESTRICT força UX explícita: "este imóvel tem R$ X
  de dívida vinculada — desvincule antes ou delete junto." UX chata
  vence bug silencioso em fintech.
- **`saldo_devedor_cents BIGINT`** (ADR-090): proibido `float` para
  dinheiro; cents inteiro no DB, `Decimal` em Python no boundary.
- **`tipo` enum com `consignado`/`cartao_rotativo` desde V1**: schema
  evolution é caro depois; adicionar enum agora é grátis. `cartao_rotativo`
  separado de `rotativo` porque cartão tem comportamento próprio em E5
  (categorização Cerbasi anti-rotativo).
- **`migration_source_key`** persistido (não logado): permite re-conciliar
  se descobrir bug na migration. Custo: 1 varchar por row.
- **`needs_review` flag**: migration extrai N dívidas como rows com
  `needs_review=true`; UI batch (D5) força revisão.
- **`percentual_atribuicao_imovel`** (sugestão `product-designer`): cobre
  co-propriedade familiar com debt no nome de 1 cônjuge. Default 100%
  quando property_id; rateio é override consciente.
- **CHECK `identity`**: evita row órfã sem nenhuma identidade
  (sem membro, sem property, sem descrição).

### D2 — `property_market_value` tabela versionada (append-only)

```sql
CREATE TABLE property_market_value (
  id UUID PRIMARY KEY,
  property_id UUID NOT NULL REFERENCES property_identity(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  valor_brl_cents BIGINT NOT NULL,
  valuation_date DATE NOT NULL,
  source VARCHAR(30) NOT NULL,                -- 'user_declared'|'avaliacao_terceiros'|'cep_proxy_futuro'
  confidence NUMERIC(3,2) NULL,               -- 0.00-1.00, NULL em user_declared, obrigatório em V2 cep_proxy
  notes TEXT NULL,
  superseded_by_id UUID NULL,                 -- p/ marcar "essa declaração estava errada"
  created_at TIMESTAMPTZ NOT NULL,
  created_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT uq_property_valuation_date UNIQUE (property_id, valuation_date),
  CONSTRAINT chk_pmv_source CHECK (source IN (
    'user_declared','avaliacao_terceiros','cep_proxy_futuro'
  )),
  CONSTRAINT chk_pmv_confidence CHECK (
    confidence IS NULL OR (confidence >= 0 AND confidence <= 1)
  )
);

CREATE INDEX idx_pmv_lookup
  ON property_market_value (workspace_id, property_id, valuation_date DESC);
```

**Versionada append-only** (sugestão `data-engineer`): cada declaração é
row nova; usuário corrige criando entry com `valuation_date` atual, não
UPDATE. Custo storage trivial (~50 rows/workspace/decade); ganho é
auditabilidade. `superseded_by_id` permite marcar erro sem deletar.

Resolver de leitura (DISTINCT ON Postgres / `ROW_NUMBER` SQLite):

```python
def latest_market_value_by_property(
    workspace_id: str,
) -> dict[str, MarketValueResolution]:
    """1 row por property, mais recente. Lazy: ausente → caller usa valor_irpf."""
```

### D3 — `investivel_efetivo` usa líquido econômico; cat_2 na tabela continua bruto

**Invariante de apresentação preservada (sugestão `financial-planner`):**
patrimônio bruto na tabela de composição = valor de mercado (quando
declarado) **sem subtrair saldo devedor**; passivo continua agregado em
`total_dividas`. Isso preserva o invariante "categoria = valor do ativo
bruto, passivo = bucket separado" consistente com cat_1 (residência) e
veículos.

**Líquido econômico entra APENAS em `investivel_efetivo`** ([[ADR-142]]):

```python
def _compute_investivel_efetivo(
    self,
    investivel_financeiro: float,
    imoveis_geradores: list[ImovelResolvido],  # com property_id + valor_efetivo + saldo_devedor
) -> float:
    if not self._config.include_real_estate_in_if:
        return max(0.0, investivel_financeiro)
    cat2_efetivo = sum(
        max(0.0, im.valor_efetivo - im.saldo_devedor)
        for im in imoveis_geradores
    )
    return max(0.0, investivel_financeiro + cat2_efetivo)
```

`valor_efetivo = valor_mercado (≤12m) || valor_irpf` (cascade — D5).
`saldo_devedor` é soma de `Debt.saldo_devedor_cents` com `property_id`
matching, multiplicada por `percentual_atribuicao_imovel / 100`.

**Apresentação dual no relatório** (acomoda `product-designer` em card):
hero do card S4 (`RealEstateYieldCard`) ganha breakdown opcional drill-down
expondo `Valor IRPF | Valor Mercado | Saldo Devedor | Líquido Econômico`
em modal/painel lateral. Tabela principal de patrimônio mantém só
`valor_efetivo` por categoria (cat_2).

### D4 — Resolver puro como função module-level + Protocol opcional

[[ADR-097]] D3 exige services receberem value objects tipados.
`PatrimonioCalculator` ganha novo dependency object (sugestão
`senior-cto` — não estender `PatrimonioConfig`):

```python
@dataclass(frozen=True)
class RealEstateValuationContext:
    market_values: Mapping[str, MarketValueResolution]  # property_id → resolução
    debts_by_property: Mapping[str, Decimal]             # property_id → soma rateada
    today: date                                          # p/ TTL determinístico em teste

# Calculator recebe via PatrimonioInputs (não Config — é dado de domínio carregado do DB)
@dataclass(frozen=True)
class PatrimonioInputs:
    # ... campos existentes
    valuation_context: RealEstateValuationContext | None = None  # opcional p/ retrocompat
```

Resolver puro em `pipeline/domain/services/real_estate_valuation_resolver.py`:

```python
def resolve_valor_efetivo(
    property_id: str,
    valor_irpf_brl: Decimal,
    context: RealEstateValuationContext,
    ttl_days: int = 365,
) -> tuple[Decimal, Literal["mercado", "irpf"]]: ...
```

Protocol exposto no consumer (calculator) para teste:

```python
class RealEstateValuationResolver(Protocol):
    def resolve(self, property_id: str, valor_irpf: Decimal) -> tuple[Decimal, str]: ...
```

[[ADR-111]] stateless: resolver é puro, sem cache in-memory; lookup vem
do dict pré-carregado em `RealEstateValuationContext`. Quando V2 entrar
com I/O real (CEP proxy), implementação do Protocol vira service com
caching Redis explícito.

### D5 — TTL `valor_mercado`: banner persistente, sem fallback automático

Após 12 meses sem nova declaração, **banner persistente** "valor
desatualizado — atualizar?" — **sem trocar valor automaticamente para
`valor_irpf`** (posição `financial-planner` contra fallback silencioso).

Justificativa: mudar KPI sem aviso é exatamente o anti-padrão que
[[ADR-223]] §Riscos rejeitou ("usuário viu KPI X por meses não pode
acordar com KPI Y sem aviso"). Banner trava decisão com o usuário;
sistema mantém `valor_mercado` até resposta.

Resolver (D4) recebe `ttl_days=365` apenas para sinalizar staleness no
payload (`valor_imovel_staleness_days`), não para trocar fonte. Frontend
decide threshold visual:
- 0-12m → sem badge
- 12-24m → `Badge variant="warning"` "atualizado há N meses"
- >24m → `Badge variant="critical"` + nudge contextual

Cascade hierárquica de fontes (espelha [[ADR-216]] D9):

| Prioridade | Fonte | Lookup |
|---|---|---|
| 1 | `property_market_value` (mais recente) | `latest_market_value_by_property()` |
| 2 | `valor_irpf` (baseline E1.5c) | `imovel_valor(im)` (atual) |

Sem prioridades 3+ em V1. V2 (post-A15) pode adicionar `cep_proxy`
estimado, com `confidence < 0.7` exigindo confirmação humana antes de
afetar KPI.

### D6 — Migration de cutover: extrair `total_dividas` baseline → rows Debt

Migration Alembic faz **só `CREATE TABLE debt` + `CREATE TABLE property_market_value`** (regra CLAUDE.md "Backfill é stage separado"). Backfill em script dedicado:

```
dev/backfill_debt_from_baseline.py --workspace-id <id> [--dry-run] [--apply]
```

Defaults para **dry-run**. Behavior:

1. Para cada workspace × membro com `total_dividas > 0` no baseline:
   cria 1 row Debt com:
   - `tipo='outro'` (não tentar inferir tipo de descrição)
   - `saldo_devedor_cents = total_dividas * 100`
   - `descricao = f"Migrado de baseline IRPF ({membro})"`
   - `source = 'baseline_irpf_migration'`
   - `migration_source_key = f"{workspace_id}_{member_key}"`
   - `needs_review = true`
   - `property_id = NULL` (não auto-atribui)
2. **Não** tentar heurística por descrição (`'%financiamento%' OR '%imobiliário%'`)
   → falso-positivo garantido com >1 imóvel.
3. Audit em `storage/<workspace>/logs/debt_migration_audit.json` (gitignored).
4. Idempotência: partial unique index
   `(workspace_id, migration_source_key) WHERE source='baseline_irpf_migration'`
   torna re-run no-op por workspace já migrado.

UI batch review em `/imoveis/financiamentos-review`: tabela com `Debt.needs_review=true`,
dropdown por linha pra atribuir property, bulk action "Não vincular a imóvel".

**Conflito declarativo IRPF↔per-property** (achado `financial-planner`):
quando soma de `Debt.saldo_devedor` per-property > `total_dividas_imobiliarias_irpf × 1.1`,
emite warning de domínio tipado ([[ADR-097]] D1):

```python
@dataclass(frozen=True)
class DebtVsIrpfDeclaracaoConflict:
    member_key: str
    soma_debt_brl: Decimal
    total_dividas_irpf_brl: Decimal
    ratio: Decimal
    def format(self) -> str: ...
```

Per-property vence agregado IRPF (fonte mais fresca/granular); warning
sinaliza inconsistência ao usuário.

## Alternativas consideradas

### (A) `WorkspacePropertyOverride` minimal (financial-planner): só colunas em tabela existente

Adicionar `valor_mercado_brl`, `valor_mercado_set_at`, `saldo_devedor_brl`
em [`WorkspacePropertyOverride`](../../backend/app/models/property_identity.py) (linha 95).
2 PRs, ~3d eng.

**Descartada por escopo:** não modela CDC/consignado/cartão rotativo
(passivos não-imobiliários permanecem como hoje, runtime sem persistência).
Quando 3º caso de passivo per-item aparecer (provavelmente <6 meses pelo
ICP), abriria ADR de migração — duplica trabalho. Decisão consciente:
modelar todas as classes de passivo agora, paviment futuro.

Trade-off honesto: aceitamos +7d eng a mais nesta sprint para evitar
migration de modelo de passivo depois.

### (B) Tabela ponte `property_debt` (N:N)

Suporta caso 1 financiamento cobre 2 imóveis (real mas raro).
**Descartada por YAGNI:** caso é cauda; quando aparecer >3 workspaces,
promove para N:N via ADR. Hoje: usuário aloca manualmente em 1 Debt por
imóvel (split do saldo).

### (C) `ON DELETE SET NULL` em Debt→Property (briefing original)

Preserva débito quando imóvel deletado. **Descartada:** consenso
`senior-cto` + `data-engineer` — órfão silencioso é classe inteira de
bug invisível em fintech (deleta property, Debt vira "solta",
`investivel_efetivo` infla sem aviso). RESTRICT força UX explícita.

### (D) Materializar `valor_efetivo` em stage E1.5d / E5

Cache do compute. **Descartada:** mudança de valor_mercado força
re-rodar pipeline (caro). Pattern [[ADR-215]] §6 + [[ADR-224]] §5 é
read-time em service-layer, custo trivial (2 SELECTs por render).

### (E) Líquido econômico na tabela de composição (cat_2 já líquido)

Mental model mais honesto, mas quebra invariante "categoria = valor
bruto, passivo = bucket separado" (incompatível com cat_1, veículos).
**Descartada:** dual presentation (D3) resolve sem quebrar invariante.

### (F) Hard TTL (após 12m, fallback automático para valor_irpf)

UX mais simples. **Descartada:** anti-padrão [[ADR-223]] §Riscos
(KPI muda sem aviso explícito).

### (G) Heurística automática para atribuir Debt a property na migration

Regex em descrição. **Descartada:** falso-positivo garantido com >1
imóvel. `data-engineer` + `product-designer` convergiram em batch
review humano explícito.

## Consequências

**Positivas:**

- ✅ Bug 1 resolvido: cat_2 mostra `valor_mercado` (≤12m) quando
  declarado, não custo histórico defasado.
- ✅ Bug 2 resolvido: `investivel_efetivo` usa líquido econômico
  `max(0, valor_efetivo − saldo_devedor)` — IF calibrado.
- ✅ Modelo Debt persistido cobre CDC/consignado/cartão rotativo +
  financiamento imobiliário — paviment futuro sem ADR adicional.
- ✅ Invariante de apresentação preservado (cat_2 bruto na tabela);
  drill-down expõe breakdown sem quebrar mental model.
- ✅ Versionamento `property_market_value` mantém histórico de
  declarações.
- ✅ Migration idempotente com dry-run separado da Alembic.
- ✅ Trilho `valor_imovel_origem` ([[ADR-216]] D6 / `real_estate_metrics.py:71`)
  é finalmente populado — destrava cap rate líquido honesto.

**Negativas:**

- ⚠️ Sprint A15 dedicada (~10d eng + 4 co-designs consumidos + 5 PRs).
- ⚠️ Migration de cutover é one-shot; workspaces existentes ganham
  rows Debt com `needs_review=true` — UX batch review post-deploy.
- ⚠️ Schema E5 (`config/schemas/e5_analysis.schema.json`) ganha
  `source_valor` opcional em `imoveis.{geradores,nao_geradores}[]`.
  Aditivo — goldens E5 atualizam.
- ⚠️ Mudança breaking no contrato `composicao_patrimonial.imoveis.*`:
  cat_2 entries ganham `valor_efetivo` + `saldo_devedor_link` (opcional).
  Frontend `MonetaryValue` tabela patrimônio precisa de coluna extra.

**Riscos:**

| Risco | Mitigação |
|---|---|
| Migration extrai `total_dividas` errado para workspace com vários IRPFs (acumulação) | Backfill consume `baseline_patrimonial-1.5_consolidated` que já é deduplicado por [[ADR-225]]; idempotência via partial unique index protege re-run. |
| Co-propriedade familiar com debt no nome de 1 cônjuge | `percentual_atribuicao_imovel` opcional (default 100%); UI no form Debt mostra input só quando property tem `cotitulares.length > 1`. |
| Conflito `total_dividas` IRPF ↔ soma per-property | Warning de domínio tipado quando ratio >1.1; per-property vence. UI sinaliza no card S4. |
| Saldo devedor manual fica desatualizado (financiamento amortiza mensalmente) | Banner soft "última atualização há N meses"; open banking integration é V2 fora desta ADR. |
| `RESTRICT` em Debt→Property irrita UX em casos legítimos (vendeu imóvel mas refinanciou debt) | Modal explícito "Desvincule o débito antes" + ação rápida "Manter débito sem vínculo" que faz UPDATE para `property_id=NULL` antes do DELETE. |
| Cap rate líquido ([[ADR-216]]) baseado em valor_mercado pode mudar materialmente após deploy | Telemetria mede `Δcap_rate_liquido` pré/pós-cutover; sinaliza usuários para revisão; documentação no banner explica. |

## Gates

- **Schema:**
  - Migration Alembic só `CREATE TABLE` (zero UPDATE); `downgrade()` faz
    `DROP TABLE` limpo.
  - Backfill script em `dev/backfill_debt_from_baseline.py` com
    `--dry-run` default; audit log em `storage/<workspace>/logs/`.
  - Partial unique index `uq_debt_migration_source` garante idempotência.
- **Calculator:**
  - Golden test: imóvel financiado em cat_2 → `investivel_efetivo` usa
    `max(0, valor_efetivo − saldo_devedor)`, não `valor_irpf`.
  - Paridade legado para workspace **sem** market_value declarado:
    comportamento idêntico ao atual (fallback `valor_irpf`).
- **Boundary:**
  - `dev/check_pipeline_boundaries.py` verde — resolver em `pipeline/domain/`
    permanece puro; lookup vem do adapter `backend/app/services/`.
  - Test integration: deletar `PropertyIdentity` com Debt vinculada →
    409 + payload listando Debts bloqueantes.
- **API + UI:**
  - Snapshot OpenAPI atualizado (`make update-openapi-snapshot`,
    [[ADR-109]]) para endpoints `GET /debts`, `POST /debts`,
    `PATCH /debts/{id}`, `DELETE /debts/{id}`, `GET /property-market-values`,
    `POST /property-market-values`.
  - Test E2E Playwright: fluxo de declarar `valor_mercado` em MembersTab
    + vincular Debt a property + ver patrimônio atualizado.
- **Schema E5:**
  - `config/schemas/e5_analysis.schema.json` bumpa version (aditivo).
  - Hook `DBArtifactStore.write` ([[ADR-212]]) valida payload.
  - Goldens E5 atualizados.
- **Telemetria:**
  - Métrica `mathoms.real_estate.valor_mercado.declarations_count` +
    `mathoms.real_estate.debt.link_to_property_rate` (% de Debt com
    `property_id NOT NULL` por workspace).
- **DB schema reference:**
  - `docs/reference/DB_SCHEMA_REFERENCE.md` regenerado.

## Referências

- [[ADR-090]] — proibição `float` para dinheiro; cents inteiro no DB,
  `Decimal` em Python.
- [[ADR-097]] D1/D3 — warnings tipadas + services recebem value
  objects (`RealEstateValuationContext`).
- [[ADR-109]] — `response_model` explícito + snapshot OpenAPI.
- [[ADR-111]] — stateless; resolver puro sem cache in-memory.
- [[ADR-134]] — `ConfigStore`; pattern de override per-workspace
  (alternativa B avaliada e descartada por tipagem).
- [[ADR-142]] — `imoveis_no_if` invariante anti-dupla-contagem;
  `investivel_efetivo` é o lugar onde líquido econômico entra.
- [[ADR-143]] — `methodology=code`; cap rate + valor_efetivo são
  regras universais em docstring.
- [[ADR-145]] — taxonomia patrimonial canônica; cat_1 e cat_2
  preservados.
- [[ADR-157]] — schema E1.6 `extract_irpf_full`; baseline source para
  migration.
- [[ADR-186]] — override sticky pattern; mesmo princípio em Debt
  (`needs_review` flag não é sobrescrita por re-upload IRPF).
- [[ADR-212]] — schema validation hook em `DBArtifactStore.write`;
  E5 payload validado.
- [[ADR-215]] — `property_identity` + `WorkspacePropertyOverride`;
  FK target para Debt.property_id e PropertyMarketValue.property_id.
- [[ADR-216]] — cap rate líquido + `valor_imovel_origem`; trilho de
  destino que esta ADR finalmente popula.
- [[ADR-222]] — `imoveis_no_if` per-workspace; per-workspace gate.
- [[ADR-223]] — default conservador; anti-padrão "fallback silencioso"
  citado em D5.
- [[ADR-225]] — `codigo_rfb` invariante; Debt.property_id referencia
  `PropertyIdentity.id` (UUID interno), não `codigo_rfb`.
- Plano operacional: [PLAN-imovel-financiado](../archive/IMOVEL_FINANCIADO-2026-05-20.md)
  — Sprint A15 dedicada, 5 PRs em 5 ondas.
- Co-design 2026-05-19: `financial-planner` (invariante de apresentação
  + TTL sem fallback), `senior-cto` (boundary, RESTRICT, Protocol),
  `data-engineer` (versionamento, backfill separado, índices),
  `product-designer` (linkagem dropdown, batch review, percentual
  atribuição).
