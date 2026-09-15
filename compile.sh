#!/usr/bin/env bash
# ==============================================================================
# yt-dlp-gui
# Frozen Windows Build
# ==============================================================================

set -Eeuo pipefail

# ==============================================================================
# DİZİNLER
# ==============================================================================

TARGET_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORTABLE_ROOT="$(cd "$TARGET_PROJECT_DIR/../.." && pwd)"

DIST_DIR="$TARGET_PROJECT_DIR/dist"
BUILD_DIR="$TARGET_PROJECT_DIR/build"

PORTABLE_GUI_DIR="$BUILD_DIR/portable/yt-dlp-gui"
PORTABLE_CORE_DIR="$BUILD_DIR/portable/yt-dlp-core"

CORE_SOURCE_DIR="$PORTABLE_ROOT/projects/yt-dlp-core"

REQUIREMENTS_FILE="$CORE_SOURCE_DIR/requirements.txt"

FFMPEG_BUILDER="$PORTABLE_ROOT/projects/yt-dlp-build-infra/ffmpeg/build-ffmpeg-windows.sh"

PYTHON_EXE="$(command -v python)"
PYTHON_DIR="$(cd "$(dirname "$PYTHON_EXE")" && pwd)"
PYTHON_SITE_PACKAGES="$PYTHON_DIR/Lib/site-packages"

FFMPEG_BIN_DIR="$PYTHON_SITE_PACKAGES/static_ffmpeg/bin/win32"
FFMPEG_EXE="$FFMPEG_BIN_DIR/ffmpeg.exe"
FFPROBE_EXE="$FFMPEG_BIN_DIR/ffprobe.exe"
INSTALLED_CRUMB="$FFMPEG_BIN_DIR/installed.crumb"

DENO_EXE="$PYTHON_DIR/Scripts/deno.exe"

WPC_PLUGIN_SOURCE="$PYTHON_SITE_PACKAGES/yt_dlp_plugins/extractor/getpot_wpc.py"

# ==============================================================================
# DURUM
# ==============================================================================

BUILD_SUCCESS=0
BUILD_INTERRUPTED=0
FFMPEG_PID=""
FFMPEG_READY=0

# ==============================================================================
# WINDOWS GÖRÜNTÜ YOLLARI
# ==============================================================================

if ! command -v cygpath >/dev/null 2>&1; then

    echo "❌ cygpath bulunamadı."
    echo "   Windows build için cygpath gereklidir."

    exit 1

fi

DISP_ROOT="$(cygpath -w "$PORTABLE_ROOT")"
DISP_PROJECT="$(cygpath -w "$TARGET_PROJECT_DIR")"
DISP_PYTHON="$(cygpath -w "$PYTHON_EXE")"
DISP_PYTHON_SITE_PACKAGES="$(cygpath -w "$PYTHON_SITE_PACKAGES")"
DISP_OUTPUT="$(cygpath -w "$DIST_DIR")"
DISP_CORE="$(cygpath -w "$CORE_SOURCE_DIR")"
DISP_FFMPEG_BIN="$(cygpath -w "$FFMPEG_BIN_DIR")"
DISP_FFMPEG_EXE="$(cygpath -w "$FFMPEG_EXE")"
DISP_FFPROBE_EXE="$(cygpath -w "$FFPROBE_EXE")"
DISP_INSTALLED_CRUMB="$(cygpath -w "$INSTALLED_CRUMB")"
DISP_DENO="$(cygpath -w "$DENO_EXE")"
DISP_WPC_PLUGIN_SOURCE="$(cygpath -w "$WPC_PLUGIN_SOURCE")"

# ==============================================================================
# ORTAM
# ==============================================================================

if [ -n "${CI:-}" ]; then
    BUILD_MODE="CI"
else
    BUILD_MODE="LOCAL"
fi

# ==============================================================================
# BAŞLIK
# ==============================================================================

echo "========================================================"
echo "🚀 yt-dlp-gui FROZEN BUILD"
echo "========================================================"
echo "Proje       : $DISP_PROJECT"
echo "Portable    : $DISP_ROOT"
echo "Python      : $DISP_PYTHON"
echo "Python site : $DISP_PYTHON_SITE_PACKAGES"
echo "FFmpeg bin  : $DISP_FFMPEG_BIN"
echo "Deno        : $DISP_DENO"
echo "WPC plugin  : $DISP_WPC_PLUGIN_SOURCE"
echo "Çıktı       : $DISP_OUTPUT"
echo "Core        : $DISP_CORE"
echo "Ortam       : $BUILD_MODE"
echo "========================================================"
echo ""

