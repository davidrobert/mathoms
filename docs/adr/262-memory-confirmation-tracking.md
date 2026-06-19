---
id: ADR-262
type: adr
title: "Memory confirmation tracking — flag por aggregate de leitura, não enum em Decision (Fase 3.E pré-req)"
status: Decidido
phase: A17.competitive-pierre-3e-prereq
date: "2026-05-23"
relates_to:
  - "[[ADR-073]]"
  - "[[ADR-136]]"
  - "[[ADR-157]]"
  - "[[ADR-178]]"
  - "[[PLAN-competitive-pierre]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 262"
  - "Memory confirmation"
  - "Memory source tracking"
tags:
  - area/persistence
  - area/domain
  - area/competitive
  - status/decidido
  - type/adr
---

# ADR-262 — Memory confirmation tracking

**Status:** Decidido • **Data:** 2026-05-23 • **Relaciona** [[ADR-073]] (Goal versionado), [[ADR-136]] (Decision event-sourced), [[ADR-157]] (IRPF schema), [[ADR-178]] (Risk aggregate), [[PLAN-competitive-pierre]] (Fase 3.E Financial Memories surface).

## Contexto

A sub-fase **3.E — Financial Memories surface** do plano [[PLAN-competitive-pierre]] (resposta competitiva a ChatGPT Personal Finance, mai/2026) propõe view consolidada em `/workspace/memories` projetando `Goal` + `Decision` + `family_members` + workspace settings + IRPF metadata.

O discovery do `product-designer` ([asset 3e-discovery-2026-05-23.md §4 D2](../plan/COMPETITIVE_PIERRE/assets/3e-discovery-2026-05-23.md)) decidiu **distinção visual obrigatória** entre memórias:

- **Declarada** — user digitou explicitamente.
- **Derivada** — pipeline (E5 analyzer, IRPF parser) inferiu de documentos.
- **Confirmada** — derivada que user revisou e endossou ("Confirmar" CTA em derivada).

O designer levantou pergunta de bloqueio: **"o `Decision` aggregate (ADR-136) hoje expõe `source: user_declared | user_confirmed | system_derived` no domínio?"**

### Investigação

Leitura de `backend/app/models/decision.py:64-143` confirma:

- `Decision` **não tem coluna `source`**.
- `Decision` carrega `target_field`/`target_value`/`target_value_type` (ADR-162 — projection target) e `context_snapshot` (ADR-163 — KPIs frozen do relatório que originou Suggestion).
- **Toda `Decision` nasce editorial** — sempre criada por user (manual no plano ou aceitando Suggestion). O conceito "system_derived Decision" não existe e não deveria existir (Decision = ato deliberado).

**Conclusão:** o problema do designer não é falta de `source` em `Decision`. É falta de **marker transversal** de "user revisou X em DATE" para campos derivados que vivem em **aggregates de leitura** (E5 payload, IRPF metadata, balance_sheet, Risk).

### Por que `Decision.source` resolveria errado

Adicionar `source` a `Decision` quebraria a semântica editorial do aggregate:

1. **Toda `Decision` é declarada por construção** — adicionar coluna seria 100% das linhas com mesmo valor (`user_declared`).
2. **Confirmar uma memória derivada (ex.: "aporte mensal de R$ 7.450 calculado de extratos") NÃO deveria criar `Decision`** — não é decisão editorial, é endosse de leitura.
3. **Criar `Decision` para confirmação infla o aggregate** e contamina queries de plano de ação ("Top 5 Decisões de Impacto" do card S10) com endossos não-acionáveis.

## Decisão

Introduzir **padrão transversal de tracking de confirmação** desacoplado de `Decision`/`Goal`/IRPF. Tabela própria, escopo workspace, append-only, indexada por aggregate de origem.

### Estrutura

Nova tabela `workspace_memory_confirmations` (Alembic migration), schema mínimo:

```python
class WorkspaceMemoryConfirmation(Base):
    """Endosse de user para campo derivado de aggregate de leitura.
    Append-only: confirmação posterior sobrepõe via timestamp, mas
    histórico permanece.
    """
    __tablename__ = "workspace_memory_confirmations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Identifica o fato confirmado de forma estável.
    # Formato: "<aggregate>.<field_path>" — exemplos:
    #   "e5.patrimonio.liquido"
    #   "irpf_metadata.regime_dominante"
    #   "balance_sheet.imoveis[uuid].valor_mercado"
    memory_key: Mapped[str] = mapped_column(String(256), nullable=False)
    # Aggregate fonte (referência simbólica para debug; não FK).
    source_aggregate: Mapped[str] = mapped_column(String(64), nullable=False)
    # Snapshot do valor confirmado no momento (para detectar invalidação
    # quando aggregate de origem muda).
    confirmed_value_snapshot: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
    )
    confirmed_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    # Razão opcional declarada pelo user ("revisei e está correto",
    # "corrigi de R$ 7.500 para R$ 7.450"). Quando preenchido com
    # correção, deve haver Goal/Decision/workspace settings write
    # correspondente — auditável.
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workspace = relationship("Workspace")

    __table_args__ = (
        Index("ix_wmc_ws_key", "workspace_id", "memory_key"),
        Index("ix_wmc_ws_confirmed_at", "workspace_id", "confirmed_at"),
    )
```

### Semântica de cada origem

