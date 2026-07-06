> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CHANGELOG_RECENT — entregas recentes

Janela de 14 dias a partir da última entrega registrada (2026-07-06). 7 entries entre 2026-06-29 e 2026-07-06.

## 2026-07-06 (1 entries)

- [[CHG-2026-07-06-A29-REVIEW-UX-SPRINT]] — Sprint A29 Review UX completa (3/3 lanes, mesma sessão do dogfood que a originou): tela de conferência v1.5 (agrupamento com contador, consequência explícita, telemetria review_action p/ KR1), cobertura ReviewReason completa em E3 (4 famílias domain.*, gate por BLOCKING_CODES, projeção validation_issues fecha ADR-272 crit. 6, document_id por hash) e inbox de pendências em /documents com retomada explícita. ADR-308 Proposto→Decidido.

## 2026-07-02 (1 entries)

- [[CHG-2026-07-02-A27-L1-EVIDENCIA-LINEAGE-EDGE]] — Citação do parecer materializada como edge de lineage por chave natural (ADR-293 Decidido): resolver de chave + DELETE-por-produtor (slices 1+3), hook pós-run + queries de reverse-lineage doc→parecer (slices 2+4). KR3/G6 provado por teste de reordenação de top_ativos. Zero migration. (lane [[A27.l1]])

## 2026-07-01 (3 entries)

- [[CHG-2026-07-01-A22-L2-RED-LINES-CALIBRATION]] — Calibração das red lines do parecer via 2 rodadas de dogfood do eval LLM (lane [[A22.l2]])
- [[CHG-2026-07-01-A26-L3-DROP-DEDUP-V1-SHIM]] — M2-A: drop do shim v1 compute_transaction_hash do dedup — gate cumprido (natural_key v2 a 100% + counter v1_fallback zerado ≥1 sprint). Primeiro drop "canário" (reversível) antes da M2-B destrutiva. (lane [[A26.l3]])
- [[CHG-2026-07-01-A26-L4-INSTRUMENTACAO-DUALREAD]] — Instrumentação do gate M2 do override (parcial — lane in_progress): v2_match_count + shadow-compare divergence_count + snapshot em AuditLog, wired nos consumidores E4. Resta o flip do default (backfill→workspace→DEFAULTS) + observação ≥1 sprint. (lane [[A26.l4]])

## 2026-06-29 (2 entries)

- [[CHG-2026-06-29-A22-L2-RED-LINES]] — Camada de red lines do parecer (F3-O1 / KR7). 4ª validação determinística (lane [[A22.l2]])
- [[CHG-2026-06-29-A22-L5-DIVIDAS-DEDUP]] — Dedup de dívida cross-IRPF + schema formal de `dividas` (F1-O3). dividas_dedup.py (lane [[A22.l5]])

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
