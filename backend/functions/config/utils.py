"""Utility functions for message generation."""
import hashlib
import re


def normalize_context(context: str) -> str:
    """Trim and collapse whitespace in context (speaker notes)."""
    if not context:
        return ""
    return " ".join(str(context).split())


def sanitize_text_for_tts(text: str, max_length: int = 5000) -> str:
    """Clean and prepare text for Google TTS API.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum character length for TTS input
        
    Returns:
        Sanitized text safe for TTS API
    """
    if not text:
        return ""
    
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
