import importlib
from typing import Callable
from typing import Optional, Dict, List

from PIL import Image


class ScreenCapture:
    @staticmethod
    def _fallback_screenshot() -> Image.Image:
        try:
            import pyautogui
        except Exception as exc:
            raise RuntimeError(
                "pyautogui screenshot fallback is unavailable in this environment"
            ) from exc
        return pyautogui.screenshot()

    def __init__(
        self,
        monitor_index: Optional[int] = None,
        mss_factory: Callable[[], object] | None = None,
        screenshot_fn: Callable[[], Image.Image] | None = None,
    ):
        self.monitor_index = monitor_index
        self.monitor_rect: Optional[Dict[str, int]] = None
        self._mss_factory = mss_factory
        self._screenshot_fn = screenshot_fn or self._fallback_screenshot
        try:
            self.sct = self._create_mss()
        except ModuleNotFoundError:
            self.sct = None

    def _create_mss(self):
        if self._mss_factory is not None:
            return self._mss_factory()
        _mss = importlib.import_module("mss")
        return _mss.mss()

    def refresh_mss(self):
        try:
            self.sct = self._create_mss()
        except ModuleNotFoundError:
            self.sct = None

    def list_monitors(self) -> List[Dict[str, int]]:
        if not self.sct:
            return []
        mons: List[Dict[str, int]] = []
        for idx, m in enumerate(self.sct.monitors):
            if idx == 0:
                continue
            mons.append(
                {
                    "index": idx,
                    "left": m["left"],
                    "top": m["top"],
                    "width": m["width"],
                    "height": m["height"],
                }
            )
        return mons

    def ensure_monitor_selected(self, gui: bool = False, parent=None):
        if self.monitor_rect:
            return
        mons = self.list_monitors()
        if not mons:
            if self.sct:
                self.monitor_rect = self.sct.monitors[0]
            return
        if (
            self.sct
            and self.monitor_index
            and 1 <= int(self.monitor_index) <= len(self.sct.monitors) - 1
        ):
            self.monitor_rect = self.sct.monitors[int(self.monitor_index)]
            return
        if gui and parent is not None:
            try:
                import tkinter as tk  # noqa: F401
                from tkinter import ttk
            except ImportError:
                self.monitor_rect = self.sct.monitors[1]
                return

            sel = {"value": mons[0]["index"]}
            dialog = tk.Toplevel(parent)
            dialog.title("Select Monitor")
            dialog.transient(parent)
            dialog.grab_set()
            tk.Label(dialog, text="Select monitor to capture:").pack(
                padx=10, pady=(10, 4)
            )
            values = [
                f"#{m['index']} - {m['width']}x{m['height']} @ "
                f"({m['left']},{m['top']})"
                for m in mons
            ]
            combo = ttk.Combobox(dialog, values=values, state="readonly")
            combo.current(0)
            combo.pack(padx=10, pady=4)

            def on_change(_event=None):
                i = combo.current()
                sel["value"] = mons[i]["index"]

            combo.bind("<<ComboboxSelected>>", on_change)

            def on_ok():
                dialog.destroy()

            tk.Button(dialog, text="OK", command=on_ok).pack(
                padx=10, pady=(6, 10)
            )
            parent.wait_window(dialog)
            idx = sel["value"]
            self.monitor_rect = self.sct.monitors[int(idx)]
        elif not gui:
            print("Available monitors:")
            for m in mons:
                info = (
                    f"  {m['index']}: {m['width']}x{m['height']} at "
                    f"({m['left']},{m['top']})"
                )
                print(info)
            try:
                choice = input("Select monitor index: ").strip()
                idx = int(choice)
                if 1 <= idx <= len(self.sct.monitors) - 1:
                    self.monitor_rect = self.sct.monitors[idx]
                else:
                    self.monitor_rect = self.sct.monitors[1]
            except (ValueError, EOFError, KeyboardInterrupt):
                self.monitor_rect = self.sct.monitors[1]

    def capture(self) -> Image.Image:
        if not self.monitor_rect:
            self.ensure_monitor_selected(gui=False)
        if not self.sct:
            self.refresh_mss()
            if not self.sct:
                return self._screenshot_fn()
        mon = self.monitor_rect or self.sct.monitors[0]
        try:
            shot = self.sct.grab(mon)
            img = Image.frombytes("RGB", (shot.width, shot.height), shot.rgb)
            return img
        except Exception:
            self.refresh_mss()
            self.monitor_rect = None
            self.ensure_monitor_selected(gui=False)
            try:
                mon2 = self.monitor_rect or (
                    self.sct.monitors[0] if self.sct else None
                )
                if self.sct and mon2 is not None:
                    shot = self.sct.grab(mon2)
                    img = Image.frombytes(
                        "RGB", (shot.width, shot.height), shot.rgb
                    )
                    return img
            except Exception:
                pass
            return self._screenshot_fn()
