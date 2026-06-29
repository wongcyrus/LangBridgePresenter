# Multi-Style Presentation System - How To Use

## Overview

The LangBridge system now supports multiple presentation styles for the same content. You can create themed variations (cyberpunk, gundam, hkcomic, star_wars, professional) that transform the same source material into different presentation experiences.

## Available Styles

- **professional**: Standard business presentation style (default)
- **cyberpunk**: Futuristic tech-noir themed language and visuals
- **gundam**: Mecha/anime inspired presentation style
- **hkcomic**: Hong Kong comic book aesthetic and language
- **starwars**: Space opera themed content

## Quick Start

### 1. Prepare Style Content

First, ensure you have style-themed content in the output directory:
```
/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/
├── professional/generate/
├── cyberpunk/generate/
├── gundam/generate/
├── hkcomic/generate/
└── star_wars/generate/
```

Each style directory should contain:
- `*_en_progress.json` - English content with themed language
- `*_zh-CN_progress.json` - Chinese content
- `*_yue-HK_progress.json` - Cantonese content
- `*_visuals/` - Style-appropriate images
- `*.pptm` - PowerPoint files

### 2. Create Multi-Style Course

Create a course that supports multiple styles:

```bash
cd backend/admin_tools
python manage_courses.py update \
  --id "showcase" \
  --title "Showcase" \
  --langs "en-US,zh-CN,yue-HK" \
  --styles "professional,cyberpunk,gundam,hkcomic,starwars"
```

### 3. Seed All Style Variants

Process each style to populate the system:

```bash
cd backend/seeds

# Professional (default)
python seed_course_content.py \
  --course-id "showcase" \
  --course-title "Showcase" \
  --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/professional/generate"

# Cyberpunk
python seed_course_content.py \
  --course-id "showcase-cyberpunk" \
  --course-title "Showcase (Cyberpunk)" \
  --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/cyberpunk/generate"

# Gundam
python seed_course_content.py \
  --course-id "showcase-gundam" \
  --course-title "Showcase (Gundam)" \
  --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/gundam/generate"

# HK Comic
python seed_course_content.py \
  --course-id "showcase-hkcomic" \
  --course-title "Showcase (HK Comic)" \
  --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/hkcomic/generate"

# Star Wars
python seed_course_content.py \
  --course-id "showcase-starwars" \
  --course-title "Showcase (Star Wars)" \
  --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/star_wars/generate"
```

## How It Works

### Synchronized Broadcasting

When you change slides in the main course (`showcase`), the system automatically:

1. **Updates the main course** with your input content
2. **Broadcasts to all style variants** using their themed content
3. **Maintains slide synchronization** across all styles
4. **Preserves style-specific content** (text, audio, visuals)

### Content Sources

- **Main Course**: Uses live input from PowerPoint + enriched with seeded audio/visuals
- **Style Variants**: Uses pre-seeded themed content for that style

### Example Flow

1. You advance to slide 5 in PowerPoint (connected to `showcase`)
2. System updates `showcase` with slide 5 content
3. System also updates:
   - `showcase-cyberpunk` with cyberpunk-themed slide 5 content
   - `showcase-gundam` with gundam-themed slide 5 content
   - `showcase-hkcomic` with HK comic-themed slide 5 content
   - `showcase-starwars` with Star Wars-themed slide 5 content
4. All courses now point to slide 5, but each has its own themed content

## Client Usage

### Web Client

Students can select their preferred style:

1. Navigate to the course selection
2. Choose from available courses:
   - `showcase` (Professional)
   - `showcase-cyberpunk` (Cyberpunk)
   - `showcase-gundam` (Gundam)
   - `showcase-hkcomic` (HK Comic)
   - `showcase-starwars` (Star Wars)
3. Experience the same presentation with themed content

### PowerPoint VBA Client

Configure the VBA client to connect to the main course (`showcase`). The system will automatically handle broadcasting to all style variants.

## Management Commands

### List Available Styles
```bash
python manage_courses.py styles
```

