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

# Geliştirme venv.
# Build işlemlerinde kullanılacak Python/pip buradadır.
DEV_VENV_DIR="$PORTABLE_ROOT/apps/python/venv"
DEV_VENV_PYTHON="$DEV_VENV_DIR/Scripts/python.exe"

DIST_DIR="$TARGET_PROJECT_DIR/dist"
BUILD_DIR="$TARGET_PROJECT_DIR/build"

# DIST içindeki portable Python venv.
PORTABLE_VENV_DIR="$DIST_DIR/python"

PORTABLE_SITE_PACKAGES="$PORTABLE_VENV_DIR/Lib/site-packages"
PORTABLE_SCRIPTS_DIR="$PORTABLE_VENV_DIR/Scripts"
PORTABLE_PYTHON_EXE="$PORTABLE_SCRIPTS_DIR/python.exe"

PORTABLE_WEB_DIR="$DIST_DIR/web"
PORTABLE_CORE_DIR="$DIST_DIR/yt-dlp-core"

REQUIREMENTS_FILE="$TARGET_PROJECT_DIR/requirements.txt"

# ==============================================================================
# yt-dlp CORE
# ==============================================================================

CORE_SOURCE_DIR="$PORTABLE_ROOT/projects/yt-dlp-core"

# ==============================================================================
# DURUM
# ==============================================================================

BUILD_SUCCESS=0
BUILD_INTERRUPTED=0


# ==============================================================================
# WINDOWS GÖRÜNTÜ YOLLARI
# ==============================================================================

if command -v cygpath >/dev/null 2>&1; then

    DISP_ROOT="$(cygpath -w "$PORTABLE_ROOT")"
    DISP_PROJECT="$(cygpath -w "$TARGET_PROJECT_DIR")"
    DISP_DEV_VENV="$(cygpath -w "$DEV_VENV_DIR")"
    DISP_VENV="$(cygpath -w "$PORTABLE_VENV_DIR")"
    DISP_OUTPUT="$(cygpath -w "$DIST_DIR")"
    DISP_CORE="$(cygpath -w "$CORE_SOURCE_DIR")"

else

    DISP_ROOT="$PORTABLE_ROOT"
    DISP_PROJECT="$TARGET_PROJECT_DIR"
    DISP_DEV_VENV="$DEV_VENV_DIR"
    DISP_VENV="$PORTABLE_VENV_DIR"
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
echo "Dev Venv    : $DISP_DEV_VENV"
echo "Venv        : $DISP_VENV"
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

        if command -v explorer.exe >/dev/null 2>&1; then

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

echo "[1/7] Ortam kontrol ediliyor..."

if [ ! -f "$DEV_VENV_PYTHON" ]; then

    echo "❌ Geliştirme venv Python'u bulunamadı:"
    echo "   $DEV_VENV_PYTHON"

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

if ! command -v git >/dev/null 2>&1; then

    echo "❌ Git bulunamadı."

    exit 1

fi

if ! command -v gh >/dev/null 2>&1; then

    echo "❌ GitHub CLI (gh) bulunamadı."

    exit 1

fi

if ! command -v unzip >/dev/null 2>&1; then

    echo "❌ unzip bulunamadı."

    exit 1

fi

echo "   Geliştirme Venv Python:"
"$DEV_VENV_PYTHON" --version

echo ""

# ==============================================================================
# 2 — DIST TEMİZLİĞİ
# ==============================================================================

echo "[2/7] Eski dist klasörü temizleniyor..."

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
# 3 — GERÇEK PORTABLE VENV
# ==============================================================================

echo "[3/7] Portable venv oluşturuluyor..."

# Geliştirme venv'sindeki Python kullanılarak
# dist/python altında yeni ve bağımsız bir Windows venv oluşturulur.
#
# Kaynak:
#
#   DEV_VENV_PYTHON
#
# Hedef:
#
#   dist/python/
#   ├── Include/
#   ├── Lib/
#   ├── Scripts/
#   │   ├── python.exe
#   │   ├── pythonw.exe
#   │   └── ...
#   └── pyvenv.cfg
#
# ÖNEMLİ:
# Windows venv'de python.exe Scripts klasörü içindedir.

"$DEV_VENV_PYTHON" -m venv \
    --without-pip \
    "$PORTABLE_VENV_DIR"

if [ ! -f "$PORTABLE_PYTHON_EXE" ]; then

    echo "❌ Portable venv içinde python.exe bulunamadı:"
    echo "   $PORTABLE_PYTHON_EXE"

    exit 1

