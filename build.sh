#!/usr/bin/env bash
# ==============================================================================
# yt-dlp-web
# Portable Windows Build
# ==============================================================================

set -Eeuo pipefail

# ==============================================================================
# DİZİNLER
# ==============================================================================

TARGET_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORTABLE_ROOT="$(cd "$TARGET_PROJECT_DIR/../.." && pwd)"

DIST_DIR="$TARGET_PROJECT_DIR/dist"
BUILD_DIR="$TARGET_PROJECT_DIR/build"

mkdir -p "$BUILD_DIR"

PYTHON_DIR="$DIST_DIR/yt-dlp-python"
PYTHON_EXE="$PYTHON_DIR/python.exe"
PYTHON_SITE_PACKAGES="$PYTHON_DIR/Lib/site-packages"
PYTHON_SCRIPTS_DIR="$PYTHON_DIR/Scripts"

PORTABLE_WEB_DIR="$DIST_DIR/yt-dlp-web"
PORTABLE_CORE_DIR="$DIST_DIR/yt-dlp-core"

CORE_SOURCE_DIR="$PORTABLE_ROOT/projects/yt-dlp-core"

REQUIREMENTS_FILE="$CORE_SOURCE_DIR/requirements.txt"

FFMPEG_BUILDER="$PORTABLE_ROOT/projects/yt-dlp-build-infra/ffmpeg/build-ffmpeg.sh"
FFMPEG_BIN_DIR="$PYTHON_SITE_PACKAGES/static_ffmpeg/bin/win32"

# ==============================================================================
# DURUM
# ==============================================================================

BUILD_SUCCESS=0
BUILD_INTERRUPTED=0
FFMPEG_PID=""

# ==============================================================================
# WINDOWS GÖRÜNTÜ YOLLARI
# ==============================================================================

if command -v cygpath >/dev/null 2>&1; then

    DISP_ROOT="$(cygpath -w "$PORTABLE_ROOT")"
    DISP_PROJECT="$(cygpath -w "$TARGET_PROJECT_DIR")"
    DISP_PYTHON="$(cygpath -w "$PYTHON_DIR")"
    DISP_OUTPUT="$(cygpath -w "$DIST_DIR")"
    DISP_CORE="$(cygpath -w "$CORE_SOURCE_DIR")"

else

    DISP_ROOT="$PORTABLE_ROOT"
    DISP_PROJECT="$TARGET_PROJECT_DIR"
    DISP_PYTHON="$PYTHON_DIR"
    DISP_OUTPUT="$DIST_DIR"
    DISP_CORE="$CORE_SOURCE_DIR"

fi

# ==============================================================================
# BAŞLIK
# ==============================================================================

echo "========================================================"
echo "🚀 yt-dlp-web PORTABLE BUILD"
echo "========================================================"
echo "Proje       : $DISP_PROJECT"
echo "Portable    : $DISP_ROOT"
echo "Python      : $DISP_PYTHON"
echo "Çıktı       : $DISP_OUTPUT"
echo "Core        : $DISP_CORE"
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
        echo "🎉 DERLEME BAŞARIYLA TAMAMLANDI"
        echo ""
        echo "Çıktı:"
        echo "$DISP_OUTPUT"
        echo "========================================================"

        if [ -z "${CI:-}" ] && command -v explorer.exe >/dev/null 2>&1; then

            explorer.exe \
                "$(cygpath -w "$DIST_DIR" 2>/dev/null || echo "$DIST_DIR")"

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
# 1 — ÖN KONTROLLER
# ==============================================================================

echo "[1/8] Ortam kontrol ediliyor..."

if ! command -v pymanager >/dev/null 2>&1; then

    echo "❌ Python Install Manager bulunamadı."

    exit 1

fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then

    echo "❌ requirements.txt bulunamadı:"
    echo "   $REQUIREMENTS_FILE"

    exit 1

fi

if [ ! -d "$CORE_SOURCE_DIR" ]; then

    echo "❌ yt-dlp-core bulunamadı:"
    echo "   $CORE_SOURCE_DIR"

    exit 1

fi

if [ ! -d "$CORE_SOURCE_DIR/toolbox" ]; then

    echo "❌ yt-dlp-core/toolbox bulunamadı:"
    echo "   $CORE_SOURCE_DIR/toolbox"

    exit 1

