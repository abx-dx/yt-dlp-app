from __future__ import annotations

import sys
import static_ffmpeg

# ffmpeg / ffprobe'u Python prosesinin PATH'ine ekle
static_ffmpeg.add_paths()

from .cookies import cookie_args
from .output import build_output
from .playlist import resolve_profile
from .profiles import Profile, build_video_format
from .tools import Tools


COMMON_ARGS = [
    "--continue",
    "--no-overwrites",
    "--windows-filenames",
    "--newline",
    "--proxy",
    "",
    "--progress",
    "--no-quiet",
    "--retries",
    "inf",
    "--fragment-retries",
    "inf",
    "--encoding",
    "utf-8",
    "--concurrent-fragments",
    "16",
]


def build_command(
    tools: Tools,
    profile: Profile,
    url: str,
    output_dir: str | None = None,
    use_cookies: bool = False,
    max_resolution: str | None = None,
    final_output_dir: str | None = None,
) -> list[str]:

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
    ]

    # --------------------------------------------------------------
    # Cookies
    # --------------------------------------------------------------

    cmd.extend(
        cookie_args(use_cookies)
    )

    # --------------------------------------------------------------
    # Ortak yt-dlp seçenekleri
    # --------------------------------------------------------------

    cmd.extend(COMMON_ARGS)

    # --------------------------------------------------------------
    # JavaScript runtime
    # --------------------------------------------------------------

    cmd.extend(
        [
            "--js-runtimes",
            f"deno:{tools.deno}",
            "--remote-components",
            "ejs:github",
        ]
    )

    # --------------------------------------------------------------
    # Dosya tamamlandığında runner tarafından yakalanacak event
    # --------------------------------------------------------------

    cmd.extend(
        [
            "--print",
            (
                "after_move:"
                "FILE_DONE|%(id)s|%(format_id)s|%(vcodec)s|"
                "%(acodec)s|%(resolution)s|%(vbr)s|%(abr)s|"
                "%(filepath)s"
            ),
        ]
    )

    # --------------------------------------------------------------
    # Playlist
    # --------------------------------------------------------------

    if profile.playlist:
        cmd.append(
            "--yes-playlist"
        )

    # --------------------------------------------------------------
    # Format
    # --------------------------------------------------------------

    selected_format = profile.format

    if (
        profile.name == "video"
        and max_resolution
    ):
        selected_format = build_video_format(
            max_resolution
        )

    cmd.extend(
        [
            "-f",
            selected_format,
        ]
    )

    # --------------------------------------------------------------
    # Profil output / extra args
    # --------------------------------------------------------------

    output, extra_args = resolve_profile(
        tools,
        profile,
        url,
        output_dir,
        use_cookies,
    )

    cmd.extend(
        profile.args
    )

    cmd.extend(
        extra_args
    )

    # --------------------------------------------------------------
    # Output
    # --------------------------------------------------------------

    cmd.extend(
        [
            "-o",
            output,
        ]
    )

    # --------------------------------------------------------------
    # URL en son argüman
    # --------------------------------------------------------------

    cmd.append(url)

    return cmd