"""Pipeline domain layer — value objects e domain services (ADR-089).

Camada isolada de I/O: ``pipeline.domain.models`` expõe value objects
(``Money``, ``Transaction``, ``BankStatement``, ...) e ``pipeline.domain.services``
expõe services de negócio puros (``ReconciliationService``,
``CategorizationService``, ``FinancialAnalyzer``).

Testável sem disco/banco: usar ``InMemoryArtifactStore`` como fixture.
"""
