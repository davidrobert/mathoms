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

from backend.tests.fakes.config_blob import (
    FakeConfigBlobRepository,
    FakeGlobalDefaultsLoader,
)
from backend.tests.fakes.document import (
    FakeClassificationService,
    FakeDocumentRepository,
)
from backend.tests.fakes.family_member import (
    FakeFamilyMemberRepository,
    FakeVault,
)
from backend.tests.fakes.goal import FakeGoalRepository
from backend.tests.fakes.health_dependencies import (
    DeadCeleryApp,
    FakeCeleryApp,
    FakeEngine,
    patch_healthy_dependencies,
)
from backend.tests.fakes.task import (
    FakeTaskAttachmentRepository,
    FakeTaskRepository,
    FakeTaskSuggestionRepository,
)

__all__ = [
    "DeadCeleryApp",
    "FakeCeleryApp",
    "FakeClassificationService",
    "FakeConfigBlobRepository",
    "FakeDocumentRepository",
    "FakeEngine",
    "FakeFamilyMemberRepository",
    "FakeGlobalDefaultsLoader",
    "FakeGoalRepository",
    "FakeTaskAttachmentRepository",
    "FakeTaskRepository",
    "FakeTaskSuggestionRepository",
    "FakeVault",
    "patch_healthy_dependencies",
]
