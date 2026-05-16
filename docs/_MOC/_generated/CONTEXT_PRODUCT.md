> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CONTEXT_PRODUCT - dominio financeiro

Use para regras de planejamento, relatorio ao cliente, metodologia e copy de produto.

## Leia primeiro

- [`PRODUCT`](../../reference/PRODUCT.md) - promessa e escopo do produto.
- [`FORMULAS`](../../reference/FORMULAS.md) - formulas e conceitos calculados.
- [`reference/rules`](../../reference/rules/) - regras de dominio materializadas.
- [`PLAN_PROGRESS`](PLAN_PROGRESS.md) - iniciativas abertas por plano.
- [`ADR_INDEX`](ADR_INDEX.md) - decisoes de produto e dominio.

## Guardrails

- Nao invente regra financeira: consulte `config/`, `reference/rules/` e ADRs.
- Dados sensiveis nunca entram em docs, fixtures, logs ou exemplos.
- Methodology = code: regra universal vive perto do enforcer + ADR.
- Copy publica nao atribui marcas/metodologias de terceiros.
- Mudanca em dinheiro, reserva, divida, IF ou alocacao pede `financial-planner`.

## Busca economica

- Comece por `rg <conceito> docs/reference docs/plan docs/adr`.
- Se a pergunta for sobre sprint, use `docs/sprint/<X>/` em vez de vault inteira.
- Abra `docs/archive/**` so para entender decisao historica ou plano substituido.

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