| Origem visual em memories | Como detectar |
|---|---|
| **Declarada** | Aggregate canônico (`Goal`, `Decision`, `family_members`, workspace settings) tem registro vigente com `created_by` (user_id). Memory surface lê do aggregate diretamente. |
| **Derivada (não-confirmada)** | Campo presente em E5 payload / IRPF metadata / balance_sheet, **sem** entrada correspondente em `workspace_memory_confirmations` para o `(workspace_id, memory_key)`. |
| **Derivada confirmada** | Campo presente no aggregate de leitura **+** entrada em `workspace_memory_confirmations` com `confirmed_at` mais recente que `updated_at` do aggregate de origem (snapshot ainda válido). |
| **Derivada com correção** | User clicou "Corrigir" — sistema escreve `Goal` / `Decision` / workspace setting novo (origem declarada) **e** registra entrada em `workspace_memory_confirmations` com `note: "corrigido de X para Y"` apontando para o derived original. |

### Invalidação de confirmação

Quando aggregate de leitura **muda** (pipeline re-roda e gera novo valor derivado), confirmação prévia vira "stale" — UI mostra "Você confirmou R$ 7.450 em 12/mar; agora calculamos R$ 7.620 (variação ≥ 2%). Confirmar novamente?". Critério de stale:

- **Mudança absoluta significativa:** `|valor_atual - valor_confirmado| / valor_confirmado ≥ 2%` para valores monetários.
- **Mudança categórica:** qualquer alteração para campos enum/string (regime IRPF, alocação alvo).
- **Tempo desde confirmação ≥ 12 meses:** force re-confirmação anual (alinhado com revisão metodológica de F6 risk profile e demais).

## Consequências

### Positivas

- **`Decision` aggregate preserva semântica editorial** — não vira balde de endossos não-acionáveis.
- **Confirmação cross-aggregate** — mesmo padrão serve E5, IRPF metadata, Risk, family_members, workspace settings. Memories surface tem 1 padrão para distinção visual.
- **Audit trail preservado** — confirmação tem `confirmed_by_user_id` + `confirmed_at`; correção tem write correspondente no aggregate canônico + `note`. Compatível com Fase 3.E KR secundário ("≥ 90% edições resolvem para aggregate canônico").
- **Cônjuge multi-tenant** — `confirmed_by_user_id` permite mostrar "Ana confirmou em 12/mar" no audit trail leve (D4 do designer).
- **Stale detection** — confirmação anual re-perguntada respeitando INV2 (risk re-questionário) e INV3 (IF revisão).

### Negativas / trade-offs

- **Nova tabela = nova migration + repositório.** Custo de ~80-120 linhas de código (model + repo + 1 service `memory_confirmation_service.py`). Aceitável dado o ganho de coerência cross-aggregate.
- **Storage:** confirmação por workspace por memory_key — base dogfood pequena hoje, mas escala linearmente. Mitigação: índice composto + retenção (manter apenas confirmação mais recente por `(workspace_id, memory_key)`? **Recomendação inicial: append-only, sem truncar** — barato e audit-friendly).
- **`memory_key` string opaca** — formato "aggregate.field_path" é convenção, não enum. Mitigação: documentar lista canônica em `pipeline/domain/services/memory_keys.py` (sem virar enum hard — Memories surface evolui rápido). Reviews de PR conferem aderência.
- **Snapshot vs lookup live** — `confirmed_value_snapshot` duplica valor que vive no aggregate de origem. Mitigação: snapshot é só para detectar stale; queries de display sempre re-leem do aggregate de origem.

### Risco assimétrico

- **Padrão precisa pegar.** Se developers começarem a marcar "derivada confirmada" em locais ad-hoc (workspace settings JSON, flag em Goal), o padrão fragmenta. Mitigação: code review enforça uso do service `memory_confirmation_service.confirm(ws, memory_key, user, snapshot)`.
- **Não cobre "memória puramente declarada por user fora de aggregate canônico"** — anti-pattern §7.1 do discovery (mural de post-its). Compatível com decisão de plano de não criar `WorkspaceFact` aggregate v2 (abstração prematura). Se aparecer demanda, abre ADR separada.

## Sequência operacional

1. **PR-A (esta ADR):** mergeada como `Proposto`.
2. **PR-B:** model + migration Alembic + repositório + service `memory_confirmation_service.py` + testes unitários. Branch: `agent/adr-262-memory-confirmation/<ts>`. Owner: `senior-cto`.
3. **PR-C:** integração no payload E5 (campo `confirmations_metadata: dict[str, bool]` por memory_key derivada — calculado on-read para Memories surface não precisar de join custoso). Owner: `senior-cto` + `data-engineer`.
4. **PR-D:** consumido pelo MVP de 3.E (ADR `financial-memories-surface`) — não materializado nesta ADR.

## Critério de aceite (`Proposto` → `Decidido`)

- [ ] PR-A mergeado (esta ADR).
- [ ] PR-B mergeado: model + migration + service + ≥80% coverage de unit tests.
- [ ] PR-C mergeado: E5 payload exposes `confirmations_metadata` consumível pela API.
- [ ] Memory surface MVP (3.E) usa exclusivamente esta tabela para origem visual derivada↔confirmada — **zero** flags ad-hoc em outros aggregates.
- [ ] Audit gate: hook pre-commit `dev/check_memory_keys.py` (se materializado) valida que strings `memory_key` aderem ao formato `<aggregate>.<field_path>`.

Promoção a `Decidido (Sprint XX.Y)` ocorre quando 3.E MVP estiver live em produção com pelo menos 5 workspaces dogfood usando o padrão.
