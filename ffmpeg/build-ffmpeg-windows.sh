#!/usr/bin/env bash
# ==============================================================================
# yt-dlp-app — Custom FFmpeg Windows Builder
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
    echo "   build-ffmpeg-windows.sh <output-dir>"
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
WORKFLOW="build-ffmpeg-windows.yml"
BRANCH="yt-dlp-yml"
ARTIFACT_NAME="ffmpeg-win-x64"

RUN_ID=""
WATCH_PID=""
INTERRUPTED=0

# ==============================================================================
# CTRL+C / TERM
# ==============================================================================

handle_interrupt() {

    INTERRUPTED=1

    echo ""
    echo "========================================================"
    echo "⚠️ CUSTOM FFMPEG WINDOWS BUILD DURDURULUYOR"
    echo "========================================================"

    # --------------------------------------------------------------------------
    # GitHub Actions run'ını iptal et
    # --------------------------------------------------------------------------

    if [ -n "$RUN_ID" ]; then

        echo "→ GitHub Actions run iptal ediliyor..."
        echo "   Run ID: $RUN_ID"

        gh run cancel \
            "$RUN_ID" \
            --repo "$REPO" \
            2>/dev/null || true

        echo "   ✅ İptal isteği gönderildi."

    else

        echo "→ Henüz workflow run ID alınmadı."

    fi

    # --------------------------------------------------------------------------
    # gh run watch sürecini sonlandır
    # --------------------------------------------------------------------------

    if [ -n "$WATCH_PID" ]; then

        if kill -0 "$WATCH_PID" 2>/dev/null; then

            echo "→ GitHub Actions watch süreci sonlandırılıyor..."

            kill "$WATCH_PID" 2>/dev/null || true

            echo "   ✅ Watch süreci sonlandırıldı."

        fi

        WATCH_PID=""

    fi

    echo ""

    exit 130
}

trap handle_interrupt INT TERM

# ==============================================================================
# TEMİZLİK
# ==============================================================================

cleanup() {

    local exit_code=$?

    # Interrupt sırasında watch hâlâ varsa zorla sonlandır
    if [ -n "$WATCH_PID" ]; then

        if kill -0 "$WATCH_PID" 2>/dev/null; then
            kill "$WATCH_PID" 2>/dev/null || true
        fi

    fi

    rm -rf "$FFMPEG_BIN_DIR"

    return "$exit_code"
}

trap cleanup EXIT

# ==============================================================================
# BAŞLIK
# ==============================================================================

echo "========================================================"
echo "🚀 CUSTOM FFMPEG WINDOWS BUILD"
echo "========================================================"
echo "Repository : $REPO"
echo "Workflow   : $WORKFLOW"
echo "Branch     : $BRANCH"
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
# ÇALIŞMA ALANI
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

echo "→ GitHub Actions FFmpeg Windows build tetikleniyor..."

WORKFLOW_RUN_URL="$(
    gh workflow run \
        "$WORKFLOW" \
        --repo "$REPO" \
        --ref "$BRANCH" \
        2>&1
)"

echo "$WORKFLOW_RUN_URL"

RUN_ID="$(
    printf '%s\n' "$WORKFLOW_RUN_URL" |
        grep -oE '/actions/runs/[0-9]+' |
        grep -oE '[0-9]+$' |
        tail -n 1
)"

if [ -z "$RUN_ID" ]; then

    echo "❌ Workflow run ID alınamadı."
    exit 1

fi

echo "   ✅ CI tetiklendi."
echo "   Run ID: $RUN_ID"
echo ""

# ==============================================================================
# CI BEKLE
# ==============================================================================

echo "→ Custom FFmpeg Windows derlemesi bekleniyor..."

gh run watch \
    "$RUN_ID" \
    --repo "$REPO" \
    --exit-status &

WATCH_PID=$!

if wait "$WATCH_PID"; then

    WATCH_PID=""

else

    WATCH_EXIT=$?
    WATCH_PID=""

    if [ "$INTERRUPTED" -eq 1 ]; then
        exit 130
    fi

    echo ""
    echo "❌ Custom FFmpeg Windows CI başarısız oldu."
    echo ""
    echo "Hata logu:"

    gh run view \
        "$RUN_ID" \
        --repo "$REPO" \
        --log-failed \
        || true

    exit "$WATCH_EXIT"

fi

echo ""
echo "   ✅ Custom FFmpeg Windows derlemesi tamamlandı."
echo ""

# ==============================================================================
# ARTIFACT İNDİR
# ==============================================================================

echo "→ FFmpeg Windows artifact indiriliyor..."

gh run download \
    "$RUN_ID" \
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
    echo "❌ FFmpeg Windows artifact ZIP bulunamadı."
    exit 1
fi

# ==============================================================================
# ARTIFACT AÇ
# ==============================================================================

echo "→ Artifact açılıyor..."

unzip -o \
    "$ZIP_FILE" \
    -d "$FFMPEG_BIN_DIR"

rm -f "$ZIP_FILE"

# ==============================================================================
# KONTROL
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
echo "🎉 CUSTOM FFMPEG WINDOWS HAZIR"
echo "========================================================"
echo "FFmpeg : $FFMPEG_OUTPUT_DIR/ffmpeg.exe"
echo "FFprobe: $FFMPEG_OUTPUT_DIR/ffprobe.exe"
echo "Run ID : $RUN_ID"