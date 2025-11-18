# VBA Client Configuration

## API Key Configuration

The VBA client supports three methods for configuring the API key (in order of priority):

### Option 1: Config File (Recommended for Development)
Create a file named `api_config.txt` containing only your API key (one line, no extra spaces).

The VBA code will search for this file in the following locations (in order):

1. **Same directory as your PowerPoint presentation** (if the presentation is saved)
2. **`%USERPROFILE%\Documents\XiaoiceClassAssistant\api_config.txt`** (Recommended)
3. **`%APPDATA%\XiaoiceClassAssistant\api_config.txt`**
4. **`%TEMP%\api_config.txt`** (fallback)

**Example file content:**
```
AIzaSyDbT1tVQgd_-bxDc0hxm_xxkllboCiTh-w
```

**Quick Setup:**
1. Open Windows Explorer
2. Navigate to `%USERPROFILE%\Documents`
3. Create a new folder named `XiaoiceClassAssistant`
4. Create a text file named `api_config.txt` in that folder
5. Paste your API key as the only line in the file

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
    "HKCU\Software\XiaoiceClassAssistant\ApiKey", _
    "your-api-key-here", _
    "REG_SZ"
```

Or manually via Registry Editor:
1. Press `Win + R`, type `regedit`
2. Navigate to `HKEY_CURRENT_USER\Software`
3. Create key: `XiaoiceClassAssistant`
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
- Windows Registry: `HKCU\Software\XiaoiceClassAssistant\ApiKey`
- File: `%USERPROFILE%\Documents\XiaoiceClassAssistant\api_config.txt`

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
3. Create folder: `XiaoiceClassAssistant`
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
   - `%USERPROFILE%\Documents\XiaoiceClassAssistant\`
   - Same folder as your PowerPoint file
   - `%APPDATA%\XiaoiceClassAssistant\`

2. **Verify file content** - Open the file and ensure:
   - Contains only the API key (one line)
   - No extra spaces, quotes, or line breaks
   - File is saved as plain text (not .doc or .rtf)

3. **Check registry** - Verify the key exists:
   - Press `Win + R`, type `regedit`
   - Navigate to: `HKCU\Software\XiaoiceClassAssistant`
   - Look for `ApiKey` string value

4. **Enable debug mode** - In PowerPoint:
   - Press `Alt + F11` to open VBA Editor
   - Press `Ctrl + G` to open Immediate Window
   - Look for debug messages showing which location was checked

5. **Re-enter the key** - Delete the registry key and config files, then run the macro again to trigger the prompt
