import os
import sys
import shutil
import sysconfig
from pathlib import Path

def get_subprocess_args():
    """Windows üzerinde konsol penceresi açılmasını engeller."""
    if sys.platform == "win32":
        import subprocess
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": startupinfo}
    return {}

class Tools:
    def __init__(self, python_exec: str, app_dir: Path, deno: str | None = None, has_ffmpeg: bool = False):
        self.python_exec = python_exec
        self.app_dir = app_dir
        self.deno = deno
        self.has_ffmpeg = has_ffmpeg

    @property
    def yt_dlp_cmd(self) -> list[str]:
        """yt-dlp'yi aktif Python runtime üzerinden tetikler."""
        return [self.python_exec, "-m", "yt_dlp"]

    def env(self) -> dict:
        """Çalıştırma ortamı değişkenlerini (environment variables) döndürür."""
        env_dict = os.environ.copy()
        
        # Deno binary'sinin bulunduğu klasörü PATH'in EN BAŞINA ekliyoruz.
        # yt-dlp alt süreç başladığında Deno'yu doğrudan PATH üzerinden otomatik tespit eder.
        if self.deno:
            deno_dir = str(Path(self.deno).parent)
            current_path = env_dict.get("PATH", "")
            env_dict["PATH"] = f"{deno_dir}{os.pathsep}{current_path}"
            
        return env_dict

    @classmethod
    def discover(cls):
        python_exec = sys.executable
        app_dir = Path(__file__).resolve().parent.parent

        # 1. static_ffmpeg Entegrasyonu (Wheel paketi PATH'e eklenir)
        has_ffmpeg = False
        try:
            import static_ffmpeg
            static_ffmpeg.add_paths()
            has_ffmpeg = True
        except Exception:
            has_ffmpeg = False

        # 2. Deno Tespiti
        # Aktif Python runtime ile aynı dizindeki Deno
        # öncelikli olarak kullanılır.
        scripts_dir = Path(sysconfig.get_path("scripts"))
        deno_exe = scripts_dir / (
            "deno.exe"
            if sys.platform == "win32"
            else "deno"
        )

        if deno_exe.exists():
            deno_path = str(deno_exe)
        else:
            deno_path = shutil.which("deno")

        return cls(
            python_exec=python_exec,
            app_dir=app_dir,
            deno=deno_path,
            has_ffmpeg=has_ffmpeg
        )