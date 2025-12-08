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

        # Extract presenter_id from userParams
        userParams = request_json.get("userParams", {})
        logger.debug(f"Raw userParams received: {userParams} (type: {type(userParams)})")
        presenter_id = userParams.get("presenterId") if isinstance(userParams, dict) else None
        logger.debug(f"Extracted presenter_id: {presenter_id}")

        # If latest_languages is missing, try to fetch from broadcast document first
        if not latest_languages:
            if course_id and ppt_filename and page_number is not None:
                try:
                    # Try to fetch from client broadcast document
                    client_project_id = os.environ.get("CLIENT_PROJECT_ID")
                    if client_project_id:
                        client_db = firestore.Client(project=client_project_id, database="(default)")
                        
                        # Normalize ppt filename
                        safe_ppt_id = ppt_filename
                        try:
                            _ppt_norm = os.path.splitext(ppt_filename.lower())[0]
                            for _s in ("_with_visuals", "_with_notes", "_visuals", "_en", "_zh-cn", "_yue-hk"):
                                if _ppt_norm.endswith(_s):
                                    _ppt_norm = _ppt_norm[: -len(_s)]
                            safe_ppt_id = _ppt_norm.replace('/', '_').replace('\\', '_')
                        except:
                            safe_ppt_id = ppt_filename.replace('/', '_').replace('\\', '_')
                        
                        slide_ref = client_db.collection('presentation_broadcast').document(course_id)\
                                             .collection('presentations').document(safe_ppt_id)\
                                             .collection('slides').document(str(page_number))
                        slide_doc = slide_ref.get()
                        
                        if slide_doc.exists:
                            slide_data = slide_doc.to_dict()
                            latest_languages = slide_data.get("languages", {})
                            logger.info(f"✅ Fetched languages from broadcast: {list(latest_languages.keys())}")
                except Exception as e:
                    logger.warning(f"Failed to fetch from broadcast document: {e}")
            
            # Fallback to cache rehydration if broadcast fetch failed
            if not latest_languages and context:
                latest_languages = {}
                target_langs = ["en-US", "zh-CN", "yue-HK"]
                
                logger.info(f"Rehydrating from cache for languages: {target_langs}")
                for lang in target_langs:
                    msg, audio_url = get_cached_presentation_message(lang, context)
                    if msg:
                        lang_data = {"text": msg}
                        if audio_url:
                            lang_data["audio_url"] = audio_url
                        latest_languages[lang] = lang_data
                
                # Final fallback if cache completely empty
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

            # Update presentation timestamp
            ppt_ref.set({"updated_at": firestore.SERVER_TIMESTAMP}, merge=True)
            
            # Only update slide if it doesn't exist or if context has changed
            slide_ref = ppt_ref.collection('slides').document(str(page_number))
            existing_slide = slide_ref.get()
            
            should_update = False
            if not existing_slide.exists:
                logger.info(f"Slide {page_number} doesn't exist, creating it")
                should_update = True
            else:
                # Check if context has changed
                existing_data = existing_slide.to_dict()
                existing_context = existing_data.get("source_context", "")
                if existing_context != context:
                    logger.info(f"Slide {page_number} context changed, updating")
                    should_update = True
                else:
                    logger.info(f"Slide {page_number} unchanged, skipping update")
            
            if should_update:
                slide_ref.set({
                    "languages": latest_languages,
                    "page_number": page_number,
                    "source_context": context  # Store context to detect changes
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

            # C. Update Presenter Context (Backend DB)
            # Save current course, presentation, slide, and ALL slides from the presentation
            # This context will be loaded by talk-stream to provide the agent with full presentation context
            # REQUIRES both course_id and presenter_id
            logger.debug(f"Before presenter context update - course_id: {course_id}, presenter_id: {presenter_id}")
            if presenter_id and course_id:
                try:
                    # Load all slides from the presentation
                    slides_ref = client_db.collection('presentation_broadcast').document(course_id)\
                                          .collection('presentations').document(safe_ppt_id)\
                                          .collection('slides')
                    
                    all_slides = {}
                    slides_docs = slides_ref.stream()
                    for slide_doc in slides_docs:
                        slide_data = slide_doc.to_dict()
                        slide_id = slide_doc.id
                        all_slides[slide_id] = slide_data
                    
                    logger.info(f"Loaded {len(all_slides)} slides for presentation {safe_ppt_id}")
                    
                    presenter_update = {
                        "current_course_id": course_id,
                        "current_presentation_id": safe_ppt_id,
                        "current_slide_id": str(page_number),
                        "current_slide_languages": latest_languages,
                        "all_slides": all_slides,
                        "updated_at": firestore.SERVER_TIMESTAMP
                    }
                    presenter_ref = db.collection('presenters').document(presenter_id)
                    presenter_ref.set(presenter_update, merge=True)
                    logger.info(f"Updated presenter {presenter_id} context with {len(all_slides)} slides, current slide: {page_number}")
                except Exception as presenter_e:
                    logger.error(f"Failed to update presenter context: {presenter_e}", exc_info=True)
            elif presenter_id and not course_id:
                logger.warning(f"Presenter ID provided ({presenter_id}) but missing Course ID - skipping presenter context update")
            elif course_id and not presenter_id:
                logger.warning(f"Course ID provided ({course_id}) but missing Presenter ID - skipping presenter context update")

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
