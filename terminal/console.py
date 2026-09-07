from __future__ import annotations

import ctypes
import os
import sys


# ----------------------------------------------------------------------
# WINDOWS ANSI / VT TERMINAL DESTEĞİ
# ----------------------------------------------------------------------

def enable_windows_vt() -> None:
    """Windows konsolunda ANSI / Virtual Terminal desteğini açar."""

    if os.name != "nt":
        return

    try:
        kernel32 = ctypes.windll.kernel32

        ENABLE_PROCESSED_OUTPUT = 0x0001
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        for handle_value in (-11, -12):
            handle = kernel32.GetStdHandle(
                handle_value
            )

            if handle in (0, -1):
                continue

            mode = ctypes.c_uint32()

            if not kernel32.GetConsoleMode(
                handle,
                ctypes.byref(mode),
            ):
                continue

            new_mode = (
                mode.value
                | ENABLE_PROCESSED_OUTPUT
                | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            )

            kernel32.SetConsoleMode(
                handle,
                new_mode,
            )

    except Exception:
        pass


# ----------------------------------------------------------------------
# İkinci PowerShell için Console API yapıları
# ----------------------------------------------------------------------

class COORD(ctypes.Structure):
    _fields_ = [
        ("X", ctypes.c_short),
        ("Y", ctypes.c_short),
    ]


class CONSOLE_FONT_INFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("nFont", ctypes.c_ulong),
        ("dwFontSize", COORD),
        ("FontFamily", ctypes.c_uint),
        ("FontWeight", ctypes.c_uint),
        (
            "FaceName",
            ctypes.c_wchar * 32,
        ),
    ]


def apply_console_settings() -> None:
    """
    Child PowerShell penceresine mevcut normal PowerShell
    görünümünü uygular.

    Referans:
        Font       : Consolas
        Font size  : 7 x 14
        FontFamily : 54
        FontWeight : 400
        Window     : 120 x 50
        Buffer     : 120 x 3000
        Colors     : DarkYellow / DarkMagenta
        Cursor     : 25
    """

    if os.name != "nt":
        return

    try:
        kernel32 = ctypes.windll.kernel32

        # --------------------------------------------------------------
        # Standart output handle
        # --------------------------------------------------------------

        stdout_handle = kernel32.GetStdHandle(
            -11
        )

        if stdout_handle in (0, -1):
            return

        # --------------------------------------------------------------
        # Font
        # --------------------------------------------------------------

        font = CONSOLE_FONT_INFOEX()

        font.cbSize = ctypes.sizeof(
            CONSOLE_FONT_INFOEX
        )

        if kernel32.GetCurrentConsoleFontEx(
            stdout_handle,
            False,
            ctypes.byref(font),
        ):
            font.dwFontSize.X = 7
            font.dwFontSize.Y = 14

            font.FontFamily = 54
            font.FontWeight = 400
            font.nFont = 0
            font.FaceName = "Consolas"

            kernel32.SetCurrentConsoleFontEx(
                stdout_handle,
                False,
                ctypes.byref(font),
            )

        # --------------------------------------------------------------
        # Console ekran bilgileri
        # --------------------------------------------------------------

        try:
            raw_output = sys.stdout

            buffer_size = COORD(
                120,
                3000,
            )

            kernel32.SetConsoleScreenBufferSize(
                stdout_handle,
                buffer_size,
            )

            class SMALL_RECT(ctypes.Structure):
                _fields_ = [
                    (
                        "Left",
                        ctypes.c_short,
                    ),
                    (
                        "Top",
                        ctypes.c_short,
                    ),
                    (
                        "Right",
                        ctypes.c_short,
                    ),
                    (
                        "Bottom",
                        ctypes.c_short,
                    ),
                ]

            window_rect = SMALL_RECT(
                0,
                0,
                119,
                49,
            )

            kernel32.SetConsoleWindowInfo(
                stdout_handle,
                True,
                ctypes.byref(window_rect),
            )

            del raw_output

        except Exception:
            pass

        # --------------------------------------------------------------
        # Cursor size
        # --------------------------------------------------------------

        class CONSOLE_CURSOR_INFO(ctypes.Structure):
            _fields_ = [
                (
                    "dwSize",
                    ctypes.c_ulong,
                ),
                (
                    "bVisible",
                    ctypes.c_bool,
                ),
            ]

        cursor_info = CONSOLE_CURSOR_INFO()

        if kernel32.GetConsoleCursorInfo(
            stdout_handle,
            ctypes.byref(cursor_info),
        ):
            cursor_info.dwSize = 25

            kernel32.SetConsoleCursorInfo(
                stdout_handle,
                ctypes.byref(cursor_info),
            )

        # --------------------------------------------------------------
        # Renkler
        #
        # DarkYellow = 6
        # DarkMagenta = 5
        #
        # Console attribute:
        #   background << 4 | foreground
        # --------------------------------------------------------------

        dark_yellow = 0x0006
        dark_magenta = 0x0005

        attributes = (
            dark_magenta << 4
        ) | dark_yellow

        kernel32.SetConsoleTextAttribute(
            stdout_handle,
            attributes,
        )

        # --------------------------------------------------------------
        # Output mode
        # --------------------------------------------------------------

        output_mode = ctypes.c_uint32()

        if kernel32.GetConsoleMode(
            stdout_handle,
            ctypes.byref(output_mode),
        ):
            ENABLE_PROCESSED_OUTPUT = 0x0001
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

            new_mode = (
                output_mode.value
                | ENABLE_PROCESSED_OUTPUT
                | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            )

            kernel32.SetConsoleMode(
                stdout_handle,
                new_mode,
            )

    except Exception:
        pass