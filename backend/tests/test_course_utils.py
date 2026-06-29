import os
import sys
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

FUNC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../functions/config"))
if FUNC_PATH not in sys.path:
    sys.path.append(FUNC_PATH)

import course_utils  # noqa: E402


def test_get_course_config_handles_missing_course_id():
    assert course_utils.get_course_config("") is None


def test_get_course_config_returns_document(monkeypatch):
    db = MagicMock()
    doc = MagicMock()
    doc.exists = True
    doc.to_dict.return_value = {"languages": ["en-US"]}
    db.collection.return_value.document.return_value.get.return_value = doc
    monkeypatch.setattr(course_utils, "_get_db", lambda: db)

    assert course_utils.get_course_config("course-a") == {"languages": ["en-US"]}


def test_get_course_config_missing_document(monkeypatch):
    db = MagicMock()
    doc = MagicMock()
    doc.exists = False
    db.collection.return_value.document.return_value.get.return_value = doc
    monkeypatch.setattr(course_utils, "_get_db", lambda: db)

    assert course_utils.get_course_config("course-a") is None


def test_get_course_config_handles_exception(monkeypatch):
    monkeypatch.setattr(course_utils, "_get_db", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert course_utils.get_course_config("course-a") is None


def test_get_db_uses_env_and_default(monkeypatch):
    calls = []

    def fake_client(**kwargs):
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(course_utils.firestore, "Client", fake_client)
    monkeypatch.setenv("FIRESTORE_DATABASE", "custom-db")
    assert course_utils._get_db() is not None
    monkeypatch.setenv("FIRESTORE_DATABASE", "   ")
    assert course_utils._get_db() is not None
    assert calls[0] == {"database": "custom-db"}
    assert calls[1] == {"database": "langbridge"}


def test_get_course_languages_and_defaults(monkeypatch):
    monkeypatch.setattr(course_utils, "get_course_config", lambda _course_id: {"languages": ["zh-CN"]})
    assert course_utils.get_course_languages("course-a") == ["zh-CN"]
    monkeypatch.setattr(course_utils, "get_course_config", lambda _course_id: None)
    assert course_utils.get_course_languages("course-a") == course_utils.DEFAULT_LANGUAGES


def test_get_voice_params_uses_course_config(monkeypatch):
    texttospeech = pytest.importorskip("google.cloud.texttospeech")
    monkeypatch.setattr(
        course_utils,
        "get_course_config",
        lambda _course_id: {
            "voice_configs": {
                "zh-CN": {"name": "cmn-CN-Chirp3-HD-Achernar", "gender": "female"}
            }
        },
    )

    voice = course_utils.get_voice_params("course-a", "zh-CN")

    assert voice.language_code == "cmn-CN"
    assert voice.name == "cmn-CN-Chirp3-HD-Achernar"
    assert voice.ssml_gender == texttospeech.SsmlVoiceGender.FEMALE


def test_get_voice_params_falls_back_to_default_and_system(monkeypatch):
    texttospeech = pytest.importorskip("google.cloud.texttospeech")
    monkeypatch.setattr(course_utils, "get_course_config", lambda _course_id: {})

    default_voice = course_utils.get_voice_params("course-a", "en-US")
    assert default_voice.name == course_utils.DEFAULT_VOICES["en-US"]["name"]

    system_voice = course_utils.get_voice_params("course-a", "fr-FR")
    assert system_voice.language_code == "fr-FR"
    assert system_voice.ssml_gender == texttospeech.SsmlVoiceGender.FEMALE


def test_get_voice_params_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "google.cloud.texttospeech", None)
    monkeypatch.delitem(sys.modules, "google.cloud", raising=False)
    monkeypatch.delitem(sys.modules, "google", raising=False)
    monkeypatch.setattr(
        course_utils,
        "get_course_config",
        lambda _course_id: None,
    )

    with pytest.raises(ImportError):
        course_utils.get_voice_params("course-a", "en-US")


def test_log_presentation_event_handles_missing_course_and_success(monkeypatch):
    assert course_utils.log_presentation_event("", {"event": 1}) is None

    db = MagicMock()
    monkeypatch.setattr(course_utils, "_get_db", lambda: db)
    course_utils.log_presentation_event("course-a", {"event": 1})
    db.collection.return_value.document.return_value.collection.return_value.add.assert_called_once()


def test_log_presentation_event_handles_exception(monkeypatch):
    monkeypatch.setattr(course_utils, "_get_db", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    course_utils.log_presentation_event("course-a", {"event": 1})