# ==============================================================================
# CTRL+C
# ==============================================================================

handle_interrupt() {

    BUILD_INTERRUPTED=1

    echo ""
    echo "========================================================"
    echo "⚠️ DERLEME KULLANICI TARAFINDAN DURDURULDU"
    echo "========================================================"

    if [ -n "$FFMPEG_PID" ]; then

        echo "→ FFmpeg build'e TERM sinyali gönderiliyor..."

        kill -TERM "$FFMPEG_PID" 2>/dev/null || true

        echo "   ✅ FFmpeg build durdurma sinyali gönderildi."

    fi

    echo ""

    exit 130
}

trap handle_interrupt INT TERM

# ==============================================================================
# ÇIKIŞ TEMİZLİĞİ
# ==============================================================================

cleanup() {

    local exit_code=$?

    echo ""
    echo "========================================================"
    echo "🧹 ÇIKIŞ TEMİZLİĞİ"
    echo "========================================================"

    if [ -n "$FFMPEG_PID" ]; then

        if kill -0 "$FFMPEG_PID" 2>/dev/null; then

            echo "→ FFmpeg build sonlandırılıyor..."

            kill -TERM "$FFMPEG_PID" 2>/dev/null || true

            for _ in $(seq 1 10); do

                if ! kill -0 "$FFMPEG_PID" 2>/dev/null; then
                    break
                fi

                sleep 0.5

            done

            if kill -0 "$FFMPEG_PID" 2>/dev/null; then

                echo "⚠️ FFmpeg build kapanmadı, zorla sonlandırılıyor..."

                kill -KILL "$FFMPEG_PID" 2>/dev/null || true

            fi

            wait "$FFMPEG_PID" 2>/dev/null || true

        fi

    fi

    FFMPEG_PID=""

    rm -rf "$BUILD_DIR"

    if [ "$BUILD_SUCCESS" -eq 1 ] \
        && [ "$BUILD_INTERRUPTED" -eq 0 ] \
        && [ "$exit_code" -eq 0 ]; then

        echo ""
        echo "========================================================"
        echo "🎉 FROZEN DERLEME BAŞARIYLA TAMAMLANDI"
        echo ""
        echo "Çıktı:"
        echo "$DISP_OUTPUT"
        echo "========================================================"

        if [ -z "${CI:-}" ] && command -v explorer.exe >/dev/null 2>&1; then

            explorer.exe "$DISP_OUTPUT"

        fi

    elif [ "$BUILD_INTERRUPTED" -eq 0 ]; then

        echo ""
        echo "========================================================"
        echo "❌ DERLEME BAŞARISIZ"
        echo "========================================================"

    fi

    return "$exit_code"
}

trap cleanup EXIT

# ==============================================================================
# 1 — ORTAM KONTROLLERİ
# ==============================================================================

echo "[1/8] Ortam kontrol ediliyor..."

if ! command -v python >/dev/null 2>&1; then

    echo "❌ Python bulunamadı."

    exit 1

fi

if ! "$PYTHON_EXE" -m pip --version >/dev/null 2>&1; then

    echo "❌ pip bulunamadı."

    exit 1

fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then

    echo "❌ requirements.txt bulunamadı:"
    echo "   $(cygpath -w "$REQUIREMENTS_FILE")"

    exit 1

fi

if [ ! -d "$CORE_SOURCE_DIR" ]; then

    echo "❌ yt-dlp-core bulunamadı:"
    echo "   $DISP_CORE"

    exit 1

fi

if [ ! -d "$CORE_SOURCE_DIR/toolbox" ]; then

    echo "❌ yt-dlp-core/toolbox bulunamadı:"
    echo "   $(cygpath -w "$CORE_SOURCE_DIR/toolbox")"

    exit 1

fi

if [ ! -f "$TARGET_PROJECT_DIR/gui.py" ]; then

    echo "❌ gui.py bulunamadı:"
    echo "   $(cygpath -w "$TARGET_PROJECT_DIR/gui.py")"

    exit 1

fi

if [ -n "${CI:-}" ]; then

    if [ ! -f "$FFMPEG_BUILDER" ]; then

        echo "❌ FFmpeg builder bulunamadı:"
        echo "   $(cygpath -w "$FFMPEG_BUILDER")"

        exit 1

    fi