fi

if [ ! -f "$FFMPEG_BUILDER" ]; then

    echo "❌ FFmpeg builder bulunamadı:"
    echo "   $FFMPEG_BUILDER"

    exit 1

fi

if ! command -v git >/dev/null 2>&1; then

    echo "❌ Git bulunamadı."

    exit 1

fi

if ! command -v gh >/dev/null 2>&1; then

    echo "❌ GitHub CLI (gh) bulunamadı."

    exit 1

fi

echo "   ✅ Ortam hazır."
echo ""

# ==============================================================================
# 2 — DIST TEMİZLİĞİ
# ==============================================================================

echo "[2/8] Eski dist klasörü temizleniyor..."

if [ -d "$DIST_DIR" ]; then

    if command -v tasklist.exe >/dev/null 2>&1; then

        if tasklist.exe 2>/dev/null | grep -qi "python.exe"; then

            echo "⚠️ UYARI: python.exe çalışıyor."
            echo "   Eski portable uygulamanın açık olmadığından emin olun."

        fi

    fi

    rm -rf "$DIST_DIR"

fi

if [ -d "$DIST_DIR" ]; then

    echo "❌ dist klasörü temizlenemedi."
    echo "   Dosya kullanımda veya kilitli olabilir."

    exit 1

fi

mkdir -p "$DIST_DIR"

echo "   ✅ dist temizlendi."
echo ""

# ==============================================================================
# 3 — FFMPEG BUILD
# ==============================================================================

echo "[3/8] FFmpeg build paralel olarak başlatılıyor..."

mkdir -p "$FFMPEG_BIN_DIR"

"$FFMPEG_BUILDER" \
    "$FFMPEG_BIN_DIR" \
    > "$BUILD_DIR/ffmpeg-build.log" 2>&1 &

FFMPEG_PID=$!

echo "   FFmpeg PID: $FFMPEG_PID"
echo ""

# ==============================================================================
# PYTHON RUNTIME
# ==============================================================================

echo "[4/8] Python runtime hazırlanıyor..."

PYTHON_VERSION="3.14"

PYTHON_TARGET_WIN="$(
    cygpath -w "$PYTHON_DIR" 2>/dev/null ||
    echo "$PYTHON_DIR"
)"

echo "   Python sürümü : $PYTHON_VERSION"
echo "   Hedef         : $PYTHON_TARGET_WIN"

pymanager install \
    --target="$PYTHON_TARGET_WIN" \
    "$PYTHON_VERSION"

if [ ! -f "$PYTHON_EXE" ]; then

    echo "❌ Python runtime oluşturulamadı."

    exit 1

fi

echo "   Python:"
"$PYTHON_EXE" --version

echo "   Tkinter:"

if "$PYTHON_EXE" -c "import tkinter" >/dev/null 2>&1; then

    echo "      ✅ mevcut"

else

    echo "      ❌ bulunamadı"

    exit 1

fi

echo "   pip:"

if "$PYTHON_EXE" -m pip --version >/dev/null 2>&1; then

    echo "      ✅ mevcut"

else

    echo "      ❌ bulunamadı"

    exit 1

fi

echo "   ✅ Python runtime hazır."
echo ""

# ==============================================================================
# 4 — PYTHON BAĞIMLILIKLARI
# ==============================================================================

echo "[5/8] Python bağımlılıkları kuruluyor..."

"$PYTHON_EXE" -m pip install \
    --disable-pip-version-check \
    --no-warn-script-location \
    -q \
    -r "$REQUIREMENTS_FILE"

echo ""
echo "   → Python bağımlılıkları kontrol ediliyor..."

if ! "$PYTHON_EXE" -c "import fastapi"; then
    echo "❌ FastAPI bulunamadı."
    exit 1
fi

if ! "$PYTHON_EXE" -c "import uvicorn"; then
    echo "❌ Uvicorn bulunamadı."
    exit 1
fi

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

echo "   ✅ Python bağımlılıkları hazır."
echo ""

# ==============================================================================
# NODRIVER PATCHLERİ
# ==============================================================================

echo "→ nodriver patchleri uygulanıyor..."

