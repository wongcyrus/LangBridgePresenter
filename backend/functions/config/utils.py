"""Utility functions for message generation."""
import hashlib
import re
import logging

logger = logging.getLogger(__name__)


def normalize_context(context: str) -> str:
    """Trim and collapse whitespace in context (speaker notes)."""
    if not context:
        return ""
    return " ".join(str(context).split())


def sanitize_text_for_tts(text: str, max_length: int = 5000, aggressive: bool = False) -> str:
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
    
    # Split overlong sentences to avoid TTS "sentence too long" failures.
    sentence_limit = 220
    sentence_parts = re.split(r'([.!?。！？])\s*', text)
    normalized_parts = []
    for i in range(0, len(sentence_parts), 2):
        sentence = (sentence_parts[i] or "").strip()
        punct = sentence_parts[i + 1] if i + 1 < len(sentence_parts) else ""
        if not sentence:
            continue
        if len(sentence) <= sentence_limit:
            normalized_parts.append(f"{sentence}{punct}")
            continue

        # Try natural pauses first.
        chunks = [s.strip() for s in re.split(r'[，,;；:：、]\s*', sentence) if s.strip()]
        if not chunks:
            chunks = [sentence]
        for chunk in chunks:
            while len(chunk) > sentence_limit:
                normalized_parts.append(f"{chunk[:sentence_limit]}。")
                chunk = chunk[sentence_limit:].lstrip()
            if chunk:
                normalized_parts.append(f"{chunk}。")

    if normalized_parts:
        text = " ".join(normalized_parts).strip()

    # Keep total input bounded.
    if len(text) > max_length:
        text = text[:max_length].rstrip()
    
    return text.strip()


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
    from google.cloud import texttospeech
    
    # First attempt with normal sanitization
    clean_text = sanitize_text_for_tts(text, aggressive=False)
    synthesis_input = texttospeech.SynthesisInput(text=clean_text)
    
    try:
        logger.info("Attempting TTS synthesis (normal sanitization)")
        return tts_client.synthesize_speech(
            request={
                "input": synthesis_input,
                "voice": voice,
                "audio_config": audio_config
            }
        )
    except Exception as e:
        logger.warning(f"TTS synthesis failed with normal sanitization: {e}")
        
        # Retry with aggressive sanitization
        for attempt in range(max_retries):
            try:
                logger.info(f"Retrying TTS synthesis with aggressive sanitization (attempt {attempt + 1}/{max_retries})")
                aggressive_text = sanitize_text_for_tts(text, aggressive=True)
                
                if not aggressive_text:
                    raise ValueError("Text became empty after aggressive sanitization")
                
                synthesis_input = texttospeech.SynthesisInput(text=aggressive_text)
                return tts_client.synthesize_speech(
                    request={
                        "input": synthesis_input,
                        "voice": voice,
                        "audio_config": audio_config
                    }
                )
            except Exception as retry_error:
                logger.warning(f"TTS retry {attempt + 1} failed: {retry_error}")
                if attempt == max_retries - 1:
                    raise
        
        # If we get here, all retries failed
        raise e
