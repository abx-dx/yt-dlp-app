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
# FFmpeg REPOSITORY
# ==============================================================================

FFMPEG_REPO_DIR="$PORTABLE_ROOT/projects/yt-dlp-downloader"

FFMPEG_REPO="abx-dx/yt-dlp-downloader"
FFMPEG_BRANCH="refactor/py-core"

# Kısa SHA kullanılabilir.
# Script bunu gerçek commit SHA'ya çözer.
FFMPEG_BASE_COMMIT="edd0133"

FFMPEG_WORKFLOW=".github/workflows/build-ffmpeg.yml"
FFMPEG_BIN_DIR="$FFMPEG_REPO_DIR/build_bin"

# ==============================================================================
# DURUM
# ==============================================================================

BUILD_SUCCESS=0
BUILD_INTERRUPTED=0

# Workflow run ID
TRIGGERED_RUN_ID=""

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
echo "Çıktı        : $DISP_OUTPUT"
echo "Core        : $DISP_CORE"
echo "FFmpeg repo : $FFMPEG_REPO"
echo "FFmpeg base : $FFMPEG_BASE_COMMIT"
echo "Branch      : $FFMPEG_BRANCH"
echo "========================================================"
echo ""

# ==============================================================================
# FFmpeg REPOSITORY KONTROL / TEMİZLEME
# ==============================================================================

reset_ffmpeg_repo() {

    echo ""
    echo "→ FFmpeg repository kontrol ediliyor..."

    if [ ! -d "$FFMPEG_REPO_DIR/.git" ]; then

        echo "❌ FFmpeg Git repository bulunamadı:"
        echo "   $FFMPEG_REPO_DIR"

        return 1

    fi

    # Hedef kısa SHA'yı gerçek commit SHA'ya çöz.
    local target_commit

    if ! target_commit="$(
        git -C "$FFMPEG_REPO_DIR" rev-parse \
            "${FFMPEG_BASE_COMMIT}^{commit}"
    )"; then

        echo "❌ Hedef commit bulunamadı:"
        echo "   $FFMPEG_BASE_COMMIT"

        return 1

    fi

    local current_commit

    current_commit="$(
        git -C "$FFMPEG_REPO_DIR" rev-parse HEAD
    )"

    echo "   Mevcut commit : $current_commit"
    echo "   Hedef commit  : $target_commit"
    echo "   Hedef kısa SHA: $FFMPEG_BASE_COMMIT"

    # --------------------------------------------------------------------------
    # Zaten tam olarak istediğimiz commit'teysek:
    # hiçbir reset / temizleme / push yapılmaz.
    # --------------------------------------------------------------------------

    if [ "$current_commit" = "$target_commit" ]; then

        echo "   ✅ Repository zaten hedef commit'te."
        echo "   → Temizleme/reset/push atlanıyor."

        return 0

    fi

    # --------------------------------------------------------------------------
    # Farklı commit → hedef commit'e dön.
    # --------------------------------------------------------------------------

    echo "   → Repository hedef commit'e döndürülüyor..."

    if ! git -C "$FFMPEG_REPO_DIR" reset \
        --hard \
        "$target_commit"; then

        echo "❌ Lokal reset başarısız."

        return 1

    fi

    echo "   → Remote branch hedef commit'e döndürülüyor..."

    if ! git -C "$FFMPEG_REPO_DIR" push \
        origin \
        "$target_commit:$FFMPEG_BRANCH" \
        --force; then

        echo "❌ Remote reset başarısız."

        return 1

    fi

    echo "   ✅ FFmpeg repository hedef commit'e getirildi."

    return 0
}

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

    # Build ne şekilde biterse bitsin FFmpeg repo hedef commit'e döndürülür.
    if ! reset_ffmpeg_repo; then

        echo ""
        echo "❌ FFmpeg repository otomatik olarak temizlenemedi."
        echo "   Hedef commit: $FFMPEG_BASE_COMMIT"

    fi

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

echo "[1/10] Ortam kontrol ediliyor..."

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

