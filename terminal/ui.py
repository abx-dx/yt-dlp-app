from __future__ import annotations

from pathlib import Path
from typing import List

from terminal.input import clear_screen, hide_cursor


SEPARATOR = "-" * 50
APP_NAME = "Video / Ses / Playlist İndirici (CLI)"
APP_VERSION = "1.0"


def render_ui(
    state,
    error_msg: str = "",
    clear: bool = True,
) -> None:
    """Aktif stage'i tek bir ayırıcıyla birlikte çizer."""

    lines: List[str] = [
        APP_NAME,
        APP_VERSION,
        SEPARATOR,
    ]

    if state.stage > 0 and state.url:
        lines.append(f"URL            : {state.url}")

    if state.stage > 1 and state.profile:
        lines.append(f"Profil         : {state.profile}")

    if (
        state.stage > 2
        and state.profile == "Video"
        and state.resolution
    ):
        lines.append(
            f"Çözünürlük     : {state.resolution}"
        )

    if state.stage > 3 and state.download_dir:
        lines.append(
            f"İndirme Dizini : {state.download_dir}"
        )

    if state.stage > 4:
        cookie_display = state.cookie_mode

        if (
            state.cookie_mode == "Çerez dosyası"
            and state.cookie_value
        ):
            cookie_display += (
                f" ({Path(state.cookie_value).name})"
            )

        lines.append(
            f"Çerez          : {cookie_display}"
        )

    if (
        state.stage > 5
        and state.cookie_mode == "Çerez dosyası"
        and state.cookie_value
    ):
        lines.append(
            f"Çerez Dosyası  : {state.cookie_value}"
        )

    if state.stage > 0:
        lines.append(SEPARATOR)

    if state.stage == 0:
        if error_msg:
            lines.append(f"Hata: {error_msg}")
            lines.append("")

        lines.append("URL girin:")

    elif state.stage == 1:
        options = [
            "Video",
            "Ses",
            "Playlist",
        ]

        lines.append("Profil Seçin:")
        lines.append("")

        for idx, option in enumerate(options):
            prefix = ">" if idx == state.profile_cursor else " "
            lines.append(f" {prefix} {option}")

        lines.append("")
        lines.append(
            "[↑/↓] Seç     "
            "[Enter] Onayla     "
            "[Esc] Çıkış"
        )

    elif state.stage == 2:
        lines.append(
            "Çözünürlük Seçin (Motordan Çekildi):"
        )
        lines.append("")

        for idx, option in enumerate(
            state.resolution_options or []
        ):
            prefix = (
                ">"
                if idx == state.resolution_cursor
                else " "
            )
            lines.append(f" {prefix} {option}")

        lines.append("")
        lines.append(
            "[↑/↓] Seç     "
            "[Enter] Onayla     "
            "[Esc] Geri"
        )

    elif state.stage == 3:
        if error_msg:
            lines.append(f"Hata: {error_msg}")
            lines.append("")

        lines.append("İndirme Dizini:")

    elif state.stage == 4:
        options = [
            "Çerez yok",
            "Firefox",
            "Çerez dosyası",
        ]

        lines.append("Çerez (Cookie) Kaynağı Seçin:")
        lines.append("")

        for idx, option in enumerate(options):
            prefix = (
                ">"
                if idx == state.cookie_cursor
                else " "
            )
            lines.append(f" {prefix} {option}")

        lines.append("")
        lines.append(
            "Yalnızca Firefox üzerinden çerez tespiti yapılabilir. "
            "Diğer tarayıcılarda Cookie Exporter eklentisi ile"
        )
        lines.append(
            "indirilen dosyayı çerez dosyası olarak yükleyebilirsiniz."
        )

        lines.append("")
        lines.append(
            "[↑/↓] Seç     "
            "[Enter] Onayla     "
            "[W] Web Sayfası     "
            "[Esc] Geri"
        )

    elif state.stage == 5:
        if error_msg:
            lines.append(f"Hata: {error_msg}")
            lines.append("")

        lines.append("Çerez Dosyası:")
        lines.append("")
        lines.append(
            "[Enter] Onayla     "
            "[Esc] Geri"
        )

    elif state.stage == 6:
        lines.append(
            "İndirme İşlemi Başlatılmaya Hazır."
        )
        lines.append("")
        lines.append(
            "[Enter] Başlat     "
            "[Esc] Yapılandırmaya Dön"
        )

    output = "\n".join(lines)

    if clear:
        clear_screen()
        hide_cursor()

        print(
            output,
            end="",
            flush=True,
        )

        return

    print(
        "\033[H",
        end="",
        flush=True,
    )

    for index, line in enumerate(lines):
        print(
            f"\033[2K{line}",
            end="",
            flush=True,
        )

        if index < len(lines) - 1:
            print(
                "\n",
                end="",
                flush=True,
            )

    print(
        "\033[J",
        end="",
        flush=True,
    )


def draw_progress_bar(
    percent: float,
    width: int = 30,
) -> str:
    """ASCII ilerleme çubuğu oluşturur."""

    percent = max(
        0.0,
        min(
            100.0,
            percent,
        ),
    )

    completed = int(
        width * (percent / 100.0)
    )

    bar = (
        "█" * completed
        + "-" * (width - completed)
    )

    return f"[{bar}] %{percent:.1f}"