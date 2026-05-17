> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CONTEXT_INDEX - leitura minima por intencao

Use este indice antes de abrir a vault inteira. Escolha 1 pack, leia as fontes
indicadas e so depois faca buscas estreitas com `rg`.

| Intencao | Pack | Fontes curtas sempre uteis |
| --- | --- | --- |
| Engenharia geral | [`CONTEXT_ENGINEERING`](CONTEXT_ENGINEERING.md) | [`SPRINT_CURRENT`](SPRINT_CURRENT.md), [`PLAN_PROGRESS`](PLAN_PROGRESS.md), [`ADR_INDEX`](ADR_INDEX.md) |
| Backend/API/pipeline | [`CONTEXT_BACKEND`](CONTEXT_BACKEND.md) | [`ARCHITECTURE`](../../reference/ARCHITECTURE.md), [`PIPELINE_ARTIFACTS`](../../reference/PIPELINE_ARTIFACTS.md) |
| Frontend/relatorio | [`CONTEXT_FRONTEND`](CONTEXT_FRONTEND.md) | [`PRODUCT`](../../reference/PRODUCT.md), [`COPY_GUIDELINES`](../../reference/COPY_GUIDELINES.md) |
| Produto/dominio financeiro | [`CONTEXT_PRODUCT`](CONTEXT_PRODUCT.md) | [`FORMULAS`](../../reference/FORMULAS.md), [`reference/rules`](../../reference/rules/) |
| Documentacao/vault | [`CONTEXT_DOCS`](CONTEXT_DOCS.md) | [`00-INDEX`](../00-INDEX.md), [`DOC_STATS`](DOC_STATS.md) |

Regra de economia: evite `rg docs` amplo. Prefira `rg <termo> docs/reference docs/plan`
ou o bucket indicado pelo pack. Consulte `docs/archive/**` apenas para arqueologia.

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
