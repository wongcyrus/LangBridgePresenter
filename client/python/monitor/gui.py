import importlib
import os
from typing import Dict


def run_preview(controller, tk_module=None, image_tk_module=None):
    try:
        tk = tk_module or importlib.import_module("tkinter")
        ImageTk = image_tk_module or importlib.import_module("PIL.ImageTk")
    except ImportError as e:
        print("Preview mode requires Tkinter support (ImageTk).", e)
        print("Falling back to headless mode.")
        return controller.run_headless()

    root = tk.Tk()
    root.title("Window Monitor Preview")

    running: Dict[str, bool] = {"val": True, "selecting": False}

    controls = tk.Frame(root)
    controls.pack(padx=10, pady=(10, 0), fill="x")

    def on_change_monitor_btn():
        running["selecting"] = True
        try:
            # Refresh display topology and force re-selection
            controller.capture.monitor_rect = None
            controller.capture.refresh_mss()
            controller.capture.ensure_monitor_selected(gui=True, parent=root)
            # Reset hash so the next change triggers a save immediately
            controller.last_text_hash = None
        finally:
            running["selecting"] = False

    tk.Button(
        controls,
        text="Change Monitor",
        command=on_change_monitor_btn,
    ).pack(side="left")

    img_label = tk.Label(root)
    img_label.pack(padx=10, pady=10)

    text_var = tk.StringVar(value="hash: <none>\nlast: <none>")
    tk.Label(root, textvariable=text_var, wraplength=800, justify="left").pack(
        padx=10, pady=(0, 10)
    )

    status_var = tk.StringVar(value=controller.ocr.status_message or "")
    tk.Label(root, textvariable=status_var, fg="gray").pack(
        padx=10, pady=(0, 10)
    )

    photo_ref: Dict[str, object] = {"img": None}

    def on_close():
        running["val"] = False
        try:
            root.destroy()
        except tk.TclError:
            pass

    root.protocol("WM_DELETE_WINDOW", on_close)

    controller.capture.ensure_monitor_selected(gui=True, parent=root)

    def update_loop():
        try:
            if (
                not running["val"]
                or running.get("selecting")
                or not root.winfo_exists()
            ):
                return
            screenshot, _text, _changed = controller.process_once()
            disp = screenshot.resize(
                (int(screenshot.width * 0.5), int(screenshot.height * 0.5))
            )
            photo = ImageTk.PhotoImage(disp, master=root)
            photo_ref["img"] = photo
            try:
                img_label.configure(image=photo)
            except tk.TclError:
                return
            # GUI: show only hash and last saved filename
            last_hash = controller.last_text_hash or "<none>"
            last_name = (
                os.path.basename(controller.last_saved_path)
                if controller.last_saved_path
                else "<none>"
            )
            text_var.set(f"hash: {last_hash}\nlast: {last_name}")
            status_var.set(controller.ocr.status_message)
        except (RuntimeError, OSError, ValueError) as e:
            text_var.set(f"Error: {e}")
        finally:
            if running["val"] and root.winfo_exists():
                root.after(int(controller.interval * 1000), update_loop)

    update_loop()
    print("Preview window open. Close it to stop.")
    root.mainloop()
