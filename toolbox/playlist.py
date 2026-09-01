from __future__ import annotations

from .output import build_output
from .playlist_info import (
    PlaylistInfo,
    get_playlist_info,
)
from .tools import Tools
from .profiles import Profile


def resolve_profile(
    tools: Tools,
    profile: Profile,
    url: str,
    output_dir: str | None,
    use_cookies: bool,
) -> tuple[str, list[str]]:

    if profile.name != "playlist":
        return build_output(profile, output_dir), []

    info = get_playlist_info(
        tools,
        url,
        use_cookies,
    )

    if info.is_album:
        return resolve_album(
            info,
            output_dir,
        )

    return resolve_playlist(
        profile,
        output_dir,
    )


def resolve_album(
    info: PlaylistInfo,
    output_dir: str | None,
) -> tuple[str, list[str]]:

    base = (
        output_dir.replace("\\", "/")
        if output_dir
        else "."
    )

    output = (
        f"{base}/"
        f"{info.artist} - {info.album}/"
        "%(artist)s - %(playlist_index)s - %(title,track)s.%(ext)s"
    )

    args = [
        "--parse-metadata",
        "%(playlist_index)s:%(meta_track)s",

        "--parse-metadata",
        f"{info.playlist_count}:%(meta_tracktotal)s",

        "--parse-metadata",
        "%(release_year,release_date,upload_date)s:%(meta_date)s",
    ]

    if info.release_year:
        args.extend(
            [
                "--parse-metadata",
                f"{info.release_year}:%(meta_year)s",
            ]
        )

    return output, args


def resolve_playlist(
    profile: Profile,
    output_dir: str | None,
) -> tuple[str, list[str]]:

    output = build_output(
        profile,
        output_dir,
    )

    args = [
        "--parse-metadata",
        "%(release_year,release_date,upload_date)s:%(meta_date)s",

        "--parse-metadata",
        "%(release_year,upload_year)s:%(meta_year)s",
    ]

    return output, args