fi

echo "   Portable venv Python:"
"$PORTABLE_PYTHON_EXE" --version

echo "   ✅ Portable venv hazır."
echo ""

# ==============================================================================
# 4 — PYTHON BAĞIMLILIKLARI
# ==============================================================================

echo "[4/7] Python bağımlılıkları kuruluyor..."

"$DEV_VENV_PYTHON" -m pip install \
    --disable-pip-version-check \
    --no-warn-script-location \
    --target "$PORTABLE_SITE_PACKAGES" \
    -q \
    -r "$REQUIREMENTS_FILE"

if [ ! -f "$PORTABLE_SITE_PACKAGES/bin/deno.exe" ]; then

    echo "❌ Deno binary'si bulunamadı:"
    echo "   $PORTABLE_SITE_PACKAGES/bin/deno.exe"

    exit 1

fi

mv \
    "$PORTABLE_SITE_PACKAGES/bin/deno.exe" \
    "$PORTABLE_SCRIPTS_DIR/deno.exe"

echo "   → Bağımlılık kontrolü..."

if ! "$PORTABLE_PYTHON_EXE" -c "import fastapi" >/dev/null 2>&1; then

    echo "❌ FastAPI portable venv içinde bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import uvicorn" >/dev/null 2>&1; then

    echo "❌ Uvicorn portable venv içinde bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import yt_dlp" >/dev/null 2>&1; then

    echo "❌ yt-dlp portable venv içinde bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import mutagen" >/dev/null 2>&1; then

    echo "❌ mutagen portable venv içinde bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import static_ffmpeg" >/dev/null 2>&1; then

    echo "❌ static_ffmpeg portable venv içinde bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import deno" >/dev/null 2>&1; then

    echo "❌ deno portable venv içinde bulunamadı."

    exit 1

fi

echo "   ✅ Python bağımlılıkları hazır."
echo ""

# ==============================================================================
# 5 — WEB DOSYALARI
# ==============================================================================

echo "[5/7] Web uygulaması hazırlanıyor..."

mkdir -p "$PORTABLE_WEB_DIR"

cp \
    "$TARGET_PROJECT_DIR/app.py" \
    "$PORTABLE_WEB_DIR/"

if [ -f "$TARGET_PROJECT_DIR/app2.py" ]; then

    cp \
        "$TARGET_PROJECT_DIR/app2.py" \
        "$PORTABLE_WEB_DIR/"

fi

if [ -d "$TARGET_PROJECT_DIR/static" ]; then

    cp -a \
        "$TARGET_PROJECT_DIR/static" \
        "$PORTABLE_WEB_DIR/"

fi

echo "   ✅ Web dosyaları hazır."
echo ""

# ==============================================================================
# yt-dlp CORE
# ==============================================================================

echo "→ yt-dlp-core portable pakete kopyalanıyor..."

rm -rf "$PORTABLE_CORE_DIR"

mkdir -p "$PORTABLE_CORE_DIR"

cp -a \
    "$CORE_SOURCE_DIR/." \
    "$PORTABLE_CORE_DIR/"

if [ ! -d "$PORTABLE_CORE_DIR/toolbox" ]; then

    echo "❌ Portable yt-dlp-core/toolbox kopyalanamadı."

    exit 1

fi

echo "   ✅ yt-dlp-core hazır:"
echo "      $PORTABLE_CORE_DIR"
echo ""

# ==============================================================================
# STATIC-FFMPEG CRUMB
# ==============================================================================

echo "→ static_ffmpeg installed.crumb hazırlanıyor..."

STATIC_FFMPEG_BIN="$PORTABLE_SITE_PACKAGES/static_ffmpeg/bin/win32"
INSTALLED_CRUMB="$STATIC_FFMPEG_BIN/installed.crumb"

mkdir -p "$STATIC_FFMPEG_BIN"

# Bilerek touch kullanıyoruz.
# Böylece static_ffmpeg binary'leri tekrar lazy-download etmez.
touch "$INSTALLED_CRUMB"

echo "   ✅ installed.crumb oluşturuldu."
echo "      $INSTALLED_CRUMB"
echo ""

# ==============================================================================
# 6 — CUSTOM FFmpeg
# ==============================================================================

echo "[6/7] Custom FFmpeg hazırlanıyor..."

FFMPEG_BUILDER="$PORTABLE_ROOT/projects/yt-dlp-build-infra/ffmpeg/build-ffmpeg.sh"

