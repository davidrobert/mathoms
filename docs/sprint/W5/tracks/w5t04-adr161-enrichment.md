---
id: TRACK-w5t04-adr161-enrichment
type: track
title: "Track W5-T04 — FP-004 ADR-161 enrichment (5 sub-PRs paralelos)"
sprint: W5
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/w5
  - status/consumed
---

# Track W5-T04 — FP-004 ADR-161 enrichment (5 sub-PRs paralelos)

> **Lane ID:** `w5t04-adr161-enrich`
> **Branch prefix:** `agent/w5t04-adr161-enrich/<sub>/<yyyyMMdd-HHmm>`
> **Plano canônico:** [plan/PLATFORM_REVIEW/_README.md §W5-T04](../../../plan/PLATFORM_REVIEW/_README.md)
> **ADR:** ADR-161 §Follow-ups #1
> **Onda:** Wave 5 (paraleliza com W5-T01/T03 e W6-T*)
> **Severity:** P1 · **Effort:** L (~7-10d paralelizáveis)
> **Owner:** financial-planner
> **Depende de:** W1-T07 ✅ (retorno_esperado_pct_aa) · A7.2b ✅ (MarketRate)
> **Findings cobertos:** FP-004

---

## Por que esta lane

ADR-161 entregou 6 regras v2 mas só 1 (`endividamento_perigoso`) está
acordada. As outras 5 são determinísticas e testadas, **dormentes**
porque o snapshot E5 não popula seus campos. Cada sub-PR ativa uma
regra fechando o gap snapshot ↔ regra.

---

## Sub-PRs (5 paralelizáveis — ordem em §Sequência)

### Sub-PR #1 — `feat(pipeline): popular taxa_poupanca_trimestral_historico`

- **Regra:** `taxa_poupanca_caindo` (Cerbasi · comportamental)
- **Trigger:** 2 quedas trimestrais consecutivas >5pp na taxa de poupança recorrente.
- **Arquivos:** `pipeline/domain/services/fluxo_caixa_enricher.py`, `pipeline/domain/services/e5_serialization.py`.
- **Dado faltante:** `fluxo_caixa.taxa_poupanca_trimestral_historico: list[float]` (≥3 trimestres).
- **Fonte:** agregar `Janela12m.taxa_poupanca_recorrente` por trimestre fiscal (`fluxo_mensal.por_mes` rolling 3M sliding).
- **Teste e2e:** workspace fictício com 4 trimestres `[35, 28, 22, 17]` (queda monotônica >5pp); asserir kind presente.

### Sub-PR #2 — `feat(backend): WorkspaceInsurance + endpoint + snapshot field`

- **Regra:** `seguros_insuficientes` (Cerbasi · proteção)
- **Trigger:** `renda_pj_mensal > R$50k` AND zero `WorkspaceInsurance` ativo `kind in ('vida','invalidez')`.
- **Arquivos novos:**
  - `backend/app/models/workspace_insurance.py`
  - `backend/alembic/versions/<hash>_workspace_insurance.py`
  - `backend/app/repositories/workspace_insurance_repository.py`
  - `backend/app/api/v1/insurance.py`
  - `pipeline/domain/services/seguros_snapshot_builder.py`
- **Schema:**
  ```python
  class WorkspaceInsurance(Base):
      id: str (UUID PK)
      workspace_id: str (FK CASCADE)
      kind: str  # vida | invalidez | saude | residencial | auto | patrimonial
      provider: str
      coverage_brl_cents: int (BIGINT — ADR-090)
      premium_monthly_brl_cents: int (BIGINT)
      beneficiary_member_id: str | None (FK family_members SET NULL)
      effective_from: date
      effective_to: date | None
      policy_number_encrypted: str | None  # Fernet
      notes: str | None
      created_at: datetime
      updated_at: datetime
      # UniqueConstraint(workspace_id, kind, provider, effective_from)
  ```
- **Teste e2e:** workspace `renda_pj_mensal=80_000` zero rows → kind presente. Adicionar row vida vigente → kind ausente.

### Sub-PR #3 — `feat(pipeline): patrimonio.por_instituicao agregado em BRL`

- **Regra:** `concentracao_instituicao` (AUVP)
- **Trigger:** alguma instituição com `>40%` do investível.
- **Arquivos:** `pipeline/domain/services/instituicoes_por_membro_analyzer.py` (estende), `pipeline/domain/services/e5_serialization.py`.
- **Dado faltante:** `snapshot.patrimonio.por_instituicao: dict[str, float]` (BRL por banco). Hoje só lista de nomes.
- **Fonte:** somar `valor_atual_brl` de cada `investimento` em `bens_por_membro[*].investimentos` agrupando por `instituicao`.
- **Teste e2e:** `por_instituicao={"Itau": 600_000, "BTG": 300_000, "XP": 100_000}` → kind presente (Itaú=60%). `{"Itau": 350, "BTG": 350, "XP": 300}` → ausente.

### Sub-PR #4 — `feat(pipeline): inflacao reader via MarketRate IPCA`

