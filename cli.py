from __future__ import annotations

import os
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from terminal.input import (
    clear_screen,
    editable_input,
    filesystem_dialog,
    read_key,
    show_cursor,
)

from terminal.ui import render_ui

from terminal.console import (
    apply_console_settings,
    enable_windows_vt,
)

from terminal.debug import (
    CLI_CHILD_ENV,
    launch_application_console,
)


# ----------------------------------------------------------------------
# CORE MOTOR DİZİNÜNÜ PYTHON YOLUNA EKLİYORUZ
# ----------------------------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent
CORE_DIR = CURRENT_DIR.parent / "yt-dlp-core"

COOKIE_EXPORTER_URL = (
    "https://chromewebstore.google.com/detail/"
    "cookie-exporter/fhnmmidekmgocpjdceeffppcodigillk"
)

if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))


# ----------------------------------------------------------------------
# CORE importları
#
# CORE_DIR sys.path'e eklendikten sonra yapılmalıdır.
# terminal.download da toolbox.* kullandığı için o da burada import edilir.
# ----------------------------------------------------------------------

from toolbox.profiles import RESOLUTIONS
from terminal.download import run_download_process


# ----------------------------------------------------------------------
# WINDOWS UTF-8 ÇIKIŞI
# ----------------------------------------------------------------------

if os.name == "nt":
    try:
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )
        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace",
        )
    except AttributeError:
        pass


# ----------------------------------------------------------------------
# GUI ile aynı profil sözleşmesi
# ----------------------------------------------------------------------

PROFILE_OPTIONS = {
    "Video": "video",
    "Ses": "audio",
    "Playlist": "playlist",
}


# ----------------------------------------------------------------------
# GUI ile aynı çerez sözleşmesi
# ----------------------------------------------------------------------

COOKIE_MODES = {
    "Çerez yok": "none",
    "Firefox": "browser",
    "Çerez dosyası": "file",
}


@dataclass
class CLIState:
    url: str = ""

    profile: str = ""
    profile_cursor: int = 0

    resolution: str = ""
    resolution_options: List[str] | None = None
    resolution_cursor: int = 0

    download_dir: str = ""

    cookie_mode: str = "Çerez yok"
    cookie_value: str = ""
    cookie_cursor: int = 0

    # Stage'ler:
    # 0: URL
    # 1: Profil
    # 2: Çözünürlük
    # 3: İndirme Dizini
    # 4: Çerezler
    # 5: Çerez Dosyası
    # 6: Özet
    stage: int = 0

    def __post_init__(self) -> None:
        if self.resolution_options is None:
            self.resolution_options = []


def is_valid_url(
    value: str,
) -> bool:
    """HTTP/HTTPS URL kontrolü yapar."""

    try:
        parsed = urlparse(value)

        return (
            parsed.scheme in (
                "http",
                "https",
            )
            and bool(parsed.netloc)
        )

    except ValueError:
        return False


def fetch_resolutions_from_core(
    url: str,
) -> List[str]:
    """GUI ile aynı şekilde core'daki RESOLUTIONS listesini kullanır."""

    del url

    return list(RESOLUTIONS)


