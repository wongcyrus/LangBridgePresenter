import hashlib
import logging
import re
from google.cloud import texttospeech, storage

logger = logging.getLogger(__name__)

def _normalize_context(context: str) -> str:
    """Normalize context by trimming and collapsing whitespace."""
    if not context:
        return ""
    # Collapse all whitespace runs to a single space and strip ends
    return " ".join(str(context).split())

def _sanitize_text_for_tts(text: str, max_length: int = 5000, aggressive: bool = False) -> str:
    """Clean and prepare text for Google TTS API.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum character length for TTS input
        aggressive: If True, apply more aggressive filtering (for retry scenarios)
        
    Returns:
        Sanitized text safe for TTS API
    """
    if not text:
        return ""
    
    if aggressive:
        # Aggressive mode: remove more characters for retry scenarios
        # Keep only: letters, numbers, common punctuation, whitespace, and CJK characters
        # This removes emojis, special symbols, and rare Unicode characters
        text = re.sub(r'[^\w\s.,!?;:()\-\'"。，！？；：（）、""''—\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', '', text)
        
        # Remove SSML reserved characters
        text = text.replace('<', '').replace('>', '').replace('&', 'and')
        
        # Remove any remaining control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    else:
        # Normal mode: gentle sanitization
        # Remove or replace problematic characters
        # Remove special unicode characters that TTS doesn't handle well
        text = text.replace('⟪', '')
        text = text.replace('⧸', '/')
        text = text.replace('⟫', '')
        
        # Remove control characters except common whitespace
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Ensure sentences end with proper punctuation
    # Split very long sentences at natural break points
    if len(text) > max_length:
        # Try to split at sentence boundaries
        sentences = re.split(r'([.!?。！？])\s*', text)
        result = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""
            
            # If adding this sentence would exceed max, start new chunk
            if len(current_chunk) + len(sentence) + len(punct) > max_length:
                if current_chunk:
                    result.append(current_chunk.strip())
                current_chunk = sentence + punct
            else:
                current_chunk += sentence + punct
        
        if current_chunk:
            result.append(current_chunk.strip())
        
        # Return first chunk only (or consider limiting message generation)
        text = result[0] if result else text[:max_length]
    
    return text.strip()


def synthesize_speech_with_retry(tts_client, text: str, voice, audio_config, max_retries: int = 1):
    """Synthesize speech with automatic retry using aggressive sanitization on failure.
    
    Args:
        tts_client: Google TTS client instance
        text: Text to synthesize
        voice: Voice selection parameters
        audio_config: Audio configuration
        max_retries: Number of retries with aggressive sanitization (default: 1)
        
    Returns:
        TTS response object
        
    Raises:
        Exception: If synthesis fails after all retries
    """
    # First attempt with normal sanitization
    clean_text = _sanitize_text_for_tts(text, aggressive=False)
    synthesis_input = texttospeech.SynthesisInput(text=clean_text)
    
    try:
        logger.info("Attempting TTS synthesis (normal sanitization)")
        return tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
    except Exception as e:
        logger.warning(f"TTS synthesis failed with normal sanitization: {e}")
        
        # Retry with aggressive sanitization
        for attempt in range(max_retries):
            try:
                logger.info(f"Retrying TTS synthesis with aggressive sanitization (attempt {attempt + 1}/{max_retries})")
                aggressive_text = _sanitize_text_for_tts(text, aggressive=True)
                
                if not aggressive_text:
                    raise ValueError("Text became empty after aggressive sanitization")
                
                synthesis_input = texttospeech.SynthesisInput(text=aggressive_text)
                return tts_client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
            except Exception as retry_error:
                logger.warning(f"TTS retry {attempt + 1} failed: {retry_error}")
                if attempt == max_retries - 1:
                    raise
        
        # If we get here, all retries failed
        raise e


def generate_speech_file(
    bucket_name: str,
    message: str,
    language_code: str,
    context: str,
    voice_params: texttospeech.VoiceSelectionParams = None
) -> str:
    """Generate speech file and upload to bucket.
    
    Returns:
        Filename of uploaded speech file
    """
    tts_client = texttospeech.TextToSpeechClient()
    storage_client = storage.Client()
    
    # Generate stable filename from CONTEXT hash (not message content)
    # This ensures same context always gets same filename
    norm_ctx = _normalize_context(context)
    content_hash = hashlib.sha256(
        norm_ctx.encode("utf-8")
    ).hexdigest()[:12]
    filename = f"speech_{language_code}_{content_hash}.mp3"
    
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    
    # Note: We deliberately DO NOT skip if the file exists, 
    # because the user might have changed the message content (but not context).
    # In the import flow, we want to overwrite the existing audio file 
    # with the new message content.
    
    # Determine voice params if not provided
    if not voice_params:
        if language_code.startswith("en"):
            voice_language = "en-US"
        elif language_code.startswith("zh"):
            voice_language = "zh-CN"
        else:
            voice_language = "en-US"
            
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=voice_language,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
    
    # Use retry logic for TTS synthesis
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0
    )
    
    tts_response = synthesize_speech_with_retry(
        tts_client, message, voice_params, audio_config
    )
    
    blob.upload_from_string(
        tts_response.audio_content,
        content_type="audio/mpeg"
    )
    logger.info("Generated speech file: %s", filename)
    return filename
