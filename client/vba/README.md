# VBA Client Configuration

## Prerequisites

Before using the VBA client, ensure you have:

1. **Created a course** in the backend (see [Admin Tools Documentation](../../docs/ADMIN_TOOLS.md)):
   ```bash
   cd backend/admin_tools
   python manage_courses.py update --id "demo" --title "Demo Course" --langs "en-US,zh-CN,yue-HK"
   ```

2. **Generated an API key** for your digital human:
   ```bash
   python create_api_key.py 12345678 "Cyrus"
   ```

3. **Configured your presentation** with the Course ID in the speaker notes (see Course Configuration section below)

## Course Configuration

To associate your presentation with a course (required for multi-language support), add the Course ID as the **third line** in your `api_config.txt` file. The language codes used for configuration (e.g., in `manage_courses.py`) should follow the **BCP-47** standard (e.g., `en-US`, `zh-CN`, `yue-HK`).

### File Format (3 lines):
```
XXXXXXXXXXXXXXXXXXXXXX
https://langbridgeapi-1ynqko7b4cw5d.apigateway.langbridge-presenter.cloud.goog
demo
```

**Line 1**: API Key  
**Line 2**: Base URL  
**Line 3**: Course ID (e.g., `demo`)

This tells the system which course configuration to use, including:
- Supported languages (e.g., English, Mandarin, Cantonese)
- Voice settings for each language
- Cached presentation content

**Note**: If no Course ID is provided (only 2 lines in the file), the system will use default languages (en, zh).

## API Key Configuration

The VBA client supports three methods for configuring the API key (in order of priority):

### Option 1: Config File (Recommended for Development)
Create a file named `api_config.txt` with up to three lines:
1. API Key (required)
2. Base URL (optional - will prompt if not provided)
3. Course ID (optional - defaults to legacy behavior if not provided)

The VBA code will search for this file in the following locations (in order):

1. **Same directory as your PowerPoint presentation** (if the presentation is saved)
2. **`%USERPROFILE%\Documents\LangBridge\api_config.txt`** (Recommended)
3. **`%APPDATA%\LangBridge\api_config.txt`**
4. **`%TEMP%\api_config.txt`** (fallback)

**Example file content:**
```
AIzaSyCTgbvlKqCTbb-ICq_fcTDR7cZsz6l8G2g
https://langbridgeapi-1ynqko7b4cw5d.apigateway.langbridge-presenter.cloud.goog
demo
```

**Quick Setup:**
1. Open Windows Explorer
2. Navigate to `%USERPROFILE%\Documents`
3. Create a new folder named `LangBridge`
4. Create a text file named `api_config.txt` in that folder
5. Add three lines: your API key, the Base URL, and the Course ID

**Pros:**
- Easy to update
- Works immediately without reopening PowerPoint
- Can be different per presentation (if placed in presentation folder)

**Cons:**
- Key visible in plain text
- Requires manual file creation

### Option 2: Windows Registry (Recommended for Production)
Store the API key in the Windows Registry (set once, used everywhere):

```vb
' Run this once to set the key (or use regedit):
CreateObject("WScript.Shell").RegWrite _
    "HKCU\Software\LangBridge\ApiKey", _
    "your-api-key-here", _
    "REG_SZ"
```

Or manually via Registry Editor:
1. Press `Win + R`, type `regedit`
2. Navigate to `HKEY_CURRENT_USER\Software`
3. Create key: `LangBridge`
4. Create String Value: `ApiKey` = `your-api-key-here`

**Pros:**
- Centralized configuration
- No files to distribute
- Works across all presentations

**Cons:**
- Requires one-time setup per user
- Needs registry access

### Option 3: User Prompt (Fallback)
If no key is found, the user will be prompted to enter it. The key will automatically be saved to both:
- Windows Registry: `HKCU\Software\LangBridge\ApiKey`
- File: `%USERPROFILE%\Documents\LangBridge\api_config.txt`

**Pros:**
- Works without pre-configuration
- User-friendly for first-time setup
- Automatically saves for future use

**Cons:**
- Interrupts workflow on first use

## Security Notes

- **Never commit `api_config.txt` with real keys to version control**
- Add `api_config.txt` to `.gitignore`
- For production, use Option 2 (Registry) to avoid exposing keys in files
- Consider implementing key rotation policies
- Use different keys for development vs. production environments

## Setup Instructions

### For Developers:
**Method 1 - Documents Folder (Recommended):**
1. Open Windows Explorer
2. Navigate to `%USERPROFILE%\Documents` (usually `C:\Users\YourName\Documents`)
3. Create folder: `LangBridge`
4. Create text file: `api_config.txt` inside that folder
5. Paste your API key as the only line
6. Save and close

**Method 2 - Presentation Folder:**
1. Save your PowerPoint presentation first
2. Place `api_config.txt` in the same folder as your .pptm file
3. The file should contain only the API key (one line)

### For End Users:
1. Run the macro once - you'll be prompted to enter your API key
2. Enter your key and click OK
3. The key will automatically be saved to:
   - Registry: For persistent storage
   - Documents folder: For easy editing later
4. The key will be remembered for all future presentations

## Troubleshooting

If the macro reports "No API key configured":

1. **Check file locations** - Look for `api_config.txt` in:
   - `%USERPROFILE%\Documents\LangBridge\`
   - Same folder as your PowerPoint file
   - `%APPDATA%\LangBridge\`

2. **Verify file content** - Open the file and ensure:
   - Contains only the API key (one line)
   - No extra spaces, quotes, or line breaks
   - File is saved as plain text (not .doc or .rtf)

3. **Check registry** - Verify the key exists:
   - Press `Win + R`, type `regedit`
   - Navigate to: `HKCU\Software\LangBridge`
   - Look for `ApiKey` string value

4. **Enable debug mode** - In PowerPoint:
   - Press `Alt + F11` to open VBA Editor
   - Press `Ctrl + G` to open Immediate Window
   - Look for debug messages showing which location was checked

5. **Re-enter the key** - Delete the registry key and config files, then run the macro again to trigger the prompt
