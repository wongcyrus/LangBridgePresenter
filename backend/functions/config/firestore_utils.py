import logging
import os
import hashlib
from google.cloud import firestore

logger = logging.getLogger(__name__)


def _get_db():
    """Return a Firestore client using an optional env database name.

    If `FIRESTORE_DATABASE` is set, use that database; otherwise use the
    'xiaoice' database.
    """
    db_name = os.environ.get("FIRESTORE_DATABASE", "xiaoice").strip()
    if db_name:
        return firestore.Client(database=db_name)
    return firestore.Client(database="xiaoice")


def get_config():
    try:
        db = _get_db()
        doc_ref = db.collection('xiaoice_config').document('messages')
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            return get_default_config()
    except Exception:
        return get_default_config()


def get_default_config():
    return {
        "welcome_messages": {
            "en": "Welcome! How can I help you today?",
            "zh": "欢迎！今天我能为您做些什么？"
        },
        "goodbye_messages": {
            "en": "Goodbye! Have a great day!",
            "zh": "再见！祝您有美好的一天！"
        },
        "recommended_questions": {
            "en": [
                "What can you help me with?",
                "How does this work?",
                "Can you explain more about this topic?"
            ],
            "zh": [
                "你能帮我做什么？",
                "这是如何工作的？",
                "你能详细解释一下这个话题吗？"
            ]
        },
        "talk_responses": {
            "en": "I understand your question. Let me help you with that.",
            "zh": "我理解您的问题。让我来帮助您。"
        }
    }


def _normalize_context(context: str) -> str:
    """Normalize context by trimming and collapsing whitespace."""
    if not context:
        return ""
    # Collapse all whitespace runs to a single space and strip ends
    return " ".join(str(context).split())


def _cache_key(language_code: str, context: str) -> str:
    """Build a stable, short cache key safe for Firestore doc IDs.

    Uses lowercase language + 12-char SHA256 of normalized context.
    Avoids very long document IDs and ensures consistent lookups.
    """
    lang = (language_code or "").strip().lower() or "unknown"
    norm_ctx = _normalize_context(context)
    if not norm_ctx:
        return f"v1:{lang}:default"
    digest = hashlib.sha256(norm_ctx.encode("utf-8")).hexdigest()[:12]
    return f"v1:{lang}:{digest}"


def get_cached_presentation_message(language_code: str, context: str = ""):
    """Retrieve cached presentation message from Firestore.
    
    Returns the cached message if found, None otherwise.
    """
    cache_key = _cache_key(language_code, context)
    logger.debug("Looking up cache with key=%s", cache_key)
    try:
        db = _get_db()
        cache_ref = db.collection(
            'xiaoice_presentation_cache'
        ).document(cache_key)
        cached_doc = cache_ref.get()
        
        if cached_doc.exists:
            cached_data = cached_doc.to_dict()
            if cached_data and "message" in cached_data:
                logger.info(
                    "✅ Cache hit for %s (key=%s)",
                    language_code,
                    cache_key
                )
                return cached_data["message"]
            else:
                logger.warning(
                    "Cache doc exists but missing 'message' for key=%s",
                    cache_key
                )
        else:
            logger.info(
                "Cache miss for key=%s (document does not exist)",
                cache_key
            )
    except Exception as e:
        logger.exception(
            "Cache lookup failed for key=%s: %s",
            cache_key,
            e
        )
    return None


def cache_presentation_message(
    language_code: str, message: str, context: str = ""
):
    """Store generated presentation message in Firestore cache."""
    if not message:
        logger.warning(
            "Refusing to cache empty message for %s",
            language_code
        )
        return
    
    cache_key = _cache_key(language_code, context)
    norm_ctx = _normalize_context(context)
    logger.debug("Attempting to cache with key=%s", cache_key)
    try:
        db = _get_db()
        cache_ref = db.collection(
            'xiaoice_presentation_cache'
        ).document(cache_key)
        cache_data = {
            "message": message,
            "language_code": (language_code or "").strip().lower(),
            "context": norm_ctx,
            "context_hash": cache_key.rsplit(":", 1)[-1],
            "updated_at": firestore.SERVER_TIMESTAMP
        }
        logger.debug("Writing cache data: %s", cache_data)
        cache_ref.set(cache_data)
        logger.info("✅ Successfully cached result for key=%s", cache_key)
    except Exception as e:
        logger.exception(
            "❌ Failed to cache result for key=%s: %s",
            cache_key,
            e
        )
