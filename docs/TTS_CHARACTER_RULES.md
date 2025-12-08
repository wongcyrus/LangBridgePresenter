# Google Cloud TTS Character Rules and Retry Logic

## Unsupported Characters in Google TTS

Google Cloud Text-to-Speech has specific character limitations that can cause synthesis errors:

### 1. Control Characters
- **Range**: 0x00-0x1F (except tab, newline, carriage return) and 0x7F-0x9F
- **Examples**: NULL, BEL, ESC, DEL
- **Why**: These are non-printable control characters

### 2. Invalid Unicode
- Malformed UTF-8 sequences
- Invalid Unicode code points
- Surrogate pairs used incorrectly

### 3. SSML Reserved Characters (when not using SSML mode)
- `<` (less than)
- `>` (greater than)
- `&` (ampersand)
- `"` (double quote)
- `'` (single quote)

### 4. Rare Unicode Symbols
- Some mathematical symbols (⟪, ⧸, ⟫, etc.)
- Certain emoji or special Unicode blocks
- Uncommon diacritical marks

### 5. Text Length Limits
- **Plain text**: Maximum 5000 bytes
- **SSML**: Maximum 5000 bytes

## Retry Logic Implementation

The codebase now includes automatic retry logic with two-tier sanitization:

### Normal Sanitization (First Attempt)
- Removes known problematic Unicode symbols (⟪, ⧸, ⟫)
- Removes control characters
- Normalizes whitespace
- Handles text length limits

### Aggressive Sanitization (Retry)
When normal sanitization fails, the retry uses more aggressive filtering:
- **Keeps only**: 
  - Letters and numbers (`\w`)
  - Common punctuation: `. , ! ? ; : ( ) - ' "`
  - Whitespace
  - CJK characters (Chinese, Japanese, Korean): `\u4e00-\u9fff`, `\u3040-\u309f`, `\u30a0-\u30ff`
- **Removes**:
  - All emojis
  - Special symbols
  - Rare Unicode characters
  - SSML reserved characters (`<`, `>`, `&`)

## Usage

### In Cloud Functions (backend/functions/*/main.py)
```python
from utils import synthesize_speech_with_retry

# Instead of direct synthesize_speech call:
tts_response = synthesize_speech_with_retry(
    tts_client, 
    text, 
    voice, 
    audio_config,
    max_retries=1  # Optional, defaults to 1
)
```

### In Admin Tools (backend/admin_tools/tts_utils.py)
```python
from tts_utils import synthesize_speech_with_retry

# Same usage as above
tts_response = synthesize_speech_with_retry(
    tts_client, 
    message, 
    voice_params, 
    audio_config
)
```

## Files Updated

1. **backend/functions/config/utils.py**
   - Added `aggressive` parameter to `sanitize_text_for_tts()`
   - Added `synthesize_speech_with_retry()` function

2. **backend/functions/speech/main.py**
   - Updated to use retry logic

3. **backend/seeds/seed_course_content.py**
   - Updated to use retry logic

4. **backend/admin_tools/tts_utils.py**
   - Added `aggressive` parameter to `_sanitize_text_for_tts()`
   - Added `synthesize_speech_with_retry()` function
   - Updated `generate_speech_file()` to use retry logic

## Error Handling

The retry logic will:
1. Attempt synthesis with normal sanitization
2. If it fails, log the error and retry with aggressive sanitization
3. If all retries fail, raise the original exception
4. Log each attempt for debugging

## Common Error Messages

- **"Invalid character in text"**: Usually control characters or invalid Unicode
- **"Text too long"**: Exceeds 5000 byte limit
- **"Invalid SSML"**: SSML reserved characters in plain text mode
- **"Unsupported character"**: Rare Unicode symbols not supported by the voice

## Best Practices

1. Always use the retry logic for user-generated content
2. Pre-sanitize text when possible to avoid retries
3. Monitor logs for frequent retries (indicates content issues)
4. Consider using SSML mode for more control over special characters
5. Test with various languages and character sets
