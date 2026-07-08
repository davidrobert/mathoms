---
id: CHG-2026-05-06-FIX-DOCUMENTS
type: changelog-entry
date: "2026-05-06"
sprint: A10
summary: |
  fix(documents): "Sem extrato" enganoso em investment_report misclassificado (2026-05-06). - **fix(documents): "Sem extrato" enganoso em investment_report misclassificado (2026-05-06):** Filename `itau_extratoconta_*.xls` cujo conteúdo é Posição de In
tags:
  - type/changelog-entry
  - sprint/a10
---


# fix(documents): "Sem extrato" enganoso em investment_report misclassificado (2026-05-06)

- **fix(documents): "Sem extrato" enganoso em investment_report misclassificado (2026-05-06):**
  Filename `itau_extratoconta_*.xls` cujo conteúdo é Posição de Investimentos
  (override de classificação OU PATCH manual) ficava com badge "Sem extrato"
  porque (a) `pipeline_e2_extract_ok=False` era setado mesmo para `investment_report`
  sem extract, e (b) `update_document_classification` mudava `doc_type` no DB
  mas mantinha o filename antigo, fazendo E2 rotear para `parse_itau_xls`
  (que falha por sheet `Lançamentos` ausente) em vez do E2-LLM.
  - **A — sync**: `_OPTIONAL_E2_EXTRACT_TYPE_VALUES = {"investment_report"}`
    em [backend/app/services/document_pipeline_sync.py](../../../../backend/app/services/pipeline/document_pipeline_sync.py) —
    sem extract → `pipeline_e2_extract_ok=None` ("Processado"), em vez de
    `False` ("Sem extrato"). Com extract → `True` ("Extraído") como antes.
  - **B — rename canônico no PATCH**: `_maybe_rename_after_manual_override`
    em [backend/app/api/documents.py](../../../../backend/app/api/documents.py) chama
    `rename_to_canonical` quando `doc_type`/`bank_code`/`period` mudam.
    Reverse mapping `document_type_to_e0_dest()` em
    [backend/app/services/document_classification.py](../../../../backend/app/services/document_classification.py).
    Preserva e0_doc_type existente quando ele ainda casa com o novo
    `DocumentType` (ex.: `informerendimentos*` continua válido para IRPF —
    sem churn de path desnecessário).
  - Cobertura: 8 testes unitários novos em
    [backend/tests/test_documents_rename_helper.py](../../../../backend/tests/test_documents_rename_helper.py),
    2 em [backend/tests/test_document_pipeline_sync.py](../../../../backend/tests/test_document_pipeline_sync.py),
    3 em [backend/tests/test_document_classification.py](../../../../backend/tests/test_document_classification.py).
