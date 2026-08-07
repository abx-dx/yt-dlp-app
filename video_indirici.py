# -*- coding: utf-8 -*-
"""
Basit Türkçe yt-dlp arayüzü.

Bu uygulama taşınabilir (portable) kullanım amacıyla geliştirilmiştir.
Derlenen MediaDownloader ile aynı dizinde aşağıdaki yapı bulunmalıdır.

Gerekli araçlar (bin):
    - bin/yt-dlp (.exe)
    - bin/ffmpeg (.exe)
    - bin/ffprobe (.exe)
    - bin/deno (.exe)

Not:
Bu açıklama aynı zamanda build-portable.sh betiği tarafından bağımlılık
tespiti amacıyla kullanılmaktadır. Yukarıdaki araç listesinde yapılacak
değişiklikler derleme paketine doğrudan yansır.

@thefinega projesinden forklanmıştır.
"""

from __future__ import annotations

import argparse
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, List, Optional, Sequence

# Windows konsol/log akışını UTF-8'e zorlar ve bilinmeyen karakterlerde çökmesini engeller
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


from toolbox.parser import (
    ProgressEvent,
    PlaylistEvent,
    FileDoneEvent,
    LogEvent,
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

IS_WINDOWS = sys.platform.startswith("win")


class DownloadWorker(threading.Thread):
    def __init__(
        self,
        *,
        tools: Tools,
        url: str,
        profile_name: str,
        output_dir: Optional[Path],
        use_firefox_cookies: bool,
        max_resolution: Optional[str] = None,
        event_queue: queue.Queue[tuple[str, Any]],
    ):
        super().__init__(daemon=True)
        self.tools = tools
        self.url = url
        self.profile_name = profile_name
        self.output_dir = output_dir
        self.use_firefox_cookies = use_firefox_cookies
        self.max_resolution = max_resolution
        self.event_queue = event_queue
        self.cancel_requested = threading.Event()
        self.runner: Optional[YtDlpRunner] = None

    def cancel(self) -> None:
        self.cancel_requested.set()

        runner = self.runner
        if runner and hasattr(runner, "stop"):
            try:
                runner.stop()
            except OSError:
                pass

    def emit(self, event_type: str, payload: Any) -> None:
        self.event_queue.put((event_type, payload))

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:
            self.emit("error", f"Beklenmeyen hata: {exc}")
        finally:
            self.emit("done", "finished")

    def _run(self) -> None:
        if not self.tools.ytdlp.exists():
            self.emit("error", f"Eksik araç: {self.tools.ytdlp.name} bin/ klasöründe bulunamadı.")
            return

        out_dir_str = str(self.output_dir) if self.output_dir else None
        if self.output_dir:
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self.emit("error", f"İndirme klasörü oluşturulamadı: {exc}")
                return

        profile = get_profile(self.profile_name)

        self.runner = YtDlpRunner(
            tools=self.tools,
            profile=profile,
            url=self.url,
            output_dir=out_dir_str,
            use_cookies=self.use_firefox_cookies,
            max_resolution=self.max_resolution,
        )

        self.emit("log", f"İndirme klasörü: {self.output_dir or 'Varsayılan'}")
        if self.use_firefox_cookies:
            self.emit("log", "Firefox çerezleri kullanılacak. Uygulama çerez kaydetmez.")

        self.emit("log", "İndirme başlatılıyor...")

        try:
            self.runner.start()
        except OSError as exc:
            self.emit("error", f"yt-dlp başlatılamadı: {exc}")
            return

        try:
            for event in self.runner.events():
                if self.cancel_requested.is_set():
                    break

                if isinstance(event, PlaylistEvent):
                    self.emit("event", event)
                    continue

                if isinstance(event, ProgressEvent):
                    self.emit("event", event)
                    continue

                if isinstance(event, FileDoneEvent):
                    self.emit("log", "")
                    self.emit("log", event.report)
                    self.emit("event", event)
                    self.emit("log", f"İndirme tamamlandı: {event.file_name}")
                    self.emit("log", "")
                    continue

                if isinstance(event, WarningEvent):
                    self.emit("warning", event.text)
                    continue

                if isinstance(event, ErrorEvent):
                    self.emit("error", event.text)
                    continue

                if isinstance(event, LogEvent):
                    self.emit("log", event.text)
                    continue
        except Exception as exc:
            self.emit("error", f"Olaylar okunurken hata oluştu: {exc}")
            return

        return_code = self.runner.wait()
        if self.cancel_requested.is_set():
            self.emit("warning", "İndirme kullanıcı tarafından durduruldu.")
            return

        if return_code == 0:
            if self.profile_name == "playlist":
                self.emit("success", "Tüm playlist başarıyla indirildi ve raporlandı.")
            else:
                self.emit("success", "İndirme başarıyla tamamlandı ve raporlandı.")
            return

        if self.use_firefox_cookies:
            self.emit(
                "warning",
                "Not: Firefox çerezleri okunamadıysa Firefox'u kapatıp tekrar deneyin.",
            )
        self.emit("error", f"İndirme tamamlanamadı. yt-dlp çıkış kodu: {return_code}")


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
        self.output_dir_var = tk.StringVar(value=str(self.tools.app_dir / "indirilenler"))
        self.use_firefox_cookies_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Hazır.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="Henüz indirme yok.")
        self.tool_status_vars = {
            "yt-dlp": tk.StringVar(value="Kontrol bekleniyor."),
            "ffmpeg": tk.StringVar(value="Kontrol bekleniyor."),
            "ffprobe": tk.StringVar(value="Kontrol bekleniyor."),
            "deno": tk.StringVar(value="Kontrol bekleniyor."),
        }

        self._build_ui()
        self.root.after(100, self.refresh_tools)
        self.root.after(100, self._process_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _add_entry_context_menu(self, entry: ttk.Entry) -> None:
        menu = tk.Menu(entry, tearoff=0)
        menu.add_command(label="Kes", command=lambda: entry.event_generate("<<Cut>>"))
        menu.add_command(label="Kopyala", command=lambda: entry.event_generate("<<Copy>>"))
        menu.add_command(label="Yapıştır", command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Tümünü Seç", command=lambda: entry.select_range(0, tk.END))

        def show_menu(event: tk.Event[Any]) -> None:
            entry.focus_set()
            entry.icursor(entry.index(f"@{event.x}"))
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        entry.bind("<Button-3>", show_menu)

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Hint.TLabel", foreground="#555555")
        style.configure("Status.TLabel", foreground="#333333")

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(main, text=APP_NAME, style="Title.TLabel")
        title.pack(anchor=tk.W)

        source_frame = ttk.LabelFrame(main, text="Video / Ses / Playlist Linki")
        source_frame.pack(fill=tk.X, pady=(12, 8))
        source_frame.columnconfigure(0, weight=1)

        self.url_entry = ttk.Entry(source_frame, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=10)
        self.url_entry.focus_set()
        self._add_entry_context_menu(self.url_entry)

        options_frame = ttk.LabelFrame(main, text="Ayarlar")
        options_frame.pack(fill=tk.X, pady=8)
        options_frame.columnconfigure(1, weight=1)

        ttk.Label(options_frame, text="Profil:").grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=8
        )

        profile_row = ttk.Frame(options_frame)
        profile_row.grid(row=0, column=1, sticky=tk.W, padx=10, pady=8)

        self.profile_var = tk.StringVar(value="Video")
        profile_combo = ttk.Combobox(
            profile_row,
            textvariable=self.profile_var,
            values=list(PROFILE_OPTIONS.keys()),
            state="readonly",
            width=12,
        )
        profile_combo.pack(side=tk.LEFT)

        # Çözünürlük Alanı (Video profilinde yan tarafa açılır)
        self.res_lbl = ttk.Label(profile_row, text="Çözünürlük:")
        self.res_var = tk.StringVar(value="En İyi")
        self.res_combo = ttk.Combobox(
            profile_row,
            textvariable=self.res_var,
            values=RESOLUTIONS,
            state="readonly",
            width=14,
        )

        def _on_profile_change(event: Optional[tk.Event[Any]] = None) -> None:
            if PROFILE_OPTIONS.get(self.profile_var.get()) == "video":
                self.res_lbl.pack(side=tk.LEFT, padx=(16, 6))
                self.res_combo.pack(side=tk.LEFT)
            else:
                self.res_lbl.pack_forget()
                self.res_combo.pack_forget()

        profile_combo.bind("<<ComboboxSelected>>", _on_profile_change)
        _on_profile_change()

        ttk.Label(options_frame, text="Klasör:").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=8
        )
        folder_row = ttk.Frame(options_frame)
        folder_row.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=8)
        folder_row.columnconfigure(0, weight=1)
        self.output_dir_entry = ttk.Entry(folder_row, textvariable=self.output_dir_var)
        self.output_dir_entry.grid(row=0, column=0, sticky=tk.EW)
        self._add_entry_context_menu(self.output_dir_entry)

        ttk.Button(
            folder_row,
            text="Seç",
            command=self.choose_output_dir,
        ).grid(row=0, column=1, padx=(8, 0))

        ttk.Checkbutton(
            options_frame,
            text="Firefox çerezlerini kullan",
            variable=self.use_firefox_cookies_var,
        ).grid(row=2, column=1, sticky=tk.W, padx=10, pady=(0, 10))

        tools_frame = ttk.LabelFrame(main, text="Sistem Araçları Durumu", padding=10)
        tools_frame.pack(fill=tk.X, pady=(0, 10))

        status_container = ttk.Frame(tools_frame)
        status_container.pack(fill=tk.X, expand=True, pady=(0, 8))

        tool_map = {
            "yt-dlp": self.tools.ytdlp,
            "ffmpeg": self.tools.ffmpeg,
            "ffprobe": self.tools.ffprobe,
            "deno": self.tools.deno,
        }

        for col, (name, path) in enumerate(tool_map.items()):
            col_frame = ttk.Frame(status_container)
            col_frame.grid(row=0, column=col, sticky=tk.W, padx=12)

            lbl_title = ttk.Label(col_frame, text=f"{path.name}:")
            lbl_title.pack(side=tk.LEFT, padx=(0, 4))

            lbl_status = ttk.Label(col_frame, textvariable=self.tool_status_vars[name])
            lbl_status.pack(side=tk.LEFT)

            status_container.columnconfigure(col, weight=1)

        btn_refresh = ttk.Button(tools_frame, text="Araçları Tekrar Kontrol Et", command=self.refresh_tools)
        btn_refresh.pack(fill=tk.X, expand=True)
        
        progress_frame = ttk.LabelFrame(main, text="İlerleme")
        progress_frame.pack(fill=tk.X, pady=8)
        progress_frame.columnconfigure(0, weight=1)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress_bar.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=(10, 4))
        ttk.Label(progress_frame, textvariable=self.progress_text_var, style="Status.TLabel").grid(
            row=1,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=(0, 10),
        )

        action_frame = ttk.Frame(main)
        action_frame.pack(fill=tk.X, pady=(8, 10))
        self.start_button = ttk.Button(action_frame, text="İndirmeyi Başlat", command=self.start_download)
        self.start_button.pack(side=tk.LEFT)
        self.cancel_button = ttk.Button(
            action_frame,
            text="Durdur",
            command=self.cancel_download,
            state=tk.DISABLED,
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(action_frame, textvariable=self.status_var, style="Status.TLabel").pack(
            side=tk.LEFT,
            padx=(14, 0),
        )

        log_frame = ttk.LabelFrame(main, text="İşlem Günlüğü")
        log_frame.pack(fill=tk.BOTH, expand=True)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame,
            height=12,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 9),
        )
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(
            title="İndirme klasörünü seç",
            initialdir=self.output_dir_var.get() or str(self.tools.app_dir / "indirilenler"),
        )
        if selected:
            self.output_dir_var.set(selected)

    def refresh_tools(self) -> None:
        self.status_var.set("Araçlar kontrol ediliyor...")
        thread = threading.Thread(target=self._refresh_tools_worker, daemon=True)
        thread.start()

    def _refresh_tools_worker(self) -> None:
        tool_map = {
            "yt-dlp": self.tools.ytdlp,
            "ffmpeg": self.tools.ffmpeg,
            "ffprobe": self.tools.ffprobe,
            "deno": self.tools.deno,
        }

        all_ok = True
        for name, path in tool_map.items():
            if path.exists():
                text = "Tamam"
            else:
                text = "Eksik"
                all_ok = False
            self.event_queue.put((f"tool:{name}", text))

        if all_ok:
            self.event_queue.put(("status", "Hazır."))
        else:
            self.event_queue.put(("status", "Eksik araç var."))

    def start_download(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showwarning(APP_NAME, "Devam eden indirme bitmeden yeni indirme başlatılamaz.")
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(APP_NAME, "Video, ses veya playlist linki girin.")
            self.url_entry.focus_set()
            return

        if not (url.startswith("http://") or url.startswith("https://")):
            messagebox.showwarning(APP_NAME, "Geçerli bir http veya https linki girin.")
            self.url_entry.focus_set()
            return

        output_dir = Path(self.output_dir_var.get().strip() or str(self.tools.app_dir / "indirilenler"))

        if not self.tools.ytdlp.exists():
            messagebox.showerror(
                APP_NAME,
                f"Eksik araç dosyası: {self.tools.ytdlp.name}\n\nBu dosya bin/ altında olmalıdır.",
            )
            self.refresh_tools()
            return

        self._clear_log()
        self.current_playlist_counter = ""
        self.progress_var.set(0.0)
        self.progress_text_var.set("Başlatılıyor...")
        self._append_log(f"{APP_NAME} {APP_VERSION}")
        self._append_log(f"Uygulama klasörü: {self.tools.app_dir}")
        self.status_var.set("İndirme çalışıyor...")
        self.start_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)

        profile_key = PROFILE_OPTIONS[self.profile_var.get()]
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
            use_firefox_cookies=self.use_firefox_cookies_var.get(),
            max_resolution=selected_res,
            event_queue=self.event_queue,
        )
        self.worker.start()

    def cancel_download(self) -> None:
        if self.worker and self.worker.is_alive():
            self.status_var.set("Durduruluyor...")
            self.worker.cancel()
            self.cancel_button.configure(state=tk.DISABLED)

    def _process_queue(self) -> None:
        try:
            while True:
                event_type, text = self.event_queue.get_nowait()
                if event_type.startswith("tool:"):
                    name = event_type.split(":", 1)[1]
                    self.tool_status_vars[name].set(text)
                elif event_type == "status":
                    self.status_var.set(text)
                elif event_type == "log":
                    self._append_log(text)
                elif event_type == "event":
                    self._handle_event(text)                    
                elif event_type == "success":
                    self._append_log(text)
                    self.status_var.set("Tamamlandı.")
                    self.progress_var.set(100.0)
                    self.progress_text_var.set("Tamamlandı.")
                    messagebox.showinfo(APP_NAME, text)
                elif event_type == "warning":
                    self._append_log(text)
                    self.status_var.set(text)
                    self.progress_text_var.set(text)
                elif event_type == "error":
                    self._append_log(text)
                    self.status_var.set("Hata oluştu.")
                    self.progress_text_var.set("Hata oluştu.")
                    messagebox.showerror(APP_NAME, text)
                elif event_type == "done":
                    self.start_button.configure(state=tk.NORMAL)
                    self.cancel_button.configure(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.root.after(100, self._process_queue)

    def _handle_event(self, event: Any) -> None:

        if isinstance(event, PlaylistEvent):
            self.current_playlist_counter = f"Video {event.current}/{event.total}"
            self.progress_var.set(0.0)
            self.progress_text_var.set(
                f"{self.current_playlist_counter} | Video hazırlanıyor..."
            )
            return

        if isinstance(event, ProgressEvent):
            self.progress_var.set(max(0.0, min(100.0, event.percent)))

            prefix = (
                f"{self.current_playlist_counter} | "
                if self.current_playlist_counter
                else ""
            )

            speed = getattr(event, "speed", "") or "?"
            eta = getattr(event, "eta", "") or "?"

            self.progress_text_var.set(
                f"{prefix}{event.percent:.1f}% | {speed} | ETA {eta}"
            )
            return

        if isinstance(event, FileDoneEvent):
            self.progress_var.set(100.0)

            prefix = (
                f"{self.current_playlist_counter} | "
                if self.current_playlist_counter
                else ""
            )

            self.progress_text_var.set(
                f"{prefix}Tamamlandı: {event.file_name}"
            )

    def _append_log(self, text: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state=tk.NORMAL)
        if text == "":
            self.log_text.insert(tk.END, "\n")
        else:
            self.log_text.insert(tk.END, f"[{timestamp}] {text}\n")
        self.log_text.configure(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def _clear_log(self) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _on_close(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            should_close = messagebox.askyesno(
                APP_NAME,
                "İndirme devam ediyor. Uygulamadan çıkılsın mı?",
            )
            if not should_close:
                return
            self.worker.cancel()
            self.worker.join(timeout=5.0)
        self.root.destroy()


def run_self_test() -> int:
    tools = Tools.discover()
    print(f"{APP_NAME} {APP_VERSION} self-test")
    print(f"App dir: {tools.app_dir}")

    ok = True
    tool_map = {
        "yt-dlp": tools.ytdlp,
        "ffmpeg": tools.ffmpeg,
        "ffprobe": tools.ffprobe,
        "deno": tools.deno,
    }

    for name, path in tool_map.items():
        exists = path.exists()
        state = "OK" if exists else "FAIL"
        print(f"{state}: {name} -> {path}")
        ok = ok and exists

    print("Command check:", "OK" if ok else "FAIL")
    return 0 if ok else 1


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--self-test", action="store_true", help="GUI açmadan temel kontrolleri çalıştırır.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.self_test:
        return run_self_test()

    root = tk.Tk()
    VideoDownloaderApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())