import os
import sys

import pytest

pytestmark = pytest.mark.unit

FUNC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../functions"))
if FUNC_PATH not in sys.path:
    sys.path.append(FUNC_PATH)

from config.broadcast_utils import (  # noqa: E402
    build_broadcast_course_ids,
    build_live_update,
    build_presenter_update,
    build_safe_ppt_id,
    enrich_slide_languages,
    resolve_slide_content,
    should_fetch_slide_content,
    should_update_slide_registry,
)


def test_resolve_and_fetch_slide_content():
    assert resolve_slide_content({"latest_languages": {"en": {"text": "Hi"}}}) == {
        "en": {"text": "Hi"}
    }
    assert resolve_slide_content({"presentation_messages": {"en": "Hi"}}) == {
        "en": "Hi"
    }
    assert should_fetch_slide_content({})
    assert should_fetch_slide_content(None)
    assert not should_fetch_slide_content({"en": {"text": "Hi"}})
    assert not should_fetch_slide_content({"en": {}})


def test_build_safe_ppt_id_and_broadcast_course_ids():
    assert build_safe_ppt_id("Folder/Sub Folder/Deck.yue-HK.pptx") == "folder_sub_folder_deck"
    assert build_safe_ppt_id(None) is None
    assert build_broadcast_course_ids(
        "course-a", {"available_styles": ["professional", "casual"]}
    ) == ["course-a", "course-a-casual"]
    assert build_broadcast_course_ids("course-a", None) == ["course-a"]
    assert build_broadcast_course_ids("course-a", {"available_styles": []}) == ["course-a"]

    from config import broadcast_utils as module

    original = module.normalize_ppt_id
    module.normalize_ppt_id = lambda _filename: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        assert build_safe_ppt_id("Deck.pptx") == "Deck.pptx"
    finally:
        module.normalize_ppt_id = original


def test_enrich_and_update_slide_registry():
    slide_content = {
        "en": {"text": "Hello"},
        "zh": "你好",
    }
    existing = {
        "languages": {
            "en": {"text": "Hello", "audio_url": "https://example.com/en.mp3"}
        },
        "source_context": "old-context",
    }

    enriched = enrich_slide_languages(slide_content, existing["languages"])

    assert enriched["en"]["audio_url"] == "https://example.com/en.mp3"
    assert enriched["zh"]["text"] == "你好"
    assert should_update_slide_registry(existing, "new-context", enriched)
    assert should_update_slide_registry(
        {"languages": existing["languages"], "source_context": "old-context"},
        "old-context",
        enriched,
    )
    assert not should_update_slide_registry(
        {"languages": enriched, "source_context": "old-context"},
        "old-context",
        enriched,
    )
    assert not should_update_slide_registry(
        {"languages": enriched, "source_context": "old-context"},
        "old-context",
        enriched,
    )


def test_live_and_presenter_updates_are_derived_from_same_state():
    enriched = {"en": {"text": "Hello", "audio_url": "x"}}
    live = build_live_update("deck", 3, enriched)
    presenter = build_presenter_update("course-a", "deck", 3, enriched)

    assert live["current_slide_id"] == "3"
    assert live["latest_languages"] == enriched
    assert presenter["current_course_id"] == "course-a"
    assert presenter["current_slide_languages"] == enriched
