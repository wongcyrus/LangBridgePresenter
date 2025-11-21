# Python Client: Window Monitor

The Window Monitor is a cross-platform desktop application that captures screen content, performs Optical Character Recognition (OCR), and synchronizes the text with the backend.

## Key Features
- **Real-time Monitoring**: Captures screenshots at a user-defined interval (default: 1s).
- **OCR Integration**: Uses Tesseract OCR to extract text from images.
- **Change Detection**: Only sends updates to the backend when the text content changes.
- **Multi-Monitor Support**: Allows selecting a specific monitor to capture.
- **Preview Mode**: Optional GUI to view what the monitor sees.

## Installation

1. **Prerequisites**:
    - Python 3.8+
    - Tesseract OCR installed on the system.

2. **Setup**:
   ```bash
   cd client/python
   python setup.py
   ```

3. **Activate Virtual Environment**:
   - Windows: `.\venv\Scripts\Activate.ps1`
   - Linux/Mac: `source venv/bin/activate`

## Usage

### Basic Run
```bash
python window_monitor.py
```

### With Preview Window
```bash
python window_monitor.py --preview
```

### Custom Configuration
```bash
python window_monitor.py --interval 2 --lang chi_sim --monitor 1
```

## Configuration Options

| Flag | Description | Default |
|------|-------------|---------|
| `--preview` | Show a GUI window with the captured stream. | False |
| `--headless` | Force console-only mode (no GUI). | False |
| `--interval` | Capture interval in seconds. | 1.0 |
| `--lang` | Tesseract language code (e.g., `eng`, `chi_sim`). | `eng` |
| `--monitor` | Index of the monitor to capture. | 0 |
| `--output` | Directory to save screenshots (optional). | None |

## Architecture

- **`monitor/capture.py`**: Handles screen capturing using `mss` or `pyautogui`.
- **`monitor/ocr.py`**: Wraps `pytesseract` for text extraction.
- **`monitor/core.py`**: Main loop logic, change detection, and backend communication.
- **`monitor/gui.py`**: `tkinter`-based preview window.
