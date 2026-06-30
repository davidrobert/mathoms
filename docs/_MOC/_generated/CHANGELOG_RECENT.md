> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CHANGELOG_RECENT — entregas recentes

Janela de 14 dias a partir da última entrega registrada (2026-06-29). 9 entries entre 2026-06-15 e 2026-06-29.

## 2026-06-29 (2 entries)

- [[CHG-2026-06-29-A22-L2-RED-LINES]] — Camada de red lines do parecer (F3-O1 / KR7). 4ª validação determinística (lane [[A22.l2]])
- [[CHG-2026-06-29-A22-L5-DIVIDAS-DEDUP]] — Dedup de dívida cross-IRPF + schema formal de `dividas` (F1-O3). dividas_dedup.py (lane [[A22.l5]])

## 2026-06-21 (1 entries)

- [[CHG-2026-06-21-A26-L9-CITACAO-DETERMINISTICA]] — Citação determinística (ADR-296 Decidido): LLM emite (claim, path, rótulo) e o pipeline renderiza o valor da folha; gates do eval reconciliados, value_mismatch→0. (lane [[A26.l9]])

## 2026-06-19 (1 entries)

- [[CHG-2026-06-19-A26-L7-EVIDENCIA-CATALOG-LISTAS]] — Catálogo de citação cobre folhas de LISTA via [idx].subkey (fecha a raiz comportamental do ADR-292). (lane [[A26.l7]])

## 2026-06-18 (1 entries)

- [[CHG-2026-06-18-A26-L6-EVIDENCIA-COVERAGE-KPI]] — KPI de citação: cobertura vs. correção + by_section (instrumenta o gate do flip strict da l2). (lane [[A26.l6]])

## 2026-06-16 (3 entries)

- [[CHG-2026-06-16-A25-L2-DEDUP-E4-FLIP-V2]] — Cutover do flip dedup natural_key v2 em E4 + member_hashes reais (ADR-287 Decidido): resolver+sentinela, flip DEFAULTS→True, rebaseline v2≡v1 zero-delta. (lane [[A25.l2]])
- [[CHG-2026-06-16-A25-L6-KR2-RESTO]] — KR2 6/6 lineage (parte A #609: fluxo_liquido + endividamento.total_dividas) + member_hashes reais no item E4 (parte B #648). (lane [[A25.l6]])
- [[CHG-2026-06-16-A25-L7-EVIDENCIA-STRICT-DECISION]] — Decisão registrada: flip strict do evidencia_path vira carry-over A26 (só 3 gerações c/ telemetria << gate de 20; ~89% taxa, 81% conformidade de path). (lane [[A25.l7]])

## 2026-06-15 (1 entries)

- [[CHG-2026-06-15-A25-L5-F6-PRODUTO-N1N2]] — Produto N1/N2: selo de proveniência <MonetaryValue/> + popover sobre o lineage reverso (flag off; teste dogfood pendente). (lane [[A25.l5]])

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
