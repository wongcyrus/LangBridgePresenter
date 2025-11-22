import json
import logging
import os
import sys
import hashlib
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

            for lang in languages:
                # Pass course_id to generation logic
                generated = generate_presentation_message(lang, context, course_id=course_id)
                if generated:
                    presentation_messages[lang] = generated
                    logger.info(
                        "Generated presentation for %s: %s",
                        lang,
                        generated
                    )
                    
                    # Logic to broadcast speech URL
                    lang_data = {"text": generated}
                    if bucket_name:
                        try:
                            # Reconstruct filename hash logic matching preload script
                            content_hash = hashlib.sha256(
                                f"{generated}:{lang}".encode("utf-8")
                            ).hexdigest()[:12]
                            filename = f"speech_{lang}_{content_hash}.mp3"
                            
                            # Check if file exists, if not create it
                            storage_client = storage.Client()
                            bucket = storage_client.bucket(bucket_name)
                            blob = bucket.blob(filename)
                            
                            if not blob.exists():
                                logger.info("Generating new speech file: %s", filename)
                                tts_client = texttospeech.TextToSpeechClient()
                                
                                # Use Course Config for Voice Selection
                                voice = course_utils.get_voice_params(course_id, lang)
                                
                                synthesis_input = texttospeech.SynthesisInput(text=generated)
                                audio_config = texttospeech.AudioConfig(
                                    audio_encoding=texttospeech.AudioEncoding.MP3,
                                    speaking_rate=1.0
                                )
                                tts_response = tts_client.synthesize_speech(
                                    input=synthesis_input,
                                    voice=voice,
                                    audio_config=audio_config
                                )
                                
                                blob.upload_from_string(
                                    tts_response.audio_content,
                                    content_type="audio/mpeg"
                                )
                                logger.info("Uploaded new speech file: %s", filename)
                            else:
                                logger.info("Using cached speech file: %s", filename)

                            # Public URL for the object
                            speech_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
                            lang_data["audio_url"] = speech_url
                            logger.info("Broadcast audio URL for %s: %s", lang, speech_url)
                        except Exception as tts_e:
                             logger.error("Failed to generate/upload speech for %s: %s", lang, tts_e)
                    
                    broadcast_payload["languages"][lang] = lang_data
            
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
