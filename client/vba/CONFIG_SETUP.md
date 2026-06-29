# VBA Client Configuration Setup

## Configuration File Format

The VBA client reads configuration from `api_config.txt` with the following format (one value per line):

```
Line 1: API Key (required)
Line 2: Base URL (required, e.g., https://gateway-xxx.ue.gateway.dev)
Line 3: Course ID (required for presenter context feature)
Line 4: Presenter ID (required for presenter context feature)
```

**Note:** Lines 3 and 4 are both required to enable the presenter context feature. If either is missing, the feature will be disabled but basic functionality will still work.

### Example

```
abc123def456ghi789
https://gateway-abc123.ue.gateway.dev
IT523504Q
summer
```

## Configuration File Locations

The VBA client searches for `api_config.txt` in the following locations (in order):

1. **Same directory as the presentation** (not recommended for OneDrive/SharePoint)
2. **User's Documents folder**: `%USERPROFILE%\Documents\LangBridge\api_config.txt` (recommended)
3. **User's AppData folder**: `%APPDATA%\LangBridge\api_config.txt`
4. **Temp folder**: `%TEMP%\api_config.txt` (last resort)

## Registry Fallback

If the config file is not found, the VBA client will also check Windows Registry:

- API Key: `HKCU\Software\LangBridge\ApiKey`
- Base URL: `HKCU\Software\LangBridge\BaseUrl`
- Course ID: `HKCU\Software\LangBridge\CourseId`
- Presenter ID: `HKCU\Software\LangBridge\PresenterId`

## Setup Instructions

### Option 1: Using Config File (Recommended)

1. Create the folder: `%USERPROFILE%\Documents\LangBridge\`
2. Create a file named `api_config.txt` in that folder
3. Add your configuration (4 lines as shown above)
4. Save the file

### Option 2: Using Registry

Run these commands in PowerShell (replace values with your own):

```powershell
New-Item -Path "HKCU:\Software\LangBridge" -Force
Set-ItemProperty -Path "HKCU:\Software\LangBridge" -Name "ApiKey" -Value "your-api-key"
Set-ItemProperty -Path "HKCU:\Software\LangBridge" -Name "BaseUrl" -Value "https://gateway-xxx.ue.gateway.dev"
Set-ItemProperty -Path "HKCU:\Software\LangBridge" -Name "CourseId" -Value "IT523504Q"
Set-ItemProperty -Path "HKCU:\Software\LangBridge" -Name "PresenterId" -Value "summer"
```

## What Each Field Does

- **API Key** (required): Authenticates your requests to the LangBridge backend
- **Base URL** (required): The endpoint where your LangBridge backend is hosted
- **Course ID** (required for presenter context): Links your presentation to a specific course
- **Presenter ID** (required for presenter context): Identifies you as the presenter

## Presenter Context Feature

**IMPORTANT:** Both Course ID and Presenter ID are required for this feature to work.

When both are configured:

1. Each slide change updates the presenter's context in Firestore
2. The context includes all slides from the presentation
3. When students ask questions via talk-stream, the agent has full presentation context
4. The current slide is highlighted for the agent to provide relevant answers

Without both Course ID and Presenter ID:
- Basic slide broadcasting still works
- Students can see slides in real-time
- But the AI agent won't have full presentation context when answering questions
