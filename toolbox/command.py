from __future__ import annotations

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
    "--progress",
    "--no-quiet",
    "--retries", "infinite",
    "--fragment-retries", "infinite",
    "--encoding", "utf-8",
    "--concurrent-fragments", "16",
]


def build_command(
    tools: Tools,
    profile: Profile,
    url: str,
    output_dir: str | None = None,
    use_cookies: bool = False,
    max_resolution: str | None = None, # <-- Yeni parametre
) -> list[str]:

    cmd = [str(tools.ytdlp)]
    cmd.extend(cookie_args(use_cookies))
    cmd.extend(COMMON_ARGS)

    cmd.extend([
        "--print",
        (
            "after_move:"
            "FILE_DONE|%(id)s|%(format_id)s|%(vcodec)s|%(acodec)s|"
            "%(resolution)s|%(vbr)s|%(abr)s|%(filepath)s"
        ),
    ])

    if profile.playlist:
        cmd.append("--yes-playlist")

    # Profil video ise kullanıcının seçtiği max_resolution'a göre format oluştur
    selected_format = profile.format
    if profile.name == "video" and max_resolution:
        selected_format = build_video_format(max_resolution)

    cmd.extend([
        "-f",
        selected_format,
    ])

    output, extra_args = resolve_profile(
        tools,
        profile,
        url,
        output_dir,
        use_cookies,
    )

    cmd.extend(profile.args)
    cmd.extend(extra_args)
    cmd.extend(["-o", output])
    cmd.append(url)

    return cmd