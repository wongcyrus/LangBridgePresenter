import json
import logging
import os
import sys
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import functions_framework
from google.cloud import firestore, texttospeech, storage
from message_generator import generate_presentation_message
import course_utils

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

        # Handle presentation message generation if requested
        presentation_messages = request_json.get("presentation_messages", {})
        
        # Prepare broadcast payload
        broadcast_payload = {
            "updated_at": firestore.SERVER_TIMESTAMP,
            "languages": {}
        }
        bucket_name = os.environ.get("SPEECH_FILE_BUCKET")
        course_id = request_json.get("courseId")

        if request_json.get("generate_presentation", False):
            logger.info(f"Generating presentation messages with agent. CourseID: {course_id}")
            
            # Use course languages if available, else fallback to request or default
            if course_id:
                languages = course_utils.get_course_languages(course_id)
            else:
                languages = request_json.get("languages", ["en"])
            
            # Only accept the canonical 'context' field from clients
            context = request_json.get("context", "")
            # Log the provided speaker notes context with a safe preview
            _ctx = context or ""
            _preview = _ctx[:500] + ("…" if len(_ctx) > 500 else "")
            logger.info(
                "Received presentation 'context' (%d chars): %s",
                len(_ctx),
                _preview
            )
            
            # Log this event
            if course_id:
                course_utils.log_presentation_event(course_id, {
                    "type": "slide_change",
                    "context_snippet": _preview,
                    "languages": languages,
                    "timestamp": firestore.SERVER_TIMESTAMP
                })

            # Add context to broadcast payload so clients can see original text if needed
            broadcast_payload["original_context"] = context
            broadcast_payload["course_id"] = course_id
            broadcast_payload["supported_languages"] = languages

            if not context:
                logger.warning(
                    "No speaker notes provided in 'context'. "
                    "Will generate a generic message and skip caching."
                )

            # Step 1: Generate all messages in parallel
            logger.info("Generating messages for %d languages in parallel", len(languages))
            message_results = {}
            
            def generate_for_language(lang):
                """Helper to generate message for a single language"""
                try:
                    result = generate_presentation_message(lang, context, course_id=course_id)
                    if isinstance(result, tuple):
                        generated, audio_url = result
                    else:
                        # Backwards compatibility
                        generated = result
                        audio_url = None
                    
                    if generated:
                        logger.info("Generated presentation for %s: %s", lang, generated)
                        return (lang, generated, audio_url, None)
                    else:
                        logger.warning("Failed to generate message for %s", lang)
                        return (lang, None, None, "Generation failed")
                except Exception as e:
                    logger.error("Error generating message for %s: %s", lang, e)
                    return (lang, None, None, str(e))
            
            with ThreadPoolExecutor(max_workers=min(len(languages), 5)) as executor:
                future_to_lang = {executor.submit(generate_for_language, lang): lang for lang in languages}
                for future in as_completed(future_to_lang):
                    lang, generated, audio_url, error = future.result()
                    if generated:
                        message_results[lang] = {
                            "text": generated,
                            "audio_url": audio_url  # May be None
                        }
                        presentation_messages[lang] = generated
            
            logger.info("Generated %d/%d messages successfully", len(message_results), len(languages))
            
            # Step 2: Generate MP3s in parallel for all successful messages
            if not bucket_name:
                logger.warning("SPEECH_FILE_BUCKET not configured - skipping all audio generation")
                # Add text-only data to broadcast
                for lang, data in message_results.items():
                    broadcast_payload["languages"][lang] = {"text": data["text"]}
            else:
                logger.info("Generating MP3s for %d languages in parallel", len(message_results))
                
                def generate_mp3_for_language(lang, data):
                    """Helper to generate MP3 for a single language"""
                    generated = data["text"]
                    cached_audio_url = data.get("audio_url")
                    
                    # If we have cached audio_url, use it
                    if cached_audio_url:
                        logger.info("[MP3-%s] ✅ Using cached audio_url: %s", lang, cached_audio_url)
                        return (lang, {"text": generated, "audio_url": cached_audio_url}, None)
                    
                    logger.info("[MP3-START] Processing %s: '%s...'", lang, generated[:50])
                    lang_data = {"text": generated}
                    try:
                        # Generate filename from CONTEXT hash (not message content)
                        # This ensures same context always gets same filename
                        from utils import normalize_context
                        norm_ctx = normalize_context(context)
                        content_hash = hashlib.sha256(
                            norm_ctx.encode("utf-8")
                        ).hexdigest()[:12]
                        filename = f"speech_{lang}_{content_hash}.mp3"
                        logger.info("[MP3-%s] Context hash: %s, Filename: %s", lang, content_hash, filename)
                        
                        # Initialize clients inside the thread
                        storage_client = storage.Client()
                        bucket = storage_client.bucket(bucket_name)
                        blob = bucket.blob(filename)
                        
                        if not blob.exists():
                            logger.info("[MP3-%s] File not cached, generating TTS", lang)
                            tts_client = texttospeech.TextToSpeechClient()
                            
                            # Use Course Config for Voice Selection
                            voice = course_utils.get_voice_params(course_id, lang)
                            logger.info("[MP3-%s] Using voice: %s", lang, voice.name if hasattr(voice, 'name') else voice.language_code)
                            
                            # Sanitize text for TTS API
                            from utils import sanitize_text_for_tts
                            clean_text = sanitize_text_for_tts(generated)
                            if clean_text != generated:
                                logger.info("[MP3-%s] Text sanitized for TTS (removed %d chars)", lang, len(generated) - len(clean_text))
                            
                            synthesis_input = texttospeech.SynthesisInput(text=clean_text)
                            audio_config = texttospeech.AudioConfig(
                                audio_encoding=texttospeech.AudioEncoding.MP3,
                                speaking_rate=1.0
                            )
                            logger.info("[MP3-%s] Calling TTS API...", lang)
                            tts_response = tts_client.synthesize_speech(
                                input=synthesis_input,
                                voice=voice,
                                audio_config=audio_config
                            )
                            logger.info("[MP3-%s] TTS response received, size: %d bytes", lang, len(tts_response.audio_content))
                            
                            blob.upload_from_string(
                                tts_response.audio_content,
                                content_type="audio/mpeg"
                            )
                            logger.info("[MP3-%s] ✅ Uploaded new speech file: %s", lang, filename)
                        else:
                            logger.info("[MP3-%s] ✅ Using cached speech file: %s", lang, filename)

                        # Public URL for the object
                        speech_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
                        lang_data["audio_url"] = speech_url
                        logger.info("[MP3-%s] ✅ Audio URL ready: %s", lang, speech_url)
                        
                        # Update cache with audio_url for future lookups
                        from firestore_utils import cache_presentation_message
                        try:
                            cache_presentation_message(
                                lang, 
                                generated, 
                                context, 
                                course_id=course_id, 
                                audio_url=speech_url
                            )
                            logger.info("[MP3-%s] Updated cache with audio_url", lang)
                        except Exception as cache_e:
                            logger.warning("[MP3-%s] Failed to update cache: %s", lang, cache_e)
                        
                        return (lang, lang_data, None)
                        
                    except Exception as tts_e:
                        logger.error("[MP3-%s] ❌ Failed: %s", lang, str(tts_e), exc_info=True)
                        logger.warning("[MP3-%s] Broadcasting text without audio", lang)
                        return (lang, lang_data, str(tts_e))
                
                with ThreadPoolExecutor(max_workers=min(len(message_results), 5)) as executor:
                    future_to_lang = {
                        executor.submit(generate_mp3_for_language, lang, data): lang 
                        for lang, data in message_results.items()
                    }
                    for future in as_completed(future_to_lang):
                        lang, lang_data, error = future.result()
                        broadcast_payload["languages"][lang] = lang_data
                        if error:
                            logger.warning("MP3 generation had error for %s: %s", lang, error)
                
                logger.info("Completed MP3 generation for %d languages", len(broadcast_payload["languages"]))
            
            # Broadcast the updates to a dedicated collection for listeners
            if broadcast_payload["languages"]:
                try:
                    # TARGET THE CLIENT PROJECT
                    # The client is connected to 'xiaoice-class-assistant' project.
                    # The database there is named '(default)'.
                    broadcast_db = firestore.Client(
                        project=os.environ.get("CLIENT_FIRESTORE_PROJECT_ID", "ai-presenter-client"),
                        database=os.environ.get("CLIENT_FIRESTORE_DATABASE_ID", "(default)") 
                    )
                    # Use course_id as document ID if available, else 'current'
                    doc_id = course_id if course_id else 'current'
                    broadcast_ref = broadcast_db.collection('presentation_broadcast').document(doc_id)
                    broadcast_ref.set(broadcast_payload)
                    
                    # Add to history (subcollection)
                    broadcast_ref.collection('messages').add(broadcast_payload)
                    
                    logger.info(f"Successfully broadcasted presentation updates to xiaoice-class-assistant (doc: {doc_id})")
                except Exception as b_e:
                    logger.error("Failed to broadcast presentation updates: %s", b_e)

        config_data = {
            "presentation_messages": presentation_messages,
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
        logger.info("config updated in Firestore")
        return json.dumps({"success": True}), 200, {
            "Content-Type": "application/json"
        }

    except Exception as e:
        logger.exception("failed to update config: %s", e)
        return json.dumps({"error": str(e)}), 500, {
            "Content-Type": "application/json"
        }
