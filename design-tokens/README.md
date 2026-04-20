# Design Tokens — Ferreira Campos Editorial

Fonte única de tokens de design do produto Mathoms AI. Ver **ADR-076** em [../docs/DECISIONS.md](../docs/DECISIONS.md).

## Estrutura

```
design-tokens/
├── tokens.json              ← FONTE DE VERDADE (editar aqui)
├── build.py                 ← gera CSS
└── README.md
```

Saídas geradas (não editar à mão):

```
frontend/src/styles/tokens.css       ← site (Next.js + Tailwind v4 @theme inline)
config/templates/_tokens.css         ← relatório standalone (E6)
```

## Uso

Gerar:
```bash
python3 design-tokens/build.py
```

Verificar sync (usado no pre-commit e CI):
```bash
python3 design-tokens/build.py --check
```

## Categorias de tokens

- **typography** — fontes (display/body/mono), tamanhos, pesos, line-heights
- **spacing** — escala 4px
- **radius** — cantos
- **shadow** — elevação (light + dark)
- **modes.light / modes.dark** — paletas por modo:
  - `brand` (primary, accent, danger, warning, neutral, info)
  - `surface` (background, card, border, muted…)
  - `semantic` (gain, loss, alert — domínio financeiro)
  - `chart` (12 cores categóricas)
  - `sidebar`
- **card_variants** — variantes do relatório (highlight, feature, success, warn, critical, primary, neutral, top-danger, top-accent)

## Regras de uso

1. Nenhum literal hex ou cor OKLch fora de `tokens.json`.
2. Nenhum `font-family:` fora de `tokens.css`.
3. Valores monetários SEMPRE com `font-mono` + `tabular-nums` — use o componente `<MonetaryValue/>`.
4. Variantes de card são consumidas via classe `.card-variant-<nome>` — não reestilize à mão.

## Fluxo de mudança

1. Edita `tokens.json`.
2. Roda `python3 design-tokens/build.py`.
3. Commita os 3 arquivos (tokens.json + 2 CSS gerados).
4. Pre-commit valida sync via `--check`.
