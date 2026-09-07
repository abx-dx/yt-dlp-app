from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import List


SEPARATOR = "-" * 50


def show_cursor() -> None:
    """Terminal imlecini görünür yapar."""

    print(
        "\033[?25h",
        end="",
        flush=True,
    )


def hide_cursor() -> None:
    """Terminal imlecini gizler."""

    print(
        "\033[?25l",
        end="",
        flush=True,
    )


def clear_screen() -> None:
    """Ekranı tamamen temizler ve imleci en üste taşır."""

    print(
        "\033[H\033[2J\033[3J",
        end="",
        flush=True,
    )


def get_terminal_width() -> int:
    """Terminalin sütun sayısını güvenli şekilde alır."""

    try:
        return os.get_terminal_size().columns

    except OSError:
        return 80


def read_key() -> str:
    """Tek bir terminal tuşunu platforma göre okur."""

    # ------------------------------------------------------------------
    # Windows
    # ------------------------------------------------------------------

    if os.name == "nt":
        import msvcrt

        key = msvcrt.getwch()

        if key == "\x03":
            raise KeyboardInterrupt

        if key in ("\x00", "\xe0"):
            key = msvcrt.getwch()

            if key == "R":  # Shift+Insert
                return "mouse_right"

            return {
                "H": "up",
                "P": "down",
                "K": "left",
                "M": "right",
                "S": "delete",
                "I": "page_up",
                "Q": "page_down",
            }.get(key, "")

        return {
            "\r": "enter",
            "\x1b": "esc",
            "\x08": "backspace",
        }.get(key, key)

    # ------------------------------------------------------------------
    # Linux / macOS / POSIX
    # ------------------------------------------------------------------

    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)

        if key == "\x03":
            raise KeyboardInterrupt

        if key == "\x1b":
            if select.select(
                [sys.stdin],
                [],
                [],
                0.05,
            )[0]:
                next_key = sys.stdin.read(1)

                if next_key == "[":
                    if select.select(
                        [sys.stdin],
                        [],
                        [],
                        0.05,
                    )[0]:
                        final_key = sys.stdin.read(1)

                        return {
                            "A": "up",
                            "B": "down",
                            "C": "right",
                            "D": "left",
                        }.get(final_key, "")

            return "esc"

        return {
            "\r": "enter",
            "\n": "enter",
            "\x7f": "backspace",
        }.get(key, key)

    finally:
        termios.tcsetattr(
            fd,
            termios.TCSADRAIN,
            old_settings,
        )


def editable_input(
    prompt: str,
    initial_text: str = "",
) -> str | None:
    """Tek satır, yatay kaydırmalı metin editörü."""

    buffer = list(initial_text)
    cursor_pos = len(buffer)

    show_cursor()

    while True:
        term_width = get_terminal_width()

        max_input_len = max(
            10,
            term_width - len(prompt) - 3,
        )

        if cursor_pos < max_input_len:
            view_start = 0

        else:
            view_start = (
                cursor_pos
                - max_input_len
                + 1
            )

        view_buffer = buffer[
            view_start:
            view_start + max_input_len
        ]

        visible_text = "".join(
            view_buffer
        )

        print(
            f"\r\033[2K"
            f"{prompt}{visible_text}",
            end="",
            flush=True,
        )

        relative_cursor = (
            cursor_pos - view_start
        )

        offset = (
            len(visible_text)
            - relative_cursor
        )

        if offset > 0:
            print(
                f"\033[{offset}D",
                end="",
                flush=True,
            )

        key = read_key()

        if key == "enter":
            hide_cursor()
            print()

            return "".join(buffer)

        if key == "esc":
            hide_cursor()
            print()

            return None

        if key == "mouse_right":
            if os.name == "nt":
                ctypes.windll.user32.mouse_event(
                    0x0008,
                    0,
                    0,
                    0,
                    0,
                )

                ctypes.windll.user32.mouse_event(
                    0x0010,
                    0,
                    0,
                    0,
                    0,
                )

        elif key == "backspace":
            if cursor_pos > 0:
                buffer.pop(cursor_pos - 1)
                cursor_pos -= 1

        elif key == "left":
            if cursor_pos > 0:
                cursor_pos -= 1

        elif key == "right":
            if cursor_pos < len(buffer):
                cursor_pos += 1

        elif key == "delete":
            if cursor_pos < len(buffer):
                buffer.pop(cursor_pos)

        elif (
            len(key) == 1
            and key.isprintable()
        ):
            buffer.insert(
                cursor_pos,
                key,
            )

            cursor_pos += 1