fi

if ! command -v git >/dev/null 2>&1; then

    echo "❌ Git bulunamadı."

    exit 1

fi

if ! command -v gh >/dev/null 2>&1; then

    echo "❌ GitHub CLI (gh) bulunamadı."

    exit 1

fi

echo "   Python:"
"$PYTHON_EXE" --version

echo "   Python yolu:"
echo "      $DISP_PYTHON"

echo "   Python site-packages:"
echo "      $DISP_PYTHON_SITE_PACKAGES"

if [ -n "${CI:-}" ]; then

    echo "   CI ortamı algılandı."
    echo "   → Yerel checkpoint kontrolleri uygulanmayacak."

else

    echo "   Yerel ortam algılandı."
    echo "   → Mevcut ortam checkpointleri kullanılacak."

fi

echo "   ✅ Ortam hazır."
echo ""

# ==============================================================================
# 2 — DIST TEMİZLİĞİ
# ==============================================================================

echo "[2/8] Eski dist klasörü temizleniyor..."

if [ -d "$DIST_DIR" ]; then

    rm -rf "$DIST_DIR"

fi

if [ -d "$DIST_DIR" ]; then

    echo "❌ dist klasörü temizlenemedi."
    echo "   Dosya kullanımda veya kilitli olabilir."

    exit 1

fi

mkdir -p "$DIST_DIR"
mkdir -p "$BUILD_DIR"

echo "   ✅ dist temizlendi."
echo ""

# ==============================================================================
# 3 — FFMPEG CHECKPOINT / BUILD
# ==============================================================================

echo "[3/8] FFmpeg ortamı hazırlanıyor..."

mkdir -p "$FFMPEG_BIN_DIR"

if [ -n "${CI:-}" ]; then

    echo "   CI ortamı: FFmpeg tam kuruluma hazırlanıyor."
    echo "   → installed.crumb oluşturuluyor..."

    touch "$INSTALLED_CRUMB"

    echo "   ✅ installed.crumb hazır."
    echo "   → FFmpeg build başlatılıyor..."

else

    if [ -f "$INSTALLED_CRUMB" ] \
        && [ -f "$FFMPEG_EXE" ] \
        && [ -f "$FFPROBE_EXE" ]; then

        FFMPEG_READY=1

        echo "   Mevcut FFmpeg:"
        echo "      $DISP_FFMPEG_EXE"
        echo "      $DISP_FFPROBE_EXE"

        echo "   ✅ FFmpeg hazır."

    else

        echo "   FFmpeg mevcut ortamda hazır değil."
        echo "   → installed.crumb oluşturuluyor..."

        touch "$INSTALLED_CRUMB"

        echo "   ✅ installed.crumb hazır."
        echo "   → FFmpeg build başlatılıyor..."

    fi

fi

if [ "$FFMPEG_READY" -eq 0 ]; then

    FFMPEG_LOG="$BUILD_DIR/ffmpeg-build.log"

    "$FFMPEG_BUILDER" \
        "$FFMPEG_BIN_DIR" \
        > "$FFMPEG_LOG" 2>&1 &

    FFMPEG_PID=$!

    echo "   FFmpeg PID: $FFMPEG_PID"
    echo "   Build log : $(cygpath -w "$FFMPEG_LOG")"

else

    echo "   → FFmpeg builder başlatılmayacak."

fi

echo ""

# ==============================================================================
# 4 — PYTHON BAĞIMLILIKLARI + NODRIVER
# ==============================================================================

echo "[4/8] Python bağımlılıkları hazırlanıyor..."

GUI_REQUIREMENTS="$BUILD_DIR/gui-requirements.txt"

sed \
    -E \
    -e '/^[[:space:]]*(fastapi|uvicorn)([[:space:]]*([<>=!~].*)?)?[[:space:]]*$/d' \
    "$REQUIREMENTS_FILE" \
    > "$GUI_REQUIREMENTS"

sed -i \
    '/^[[:space:]]*pyinstaller([[:space:]]*([<>=!~].*)?)?[[:space:]]*$/d' \
    "$GUI_REQUIREMENTS"

printf '%s\n' "pyinstaller" >> "$GUI_REQUIREMENTS"

echo "   → GUI requirements hazırlanıyor..."

