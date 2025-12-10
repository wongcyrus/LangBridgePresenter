# Multi-Style Presentation Support Plan

## Simple Integration Approach

The output directory `/home/developer/Documents/data-disk/gemini-powerpoint-sage/output` contains style variations:
- `professional/`, `cyberpunk/`, `gundam/`, `hkcomic/`, `star_wars/`
- Each has the same structure as current `backend/seeds/generate/`
- Just different themed content in the `note` fields

## Simple Solution

### Step 1: Add Style Parameter to Seeding Script

Just add a `--style` parameter to `seed_course_content.py`:

```bash
# Current usage
python seed_course_content.py --data-dir "generate"

# New usage with styles
python seed_course_content.py --data-dir "/path/to/output/professional/generate"
python seed_course_content.py --data-dir "/path/to/output/cyberpunk/generate" --course-id "showcase-cyberpunk"
```

### Step 2: Course ID Convention

Use course ID to indicate style:
- `showcase` = professional style (default)
- `showcase-cyberpunk` = cyberpunk style  
- `showcase-gundam` = gundam style
- etc.

### Step 3: Batch Processing Script

Create simple batch script `seed_all_styles.sh`:

```bash
#!/bin/bash
OUTPUT_DIR="/home/developer/Documents/data-disk/gemini-powerpoint-sage/output"

for style in professional cyberpunk gundam hkcomic star_wars; do
    echo "Processing $style style..."
    python seed_course_content.py \
        --course-id "showcase-$style" \
        --course-title "Showcase ($style)" \
        --data-dir "$OUTPUT_DIR/$style/generate"
done
```

### Step 4: Client Style Selection

Add simple course selector to clients:

**VBA Client**: Add dropdown to select course (showcase, showcase-cyberpunk, etc.)
**Web Client**: Add course/style selector in UI

No API changes needed - just use different course IDs.

## Implementation

**Week 1**: 
- Add `--style` parameter to seeding script
- Create batch processing script
- Test with one style variant

**Week 2**:
- Process all 5 styles 
- Add course selector to clients
- Done

## That's it

The existing system already handles everything. We just:
1. Run the seeding script 5 times with different data directories
2. Create 5 different courses (showcase, showcase-cyberpunk, etc.)  
3. Let users pick which course/style they want

No complex data structure changes, no new APIs, no complicated merging logic. Just use the existing course system with style-specific course IDs.


# Professional style (default)
python seed_course_content.py --course-id "showcase" --course-title "Showcase" --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/professional/generate"

# Cyberpunk style
python seed_course_content.py --course-id "showcase-cyberpunk" --course-title "Showcase (Cyberpunk)" --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/cyberpunk/generate"

# Gundam style
python seed_course_content.py --course-id "showcase-gundam" --course-title "Showcase (Gundam)" --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/gundam/generate"

# Hong Kong Comic style
python seed_course_content.py --course-id "showcase-hkcomic" --course-title "Showcase (HK Comic)" --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/hkcomic/generate"

# Star Wars style
python seed_course_content.py --course-id "showcase-starwars" --course-title "Showcase (Star Wars)" --data-dir "/home/developer/Documents/data-disk/gemini-powerpoint-sage/output/starwars/generate"
