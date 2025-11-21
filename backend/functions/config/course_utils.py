import logging
import os
from google.cloud import firestore
from google.cloud import texttospeech

logger = logging.getLogger(__name__)

# Default configuration if no course is specified or found
DEFAULT_LANGUAGES = ["en-US", "zh-CN"]
DEFAULT_VOICES = {
    "en-US": {"name": "en-US-Neural2-J", "gender": texttospeech.SsmlVoiceGender.FEMALE},
    "zh-CN": {"name": "zh-CN-Neural2-C", "gender": texttospeech.SsmlVoiceGender.FEMALE},
    "yue-HK": {"name": "yue-HK-Standard-A", "gender": texttospeech.SsmlVoiceGender.FEMALE},
    "zh-TW": {"name": "zh-TW-Standard-A", "gender": texttospeech.SsmlVoiceGender.FEMALE}
}

def _get_db():
    """Return a Firestore client."""
    db_name = os.environ.get("FIRESTORE_DATABASE", "xiaoice").strip()
    if db_name:
        return firestore.Client(database=db_name)
    return firestore.Client(database="xiaoice")

def get_course_config(course_id: str):
    """Fetch course configuration from Firestore."""
    if not course_id:
        return None

    try:
        db = _get_db()
        doc = db.collection('courses').document(course_id).get()
        if doc.exists:
            return doc.to_dict()
        else:
            logger.warning(f"Course {course_id} not found. Using defaults.")
            return None
    except Exception as e:
        logger.error(f"Error fetching course {course_id}: {e}")
        return None

def get_course_languages(course_id: str):
    """Get list of supported languages for a course."""
    config = get_course_config(course_id)
    if config and "languages" in config:
        return config["languages"]
    return DEFAULT_LANGUAGES

def get_voice_params(course_id: str, language_code: str):
    """Resolve Google TTS VoiceSelectionParams for a given course and language."""
    
    # Defaults
    voice_name = None
    ssml_gender = texttospeech.SsmlVoiceGender.FEMALE

    # Try to find in Course Config
    config = get_course_config(course_id)
    if config and "voice_configs" in config:
        voice_cfg = config["voice_configs"].get(language_code)
        if voice_cfg:
            voice_name = voice_cfg.get("name")
            gender_str = voice_cfg.get("gender", "FEMALE").upper()
            ssml_gender = getattr(texttospeech.SsmlVoiceGender, gender_str, texttospeech.SsmlVoiceGender.FEMALE)

    # Fallback to defaults if not found in course config
    if not voice_name:
        default_cfg = DEFAULT_VOICES.get(language_code)
        if default_cfg:
            voice_name = default_cfg["name"]
            ssml_gender = default_cfg["gender"]
        else:
            # Ultimate fallback
            logger.warning(f"No voice configuration found for {language_code}. Using system default.")
            return texttospeech.VoiceSelectionParams(
                language_code=language_code,
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )

    return texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
        ssml_gender=ssml_gender
    )

def log_presentation_event(course_id: str, event_data: dict):
    """Log a presentation event to the course's history."""
    if not course_id:
        logger.warning("No course_id provided for logging.")
        return

    try:
        db = _get_db()
        # Store in a subcollection 'logs' under the course document
        # This allows easy querying of logs for a specific course
        db.collection('courses').document(course_id).collection('logs').add(event_data)
        logger.info(f"Logged event for course {course_id}")
    except Exception as e:
        logger.error(f"Failed to log event for course {course_id}: {e}")
