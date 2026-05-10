---
id: TRACK-report-publication-impl
type: track
title: "Report publication — schema + API + helper (mês fechado imutável)"
lane: "[[A11.report-publication]]"
sprint: A11
plan: null
status: ready
created_at: "2026-05-10"
consumed_at: null
agent_role: data-engineer + senior-cto
tags:
  - type/track
  - sprint/a11
  - status/ready
  - area/report
  - area/methodology
  - phase/a11
---

# Track — Report publication (mês fechado imutável)

> **Lane ID:** A11.report-publication
> **Branch prefix:** `agent/report-publication-impl/<yyyyMMdd-HHmm>`
> **Depende de:** —
> **Paralelo com:** A11.w2, A11.w5, A11.competitive-pierre (não toca
> código de pipeline E4, categorização, nem rotas Pierre)
> **Conflita com:** outra sessão `agent/report-publication-*` ativa
> **Sprint:** A11
> **Time-box:** ≤3 dias eng (1 backend + 0,5 frontend para badge mínimo)
> **Owner sugerido:** `data-engineer` (lead) + `senior-cto` (review API +
> contrato de imutabilidade)
> **Decisão arquitetural:** [[ADR-187]]
> **Habilita** (mas não é mais "fase 0 de"): [[A12.cat-learning-loop]]
> ([[ADR-186]]) — pré-requisito externo para P2 daquela lane.
> **Reusabilidade:** mesma invariante atende Decision aggregate, IRPF
> declarado, cenários comparativos congelados.
> **Fonte de verdade das regras:** [CLAUDE.md](../../../../CLAUDE.md)

---

## 1. Objetivo

Introduzir conceito de **"relatório publicado / mês fechado"** no domínio
do Mathoms. Evento explícito, imutável, auditável, que serve de barreira
para qualquer mutação retroativa em dados consolidados.

**Não-objetivos:**

- Não tocar pipeline E4 (consumidor real entra em [[A12.cat-learning-loop]]).
- Não tocar categorização (schema dessas tabelas é A12 P1).
- Não auto-publicar (manual V1; auto-publish fica em backlog futuro).
- Não escrever UI completa de "publicar mês" (só o banner de leitura V1;
  CTA "Publicar mês" entra em sprint posterior junto com polish UX).

## 2. Por que esta lane existe

Co-design `financial-planner` (sessão 2026-05-10) flagou que
re-categorização retroativa proposta em [[ADR-186]] (learning loop)
viola snapshot do mês fechado AUVP. Sem barreira temporal, regras criadas
em maio mudariam gráficos de janeiro, quebrando contrato implícito com
cliente.

Review `product-manager` (mesma sessão) promoveu este trabalho a lane
**standalone em A11** (em vez de fase P0 do learning loop) por três
razões:

1. **Reusabilidade:** mesma invariante atende Decision aggregate
   ([[ADR-136]]), IRPF declarado ([[ADR-178]]), cenários comparativos
   congelados.
2. **Custo isolado:** 3d eng cabe entre W2 e W3 do PLATFORM_REVIEW sem
   roubar capacidade de hardening.
3. **Desacopla:** [[A12.cat-learning-loop]] passa a depender de invariante
   já em produção, não de fase própria — reduz risco de slippage cruzado.

Ver [[ADR-187]] para racional arquitetural completo.

## 3. Entregáveis

### 3.1. Migration Alembic

```sql
CREATE TABLE report_publications (
  id              UUID PRIMARY KEY,
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  period_yyyymm   CHAR(6) NOT NULL,                 -- '202601'
  artifact_id     UUID NOT NULL REFERENCES pipeline_artifacts(id),
  published_at    TIMESTAMPTZ NOT NULL,
  published_by    VARCHAR(64) NOT NULL,
  immutable_hash  VARCHAR(64) NOT NULL,
  unpublished_at  TIMESTAMPTZ NULL,
  CONSTRAINT chk_period_format CHECK (period_yyyymm ~ '^[0-9]{6}$')
);

CREATE UNIQUE INDEX uq_report_pub_active
  ON report_publications (workspace_id, period_yyyymm)
  WHERE unpublished_at IS NULL;

CREATE INDEX ix_report_pub_workspace ON report_publications (workspace_id);
```

- Backfill: workspaces existentes ficam **sem publicações** (default
  inclusive: mês NÃO está fechado se não tem linha viva).
- Up + down testado em `backend/tests/test_alembic_up_down.py`.

### 3.2. Model + repo

- `backend/app/models/report_publication.py` — SQLAlchemy model.
- `backend/app/repositories/report_publication_repo.py` — async repo
  com `get_active(workspace_id, period)`, `publish(...)`,
  `unpublish(id)`, `list_by_workspace(workspace_id)`.

### 3.3. Helper canônico

```python
# backend/app/services/report_publication.py

async def is_month_closed(
    workspace_id: str,
    period_yyyymm: str,
    *,
    db: AsyncSession,
) -> bool:
    """Verifica se há report_publication viva para o (workspace, período).

    Único ponto de leitura para invariante temporal de imutabilidade.
    Qualquer caller que precisa decidir "posso re-categorizar/editar este
    período?" consulta esta função.
    """
```

### 3.4. Endpoints REST

```
POST   /workspaces/{ws}/reports/{period}/publish     201
DELETE /workspaces/{ws}/reports/{period}/publish     204
GET    /workspaces/{ws}/reports/publications        200
```

- `response_model` explícito ([[ADR-109]]) — `ReportPublicationResponse`
  para POST/GET; 204 No Content para DELETE.
- Bodies: POST aceita `{artifact_id: str}`; DELETE sem body.
- Erros: 404 se artifact não existe; 409 se já publicado (POST) ou
  já despublicado (DELETE).
