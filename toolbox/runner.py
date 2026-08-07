from __future__ import annotations

import subprocess
import sys
from typing import Iterator

from .command import build_command
from .parser import Event, OutputParser
from .profiles import Profile
from .tools import Tools, get_subprocess_args


class YtDlpRunner:

    def __init__(
        self,
        tools: Tools,
        profile: Profile,
        url: str,
        output_dir: str | None = None,
        use_cookies: bool = False,
        max_resolution: str | None = None,
    ):
        self.tools = tools
        self.profile = profile
        self.url = url
        self.output_dir = output_dir
        self.use_cookies = use_cookies
        self.max_resolution = max_resolution

        self.process: subprocess.Popen[str] | None = None

    def start(self) -> subprocess.Popen[str]:
        cmd = build_command(
            tools=self.tools,
            profile=self.profile,
            url=self.url,
            output_dir=self.output_dir,
            use_cookies=self.use_cookies,
            max_resolution=self.max_resolution,
        )

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=self.tools.app_dir,
            env=self.tools.env(),
            **get_subprocess_args(),
        )

        return self.process

    def stop(self) -> None:
            """Süreci ve alt çocuk süreçleri (ffmpeg/yt-dlp) pencere açmadan sonlandırır."""
            if self.process and self.process.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        **get_subprocess_args(),
                    )
                else:
                    self.process.terminate()

    def lines(self) -> Iterator[str]:
        if self.process is None or self.process.stdout is None:
            raise RuntimeError("Süreç henüz başlatılmadı.")

        yield from self.process.stdout

    def wait(self) -> int:
        if self.process is None:
            return -1
        
        return self.process.wait()
            
    def events(self) -> Iterator[Event]:
        
        if self.process is None:
            raise RuntimeError("Process başlatılmadı.")

        parser = OutputParser(self.profile.name, max_resolution=self.max_resolution)

        stdout = self.process.stdout
        if stdout is None:
            raise RuntimeError("stdout bulunamadı.")

        for line in stdout:
            if "[MetadataParser]" in line:
                continue

            if event := parser.parse(line):
                yield event