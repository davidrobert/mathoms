"""Application layer — 1 endpoint = 1 use case (ADR-101 R15).

Use cases orquestram regras de negócio chamando repositórios e serviços de
domínio. Não conhecem FastAPI nem HTTP — erros voltam como exceções de
domínio tipadas (:mod:`backend.app.application.base.errors`), convertidas
para HTTP nos routers.

Pacotes por agregado:

- :mod:`backend.app.application.family_member`
- :mod:`backend.app.application.category`
- :mod:`backend.app.application.goal`

Base compartilhada (errors tipados) em
:mod:`backend.app.application.base`.
"""