"$PYTHON_EXE" -m pip install \
    --disable-pip-version-check \
    --no-warn-script-location \
    -q \
    -r "$GUI_REQUIREMENTS"

echo ""
echo "   PyInstaller:"
"$PYTHON_EXE" -m PyInstaller --version

echo ""
echo "   → Python bağımlılıkları kontrol ediliyor..."

if ! "$PYTHON_EXE" -c "import yt_dlp"; then

    echo "❌ yt-dlp bulunamadı."

    exit 1

fi

if ! "$PYTHON_EXE" -c "import yt_dlp_ejs"; then

    echo "❌ yt-dlp-ejs bulunamadı."

    exit 1

fi

if ! "$PYTHON_EXE" -c "import mutagen"; then

    echo "❌ mutagen bulunamadı."

    exit 1

fi

if ! "$PYTHON_EXE" -c "import static_ffmpeg"; then

    echo "❌ static_ffmpeg bulunamadı."

    exit 1

fi

if ! "$PYTHON_EXE" -c "import psutil"; then

    echo "❌ psutil bulunamadı."

    exit 1

fi

if [ ! -f "$WPC_PLUGIN_SOURCE" ]; then

    echo "❌ yt-dlp-getpot-wpc plugin dosyası bulunamadı:"
    echo "   $DISP_WPC_PLUGIN_SOURCE"

    exit 1

fi

echo "   WPC plugin:"
echo "      $DISP_WPC_PLUGIN_SOURCE"

echo "   ✅ Python bağımlılıkları hazır."
echo ""

# ------------------------------------------------------------------------------
# NODRIVER
# ------------------------------------------------------------------------------

if [ -n "${CI:-}" ]; then

    echo "→ CI ortamı: nodriver patchleri uygulanıyor..."

    NODRIVER_DIR="$PYTHON_SITE_PACKAGES/nodriver"

    NODRIVER_NETWORK="$NODRIVER_DIR/cdp/network.py"
    NODRIVER_CONFIG="$NODRIVER_DIR/core/config.py"

    if [ ! -f "$NODRIVER_NETWORK" ]; then

        echo "❌ nodriver/cdp/network.py bulunamadı:"
        echo "   $(cygpath -w "$NODRIVER_NETWORK")"

        exit 1

    fi

    if [ ! -f "$NODRIVER_CONFIG" ]; then

        echo "❌ nodriver/core/config.py bulunamadı:"
        echo "   $(cygpath -w "$NODRIVER_CONFIG")"

        exit 1

    fi

    # --------------------------------------------------------------------------
    # network.py UTF-8 patch
    # --------------------------------------------------------------------------

    if ! head -n 1 "$NODRIVER_NETWORK" | grep -q "coding: utf-8"; then

        sed -i '1i# -*- coding: utf-8 -*-' \
            "$NODRIVER_NETWORK"

    fi

    NODRIVER_NETWORK_WIN="$(cygpath -w "$NODRIVER_NETWORK")"

    "$PYTHON_EXE" -c "
from pathlib import Path

p = Path(r'$NODRIVER_NETWORK_WIN')
data = p.read_bytes()

if b'\xB1Inf' in data:
    data = data.replace(b'\xB1Inf', b'\xC2\xB1Inf')
    p.write_bytes(data)
"

    echo "   ✅ network.py UTF-8 patchi uygulandı."

    # --------------------------------------------------------------------------
    # config.py patch
    #
    # Orijinal nodriver 0.50.3 Config.__init__() bölümü,
    # çalışan Edge/WPC ayarlarıyla değiştirilir.
    # --------------------------------------------------------------------------

    "$PYTHON_EXE" - "$NODRIVER_CONFIG" <<'PY'
from pathlib import Path
import sys


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")


old = """        if not browser_executable_path:
            browser_executable_path = find_chrome_executable()

        self._browser_args = browser_args

        self.browser_executable_path = browser_executable_path
        self.headless = headless
"""

new = """        browser_executable_path = (
            r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        )

        required_browser_args = [
            "--no-proxy-server",
            "--inprivate",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-breakpad",
            "--disable-dev-shm-usage",
            "--disable-session-crashed-bubble",
            "--disable-search-engine-choice-screen",
            "--no-first-run",
            "--no-service-autorun",
            "--no-default-browser-check",
            "--no-proxy-server-check",
            "--no-pings",
            "--password-store=basic",
            "--disable-infobars",
            "--mute-audio",
        ]

        for arg in required_browser_args:
            if arg not in browser_args:
                browser_args.append(arg)

        self._browser_args = browser_args

        self.browser_executable_path = browser_executable_path

        # WPC için headless zorunlu.
        self.headless = True
"""

