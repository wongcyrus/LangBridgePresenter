# Data Structures Reference

## Slide Content Format

The `slide_content` (also called `latest_languages` in legacy code) is a map of language codes to content objects.

### Structure

```json
{
  "en-US": {
    "text": "Welcome to the presentation about AI",
    "audio_url": "https://storage.googleapis.com/bucket/speech_en-US_abc123.mp3",
    "slide_link": "https://storage.googleapis.com/bucket/slide_0_reimagined.png"
  },
  "zh-CN": {
    "text": "欢迎来到关于人工智能的演示",
    "audio_url": "https://storage.googleapis.com/bucket/speech_zh-CN_abc123.mp3",
    "slide_link": "https://storage.googleapis.com/bucket/slide_0_reimagined.png"
  },
  "yue-HK": {
    "text": "歡迎嚟到關於人工智能嘅演示",
    "audio_url": "https://storage.googleapis.com/bucket/speech_yue-HK_abc123.mp3",
    "slide_link": "https://storage.googleapis.com/bucket/slide_0_reimagined.png"
  }
}
```

### Fields

- **Key**: Language code (BCP-47 format, e.g., `en-US`, `zh-CN`, `yue-HK`)
- **Value**: Object containing:
  - `text` (required): The translated slide content/notes
  - `audio_url` (optional): URL to pre-generated TTS audio file
  - `slide_link` (optional): URL to slide visual image

## VBA Request Format

When VBA sends a slide change to `/api/config`:

```json
{
  "courseId": "showcase",
  "ppt_filename": "presentation_with_visuals.pptm",
  "page_number": 5,
  "context": "This slide discusses machine learning basics",
  "latest_languages": {
    "en-US": {
      "text": "This slide discusses machine learning basics"
    }
  },
  "userParams": {
    "presenterId": "cyber,honey,summer"
  }
}
```

**Note**: VBA typically sends only `text` without `audio_url` or `slide_link`. The backend enriches this data from the registry.

## Registry Structure

### Live Pointer

**Path**: `presentation_broadcast/{courseId}`

```json
{
  "current_presentation_id": "presentation",
  "current_slide_id": "5",
  "latest_languages": {
    "en-US": {
      "text": "...",
      "audio_url": "...",
      "slide_link": "..."
    }
  },
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Slide Registry

**Path**: `presentation_broadcast/{courseId}/presentations/{pptId}/slides/{slideNum}`

```json
{
  "languages": {
    "en-US": {
      "text": "...",
      "audio_url": "...",
      "slide_link": "..."
    },
    "zh-CN": {
      "text": "...",
      "audio_url": "...",
      "slide_link": "..."
    }
  },
  "page_number": 5,
  "source_context": "Original slide notes",
  "course_id": "showcase",
  "supported_languages": ["en-US", "zh-CN", "yue-HK"],
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Backend Config Format

**Path**: `langbridge_config/messages` (Backend DB)

```json
{
  "presentation_messages": {
    "en-US": {
      "text": "...",
      "audio_url": "..."
    }
  },
  "welcome_messages": {},
  "goodbye_messages": {},
  "recommended_questions": {},
  "talk_responses": {},
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Presenter Context Format

**Path**: `presenters/{presenterId}` (Backend DB)

```json
{
  "id": "cyber",
  "name": "Cyber",
  "language": "en-US",
  "background": "Cybersecurity expert AI assistant",
  "current_course_id": "showcase",
  "current_presentation_id": "presentation",
  "current_slide_id": "5",
  "current_slide_languages": {
    "en-US": {
      "text": "...",
      "audio_url": "..."
    }
  },
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Web Client Data Flow

### Live Mode
1. Listen to `presentation_broadcast/{courseId}`
2. Read `latest_languages` for current slide content
3. Extract `audio_url` for selected language
4. Play audio

### Manual/Browse Mode
1. Fetch `presentation_broadcast/{courseId}/presentations/{pptId}/slides/{slideNum}`
2. Read `languages` map
3. Extract `audio_url` for selected language
4. Play audio

## Common Issues

### "Slide not found in registry"
- **Cause**: Slide hasn't been seeded yet
- **Solution**: Run `seed_course_content.py` to populate the registry

### "Audio not playing in live mode"
- **Cause**: `audio_url` missing from `latest_languages`
- **Solution**: Ensure seeding completed successfully and backend enrichment is working

### "Missing required fields"
- **Cause**: VBA not sending complete data
- **Solution**: Check VBA configuration and ensure `courseId`, `ppt_filename`, and `page_number` are set
