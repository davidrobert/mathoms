# Report publication — mês fechado imutável (ADR-186)

> Source-of-truth da semântica e dos invariantes.
> Decisão arquitetural: [ADR-186](../adr/186-relatorio-publicado-imutavel-mes-fechado.md).

## Conceito

Uma **publicação de relatório** é um evento explícito, imutável e auditável
que congela o relatório de um período (`YYYYMM`) para um workspace.

- Linha **viva** (`unpublished_at IS NULL`) → mês está **fechado** para
  aquele `(workspace_id, period_yyyymm)`.
- Linha **revogada** (`unpublished_at IS NOT NULL`) → publicação foi
  desfeita; mantém histórico para auditoria.

Mutações retroativas em dados consolidados (re-categorização automática,
edição de transação em mês passado, reanálise downstream) **devem
respeitar a barreira** consultando o helper canônico
`backend.app.services.report_publication.is_month_closed`.

## Default policy

Workspace **sem linha** para um período → mês NÃO está fechado, regras
podem mutar livremente. Backfill manual opcional para clientes legados
que já receberam PDFs assinados e querem barreira histórica.

## API

| Método | Path | Status | Descrição |
|---|---|---|---|
| `POST` | `/workspaces/{ws}/reports/{period}/publish` | 201 / 409 / 404 | Publica o período. Body: `{artifact_id: int}`. 409 se já há publicação viva; 404 se artifact não existe / pertence a outro workspace. |
| `DELETE` | `/workspaces/{ws}/reports/{period}/publish` | 204 / 409 | Revoga publicação viva (soft-delete). 409 se mês está em aberto. |
| `GET` | `/workspaces/{ws}/reports/publications` | 200 | Histórico completo (vivas + revogadas), ordenado por período desc. |
| `GET` | `/workspaces/{ws}/reports/{period}/publication` | 200 | Publicação viva ou `null` se mês está aberto. |

`{period}` é `YYYYMM` (6 dígitos). Schema OpenAPI canônico em
`docs/reference/api/v1/openapi.json` (regenerado por
`make update-openapi-snapshot` após mudanças).

## Hash imutável

`compute_immutable_hash(snapshot: dict) -> str` produz SHA-256 do
snapshot E7 normalizado:

1. Remove chaves voláteis recursivamente (`generated_at`, `rendered_at`,
   `computed_at`, `schema_version`).
2. Serializa com `json.dumps(sort_keys=True, ensure_ascii=False,
   separators=(",", ":"))`.
3. Calcula SHA-256 hex.

Estável entre runs idênticos: re-publicar com mesmo conteúdo produz
mesmo hash. Mudança real altera hash — detecta tentativa de
"re-publicar com diferente" silenciosamente (ADR-186 alternativa B).

## Helper canônico — `is_month_closed`

```python
from backend.app.services.report_publication import is_month_closed

closed = await is_month_closed(workspace_id, "202601", db=db)
```

**Único** ponto de leitura da invariante. Callers atuais e planejados:

| Caller | Uso |
|---|---|
| ADR-186 V1 | Banner UI no relatório (`MonthClosedBanner`) e API. |
| Learning loop (futuro, A12) | Pré-condição para re-categorizar transação retroativa via promoção de regra. |
| Decision aggregate (futuro) | Bloquear edição de Decision após mês fechado. |
| IRPF declarado (futuro) | Congelar dedução fiscal na publicação. |

## Invariantes garantidos

1. **Unicidade**: máximo 1 publicação viva por `(workspace_id,
   period_yyyymm)` — partial unique index.
2. **Auditabilidade**: linhas revogadas nunca são deletadas; sequência
   `published_at`/`unpublished_at` é o trail.
3. **Isolamento por workspace**: hash, helper e endpoints filtram
   por `workspace_id` (R13/R14, ADR-101).
4. **Default inclusive**: ausência de linha = mês aberto (não bloqueia
   produto pré-A11).

## Quem publica

V1 (esta ADR): publicação **manual e explícita** via POST. Sem
auto-publish, sem deadline. Cliente/planejador decide quando o mês está
fechado.

V2 (futuro, fora de A11): auto-publish após N dias do fim do mês com
janela de "edição quente". UI dedicada de gerenciamento (CTA "Publicar
mês" em `/config` ou no header do relatório) entra em sprint posterior.

## Onde está o código

- Migration: `backend/alembic/versions/d6e7f8a9b0c1_adr186_report_publications.py`.
- Model: `backend/app/models/report_publication.py`.
- Repository: `backend/app/repositories/report_publication_repository.py`.
- Service: `backend/app/services/report_publication.py`.
- Schemas (Pydantic): `backend/app/schemas/report_publication.py`.
- Router: `backend/app/api/report_publications.py`.
- UI: `frontend/src/components/report/MonthClosedBanner.tsx` +
  `frontend/src/lib/api/report-publications.ts`.
- Tests: `backend/tests/test_report_publication_helper.py` +
  `backend/tests/integration/test_report_publication_api.py`.
