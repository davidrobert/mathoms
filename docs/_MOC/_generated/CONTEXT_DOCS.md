> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CONTEXT_DOCS - vault e economia de tokens

Use para editar docs, criar plano/ADR/lane/track ou investigar a organizacao da vault.

## Leia primeiro

- [`00-INDEX`](../00-INDEX.md) - entrada editorial da vault.
- [`DOC_STATS`](DOC_STATS.md) - inventario compacto.
- [`SPRINT_CURRENT`](SPRINT_CURRENT.md) - trabalho ativo.
- [`PLAN_PROGRESS`](PLAN_PROGRESS.md) - planos canonicos e lanes ligadas.
- [`CHANGELOG_RECENT`](CHANGELOG_RECENT.md) - entregas recentes.

## Onde escrever

- Plano multi-fase: `docs/plan/<TOPIC>/_README.md`.
- Lane/track operacional: `docs/sprint/<SPRINT>/lanes/` ou `docs/sprint/<SPRINT>/tracks/`.
- Decisao arquitetural/produto: `docs/adr/NNN-slug.md`.
- Referencia estavel: `docs/reference/`.
- Historico substituido: `docs/archive/` com nota no indice do archive.

## Gates de docs

- `python3 dev/validate_frontmatter.py`.
- `python3 dev/check_doc_filename_id.py`.
- `python3 dev/check_doc_links.py`.
- `python3 dev/check_doc_markdown_links.py --report --limit 0`.
- `python3 dev/build_doc_index.py --check`.
- `python3 dev/benchmark_doc_token_cost.py --check`.

## Politica de token

- Leia MOCs e packs antes de abrir documentos longos.
- Busque por bucket; nao faca varredura ampla em `docs/archive/**`.
- Links quebrados em docs ativos sao bloqueantes; archive e arqueologia.

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
