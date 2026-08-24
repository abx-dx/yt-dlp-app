from __future__ import annotations

from .profiles import DOWNLOAD_DIR, Profile
from .output import build_output
from .playlist_info import (
    PlaylistInfo,
    get_playlist_info,
)
from .tools import Tools


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

    base = DOWNLOAD_DIR

    if output_dir:
        base = output_dir.replace("\\", "/")

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

        # meta_date mevcut davranışını korur.
        "--parse-metadata",
        "%(release_year,release_date,upload_date)s:%(meta_date)s",
    ]

    # YT Music albüm yılı varsa birincil kaynak.
    #
    # Yoksa bu argümanı eklemiyoruz ve profiles.py'deki
    # mevcut release_year -> upload_year fallback'i çalışıyor.
    if info.release_year is not None:
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

    # Normal playlistte mevcut davranışı koruyoruz.
    # Entry-başına YT Music yıl çözümlemesi ayrı katmanda
    # yapılacak; burada mevcut fallback kaldırılmıyor.
    args = [
        "--parse-metadata",
        "%(release_year,release_date,upload_date)s:%(meta_date)s",

        "--parse-metadata",
        "%(release_year,upload_year)s:%(meta_year)s",
    ]

    return output, args