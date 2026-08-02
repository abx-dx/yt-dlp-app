#!/usr/bin/env bash
# ==============================================================================
# Portable Windows Uygulaması Derleme Betiği
# ==============================================================================

set -e

# ==============================================================================
# DİZİN TANIMLARI & MOD BELİRTİMİ
# ==============================================================================

# Betiğin bulunduğu proje klasörü (yt-dlp-downloader)
TARGET_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Eğer GitHub Actions (CI) ortamındaysak farklı, yereldeysek standart yolları kullan
if [ "$CI" = "true" ]; then
    BUILD_MODE="GitHub Actions (CI)"
    PYTHON_EXE="python"
    PORTABLE_APP_DIR="$TARGET_PROJECT_DIR/portable-app"
    PORTABLE_ROOT="$TARGET_PROJECT_DIR"
else
    BUILD_MODE="Portable (Lokal)"
    PORTABLE_ROOT="$(cd "$TARGET_PROJECT_DIR/../.." && pwd)"
    PYTHON_EXE="$PORTABLE_ROOT/apps/python/python.exe"
    PORTABLE_APP_DIR="$PORTABLE_ROOT/portable-app"
fi

# Derlenecek Ana Kod
PY_FILE="$TARGET_PROJECT_DIR/video_indirici.py"


# ==============================================================================
# EKRAN ÇIKTILARI İÇİN WINDOWS YOLU DÖNÜŞÜMÜ
# ==============================================================================

if command -v cygpath >/dev/null 2>&1; then
    DISP_ROOT="$(cygpath -w "$PORTABLE_ROOT")"
    DISP_PROJECT="$(cygpath -w "$TARGET_PROJECT_DIR")"
    DISP_PYTHON="$(cygpath -w "$PYTHON_EXE")"
    DISP_OUTPUT="$(cygpath -w "$PORTABLE_APP_DIR")"
else
    DISP_ROOT="$PORTABLE_ROOT"
    DISP_PROJECT="$TARGET_PROJECT_DIR"
    DISP_PYTHON="$PYTHON_EXE"
    DISP_OUTPUT="$PORTABLE_APP_DIR"
fi


echo "========================================================"
echo "🚀 Derleme Başlatılıyor"
echo "========================================================"
echo "Mod          : $BUILD_MODE"
echo "Kök Dizin    : $DISP_ROOT"
echo "Proje Dizin  : $DISP_PROJECT"
echo "Python       : $DISP_PYTHON"
echo "Çıktı Dizin  : $DISP_OUTPUT"
echo "========================================================"
echo ""


# ==============================================================================
# ÖN KONTROLLER
# ==============================================================================

# Python Varlık Kontrolü (CI ve Lokal ortam tamamen ayrıldı)
if [ "$CI" = "true" ]; then
    if ! command -v python >/dev/null 2>&1; then
        echo "❌ HATA: Python PATH içinde bulunamadı."
        exit 1
    fi
else
    if [ ! -f "$PYTHON_EXE" ]; then
        echo "❌ HATA: Portable Python bulunamadı:"
        echo "$PYTHON_EXE"
        exit 1
    fi
fi

if [ ! -f "$PY_FILE" ]; then
    echo "❌ HATA: video_indirici.py bulunamadı:"
    echo "$PY_FILE"
    exit 1
fi

if ! "$PYTHON_EXE" -m PyInstaller --version >/dev/null 2>&1; then
    echo "❌ HATA: PyInstaller bulunamadı."
    exit 1
fi

echo "Python:"
"$PYTHON_EXE" --version

echo "PyInstaller:"
"$PYTHON_EXE" -m PyInstaller --version

echo ""


# ==============================================================================
# ÇALIŞAN UYGULAMA KONTROLÜ
# ==============================================================================

# Yalnızca CI dışında VE tasklist.exe komutunun var olduğu ortamlarda (Windows/Git Bash) çalışır
if [ "$CI" != "true" ] && command -v tasklist.exe >/dev/null 2>&1; then
    if tasklist.exe 2>/dev/null | grep -qi "MediaDownloader.exe"; then
        echo "❌ HATA: MediaDownloader.exe halen çalışıyor."
        echo "Lütfen uygulamayı kapatıp tekrar deneyin."
        exit 1
    fi
fi

# ==============================================================================
# TEMİZLİK
# ==============================================================================

echo "[1/5] Eski çıktı temizleniyor..."

rm -rf "$PORTABLE_APP_DIR"

if [ -d "$PORTABLE_APP_DIR" ]; then
    echo "❌ HATA: portable-app klasörü temizlenemedi."
    echo "Dosya kilidi olabilir."
    exit 1
fi

