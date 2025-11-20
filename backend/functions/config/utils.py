"""Utility functions for message generation."""
import hashlib


def normalize_context(context: str) -> str:
    """Trim and collapse whitespace in context (speaker notes)."""
    if not context:
        return ""
    return " ".join(str(context).split())


def session_id_for(language_code: str, context: str) -> str:
    """Build a stable session id per language and notes content.

    Prevents reusing the same conversation for different slides/notes,
    which could cause the model to repeat the first response.
    """
    norm = normalize_context(context)
    if not norm:
        digest = "default"
    else:
        digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]
    lang = (language_code or "").strip().lower() or "unknown"
    return f"presentation_gen_{lang}_{digest}"
