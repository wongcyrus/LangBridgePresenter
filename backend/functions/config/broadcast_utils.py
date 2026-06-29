"""Pure helpers for config broadcast behavior."""

from __future__ import annotations

from typing import Any, Mapping

from _shared.context_utils import extract_presenter_ids, normalize_ppt_id


def resolve_slide_content(request_json: Mapping[str, Any]) -> Any:
    return request_json.get("latest_languages") or request_json.get("presentation_messages")


def should_fetch_slide_content(slide_content: Any) -> bool:
    return not slide_content or (isinstance(slide_content, dict) and len(slide_content) == 0)


def build_safe_ppt_id(ppt_filename: str | None) -> str | None:
    try:
        return normalize_ppt_id(ppt_filename)
    except Exception:
        if not ppt_filename:
            return ppt_filename
        return (
            ppt_filename.replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
        )


def build_broadcast_course_ids(course_id: str, course_config: Mapping[str, Any] | None) -> list[str]:
    broadcast_course_ids = [course_id]
    if not course_config:
        return broadcast_course_ids

    available_styles = course_config.get("available_styles", [])
    if not available_styles:
        return broadcast_course_ids

    for style in available_styles:
        if style != "professional":
            broadcast_course_ids.append(f"{course_id}-{style}")
    return broadcast_course_ids


def enrich_slide_languages(
    slide_content: Mapping[str, Any],
    existing_languages: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    registry_languages = existing_languages or {}
    enriched_languages: dict[str, dict[str, Any]] = {}
    for lang, content in slide_content.items():
        enriched_languages[lang] = (
            content.copy() if isinstance(content, dict) else {"text": content}
        )
        if "audio_url" not in enriched_languages[lang]:
            registry_lang = registry_languages.get(lang, {})
            if isinstance(registry_lang, dict) and "audio_url" in registry_lang:
                enriched_languages[lang]["audio_url"] = registry_lang["audio_url"]
    return enriched_languages


def slide_has_new_audio(
    enriched_languages: Mapping[str, Mapping[str, Any]],
    existing_languages: Mapping[str, Any] | None,
) -> bool:
    registry_languages = existing_languages or {}
    return any(
        "audio_url" in enriched_languages.get(lang, {})
        and "audio_url" not in registry_languages.get(lang, {})
        for lang in enriched_languages
    )


def should_update_slide_registry(
    existing_slide_data: Mapping[str, Any] | None,
    context: str | None,
    enriched_languages: Mapping[str, Mapping[str, Any]],
) -> bool:
    if not existing_slide_data:
        return True

    existing_context = existing_slide_data.get("source_context", "")
    if existing_context != context:
        return True

    existing_languages = existing_slide_data.get("languages", {})
    return existing_languages != enriched_languages


def build_live_update(
    safe_ppt_id: str,
    page_number: int | str,
    enriched_languages: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "latest_languages": enriched_languages,
        "current_presentation_id": safe_ppt_id,
        "current_slide_id": str(page_number),
    }


def build_presenter_update(
    course_id: str,
    safe_ppt_id: str,
    page_number: int | str,
    enriched_languages: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "current_course_id": course_id,
        "current_presentation_id": safe_ppt_id,
        "current_slide_id": str(page_number),
        "current_slide_languages": enriched_languages,
    }