if old not in text:
    raise SystemExit(
        "nodriver config.py patch noktasi bulunamadi."
    )

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
PY

    echo "   ✅ config.py patchi uygulandı."

    # --------------------------------------------------------------------------
    # config.py doğrulama
    # --------------------------------------------------------------------------

    "$PYTHON_EXE" - "$NODRIVER_CONFIG" <<'PY'
from pathlib import Path
import sys


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")


expected_path = (
    'browser_executable_path = (\n'
    '            r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"\n'
    '        )'
)

if expected_path not in text:
    raise SystemExit(
        "nodriver config.py icinde Edge yolu dogrulanamadi."
    )


required = [
    "--no-proxy-server",
    "--inprivate",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-breakpad",
    "--disable-dev-shm-usage",
    "--disable-session-crashed-bubble",
    "--disable-search-engine-choice-screen",
    "--no-first-run",
    "--no-service-autorun",
    "--no-default-browser-check",
    "--no-proxy-server-check",
    "--no-pings",
    "--password-store=basic",
    "--disable-infobars",
    "--mute-audio",
]

for arg in required:
    if f'"{arg}"' not in text:
        raise SystemExit(
            f"nodriver browser arg eksik: {arg}"
        )


if "self._browser_args = browser_args" not in text:
    raise SystemExit(
        "nodriver browser_args dogrulanamadi."
    )


if "self.headless = True" not in text:
    raise SystemExit(
        "nodriver headless=True dogrulanamadi."
    )


if "required_browser_args = [" not in text:
    raise SystemExit(
        "nodriver required_browser_args blogu dogrulanamadi."
    )


print("   OK: Edge executable yolu dogru.")
print("   OK: Browser argumanlari dogru.")
print("   OK: browser_args korunuyor.")
print("   OK: headless=True dogru.")
PY

    echo "   → nodriver patchleri tamamlandı."
    echo "   ✅ Edge executable ayarlandı."
    echo "   ✅ Browser argümanları ayarlandı."
    echo "   ✅ headless=True ayarlandı."
    echo ""

else

    echo "→ Yerel ortam: mevcut nodriver değiştirilmeyecek."
    echo "   Nodriver patch uygulanmayacak."
    echo ""

fi

echo "   → nodriver kontrol ediliyor..."

if ! "$PYTHON_EXE" -c "import nodriver"; then

    echo "❌ nodriver import edilemedi."

    exit 1

fi

echo "   ✅ nodriver hazır."
echo ""

# ==============================================================================
# 5 — GUI + CORE
# ==============================================================================

echo "[5/8] GUI ve core hazırlanıyor..."

# ------------------------------------------------------------------------------
# GUI
# ------------------------------------------------------------------------------

mkdir -p "$PORTABLE_GUI_DIR"

SOURCE_FILE="$TARGET_PROJECT_DIR/gui.py"
TARGET_FILE="$PORTABLE_GUI_DIR/gui.py"

cp "$SOURCE_FILE" "$TARGET_FILE"

echo "   ✅ yt-dlp-gui hazır."

# ------------------------------------------------------------------------------
# CORE
# ------------------------------------------------------------------------------

mkdir -p "$PORTABLE_CORE_DIR/toolbox"

CORE_FILES=(
    "toolbox/__init__.py"
    "toolbox/command.py"
    "toolbox/cookies.py"
    "toolbox/metadata.py"
    "toolbox/output.py"
    "toolbox/parser.py"
    "toolbox/playlist.py"
    "toolbox/playlist_info.py"
    "toolbox/profiles.py"
    "toolbox/runner.py"
    "toolbox/tools.py"
    "toolbox/resolver.py"
)

for file in "${CORE_FILES[@]}"; do

    SOURCE_FILE="$CORE_SOURCE_DIR/$file"
    TARGET_FILE="$PORTABLE_CORE_DIR/$file"

    if [ ! -f "$SOURCE_FILE" ]; then

        echo "❌ Core dosyası bulunamadı:"
        echo "   $(cygpath -w "$SOURCE_FILE")"

        exit 1

    fi

    mkdir -p "$(dirname "$TARGET_FILE")"

    cp "$SOURCE_FILE" "$TARGET_FILE"

