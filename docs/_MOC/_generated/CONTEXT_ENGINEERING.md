> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CONTEXT_ENGINEERING - mudancas gerais

Use para tarefas que cruzam arquitetura, tests, CI, contratos ou varios buckets.

## Leia primeiro

- [`SPRINT_CURRENT.md`](SPRINT_CURRENT.md) - lanes ativas e prontas.
- [`PLAN_PROGRESS.md`](PLAN_PROGRESS.md) - planos canonicos abertos e status.
- [`ADR_INDEX.md`](ADR_INDEX.md) - decisoes vigentes por area.
- [`DOC_STATS.md`](DOC_STATS.md) - tamanho da vault antes de buscar.
- [`CLAUDE.md`](../../../CLAUDE.md) - invariantes de agente e protocolo git.

## Onde procurar

- Arquitetura tecnica: [`ARCHITECTURE`](../../reference/ARCHITECTURE.md).
- Setup/runbook/testes: [`SETUP`](../../reference/SETUP.md), [`RUNBOOK`](../../reference/RUNBOOK.md), [`TESTING`](../../reference/TESTING.md).
- Pipeline/artifacts: [`PIPELINE_ARTIFACTS`](../../reference/PIPELINE_ARTIFACTS.md).
- De onde vem um numero (arqueologia de valor): `python3 dev/explain_number.py --field <path> --format llm` (lineage ADR-281, ~80 tok vs ler stage inteiro).
- Planos grandes: [`docs/plan`](../../plan/).
- Lanes/tracks: [`docs/sprint`](../../sprint/).

## Invariantes que evitam retrabalho

- Dinheiro nunca e `float`; siga ADR-090.
- `pipeline/**` nao importa FastAPI/Celery/SQLAlchemy.
- Backend e pipeline devem ser stateless salvo excecoes registradas.
- JSON endpoint novo exige `response_model` e snapshot OpenAPI.
- ArtifactStore e DB-only; testes injetam store explicito.

## Verificacao base

- Docs: `python3 dev/build_doc_index.py --check` e `python3 dev/check_doc_markdown_links.py --report`.
- Python touched files: `.venv/bin/ruff check <files>`.
- Suite direcionada: rode o menor pytest que cubra o contrato alterado.

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
