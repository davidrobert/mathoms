"""``SourceRef`` (ADR-278 §37): discriminated union ``document|feed``, frozen, com
validação de chave natural no construtor; narrowing por ``kind``."""

from __future__ import annotations

import pytest

from pipeline.domain.ports.source import DocumentSource, FeedSource


def test_document_source_carries_natural_key() -> None:
    ref = DocumentSource(document_id="doc-1")
    assert ref.kind == "document"
    assert ref.document_id == "doc-1"


def test_feed_source_carries_natural_key() -> None:
    ref = FeedSource(provider="openfinance", account_id="acc-1", sync_id="sync-1")
    assert ref.kind == "feed"
    assert (ref.provider, ref.account_id, ref.sync_id) == ("openfinance", "acc-1", "sync-1")


def test_frozen_is_immutable() -> None:
    ref = DocumentSource(document_id="doc-1")
    with pytest.raises(Exception):
        ref.document_id = "other"  # type: ignore[misc]


def test_document_source_requires_document_id() -> None:
    with pytest.raises(ValueError):
        DocumentSource(document_id="")


def test_feed_source_requires_all_fields() -> None:
    with pytest.raises(ValueError):
        FeedSource(provider="openfinance", account_id="", sync_id="sync-1")
