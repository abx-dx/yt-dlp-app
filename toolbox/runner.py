from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterator

import psutil

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

        # Kullanıcının seçtiği nihai hedef klasör
        self.final_output_dir = output_dir

        # Portable geçici indirme klasörü
        self.temp_dir = Path(self.tools.app_dir) / ".tmp_downloads"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.use_cookies = use_cookies
        self.max_resolution = max_resolution

        self.process: subprocess.Popen[str] | None = None

        # Durdurma bayrağı
        self.is_stopped = False

    def _clear_temp_dir(self) -> None:
        """
        Yeni indirme başlamadan önce .tmp_downloads içeriğini temizler.
        Klasörün kendisi korunur.
        """
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        for item in list(self.temp_dir.iterdir()):
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

                print(
                    f"[Portable System] Geçici içerik temizlendi: {item}"
                )

            except Exception as exc:
                print(
                    f"[Hata] Geçici içerik temizlenemedi: "
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

        # Her yeni indirme başlamadan önce eski geçici içerikleri temizle.    

        self._clear_temp_dir()

        self.is_stopped = False

        cmd = build_command(
            tools=self.tools,
            profile=self.profile,
            url=self.url,
            output_dir=str(self.temp_dir),
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
        """
        Süreci ve tüm çocuk süreçlerini anında sonlandırır.
        """

        self.is_stopped = True

        if not self.process:
            return
        try:
            parent = psutil.Process(self.process.pid)

            children = parent.children(recursive=True)

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
        if self.process is None or self.process.stdout is None:
            raise RuntimeError("Süreç henüz başlatılmadı.")

        for line in self.process.stdout:
            cleaned_line = line.strip()

            yield cleaned_line

    def wait(self) -> int:
        if self.process is None:
            return -1

        exit_code = self.process.wait()

        # Süreç tamamen bittiğinde boş geçici klasörleri temizle.
        if self.temp_dir.exists():
            try:
                for subfolder in self.temp_dir.iterdir():
                    if (
                        subfolder.is_dir()
                        and not any(subfolder.iterdir())
                    ):
                        subfolder.rmdir()

            except Exception:
                pass

        return exit_code

    def events(self) -> Iterator[Event]:
        if self.process is None:
            raise RuntimeError("Process başlatılmadı.")

        parser = OutputParser(
            self.profile.name,
            max_resolution=self.max_resolution,
        )

        stdout = self.process.stdout

        if stdout is None:
            raise RuntimeError("stdout bulunamadı.")

        for line in stdout:
            # Durdurma mümkün olan en erken noktada yakalanır.
            if self.is_stopped:
                break

            cleaned_line = line.strip()

            if self.is_stopped:
                break

            # Dosya tamamlandığında nihai klasöre aktar.
            if (
                "FILE_DONE|" in cleaned_line
                and self.final_output_dir
            ):
                if self.is_stopped:
                    break

                try:
                    parts = cleaned_line.split("|")
                    downloaded_file_path = Path(parts[-1])

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
                            str(target_file_path),
                        )
                        
                        # MetadataParser/metadata.py artık dosyanın
                        # nihai konumunu kullanabilsin.
                        parts[-1] = str(target_file_path)
                        cleaned_line = "|".join(parts)

                        print(
                            "[Portable System] "
                            f"Dosya başarıyla aktarıldı: "
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