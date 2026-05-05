"""Schemas report collaboration — REMOVED (Direção E · Onda 1 · M3).

ADR-154 M3 (2026-05-05): `ReportNotes*` and `KanbanItem*` schemas removed
together with the SQLAlchemy models. The 410-Gone endpoints in
`reports_collab.py` use `response_class=Response` and require no DTO.
"""

__all__: list[str] = []