NODRIVER_DIR="$PYTHON_SITE_PACKAGES/nodriver"
NODRIVER_NETWORK="$NODRIVER_DIR/cdp/network.py"
NODRIVER_CONFIG="$NODRIVER_DIR/core/config.py"

if [ ! -f "$NODRIVER_NETWORK" ]; then

    echo "❌ nodriver/cdp/network.py bulunamadı:"
    echo "   $NODRIVER_NETWORK"

    exit 1

fi

if [ ! -f "$NODRIVER_CONFIG" ]; then

    echo "❌ nodriver/core/config.py bulunamadı:"
    echo "   $NODRIVER_CONFIG"

    exit 1

fi

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

sed -i \
-e 's|browser_executable_path = find_chrome_executable()|browser_executable_path = r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"|' \
-e '/self\._browser_args = browser_args/a\        if "--no-proxy-server" not in self._browser_args:\n            self._browser_args.append("--no-proxy-server")\n        if "--inprivate" not in self._browser_args:\n            self._browser_args.append("--inprivate")' \
-e 's|self.headless = headless|self.headless = True|' \
"$NODRIVER_CONFIG"

echo "   ✅ network.py UTF-8 patchi uygulandı."
echo "   ✅ Edge executable ayarlandı."
echo "   ✅ --no-proxy-server eklendi."
echo "   ✅ --inprivate eklendi."
echo "   ✅ headless=True ayarlandı."
echo ""

echo "   → nodriver kontrol ediliyor..."

if ! "$PYTHON_EXE" -c "import nodriver"; then

    echo "❌ nodriver import edilemedi."

    exit 1

fi

echo "   ✅ nodriver hazır."
echo ""

# ==============================================================================
# STATIC-FFMPEG DİZİNİ
# ==============================================================================

echo "→ static_ffmpeg FFmpeg dizini hazırlanıyor..."

mkdir -p "$FFMPEG_BIN_DIR"

INSTALLED_CRUMB="$FFMPEG_BIN_DIR/installed.crumb"

touch "$INSTALLED_CRUMB"

echo "   ✅ static_ffmpeg dizini hazır."
echo "   ✅ installed.crumb hazır."
echo ""

# ==============================================================================
# 5 — WEB + CORE
# ==============================================================================

echo "[6/8] Web ve core hazırlanıyor..."

# ------------------------------------------------------------------------------
# WEB
# ------------------------------------------------------------------------------

mkdir -p "$PORTABLE_WEB_DIR/static"

WEB_FILES=(
    "web.py"
    "static/web.js"
    "static/index.html"
    "static/style.css"
)

for file in "${WEB_FILES[@]}"; do

    SOURCE_FILE="$TARGET_PROJECT_DIR/$file"
    TARGET_FILE="$PORTABLE_WEB_DIR/$file"

    if [ ! -f "$SOURCE_FILE" ]; then

        echo "❌ Web dosyası bulunamadı:"
        echo "   $SOURCE_FILE"

        exit 1

    fi

    mkdir -p "$(dirname "$TARGET_FILE")"

    cp "$SOURCE_FILE" "$TARGET_FILE"

done

echo "   ✅ yt-dlp-web hazır."

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
        echo "   $SOURCE_FILE"

        exit 1

    fi

    mkdir -p "$(dirname "$TARGET_FILE")"

    cp "$SOURCE_FILE" "$TARGET_FILE"

done

if [ ! -d "$PORTABLE_CORE_DIR/toolbox" ]; then

    echo "❌ Portable yt-dlp-core/toolbox bulunamadı."

    exit 1

fi

echo "   ✅ yt-dlp-core hazır."
echo ""

# ==============================================================================
# 6 — FFMPEG BUILD BEKLENİYOR
# ==============================================================================

echo "[7/8] FFmpeg build tamamlanması bekleniyor..."

if wait "$FFMPEG_PID"; then

    echo "   ✅ FFmpeg build başarılı."

else

    FFMPEG_EXIT=$?

    echo "❌ FFmpeg build başarısız."
    echo "   Exit code: $FFMPEG_EXIT"
    echo ""
    echo "FFmpeg build log:"
    cat "$BUILD_DIR/ffmpeg-build.log"

    exit "$FFMPEG_EXIT"

fi

FFMPEG_PID=""