### List All Courses
```bash
python manage_courses.py list
```

### Check Course Configuration
```bash
# View course details in Firestore console or use admin tools
```

## File Structure

### Seeded Content Location

Each style creates separate content in Firestore:

```
presentation_broadcast/
├── showcase/                    # Professional style
│   └── presentations/
│       └── cloudtech/
│           └── slides/
│               ├── 1/
│               ├── 2/
│               └── ...
├── showcase-cyberpunk/          # Cyberpunk style
│   └── presentations/
│       └── cloudtech/
│           └── slides/
│               ├── 1/           # Cyberpunk-themed content
│               ├── 2/
│               └── ...
└── showcase-gundam/             # Gundam style
    └── presentations/
        └── cloudtech/
            └── slides/
                ├── 1/           # Gundam-themed content
                ├── 2/
                └── ...
```

### Cloud Storage Organization

Images and audio are stored separately by course:

```
Cloud Storage Bucket/
├── generated_visuals/
│   ├── showcase/
│   │   └── cloudtech/
│   │       ├── en-US/
│   │       ├── zh-CN/
│   │       └── yue-HK/
│   ├── showcase-cyberpunk/
│   │   └── cloudtech/
│   │       ├── en-US/           # Cyberpunk-themed images
│   │       ├── zh-CN/
│   │       └── yue-HK/
│   └── showcase-gundam/
│       └── cloudtech/
│           ├── en-US/           # Gundam-themed images
│           ├── zh-CN/
│           └── yue-HK/
└── speech_files/
    ├── speech_showcase_*.mp3    # Professional audio
    ├── speech_cyberpunk_*.mp3   # Cyberpunk audio
    └── speech_gundam_*.mp3      # Gundam audio
```

## Troubleshooting

### Style Not Updating

1. **Check seeding**: Ensure all styles have been seeded
   ```bash
   # Check if slide exists in registry
   # Look in Firestore: presentation_broadcast/{course-id}/presentations/{ppt}/slides/{slide}
   ```

2. **Verify course configuration**: Ensure course has `available_styles` field
   ```bash
   python manage_courses.py list
   ```

3. **Check logs**: Look for broadcast messages in Cloud Functions logs

### Missing Content

1. **Re-run seeding** for the problematic style
2. **Check source files** in the output directory
3. **Verify file structure** matches expected format

### Audio/Visual Issues

1. **Check Cloud Storage** for uploaded files
2. **Verify bucket permissions**
3. **Re-run seeding** to regenerate missing assets

## Adding New Styles

### 1. Create Style Content

Add new style directory to output:
```
/path/to/output/new_style/generate/
```

### 2. Update Constants

Add to `backend/admin_tools/constants.py`:
```python
AVAILABLE_STYLES = ["professional", "cyberpunk", "gundam", "hkcomic", "starwars", "new_style"]
```

### 3. Update Course

```bash
python manage_courses.py update \
  --id "showcase" \
  --title "Showcase" \
  --langs "en-US,zh-CN,yue-HK" \
  --styles "professional,cyberpunk,gundam,hkcomic,starwars,new_style"
```

### 4. Seed New Style

```bash
python seed_course_content.py \
  --course-id "showcase-new_style" \
  --course-title "Showcase (New Style)" \
  --data-dir "/path/to/output/new_style/generate"
```

## Best Practices

1. **Consistent Structure**: Ensure all styles have the same slide count and structure
2. **Quality Content**: Review themed content for appropriateness and accuracy
3. **Testing**: Test each style variant before deployment
4. **Backup**: Keep backups of original content before applying styles
5. **Documentation**: Document any custom styles or modifications

## Performance Considerations

- **Storage**: Each style multiplies storage requirements
- **Processing**: Seeding time increases with number of styles
- **Bandwidth**: Clients download style-specific assets
- **Caching**: System caches content per style variant

## Security Notes

- All styles share the same access controls as the main course
- Style-specific content follows the same security model
- No additional authentication required for style variants