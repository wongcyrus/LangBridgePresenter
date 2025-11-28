import json
import logging
import os
import sys
import functions_framework
from google.cloud import firestore
from firestore_utils import get_cached_presentation_message

_level_name = os.environ.get("LOG_LEVEL", "DEBUG").upper()
_level = getattr(logging, _level_name, logging.DEBUG)
_root = logging.getLogger()
_root.setLevel(_level)
if not any(isinstance(h, logging.StreamHandler) for h in _root.handlers):
    _handler = logging.StreamHandler(sys.stdout)
    _formatter = logging.Formatter(
        "%(levelname)s:%(name)s:%(asctime)s:%(message)s"
    )
    _handler.setFormatter(_formatter)
    _handler.setLevel(_level)
    _root.addHandler(_handler)
logger = logging.getLogger(__name__)
logger.setLevel(_level)


@functions_framework.http
def config(request):
    logger.debug("config invoked: method=%s", request.method)

    if request.method != 'POST':
        logger.warning("method not allowed: %s", request.method)
        return json.dumps({"error": "Method not allowed"}), 405, {
            "Content-Type": "application/json"
        }

    request_json = request.get_json(silent=True)
    if not request_json:
        logger.warning("invalid json body")
        return json.dumps({"error": "Invalid JSON"}), 400, {
            "Content-Type": "application/json"
        }

    try:
        db = firestore.Client(database="langbridge")

        # 1. Extract & Validate Inputs
        course_id = request_json.get("courseId")
        ppt_filename = request_json.get("ppt_filename")
        page_number = request_json.get("page_number")
        latest_languages = request_json.get("latest_languages")
        context = request_json.get("context")

        # If latest_languages is missing but we have context (e.g. from VBA client),
        # attempt to rehydrate from cache.
        if not latest_languages and context:
            latest_languages = {}
            # Use default languages for rehydration
            target_langs = ["en-US", "zh-CN", "yue-HK"]
            
            logger.info(f"Rehydrating from cache for languages: {target_langs}")
            for lang in target_langs:
                msg, audio_url = get_cached_presentation_message(lang, context)
                if msg:
                    lang_data = {"text": msg}
                    if audio_url:
                        lang_data["audio_url"] = audio_url
                    latest_languages[lang] = lang_data
            
            # Fallback if cache completely empty (at least provide English context)
            if not latest_languages:
                 latest_languages = {"en-US": {"text": context}}       


        config_data = {
            "presentation_messages": latest_languages,
            "welcome_messages": request_json.get("welcome_messages", {}),
            "goodbye_messages": request_json.get("goodbye_messages", {}),
            "recommended_questions": request_json.get(
                "recommended_questions", {}
            ),
            "talk_responses": request_json.get("talk_responses", {}),
            "updated_at": firestore.SERVER_TIMESTAMP
        }

        doc_ref = db.collection('langbridge_config').document('messages')
        doc_ref.set(config_data)
        logger.info("Backend config updated in Firestore")

        # --- Restore Client Broadcast Logic for Live Slide ---
        # This part ensures the web-student client can still track the live slide
        # based on data sent to this endpoint.

        if not (course_id and ppt_filename and page_number is not None and latest_languages):
            logger.info(
                "Skipping client broadcast: Missing required fields (courseId, ppt_filename, page_number, or latest_languages).")
            return json.dumps({"success": True}), 200, {"Content-Type": "application/json"}

        # 2. Data Preparation / Normalization
        # Normalize ppt_filename -> safe_ppt_id
        ppt_norm = ppt_filename
        try:
            ppt_norm = os.path.splitext(ppt_filename.lower())[0]
            for _s in ("_with_visuals", "_with_notes", "_visuals", "_en", "_zh-cn", "_yue-HK"):
                if ppt_norm.endswith(_s):
                    ppt_norm = ppt_norm[: -len(_s)]
        except Exception:
            logger.warning(
                f"Normalization failed for {ppt_filename}, using raw value.")

        safe_ppt_id = ppt_norm.replace('/', '_').replace('\\', '_')

        logger.info(
            f"Broadcasting live slide update for course: {course_id} / PPT: {safe_ppt_id} / Slide: {page_number}")

        # 3. Database Operations
        try:
            # TARGET THE CLIENT PROJECT
            client_project_id = os.environ.get(
                "CLIENT_FIRESTORE_PROJECT_ID", "ai-presenter-client")
            client_db = firestore.Client(
                project=client_project_id,
                database=os.environ.get(
                    "CLIENT_FIRESTORE_DATABASE_ID", "(default)")
            )

            doc_id = course_id  # Always use course_id for broadcast doc
            broadcast_ref = client_db.collection(
                'presentation_broadcast').document(doc_id)

            # A. Update Registry
            # This preserves the "history" or "catalog" of the presentation
            ppt_ref = client_db.collection('presentation_broadcast').document(course_id)\
                               .collection('presentations').document(safe_ppt_id)

            # Batch the registry updates if possible, or just sequential
            ppt_ref.set({"updated_at": firestore.SERVER_TIMESTAMP}, merge=True)
            ppt_ref.collection('slides').document(str(page_number)).set({
                "languages": latest_languages,
                "page_number": page_number
            }, merge=True)
            logger.info("Updated slide registry.")

            # B. Update Live Pointer (The "Current State")
            # This tells all connected clients where to look
            live_update = {
                "latest_languages": latest_languages,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "current_presentation_id": safe_ppt_id,
                "current_slide_id": str(page_number)
            }
            broadcast_ref.set(live_update, merge=True)
            logger.info(
                f"Successfully broadcasted live slide updates to client project {client_project_id}.")

        except Exception as b_e:
            logger.error(
                f"❌ Failed to broadcast live slide updates: {b_e}", exc_info=True)

        return json.dumps({"success": True}), 200, {
            "Content-Type": "application/json"
        }

    except Exception as e:
        logger.exception("Failed to update config or broadcast: %s", e)
        return json.dumps({"error": str(e)}), 500, {
            "Content-Type": "application/json"
        }