done

echo "   ✅ yt-dlp-core kopyası hazır."

# ------------------------------------------------------------------------------
# GEÇİCİ FROZEN RUNTIME PATCH
#
# Kaynak yt-dlp-core kesinlikle değiştirilmez.
# Yalnızca build/portable/yt-dlp-core kopyası patchlenir.
# ------------------------------------------------------------------------------

echo "   → Frozen runtime için geçici core patchi uygulanıyor..."

"$PYTHON_EXE" - "$PORTABLE_CORE_DIR/toolbox/command.py" "$PORTABLE_CORE_DIR/toolbox/tools.py" <<'PY'
from pathlib import Path
import sys


command_path = Path(sys.argv[1])
tools_path = Path(sys.argv[2])


# ------------------------------------------------------------------
# command.py
# ------------------------------------------------------------------

command_text = command_path.read_text(encoding="utf-8")

old_command = """    cmd = [
        sys.executable,
        "-m",
        "toolbox.runner",
    ]
"""

new_command = """    cmd = [
        *tools.yt_dlp_cmd,
    ]
"""

if old_command not in command_text:
    raise SystemExit(
        "command.py gecici patch icin beklenen blok bulunamadi."
    )

command_text = command_text.replace(
    old_command,
    new_command,
    1,
)

command_path.write_text(
    command_text,
    encoding="utf-8",
)


# ------------------------------------------------------------------
# tools.py
# ------------------------------------------------------------------

tools_text = tools_path.read_text(encoding="utf-8")

old_tools = """    @property
    def yt_dlp_cmd(self) -> list[str]:
        \"\"\"yt-dlp'yi aktif Python runtime üzerinden tetikler.\"\"\"
        return [self.python_exec, "-m", "yt_dlp"]
"""

new_tools = """    @property
    def yt_dlp_cmd(self) -> list[str]:
        \"\"\"yt-dlp'yi aktif runtime üzerinden tetikler.\"\"\"
        if getattr(sys, "frozen", False):
            runner_exe = Path(self.python_exec).with_name("yt-dlp-runner.exe")
            if runner_exe.exists():
                return [str(runner_exe)]

        return [self.python_exec, "-m", "yt_dlp"]
"""

if old_tools not in tools_text:
    raise SystemExit(
        "tools.py gecici patch icin beklenen blok bulunamadi."
    )

tools_text = tools_text.replace(
    old_tools,
    new_tools,
    1,
)

tools_path.write_text(
    tools_text,
    encoding="utf-8",
)
PY

echo "   ✅ Frozen runtime patchi yalnızca geçici build kopyasına uygulandı."
echo ""

# ==============================================================================
# 6 — FFMPEG HAZIRLIK / BEKLEME
# ==============================================================================

echo "[6/8] FFmpeg durumu kontrol ediliyor..."

if [ "$FFMPEG_READY" -eq 1 ]; then

    echo "   FFmpeg checkpoint hazır."
    echo "   → Build beklenmeyecek."

elif [ -n "$FFMPEG_PID" ]; then

    echo "   FFmpeg build devam ediyor."
    echo "   → Build tamamlanması bekleniyor..."

    if wait "$FFMPEG_PID"; then

        echo "   ✅ FFmpeg build başarılı."

    else

        FFMPEG_EXIT=$?

        echo "❌ FFmpeg build başarısız."
        echo "   Exit code: $FFMPEG_EXIT"
        echo ""

        if [ -f "$BUILD_DIR/ffmpeg-build.log" ]; then

            echo "FFmpeg build log:"
            cat "$BUILD_DIR/ffmpeg-build.log"

        fi

        exit "$FFMPEG_EXIT"

    fi

    FFMPEG_PID=""

else

    echo "   Mevcut FFmpeg kullanılacak."

fi

if [ ! -f "$FFMPEG_EXE" ]; then

    echo "❌ ffmpeg.exe bulunamadı:"
    echo "   $DISP_FFMPEG_EXE"

    exit 1

fi

if [ ! -f "$FFPROBE_EXE" ]; then

    echo "❌ ffprobe.exe bulunamadı:"
    echo "   $DISP_FFPROBE_EXE"

    exit 1

fi

echo "   ✅ ffmpeg.exe hazır."
echo "   ✅ ffprobe.exe hazır."
echo ""

# ==============================================================================
# 7 — PYINSTALLER FROZEN BUILD
# ==============================================================================

