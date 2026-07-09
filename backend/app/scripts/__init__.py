"""Scripts operacionais da aplicação (CLI, manutenção de DB/storage).

Documentos em disco: ``Document.stored_path`` é **relativo à raiz do tenant**
(``storage/<workspace_id>/``), salvo legado com caminho absoluto. Scripts que
leem ficheiros devem usar :meth:`backend.app.services.storage.StorageService.abs_stored_file`.

- ``backfill_content_hash`` — preenche ``content_hash`` em linhas antigas
- ``reclassify_documents`` — reexecuta o classificador content-first
- ``reset_documents`` — apaga linhas ``documents`` e limpa dirs de tenant (destructivo)
- ``cutover_execute`` — cutover ADR-077 (paridade
  ``validate_adapter_parity`` removida em Sprint A10.8 / ADR-181 após
  ``goals.json`` arquivado ser deletado)
- ``seed_*`` — dados de exemplo Andrade Silva
"""