if [ ! -d "$FFMPEG_REPO_DIR/.git" ]; then

    echo "❌ FFmpeg repository bulunamadı:"
    echo "   $FFMPEG_REPO_DIR"

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
# 2 — FFmpeg BAŞLANGIÇ KONTROLÜ
# ==============================================================================

echo "[2/10] FFmpeg başlangıç kontrolü..."

if ! reset_ffmpeg_repo; then

    echo ""
    echo "❌ FFmpeg repository hazırlığı başarısız."

    exit 1

fi

echo ""

# ==============================================================================
# 3 — DIST TEMİZLİĞİ
# ==============================================================================

echo "[3/10] Eski dist klasörü temizleniyor..."

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
# 4 — GERÇEK PORTABLE VENV
# ==============================================================================

echo "[4/10] Portable venv oluşturuluyor..."

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
# 5 — PYTHON BAĞIMLILIKLARI
# ==============================================================================

echo "[5/10] Python bağımlılıkları kuruluyor..."

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
# 6 — WEB DOSYALARI
# ==============================================================================

echo "[6/10] Web uygulaması hazırlanıyor..."

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
# 7 — CUSTOM FFmpeg WORKFLOW
# ==============================================================================

echo "[7/10] Custom FFmpeg workflow hazırlanıyor..."

mkdir -p \
    "$(dirname "$FFMPEG_REPO_DIR/$FFMPEG_WORKFLOW")"

cat > "$FFMPEG_REPO_DIR/$FFMPEG_WORKFLOW" <<'YAML'
name: On-The-Fly Custom FFmpeg Build

on:
  workflow_dispatch:

jobs:
  build-windows:
    runs-on: windows-latest

    steps:
      - name: Setup MSYS2
        uses: msys2/setup-msys2@v2
        with:
          msystem: MINGW64
          update: true
          install: >-
            base-devel
            git
            mingw-w64-x86_64-toolchain
            mingw-w64-x86_64-yasm
            mingw-w64-x86_64-nasm

      - name: Checkout FFmpeg Release Branch
        uses: actions/checkout@v4
        with:
          repository: FFmpeg/FFmpeg
          ref: release/6.1
          path: ffmpeg_src

      - name: Configure and Build
        shell: msys2 {0}
        run: |
          cd ffmpeg_src

          ./configure \
            --target-os=mingw32 \
            --arch=x86_64 \
            --disable-everything \
            --disable-doc \
            --disable-debug \
            --disable-version3 \
            --disable-autodetect \
            --enable-ffmpeg \
            --enable-ffprobe \
            --enable-protocol=file,pipe \
            --enable-demuxer=matroska,webm,ogg,mov,image2,image2pipe,mjpeg,webp \
            --enable-muxer=matroska,ogg,opus,image2,image2pipe,mjpeg,mov,mp4,mp3,webm \
            --enable-decoder=mjpeg,webp \
            --enable-encoder=mjpeg \
            --enable-parser=opus,vp9,av1,h264,mjpeg \
            --enable-bsf=mjpeg2jpeg,opus_metadata \
            --enable-filter=crop,scale,format \
            --enable-swscale \
            --enable-small \
            --extra-cflags="-Os" \
            --extra-ldflags="-static -static-libgcc -static-libstdc++"

          make -j$(nproc)

      - name: Archive Binaries
        shell: bash
        run: |
          mkdir -p build_bin
          cp ffmpeg_src/ffmpeg.exe build_bin/
          cp ffmpeg_src/ffprobe.exe build_bin/
          cd build_bin
          7z a -tzip ../ffmpeg-win-x64.zip ffmpeg.exe ffprobe.exe

      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: ffmpeg-win-x64
          path: ffmpeg-win-x64.zip
YAML

echo "   Workflow oluşturuldu."

# ==============================================================================
# GEÇİCİ WORKFLOW COMMIT
# ==============================================================================

echo "→ Geçici workflow commit'i oluşturuluyor..."

git -C "$FFMPEG_REPO_DIR" add "$FFMPEG_WORKFLOW"

