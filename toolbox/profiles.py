# profiles.py

from __future__ import annotations

from dataclasses import dataclass, field


DOWNLOAD_DIR = "./indirilenler"


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

def build_video_format(max_res: str | None = None) -> str:
    """
    Sesi her zaman 'bestaudio[acodec=opus]/bestaudio' tutar.
    Videoyu ise kullanıcının seçtiği tavan çözünürlük (veya altı) olarak sınırlar.
    """
    if not max_res or max_res == "En İyi":
        return "bestvideo+bestaudio[acodec=opus]/bestaudio/best"

    height = extract_height(max_res)

    if not height.isdigit():
        return "bestvideo+bestaudio[acodec=opus]/bestaudio/best"

    return (
        f"bestvideo[height<={height}]"
        f"+bestaudio[acodec=opus]"
        f"/bestvideo[height<={height}]"
        f"+bestaudio"
        f"/best[height<={height}]"
        f"/best"
    )


def extract_height(text: str) -> str:
    return (
        text
        .split("(")[-1]
        .replace("p)", "")
        .replace("p", "")
        .strip()
    )


PROFILES: dict[str, Profile] = {

    "video": Profile(
        name="video",
        format=build_video_format(),
        output=f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        args=[
            "--merge-output-format",
            "mkv",
            "--parse-metadata", "%(upload_date)s:%(meta_date)s",
            "--parse-metadata", "%(upload_year)s:%(meta_year)s",
            "--embed-thumbnail",
            "--convert-thumbnails", "jpg",
        ],
    ),

    "audio": Profile(
        name="audio",
        format="bestaudio[acodec=opus]/bestaudio",
        output=f"{DOWNLOAD_DIR}/%(artist,uploader)s - %(title)s.%(ext)s",
        args=[
            "-x",
            # Prefer native Opus streams and do a lossless remux to an .opus container.
            # Format selector uses: bestaudio[acodec=opus]/bestaudio so yt-dlp will
            # pick native Opus when available; --remux-video opus + -x does a lossless
            # remux instead of forcing an ffmpeg re-encode (which --audio-format opus would do).
            "--remux-video", "opus",

            "--embed-metadata",

            "--parse-metadata",
            "%(release_year,release_date,upload_date)s:%(meta_date)s",

            "--parse-metadata",
            "%(release_year,upload_year)s:%(meta_year)s",

            "--embed-thumbnail",
            "--convert-thumbnails", "jpg",

            "--ppa",
            "ThumbnailsConvertor+ffmpeg:-vf crop=ih:ih",
        ],
    ),

    "playlist": Profile(
        name="playlist",
        format="bestaudio[acodec=opus]/bestaudio",
        playlist=True,
        output=(
            f"{DOWNLOAD_DIR}/"
            "%(playlist_title)s/"
            "%(playlist_index)s - %(title)s.%(ext)s"
        ),
        args=[
            "--yes-playlist",
            "-x",
            # Prefer native Opus streams and do a lossless remux to an .opus container.
            # Format selector uses: bestaudio[acodec=opus]/bestaudio so yt-dlp will
            # pick native Opus when available; --remux-video opus + -x does a lossless
            # remux instead of forcing an ffmpeg re-encode (which --audio-format opus would do).
            "--remux-video", "opus",
            "--embed-metadata",
            "--embed-thumbnail",
            "--convert-thumbnails", "jpg",
            "--ppa", "ThumbnailsConvertor+ffmpeg:-vf crop=ih:ih",
        ],
    ),
}


def get_profile(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"Geçersiz profil: {name}") from exc