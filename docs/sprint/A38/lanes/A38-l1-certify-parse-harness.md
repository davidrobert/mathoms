---
id: A38.l1
type: lane
title: "Harness local de certificação de parse (classify→route→parse, métricas mascaradas)"
sprint: A38
status: open
priority: P0
branch_slug: a38-l1-certify-parse-harness
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a38
  - status/open
  - priority/p0
  - area/pipeline
  - area/dev-tooling
---

# A38.l1 — `certify-parse-harness` (transversal)

## Problema

A certificação de 2026-07-22 que originou este sprint foi feita com scripts
descartáveis. Sem ferramenta repetível, (a) o aceite das demais lanes vira
medição ad-hoc não comparável, e (b) toda mudança futura de parser volta a
depender de sorte para detectar regressão sobre documentos reais — que não
podem entrar em fixtures (política de PII).

## Escopo

- `dev/certify_parse_local.py`: CLI que recebe `--dir <pasta local de PDFs>`
  e, para cada arquivo, roda o caminho real de produção:
  `classify_file` (regex, sem LLM) → `build_final_name` → `route_to_parser` →
  `process_file` (parse + validação E2).
- Saída **exclusivamente mascarada** (contagens, datas, booleans, códigos):
  doc_type/banco/confidence, nome canônico, parser roteado, `n_tx`, range de
  datas, moeda, saldos presentes (bool), conservação
  `saldo_inicial + Σtx == saldo_final` (bool, cents), flags de escalação,
  notas/erros de validação com valores monetários substituídos.
- `--baseline <json>` grava snapshot e `--compare <json>` falha (exit≠0) se
  qualquer doc regredir (`n_tx` menor, conservação passa→falha, moeda/banco
  correto→errado) — é o gate manual de KR-E sobre o corpus local.
- Baseline e relatórios vão para path indicado pelo operador (default
  `_scratch/`, gitignored). O corpus real do owner fica **fora do git**; o
  harness não conhece paths hardcoded.

## Critério de aceite

- Rodado sobre o corpus local do owner, reproduz a tabela de baseline do
  [[A38]] (§Baseline medida) — mesmos `n_tx`/classificações da certificação.
- Teste unitário da máscara: saída não contém padrão monetário
  (`\d{1,3}(\.\d{3})*,\d{2}`), CPF ou sequências numéricas longas, dado um
  resultado sintético com esses campos.
- `--compare` retorna exit≠0 num baseline mutado (doc com `n_tx` menor).
- Docstring de uso no próprio script (`--help` suficiente; sem doc canônica).

## Risco

Baixo. Ferramenta read-only de dev; não toca produção. Cuidado único: nunca
logar conteúdo bruto de documento (a máscara é testada, não prometida).