git -C "$FFMPEG_REPO_DIR" commit \
    -m "temp: trigger on-the-fly ffmpeg build" \
    || true

echo "→ Geçici workflow commit'i GitHub'a gönderiliyor..."

git -C "$FFMPEG_REPO_DIR" push \
    origin \
    "$FFMPEG_BRANCH"

echo "   ✅ Geçici workflow commit'i gönderildi."
echo ""

# ==============================================================================
# CI TETİKLE
# ==============================================================================

echo "→ GitHub Actions FFmpeg build tetikleniyor..."

# Tetiklemeden önce mevcut son run ID'sini sakla.
PREVIOUS_RUN_ID="$(
    gh run list \
        --repo "$FFMPEG_REPO" \
        --workflow=build-ffmpeg.yml \
        --branch "$FFMPEG_BRANCH" \
        --limit 1 \
        --json databaseId \
        --jq '.[0].databaseId // empty' \
        2>/dev/null || true
)"

echo "   Önceki run ID: ${PREVIOUS_RUN_ID:-yok}"

gh workflow run build-ffmpeg.yml \
    --repo "$FFMPEG_REPO" \
    --ref "$FFMPEG_BRANCH"

echo "   ✅ CI tetiklendi."
echo ""

# ==============================================================================
# YENİ RUN ID'SİNİ BUL
# ==============================================================================

echo "→ Yeni workflow run bekleniyor..."

TRIGGERED_RUN_ID=""

for _ in $(seq 1 30); do

    CURRENT_RUN_ID="$(
        gh run list \
            --repo "$FFMPEG_REPO" \
            --workflow=build-ffmpeg.yml \
            --branch "$FFMPEG_BRANCH" \
            --limit 1 \
            --json databaseId \
            --jq '.[0].databaseId // empty' \
            2>/dev/null || true
    )"

    if [ -n "$CURRENT_RUN_ID" ] \
        && [ "$CURRENT_RUN_ID" != "$PREVIOUS_RUN_ID" ]; then

        TRIGGERED_RUN_ID="$CURRENT_RUN_ID"

        break

    fi

    sleep 2

done

if [ -z "$TRIGGERED_RUN_ID" ]; then

    echo "❌ Yeni workflow run bulunamadı."

    exit 1

fi

echo "   ✅ Yeni run ID: $TRIGGERED_RUN_ID"
echo ""

# ==============================================================================
# CI BEKLE
# ==============================================================================

echo "→ Custom FFmpeg derlemesi bekleniyor..."

while true; do

    STATUS_RAW="$(
        gh run view \
            "$TRIGGERED_RUN_ID" \
            --repo "$FFMPEG_REPO" \
            --json status,conclusion,url \
            2>/dev/null || true
    )"

    STATUS="$(
        printf '%s' "$STATUS_RAW" |
        "$PORTABLE_PYTHON_EXE" -c '
import json
import sys

try:
    data = json.load(sys.stdin)
    print(data.get("status", ""))
except Exception:
    print("")
'
    )"

    CONCLUSION="$(
        printf '%s' "$STATUS_RAW" |
        "$PORTABLE_PYTHON_EXE" -c '
import json
import sys

try:
    data = json.load(sys.stdin)
    print(data.get("conclusion", ""))
except Exception:
    print("")
'
    )"

    RUN_URL="$(
        printf '%s' "$STATUS_RAW" |
        "$PORTABLE_PYTHON_EXE" -c '
import json
import sys

try:
    data = json.load(sys.stdin)
    print(data.get("url", ""))
except Exception:
    print("")
'
    )"

    case "$STATUS" in

        completed)

            if [ "$CONCLUSION" = "success" ]; then

                echo "   ✅ Custom FFmpeg derlemesi tamamlandı."

                break

            fi

            echo ""
            echo "❌ Custom FFmpeg CI başarısız oldu."

            if [ -n "$RUN_URL" ]; then
                echo "   $RUN_URL"
            fi

            echo ""
            echo "Hata logu:"

            gh run view \
                "$TRIGGERED_RUN_ID" \
                --repo "$FFMPEG_REPO" \
                --log-failed \
                || true

            exit 1
            ;;

        in_progress|queued|waiting)

            echo "   → FFmpeg derlemesi devam ediyor..."

            ;;

        *)

            echo "   → CI durumu kontrol ediliyor..."

            ;;

    esac

    sleep 15

