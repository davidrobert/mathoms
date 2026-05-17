---
id: F12.6
type: lane
title: "Tradução do relatório (bulk, paralelizável)"
sprint: F12
plan: PLAN-i18n
status: blocked
priority: P0
adrs: ["[[ADR-130]]"]
depends_on: ["[[F12.2]]", "[[F12.4]]"]
parallel_with: []
tags:
  - type/lane
  - sprint/f12
  - status/blocked
  - priority/p0
---


# F12.6 — Tradução do relatório (bulk, paralelizável)


> 🚧 **Blocked-by-gate.** Aguarda gatilho de §10 do
> [plan/I18N/_README.md](../../../plan/I18N/_README.md). Escopo: 3 locales
> (pt-BR + en + es) — 2 locales a traduzir (en + es). Pré-requisito
> material: F12.2 + F12.4 mergeadas.

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.6a | Migrar ~85 componentes de `frontend/src/components/report/` strings → `messages/pt-BR.json`. ICU MessageFormat para plurais (2-form em pt-BR/en/es). ESLint rule custom proíbe novas strings literais em JSX. Banner "Brazilian fiscal residency assumed" em EN/ES nas seções tributárias do relatório (edge case nômade pós-DSDP — produto real fica em frente separada). | P0 | 10h | ⏳ |
| F12.6b | Script `dev/translate_messages.py` (DeepL Pro + glossário canônico `config/i18n_glossary.yaml`). Aplica buckets: `do_not_translate` passa intacto (IRPF/PGBL/CDB/FII/JCP/INSS/FGTS/Selic/CDI/...); `inline_glossary` insere tooltip/abbr na primeira ocorrência; `translate` segue DeepL normalmente. Custo estimado ~$400 (DeepL Pro + chars overage). Marca `_meta.mt: true` por chave. | P0 | 5h | ⏳ |
| F12.6c | Revisão humana por nativo nos 2 locales não-pt-BR (~5h cada = 10h externas). Confere que termos `do_not_translate` aparecem intactos no DOM. Marca `_meta.mt: false` quando ratificado. Locale liberado para produção quando ratio MT < 5%; acima disso, banner "beta". | P0 | 5h ext./locale | ⏳ |
