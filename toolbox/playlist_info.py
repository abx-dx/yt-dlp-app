from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from .cookies import cookie_args
from .tools import Tools, get_subprocess_args


@dataclass(slots=True)
class PlaylistInfo:
    is_album: bool = False
    playlist_count: int = 0
    playlist_title: str = ""
    album: str = ""
    artist: str = ""
    
def get_playlist_info(
    tools: Tools,
    url: str,
    use_cookies: bool,
) -> PlaylistInfo:

    cmd = [
        str(tools.ytdlp),
        "--dump-single-json",
        "--playlist-items", "1",
    ]

    cmd.extend(cookie_args(use_cookies))
    cmd.append(url)

    # get_subprocess_args() eklenerek pencere açılması engellendi
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **get_subprocess_args(),
    )

    if result.returncode != 0:
        return PlaylistInfo()

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return PlaylistInfo()

    title = data.get("title") or ""

    entries = data.get("entries") or []
    first = entries[0] if entries else {}

    raw_album = first.get("album") or ""
    if not raw_album and title.startswith("Album - "):
        raw_album = title.replace("Album - ", "", 1)
    if not raw_album:
        raw_album = title or "Bilinmeyen Album"

    artist = (
        first.get("artist")
        or first.get("uploader")
        or data.get("uploader")
        or data.get("channel")
        or "Bilinmeyen Sanatci"
    )

    return PlaylistInfo(
        is_album=title.startswith("Album - "),
        playlist_count=data.get("playlist_count") or len(entries),
        playlist_title=title,
        album=raw_album,
        artist=artist,
    )