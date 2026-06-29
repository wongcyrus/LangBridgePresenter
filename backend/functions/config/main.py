import json
import logging
import os
import sys
import functions_framework
from google.cloud import firestore
from firestore_utils import _get_db, _get_client_db
from course_utils import get_course_config
from _shared.context_utils import extract_presenter_ids
from broadcast_utils import (
    build_broadcast_course_ids,
    build_live_update,
    build_presenter_update,
    build_safe_ppt_id,
    enrich_slide_languages,
    resolve_slide_content,
    should_fetch_slide_content,
    should_update_slide_registry,
)

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
    logger.info("=" * 80)
    logger.info("📥 CONFIG ENDPOINT INVOKED")
    logger.info("=" * 80)
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request headers: {dict(request.headers)}")

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

    logger.debug(f"📦 Request payload keys: {list(request_json.keys())} ")

    try:
        db = _get_db()

        # 1. Extract & Validate Inputs
        course_id = request_json.get("courseId")
        ppt_filename = request_json.get("ppt_filename")
        page_number = request_json.get("page_number")
        context = request_json.get("context")
        
        # slide_content: Map of language codes to content
        # Format: {"en-US": {"text": "...", "audio_url": "...", "slide_link": "..."}}
        # Accept both 'latest_languages' (new) and 'presentation_messages' (VBA legacy)
        slide_content = resolve_slide_content(request_json)
        
        logger.info(f"📋 Extracted Fields:")
        logger.info(f"   courseId: {course_id}")
        logger.info(f"   ppt_filename: {ppt_filename}")
        logger.info(f"   page_number: {page_number}")
        logger.info(f"   context length: {len(context) if context else 0} chars")
        logger.info(f"   slide_content type: {type(slide_content)}")
        logger.info(f"   slide_content value: {slide_content}")
        logger.info(f"   slide_content bool: {bool(slide_content)}")
        if slide_content:
            logger.info(f"   slide_content languages: {list(slide_content.keys())}")
            for lang, data in slide_content.items():
                has_text = "text" in data if isinstance(data, dict) else False
                has_audio = "audio_url" in data if isinstance(data, dict) else False
                has_visual = "slide_link" in data if isinstance(data, dict) else False
                logger.debug(f"      [{lang}] text={has_text}, audio={has_audio}, visual={has_visual}")

        # Extract presenter_id from userParams (supports comma-separated IDs)
        userParams = request_json.get("userParams", {})
        logger.debug(f"Raw userParams received: {userParams} (type: {type(userParams)})")
        presenter_ids = extract_presenter_ids(userParams)
        logger.debug(f"Extracted presenter_ids: {presenter_ids}")

        # If slide_content not provided by VBA or is empty, fetch from registry
        # This happens when VBA sends slide changes without pre-loaded content
        # Check for None, empty dict, empty string, etc.
        if should_fetch_slide_content(slide_content):
            logger.info("🔍 Slide content not provided by VBA, fetching from registry...")
            
            if course_id and ppt_filename and page_number is not None:
                logger.debug(f"   Attempting registry fetch with: course={course_id}, ppt={ppt_filename}, page={page_number}")
                try:
                    # Fetch from client broadcast registry (seeded data)
                    # Use the same env var name as set in CDKTF
                    client_project_id = os.environ.get("CLIENT_FIRESTORE_PROJECT_ID", "ai-presenter-client")
                    logger.debug(f"   Client project ID: {client_project_id}")
                    
                    if client_project_id:
                        client_db = _get_client_db()
                        
                        # Normalize ppt filename
                        try:
                            safe_ppt_id = build_safe_ppt_id(ppt_filename)
                            logger.debug(
                                "   Normalized PPT ID: %s → %s",
                                ppt_filename,
                                safe_ppt_id,
                            )
                        except Exception as norm_e:
                            safe_ppt_id = build_safe_ppt_id(ppt_filename)
                            logger.warning("   Normalization failed: %s, using: %s", norm_e, safe_ppt_id)
                        
                        registry_path = f"presentation_broadcast/{course_id}/presentations/{safe_ppt_id}/slides/{page_number}"
                        logger.info(f"   📂 Registry lookup:")
                        logger.info(f"      Original filename: {ppt_filename}")
                        logger.info(f"      Normalized ID: {safe_ppt_id}")
                        logger.info(f"      Full path: {registry_path}")
                        
                        slide_ref = client_db.collection('presentation_broadcast').document(course_id)\
                                             .collection('presentations').document(safe_ppt_id)\
                                             .collection('slides').document(str(page_number))
                        slide_doc = slide_ref.get()
                        logger.info(f"      Exists: {slide_doc.exists}")
                        
                        if slide_doc.exists:
                            slide_data = slide_doc.to_dict()
                            slide_content = slide_data.get("languages", {})
                            logger.info(f"✅ Fetched complete slide data from registry")
                            logger.info(f"   Languages: {list(slide_content.keys())}")
                            for lang, data in slide_content.items():
                                has_audio = "audio_url" in data if isinstance(data, dict) else False
                                logger.debug(f"      [{lang}] has_audio={has_audio}")
                        else:
                            logger.warning(f"⚠️  Slide not found in registry. Please run seeding first.")
                            logger.warning(f"    Path: {registry_path}")
                            logger.warning(f"    Skipping broadcast for unseeded slide.")
                            # Don't create fallback - let it remain None so broadcast is skipped
                            slide_content = None
                except Exception as e:
                    logger.error(f"Failed to fetch from broadcast registry: {e}", exc_info=True)
                    logger.warning(f"Skipping broadcast due to registry fetch error.")
                    slide_content = None
            else:
                logger.warning(f"Cannot fetch from registry - missing fields: courseId={course_id}, ppt={ppt_filename}, page={page_number}")
                logger.warning(f"Skipping broadcast for incomplete request.")
                slide_content = None       


        # Update backend config (for legacy compatibility)
        config_data = {
            "presentation_messages": slide_content,
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

        # --- Client Broadcast Logic for Live Slide ---
        # This updates the live pointer so web clients know what's currently being presented

        if not (course_id and ppt_filename and page_number is not None and slide_content):
            logger.warning(
                f"⚠️  Skipping client broadcast - Missing required fields:")
            logger.warning(f"    courseId: {course_id}")
            logger.warning(f"    ppt_filename: {ppt_filename}")
            logger.warning(f"    page_number: {page_number}")
            logger.warning(f"    slide_content: {'Present' if slide_content else 'Missing'}")
            return json.dumps({"success": True}), 200, {"Content-Type": "application/json"}

        # Check if this course has multiple styles - if so, broadcast to all style variants
        try:
            course_config = get_course_config(course_id)
            broadcast_course_ids = build_broadcast_course_ids(course_id, course_config)
            if len(broadcast_course_ids) > 1:
                logger.info(f"Course {course_id} has multiple styles: {broadcast_course_ids[1:]}")
                logger.info(f"Broadcasting to course IDs: {broadcast_course_ids}")
        except Exception as e:
            logger.warning(f"Failed to check course styles: {e}")
            # Continue with just the main course_id
            broadcast_course_ids = [course_id]

        # 2. Data Preparation / Normalization
        logger.info("🔧 Normalizing PPT filename for broadcast...")
        # Normalize ppt_filename -> safe_ppt_id
        try:
            safe_ppt_id = build_safe_ppt_id(ppt_filename)
            logger.debug("   Normalized: %s → %s", ppt_filename, safe_ppt_id)
        except Exception as e:
            logger.warning(f"   Normalization failed for {ppt_filename}: {e}")
            safe_ppt_id = build_safe_ppt_id(ppt_filename)
        logger.debug(f"   Safe ID: {safe_ppt_id}")

        logger.info(f"📡 Broadcasting live slide update:")
        logger.info(f"   Course: {course_id}")
        logger.info(f"   PPT: {safe_ppt_id}")
        logger.info(f"   Slide: {page_number}")

        # 3. Database Operations
        try:
            # TARGET THE CLIENT PROJECT
            client_db = _get_client_db()

            # Broadcast to all relevant course IDs (main course + style variants)
            for broadcast_course_id in broadcast_course_ids:
                logger.info(f"📡 Broadcasting to course: {broadcast_course_id}")
                
                broadcast_ref = client_db.collection(
                    'presentation_broadcast').document(broadcast_course_id)

                # A. Fetch existing registry data for this specific course
                ppt_ref = client_db.collection('presentation_broadcast').document(broadcast_course_id)\
                                   .collection('presentations').document(safe_ppt_id)
                slide_ref = ppt_ref.collection('slides').document(str(page_number))
                existing_slide = slide_ref.get()
            
                # Use style-specific content if available, otherwise use the input content
                logger.info(f"🎨 Preparing slide content for {broadcast_course_id}...")
                logger.debug(f"   Existing slide in registry: {existing_slide.exists}")
                
                # If this is a style variant and we have seeded content, use that instead
                existing_data = existing_slide.to_dict() if existing_slide.exists else {}
                existing_languages = existing_data.get("languages", {})

                if broadcast_course_id != course_id and existing_slide.exists:
                    # Use the seeded style-specific content
                    enriched_languages = existing_languages
                    logger.info(f"   ✅ Using seeded style-specific content for {broadcast_course_id}")
                    logger.info(f"   Languages: {list(enriched_languages.keys())}")
                else:
                    # Use the input content and enrich with audio URLs
                    enriched_languages = enrich_slide_languages(slide_content, existing_languages)
                    for lang, data in enriched_languages.items():
                        has_audio = "audio_url" in data
                        has_visual = "slide_link" in data
                        logger.debug(f"   [{lang}] Input: audio={has_audio}, visual={has_visual}")
                        if has_audio:
                            logger.debug(f"   ✓ [{lang}] Already has audio_url")
                        elif lang in existing_languages and "audio_url" in existing_languages.get(lang, {}):
                            audio_url = existing_languages[lang]["audio_url"]
                            logger.info(f"   ✅ [{lang}] Enriched with audio_url: {audio_url[:60]}...")
                        elif existing_slide.exists:
                            logger.warning(f"   ⚠️  [{lang}] Not found in registry or missing audio_url")
                            if lang in existing_languages:
                                logger.debug(f"      Registry has: {list(existing_languages[lang].keys())}")
                        else:
                            logger.warning(f"   ⚠️  [{lang}] Cannot enrich: slide doesn't exist in registry yet")
            
                # Update presentation timestamp
                ppt_ref.set({"updated_at": firestore.SERVER_TIMESTAMP}, merge=True)
                
                # Determine if we should update the slide registry
                should_update = False
                if not existing_slide.exists:
                    logger.info(f"Slide {page_number} doesn't exist for {broadcast_course_id}, creating it")
                    should_update = True
                else:
                    # Check if context has changed OR if we have new data to add
                    should_update = should_update_slide_registry(
                        existing_data, context, enriched_languages
                    )
                    if existing_data.get("source_context", "") != context:
                        logger.info(f"Slide {page_number} context changed for {broadcast_course_id}, updating")
                    elif should_update:
                        logger.info(
                            f"Slide {page_number} content changed for {broadcast_course_id}, updating"
                        )
                    else:
                        logger.info(f"Slide {page_number} unchanged for {broadcast_course_id}, skipping registry update")
                
                # Update registry with enriched data (preserves audio_url)
                if should_update:
                    slide_ref.set({
                        "languages": enriched_languages,
                        "page_number": page_number,
                        "source_context": context
                    }, merge=True)
                    logger.info(f"Updated slide registry for {broadcast_course_id}.")

                # B. Update Live Pointer (The "Current State")
                # This tells all connected clients where to look
                logger.info(f"📍 Updating live pointer for {broadcast_course_id}...")
                
                live_update = build_live_update(safe_ppt_id, page_number, enriched_languages)
                live_update["updated_at"] = firestore.SERVER_TIMESTAMP
                
                logger.debug(f"   Live pointer data for {broadcast_course_id}:")
                logger.debug(f"      current_presentation_id: {safe_ppt_id}")
                logger.debug(f"      current_slide_id: {page_number}")
                logger.debug(f"      latest_languages keys: {list(enriched_languages.keys())}")
                for lang, data in enriched_languages.items():
                    has_audio = "audio_url" in data if isinstance(data, dict) else False
                    logger.debug(f"         [{lang}] has_audio={has_audio}")
                
                broadcast_ref.set(live_update, merge=True)
                logger.info(f"   ✅ Live pointer updated for {broadcast_course_id}")

            # C. Update Presenter Context (Backend DB) - only once for the main course
            # Save current course, presentation, slide pointers for lazy loading
            # talk-stream will fetch all_slides on-demand when needed
            # REQUIRES both course_id and presenter_ids
            logger.debug(f"Before presenter context update - course_id: {course_id}, presenter_ids: {presenter_ids}")
            if presenter_ids and course_id:
                presenter_update = build_presenter_update(
                    course_id, safe_ppt_id, page_number, enriched_languages
                )
                presenter_update["updated_at"] = firestore.SERVER_TIMESTAMP
                
                # Update all presenters in the list
                for presenter_id in presenter_ids:
                    try:
                        presenter_ref = db.collection('presenters').document(presenter_id)
                        presenter_ref.set(presenter_update, merge=True)
                        logger.info(f"Updated presenter {presenter_id} context - current slide: {page_number}")
                    except Exception as presenter_e:
                        logger.error(f"Failed to update presenter {presenter_id} context: {presenter_e}", exc_info=True)
            elif presenter_ids and not course_id:
                logger.warning(f"Presenter IDs provided ({presenter_ids}) but missing Course ID - skipping presenter context update")
            elif course_id and not presenter_ids:
                logger.warning(f"Course ID provided ({course_id}) but missing Presenter IDs - skipping presenter context update")

        except Exception as b_e:
            logger.error(f"❌ Failed to broadcast live slide updates: {b_e}", exc_info=True)

        logger.info("=" * 80)
        logger.info("✅ CONFIG ENDPOINT COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        return json.dumps({"success": True}), 200, {
            "Content-Type": "application/json"
        }

    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ CONFIG ENDPOINT FAILED")
        logger.error("=" * 80)
        logger.exception("Failed to update config or broadcast: %s", e)
        return json.dumps({"error": str(e)}), 500, {
            "Content-Type": "application/json"
        }
