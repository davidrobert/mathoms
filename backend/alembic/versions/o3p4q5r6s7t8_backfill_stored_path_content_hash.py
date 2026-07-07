"""documents: content-addressed stored_path convention (ADR-084)

Phase 0 of the migration plan (plano_migracao_artifacts_db.md) introduces a
content-hash prefix on canonical filenames stored in ``data/`` so that distinct
uploads with the same canonical name land on distinct paths:

    itau_extratoconta_202603-0_original.pdf
    → a3f9c1b4d2e8_itau_extratoconta_202603-0_original.pdf

The prefix is the first 12 hex chars of the sha256 of the uploaded bytes, which
matches ``documents.content_hash`` (already populated by the dedup column,
migration ``f1a2b3c4d5e6``).

This migration is **documentation-only**: it does NOT rename files on disk nor
rewrite ``documents.stored_path`` for existing rows. Legacy documents keep
their non-prefixed paths; only documents ingested after this revision's code is
deployed acquire the prefix. Reclassification naturally upgrades touched files.

Revision ID: o3p4q5r6s7t8
Revises: n2o3p4q5r6s7
Create Date: 2026-04-18
"""

from typing import Sequence, Union

revision: str = "o3p4q5r6s7t8"
down_revision: Union[str, None] = "n2o3p4q5r6s7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: documents the content-addressed filename convention (ADR-084).

    Existing ``stored_path`` values are retained as-is. The application code
    (``scripts.route_documents.build_final_name`` and
    ``backend.app.services.canonical_routing``) starts emitting hash-prefixed
    filenames on new uploads and on reclassify operations.
    """
    pass


def downgrade() -> None:
    """No-op: no schema or data changes to revert."""
    pass