def main() -> None:
    state = CLIState()

    error_msg = ""
    last_stage = -1

    default_download_dir = str(
        Path(os.environ["USERPROFILE"]) / "Downloads"
    )

    try:
        while True:

            if (
                state.stage != last_stage
                or error_msg
            ):
                render_ui(
                    state,
                    error_msg,
                )

                last_stage = state.stage

                # Hata yalnızca render edilen ekranda
                # gösterilir; yeni bir ayırıcı oluşturulmaz.
                error_msg = ""

            # =========================================================
            # STAGE 0: URL
            # =========================================================

            if state.stage == 0:

                url_input = editable_input(
                    "URL: ",
                    state.url,
                )

                if url_input is None:
                    clear_screen()

                    print(
                        "Çıkılıyor..."
                    )

                    return

                url_input = url_input.strip()

                if is_valid_url(url_input):
                    state.url = url_input
                    error_msg = ""
                    state.stage = 1

                else:
                    error_msg = (
                        "Geçerli bir URL "
                        "girilmedi!"
                    )

            # =========================================================
            # STAGE 1: PROFİL
            # =========================================================

            elif state.stage == 1:

                options = [
                    "Video",
                    "Ses",
                    "Playlist",
                ]

                key = read_key()

                if key == "up":
                    state.profile_cursor = (
                        state.profile_cursor - 1
                    ) % len(options)

                    render_ui(
                        state,
                        clear=False,
                    )

                elif key == "down":
                    state.profile_cursor = (
                        state.profile_cursor + 1
                    ) % len(options)

                    render_ui(
                        state,
                        clear=False,
                    )

                elif key == "enter":
                    state.profile = (
                        options[
                            state.profile_cursor
                        ]
                    )

                    if state.profile == "Video":
                        state.resolution_options = (
                            fetch_resolutions_from_core(
                                state.url
                            )
                        )

                        state.resolution_cursor = 0
                        state.resolution = ""
                        state.stage = 2

                    else:
                        state.resolution = "-"
                        state.stage = 3

                elif key == "esc":
                    state.profile = ""
                    state.stage = 0

            # =========================================================
            # STAGE 2: ÇÖZÜNÜRLÜK
            # =========================================================

            elif state.stage == 2:

                key = read_key()

                if key == "up":
                    options = (
                        state.resolution_options
                        or []
                    )

                    if options:
                        state.resolution_cursor = (
                            state.resolution_cursor - 1
                        ) % len(options)

                    render_ui(
                        state,
                        clear=False,
                    )

                elif key == "down":
                    options = (
                        state.resolution_options
                        or []
                    )

                    if options:
                        state.resolution_cursor = (
                            state.resolution_cursor + 1
                        ) % len(options)

                    render_ui(
                        state,
                        clear=False,
                    )

                elif key == "enter":
                    options = (
                        state.resolution_options
                        or []
                    )

                    if options:
                        state.resolution = (
                            options[
                                state.resolution_cursor
                            ]
                        )

                        state.stage = 3

                elif key == "esc":
                    state.resolution = ""
                    state.stage = 1

            # =========================================================
            # STAGE 3: İNDİRME DİZİNİ
            # =========================================================

            elif state.stage == 3:

                initial_path = (
                    state.download_dir
                    if state.download_dir
                    else default_download_dir
                )

                dir_input = filesystem_dialog(
                    initial_path,
                    mode="folder",
                )

                if dir_input is None:

                    if state.profile == "Video":
                        state.stage = 2

                    else:
                        state.stage = 1

                else:
                    dir_input = dir_input.strip()

                    if dir_input:
                        state.download_dir = dir_input

                        error_msg = ""
                        state.stage = 4

                    else:
                        error_msg = (
                            "İndirme dizini "
                            "boş bırakılamaz!"
                        )

            # =========================================================
            # STAGE 4: ÇEREZ
            # =========================================================

            elif state.stage == 4:

                options = [
                    "Çerez yok",
                    "Firefox",
                    "Çerez dosyası",
                ]

                key = read_key()

                if key == "up":
                    state.cookie_cursor = (
                        state.cookie_cursor - 1
                    ) % len(options)

                    render_ui(
                        state,
                        clear=False,
                    )

                elif key == "down":
                    state.cookie_cursor = (
                        state.cookie_cursor + 1
                    ) % len(options)

                    render_ui(
                        state,
                        clear=False,
                    )

                elif key == "enter":
                    selected = (
                        options[
                            state.cookie_cursor
                        ]
                    )

                    state.cookie_mode = selected
                    state.cookie_value = ""

                    if selected == "Çerez dosyası":
                        state.stage = 5

                    else:
                        state.stage = 6

                elif key.lower() == "w":
                    webbrowser.open(
                        COOKIE_EXPORTER_URL
                    )

                elif key == "esc":
                    state.cookie_mode = "Çerez yok"
                    state.cookie_value = ""
                    state.stage = 3

            # =========================================================
            # STAGE 5: ÇEREZ DOSYASI
            # =========================================================

            elif state.stage == 5:

                initial_file_dir = str(
                    Path(os.environ["USERPROFILE"]) / "Downloads"
                )

                file_path = filesystem_dialog(
                    initial_file_dir,
                    mode="file",
                )

                if file_path is None:
                    state.cookie_value = ""
                    state.stage = 4

                else:
                    normalized_path = (
                        os.path.abspath(
                            os.path.expanduser(
                                file_path.strip()
                            )
                        )
                    )

                    if os.path.isfile(
                        normalized_path
                    ):
                        state.cookie_value = (
                            normalized_path
                        )

                        error_msg = ""
                        state.stage = 6

                    else:
                        error_msg = (
                            "Geçersiz veya "
                            "bulunamayan "
                            "dosya yolu!"
                        )

            # =========================================================
            # STAGE 6: ÖZET VE ONAY
            # =========================================================

            elif state.stage == 6:

                key = read_key()

                if key == "enter":
                    run_download_process(
                        state
                    )

                    state = CLIState()
                    last_stage = -1
                    error_msg = ""

                elif key == "esc":
                    state.stage = 4

    except KeyboardInterrupt:
        clear_screen()

        print(
            "İşlem kullanıcı tarafından "
            "iptal edildi. Çıkılıyor..."
        )

    finally:
        show_cursor()


if __name__ == "__main__":
    if (
        os.name == "nt"
        and os.environ.get(CLI_CHILD_ENV) != "1"
    ):
        launch_application_console()

    else:
        apply_console_settings()
        main()