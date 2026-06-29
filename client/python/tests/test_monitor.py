from datetime import datetime as real_datetime
from types import SimpleNamespace
import sys
import types

import pytest

from PIL import Image

from monitor.capture import ScreenCapture
from monitor.core import MonitorController
from monitor.ocr import OcrEngine


def test_ocr_engine_caches_tesseract_status(monkeypatch):
    pytesseract = pytest.importorskip("pytesseract")

    calls = {"count": 0}

    def fake_version():
        calls["count"] += 1
        return "5.0"

    monkeypatch.setattr(pytesseract, "get_tesseract_version", fake_version)

    engine = OcrEngine()

    assert engine.ensure_tesseract() is True
    assert engine.ensure_tesseract() is True
    assert calls["count"] == 1
    assert engine.status_message == "Tesseract OK"


def test_ocr_engine_image_to_text_handles_runtime_error(monkeypatch):
    pytesseract = pytest.importorskip("pytesseract")

    monkeypatch.setattr(pytesseract, "get_tesseract_version", lambda: "5.0")
    monkeypatch.setattr(
        pytesseract, "image_to_string", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    engine = OcrEngine(lang="eng")

    assert engine.image_to_text(Image.new("RGB", (1, 1), "white")) == ""


def test_ocr_engine_reports_missing_tesseract(monkeypatch):
    pytesseract = pytest.importorskip("pytesseract")

    monkeypatch.setattr(
        pytesseract,
        "get_tesseract_version",
        lambda: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )

    engine = OcrEngine()

    assert engine.ensure_tesseract() is False
    assert "not found" in engine.status_message.lower()


def test_screen_capture_uses_fallback_when_mss_is_unavailable(monkeypatch):
    sentinel = Image.new("RGB", (1, 1), "red")
    capture = ScreenCapture(screenshot_fn=lambda: sentinel)
    capture.monitor_rect = {"left": 0, "top": 0, "width": 1, "height": 1}
    monkeypatch.setattr(capture, "refresh_mss", lambda: setattr(capture, "sct", None))

    assert capture.capture() is sentinel


def test_monitor_controller_process_once_tracks_changes(tmp_path, monkeypatch):
    screenshot = Image.new("RGB", (3, 3), "blue")

    class FakeCapture:
        def __init__(self):
            self.calls = 0

        def capture(self):
            self.calls += 1
            return screenshot

    class FakeOcr:
        def __init__(self):
            self.calls = 0

        def image_to_text(self, _image):
            self.calls += 1
            return "hello"

        def ensure_tesseract(self):
            return True

    fake_now = SimpleNamespace(
        now=lambda: real_datetime(2026, 1, 2, 3, 4, 5)
    )
    monkeypatch.setattr("monitor.core.datetime", fake_now)

    controller = MonitorController(
        output_dir=str(tmp_path),
        interval=0.1,
        capture=FakeCapture(),
        ocr=FakeOcr(),
        detect_mode="both",
    )

    _, text, changed = controller.process_once()
    assert changed is True
    assert text == "hello"
    assert controller.last_saved_path is not None
    assert controller.last_saved_path.endswith("capture_20260102_030405.png")
    assert (tmp_path / "capture_20260102_030405.png").exists()

    _, _, changed_again = controller.process_once()
    assert changed_again is False


def test_run_preview_drives_gui_update_loop(monkeypatch):
    from monitor import gui as gui_module
    button_commands = []

    class FakeWidget:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs
            if "command" in kwargs:
                button_commands.append(kwargs["command"])

        def pack(self, *args, **kwargs):
            return None

        def configure(self, *args, **kwargs):
            return None

    class FakeStringVar:
        def __init__(self, value=""):
            self.value = value

        def set(self, value):
            self.value = value

        def get(self):
            return self.value

    class FakeRoot:
        def __init__(self):
            self.after_calls = 0

        def title(self, *_args, **_kwargs):
            return None

        def protocol(self, *_args, **_kwargs):
            return None

        def destroy(self):
            return None

        def winfo_exists(self):
            return True

        def after(self, *_args, **_kwargs):
            self.after_calls += 1

        def mainloop(self):
            if button_commands:
                button_commands[0]()
            return None

    fake_tk = types.SimpleNamespace(
        Tk=FakeRoot,
        Frame=lambda *args, **kwargs: FakeWidget(*args, **kwargs),
        Button=lambda *args, **kwargs: FakeWidget(*args, **kwargs),
        Label=lambda *args, **kwargs: FakeWidget(*args, **kwargs),
        StringVar=FakeStringVar,
        TclError=RuntimeError,
    )
    fake_imagetk = types.SimpleNamespace(
        PhotoImage=lambda *args, **kwargs: object()
    )
    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "PIL.ImageTk", fake_imagetk)

    class FakeCapture:
        def __init__(self):
            self.refresh_calls = 0
            self.ensure_calls = 0

        def ensure_monitor_selected(self, gui=False, parent=None):
            self.ensure_calls += 1
            return None

        def refresh_mss(self):
            self.refresh_calls += 1

    class FakeOcr:
        status_message = "Tesseract OK"

    class FakeController:
        def __init__(self):
            self.capture = FakeCapture()
            self.ocr = FakeOcr()
            self.interval = 0.1
            self.last_text_hash = None
            self.last_saved_path = None
            self.calls = 0

        def process_once(self):
            self.calls += 1
            return Image.new("RGB", (10, 10), "green"), "hello", True

    controller = FakeController()

    gui_module.run_preview(controller)

    assert controller.calls == 1
    assert controller.capture.refresh_calls == 1
    assert controller.capture.ensure_calls >= 2


