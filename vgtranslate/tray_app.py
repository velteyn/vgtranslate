"""Minimal tray GUI (pystray + Tkinter) for Windows and Linux.

The app lives in the system tray with no main window (hide-to-tray). Menu items
start/stop the server, show the log window, and open the settings window.
All Tk access is marshalled to the main thread via ``root.after`` because pystray
callbacks run on their own thread.
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from .config import Config, save_config
from .server import Server

log = logging.getLogger("vgtranslate.tray")


class _QueueHandler(logging.Handler):
    def __init__(self, sink: "queue.Queue[str]") -> None:
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.sink.put_nowait(self.format(record))
        except queue.Full:
            pass


class TrayApp:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.server = Server(config)
        self.icon = None
        self.log_queue: "queue.Queue[str]" = queue.Queue(maxsize=2000)
        self._log_text: Optional[tk.Text] = None
        self._settings_win: Optional[tk.Toplevel] = None

    # -- icon lifecycle ------------------------------------------------------

    def run(self) -> None:
        import pystray  # deferred so plain server usage doesn't need it

        from PIL import Image

        root = tk.Tk()
        root.withdraw()
        root.title("vgtranslate")

        image = Image.new("RGBA", (64, 64), (30, 120, 200, 255))
        menu = pystray.Menu(
            pystray.MenuItem("Start server", self._toggle_server, enabled=lambda item: not self.server.running),
            pystray.MenuItem("Stop server", self._toggle_server, enabled=lambda item: self.server.running),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show logs", self._open_logs),
            pystray.MenuItem("Settings", self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )
        self.icon = pystray.Icon("vgtranslate", image, "vgtranslate", menu)

        handler = _QueueHandler(self.log_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

        icon_thread = threading.Thread(target=self.icon.run, name="vgtranslate-tray", daemon=True)
        icon_thread.start()
        root.after(250, self._poll_logs)
        root.mainloop()

    # -- actions (called from icon thread; marshal Tk to main thread) --------

    def _toggle_server(self, _icon=None, _item=None) -> None:
        if self.server.running:
            self.server.stop()
        else:
            try:
                self.server.start()
            except Exception as exc:  # noqa: BLE001
                log.error("failed to start server: %s", exc)

    def _open_logs(self, _icon=None, _item=None) -> None:
        self._ui(self._create_logs_window)

    def _open_settings(self, _icon=None, _item=None) -> None:
        self._ui(self._create_settings_window)

    def _quit(self, _icon=None, _item=None) -> None:
        self.server.stop()
        if self.icon:
            self.icon.stop()
        self._ui(lambda: self._quit_tk())

    def _quit_tk(self) -> None:
        root = tk._default_root  # noqa: SLF001
        if root is not None:
            root.destroy()

    # -- helpers -------------------------------------------------------------

    def _ui(self, fn) -> None:
        root = tk._default_root  # noqa: SLF001
        if root is not None:
            try:
                root.after(0, fn)
                return
            except RuntimeError:
                pass
        threading.Thread(target=fn, daemon=True).start()

    def _poll_logs(self) -> None:
        try:
            while True:
                line = self.log_queue.get_nowait()
                if self._log_text is not None:
                    self._log_text.insert("end", line + "\n")
                    self._log_text.see("end")
                else:
                    log.debug("dropped log line while no window open")
        except queue.Empty:
            pass
        root = tk._default_root  # noqa: SLF001
        if root is not None:
            try:
                root.after(250, self._poll_logs)
            except RuntimeError:
                pass

    def _create_logs_window(self) -> None:
        root = tk._default_root  # noqa: SLF001
        if root is None:
            return
        win = tk.Toplevel(root)
        win.title("vgtranslate logs")
        win.geometry("640x400")
        text = tk.Text(win, state="normal")
        text.pack(fill="both", expand=True)
        self._log_text = text
        win.protocol("WM_DELETE_WINDOW", lambda: self._close_logs(win))

    def _close_logs(self, win: tk.Toplevel) -> None:
        self._log_text = None
        win.destroy()

    def _create_settings_window(self) -> None:
        root = tk._default_root  # noqa: SLF001
        if root is None or (self._settings_win and self._settings_win.winfo_exists()):
            return
        win = tk.Toplevel(root)
        self._settings_win = win
        win.title("vgtranslate settings")
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        base_url = tk.StringVar(value=self.config.llm.base_url)
        model = tk.StringVar(value=self.config.llm.model)
        profile_var = tk.StringVar(value=self.config.active_profile)

        ttk.Label(frame, text="LLM base URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=base_url, width=40).grid(row=0, column=1, padx=4, pady=2)
        ttk.Label(frame, text="LLM model").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=model, width=40).grid(row=1, column=1, padx=4, pady=2)

        ttk.Label(frame, text="Profile").grid(row=2, column=0, sticky="w")
        profile_box = ttk.Combobox(
            frame,
            textvariable=profile_var,
            values=list(self.config.profiles),
            state="readonly",
            width=38,
        )
        profile_box.grid(row=2, column=1, padx=4, pady=2)

        ttk.Label(frame, text="Glossary (source => target, one per line)").grid(
            row=3, column=0, columnspan=2, sticky="w"
        )
        glossary = tk.Text(frame, width=50, height=10)
        glossary.grid(row=4, column=0, columnspan=2, pady=2)
        glossary.insert("1.0", self._glossary_text())

        def save():
            glossary_name = self.config.active().glossary
            self.config.glossaries.setdefault(glossary_name, {})
            parsed = self._parse_glossary(glossary.get("1.0", "end"))
            self.config.glossaries[glossary_name] = parsed
            self.config.llm.base_url = base_url.get().strip()
            self.config.llm.model = model.get().strip()
            self.config.active_profile = profile_var.get()
            try:
                save_config(self.config)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("vgtranslate", f"failed to save config: {exc}")
                return
            self._reload_pipeline()
            log.info("settings saved (profile=%s)", self.config.active_profile)
            win.destroy()

        ttk.Button(frame, text="Save", command=save).grid(row=5, column=0, columnspan=2, pady=8)
        win.protocol("WM_DELETE_WINDOW", lambda: self._close_settings(win))

    def _close_settings(self, win: tk.Toplevel) -> None:
        self._settings_win = None
        win.destroy()

    def _glossary_text(self) -> str:
        entries = self.config.glossaries.get(self.config.active().glossary, {})
        return "\n".join(f"{k} => {v}" for k, v in entries.items())

    @staticmethod
    def _parse_glossary(text: str) -> dict[str, str]:
        parsed: dict[str, str] = {}
        for raw in text.splitlines():
            line = raw.strip()
            if not line or "=>" not in line:
                continue
            source, target = line.split("=>", 1)
            source = source.strip()
            if source:
                parsed[source] = target.strip()
        return parsed

    def _reload_pipeline(self) -> None:
        if self.server is not None:
            from .pipeline import Pipeline

            self.server.app.state.pipeline = Pipeline(self.config)