echo "[7/8] PyInstaller frozen build hazırlanıyor..."

FROZEN_BUILD_DIR="$BUILD_DIR/frozen"
FROZEN_SPEC_DIR="$BUILD_DIR/spec"

mkdir -p "$FROZEN_BUILD_DIR"
mkdir -p "$FROZEN_SPEC_DIR"

RUNNER_ENTRY="$BUILD_DIR/yt-dlp-runner-entry.py"

cat > "$RUNNER_ENTRY" <<'PY'
from toolbox.runner import _run_yt_dlp_with_resolver

if __name__ == "__main__":
    raise SystemExit(_run_yt_dlp_with_resolver())
PY

GUI_SPEC="$FROZEN_SPEC_DIR/yt-dlp-gui.spec"

# ------------------------------------------------------------------------------
# PyInstaller'a verilecek yollar Windows formatına çevriliyor.
# ------------------------------------------------------------------------------

TARGET_PROJECT_DIR_WIN="$(cygpath -w "$TARGET_PROJECT_DIR")"
PORTABLE_CORE_DIR_WIN="$(cygpath -w "$PORTABLE_CORE_DIR")"
RUNNER_ENTRY_WIN="$(cygpath -w "$RUNNER_ENTRY")"
DENO_EXE_WIN="$(cygpath -w "$DENO_EXE")"

GUI_ENTRY_WIN="$TARGET_PROJECT_DIR_WIN\\gui.py"

# ------------------------------------------------------------------------------
# GUI + RUNNER TEK SPEC
# ------------------------------------------------------------------------------

cat > "$GUI_SPEC" <<SPEC
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import collect_data_files


static_ffmpeg_datas = collect_data_files("static_ffmpeg")

nodriver_datas, nodriver_binaries, nodriver_hiddenimports = collect_all("nodriver")

deno_binary = [
    (
        r"$DENO_EXE_WIN",
        "Scripts",
    ),
]


