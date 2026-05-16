> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CONTEXT_BACKEND - API, pipeline e dados

Use para FastAPI, pipeline, DB, migrations, artifacts, auth e jobs.

## Leia primeiro

- [`ARCHITECTURE`](../../reference/ARCHITECTURE.md) - stack, camadas e glossary.
- [`PIPELINE_ARTIFACTS`](../../reference/PIPELINE_ARTIFACTS.md) - contrato de artefatos.
- [`RUNBOOK`](../../reference/RUNBOOK.md) - operacao e incidentes.
- [`STATELESS_AUDIT`](../../reference/STATELESS_AUDIT.md) - globais permitidos.
- [`ADR_INDEX`](ADR_INDEX.md) filtrando mentalmente por API, pipeline, auth, DB e LLMOps.

## Hot paths

- `backend/app/api/` - routers e DTO boundaries.
- `backend/app/application/` - use cases.
- `backend/app/repositories/` e `backend/alembic/` - persistencia/migrations.
- `backend/app/services/` - adapters e integracoes.
- `pipeline/domain/services/` - regras puras de dominio.
- `config/schemas/` - contratos JSON.

## Checks comuns

- Backend: `pytest backend/tests -q`.
- Pipeline: `pytest tests -q` ou teste unitario/golden direcionado.
- Boundary: `python3 dev/check_pipeline_boundaries.py`.
- Frontmatter/docs se mexer em ADR/plano: `python3 dev/validate_frontmatter.py`.

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
