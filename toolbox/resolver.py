from __future__ import annotations

import re

from yt_dlp import YoutubeDL


CANONICAL_PATTERN = re.compile(
    r'<link rel="canonical" href="https://music\.youtube\.com/watch\?v=([A-Za-z0-9_-]+)'
)


def resolve_music_url(
    url: str,
    ydl: YoutubeDL | None = None,
) -> str:

    video_id_match = re.search(
        r"[?&]v=([A-Za-z0-9_-]+)",
        url,
    )

    if not video_id_match:
        return url

    video_id = video_id_match.group(1)

    if ydl is None:
        return url

    try:
        response = ydl.urlopen(
            f"https://music.youtube.com/watch?v={video_id}"
        )

        html = response.read().decode(
            "utf-8",
            errors="replace",
        )

    except Exception:
        return url

    match = CANONICAL_PATTERN.search(html)

    if not match:
        return url

    resolved_id = match.group(1)

    return (
        f"https://music.youtube.com/watch?v={resolved_id}"
    )