- **Regra:** `lifestyle_creep` (Cerbasi/Perini)
- **Trigger:** despesa essencial cresce >1.5× IPCA acumulado em 6m.
- **Arquivos:**
  - `pipeline/ports/config_store.py` (estende protocol com `get_inflation_pct(start, end)`)
  - `backend/app/services/db_config_store.py`
  - `backend/app/services/inflation_reader.py` (NOVO)
  - `pipeline/adapters/file_config_store.py`
  - `pipeline/domain/services/fluxo_caixa_enricher.py` (popula `despesa_essencial_historico`)
  - `pipeline/domain/services/e5_serialization.py` (popula `inflacao.acumulada_pct_no_periodo`)
- **Reader (pseudo):**
  ```python
  def get_ipca_acumulado_pct(*, start: date, end: date, store: ConfigStore) -> float | None:
      rates = store.list_market_rates_pair("IPCA/BRL", start=start, end=end)
      if not rates: return None
      acumulado = Decimal("1")
      for r in rates:
          acumulado *= (Decimal("1") + r.rate / Decimal("100"))
      return float((acumulado - Decimal("1")) * Decimal("100"))
  ```
- **Seed Alembic:** popular `market_rates` com `pair='IPCA/BRL'` últimos 24 meses (IBGE série 433 — Bacen API/sgs).
- **Teste e2e:** `despesa_essencial_historico=[10000,10500,11000,11500,12000,12500]` (+25%) + IPCA 6m=2.5% → kind presente. Crescimento 3% → ausente.

### Sub-PR #5 — `feat(pipeline): renda_passiva + despesa_mensal_media via pipeline real`

- **Regra:** `renda_passiva_real_baixa` (Perini "300")
- **Trigger:** `if_pct >= 50%` AND `renda_passiva/custo_vida < 30%`.
- **Status:** **regra já dispara** em `tests/test_e5_to_suggestion_e2e.py::test_fp001_renda_passiva_real_baixa_dispara_em_snapshot_real` (FP-001 fechado em W1-T02).
- **Esta sub-PR é gate de validação:** confirmar adapter E5 emite os campos no caminho real (não só fixture sintética) + adicionar teste e2e com pipeline rodando E1.6+E5 sobre fixture IRPF realista.
- **Dado faltante:** **nenhum estrutural** — só paridade adapter ↔ generator.
- **Teste e2e:** rodar pipeline `extract_irpf_full` + `analyze_finances` num fixture com `bens > 2.5M`, `if_meta=5M`, IRPF anual com R$48k de dividendos → `renda_passiva_mensal_observada_brl = 4000` → kind presente.

---

## Validação metodológica

| Regra | Aderência |
|---|---|
| `taxa_poupanca_caindo` | **Cerbasi** — comportamental: queda da taxa de poupança é sinal-mestre de descontrole orçamentário. Perini concorda; AUVP neutro. |
| `seguros_insuficientes` | **Cerbasi** — proteção é prerrequisito de plano. Família alta-renda PJ sem cobertura é ponto cego clássico. |
| `concentracao_instituicao` | **AUVP** — risco institucional não-diversificável (intervenção/custódia). Axioma do Diagrama do Cerrado. |
| `lifestyle_creep` | **Cerbasi+Perini** — aumento estrutural de custo essencial atrasa ano-IF mais que choque pontual. |
| `renda_passiva_real_baixa` | **Perini "300"** — múltiplo de custo só é IF real se renda passiva cobre custo; patrimônio paper sem fluxo é IF teórica. |

---

## Sequência sugerida

1. **Sub-PR #5 primeiro** — gate de validação, baixo risco, fecha FP-001 com teste real de pipeline.
2. **Sub-PR #3 (concentracao)** — independente, só pipeline; alto valor metodológico (AUVP) com fricção mínima.
3. **Sub-PR #1 (taxa_poupanca)** — independente, só enricher.
4. **Sub-PR #4 (lifestyle_creep)** — depende de A7.2b (MarketRate ✅) e seed IPCA; estende ConfigStore — coordenar com data-engineer.
5. **Sub-PR #2 (seguros)** — maior (model + migration + endpoint + UI futura). Por último para não bloquear.

---

## Prioridade por impacto no usuário

- **P1.1 — Sub-PR #5** (Perini "300"). Fecha follow-up canônico, risco mínimo.
- **P1.2 — Sub-PR #3** (AUVP). Maior ROI/esforço — sem migration.
- **P1.3 — Sub-PR #1** (Cerbasi comportamental). Utilidade transversal.
- **P1.4 — Sub-PR #4** (Cerbasi/Perini). Custo de seed IPCA externo.
- **P1.5 — Sub-PR #2** (Cerbasi proteção). **Maior valor para usuário final** (PJ alta-renda + famílias) — único sinal que **previne ruína catastrófica**, mas custo alto. Recomendo paralelizar: começar #2 em background enquanto #1/#3/#5 fecham em série rápida.

---

## Critério de aceite global

- [ ] 5 regras dormentes disparam em `tests/test_e5_to_suggestion_e2e.py` (cenários concretos por regra).
- [ ] Teste de não-disparo (caso negativo) por regra.
- [ ] ADR-161 §Follow-ups #1 marca FP-004 ✅ com link para os 5 PRs.
- [ ] Schema E5 ganha blocos `seguros`, `inflacao`, `patrimonio.por_instituicao`, `fluxo_caixa.despesa_essencial_historico`, `fluxo_caixa.taxa_poupanca_trimestral_historico` (coordenar com W6-T01).