a = Analysis(
    [r"$GUI_ENTRY_WIN"],
    pathex=[
        r"$PORTABLE_CORE_DIR_WIN",
    ],
    binaries=[
        *deno_binary,
        *nodriver_binaries,
    ],
    datas=[
        *static_ffmpeg_datas,
        *nodriver_datas,
    ],
    hiddenimports=[
        *nodriver_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

runner_a = Analysis(
    [r"$RUNNER_ENTRY_WIN"],
    pathex=[
        r"$PORTABLE_CORE_DIR_WIN",
    ],
    binaries=[
        *nodriver_binaries,
    ],
    datas=[
        *static_ffmpeg_datas,
        *nodriver_datas,
    ],
    hiddenimports=[
        *nodriver_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

runner_pyz = PYZ(runner_a.pure)

runner_exe = EXE(
    runner_pyz,
    runner_a.scripts,
    [],
    exclude_binaries=True,
    name="yt-dlp-runner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="yt-dlp-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    runner_exe,
    a.binaries,
    a.datas,
    runner_a.binaries,
    runner_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="yt-dlp-gui",
)
SPEC

echo "   → GUI + runner tek PyInstaller spec ile build ediliyor..."

"$PYTHON_EXE" -m PyInstaller \
    --noconfirm \
    --clean \
    --log-level WARN \
    --distpath "$DIST_DIR" \
    --workpath "$FROZEN_BUILD_DIR" \
    "$GUI_SPEC"

echo "   ✅ PyInstaller build tamamlandı."
echo ""
echo "   → WPC plugin frozen paketine kopyalanıyor..."

FROZEN_ROOT="$DIST_DIR/yt-dlp-gui"

# yt-dlp frozen plugin loader:
#   <executable-dir>/yt-dlp-plugins/<package>/yt_dlp_plugins/...
#
# Örnek:
#   yt-dlp-gui/
#   ├── yt-dlp-gui.exe
#   ├── yt-dlp-runner.exe
#   ├── _internal/
#   └── yt-dlp-plugins/
#       └── yt-dlp-getpot-wpc/
#           └── yt_dlp_plugins/
#               └── extractor/
#                   └── getpot_wpc.py

FROZEN_WPC_PLUGIN_DIR="$FROZEN_ROOT/yt-dlp-plugins/yt-dlp-getpot-wpc/yt_dlp_plugins/extractor"
FROZEN_WPC_PLUGIN="$FROZEN_WPC_PLUGIN_DIR/getpot_wpc.py"

mkdir -p "$FROZEN_WPC_PLUGIN_DIR"

cp "$WPC_PLUGIN_SOURCE" "$FROZEN_WPC_PLUGIN"

if [ ! -f "$FROZEN_WPC_PLUGIN" ]; then
    echo "❌ WPC plugin kopyalanamadı:"
    echo "   $FROZEN_WPC_PLUGIN"
    exit 1
fi

echo "   ✅ WPC plugin frozen paketine yerleştirildi."
echo "   → $FROZEN_WPC_PLUGIN"

# ==============================================================================
# 8 — SON KONTROLLER
# ==============================================================================

echo "[8/8] Frozen paket kontrol ediliyor..."

FROZEN_ROOT="$DIST_DIR/yt-dlp-gui"

FROZEN_GUI_EXE="$FROZEN_ROOT/yt-dlp-gui.exe"
FROZEN_RUNNER_EXE="$FROZEN_ROOT/yt-dlp-runner.exe"

FROZEN_FFMPEG="$FROZEN_ROOT/_internal/static_ffmpeg/bin/win32/ffmpeg.exe"
FROZEN_FFPROBE="$FROZEN_ROOT/_internal/static_ffmpeg/bin/win32/ffprobe.exe"
FROZEN_DENO="$FROZEN_ROOT/_internal/Scripts/deno.exe"

FROZEN_WPC_PLUGIN="$FROZEN_ROOT/yt-dlp-plugins/yt-dlp-getpot-wpc/yt_dlp_plugins/extractor/getpot_wpc.py"

if [ ! -f "$FROZEN_GUI_EXE" ]; then

    echo "❌ Frozen GUI bulunamadı:"
    echo "   $(cygpath -w "$FROZEN_GUI_EXE")"

    exit 1

fi

if [ ! -f "$FROZEN_RUNNER_EXE" ]; then

    echo "❌ Frozen runner bulunamadı:"
    echo "   $(cygpath -w "$FROZEN_RUNNER_EXE")"

    exit 1

fi

if [ ! -f "$FROZEN_FFMPEG" ]; then

    echo "❌ Frozen ffmpeg.exe bulunamadı:"
    echo "   $(cygpath -w "$FROZEN_FFMPEG")"

    exit 1

fi

if [ ! -f "$FROZEN_FFPROBE" ]; then

    echo "❌ Frozen ffprobe.exe bulunamadı:"
    echo "   $(cygpath -w "$FROZEN_FFPROBE")"

    exit 1

fi

if [ ! -f "$FROZEN_DENO" ]; then

    echo "❌ Frozen deno.exe bulunamadı:"
    echo "   $(cygpath -w "$FROZEN_DENO")"

    exit 1

fi

if [ ! -f "$FROZEN_WPC_PLUGIN" ]; then
    echo "❌ Frozen WPC plugin bulunamadı:"
    echo "   $(cygpath -w "$FROZEN_WPC_PLUGIN")"
    exit 1
fi

if [ ! -f "$INSTALLED_CRUMB" ]; then

    echo "❌ installed.crumb bulunamadı:"
    echo "   $DISP_INSTALLED_CRUMB"

    exit 1

fi

echo "   WPC plugin:"
echo "      $(cygpath -w "$FROZEN_WPC_PLUGIN")"

echo "   → Frozen GUI self-test çalıştırılıyor..."

if ! "$FROZEN_GUI_EXE" --self-test; then

    echo "❌ Frozen GUI self-test başarısız."

    exit 1

fi

echo "   ✅ Frozen GUI self-test başarılı."
echo ""

echo "   GUI:"
echo "      $(cygpath -w "$FROZEN_GUI_EXE")"

echo "   Runner:"
echo "      $(cygpath -w "$FROZEN_RUNNER_EXE")"

echo "   FFmpeg:"
echo "      $(cygpath -w "$FROZEN_FFMPEG")"

echo "   FFprobe:"
echo "      $(cygpath -w "$FROZEN_FFPROBE")"

echo "   Deno:"
echo "      $(cygpath -w "$FROZEN_DENO")"

echo "   WPC:"
echo "      $(cygpath -w "$FROZEN_WPC_PLUGIN")"

echo ""
echo "   ✅ Frozen paket kontrolleri başarılı."
echo ""

# ==============================================================================
# BAŞARI
# ==============================================================================

BUILD_SUCCESS=1

exit 0
