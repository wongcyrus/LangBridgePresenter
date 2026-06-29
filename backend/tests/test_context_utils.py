import os
import sys

import pytest

pytestmark = pytest.mark.unit

FUNC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../functions"))
if FUNC_PATH not in sys.path:
    sys.path.append(FUNC_PATH)

from _shared.context_utils import (  # noqa: E402
    canonical_language_code,
    extract_presenter_ids,
    has_presentation_context,
    normalize_ppt_id,
    resolve_language_list,
    resolve_language_payload,
    resolve_message_text,
)


@pytest.mark.parametrize(
    ("language_code", "default", "expected"),
    [
        ("en", "en-US", "en-US"),
        ("zh", "en-US", "zh-CN"),
        ("yue", "en-US", "yue-HK"),
        ("fr", "en-US", "fr"),
        (None, "en-US", "en-US"),
    ],
)
def test_canonical_language_code(language_code, default, expected):
    assert canonical_language_code(language_code, default=default) == expected


@pytest.mark.parametrize(
    ("user_params", "expected"),
    [
        ({"presenterId": "alpha,beta"}, ["alpha", "beta"]),
        ("summer-presentation", ["summer"]),
        (" alpha , beta ", ["alpha", "beta"]),
        (None, []),
        ({}, []),
    ],
)
def test_extract_presenter_ids(user_params, expected):
    assert extract_presenter_ids(user_params) == expected


@pytest.mark.parametrize(
    ("user_params", "expected"),
    [
        ("summer-presentation", True),
        ({"mode": "presentation"}, True),
        ({"context": "presentation"}, True),
        ({"presentation": True}, True),
        ("summer", False),
        ({"mode": "discussion"}, False),
        (None, False),
    ],
)
def test_has_presentation_context(user_params, expected):
    assert has_presentation_context(user_params) is expected


def test_resolve_message_variants():
    messages = {
        "en": {"text": "Hello"},
        "zh": "你好",
        "list": ["a", "b"],
    }

    assert resolve_message_text(messages, ["zh"], "fallback") == "你好"
    assert resolve_message_text(messages, ["en"], "fallback") == "Hello"
    assert resolve_language_list(messages, ["list"], []) == ["a", "b"]
    assert resolve_language_payload(messages, ["missing"], "fallback") == "fallback"
    assert resolve_language_list(messages, ["missing"], []) == []
    assert resolve_language_list({"str": "hello"}, ["str"], []) == ["hello"]
    assert resolve_message_text({"bad": {"text": ""}}, ["bad"], "fallback") == "fallback"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("Deck_with_visuals.pptx", "deck"),
        ("Deck_with_notes.PPTX", "deck"),
        ("My Deck_en.pptx", "my_deck"),
        ("Folder\\Sub Folder\\Deck.yue-HK.pptx", "folder_sub_folder_deck"),
        (None, None),
    ],
)
def test_normalize_ppt_id(filename, expected):
    assert normalize_ppt_id(filename) == expected


def test_normalize_ppt_id_none_returns_none():
    assert normalize_ppt_id(None) is None
