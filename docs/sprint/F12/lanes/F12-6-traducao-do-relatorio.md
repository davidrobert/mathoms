---
id: F12.6
type: lane
title: "Tradução do relatório (bulk, paralelizável)"
sprint: F12
status: open
priority: P0
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f12
  - status/open
  - priority/p0
---


# F12.6 — Tradução do relatório (bulk, paralelizável)


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.6a | Migrar ~85 componentes de `frontend/src/components/report/` strings → `messages/pt-BR.json`. ICU MessageFormat para plurais. ESLint rule custom proíbe novas strings literais em JSX. | P0 | 10h | ⏳ |
| F12.6b | Script `dev/translate_messages.py` (DeepL Pro + glossário fintech `config/i18n_glossary.yaml`). Custo estimado ~$1.800 (DeepL Pro + chars overage). Marca `_meta.mt: true` por chave. | P0 | 15h | ⏳ |
| F12.6c | Revisão humana por nativo nos 9 locales não-pt-BR (~5h cada = 45h externas). Marca `_meta.mt: false` quando ratificado. Locale liberado para produção quando ratio MT < 5%; acima disso, banner "beta". | P0 | 5h ext./locale | ⏳ |
