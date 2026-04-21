"""Named fakes for backend tests (CLAUDE.md §Code style › Testes · ADR-101 R15).

Use dedicated fake classes instead of `MagicMock` inline when mocking
I/O collaborators. Fakes here should be small, explicit, and assertable.

Application-layer fakes implementam o Protocol declarado em
``backend/app/application/<agg>/_protocols.py`` — duck typing contra
o repo SQLAlchemy real. Uso típico::

    from backend.tests.fakes import FakeFamilyMemberRepository
    repo = FakeFamilyMemberRepository()
    await use_case(..., repo=repo)
"""

from backend.tests.fakes.category import FakeCategoryRepository
from backend.tests.fakes.family_member import (
    FakeFamilyMemberRepository,
    FakeVault,
)
from backend.tests.fakes.goal import FakeGoalRepository

__all__ = [
    "FakeCategoryRepository",
    "FakeFamilyMemberRepository",
    "FakeGoalRepository",
    "FakeVault",
]
