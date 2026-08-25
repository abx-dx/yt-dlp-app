from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

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


# ---------------------------------------------------------
# Core Import Yolları
# ---------------------------------------------------------

WEB_DIR = Path(__file__).resolve().parent
CORE_DIR = WEB_DIR.parent / "yt-dlp-core"

if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))


import static_ffmpeg

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from toolbox.parser import (
    ErrorEvent,
    FileDoneEvent,
    PlaylistEvent,
    ProgressEvent,
    WarningEvent,
)

from toolbox.profiles import (
    RESOLUTIONS,
    get_profile,
)

from toolbox.runner import YtDlpRunner
from toolbox.tools import Tools


# ---------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------

APP_NAME = "Video / Ses / Playlist İndirici"
APP_VERSION = "1.0"

PROFILE_OPTIONS = {
    "Video": "video",
    "Ses": "audio",
    "Playlist": "playlist",
}

static_ffmpeg.add_paths()


app = FastAPI(
    title=APP_NAME
)

STATIC_DIR = WEB_DIR / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


# ---------------------------------------------------------
# Aktif Runner
# ---------------------------------------------------------

app_state = {
    "active_runner": None,
}


def set_active_runner(
    runner: YtDlpRunner | None
) -> None:
    app_state["active_runner"] = runner


def get_active_runner():
    return app_state.get(
        "active_runner"
    )


def clear_active_runner(
    runner=None
) -> None:
    current = get_active_runner()

    if (
        runner is None
        or current is runner
    ):
        set_active_runner(None)


# ---------------------------------------------------------
# TMP Klasör Temizleme
# ---------------------------------------------------------

def clear_tmp_downloads(
    tools: Tools
) -> None:
    """
    .tmp_downloads klasörünü korur,
    içindeki tüm dosya ve klasörleri siler.
    """
    tmp_dir = Path(
        tools.app_dir
    ) / ".tmp_downloads"

    try:
        tmp_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        for item in tmp_dir.iterdir():

            try:
                if item.is_dir():
                    shutil.rmtree(
                        item,
                        ignore_errors=True
                    )
                else:
                    item.unlink(
                        missing_ok=True
                    )

            except Exception as exc:
                print(
                    "[TMP] Silinemedi: "
                    f"{item} -> {exc}"
                )

        print(
            "[TMP] .tmp_downloads içeriği temizlendi."
        )

    except Exception as exc:
        print(
            "[TMP] Temizleme hatası: "
            f"{exc}"
        )


# ---------------------------------------------------------
# Klasör Seçimi
# ---------------------------------------------------------

@app.get("/api/select-folder")
async def select_folder():
    """
    İşletim sisteminin native klasör seçim penceresini açar.

    Kullanıcı klasör seçerse:
        {"path": "...", "cancelled": false}

    İptal ederse:
        {"path": "", "cancelled": true}
    """

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()

        try:
            root.attributes("-topmost", True)
        except Exception:
            pass

        try:
            selected = filedialog.askdirectory(
                title="İndirme klasörünü seçin",
                mustexist=True,
            )
        finally:
            root.destroy()

        if not selected:
            return {
                "path": "",
                "cancelled": True,
            }

        return {
            "path": str(Path(selected).resolve()),
            "cancelled": False,
        }

    except Exception as exc:
        print(
            "[FOLDER] Klasör seçim hatası: "
            f"{exc}"
        )

        return {
            "path": "",
            "cancelled": False,
            "error": str(exc),
        }


# ---------------------------------------------------------
# Durdurma
# ---------------------------------------------------------

@app.post("/api/download/stop")
async def stop_download():

    runner = get_active_runner()

    if runner is None:
        print(
            "[API] Durdurma isteği geldi "
            "ancak aktif runner yok."
        )

        return {
            "status": "not_found",
            "message": (
                "Aktif indirme bulunamadı."
            ),
        }

    print(
        "[API] Durdurma isteği alındı."
    )

    try:
        runner.stop()

        return {
            "status": "success",
            "message": (
                "İndirme durduruldu."
            ),
        }

    except Exception as exc:

        print(
            "[API] Runner durdurma hatası: "
            f"{exc}"
        )

        return {
            "status": "error",
            "message": str(exc),
        }