def filesystem_dialog(
    initial_path: str,
    mode: str,
    extensions: tuple[str, ...] = (),
) -> str | None:
    """
    Hafif terminal tabanlı dosya / klasör gezgini.

    mode:
        "folder" -> klasör seçimi
        "file"   -> dosya seçimi

    Tuşlar:
        ↑ / ↓             : seçim
        PageUp / PageDown : sayfa
        Enter             : klasöre gir / dosyayı seç
        →                 : klasöre gir
        ← / Backspace     : üst dizin
        S                 : mevcut klasörü seç
        Esc               : iptal
    """

    if mode not in ("folder", "file"):
        raise ValueError(
            f"Geçersiz dosya sistemi modu: {mode}"
        )

    try:
        current_path = Path(
            os.path.expanduser(
                initial_path
            )
        ).resolve()

    except OSError:
        current_path = Path.cwd().resolve()

    if mode == "folder":

        if not current_path.exists():
            current_path.mkdir(
                parents=True,
                exist_ok=True,
            )

        if not current_path.is_dir():
            current_path = (
                current_path.parent
            )

    else:

        if not current_path.exists():
            current_path = (
                current_path.parent
            )

        if current_path.is_file():
            current_path = (
                current_path.parent
            )

    cursor = 0
    page = 0
    first_render = True

    PAGE_SIZE = 12

    while True:

        # --------------------------------------------------------------
        # Klasör içeriğini oku
        # --------------------------------------------------------------

        try:
            entries = []

            for entry in current_path.iterdir():

                try:
                    if entry.is_dir():
                        entries.append(entry)

                    elif (
                        mode == "file"
                        and entry.is_file()
                    ):
                        if (
                            not extensions
                            or entry.suffix.lower()
                            in extensions
                        ):
                            entries.append(entry)

                except OSError:
                    continue

            entries.sort(
                key=lambda item: (
                    not item.is_dir(),
                    item.name.casefold(),
                )
            )

        except OSError:
            entries = []

        # --------------------------------------------------------------
        # Sayfa hesapla
        # --------------------------------------------------------------

        if entries:
            total_pages = (
                (len(entries) + PAGE_SIZE - 1)
                // PAGE_SIZE
            )

            page = min(
                page,
                total_pages - 1,
            )

            page_start = (
                page * PAGE_SIZE
            )

            page_end = min(
                page_start + PAGE_SIZE,
                len(entries),
            )

            page_entries = entries[
                page_start:page_end
            ]

            cursor %= len(page_entries)

        else:
            total_pages = 1
            page = 0
            page_entries = []
            cursor = 0

        # --------------------------------------------------------------
        # Ekranı çiz
        # --------------------------------------------------------------

        lines: List[str] = []

        if mode == "folder":
            lines.append("Klasör Seç")

        else:
            lines.append("Dosya Seç")

        lines.append(SEPARATOR)

        lines.append(
            f"Konum: {current_path}"
        )

        lines.append(SEPARATOR)
        lines.append("")

        if not entries:

            lines.append(
                "  Bu klasörde gösterilecek "
                "öğe yok."
            )

        else:

            for index, entry in enumerate(
                page_entries
            ):
                prefix = (
                    ">"
                    if index == cursor
                    else " "
                )

                icon = (
                    "[+]"
                    if entry.is_dir()
                    else "[ ]"
                )

                lines.append(
                    f" {prefix} {icon} "
                    f"{entry.name}"
                )

        lines.append("")
        lines.append(SEPARATOR)

        lines.append(
            f"Sayfa {page + 1} / {total_pages}"
        )

        lines.append(SEPARATOR)

        if mode == "folder":
            lines.append(
                "[↑/↓] Seç   "
                "[PgUp/PgDn] Sayfa   "
                "[Enter] Aç   "
                "[S] Klasörü Seç"
            )
            lines.append(
                "[←/Backspace] Üst   "
                "[Esc] İptal"
            )

        else:
            lines.append(
                "[↑/↓] Seç   "
                "[PgUp/PgDn] Sayfa   "
                "[Enter] Aç/Seç"
            )
            lines.append(
                "[←/Backspace] Üst   "
                "[Esc] İptal"
            )

        # --------------------------------------------------------------
        # İlk çizim
        # --------------------------------------------------------------

        if first_render:
            clear_screen()
            hide_cursor()

            print(
                "\n".join(lines),
                end="",
                flush=True,
            )

            first_render = False

        # --------------------------------------------------------------
        # Sonraki çizimler
        # --------------------------------------------------------------

        else:
            print(
                "\033[H",
                end="",
                flush=True,
            )

            for index, line in enumerate(
                lines
            ):
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

        # --------------------------------------------------------------
        # Tuş oku
        # --------------------------------------------------------------

        key = read_key()

        # --------------------------------------------------------------
        # Esc
        # --------------------------------------------------------------

        if key == "esc":
            show_cursor()
            return None

        # --------------------------------------------------------------
        # Yukarı
        # --------------------------------------------------------------

        if key == "up":

            if page_entries:
                cursor = (
                    cursor - 1
                ) % len(page_entries)

            continue

        # --------------------------------------------------------------
        # Aşağı
        # --------------------------------------------------------------

        if key == "down":

            if page_entries:
                cursor = (
                    cursor + 1
                ) % len(page_entries)

            continue

        # --------------------------------------------------------------
        # Önceki sayfa
        # --------------------------------------------------------------

        if key == "page_up":

            if page > 0:
                page -= 1
                cursor = 0

            continue

        # --------------------------------------------------------------
        # Sonraki sayfa
        # --------------------------------------------------------------

        if key == "page_down":

            if page < total_pages - 1:
                page += 1
                cursor = 0

            continue

        # --------------------------------------------------------------
        # Sol / Backspace → üst klasör
        # --------------------------------------------------------------

        if key in (
            "left",
            "backspace",
        ):

            parent = current_path.parent

            if parent != current_path:
                current_path = parent
                cursor = 0
                page = 0

            continue

        # --------------------------------------------------------------
        # Sağ → klasöre gir
        # --------------------------------------------------------------

        if key == "right":

            if page_entries:
                selected = page_entries[cursor]

                if selected.is_dir():
                    current_path = selected
                    cursor = 0
                    page = 0

            continue

        # --------------------------------------------------------------
        # Enter
        # --------------------------------------------------------------

        if key == "enter":

            if not page_entries:
                continue

            selected = page_entries[cursor]

            if selected.is_dir():

                current_path = selected
                cursor = 0
                page = 0

            elif mode == "file":

                show_cursor()

                return str(
                    selected.resolve()
                )

            continue

        # --------------------------------------------------------------
        # S → mevcut klasörü seç
        # --------------------------------------------------------------

        if (
            mode == "folder"
            and key.lower() == "s"
        ):
            show_cursor()

            return str(
                current_path.resolve()
            )