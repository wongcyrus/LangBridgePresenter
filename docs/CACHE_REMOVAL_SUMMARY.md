# Cache Layer Removal - Architecture Simplification

## Summary

The system has been simplified by removing the `langbridge_presentation_cache` collection and making the presentation registry the single source of truth.

## What Changed

### Removed Components
- ❌ `langbridge_presentation_cache` Firestore collection
- ❌ Cache key generation logic (`_cache_key`, `_normalize_context`)
- ❌ Cache lookup functions in `main.py`
- ❌ Cache writing in `seed_course_content.py`
- ❌ Excel cache editor tools

### New Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SEEDING (One-time)                       │
│  seed_course_content.py                                     │
│    ↓                                                         │
│  1. Load pre-generated text from progress files             │
│  2. Generate TTS audio → Upload to GCS bucket               │
│  3. Upload visuals to GCS bucket                            │
│  4. Write complete data to REGISTRY                         │
│     presentation_broadcast/{course}/presentations/{ppt}/    │
│     slides/{num}                                            │
│       ├─ languages                                          │
│       │   ├─ en-US: {text, audio_url, slide_link}          │
│       │   ├─ zh-CN: {text, audio_url, slide_link}          │
│       │   └─ yue-HK: {text, audio_url, slide_link}         │
│       ├─ page_number                                        │
│       └─ source_context                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  LIVE PRESENTATION                          │
│  VBA → main.py (config endpoint)                            │
│    ↓                                                         │
│  1. Receive slide change from VBA                           │
│  2. Fetch complete slide data from REGISTRY                 │
│  3. Enrich any missing audio_urls from REGISTRY             │
│  4. Broadcast enriched data to LIVE POINTER                 │
│     presentation_broadcast/{course}                         │
│       ├─ current_presentation_id                            │
│       ├─ current_slide_id                                   │
│       └─ latest_languages (with audio_url)                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    WEB CLIENT                               │
│  React App (App.jsx)                                        │
│    ↓                                                         │
│  LIVE MODE: Listen to live pointer → Get audio_url → Play  │
│  MANUAL MODE: Fetch from registry → Get audio_url → Play   │
└─────────────────────────────────────────────────────────────┘
```

## Benefits

### ✅ Simplicity
- Single source of truth (registry)
- No cache key hashing logic
- No dual lookup paths
- Fewer moving parts

### ✅ Reliability
- Audio URLs guaranteed to exist (if seeded)
- No hash mismatches between seeding and runtime
- Consistent data structure everywhere

### ✅ Performance
- Direct registry fetch (no cache layer overhead)
- Pre-generated content (instant delivery)
- No runtime AI generation for slides

### ✅ Maintainability
- Easier to debug (one place to check)
- Simpler code (less complexity)
- Clear data flow

## Migration Guide

### For Existing Deployments

1. **Run seeding** to populate the registry:
   ```bash
   cd backend/seeds
   python seed_course_content.py --course-id showcase --data-dir generate
   ```

2. **Deploy updated functions**:
   ```bash
   ./deploy.sh
   ```

3. **Optional: Clean up old cache** (if desired):
   - The old `langbridge_presentation_cache` collection is no longer used
   - You can delete it manually from Firestore console if needed
   - No impact on functionality

### For New Deployments

1. Deploy infrastructure
2. Run seeding script
3. Start presenting

## Files Modified

### Backend
- `backend/functions/config/main.py` - Removed cache logic, simplified to registry-only
- `backend/seeds/seed_course_content.py` - Removed cache writing

### Documentation
- `docs/ARCHITECTURE.md` - Updated data flow and caching section
- `docs/BACKEND.md` - Updated data model and added seeding section
- `docs/ADMIN_TOOLS.md` - Removed cache editor, added seeding workflow

## Breaking Changes

### None for End Users
- VBA client works the same
- Web client works the same
- API endpoints unchanged

### For Administrators
- Excel cache editor tools no longer functional (use progress JSON files instead)
- Content editing now happens before seeding (in progress files)
- Re-seeding required to update content

## Future Considerations

### Content Updates
To update presentation content:
1. Edit progress JSON files
2. Re-run seeding script
3. Content automatically updates in registry

### Content Editing UI
Consider building a web-based content editor that:
- Reads from registry
- Allows inline editing
- Regenerates audio on save
- Updates registry directly
