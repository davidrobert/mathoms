> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CHANGELOG_RECENT — entregas recentes

Janela de 14 dias a partir da última entrega registrada (2026-07-02). 11 entries entre 2026-06-18 e 2026-07-02.

## 2026-07-02 (1 entries)

- [[CHG-2026-07-02-A27-L1-EVIDENCIA-LINEAGE-EDGE]] — Citação do parecer materializada como edge de lineage por chave natural (ADR-293 Decidido): resolver de chave + DELETE-por-produtor (slices 1+3), hook pós-run + queries de reverse-lineage doc→parecer (slices 2+4). KR3/G6 provado por teste de reordenação de top_ativos. Zero migration. (lane [[A27.l1]])

## 2026-07-01 (3 entries)

- [[CHG-2026-07-01-A22-L2-RED-LINES-CALIBRATION]] — Calibração das red lines do parecer via 2 rodadas de dogfood do eval LLM (lane [[A22.l2]])
- [[CHG-2026-07-01-A26-L3-DROP-DEDUP-V1-SHIM]] — M2-A: drop do shim v1 compute_transaction_hash do dedup — gate cumprido (natural_key v2 a 100% + counter v1_fallback zerado ≥1 sprint). Primeiro drop "canário" (reversível) antes da M2-B destrutiva. (lane [[A26.l3]])
- [[CHG-2026-07-01-A26-L4-INSTRUMENTACAO-DUALREAD]] — Instrumentação do gate M2 do override (parcial — lane in_progress): v2_match_count + shadow-compare divergence_count + snapshot em AuditLog, wired nos consumidores E4. Resta o flip do default (backfill→workspace→DEFAULTS) + observação ≥1 sprint. (lane [[A26.l4]])

## 2026-06-29 (2 entries)

- [[CHG-2026-06-29-A22-L2-RED-LINES]] — Camada de red lines do parecer (F3-O1 / KR7). 4ª validação determinística (lane [[A22.l2]])
- [[CHG-2026-06-29-A22-L5-DIVIDAS-DEDUP]] — Dedup de dívida cross-IRPF + schema formal de `dividas` (F1-O3). dividas_dedup.py (lane [[A22.l5]])

## 2026-06-21 (1 entries)

- [[CHG-2026-06-21-A26-L9-CITACAO-DETERMINISTICA]] — Citação determinística (ADR-296 Decidido): LLM emite (claim, path, rótulo) e o pipeline renderiza o valor da folha; gates do eval reconciliados, value_mismatch→0. (lane [[A26.l9]])

## 2026-06-19 (1 entries)

- [[CHG-2026-06-19-A26-L7-EVIDENCIA-CATALOG-LISTAS]] — Catálogo de citação cobre folhas de LISTA via [idx].subkey (fecha a raiz comportamental do ADR-292). (lane [[A26.l7]])

## 2026-06-18 (3 entries)

- [[CHG-2026-06-18-A26-L1-EVIDENCIA-CATALOGO]] — Catálogo de citação do evidencia_path + eval golden (ponto de entrada da A26). (lane [[A26.l1]])
- [[CHG-2026-06-18-A26-L6-EVIDENCIA-COVERAGE-KPI]] — KPI de citação: cobertura vs. correção + by_section (instrumenta o gate do flip strict da l2). (lane [[A26.l6]])
- [[CHG-2026-06-18-A26-L8-EVIDENCIA-VALUE-MISMATCH]] — Enforcement per-item do pareamento número↔path (prompt 1.9.0): item com citação incorreta é dropado ou vira needs_review — nunca número errado publicado. Cumpre a pré-condição de código do flip strict (A26.l2). (lane [[A26.l8]])

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
