# toolbox/parser.py

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from .metadata import format_file_done_report

DOWNLOAD_PERCENT_RE = re.compile(
    r"^\[download\]\s+(\d+(?:\.\d+)?)%\s+of.*?at\s+(.+?)\s+ETA\s+(.+)$"
)

PLAYLIST_COUNTER_RE = re.compile(
    r"^\[download\]\s+Downloading (?:item|video)\s+(\d+)\s+of\s+(\d+)"
)

DESTINATION_RE = re.compile(
    r"^\[(?:download|ExtractAudio|ffmpeg)\]\s+Destination:\s+(.+)$"
)

FILE_DONE_RE = re.compile(
    r"^FILE_DONE\|"
    r"([^|]+)\|"
    r"([^|]+)\|"
    r"([^|]+)\|"
    r"([^|]+)\|"
    r"([^|]+)\|"
    r"([^|]+)\|"
    r"([^|]+)\|"
    r"(.+)$"
)


@dataclass(slots=True)
class Event:
    pass


@dataclass(slots=True)
class ProgressEvent(Event):
    percent: float
    speed: str
    eta: str


@dataclass(slots=True)
class PlaylistEvent(Event):
    current: int
    total: int


@dataclass(slots=True)
class DestinationEvent(Event):
    path: Path


@dataclass(slots=True)
class FileDoneEvent(Event):
    video_id: str
    format_id: str
    vcodec: str
    acodec: str
    resolution: str
    vbr: str
    abr: str
    file_path: Path
    report: str = ""

    @property
    def file_name(self) -> str:
        return self.file_path.name


@dataclass(slots=True)
class WarningEvent(Event):
    text: str


@dataclass(slots=True)
class ErrorEvent(Event):
    text: str


class OutputParser:

    def __init__(self, profile_name: str, max_resolution: str | None = None):
        self.profile_name = profile_name
        self.max_resolution = max_resolution  # <-- Yeni
        self.current_file: Path | None = None


    def parse(self, line: str) -> Event | None:

        line = line.strip()

        if not line:
            return None

        if m := DOWNLOAD_PERCENT_RE.match(line):
            return ProgressEvent(
                percent=float(m.group(1)),
                speed=m.group(2),
                eta=m.group(3),
            )

        if m := PLAYLIST_COUNTER_RE.match(line):
            return PlaylistEvent(
                current=int(m.group(1)),
                total=int(m.group(2)),
            )

        if m := DESTINATION_RE.match(line):
            self.current_file = Path(m.group(1))
            return DestinationEvent(self.current_file)

        if m := FILE_DONE_RE.match(line):
            path = Path(m.group(8))

            return FileDoneEvent(
                video_id=m.group(1),
                format_id=m.group(2),
                vcodec=m.group(3),
                acodec=m.group(4),
                resolution=m.group(5),
                vbr=m.group(6),
                abr=m.group(7),
                file_path=path,
                report=format_file_done_report(
                    self.profile_name, 
                    line, 
                    self.max_resolution  # <-- Yeni
                ),
            )

        if "cookies" in line.lower():
            return WarningEvent(line)

        if line.startswith("WARNING:"):
            return WarningEvent(line)

        if line.startswith("ERROR:"):
            return ErrorEvent(line)

        return None