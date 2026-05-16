> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CONTEXT_FRONTEND - app e relatorio

Use para Next.js, componentes do relatorio, UX, design tokens, copy e testes UI.

## Leia primeiro

- [`PRODUCT`](../../reference/PRODUCT.md) - intencao do produto.
- [`COPY_GUIDELINES`](../../reference/COPY_GUIDELINES.md) - tom e restricoes publicas.
- [`REPORT_PREMIUM`](../../plan/REPORT_PREMIUM/_README.md) - plano canonico do relatorio.
- [`MOBILE_SPEC`](../../plan/REPORT_PREMIUM/MOBILE_SPEC.md) - comportamento responsivo.
- [`A11Y_CHECKLIST`](../../plan/REPORT_PREMIUM/A11Y_CHECKLIST.md) - gate acessibilidade.

## Hot paths

- `frontend/src/app/` - rotas Next.
- `frontend/src/components/report/` - relatorio premium.
- `frontend/src/generated/` - tipos/codegen; nao editar manualmente.
- `frontend/tests/` - Vitest e Playwright.
- `design-tokens/` e `frontend/src/styles/` - tokens e CSS base.

## Checks comuns

- Unit: `cd frontend && npm test -- --run`.
- E2E critico: `cd frontend && npm run test:e2e`.
- Codegen quando layout muda: `python3 dev/codegen_report_layout.py --check`.
- Visual/a11y: seguir checklist do plano antes de declarar pronto.

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