- Snapshot OpenAPI atualizado: `make update-openapi-snapshot`.

### 3.5. Pydantic schemas

```python
# backend/app/schemas/report_publication.py

class ReportPublicationResponse(BaseModel):
    id: str
    workspace_id: str
    period_yyyymm: str
    artifact_id: str
    published_at: datetime
    published_by: str
    immutable_hash: str
    unpublished_at: datetime | None
```

### 3.6. UI mínima — indicador "mês fechado"

> Escopo mínimo nesta lane. Polish (badge no header da seção mensal,
> ação "Publicar mês" em `/config`) fica em sprint posterior junto com
> UX dedicada de gerenciamento de publicações.

- Banner cinza no `frontend/src/app/(app)/reports/[id]/page.tsx`
  quando o relatório carregado é um `period` com publication ativa:
  "Relatório publicado em {published_at}. Mudanças retroativas
  bloqueadas para este mês."
- Estilo: `var(--surface-muted)` + `var(--text-muted)`. Não-clickável
  V1.

### 3.7. Documentação

`docs/reference/REPORT_PUBLICATION.md` (≤120 linhas):

- Semântica: "publicação viva" vs "despublicada".
- Default policy: workspace sem linha → mês está em aberto.
- Quem chama `is_month_closed`: lista atual + futura
  ([[ADR-186]] §D2 será o primeiro consumidor real em P2).
- Como publicar/despublicar via API.
- Como o hash é calculado (SHA-256 do snapshot E7 normalizado).

## 4. Critério de aceite

- [ ] Migration up/down verde (`pytest backend/tests/test_alembic_up_down.py`).
- [ ] Helper `is_month_closed` coberto por testes unitários incluindo:
      caso sem linha (False), caso linha viva (True), caso linha
      despublicada (False), caso 2 linhas com 1 viva (True).
- [ ] Endpoints cobertos por testes integration (publish → assert
      `is_month_closed=True` → unpublish → assert `is_month_closed=False`).
- [ ] Snapshot OpenAPI atualizado (`backend/tests/test_openapi_snapshot.py`
      verde após `make update-openapi-snapshot`).
- [ ] `dev/check_pipeline_boundaries.py` continua verde (helper vive em
      `backend/app/services/`, não em `pipeline/`).
- [ ] Doc `docs/reference/REPORT_PUBLICATION.md` criado e linkado em
      [docs/reference/ARCHITECTURE.md](../../../reference/ARCHITECTURE.md)
      §1 ou §10.
- [ ] Banner UI no relatório aparece quando há publicação viva (teste
      manual + Playwright `@critical` opcional).
- [ ] [[ADR-187]] flippada para `Decidido (A11.report-publication)`
      no PR de merge.
- [ ] PR description linka `[[ADR-187]]` e `[[A11.report-publication]]`.

## 5. Fora do escopo (não tocar)

- **Não tocar `pipeline/`** — `is_month_closed` é consumido em
  [[A12.cat-learning-loop]] P3 pelo backend, não pelo pipeline.
- **Não tocar `categorization_*`** — schema dessas tabelas é A12 P1.
- **Não auto-publicar** — manual V1 (auto-publish fica em backlog futuro).
- **Não escrever UI de "publicar mês"** — só o banner de leitura V1.
  CTA "Publicar mês" entra em sprint posterior.

## 6. Riscos & mitigações

| Risco | Mitigação |
|---|---|
| Hash imutável calculado com inconsistência (timestamp variável). | Normalizar snapshot E7 antes do hash: ordenar chaves JSON, remover `generated_at`, etc. Função `compute_immutable_hash(snapshot: dict) -> str` testada. |
| Workspace legado tem dados antigos que cliente já recebeu por PDF. | Default policy é "aberto" — cliente precisa publicar manualmente se quiser barreira histórica. Documentar em `REPORT_PUBLICATION.md`. |
| Concurrency: 2 publishs simultâneos para mesmo período. | Unique index com `WHERE unpublished_at IS NULL` + tratamento de `IntegrityError` retornando 409. |
| Soft-delete acumula linhas órfãs de testes. | Fixture cleanup em `conftest.py`; produção não tem volume relevante (≤12 publishs/ano/workspace). |

## 7. Comandos de validação local

```bash
# Migration
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head

# Testes
pytest backend/tests/test_alembic_up_down.py -q
pytest backend/tests/test_report_publication_helper.py -q
pytest backend/tests/integration/test_report_publication_api.py -q

# OpenAPI
make update-openapi-snapshot
git diff backend/tests/openapi_snapshot.json   # revisar diff esperado

# Boundaries
python3 dev/check_pipeline_boundaries.py

# Pre-commit completo
pre-commit run --all-files
```

## 8. Handoffs ao final

- Atualizar `docs/sprint/A11/lanes/A11-report-publication.md` marcando
  status `done`.
- Mover este track para `consumed` no frontmatter +
  `consumed_at: <date>`.
- Adicionar entrada em `docs/CHANGELOG.md` (1-2 linhas: "feat(report):
  conceito de mês fechado imutável (ADR-186)").
- Sinalizar em `docs/sprint/A12/_README.md` §Pré-requisitos externos
  que A11.report-publication mergeou — destrava P2 de
  [[A12.cat-learning-loop]].

## 9. Por que vale a pena

Habilita [[ADR-186]] (learning loop em A12) sem violar confiança do
cliente (lição Mint: auto-promote silencioso destrói credibilidade).
Conceito reusável para futuras invariantes (Decision histórica imutável,
recomendação fiscal arquivada, cenário comparativo congelado). Custo:
3d eng. Ganho duplo: viabiliza feature de aprendizado **e** entrega
invariante de produto premium isoladamente útil.