if [ ! -f "$FFMPEG_BUILDER" ]; then
    echo "❌ FFmpeg builder bulunamadı:"
    echo "   $FFMPEG_BUILDER"
    exit 1
fi

"$FFMPEG_BUILDER" \
    "$STATIC_FFMPEG_BIN"

if [ ! -f "$STATIC_FFMPEG_BIN/ffmpeg.exe" ]; then
    echo "❌ Custom ffmpeg.exe bulunamadı."
    exit 1
fi

if [ ! -f "$STATIC_FFMPEG_BIN/ffprobe.exe" ]; then
    echo "❌ Custom ffprobe.exe bulunamadı."
    exit 1
fi

touch "$STATIC_FFMPEG_BIN/installed.crumb"

echo "   ✅ Custom FFmpeg hazır."
echo "   ✅ installed.crumb hazır."
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

"%~dp0python\Scripts\python.exe" "%~dp0web\app.py"
CMD

echo "   ✅ start.cmd hazır."
echo ""

# ==============================================================================
# 7 — SON KONTROLLER
# ==============================================================================

echo "[7/7] Portable paket kontrol ediliyor..."

if [ ! -f "$DIST_DIR/start.cmd" ]; then

    echo "❌ start.cmd bulunamadı."

    exit 1

fi

if [ ! -f "$PORTABLE_PYTHON_EXE" ]; then

    echo "❌ Portable Python bulunamadı:"
    echo "   $PORTABLE_PYTHON_EXE"

    exit 1

fi

if [ ! -f "$PORTABLE_VENV_DIR/pyvenv.cfg" ]; then

    echo "❌ pyvenv.cfg bulunamadı."

    exit 1

fi

if [ ! -f "$PORTABLE_WEB_DIR/app.py" ]; then

    echo "❌ Portable app.py bulunamadı."

    exit 1

fi

if [ ! -d "$PORTABLE_CORE_DIR/toolbox" ]; then

    echo "❌ Portable yt-dlp-core/toolbox bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import fastapi" >/dev/null 2>&1; then

    echo "❌ Portable Python içinde FastAPI bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import uvicorn" >/dev/null 2>&1; then

    echo "❌ Portable Python içinde Uvicorn bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import yt_dlp" >/dev/null 2>&1; then

    echo "❌ Portable Python içinde yt-dlp bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import mutagen" >/dev/null 2>&1; then

    echo "❌ Portable Python içinde mutagen bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import static_ffmpeg" >/dev/null 2>&1; then

    echo "❌ Portable Python içinde static_ffmpeg bulunamadı."

    exit 1

fi

if ! "$PORTABLE_PYTHON_EXE" -c "import deno" >/dev/null 2>&1; then

    echo "❌ Portable Python içinde Deno paketi bulunamadı."

    exit 1

fi

if [ ! -f "$PORTABLE_SCRIPTS_DIR/deno.exe" ]; then

    echo "❌ Portable Deno binary bulunamadı."

    exit 1

fi

if [ ! -f "$STATIC_FFMPEG_BIN/installed.crumb" ]; then

    echo "❌ installed.crumb bulunamadı."

    exit 1

fi

if [ ! -f "$STATIC_FFMPEG_BIN/ffmpeg.exe" ]; then

    echo "❌ Portable ffmpeg.exe bulunamadı."

    exit 1

fi

if [ ! -f "$STATIC_FFMPEG_BIN/ffprobe.exe" ]; then

    echo "❌ Portable ffprobe.exe bulunamadı."

    exit 1

fi

echo "   ✅ Portable Python:"
echo "      $PORTABLE_PYTHON_EXE"

echo "   ✅ yt-dlp-core:"
echo "      $PORTABLE_CORE_DIR"

echo "   ✅ Deno:"
echo "      $PORTABLE_SCRIPTS_DIR/deno.exe"

echo "   ✅ FFmpeg:"
echo "      $STATIC_FFMPEG_BIN/ffmpeg.exe"

echo "   ✅ FFprobe:"
echo "      $STATIC_FFMPEG_BIN/ffprobe.exe"

echo "   ✅ installed.crumb:"
echo "      $STATIC_FFMPEG_BIN/installed.crumb"

echo "   ✅ Portable paket kontrolleri başarılı."
echo ""

# ==============================================================================
# BAŞARI
# ==============================================================================

BUILD_SUCCESS=1

exit 0