import importlib
import os
import sys
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def config_module():
    mock_ff = MagicMock()
    mock_ff.http = lambda func: func
    sys.modules["functions_framework"] = mock_ff

    mock_google = MagicMock()
    sys.modules["google"] = mock_google
    sys.modules["google.cloud"] = mock_google
    sys.modules["google.cloud.firestore"] = MagicMock()

    func_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/config")
    )
    if func_path not in sys.path:
        sys.path.append(func_path)

    module = importlib.import_module("main")
    return importlib.reload(module)


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.method = "POST"
    return request


def _make_backend_db():
    db = MagicMock()
    doc_ref = MagicMock()
    db.collection.return_value.document.return_value = doc_ref
    return db, doc_ref


def _make_client_db_with_slide(exists):
    client_db = MagicMock()
    slide_doc = MagicMock()
    slide_doc.exists = exists

    (
        client_db.collection.return_value.document.return_value
        .collection.return_value.document.return_value
        .collection.return_value.document.return_value.get
    ).return_value = slide_doc
    return client_db


def test_populate_messages_from_latest_languages(config_module, mock_request):
    latest_languages = {
        "en": {"text": "Hello English"},
        "zh": {"text": "Hello Chinese"},
    }
    mock_request.get_json.return_value = {
        "presentation_messages": {},
        "latest_languages": latest_languages,
        "context": "Fallback Context",
    }

    db, doc_ref = _make_backend_db()
    config_module._get_db = lambda: db
    config_module._get_client_db = lambda: _make_client_db_with_slide(exists=False)
    config_module.get_course_config = lambda _course_id: None

    response = config_module.config(mock_request)

    assert response[1] == 200
    config_data = doc_ref.set.call_args[0][0]
    assert config_data["presentation_messages"] == latest_languages


def test_empty_slide_content_stays_none_when_registry_missing(config_module, mock_request):
    mock_request.get_json.return_value = {
        "presentation_messages": {},
        "latest_languages": {},
        "context": "Fallback Context",
        "courseId": "test_course",
        "ppt_filename": "test.pptx",
        "page_number": 1,
    }

    db, doc_ref = _make_backend_db()
    config_module._get_db = lambda: db
    config_module._get_client_db = lambda: _make_client_db_with_slide(exists=False)
    config_module.get_course_config = lambda _course_id: None

    config_module.config(mock_request)

    config_data = doc_ref.set.call_args[0][0]
    assert config_data["presentation_messages"] is None


def test_latest_languages_take_precedence_over_legacy_messages(config_module, mock_request):
    latest_languages = {"en": {"text": "Hello English"}}
    mock_request.get_json.return_value = {
        "presentation_messages": {"fr": "Bonjour"},
        "latest_languages": latest_languages,
        "context": "Fallback Context",
    }

    db, doc_ref = _make_backend_db()
    config_module._get_db = lambda: db
    config_module._get_client_db = lambda: _make_client_db_with_slide(exists=False)
    config_module.get_course_config = lambda _course_id: None

    config_module.config(mock_request)

    config_data = doc_ref.set.call_args[0][0]
    assert config_data["presentation_messages"] == latest_languages


def test_config_rejects_non_post_requests(config_module, mock_request):
    mock_request.method = "GET"
    mock_request.get_json.return_value = None

    response = config_module.config(mock_request)

    assert response[1] == 405


def test_config_rejects_missing_json_body(config_module, mock_request):
    mock_request.get_json.return_value = None

    response = config_module.config(mock_request)

    assert response[1] == 400


def test_config_broadcasts_live_slide_and_presenter_context(config_module, mock_request):
    mock_request.get_json.return_value = {
        "courseId": "course-a",
        "ppt_filename": "Deck.yue-HK.pptx",
        "page_number": 3,
        "context": "new-context",
        "latest_languages": {"en": {"text": "Hello"}},
        "userParams": {"presenterId": "p1,p2"},
    }

    backend_db = MagicMock()
    backend_config_collection = MagicMock()
    backend_presenters_collection = MagicMock()
    backend_db.collection.side_effect = lambda name: (
        backend_config_collection
        if name == "langbridge_config"
        else backend_presenters_collection
    )
    backend_doc_ref = MagicMock()
    backend_config_collection.document.return_value = backend_doc_ref
    presenter_docs = {}

    def _backend_presenter_document(presenter_id):
        presenter_doc = presenter_docs.setdefault(presenter_id, MagicMock())
        return presenter_doc

    backend_presenters_collection.document.side_effect = _backend_presenter_document
    config_module._get_db = lambda: backend_db

    client_db = MagicMock()
    presentation_broadcast = MagicMock()
    client_db.collection.return_value = presentation_broadcast

    course_docs = {}

    def _build_course_doc(course_id):
        if course_id in course_docs:
            return course_docs[course_id]

        course_doc = MagicMock()
        presentations = MagicMock()
        course_doc.collection.return_value = presentations
        ppt_doc = MagicMock()
        presentations.document.return_value = ppt_doc
        slides = MagicMock()
        ppt_doc.collection.return_value = slides
        slide_ref = MagicMock()
        slides.document.return_value = slide_ref
        existing_slide = MagicMock()
        existing_slide.exists = True
        existing_slide.to_dict.return_value = {
            "languages": {
                "en": {
                    "text": "Seeded",
                    "audio_url": "https://example.com/seeded.mp3",
                }
            },
            "source_context": "old-context",
        }
        slide_ref.get.return_value = existing_slide
        course_doc._ppt_doc = ppt_doc
        course_doc._slide_ref = slide_ref
        course_docs[course_id] = course_doc
        return course_doc

    presentation_broadcast.document.side_effect = _build_course_doc
    config_module._get_client_db = lambda: client_db
    config_module.get_course_config = lambda _course_id: {
        "available_styles": ["professional", "casual"]
    }

    response = config_module.config(mock_request)

    assert response[1] == 200
    assert backend_doc_ref.set.called
    assert course_docs["course-a"].set.call_count == 1
    assert course_docs["course-a-casual"].set.call_count == 1
    assert course_docs["course-a"]._slide_ref.set.call_count == 1
    assert course_docs["course-a"]._slide_ref.set.call_args[0][0]["source_context"] == "new-context"
    assert course_docs["course-a"].set.call_args[0][0]["latest_languages"]["en"]["audio_url"] == "https://example.com/seeded.mp3"
    assert presenter_docs["p1"].set.call_count == 1
    assert presenter_docs["p2"].set.call_count == 1
