# Window Monitor

Cross-platform Python desktop application that captures screen content, performs OCR, and saves images when text changes.

## Features

- Captures desktop screenshots every second
- Performs OCR to extract text content
- Saves images only when text content changes
- Cross-platform compatibility (Windows, macOS, Linux)
- Virtual environment support

## Prerequisites

- Python 3.10+ (works on 3.10–3.14)
- Tesseract OCR engine

### Install Tesseract:

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

## Setup

1. Run the setup script:

	 - Windows PowerShell
		 ```powershell
		 python .\setup.py
		 ```

	 - Linux/macOS
		 ```bash
		 python setup.py
		 ```

2. Activate virtual environment:

	 - Windows PowerShell
		 ```powershell
		 .\venv\Scripts\Activate.ps1
		 ```
		 If you see a scripts execution error, allow scripts for this session and try again:
		 ```powershell
		 Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
		 .\venv\Scripts\Activate.ps1
		 ```

	 - Windows CMD
		 ```bat
		 venv\Scripts\activate.bat
		 ```

	 - Linux/macOS
		 ```bash
		 source venv/bin/activate
		 ```

3. Run the application:

	 - Windows PowerShell
		 ```powershell
		 python .\window_monitor.py
		 ```

	 - Linux/macOS
		 ```bash
		 python window_monitor.py
		 ```

	4. Deactivate the virtual environment (when you’re done):

		 - Any shell
			 ```
			 deactivate
			 ```

### Troubleshooting

- The included setup and requirements install a Pillow release that works with the supported Python versions.
- If installation still fails on Windows, upgrade tools inside the venv and retry setup:
	```powershell
	.\venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
	python .\setup.py
	```
- If activation fails in PowerShell with an error about `source`, use `Activate.ps1` as shown above.
- Ensure Tesseract is installed and on PATH. If not, set the path in code, e.g.:
	```python
	import pytesseract
	pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
	```
	On Windows, the app now defaults to this path automatically; you can still override it on the command line:
	```powershell
	python .\window_monitor.py --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"
	```

- macOS permissions: grant the terminal app Screen Recording and Accessibility permissions in
	System Settings → Privacy & Security, otherwise screenshots/automation may fail.
- Linux Wayland: on Wayland sessions, some screenshot backends are restricted. If captures fail,
	try using an X11 session or a screenshot backend compatible with your environment.
- PyAutoGUI fail-safe: moving the mouse to the top-left corner aborts the program by design. Keep
	the cursor away from (0,0) while monitoring, or disable with `pyautogui.FAILSAFE = False` (not recommended).
- OCR language: for non-English text, install the corresponding Tesseract language pack and call
	`pytesseract.image_to_string(image, lang='chi_sim')` (replace with your language code).

## Usage

- On Windows, the app opens a simple preview window by default; on Linux/macOS it runs in the console unless you pass `--preview`.
- Images are saved when text content changes; the console/GUI shows a short snippet of the detected text.
- Press Ctrl+C to stop monitoring
- Screenshots are named with timestamp: `capture_YYYYMMDD_HHMMSS.png`

### GUI vs console

- Windows (GUI by default):
	```powershell
	python .\window_monitor.py
	```
	Force console mode:
	```powershell
	python .\window_monitor.py --headless
	```

- Linux/macOS (console by default):
	```bash
	python window_monitor.py
	```
	Open GUI preview:
	```bash
	python window_monitor.py --preview
	```

Adjust settings:

```powershell
# Capture every 2 seconds, save to a custom folder, and use Simplified Chinese OCR
python .\window_monitor.py --preview --interval 2 --output .\shots --lang chi_sim
```

### Multi-monitor selection

- In GUI mode, a small dialog lets you choose the monitor at startup. In console mode, you’ll be prompted in the terminal.
- To skip the prompt, pass the monitor index directly (indexing provided by the app):
	```powershell
	python .\window_monitor.py --monitor 2
	```

- In the preview window you can also click "Change Monitor" to switch at runtime; capturing pauses during selection and resumes automatically.

## Code structure and customization

The app is organized into small modules under `client/monitor`:

- `monitor/capture.py` — MSS-based screen capture and multi-monitor selection (with a modal GUI dialog), falls back to PyAutoGUI if MSS is unavailable.
- `monitor/ocr.py` — Tesseract configuration and OCR, including health checks and a status message.
- `monitor/core.py` — Controller that orchestrates capture and OCR, saves screenshots when text changes, and provides the headless loop.
- `monitor/gui.py` — Tkinter preview UI, live image updates, OCR text display, and a "Change Monitor" button.
- `window_monitor.py` — Thin CLI that wires the modules together and parses command-line options.

Customize behavior by editing the module that matches your need:
- Change capture behavior or selection flow: `monitor/capture.py`
- Change OCR language defaults or error handling: `monitor/ocr.py`
- Change save directory, file naming, or change-detection logic: `monitor/core.py`
- Change preview layout or add controls: `monitor/gui.py`

### Command-line flags

- `--preview` Show GUI preview
- `--headless` Force console mode
- `--interval` Capture interval in seconds (default: 1.0)
- `--lang` Tesseract language code (e.g., `eng`, `chi_sim`)
- `--output` Output directory for saved images
- `--monitor` Monitor index to capture (MSS index)
- `--tesseract-cmd` Path to Tesseract executable (defaults to `C:\\Program Files\\Tesseract-OCR\\tesseract.exe` on Windows)
