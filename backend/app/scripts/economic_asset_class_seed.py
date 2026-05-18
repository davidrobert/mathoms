"""Lista canônica das 10 classes AUVP (ADR-219 D2)."""

CANONICAL_ASSET_CLASSES: list[dict] = [
    {"code": "caixa", "label": "Caixa / Liquidez", "sort_order": 5},
    {"code": "rf_pos", "label": "Renda Fixa pós-fixada (CDI, Selic)", "sort_order": 10},
    {"code": "rf_pre", "label": "Renda Fixa prefixada", "sort_order": 20},
    {"code": "rf_inflacao", "label": "Renda Fixa indexada à inflação (IPCA+)", "sort_order": 30},
    {"code": "acoes_br", "label": "Ações Brasil", "sort_order": 40},
    {"code": "acoes_intl", "label": "Ações Internacional", "sort_order": 50},
    {"code": "fii", "label": "Fundos Imobiliários (FII)", "sort_order": 60},
    {"code": "imoveis_diretos", "label": "Imóveis físicos", "sort_order": 70},
    {"code": "cambio_usd", "label": "Câmbio USD", "sort_order": 80},
    {"code": "cambio_eur", "label": "Câmbio EUR", "sort_order": 81},
]
