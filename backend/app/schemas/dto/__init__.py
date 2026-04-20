"""DTO layer (R12 — ISP backend).

Endpoints retornam Pydantic DTOs dedicados, nunca modelos ORM. Cada agregado
tem seu pacote ``<aggregate>/`` contendo:

- ``response.py`` — shapes retornados pela API (imutáveis do ponto de vista
  do cliente; mudanças são breaking).
- ``command.py`` — inputs de write (Create/Update/Replace).
- ``mapper.py`` — conversão ORM→DTO e coerções de campos derivados
  (decrypt, unpack de blobs, placeholders de privacidade).

``query.py`` só aparece quando um agregado tem filtros ricos (pipeline runs
por status, documents por doc_type, etc.). Agregados com queries triviais
(apenas ``workspace_id``) podem omitir.
"""
