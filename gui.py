# -*- coding: utf-8 -*-
"""
Basit Türkçe yt-dlp arayüzü.

Bu uygulama taşınabilir (portable) kullanım amacıyla geliştirilmiştir.

@thefinega projesinden forklanmıştır.
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional, Sequence


# yt-dlp-core paketini kullan
CORE_DIR = Path(__file__).resolve().parent.parent / "yt-dlp-core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))


# Windows konsol/log akışını UTF-8'e zorlar ve bilinmeyen karakterlerde
# çökmesini engeller.
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )

    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace",
        )
except Exception:
    pass


from toolbox.parser import (
    ProgressEvent,
    PlaylistEvent,
    FileDoneEvent,
    WarningEvent,
    ErrorEvent,
)
from toolbox.profiles import RESOLUTIONS, get_profile
from toolbox.runner import YtDlpRunner
from toolbox.tools import Tools


APP_NAME = "Video / Ses / Playlist İndirici"
APP_VERSION = "1.0"

PROFILE_OPTIONS = {
    "Video": "video",
    "Ses": "audio",
    "Playlist": "playlist",
}

COOKIE_MODES = {
    "Çerez yok": "none",
    "Firefox": "browser",
    "Çerez dosyası": "file",
}

COOKIE_EXPORTER_URL = (
    "https://chromewebstore.google.com/detail/"
    "cookie-exporter/fhnmmidekmgocpjdceeffppcodigillk"
)


class DownloadWorker(threading.Thread):
    def __init__(
        self,
        *,
        tools: Tools,
        url: str,
        profile_name: str,
        output_dir: Optional[Path],
        cookie_mode: str,
        cookie_value: Optional[str],
        max_resolution: Optional[str] = None,
        event_queue: queue.Queue[tuple[str, Any]],
    ):
        super().__init__(daemon=True)

        self.tools = tools
        self.url = url
        self.profile_name = profile_name
        self.output_dir = output_dir
        self.cookie_mode = cookie_mode
        self.cookie_value = cookie_value
        self.max_resolution = max_resolution
        self.event_queue = event_queue

        self.runner: Optional[YtDlpRunner] = None

    def cancel(self) -> None:
        runner = self.runner

        if runner is None:
            return

        try:
            runner.stop()
        except Exception:
            pass

    def emit(self, event_type: str, payload: Any) -> None:
        self.event_queue.put((event_type, payload))

    def run(self) -> None:
        try:
            if self.output_dir:
                try:
                    self.output_dir.mkdir(
                        parents=True,
                        exist_ok=True,
                    )
                except OSError as exc:
                    self.emit(
                        "error",
                        f"İndirme klasörü oluşturulamadı: {exc}",
                    )
                    return

            profile = get_profile(self.profile_name)

            self.runner = YtDlpRunner(
                tools=self.tools,
                profile=profile,
                url=self.url,
                output_dir=(
                    str(self.output_dir)
                    if self.output_dir
                    else None
                ),
                cookie_mode=self.cookie_mode,
                cookie_value=self.cookie_value,
                max_resolution=self.max_resolution,
            )

            self.emit(
                "log",
                f"İndirme klasörü: "
                f"{self.output_dir or 'Varsayılan'}",
            )

            if self.cookie_mode == "browser":
                self.emit(
                    "log",
                    "Firefox çerezleri kullanılacak.",
                )

            elif self.cookie_mode == "file":
                self.emit(
                    "log",
                    f"Çerez dosyası kullanılacak: "
                    f"{self.cookie_value}",
                )

            self.emit(
                "log",
                "İndirme başlatılıyor...",
            )

            try:
                self.runner.start()

            except Exception as exc:
                self.emit(
                    "error",
                    f"yt-dlp başlatılamadı: {exc}",
                )
                return

            try:
                for event in self.runner.events():
                    self.emit("event", event)

            except Exception as exc:
                self.emit(
                    "error",
                    f"Olaylar okunurken hata oluştu: {exc}",
                )
                return

            return_code = self.runner.wait()

            # stop() çağrıldıysa return code'a bakmadan
            # kullanıcı tarafından durdurulmuş kabul edilir.
            if self.runner.is_stopped:
                self.emit(
                    "warning",
                    "İndirme kullanıcı tarafından durduruldu.",
                )
                return

            if return_code == 0:
                if self.profile_name == "playlist":
                    self.emit(
                        "success",
                        "Tüm playlist başarıyla indirildi "
                        "ve raporlandı.",
                    )
                else:
                    self.emit(
                        "success",
                        "İndirme başarıyla tamamlandı "
                        "ve raporlandı.",
                    )
                return

            self.emit(
                "error",
                "İndirme tamamlandı ancak bazı videolar "
                "indirilemedi. "
                f"yt-dlp çıkış kodu: {return_code}",
            )

        finally:
            self.emit("done", None)


class VideoDownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("840x660")
        self.root.minsize(760, 600)

        self.tools = Tools.discover()
        self.event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: Optional[DownloadWorker] = None
        self.current_playlist_counter = ""

        self.url_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()

        self.cookie_mode_var = tk.StringVar(
            value="Çerez yok",
        )
        self.cookie_file_var = tk.StringVar()

        self.status_var = tk.StringVar(value="Hazır.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(
            value="Henüz indirme yok."
        )

        self._build_ui()
        self.root.after(100, self._process_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _add_entry_context_menu(
        self,
        entry: ttk.Entry,
    ) -> None:
        menu = tk.Menu(entry, tearoff=0)

        menu.add_command(
            label="Kes",
            command=lambda: entry.event_generate("<<Cut>>"),
        )
        menu.add_command(
            label="Kopyala",
            command=lambda: entry.event_generate("<<Copy>>"),
        )
        menu.add_command(
            label="Yapıştır",
            command=lambda: entry.event_generate("<<Paste>>"),
        )
        menu.add_separator()
        menu.add_command(
            label="Tümünü Seç",
            command=lambda: entry.select_range(0, tk.END),
        )

        def show_menu(event: tk.Event[Any]) -> None:
            entry.focus_set()
            entry.icursor(entry.index(f"@{event.x}"))

            try:
                menu.tk_popup(
                    event.x_root,
                    event.y_root,
                )
            finally:
                menu.grab_release()

        entry.bind("<Button-3>", show_menu)

    def _build_ui(self) -> None:
        style = ttk.Style()

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 16, "bold"),
        )
        style.configure(
            "Hint.TLabel",
            foreground="#555555",
        )
        style.configure(
            "Status.TLabel",
            foreground="#333333",
        )

        main = ttk.Frame(
            self.root,
            padding=16,
        )
        main.pack(
            fill=tk.BOTH,
            expand=True,
        )

        title = ttk.Label(
            main,
            text=APP_NAME,
            style="Title.TLabel",
        )
        title.pack(anchor=tk.W)

        source_frame = ttk.LabelFrame(
            main,
            text="Video / Ses / Playlist Linki",
        )
        source_frame.pack(
            fill=tk.X,
            pady=(12, 8),
        )
        source_frame.columnconfigure(
            0,
            weight=1,
        )

        self.url_entry = ttk.Entry(
            source_frame,
            textvariable=self.url_var,
        )
        self.url_entry.grid(
            row=0,
            column=0,
            sticky=tk.EW,
            padx=10,
            pady=10,
        )
        self.url_entry.focus_set()
        self._add_entry_context_menu(
            self.url_entry,
        )

        options_frame = ttk.LabelFrame(
            main,
            text="Ayarlar",
        )
        options_frame.pack(
            fill=tk.X,
            pady=8,
        )
        options_frame.columnconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            options_frame,
            text="Profil:",
        ).grid(
            row=0,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=8,
        )

        profile_row = ttk.Frame(options_frame)
        profile_row.grid(
            row=0,
            column=1,
            sticky=tk.W,
            padx=10,
            pady=8,
        )

        self.profile_var = tk.StringVar(
            value="Video",
        )

        profile_combo = ttk.Combobox(
            profile_row,
            textvariable=self.profile_var,
            values=list(PROFILE_OPTIONS.keys()),
            state="readonly",
            width=12,
        )
        profile_combo.pack(side=tk.LEFT)

        self.res_lbl = ttk.Label(
            profile_row,
            text="Çözünürlük:",
        )

        self.res_var = tk.StringVar(
            value="En İyi",
        )

        self.res_combo = ttk.Combobox(
            profile_row,
            textvariable=self.res_var,
            values=RESOLUTIONS,
            state="readonly",
            width=14,
        )

        def _on_profile_change(
            event: Optional[tk.Event[Any]] = None,
        ) -> None:
            if PROFILE_OPTIONS.get(
                self.profile_var.get()
            ) == "video":
                self.res_lbl.pack(
                    side=tk.LEFT,
                    padx=(16, 6),
                )
                self.res_combo.pack(
                    side=tk.LEFT,
                )
            else:
                self.res_lbl.pack_forget()
                self.res_combo.pack_forget()

        profile_combo.bind(
            "<<ComboboxSelected>>",
            _on_profile_change,
        )

        _on_profile_change()

        ttk.Label(
            options_frame,
            text="Klasör:",
        ).grid(
            row=1,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=8,
        )

        folder_row = ttk.Frame(options_frame)
        folder_row.grid(
            row=1,
            column=1,
            sticky=tk.EW,
            padx=10,
            pady=8,
        )
        folder_row.columnconfigure(
            0,
            weight=1,
        )

        self.output_dir_entry = ttk.Entry(
            folder_row,
            textvariable=self.output_dir_var,
        )
        self.output_dir_entry.grid(
            row=0,
            column=0,
            sticky=tk.EW,
        )

        self._add_entry_context_menu(
            self.output_dir_entry,
        )

        ttk.Button(
            folder_row,
            text="Seç",
            command=self.choose_output_dir,
            width=8,
        ).grid(
            row=0,
            column=1,
            padx=(8, 0),
        )

        ttk.Label(
            options_frame,
            text="Çerez:",
        ).grid(
            row=2,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=(4, 8),
        )

        cookie_frame = ttk.Frame(
            options_frame,
        )
        cookie_frame.grid(
            row=2,
            column=1,
            sticky=tk.EW,
            padx=10,
            pady=(4, 8),
        )
        cookie_frame.columnconfigure(
            0,
            weight=1,
        )

        cookie_radio_frame = ttk.Frame(
            cookie_frame,
        )
        cookie_radio_frame.grid(
            row=0,
            column=0,
            sticky=tk.W,
        )

        self.cookie_radios = []

        for index, label in enumerate(
            COOKIE_MODES.keys()
        ):
            radio = ttk.Radiobutton(
                cookie_radio_frame,
                text=label,
                value=label,
                variable=self.cookie_mode_var,
                command=self._update_cookie_ui,
            )
            radio.grid(
                row=0,
                column=index,
                sticky=tk.W,
                padx=(0 if index == 0 else 16, 0),
            )

            self.cookie_radios.append(radio)

        self.cookie_file_frame = ttk.Frame(
            cookie_frame,
        )
        self.cookie_file_frame.grid(
            row=1,
            column=0,
            sticky=tk.EW,
            pady=(8, 0),
        )
        self.cookie_file_frame.columnconfigure(
            0,
            weight=1,
        )

        self.cookie_file_entry = ttk.Entry(
            self.cookie_file_frame,
            textvariable=self.cookie_file_var,
        )
        self.cookie_file_entry.grid(
            row=0,
            column=0,
            sticky=tk.EW,
        )

        self._add_entry_context_menu(
            self.cookie_file_entry,
        )

        ttk.Button(
            self.cookie_file_frame,
            text="Gözat",
            command=self.choose_cookie_file,
            width=8,
        ).grid(
            row=0,
            column=1,
            padx=(8, 0),
        )

        self.cookie_hint_frame = ttk.Frame(
            cookie_frame,
        )
        self.cookie_hint_frame.grid(
            row=2,
            column=0,
            sticky=tk.EW,
            pady=(8, 0),
        )
        self.cookie_hint_frame.columnconfigure(
            0,
            weight=1,
        )

        cookie_hint_text = tk.Text(
            self.cookie_hint_frame,
            height=2,
            wrap=tk.WORD,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
            font=("Segoe UI", 9),
            foreground="#555555",
            background=style.lookup(
                "TFrame",
                "background",
            ),
            cursor="arrow",
        )
        cookie_hint_text.grid(
            row=0,
            column=0,
            sticky=tk.EW,
        )

        cookie_hint_text.insert(
            tk.END,
            "Yalnızca Firefox üzerinden çerez tespiti yapılabilir. Diğer tarayıcılarda ",
        )

        cookie_hint_text.insert(
            tk.END,
            "Cookie Exporter",
            "link",
        )

        cookie_hint_text.insert(
            tk.END,
            " eklentisi ile indirilen dosyayı çerez dosyası olarak yükleyebilirsiniz.",
        )

        cookie_hint_text.tag_configure(
            "link",
            foreground="#0563C1",
            underline=True,
        )
        cookie_hint_text.tag_bind(
            "link",
            "<Button-1>",
            lambda event: webbrowser.open(
                COOKIE_EXPORTER_URL
            ),
        )
        cookie_hint_text.tag_bind(
            "link",
            "<Enter>",
            lambda event: cookie_hint_text.configure(
                cursor="hand2",
            ),
        )
        cookie_hint_text.tag_bind(
            "link",
            "<Leave>",
            lambda event: cookie_hint_text.configure(
                cursor="arrow",
            ),
        )

        cookie_hint_text.configure(
            state=tk.DISABLED,
        )

        self._update_cookie_ui()

        progress_frame = ttk.LabelFrame(
            main,
            text="İlerleme",
        )
        progress_frame.pack(
            fill=tk.X,
            pady=8,
        )
        progress_frame.columnconfigure(
            0,
            weight=1,
        )

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress_bar.grid(
            row=0,
            column=0,
            sticky=tk.EW,
            padx=10,
            pady=(10, 4),
        )

        ttk.Label(
            progress_frame,
            textvariable=self.progress_text_var,
            style="Status.TLabel",
        ).grid(
            row=1,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=(0, 10),
        )

        action_frame = ttk.Frame(main)
        action_frame.pack(
            fill=tk.X,
            pady=(8, 10),
        )

        self.start_button = ttk.Button(
            action_frame,
            text="İndirmeyi Başlat",
            command=self.start_download,
        )
        self.start_button.pack(
            side=tk.LEFT,
        )

        self.cancel_button = ttk.Button(
            action_frame,
            text="Durdur",
            command=self.cancel_download,
            state=tk.DISABLED,
        )
        self.cancel_button.pack(
            side=tk.LEFT,
            padx=(8, 0),
        )

        ttk.Label(
            action_frame,
            textvariable=self.status_var,
            style="Status.TLabel",
        ).pack(
            side=tk.LEFT,
            padx=(14, 0),
        )

        log_frame = ttk.LabelFrame(
            main,
            text="İşlem Günlüğü",
        )
        log_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )
        log_frame.rowconfigure(
            0,
            weight=1,
        )
        log_frame.columnconfigure(
            0,
            weight=1,
        )

        self.log_text = tk.Text(
            log_frame,
            height=12,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 9),
        )
        self.log_text.grid(
            row=0,
            column=0,
            sticky=tk.NSEW,
        )

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient=tk.VERTICAL,
            command=self.log_text.yview,
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky=tk.NS,
        )

        self.log_text.configure(
            yscrollcommand=scrollbar.set,
        )

    def _update_cookie_ui(self) -> None:
        mode = COOKIE_MODES.get(
            self.cookie_mode_var.get(),
            "none",
        )

        if mode == "file":
            self.cookie_file_frame.grid()
        else:
            self.cookie_file_frame.grid_remove()

    def choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(
            title="İndirme klasörünü seç",
        )

        if selected:
            self.output_dir_var.set(
                str(Path(selected).resolve())
            )

    def choose_cookie_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Cookie dosyasını seç",
            filetypes=[
                (
                    "Cookie dosyaları",
                    "*.txt;*.cookies",
                ),
                (
                    "Tüm dosyalar",
                    "*.*",
                ),
            ],
        )

        if selected:
            self.cookie_file_var.set(
                str(Path(selected).resolve())
            )

    def start_download(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showwarning(
                APP_NAME,
                "Devam eden indirme bitmeden "
                "yeni indirme başlatılamaz.",
            )
            return

        url = self.url_var.get().strip()

        if not url:
            messagebox.showwarning(
                APP_NAME,
                "Video, ses veya playlist linki girin.",
            )
            self.url_entry.focus_set()
            return

        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):
            messagebox.showwarning(
                APP_NAME,
                "Geçerli bir http veya https linki girin.",
            )
            self.url_entry.focus_set()
            return

        output_dir_text = (
            self.output_dir_var.get().strip()
        )

        if not output_dir_text:
            messagebox.showwarning(
                APP_NAME,
                "Lütfen bir indirme klasörü seçin.",
            )
            return

        cookie_mode = COOKIE_MODES.get(
            self.cookie_mode_var.get(),
            "none",
        )

        cookie_value: Optional[str] = None

        if cookie_mode == "browser":
            cookie_value = "firefox"

        elif cookie_mode == "file":
            cookie_value = (
                self.cookie_file_var.get().strip()
            )

            if not cookie_value:
                messagebox.showwarning(
                    APP_NAME,
                    "Lütfen bir çerez dosyası seçin.",
                )
                return

            cookie_path = Path(
                cookie_value
            ).expanduser()

            if not cookie_path.is_file():
                messagebox.showwarning(
                    APP_NAME,
                    "Seçilen çerez dosyası bulunamadı.",
                )
                return

        output_dir = Path(
            output_dir_text
        ).resolve()

        self._clear_log()

        self.current_playlist_counter = ""

        self.progress_var.set(0.0)
        self.progress_text_var.set(
            "Başlatılıyor..."
        )

        self._append_log(
            f"{APP_NAME} {APP_VERSION}"
        )

        self.status_var.set(
            "İndirme çalışıyor..."
        )

        self.start_button.configure(
            state=tk.DISABLED,
        )
        self.cancel_button.configure(
            state=tk.NORMAL,
        )

        profile_key = PROFILE_OPTIONS[
            self.profile_var.get()
        ]

        selected_res = (
            self.res_var.get()
            if profile_key == "video"
            else None
        )

        self.worker = DownloadWorker(
            tools=self.tools,
            url=url,
            profile_name=profile_key,
            output_dir=output_dir,
            cookie_mode=cookie_mode,
            cookie_value=cookie_value,
            max_resolution=selected_res,
            event_queue=self.event_queue,
        )

        self.worker.start()

    def cancel_download(self) -> None:
        if self.worker and self.worker.is_alive():
            self.status_var.set(
                "Durduruluyor..."
            )

            self.worker.cancel()

            self.cancel_button.configure(
                state=tk.DISABLED,
            )

    def _process_queue(self) -> None:
        try:
            while True:
                event_type, text = (
                    self.event_queue.get_nowait()
                )

                if event_type == "status":
                    self.status_var.set(text)

                elif event_type == "log":
                    self._append_log(text)

                elif event_type == "event":
                    self._handle_event(text)

                elif event_type == "success":
                    self._append_log(text)

                    self.status_var.set(
                        "Tamamlandı."
                    )

                    self.progress_var.set(
                        100.0
                    )

                    self.progress_text_var.set(
                        "Tamamlandı."
                    )

                    messagebox.showinfo(
                        APP_NAME,
                        text,
                    )

                elif event_type == "warning":
                    self._append_log(text)

                    self.status_var.set(text)
                    self.progress_text_var.set(text)

                    if text == (
                        "İndirme kullanıcı tarafından durduruldu."
                    ):
                        messagebox.showwarning(
                            APP_NAME,
                            text,
                        )

                elif event_type == "error":
                    self._append_log_with_spacing(text)

                    self.status_var.set(
                        "Tamamlandı ancak bazı videolar indirilemedi."
                    )

                    self.progress_text_var.set(
                        "Tamamlandı ancak bazı videolar indirilemedi."
                    )

                    messagebox.showerror(
                        APP_NAME,
                        text,
                    )

                elif event_type == "done":
                    self.start_button.configure(
                        state=tk.NORMAL,
                    )

                    self.cancel_button.configure(
                        state=tk.DISABLED,
                    )

        except queue.Empty:
            pass

        self.root.after(
            100,
            self._process_queue,
        )

    def _handle_event(self, event: Any) -> None:
        if isinstance(event, PlaylistEvent):
            self.current_playlist_counter = (
                f"Video {event.current}/{event.total}"
            )

            self.progress_var.set(0.0)

            self.progress_text_var.set(
                f"{self.current_playlist_counter} | "
                "Video hazırlanıyor..."
            )
            return

        if isinstance(event, ProgressEvent):
            self.progress_var.set(
                max(
                    0.0,
                    min(
                        100.0,
                        event.percent,
                    ),
                )
            )

            prefix = (
                f"{self.current_playlist_counter} | "
                if self.current_playlist_counter
                else ""
            )

            speed = (
                getattr(event, "speed", "")
                or "?"
            )

            eta = (
                getattr(event, "eta", "")
                or "?"
            )

            self.progress_text_var.set(
                f"{prefix}"
                f"{event.percent:.1f}% | "
                f"{speed} | ETA {eta}"
            )
            return

        if isinstance(event, FileDoneEvent):
            self.progress_var.set(100.0)

            prefix = (
                f"{self.current_playlist_counter} | "
                if self.current_playlist_counter
                else ""
            )

            self._append_log("")

            if event.report:
                self._append_log(event.report)

            self._append_log(
                f"İndirme tamamlandı: "
                f"{event.file_name}"
            )

            self.progress_text_var.set(
                f"{prefix}"
                f"Tamamlandı: "
                f"{event.file_name}"
            )
            return

        if isinstance(event, WarningEvent):
            self._append_log_with_spacing(
                self._event_text(event)
            )
            return

        if isinstance(event, ErrorEvent):
            self._append_log_with_spacing(
                self._event_text(event)
            )
            return

    def _event_text(self, event: Any) -> str:
        for attribute in (
            "text",
            "message",
            "error",
            "warning",
        ):
            value = getattr(
                event,
                attribute,
                None,
            )

            if value:
                return str(value)

        return str(event)

    def _append_log(self, text: str) -> None:
        timestamp = time.strftime(
            "%H:%M:%S"
        )

        self.log_text.configure(
            state=tk.NORMAL,
        )

        if text == "":
            self.log_text.insert(
                tk.END,
                "\n",
            )
        else:
            self.log_text.insert(
                tk.END,
                f"[{timestamp}] {text}\n",
            )

        self.log_text.configure(
            state=tk.DISABLED,
        )

        self.log_text.see(
            tk.END,
        )

    def _append_log_with_spacing(
        self,
        text: str,
    ) -> None:
        self._append_log("")
        self._append_log(text)
        self._append_log("")

    def _clear_log(self) -> None:
        self.log_text.configure(
            state=tk.NORMAL,
        )

        self.log_text.delete(
            "1.0",
            tk.END,
        )

        self.log_text.configure(
            state=tk.DISABLED,
        )

    def _on_close(self) -> None:
        if (
            self.worker is not None
            and self.worker.is_alive()
        ):
            should_close = messagebox.askyesno(
                APP_NAME,
                "İndirme devam ediyor. "
                "Uygulamadan çıkılsın mı?",
            )

            if not should_close:
                return

            self.worker.cancel()

            self.worker.join(
                timeout=5.0,
            )

        self.root.destroy()


def run_self_test() -> int:
    tools = Tools.discover()

    print(
        f"{APP_NAME} {APP_VERSION} self-test"
    )
    print(
        f"App dir: {tools.app_dir}"
    )

    ok = True

    yt_dlp_ok = bool(tools.yt_dlp_cmd)

    print(
        "OK: yt-dlp ->",
        " ".join(tools.yt_dlp_cmd),
    )

    ok = ok and yt_dlp_ok

    ffmpeg_state = "OK" if tools.has_ffmpeg else "FAIL"

    print(
        f"{ffmpeg_state}: ffmpeg/ffprobe -> "
        f"static_ffmpeg {'available' if tools.has_ffmpeg else 'unavailable'}"
    )

    ok = ok and tools.has_ffmpeg

    deno_path = tools.deno

    if deno_path:
        print(
            f"OK: deno -> {deno_path}"
        )
    else:
        print(
            "FAIL: deno -> bulunamadı"
        )

        ok = False

    print(
        "Command check:",
        "OK" if ok else "FAIL",
    )

    return 0 if ok else 1


def parse_args(
    argv: Sequence[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=APP_NAME,
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
        help="GUI açmadan temel kontrolleri çalıştırır.",
    )

    return parser.parse_args(argv)


def main(
    argv: Optional[Sequence[str]] = None,
) -> int:
    args = parse_args(
        argv
        if argv is not None
        else sys.argv[1:]
    )

    if args.self_test:
        return run_self_test()

    root = tk.Tk()

    VideoDownloaderApp(root)

    root.mainloop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())