rm -rf "$TARGET_PROJECT_DIR/build"
rm -rf "$TARGET_PROJECT_DIR/dist"
rm -f "$TARGET_PROJECT_DIR"/*.spec

mkdir -p "$PORTABLE_APP_DIR"

echo "✅ Temizlik tamamlandı."
echo ""


# ==============================================================================
# PYINSTALLER DERLEME
# ==============================================================================

echo "[2/5] PyInstaller derlemesi..."

(
    cd "$TARGET_PROJECT_DIR" || exit 1
    "$PYTHON_EXE" -m PyInstaller \
        --clean \
        --noconfirm \
        --onedir \
        --windowed \
        --log-level WARN \
        --name "MediaDownloader" \
        video_indirici.py
)

if [ ! -d "$TARGET_PROJECT_DIR/dist/MediaDownloader" ]; then
    echo "❌ HATA: PyInstaller çıktısı bulunamadı."
    exit 1
fi

cp -a \
"$TARGET_PROJECT_DIR/dist/MediaDownloader/." \
"$PORTABLE_APP_DIR/"

echo "✅ EXE paketi oluşturuldu."
echo ""


# ==============================================================================
# BIN BAĞIMLILIKLARI
# ==============================================================================

echo "[3/5] Harici araç bağımlılıkları kontrol ediliyor..."

mkdir -p "$PORTABLE_APP_DIR/bin"

# .exe uzantısı zorunluluğunu kaldırarak regex'i esnetiyoruz
DEPENDENCIES=$(grep -oE 'bin[/\\][A-Za-z0-9._-]+' "$PY_FILE" \
    | sed 's|\\|/|g' \
    | sed 's/\.exe$//' \
    | sort -u)

if [ -z "$DEPENDENCIES" ]; then
    echo "❌ HATA: video_indirici.py içinde bin bağımlılığı bulunamadı."
    exit 1
fi

while IFS= read -r DEP
do
    BASE_NAME="$(basename "$DEP")"
    
    # İşletim sistemine veya CI ortamına göre uzantı yönetimi
    if [ "$CI" = "true" ] || [[ "$(uname -s)" != "MINGW"* && "$(uname -s)" != "MSYS"* ]]; then
        FILE_NAME="$BASE_NAME"
    else
        FILE_NAME="${BASE_NAME}.exe"
    fi

    SOURCE="$TARGET_PROJECT_DIR/bin/$FILE_NAME"

    # Eğer uzantılı dosya bulunamazsa uzantısız halini dene (fallback)
    if [ ! -f "$SOURCE" ] && [ -f "$TARGET_PROJECT_DIR/bin/$BASE_NAME" ]; then
        SOURCE="$TARGET_PROJECT_DIR/bin/$BASE_NAME"
        FILE_NAME="$BASE_NAME"
    fi

    if [ ! -f "$SOURCE" ]; then
        echo "❌ Eksik bağımlılık:"
        echo "   $SOURCE"
        exit 1
    fi

    cp "$SOURCE" "$PORTABLE_APP_DIR/bin/"
    echo "   + $FILE_NAME"

done <<< "$DEPENDENCIES"

echo "✅ Bin araçları tamamlandı."
echo ""

# Linux / POSIX ortamlarında ikililere çalıştırma izni ver (Windows'ta etki etmez)
if [ "$CI" = "true" ] || [[ "$(uname -s)" != "MINGW"* && "$(uname -s)" != "MSYS"* ]]; then
    chmod +x "$PORTABLE_APP_DIR/bin/"* 2>/dev/null || true
fi


# ==============================================================================
# TYPESCRIPT DOSYALARI
# ==============================================================================

echo "[4/5] TypeScript dosyaları kopyalanıyor..."

shopt -s nullglob

TS_FILES=("$TARGET_PROJECT_DIR"/*.ts)

if [ ${#TS_FILES[@]} -eq 0 ]; then
    echo "❌ HATA: Proje kökünde .ts dosyası bulunamadı."
    exit 1
fi

for TS in "${TS_FILES[@]}"
do
    cp "$TS" "$PORTABLE_APP_DIR/"
    echo "   + $(basename "$TS")"
done

shopt -u nullglob

echo "✅ TypeScript dosyaları tamamlandı."
echo ""


# ==============================================================================
# SON TEMİZLİK VE BİLGİLENDİRME
# ==============================================================================

echo "[5/5] Geçici dosyalar temizleniyor..."

rm -rf "$TARGET_PROJECT_DIR/build"
rm -rf "$TARGET_PROJECT_DIR/dist"
rm -f "$TARGET_PROJECT_DIR"/*.spec

echo ""
echo "========================================================"
echo "🎉 PORTABLE PAKET HAZIR"
echo ""
echo "Konum:"
echo "$DISP_OUTPUT"
echo "========================================================"

# CI ortamı değilse ve explorer.exe komutu varsa klasörü aç
if [ "$CI" != "true" ] && command -v explorer.exe >/dev/null 2>&1; then
    explorer.exe "$(cygpath -w "$PORTABLE_APP_DIR" 2>/dev/null || echo "$PORTABLE_APP_DIR")"
fi