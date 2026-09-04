from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Profile:
    name: str
    format: str
    output: str
    playlist: bool = False
    args: list[str] = field(default_factory=list)


RESOLUTIONS = [
    "En İyi",
    "8K (4320p)",
    "4K (2160p)",
    "2K (1440p)",
    "1080p",
    "720p",
    "480p",
    "360p",
    "240p",
    "144p",
]


AUDIO_FORMAT = (
    "774"
    "/141"
    "/bestaudio[acodec=opus]"
    "/bestaudio"
)


def build_video_format(
    max_res: str | None = None,
) -> str:

    if not max_res or max_res == "En İyi":
        return (
            "bestvideo+774"
            "/bestvideo+141"
            "/bestvideo+bestaudio[acodec=opus]"
            "/bestvideo+bestaudio"
            "/best"
        )

    height = (
        max_res
        .split("(")[-1]
        .replace("p)", "")
        .replace("p", "")
        .strip()
    )

    if not height.isdigit():
        return (
            "bestvideo+774"
            "/bestvideo+141"
            "/bestvideo+bestaudio[acodec=opus]"
            "/bestvideo+bestaudio"
            "/best"
        )

    return (
        f"bestvideo[height<={height}]+774"
        f"/bestvideo[height<={height}]+141"
        f"/bestvideo[height<={height}]+bestaudio[acodec=opus]"
        f"/bestvideo[height<={height}]+bestaudio"
        f"/best[height<={height}]"
        f"/best"
    )


PROFILES: dict[str, Profile] = {

    "video": Profile(
        name="video",
        format=build_video_format(),
        output="%(title)s.%(ext)s",
        args=[
            "--merge-output-format",
            "mkv",

            # Video yılı = YouTube yayın yılı.
            "--parse-metadata",
            "%(upload_date)s:%(meta_date)s",

            "--parse-metadata",
            "%(upload_year)s:%(meta_year)s",

            "--embed-thumbnail",
            "--convert-thumbnails",
            "jpg",
        ],
    ),

    "audio": Profile(
        name="audio",
        format=AUDIO_FORMAT,
        output="%(artist,uploader)s - %(title)s.%(ext)s",
        args=[
            "-x",

            "--embed-metadata",

            # Mevcut tarih fallback'i.
            "--parse-metadata",
            "%(release_year,release_date,upload_date)s:%(meta_date)s",

            # YT Music yılı verilmemişse mevcut fallback.
            "--parse-metadata",
            "%(release_year,upload_year)s:%(meta_year)s",

            "--embed-thumbnail",
            "--convert-thumbnails",
            "jpg",

            "--ppa",
            "ThumbnailsConvertor+ffmpeg:-vf crop=ih:ih",
        ],
    ),

    "playlist": Profile(
        name="playlist",
        format=AUDIO_FORMAT,
        playlist=True,
        output=(
            "%(playlist_title)s/"
            "%(playlist_index)s - %(title)s.%(ext)s"
        ),
        args=[
            "--yes-playlist",
            "-x",

            "--embed-metadata",
            "--embed-thumbnail",
            "--convert-thumbnails",
            "jpg",

            "--ppa",
            "ThumbnailsConvertor+ffmpeg:-vf crop=ih:ih",
        ],
    ),
}


def get_profile(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(
            f"Geçersiz profil: {name}"
        ) from exc