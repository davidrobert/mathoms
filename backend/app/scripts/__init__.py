"""Scripts operacionais da aplicação (CLI, manutenção de DB/storage).

Documentos em disco: ``Document.stored_path`` é **relativo à raiz do tenant**
(``storage/<workspace_id>/``), salvo legado com caminho absoluto. Scripts que
leem ficheiros devem usar :meth:`backend.app.services.storage.StorageService.abs_stored_file`.

- ``backfill_content_hash`` — preenche ``content_hash`` em linhas antigas
- ``reclassify_documents`` — reexecuta o classificador content-first
- ``reset_documents`` — apaga linhas ``documents`` e limpa dirs de tenant (destructivo)
- ``cutover_execute`` / ``validate_adapter_parity`` — cutover ADR-077
- ``seed_*`` — dados de exemplo Ferreira Campos
"""