def test_screen_capture_lists_monitors_and_captures_from_mss(monkeypatch):
    frame = b"\x10" * (2 * 2 * 3)

    class FakeShot:
        width = 2
        height = 2
        rgb = frame

    class FakeMss:
        monitors = [
            {"left": 0, "top": 0, "width": 10, "height": 10},
            {"left": 1, "top": 2, "width": 3, "height": 4},
        ]

        def grab(self, mon):
            return FakeShot()

    monkeypatch.setitem(
        sys.modules,
        "mss",
        types.SimpleNamespace(mss=lambda: FakeMss()),
    )

    capture = ScreenCapture(monitor_index=1)
    assert capture.list_monitors() == [
        {"index": 1, "left": 1, "top": 2, "width": 3, "height": 4}
    ]
    capture.ensure_monitor_selected(gui=False)
    image = capture.capture()

    assert image.size == (2, 2)


def test_screen_capture_defaults_to_second_monitor_when_input_is_invalid(monkeypatch):
    class FakeMss:
        monitors = [
            {"left": 0, "top": 0, "width": 10, "height": 10},
            {"left": 1, "top": 2, "width": 3, "height": 4},
        ]

        def grab(self, _mon):
            raise AssertionError("not expected")

    capture = ScreenCapture(mss_factory=lambda: FakeMss(), screenshot_fn=lambda: Image.new("RGB", (1, 1), "white"))
    monkeypatch.setattr("builtins.input", lambda _prompt: "99")

    capture.ensure_monitor_selected(gui=False)

    assert capture.monitor_rect == FakeMss.monitors[1]


def test_screen_capture_supports_injected_backends():
    class FakeShot:
        width = 1
        height = 1
        rgb = b"\x00\x00\x00"

    class FakeMss:
        monitors = [{"left": 0, "top": 0, "width": 1, "height": 1}]

        def grab(self, _mon):
            return FakeShot()

    sentinel = Image.new("RGB", (1, 1), "white")
    capture = ScreenCapture(
        mss_factory=lambda: FakeMss(),
        screenshot_fn=lambda: sentinel,
    )

    assert capture.capture().size == (1, 1)


def test_screen_capture_falls_back_when_mss_capture_fails(monkeypatch):
    class BrokenMss:
        monitors = [{"left": 0, "top": 0, "width": 10, "height": 10}]

        def grab(self, _mon):
            raise RuntimeError("boom")

    monkeypatch.setitem(
        sys.modules,
        "mss",
        types.SimpleNamespace(mss=lambda: BrokenMss()),
    )

    sentinel = Image.new("RGB", (1, 1), "red")
    capture = ScreenCapture(screenshot_fn=lambda: sentinel)
    monkeypatch.setattr(capture, "refresh_mss", lambda: setattr(capture, "sct", None))

    assert capture.capture() is sentinel