if [ ! -f "$FFMPEG_BIN_DIR/ffmpeg.exe" ]; then

    echo "❌ ffmpeg.exe bulunamadı."

    exit 1

fi

if [ ! -f "$FFMPEG_BIN_DIR/ffprobe.exe" ]; then

    echo "❌ ffprobe.exe bulunamadı."

    exit 1

fi

touch "$INSTALLED_CRUMB"

echo "   ✅ ffmpeg.exe hazır."
echo "   ✅ ffprobe.exe hazır."
echo ""

# ==============================================================================
# START.CMD
# ==============================================================================

echo "→ start.cmd oluşturuluyor..."

cat > "$DIST_DIR/start.cmd" <<'CMD'
@echo off

if "%~1"==":minimized" goto minimized

start "" /min "%ComSpec%" /c ""%~f0" :minimized"
exit /b

:minimized
cd /d "%~dp0"

"%~dp0yt-dlp-python\python.exe" "%~dp0yt-dlp-web\web.py"
CMD

echo "   ✅ start.cmd hazır."
echo ""

# ==============================================================================
# 7 — SON KONTROLLER
# ==============================================================================

echo "[8/8] Portable paket kontrol ediliyor..."

if [ ! -f "$DIST_DIR/start.cmd" ]; then
    echo "❌ start.cmd bulunamadı."
    exit 1
fi

if [ ! -f "$PYTHON_EXE" ]; then
    echo "❌ Portable Python bulunamadı."
    exit 1
fi

if [ ! -f "$PORTABLE_WEB_DIR/web.py" ]; then
    echo "❌ Portable web.py bulunamadı."
    exit 1
fi

if [ ! -d "$PORTABLE_CORE_DIR/toolbox" ]; then
    echo "❌ Portable yt-dlp-core bulunamadı."
    exit 1
fi

if ! "$PYTHON_EXE" -c "
import fastapi
import uvicorn
import yt_dlp
import yt_dlp_ejs
import mutagen
import static_ffmpeg
import nodriver
import tkinter
"; then

    echo "❌ Python paket kontrolü başarısız."

    exit 1

fi

if ! head -n 1 "$NODRIVER_NETWORK" | grep -q "coding: utf-8"; then
    echo "❌ nodriver network.py UTF-8 patchi bulunamadı."
    exit 1
fi

if ! grep -q \
    'browser_executable_path = r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"' \
    "$NODRIVER_CONFIG"; then

    echo "❌ nodriver Edge executable patchi bulunamadı."
    exit 1

fi

if ! grep -q \
    '"--no-proxy-server"' \
    "$NODRIVER_CONFIG"; then

    echo "❌ nodriver --no-proxy-server patchi bulunamadı."
    exit 1

fi

if ! grep -q \
    '"--inprivate"' \
    "$NODRIVER_CONFIG"; then

    echo "❌ nodriver --inprivate patchi bulunamadı."
    exit 1

fi

if ! grep -q \
    'self.headless = True' \
    "$NODRIVER_CONFIG"; then

    echo "❌ nodriver headless patchi bulunamadı."
    exit 1

fi

if [ ! -f "$FFMPEG_BIN_DIR/installed.crumb" ]; then
    echo "❌ installed.crumb bulunamadı."
    exit 1
fi

if [ ! -f "$FFMPEG_BIN_DIR/ffmpeg.exe" ]; then
    echo "❌ Portable ffmpeg.exe bulunamadı."
    exit 1
fi

if [ ! -f "$FFMPEG_BIN_DIR/ffprobe.exe" ]; then
    echo "❌ Portable ffprobe.exe bulunamadı."
    exit 1
fi

echo "   ✅ Python:"
echo "      $PYTHON_EXE"

echo "   ✅ yt-dlp-web:"
echo "      $PORTABLE_WEB_DIR"

echo "   ✅ yt-dlp-core:"
echo "      $PORTABLE_CORE_DIR"

echo "   ✅ FFmpeg:"
echo "      $FFMPEG_BIN_DIR/ffmpeg.exe"

echo "   ✅ FFprobe:"
echo "      $FFMPEG_BIN_DIR/ffprobe.exe"

echo "   ✅ Portable paket kontrolleri başarılı."
echo ""

# ==============================================================================
# BAŞARI
# ==============================================================================

BUILD_SUCCESS=1

exit 0