E3 RECONCILIATION SCRIPT - e3_reconcile.py
============================================

PURPOSE:
Deterministic E3 reconciliation stage that replaces the LLM-driven pipeline.
Reads E2 extracts, groups transactions by account, deduplicates, validates
saldo continuity, and outputs consolidated E3 reconciled files.

USAGE:
  cd /path/to/financas-familia
  python3 scripts/e3_reconcile.py

INPUT:
  - Directory: processed/E2_extracts/
  - Files: *-2_extract.json (105 files total)
  
OUTPUT:
  - Directory: processed/E3_reconciled/
  - Files: {banco}_{tipo_conta}_{moeda}_{MMDD}-{MMDD}-3_reconciled.json
  - Log: logs/reconciliation.md

FEATURES:
  1. Automatic account grouping:
     - Conta types: grouped by (banco, tipo, moeda)
     - Fatura types: grouped by (banco, tipo)
     
  2. Transaction deduplication:
     - Signature: (data, valor, descricao_normalized)
     - Conflict: keeps most recent file occurrence
     
  3. Saldo continuity validation:
     - Checks saldo_final (prev) ≈ saldo_inicial (next)
     - Reports gaps in reconciliation.md
     
  4. Edge case handling:
     - Skips non-transaction files (investimentos, CDB, IRPF, etc.)
     - Handles files without transacoes or periodo fields
     - Robust JSON parsing with error reporting
     
  5. Deterministic output:
     - Transactions sorted chronologically
     - Idempotent (running twice = identical output)
     - Complete metadata tracking

SKIP TYPES (intentionally excluded):
  - investimentosposicao
  - carteirarendafixa
  - cdbdetalhes, cdbresumo
  - faturaaluguel*
  - informerendimentos*
  - irpf*
  - baseline_patrimonial-1.5_consolidated.json
  - dados_imoveis-2_extract.json

LAST RUN STATS:
  - Accounts reconciled: 14
  - Total transactions: 329
  - Duplicates removed: 51
  - Files written: 14
  - Execution time: ~3 seconds
