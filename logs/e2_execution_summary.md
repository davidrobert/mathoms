# Step 6b (E1.5) - Baseline Patrimonial Execution Summary

**Execution Date:** 2026-04-09  
**Pipeline Step:** E1.5 - Baseline Patrimonial  
**Status:** COMPLETED

## Overview

Successfully extracted and consolidated financial/patrimonial data from IRPF declarations, QuintoAndar rental income reports, IRPF receipts, and real estate spreadsheet for the Ferreira Campos family.

## Files Processed

### Input Files
- ✓ `receitafederal_irpfdeclaracao_2023-0_original.pdf` (480.6 KB) - Mariana's IRPF 2023
- ✓ `receitafederal_irpfdeclaracao_2024-0_original.pdf` (600.9 KB) - David's IRPF 2024
- ✓ `receitafederal_irpfdeclaracaomariana_2024-0_original.pdf` (525.3 KB) - Mariana's IRPF 2024
- ✓ `receitafederal_irpfrecibo_2024-0_original.pdf` (82.7 KB) - David's IRPF receipt 2024
- ✓ `receitafederal_irpfrecibomariana_2024-0_original.pdf` (82.9 KB) - Mariana's IRPF receipt 2024
- ✓ `quintoandar_informerendimentosaluguel_2025-0_original.pdf` (55.3 KB) - QuintoAndar rental income 2025
- ✓ `quintoandar_informerendimentosaluguelmariana_2025-0_original.pdf` (55.7 KB) - QuintoAndar rental income Mariana 2025
- ✓ `dados_imoveis-0_original.xlsx` (17.3 KB) - Real estate spreadsheet

### Output Files Created

#### Individual Extract Files (JSON)
1. **IRPF Declarations**
   - `receitafederal_irpfdeclaracao_2023-0-0_original-2_extract.json` (3.2 KB)
   - `receitafederal_irpfdeclaracao_2024-0-0_original-2_extract.json` (6.9 KB)
   - `receitafederal_irpfdeclaracaomariana_2024-0-0_original-2_extract.json` (4.5 KB)

2. **IRPF Receipts**
   - `receitafederal_irpfrecibo_2024-0-0_original-2_extract.json` (231 B)
   - `receitafederal_irpfrecibomariana_2024-0-0_original-2_extract.json` (238 B)

3. **QuintoAndar Rental Income**
   - `quintoandar_informerendimentosaluguel_2025-0-0_original-2_extract.json` (273 B)
   - `quintoandar_informerendimentosaluguelmariana_2025-0-0_original-2_extract.json` (280 B)

4. **Real Estate**
   - `dados_imoveis-2_extract.json` (1.5 KB)

#### Consolidated Files
- **`baseline_patrimonial-1.5_consolidated.json`** (36 KB)
  - Master consolidation of all IRPF declarations
  - Cross-referenced with real estate data
  - Organized by member and declaration year

#### Logs & Documentation
- **`logs/divergences.md`** (2.9 KB)
  - Divergences between IRPF and spreadsheet data
  - Cross-reference validation results
  - Recommendations for further verification

## Data Extracted Summary

### Members Identified
1. **DAVID ROBERT CAMARGO FERREIRA CAMPOS** (CPF: 287.766.948-36)
   - IRPF Declaration: 2024
   - Real Estate (G01): 4 properties
   - Investments (G03/04/06): 15 assets

2. **MARIANA TEIXEIRA FERREIRA / MARIANA FERREIRA CAMPOS** (CPF: 085.052.396-60)
   - IRPF Declarations: 2023, 2024
   - Real Estate (G01): 4 properties
   - Investments (G03/04/06): 12 assets

### Asset Classes Extracted
- **G01 (Real Estate):** 8 total entries across both members
- **G02 (Vehicles):** 0 entries found
- **G03 (Financial Applications):** 3 entries (David), 0 entries (Mariana)
- **G04 (Investments):** 6 entries (David), 11 entries (Mariana)
- **G06 (Bank Accounts):** 6 entries (David), 1 entry (Mariana)
- **G07 (Cryptocurrencies):** 0 entries found

### Income Sources Identified
- **PJ (Pessoa Jurídica) Income:** 1 source identified (Mariana 2023)
- **Rental Income (PF/Aluguéis):** Identified and cross-referenced with QuintoAndar reports
- **Exempt/Non-Taxable Income:** Multiple sources per declaration
- **Exclusive Taxation Income:** 13º salário and financial returns documented

### Deductible Payments Documented
- Medical/Healthcare deductions
- Education payments
- Professional services (dentistry, medical, etc.)
- Insurance (health, property)

## Divergences Found

**KEY FINDING:** 8 properties declared in IRPF vs 4 in spreadsheet
- 4 properties could not be matched between IRPF and spreadsheet
- Possible causes:
  - Differences in property naming/address formatting
  - Properties sold during period
  - Properties in holding companies (not personal names)

**Status:** REQUIRES MANUAL VALIDATION

## Data Quality Notes

### Strengths
- Complete extraction of 5 IRPF declarations (2023-2024)
- All monetary values converted to numeric format (float)
- IRPF group codes preserved for categorization
- Cross-referencing between sources documented
- Date fields standardized

### Limitations
- QuintoAndar reports: Limited property-level detail in PDF extraction
- Real estate spreadsheet: Some cells contained unstructured text
- Group G07 (crypto): Not found in declarations
- Vehicle data (G02): No vehicles declared

## Technical Details

### Extraction Methods
- **PDFs:** pdfplumber library with regex pattern matching
- **XLSX:** openpyxl with flexible header matching
- **Data Validation:** Numeric conversion with error handling
- **Date Handling:** Standardized to DD/MM/YYYY format

### File Formats
- All output files: JSON with UTF-8 encoding
- Structured data organization by:
  - Member/Declarant
  - Declaration year
  - Asset class (IRPF grupos)
  - Income source type

## Recommendations for Next Steps

1. **Address Matching:** Manually review 4 properties in spreadsheet against IRPF descriptions
2. **Valuation Verification:** Cross-check current values (valor_atual) in IRPF against market data
3. **Loan/Financing Details:** Extract specific terms from real estate spreadsheet for liability calculation
4. **Missing Data:** Investigate absent vehicles (G02) and cryptocurrency holdings
5. **Timeline Analysis:** Create detailed timeline of acquisitions for each property

## Consolidated Data Location

**Base Directory:** `/sessions/nice-affectionate-thompson/mnt/Financas Familia/financas-familia/processed/E2_extracts/`

All extracted JSON files and consolidated data are available in this directory.

---

**Pipeline Status:** Ready for Step E1.6 (Liability Analysis)
