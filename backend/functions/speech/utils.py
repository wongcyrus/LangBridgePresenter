import logging
import re

from google.cloud import texttospeech

logger = logging.getLogger(__name__)


def sanitize_text_for_tts(text: str, aggressive: bool = False) -> str:
    if not text:
        return ""

    if aggressive:
        text = text.replace("<", "").replace(">", "").replace("&", "and")
        text = re.sub(
            r'[^\w\s.,!?;:()\-\'"。，！？；：（）、""''—&\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]',
            '',
            text,
        )
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    else:
        text = text.replace("⟪", "").replace("⟫", "").replace("⧸", "/")
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    return " ".join(text.split()).strip()


def synthesize_speech_with_retry(
    tts_client,
    text: str,
    voice,
    audio_config,
    max_retries: int = 1,
):
    clean_text = sanitize_text_for_tts(text, aggressive=False)
    synthesis_input = texttospeech.SynthesisInput(text=clean_text)

    try:
        return tts_client.synthesize_speech(
            request={
                "input": synthesis_input,
                "voice": voice,
                "audio_config": audio_config,
            }
        )
    except Exception:
        logger.warning("TTS synthesis failed, retrying with aggressive sanitization")

    for attempt in range(1, max_retries + 1):
        aggressive_text = sanitize_text_for_tts(text, aggressive=True)
        if not aggressive_text:
            raise ValueError("Text became empty after aggressive sanitization")
        try:
            synthesis_input = texttospeech.SynthesisInput(text=aggressive_text)
            return tts_client.synthesize_speech(
                request={
                    "input": synthesis_input,
                    "voice": voice,
                    "audio_config": audio_config,
                }
            )
        except Exception as retry_error:
            logger.warning("TTS retry %s failed: %s", attempt, retry_error)
            if attempt == max_retries:
                raise
