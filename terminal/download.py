from __future__ import annotations

from pathlib import Path

from toolbox.parser import (
    ErrorEvent,
    FileDoneEvent,
    PlaylistEvent,
    ProgressEvent,
    WarningEvent,
)
from toolbox.profiles import get_profile
from toolbox.runner import YtDlpRunner
from toolbox.tools import Tools

from terminal.debug import get_debug_channel
from terminal.input import clear_screen, hide_cursor, show_cursor
from terminal.ui import draw_progress_bar


SEPARATOR = "-" * 50


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


def start_download_cancel_listener(
    runner: YtDlpRunner,
):
    """İndirme sırasında Esc tuşunu izler ve runner'ı durdurur."""

    import os
    import threading

    stop_listener = threading.Event()

    def listen() -> None:
        if os.name != "nt":
            return

        import msvcrt

        while not stop_listener.is_set():

            if msvcrt.kbhit():
                key = msvcrt.getwch()

                if key == "\x1b":
                    try:
                        runner.stop()
                    except Exception:
                        pass

                    return

            stop_listener.wait(0.05)

    thread = threading.Thread(
        target=listen,
        daemon=True,
    )

    thread.start()

    return (
        stop_listener,
        thread,
    )


def run_download_process(
    state,
) -> None:
    """Core motorunu çalıştırır ve canlı ilerlemeyi ekrana basar."""

    clear_screen()
    hide_cursor()

    print("İndirme Başlatılıyor...")
    print(SEPARATOR)

    try:
        profile_key = PROFILE_OPTIONS[state.profile]

    except KeyError as exc:
        raise ValueError(
            f"Geçersiz profil: {state.profile}"
        ) from exc

    try:
        cookie_mode = COOKIE_MODES[state.cookie_mode]

    except KeyError as exc:
        raise ValueError(
            f"Geçersiz çerez modu: {state.cookie_mode}"
        ) from exc

    cookie_val = None

    if cookie_mode == "browser":
        cookie_val = "firefox"

    elif cookie_mode == "file":
        cookie_val = state.cookie_value

    out_dir = Path(state.download_dir).resolve()

    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    tools = Tools.discover()

    profile = get_profile(profile_key)

    runner = YtDlpRunner(
        tools=tools,
        profile=profile,
        url=state.url,
        output_dir=str(out_dir),
        cookie_mode=cookie_mode,
        cookie_value=cookie_val,
        max_resolution=(
            state.resolution
            if state.profile == "Video"
            else None
        ),
    )

    debug_channel = get_debug_channel()

    stop_listener, listener_thread = (
        start_download_cancel_listener(runner)
    )

    try:
        if debug_channel is not None:
            with debug_channel.redirect_stdout():
                runner.start()

        else:
            runner.start()

        events = runner.events()

        while True:
            try:
                if debug_channel is not None:
                    with debug_channel.redirect_stdout():
                        event = next(events)

                else:
                    event = next(events)

            except StopIteration:
                break

            if isinstance(event, ProgressEvent):
                progress_bar = draw_progress_bar(
                    event.percent
                )

                print(
                    f"\r{progress_bar} | "
                    f"{event.speed} | "
                    f"ETA {event.eta}",
                    end="",
                    flush=True,
                )

            elif isinstance(event, PlaylistEvent):
                print(
                    f"\rPlaylist: "
                    f"{event.current}/{event.total}",
                    end="",
                    flush=True,
                )

            elif isinstance(event, FileDoneEvent):
                print()

                if event.report:
                    print(event.report)

                else:
                    print(
                        f"[BAŞARILI] "
                        f"{event.file_name}"
                    )

            elif isinstance(event, WarningEvent):
                print()

                print(
                    f"[UYARI] "
                    f"{event.text}"
                )

            elif isinstance(event, ErrorEvent):
                print()

                print(
                    f"[HATA] "
                    f"{event.text}"
                )

        if debug_channel is not None:
            with debug_channel.redirect_stdout():
                exit_code = runner.wait()

        else:
            exit_code = runner.wait()

    finally:
        stop_listener.set()

        if debug_channel is not None:
            debug_channel.close()

    print()
    print(SEPARATOR)

    if runner.is_stopped:
        print(
            "İndirme kullanıcı tarafından durduruldu."
        )

    elif exit_code == 0:
        print("İşlem Tamamlandı!")

    else:
        print(
            "İşlem Hata İle Sonlandı. "
            f"Çıkış Kodu: {exit_code}"
        )

    print()
    print(
        "[Enter] tuşuna basarak "
        "ana menüye dönebilirsiniz."
    )

    show_cursor()
    input()