E3 RECONCILIATION SCRIPT - e3_reconcile.py v2.0
=================================================

PURPOSE:
Deterministic E3 reconciliation stage that replaces the LLM-driven pipeline.
Reads E2 extracts, groups transactions by account, deduplicates (cross-file only),
validates saldo continuity, detects temporal gaps, validates against baseline,
and outputs consolidated E3 reconciled files.

USAGE:
  cd /path/to/financas-familia
  python3 scripts/e3_reconcile.py

INPUT:
  - Directory: processed/E2_extracts/
  - Files: *-2_extract.json (excludes -0_original, baseline, non-transactional types)
  - Baseline: baseline_patrimonial-1.5_consolidated.json (for cross-validation)

OUTPUT:
  - Directory: processed/E3_reconciled/
  - Files: {banco}_{tipo_conta}_{moeda}_{YYYYMM}_{YYYYMM}-3_reconciled.json (contas)
           {banco}_{tipo_conta}_{YYYYMM}_{YYYYMM}-3_reconciled.json (faturas)
  - Log: logs/reconciliation.md (summary, saldo warnings, baseline warnings)
  - Log: logs/qa_log.md (temporal gaps, appended)

FEATURES:
  1. Directory cleanup:
     - Removes/tombstones all existing .json in E3_reconciled/ before writing
     - Eliminates ghost files from prior LLM runs

  2. Input filtering:
     - Skips -0_original backup files
     - Skips non-transaction types (investimentos, CDB, IRPF, etc.)
     - Logs explicitly when faturas lack data_vencimento

  3. Automatic account grouping:
     - Conta types: grouped by (banco, tipo, moeda)
     - Fatura types: grouped by (banco, tipo)
     - Recognized types include extratocontapersonnalite

  4. Fatura periodo synthesis:
     - Derives periodo from data_vencimento (1st of prev month → vencimento)
     - Adjusts inicio to actual min transaction date if earlier
     - Falls back to transaction date range if no vencimento

  5. Transaction deduplication (cross-file only):
     - Signature: (data, valor, descricao_normalized)
     - ONLY deduplicates between different source files
     - Intra-file duplicates preserved (legitimate distinct transactions)
     - When cross-file dup found, keeps file with most occurrences

  6. Saldo continuity validation:
     - Checks saldo_final (prev) ≈ saldo_inicial (next)
     - None saldos converted to 0 with warning
     - Reports gaps in reconciliation.md

  7. Temporal gap detection:
     - Gaps > 2 days between consecutive extracts logged
     - Written to logs/qa_log.md (append mode)

  8. Baseline patrimonial validation:
     - Compares 31/12 saldos against IRPF baseline
     - Discrepancies > R$1 reported in reconciliation.md

  9. Deterministic output:
     - Transactions sorted chronologically
     - YYYYMM filename format (no year ambiguity)
     - Idempotent (running twice = identical output)
     - Complete metadata tracking

SKIP TYPES (intentionally excluded):
  - -0_original backup files
  - investimentosposicao
  - carteirarendafixa
  - cdbdetalhes, cdbresumo
  - faturaaluguel*
  - informerendimentos*
  - irpf*
  - baseline_patrimonial-1.5_consolidated.json
  - dados_imoveis-2_extract.json

LAST RUN STATS (v2.0):
  - Accounts reconciled: 17
  - Total transactions: 1613
  - Duplicates removed: 15 (cross-file only)
  - Files written: 17
  - Execution time: ~2 seconds
