"""Shared parsing and normalization helpers for function handlers."""

from __future__ import annotations

import os

LANGUAGE_CODE_MAP = {
    "en": "en-US",
    "zh": "zh-CN",
    "yue": "yue-HK",
    "en-US": "en-US",
    "zh-CN": "zh-CN",
    "yue-HK": "yue-HK",
}


def canonical_language_code(language_code: str | None, default: str = "en-US") -> str:
    if not language_code:
        return default
    return LANGUAGE_CODE_MAP.get(language_code, language_code)


def extract_presenter_ids(user_params) -> list[str]:
    if isinstance(user_params, dict):
        raw_presenter_ids = user_params.get("presenterId")
    elif isinstance(user_params, str):
        normalized = user_params.strip()
        if normalized.lower().endswith("-presentation"):
            normalized = normalized[: -len("-presentation")]
        raw_presenter_ids = normalized
    else:
        raw_presenter_ids = None

    if not raw_presenter_ids:
        return []
    return [pid.strip() for pid in str(raw_presenter_ids).split(",") if pid.strip()]


def has_presentation_context(user_params) -> bool:
    if isinstance(user_params, str):
        return "presentation" in user_params.lower()
    if isinstance(user_params, dict):
        return bool(
            user_params.get("presentation")
            or user_params.get("isPresentation")
            or user_params.get("mode") == "presentation"
            or user_params.get("context") == "presentation"
        )
    return False


def resolve_language_payload(messages_by_language, preferred_codes, default_value):
    for code in preferred_codes:
        payload = messages_by_language.get(code)
        if payload is not None:
            return payload
    return default_value


def resolve_language_list(messages_by_language, preferred_codes, default_value):
    payload = resolve_language_payload(messages_by_language, preferred_codes, default_value)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, str):
        return [payload]
    return default_value


def resolve_message_text(messages_by_language, preferred_codes, default_text: str) -> str:
    payload = resolve_language_payload(messages_by_language, preferred_codes, default_text)
    if isinstance(payload, dict):
        text = payload.get("text")
        if text:
            return text
    if isinstance(payload, str):
        return payload
    return default_text


def normalize_ppt_id(ppt_filename: str | None) -> str | None:
    if not ppt_filename:
        return ppt_filename

    ppt_norm = os.path.splitext(ppt_filename.lower().replace("\\", "/"))[0]
    for suffix in (
        "_with_visuals",
        "_with_notes",
        "_visuals",
        "_en",
        "_zh-cn",
        "_yue-hk",
        ".zh-cn",
        ".yue-hk",
    ):
        if ppt_norm.endswith(suffix):
            ppt_norm = ppt_norm[: -len(suffix)]
    return ppt_norm.replace("/", "_").replace("\\", "_").replace(" ", "_")
