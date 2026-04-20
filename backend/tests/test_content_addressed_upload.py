"""Phase 0 (ADR-084) — content-addressed uploads.

Acceptance criteria (plano_migracao_artifacts_db.md §Fase 0):

- Upload do mesmo arquivo duas vezes → mesmo ``stored_path``.
- Upload de arquivos diferentes com mesmo nome original → paths distintos.
- Nenhum teste existente quebra (coberto pela suíte geral).

These tests drive ``route_inbox_to_canonical_data`` directly so the filename
convention is verified without exercising FastAPI/DB plumbing.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from backend.app.services.canonical_routing import route_inbox_to_canonical_data


# Minimal config layout that ``e0_route._init_config`` accepts. The
# classifier cache only needs ``institutions.json`` / ``pipeline.json`` /
# ``family_members.json`` to exist — contents are not exercised here.
def _bootstrap_project_config(project_root: Path) -> None:
    cfg = project_root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "institutions.json").write_text("{}")
    (cfg / "pipeline.json").write_text("{}")
    (cfg / "family_members.json").write_text("{}")


def _seed_inbox_file(tenant_root: Path, name: str, content: bytes) -> Path:
    inbox = tenant_root / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    dest = inbox / name
    dest.write_bytes(content)
    return dest


@pytest.fixture()
def tenant_and_project(tmp_path: Path) -> tuple[Path, Path]:
    tenant_root = tmp_path / "tenant"
    project_root = tmp_path / "project"
    tenant_root.mkdir()
    project_root.mkdir()
    _bootstrap_project_config(project_root)
    return tenant_root, project_root


def test_same_content_yields_same_stored_path(tenant_and_project):
    """Acceptance: uploading the same file bytes twice (post-dedup failure
    simulation) lands on the same canonical path — deterministic in the hash.
    """
    tenant_root, project_root = tenant_and_project
    content = b"dummy csv content\n"
    content_hash = hashlib.sha256(content).hexdigest()

    inbox1 = _seed_inbox_file(tenant_root, "extrato_itau_202601.csv", content)
    routed1 = route_inbox_to_canonical_data(
        inbox1,
        tenant_root,
        project_root,
        dest_group="extratos",
        e0_doc_type="extratocontabrl",
        institution="itau",
        period="202601",
        classification_meta=None,
        content_hash=content_hash,
    )
    assert routed1 is not None
    _, rel1 = routed1

    # Simulate a second upload of identical content (e.g. via a different
    # workspace path / different original filename — hash is what drives).
    inbox2 = _seed_inbox_file(tenant_root, "extrato_itau_202601.csv", content)
    routed2 = route_inbox_to_canonical_data(
        inbox2,
        tenant_root,
        project_root,
        dest_group="extratos",
        e0_doc_type="extratocontabrl",
        institution="itau",
        period="202601",
        classification_meta=None,
        content_hash=content_hash,
    )
    assert routed2 is not None
    _, rel2 = routed2

    assert rel1 == rel2, "Same content must yield the same stored_path"
    assert content_hash[:12] in rel1, "Path must contain sha256[:12] prefix"


def test_different_content_same_original_name_yields_distinct_paths(tenant_and_project):
    """Acceptance: two uploads with the same original_name but different bytes
    never silently overwrite — hash prefix separates them.
    """
    tenant_root, project_root = tenant_and_project

    content_a = b"file A contents\n"
    content_b = b"file B contents (distinct)\n"
    hash_a = hashlib.sha256(content_a).hexdigest()
    hash_b = hashlib.sha256(content_b).hexdigest()
    assert hash_a != hash_b

    inbox_a = _seed_inbox_file(tenant_root, "extrato_itau_202601.csv", content_a)
    rel_a = route_inbox_to_canonical_data(
        inbox_a,
        tenant_root,
        project_root,
        dest_group="extratos",
        e0_doc_type="extratocontabrl",
        institution="itau",
        period="202601",
        classification_meta=None,
        content_hash=hash_a,
    )[1]

    inbox_b = _seed_inbox_file(tenant_root, "extrato_itau_202601.csv", content_b)
    rel_b = route_inbox_to_canonical_data(
        inbox_b,
        tenant_root,
        project_root,
        dest_group="extratos",
        e0_doc_type="extratocontabrl",
        institution="itau",
        period="202601",
        classification_meta=None,
        content_hash=hash_b,
    )[1]

    assert rel_a != rel_b, "Distinct content must yield distinct paths"
    assert hash_a[:12] in rel_a
    assert hash_b[:12] in rel_b


def test_content_hash_is_computed_from_disk_when_not_provided(tenant_and_project):
    """When the caller omits ``content_hash`` the function falls back to
    ``file_hash(inbox_path)`` so CLI flows and legacy code still get the
    content-addressed prefix.
    """
    tenant_root, project_root = tenant_and_project
    content = b"fallback hash computation\n"
    expected_prefix = hashlib.sha256(content).hexdigest()[:12]

    inbox = _seed_inbox_file(tenant_root, "extrato_itau_202603.csv", content)
    routed = route_inbox_to_canonical_data(
        inbox,
        tenant_root,
        project_root,
        dest_group="extratos",
        e0_doc_type="extratocontabrl",
        institution="itau",
        period="202603",
        classification_meta=None,
        # content_hash omitted on purpose
    )
    assert routed is not None
    _, rel = routed
    assert expected_prefix in rel
