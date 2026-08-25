#!/usr/bin/env bash
# ==============================================================================
# yt-dlp-app — Custom FFmpeg Builder
# ==============================================================================

set -Eeuo pipefail

# ==============================================================================
# ÇIKTI
# ==============================================================================

FFMPEG_OUTPUT_DIR="${1:-}"

if [ -z "$FFMPEG_OUTPUT_DIR" ]; then

    echo "❌ FFmpeg çıktı dizini belirtilmedi."
    echo ""
    echo "Kullanım:"
    echo "   build-ffmpeg.sh <output-dir>"

    exit 1

fi

mkdir -p "$FFMPEG_OUTPUT_DIR"

# ==============================================================================
# DİZİNLER
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FFMPEG_BIN_DIR="$SCRIPT_DIR/build_bin"

# ==============================================================================
# GITHUB
# ==============================================================================

REPO="abx-dx/yt-dlp-app"
BRANCH="build-infra"

WORKFLOW="build-ffmpeg.yml"
ARTIFACT_NAME="ffmpeg-win-x64"

TRIGGERED_RUN_ID=""

# ==============================================================================
# TEMİZLİK
# ==============================================================================

cleanup() {

    rm -rf "$FFMPEG_BIN_DIR"

}

trap cleanup EXIT

# ==============================================================================
# BAŞLIK
# ==============================================================================

echo "========================================================"
echo "🚀 CUSTOM FFMPEG BUILD"
echo "========================================================"
echo "Repository : $REPO"
echo "Branch     : $BRANCH"
echo "Workflow   : $WORKFLOW"
echo "Output     : $FFMPEG_OUTPUT_DIR"
echo "========================================================"
echo ""

# ==============================================================================
# ÖN KONTROLLER
# ==============================================================================

echo "→ Ortam kontrol ediliyor..."

if ! command -v gh >/dev/null 2>&1; then

    echo "❌ GitHub CLI (gh) bulunamadı."

    exit 1

fi

if ! command -v unzip >/dev/null 2>&1; then

    echo "❌ unzip bulunamadı."

    exit 1

fi

echo "   ✅ GitHub CLI hazır."
echo "   ✅ unzip hazır."
echo ""

# ==============================================================================
# ARTIFACT ÇALIŞMA ALANI
# ==============================================================================

rm -rf "$FFMPEG_BIN_DIR"

mkdir -p "$FFMPEG_BIN_DIR"

# ==============================================================================
# ÖNCEKİ RUN ID
# ==============================================================================

echo "→ Mevcut son workflow run kontrol ediliyor..."

PREVIOUS_RUN_ID="$(
    gh run list \
        --repo "$REPO" \
        --workflow="$WORKFLOW" \
        --branch "$BRANCH" \
        --limit 1 \
        --json databaseId \
        --jq '.[0].databaseId // empty' \
        2>/dev/null || true
)"

echo "   Önceki run ID: ${PREVIOUS_RUN_ID:-yok}"
echo ""

# ==============================================================================
# CI TETİKLE
# ==============================================================================

echo "→ GitHub Actions FFmpeg build tetikleniyor..."

gh workflow run \
    "$WORKFLOW" \
    --repo "$REPO" \
    --ref "$BRANCH"

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
            --repo "$REPO" \
            --workflow="$WORKFLOW" \
            --branch "$BRANCH" \
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

if ! gh run watch \
    "$TRIGGERED_RUN_ID" \
    --repo "$REPO" \
    --exit-status; then

    echo ""
    echo "❌ Custom FFmpeg CI başarısız oldu."
    echo ""
    echo "Hata logu:"

    gh run view \
        "$TRIGGERED_RUN_ID" \
        --repo "$REPO" \
        --log-failed \
        || true

    exit 1

fi

echo ""
echo "   ✅ Custom FFmpeg derlemesi tamamlandı."
echo ""

# ==============================================================================
# ARTIFACT İNDİR
# ==============================================================================

echo "→ FFmpeg artifact indiriliyor..."

gh run download \
    "$TRIGGERED_RUN_ID" \
    --repo "$REPO" \
    --name "$ARTIFACT_NAME" \
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

# ==============================================================================
# ARTIFACT KONTROLÜ
# ==============================================================================

if [ ! -f "$FFMPEG_BIN_DIR/ffmpeg.exe" ]; then

    echo "❌ ffmpeg.exe bulunamadı."

    exit 1

fi

if [ ! -f "$FFMPEG_BIN_DIR/ffprobe.exe" ]; then

    echo "❌ ffprobe.exe bulunamadı."

    exit 1

fi

echo "   ✅ Artifact hazır."
echo ""

# ==============================================================================
# ÇIKTIYA KOPYALA
# ==============================================================================

echo "→ FFmpeg binary'leri çıktı dizinine kopyalanıyor..."

cp \
    "$FFMPEG_BIN_DIR/ffmpeg.exe" \
    "$FFMPEG_OUTPUT_DIR/"

cp \
    "$FFMPEG_BIN_DIR/ffprobe.exe" \
    "$FFMPEG_OUTPUT_DIR/"

# ==============================================================================
# SON KONTROLLER
# ==============================================================================

if [ ! -f "$FFMPEG_OUTPUT_DIR/ffmpeg.exe" ]; then

    echo "❌ ffmpeg.exe çıktı dizinine kopyalanamadı."

    exit 1

fi

if [ ! -f "$FFMPEG_OUTPUT_DIR/ffprobe.exe" ]; then

    echo "❌ ffprobe.exe çıktı dizinine kopyalanamadı."

    exit 1

fi

echo ""
echo "========================================================"
echo "🎉 CUSTOM FFMPEG HAZIR"
echo "========================================================"
echo "FFmpeg : $FFMPEG_OUTPUT_DIR/ffmpeg.exe"
echo "FFprobe: $FFMPEG_OUTPUT_DIR/ffprobe.exe"
echo "Run ID : $TRIGGERED_RUN_ID"
echo "========================================================"