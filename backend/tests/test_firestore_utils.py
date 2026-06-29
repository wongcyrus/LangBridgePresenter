import os
import sys
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

FUNC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../functions/config"))
if FUNC_PATH not in sys.path:
    sys.path.append(FUNC_PATH)

import firestore_utils  # noqa: E402


def test_normalize_context_and_cache_key():
    assert firestore_utils._normalize_context("  hello   world ") == "hello world"
    assert firestore_utils._cache_key("EN", "hello world") == "v1:en:b94d27b9934d"
    assert firestore_utils._cache_key("EN", "   ") == "v1:en:default"


def test_get_db_and_client_db_use_environment(monkeypatch):
    calls = []

    def fake_client(**kwargs):
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(firestore_utils.firestore, "Client", fake_client)
    monkeypatch.setenv("FIRESTORE_DATABASE", "custom-db")
    assert firestore_utils._get_db() is not None
    monkeypatch.setenv("CLIENT_FIRESTORE_PROJECT_ID", "project-x")
    monkeypatch.setenv("CLIENT_FIRESTORE_DATABASE_ID", "db-x")
    assert firestore_utils._get_client_db() is not None
    assert calls[0] == {"database": "custom-db"}
    assert calls[1] == {"project": "project-x", "database": "db-x"}


def test_get_cached_presentation_message_hit_and_miss(monkeypatch):
    db = MagicMock()
    cache_ref = MagicMock()
    db.collection.return_value.document.return_value = cache_ref
    hit_doc = MagicMock()
    hit_doc.exists = True
    hit_doc.to_dict.return_value = {"message": "Hello", "audio_url": "https://x"}
    miss_doc = MagicMock()
    miss_doc.exists = False
    monkeypatch.setattr(firestore_utils, "_get_db", lambda: db)

    cache_ref.get.return_value = hit_doc
    assert firestore_utils.get_cached_presentation_message("en", "ctx") == (
        "Hello",
        "https://x",
    )

    cache_ref.get.return_value = miss_doc
    assert firestore_utils.get_cached_presentation_message("en", "ctx") == (None, None)


def test_get_cached_presentation_message_missing_message(monkeypatch):
    db = MagicMock()
    cache_ref = MagicMock()
    db.collection.return_value.document.return_value = cache_ref
    doc = MagicMock()
    doc.exists = True
    doc.to_dict.return_value = {"audio_url": "https://x"}
    cache_ref.get.return_value = doc
    monkeypatch.setattr(firestore_utils, "_get_db", lambda: db)

    assert firestore_utils.get_cached_presentation_message("en", "ctx") == (None, None)


def test_get_cached_presentation_message_handles_exception(monkeypatch):
    monkeypatch.setattr(firestore_utils, "_get_db", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert firestore_utils.get_cached_presentation_message("en", "ctx") == (None, None)


def test_cache_presentation_message_writes_merge_payload(monkeypatch):
    db = MagicMock()
    cache_ref = MagicMock()
    db.collection.return_value.document.return_value = cache_ref
    monkeypatch.setattr(firestore_utils, "_get_db", lambda: db)
    monkeypatch.setattr(firestore_utils.firestore, "SERVER_TIMESTAMP", "ts")
    monkeypatch.setattr(firestore_utils.firestore, "ArrayUnion", lambda items: tuple(items))

    firestore_utils.cache_presentation_message(
        "en",
        "Hello",
        context="  some context ",
        course_id="course-a",
        audio_url="https://x",
    )

    cache_ref.set.assert_called_once()
    payload = cache_ref.set.call_args[0][0]
    assert payload["context"] == "some context"
    assert payload["course_ids"] == ("course-a",)
    assert payload["audio_url"] == "https://x"


def test_cache_presentation_message_skips_empty_and_handles_exception(monkeypatch):
    db = MagicMock()
    cache_ref = MagicMock()
    db.collection.return_value.document.return_value = cache_ref
    monkeypatch.setattr(firestore_utils, "_get_db", lambda: db)
    monkeypatch.setattr(firestore_utils.firestore, "SERVER_TIMESTAMP", "ts")
    monkeypatch.setattr(firestore_utils.firestore, "ArrayUnion", lambda items: tuple(items))

    assert firestore_utils.cache_presentation_message("en", "") is None

    cache_ref.set.side_effect = RuntimeError("boom")
    assert firestore_utils.cache_presentation_message("en", "Hello") is None