done

echo ""

# ==============================================================================
# 8 — ESKİ CI ÇALIŞMALARINI TEMİZLE
# ==============================================================================

echo "[8/10] Eski FFmpeg CI çalışmaları temizleniyor..."

OLD_RUN_IDS="$(
    gh run list \
        --repo "$FFMPEG_REPO" \
        --workflow=build-ffmpeg.yml \
        --limit 100 \
        --json databaseId \
        --jq '.[].databaseId' \
        2>/dev/null |
    while IFS= read -r RUN_ID; do

        [ -z "$RUN_ID" ] && continue

        if [ "$RUN_ID" != "$TRIGGERED_RUN_ID" ]; then
            printf '%s\n' "$RUN_ID"
        fi

    done
)"

if [ -n "$OLD_RUN_IDS" ]; then

    while IFS= read -r RUN_ID; do

        [ -z "$RUN_ID" ] && continue

        echo "   → Workflow siliniyor: $RUN_ID"

		if gh run delete \
			"$RUN_ID" \
			--repo "$FFMPEG_REPO"; then

			echo "      ✅ Silindi."

		else

			echo "      ❌ Silinemedi: $RUN_ID"

		fi

		sleep 0.5

    done <<< "$OLD_RUN_IDS"

else

    echo "   → Silinecek eski workflow bulunamadı."

fi

echo "   ✅ Eski CI çalışmaları temizlendi."
echo ""

# ==============================================================================
# 9 — ARTIFACT İNDİR
# ==============================================================================

echo "[9/10] FFmpeg artifact indiriliyor..."

rm -rf "$FFMPEG_BIN_DIR"

mkdir -p "$FFMPEG_BIN_DIR"

gh run download \
    "$TRIGGERED_RUN_ID" \
    --repo "$FFMPEG_REPO" \
    --name ffmpeg-win-x64 \
    --dir "$FFMPEG_BIN_DIR"

ZIP_FILE="$(
    find "$FFMPEG_BIN_DIR" \
        -maxdepth 1 \
        -type f \
        -name "*.zip" |
    head -n 1
)"

if [ -z "$ZIP_FILE" ]; then

    echo "❌ FFmpeg artifact ZIP bulunamadı."

    exit 1

fi

unzip -o \
    "$ZIP_FILE" \
    -d "$FFMPEG_BIN_DIR"

rm -f "$ZIP_FILE"

if [ ! -f "$FFMPEG_BIN_DIR/ffmpeg.exe" ]; then

    echo "❌ ffmpeg.exe bulunamadı."

    exit 1

fi

if [ ! -f "$FFMPEG_BIN_DIR/ffprobe.exe" ]; then

    echo "❌ ffprobe.exe bulunamadı."

    exit 1

fi

echo "   ✅ FFmpeg artifact hazır."
echo ""

# ==============================================================================
# CUSTOM FFmpeg → static_ffmpeg
# ==============================================================================

echo "→ Custom FFmpeg static_ffmpeg içine yerleştiriliyor..."

cp \
    "$FFMPEG_BIN_DIR/ffmpeg.exe" \
    "$STATIC_FFMPEG_BIN/"

cp \
    "$FFMPEG_BIN_DIR/ffprobe.exe" \
    "$STATIC_FFMPEG_BIN/"

echo "   ✅ Custom FFmpeg yerleştirildi."
echo ""

# Binary'ler değiştiği için crumb'ı tekrar garanti et.
touch "$STATIC_FFMPEG_BIN/installed.crumb"

echo "   ✅ installed.crumb mevcut."
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
# 10 — SON KONTROLLER
# ==============================================================================

echo "[10/10] Portable paket kontrol ediliyor..."

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