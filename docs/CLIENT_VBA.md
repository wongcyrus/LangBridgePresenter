# VBA Client: PowerPoint Integration

The VBA Client integrates directly into Microsoft PowerPoint to provide real-time context updates to the backend based on the presenter's current slide.

## Functionality

- **Slide Detection**: Hooks into the `SlideShowNextSlide` event.
- **Note Extraction**: Extracts text from the "Speaker Notes" section of the current slide.
- **API Communication**: Sends the extracted notes to the `/api/config` endpoint.
- **Caching Strategy**: Uses a content-based hash to identify slides, ensuring resilience against slide reordering or insertion.

## Configuration

### API Key Setup
The client looks for the API key in the following order:

1. **`api_config.txt`** in the presentation's folder.
2. **`%USERPROFILE%\Documents\XiaoiceClassAssistant\api_config.txt`**.
3. **Windows Registry**: `HKCU\Software\XiaoiceClassAssistant\ApiKey`.
4. **User Prompt**: If not found, asks the user and saves to the registry/file.

### Macros
The integration relies on a Class Module (`CAppEvents`) to handle application events.

## Deployment

1. Open the PowerPoint presentation.
2. Press `Alt + F11` to open the VBA Editor.
3. Import `CAppEvents.cls` and `modHttpNotes.bas` from the `client/vba` directory.
4. Initialize the event handler (usually via a ribbon button or auto-start macro).

## Content-Based Caching

To avoid issues where slide numbers change (breaking references), the system uses the *content* of the speaker notes as the key.

- **Logic**: `Hash(Speaker Notes) -> Cache Key`
- **Benefit**: 
    - Moving Slide 1 to position 5 doesn't invalidate the cache.
    - Duplicate slides share the same cache entry.
    - Inserting new slides doesn't affect existing ones.

See `docs/ADMIN_TOOLS.md` for details on preloading this cache.