# ---------------------------------------------------------
# Ana Sayfa
# ---------------------------------------------------------

@app.get("/")
async def index():
    return FileResponse(
        STATIC_DIR / "index.html"
    )


# ---------------------------------------------------------
# Seçenekler
# ---------------------------------------------------------

@app.get("/api/options")
async def get_options():
    return {
        "profiles": PROFILE_OPTIONS,
        "resolutions": RESOLUTIONS,
    }


# ---------------------------------------------------------
# Download SSE
# ---------------------------------------------------------

@app.get("/api/download/stream")
async def stream_download(
    url: str = Query(...),
    profile_key: str = Query("video"),
    resolution: Optional[str] = Query(None),
    use_firefox_cookies: bool = Query(False),
    output_dir: str = Query(...),
):
    async def event_stream():

        tools = Tools.discover()

        try:
            out_dir = Path(output_dir).expanduser().resolve()

            if not out_dir.exists():
                raise ValueError(
                    "Geçerli bir indirme klasörü seçilmedi."
                )

            if not out_dir.is_dir():
                raise ValueError(
                    "Seçilen indirme yolu bir klasör değil."
                )

        except Exception as exc:

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "text": (
                            "İndirme klasörü "
                            "kullanılamadı: "
                            f"{exc}"
                        ),
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

            return

        # Her yeni indirme başlamadan önce
        # geçici klasörün içini temizle.
        clear_tmp_downloads(tools)

        profile = get_profile(
            profile_key
        )


        if use_firefox_cookies:

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "log",
                        "text": (
                            "Firefox çerezleri "
                            "kullanılacak."
                        ),
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "log",
                    "text": (
                        "İndirme başlatılıyor..."
                    ),
                },
                ensure_ascii=False
            )
            + "\n\n"
        )

        runner = YtDlpRunner(
            tools=tools,
            profile=profile,
            url=url,
            output_dir=str(out_dir),
            use_cookies=use_firefox_cookies,
            max_resolution=(
                resolution
                if profile_key == "video"
                else None
            ),
        )

        set_active_runner(runner)

        try:
            runner.start()

        except Exception as exc:

            clear_active_runner(
                runner
            )

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "text": (
                            "yt-dlp başlatılamadı: "
                            f"{exc}"
                        ),
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

            return

        current_playlist = ""

        try:

            for event in runner.events():

                payload = {}

                if isinstance(
                    event,
                    PlaylistEvent
                ):

                    current_playlist = (
                        f"Video "
                        f"{event.current}/"
                        f"{event.total}"
                    )

                    payload = {
                        "type": "playlist",
                        "counter": (
                            current_playlist
                        ),
                        "text": (
                            f"{current_playlist} | "
                            "Video hazırlanıyor..."
                        ),
                    }

                elif isinstance(
                    event,
                    ProgressEvent
                ):

                    speed = (
                        getattr(
                            event,
                            "speed",
                            ""
                        )
                        or "?"
                    )

                    eta = (
                        getattr(
                            event,
                            "eta",
                            ""
                        )
                        or "?"
                    )

                    prefix = (
                        f"{current_playlist} | "
                        if current_playlist
                        else ""
                    )

                    payload = {
                        "type": "progress",
                        "percent": max(
                            0.0,
                            min(
                                100.0,
                                event.percent
                            ),
                        ),
                        "text": (
                            f"{prefix}"
                            f"{event.percent:.1f}% | "
                            f"{speed} | ETA {eta}"
                        ),
                    }

                elif isinstance(
                    event,
                    FileDoneEvent
                ):

                    prefix = (
                        f"{current_playlist} | "
                        if current_playlist
                        else ""
                    )

                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "log",
                                "text": "",
                            },
                            ensure_ascii=False
                        )
                        + "\n\n"
                    )

                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "log",
                                "text": event.report,
                            },
                            ensure_ascii=False
                        )
                        + "\n\n"
                    )

                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "log",
                                "text": (
                                    "İndirme tamamlandı: "
                                    f"{event.file_name}"
                                ),
                            },
                            ensure_ascii=False
                        )
                        + "\n\n"
                    )

                    payload = {
                        "type": "file_done",
                        "percent": 100.0,
                        "text": (
                            f"{prefix}"
                            f"Tamamlandı: "
                            f"{event.file_name}"
                        ),
                    }

                elif isinstance(
                    event,
                    WarningEvent
                ):

                    payload = {
                        "type": "warning",
                        "text": event.text,
                    }

                elif isinstance(
                    event,
                    ErrorEvent
                ):

                    payload = {
                        "type": "error",
                        "text": event.text,
                    }

                if payload:
                    yield (
                        "data: "
                        + json.dumps(
                            payload,
                            ensure_ascii=False
                        )
                        + "\n\n"
                    )

                await asyncio.sleep(
                    0.01
                )

            return_code = runner.wait()

            if runner.is_stopped:

                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "stopped",
                            "text": (
                                "İndirme kullanıcı "
                                "tarafından durduruldu."
                            ),
                        },
                        ensure_ascii=False
                    )
                    + "\n\n"
                )

            elif return_code == 0:

                message = (
                    "Tüm playlist başarıyla "
                    "indirildi ve raporlandı."
                    if profile_key == "playlist"
                    else
                    "İndirme başarıyla "
                    "tamamlandı ve raporlandı."
                )

                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "success",
                            "text": message,
                        },
                        ensure_ascii=False
                    )
                    + "\n\n"
                )

            else:

                if use_firefox_cookies:

                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "warning",
                                "text": (
                                    "Firefox çerezleri "
                                    "okunamadıysa Firefox'u "
                                    "kapatıp tekrar deneyin."
                                ),
                            },
                            ensure_ascii=False
                        )
                        + "\n\n"
                    )

                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "error",
                            "text": (
                                "İndirme tamamlanamadı. "
                                "yt-dlp çıkış kodu: "
                                f"{return_code}"
                            ),
                        },
                        ensure_ascii=False
                    )
                    + "\n\n"
                )

        except asyncio.CancelledError:


            if not runner.is_stopped:

                try:
                    runner.stop()

                except Exception:
                    pass

            raise

        except Exception as exc:

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "text": (
                            "Olaylar okunurken "
                            "hata oluştu: "
                            f"{exc}"
                        ),
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

        finally:

            clear_active_runner(
                runner
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


# ---------------------------------------------------------
# Uygulamayı Kapat
# ---------------------------------------------------------

@app.post("/api/app/exit")
async def exit_application():

    print(
        "[API] Uygulama kapatma isteği alındı."
    )

    runner = get_active_runner()

    if runner:

        try:

            print(
                "[API] Aktif runner "
                "sonlandırılıyor..."
            )

            runner.stop()

        except Exception as exc:

            print(
                "[API] Runner kapatma hatası: "
                f"{exc}"
            )

    def kill_processes():

        import time

        time.sleep(0.3)

        print(
            "[API] Deno süreçleri "
            "sonlandırılıyor..."
        )

        subprocess.run(
            [
                "taskkill",
                "/F",
                "/IM",
                "deno.exe",
                "/T",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        print(
            "[API] Python süreçleri "
            "sonlandırılıyor..."
        )

        subprocess.run(
            [
                "taskkill",
                "/F",
                "/IM",
                "python.exe",
                "/T",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        subprocess.run(
            [
                "taskkill",
                "/F",
                "/IM",
                "pythonw.exe",
                "/T",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    threading.Thread(
        target=kill_processes,
        daemon=True,
    ).start()

    return {
        "status": "success",
        "message": (
            "Uygulama kapatılıyor."
        ),
    }


# ---------------------------------------------------------
# Başlat
# ---------------------------------------------------------

if __name__ == "__main__":
    import threading
    import time
    import webbrowser
    import uvicorn

    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000")

    threading.Thread(
        target=open_browser,
        daemon=True,
    ).start()

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
