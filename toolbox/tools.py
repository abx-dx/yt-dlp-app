from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


def get_subprocess_args() -> dict:
    """Windows ortamında harici CLI pencerelerinin açılmasını engeller."""
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        return {
            "creationflags": subprocess.CREATE_NO_WINDOW,
            "startupinfo": startupinfo,
        }
    return {}


@dataclass(frozen=True, slots=True)
class Tools:
    app_dir: Path
    ytdlp: Path
    ffmpeg: Path
    ffprobe: Path
    deno: Path  # JS Challenger denetimi için korundu

    @classmethod
    def discover(cls) -> "Tools":

        if getattr(sys, "frozen", False):
            app_dir = Path(sys.executable).resolve().parent
        else:
            app_dir = Path(__file__).resolve().parent.parent

        bin_dir = app_dir / "bin"

        exe = ".exe" if os.name == "nt" else ""

        return cls(
            app_dir=app_dir,
            ytdlp=bin_dir / f"yt-dlp{exe}",
            ffmpeg=bin_dir / f"ffmpeg{exe}",
            ffprobe=bin_dir / f"ffprobe{exe}",
            deno=bin_dir / f"deno{exe}",
        )

    def env(self) -> dict[str, str]:

        env = os.environ.copy()
        
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        # bin/ klasörünü PATH'e ekleyerek yt-dlp'nin deno ve ffmpeg'i otomatik bulmasını sağlıyoruz
        env["PATH"] = (
            f"{self.ytdlp.parent}"
            + os.pathsep
            + env.get("PATH", "")
        )

        return env