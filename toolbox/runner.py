from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterator

from yt_dlp import YoutubeDL

import psutil

from .command import build_command
from .parser import Event, OutputParser
from .profiles import Profile, get_profile
from .playlist import resolve_profile
from .resolver import resolve_music_url
from .tools import Tools, get_subprocess_args


class YtDlpRunner:
    def __init__(
        self,
        tools: Tools,
        profile: Profile,
        url: str,
        output_dir: str | None = None,
        cookie_mode: str = "none",
        cookie_value: str | None = None,
        max_resolution: str | None = None,
    ):
        self.tools = tools
        self.profile = profile
        self.url = url

        self.final_output_dir = output_dir

        self.temp_dir = (
            Path(self.tools.app_dir) / ".tmp_downloads"
        )
        self.temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.cookie_mode = cookie_mode
        self.cookie_value = cookie_value
        self.max_resolution = max_resolution

        self.process: subprocess.Popen[str] | None = None

        self.is_stopped = False

    def _clear_temp_dir(self) -> None:
        self.temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        for item in list(self.temp_dir.iterdir()):
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

                print(
                    "[Portable System] "
                    f"Geçici içerik temizlendi: {item}"
                )

            except Exception as exc:
                print(
                    "[Hata] Geçici içerik temizlenemedi: "
                    f"{item} -> {exc}"
                )

    def start(self) -> subprocess.Popen[str]:
        if (
            not self.final_output_dir
            or not Path(self.final_output_dir).exists()
            or not Path(self.final_output_dir).is_dir()
        ):
            raise RuntimeError(
                "Geçerli bir indirme klasörü seçilmedi."
            )

        self._clear_temp_dir()

        self.is_stopped = False

        url = self.url

        if (
            self.profile.name == "audio"
            and not self.profile.playlist
        ):
            url = resolve_music_url(url)

        cmd = build_command(
            tools=self.tools,
            profile=self.profile,
            url=url,
            output_dir=str(self.temp_dir),
            cookie_mode=self.cookie_mode,
            cookie_value=self.cookie_value,
            max_resolution=self.max_resolution,
        )

        print("\n========== YT-DLP CMD ==========")
        print(cmd)
        print("================================\n")

        env = self.tools.env()

        print("\n========== SUBPROCESS DEBUG ==========")
        print("PYTHON   :", self.tools.python_exec)
        print("APP_DIR  :", self.tools.app_dir)
        print("DENO     :", self.tools.deno)
        print("PATH     :", env.get("PATH"))
        print("======================================\n")

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
            env=env,
            **get_subprocess_args(),
        )

        return self.process

    def stop(self) -> None:
        self.is_stopped = True

        if not self.process:
            return

        try:
            parent = psutil.Process(
                self.process.pid
            )

            children = parent.children(
                recursive=True
            )

            for child in children:
                try:
                    child.kill()
                except Exception:
                    pass

            try:
                parent.kill()
            except Exception:
                pass

        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass

    def lines(self) -> Iterator[str]:
        if (
            self.process is None
            or self.process.stdout is None
        ):
            raise RuntimeError(
                "Süreç henüz başlatılmadı."
            )

        for line in self.process.stdout:
            yield line.strip()

    def wait(self) -> int:
        if self.process is None:
            return -1

        exit_code = self.process.wait()

        if self.temp_dir.exists():
            try:
                for subfolder in self.temp_dir.iterdir():
                    if (
                        subfolder.is_dir()
                        and not any(
                            subfolder.iterdir()
                        )
                    ):
                        subfolder.rmdir()
            except Exception:
                pass

        return exit_code

    def events(self) -> Iterator[Event]:
        if self.process is None:
            raise RuntimeError(
                "Process başlatılmadı."
            )

        parser = OutputParser(
            self.profile.name,
            max_resolution=self.max_resolution,
        )

        stdout = self.process.stdout

        if stdout is None:
            raise RuntimeError(
                "stdout bulunamadı."
            )

        for line in stdout:
            print(
                "[RAW YT-DLP] "
                + line.rstrip()
            )

            if self.is_stopped:
                break

            cleaned_line = line.strip()

            if self.is_stopped:
                break

            if (
                "FILE_DONE|" in cleaned_line
                and self.final_output_dir
            ):
                if self.is_stopped:
                    break

                try:
                    parts = cleaned_line.split("|")
                    downloaded_file_path = Path(
                        parts[-1]
                    )

                    if downloaded_file_path.exists():
                        target_dir = Path(
                            self.final_output_dir
                        )

                        try:
                            relative_path = (
                                downloaded_file_path.relative_to(
                                    self.temp_dir
                                )
                            )
                        except ValueError:
                            relative_path = (
                                downloaded_file_path.name
                            )

                        target_file_path = (
                            target_dir / relative_path
                        )

                        target_file_path.parent.mkdir(
                            parents=True,
                            exist_ok=True,
                        )

                        shutil.move(
                            str(downloaded_file_path),
                            str(target_file_path)
                        )

                        parts[-1] = str(
                            target_file_path
                        )

                        cleaned_line = "|".join(parts)

                        print(
                            "[Portable System] "
                            "Dosya başarıyla aktarıldı: "
                            f"{target_file_path}"
                        )

                except Exception as exc:
                    print(
                        "[Hata] Anlık dosya taşıma "
                        f"esnasında sorun oluştu: {exc}"
                    )

            if "[MetadataParser]" in line:
                continue

            if hasattr(parser, "parser"):
                event = parser.parser.parse(
                    cleaned_line
                )
            else:
                event = parser.parse(
                    cleaned_line
                )

            if event:
                if self.is_stopped:
                    break

                yield event


class ResolverYoutubeDL(YoutubeDL):

    def process_ie_result(
        self,
        ie_result,
        download=True,
        extra_info=None,
    ):
        if (
            isinstance(ie_result, dict)
            and ie_result.get("_type") == "url"
        ):
            url = ie_result.get("url")

            if (
                isinstance(url, str)
                and "music.youtube.com/watch" in url
            ):
                ie_result = ie_result.copy()
                ie_result["url"] = resolve_music_url(
                    url,
                    self,
                )

        return super().process_ie_result(
            ie_result,
            download=download,
            extra_info=extra_info,
        )


def _run_yt_dlp_with_resolver() -> int:
    from yt_dlp import parse_options

    argv = sys.argv[1:]

    if (
        len(argv) >= 3
        and argv[0] == "profile"
    ):
        profile = get_profile(argv[1])

        tools = Tools.discover()

        output, extra_args = resolve_profile(
            tools,
            profile,
            argv[2],
            None,
            "none",
            None,
        )

        profile_args = [
            "-f",
            profile.format,
            *profile.args,
            *extra_args,
            "-o",
            output,
        ]

        argv = [
            *profile_args,
            *argv[2:],
        ]

    parsed = parse_options(argv)

    params = parsed.ydl_opts

    ydl = ResolverYoutubeDL(params)

    return ydl.download(parsed.urls)


if __name__ == "__main__":
    _run_yt_dlp_with_resolver()