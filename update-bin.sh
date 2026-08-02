#!/usr/bin/env bash

# Betiğin bulunduğu yer (Proje Kök Dizini)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$PROJECT_DIR/bin"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

# bin klasörü yoksa oluştur
mkdir -p "$BIN_DIR"

echo "========================================================"
echo " Proje İçi Bağımlılıklar Güncelleniyor..."
echo " Hedef Klasör: /$PROJECT_NAME/bin"
echo "========================================================"
echo ""

# Helper: JSON içinden download URL'sini güvenli çıkaran fonksiyon
get_json_url() {
    local json="$1"
    local pattern="$2"
    echo "$json" | grep -oP '"browser_download_url":\s*"\K[^"]+' | grep -E "$pattern" | head -n 1
}

# ----------------------------------------------------------
# 1. YT-DLP GÜNCELLEME
# ----------------------------------------------------------
echo "[1/3] yt-dlp güncelleniyor..."

if [ -f "$BIN_DIR/yt-dlp.exe" ]; then
    if "$BIN_DIR/yt-dlp.exe" -U; then
        echo "   ✅ yt-dlp güncelleme kontrolü tamamlandı."
    else
        echo "   ❌ yt-dlp güncelleme hatası oluştu."
    fi
else
    echo "   --> yt-dlp bulunamadı, API üzerinden indiriliyor..."
    YTDLP_JSON=$(curl -fsSL https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest)
    YTDLP_URL=$(get_json_url "$YTDLP_JSON" "yt-dlp\.exe$")

    if [ -n "$YTDLP_URL" ]; then
        if curl -fsSL "$YTDLP_URL" -o "$BIN_DIR/yt-dlp.exe" && [ -s "$BIN_DIR/yt-dlp.exe" ]; then
            echo "   ✅ yt-dlp.exe başarıyla indirildi!"
        else
            echo "   ❌ yt-dlp indirme başarısız oldu veya dosya 0 byte indi."
        fi
    else
        echo "   ❌ yt-dlp indirme bağlantısı alınamadı."
    fi
fi
echo ""

# ----------------------------------------------------------
# 2. DENO GÜNCELLEME
# ----------------------------------------------------------
echo "[2/3] deno güncelleniyor..."

if [ -f "$BIN_DIR/deno.exe" ]; then
    if "$BIN_DIR/deno.exe" upgrade; then
        echo "   ✅ deno güncelleme kontrolü tamamlandı."
    else
        echo "   ❌ deno güncelleme hatası oluştu."
    fi
elif [ -f "$BIN_DIR/deno" ]; then
    if "$BIN_DIR/deno" upgrade; then
        echo "   ✅ deno güncelleme kontrolü tamamlandı."
    else
        echo "   ❌ deno güncelleme hatası oluştu."
    fi
else
    echo "   --> deno bulunamadı, API üzerinden indiriliyor..."
    DENO_JSON=$(curl -fsSL https://api.github.com/repos/denoland/deno/releases/latest)
    DENO_URL=$(get_json_url "$DENO_JSON" "x86_64-pc-windows-msvc\.zip$")

    if [ -n "$DENO_URL" ]; then
        DENO_ZIP="$BIN_DIR/deno.zip"
        if curl -fsSL "$DENO_URL" -o "$DENO_ZIP" && [ -s "$DENO_ZIP" ]; then
            if unzip -o "$DENO_ZIP" -d "$BIN_DIR/" > /dev/null; then
                rm -f "$DENO_ZIP"
                echo "   ✅ deno.exe başarıyla indirildi ve çıkarıldı!"
            else
                echo "   ❌ Deno ZIP arşivi açılamadı."
            fi
        else
            echo "   ❌ Deno indirme başarısız oldu veya 0 byte indi."
        fi
    else
        echo "   ❌ Deno indirme bağlantısı alınamadı."
    fi
fi
echo ""

# ----------------------------------------------------------
# 3. FFMPEG & FFPROBE GÜNCELLEME (Latest Auto-Build)
# ----------------------------------------------------------
echo "[3/3] ffmpeg ve ffprobe güncelleniyor (yt-dlp/FFmpeg-Builds Latest)..."

NEED_FFMPEG_UPDATE=0
FFMPEG_VERSION_FILE="$BIN_DIR/.ffmpeg_version"

# Doğrudan repodaki en son Auto-Build JSON verisini çekiyoruz
FFMPEG_JSON=$(curl -fsSL https://api.github.com/repos/yt-dlp/FFmpeg-Builds/releases/latest)

if [ -z "$FFMPEG_JSON" ]; then
    echo "    ❌ FFmpeg sürüm bilgisi GitHub API'den alınamadı (Kota aşımı veya ağ hatası)."
else
    # 64-bit Windows GPL ZIP indirme bağlantısını çek
    FFMPEG_URL=$(echo "$FFMPEG_JSON" | grep -oP '"browser_download_url":\s*"\K[^"]+' | grep -E "win64-gpl\.zip$" | head -n 1)
    
    # Güncelleme takibi için yayının benzersiz tarih/saat bilgisini al
    REMOTE_DATE=$(echo "$FFMPEG_JSON" | grep -oP '"published_at":\s*"\K[^"]+' | head -n 1)

    if [ -z "$FFMPEG_URL" ]; then
        echo "    ❌ FFmpeg indirme bağlantısı filtrelenemedi."
    else
        if [ ! -f "$BIN_DIR/ffmpeg.exe" ] || [ ! -f "$BIN_DIR/ffprobe.exe" ]; then
            NEED_FFMPEG_UPDATE=1
        elif [ -f "$FFMPEG_VERSION_FILE" ]; then
            LOCAL_DATE=$(cat "$FFMPEG_VERSION_FILE")
            if [ "$LOCAL_DATE" != "$REMOTE_DATE" ]; then
                NEED_FFMPEG_UPDATE=1
            fi
        else
            NEED_FFMPEG_UPDATE=1
        fi

        if [ "$NEED_FFMPEG_UPDATE" -eq 1 ]; then
            echo "    --> En son FFmpeg Auto-Build sürümü indiriliyor..."
            FFMPEG_ZIP="$BIN_DIR/ffmpeg_temp.zip"
            FFMPEG_TEMP_DIR="$BIN_DIR/ffmpeg_temp"

            if curl -fsSL "$FFMPEG_URL" -o "$FFMPEG_ZIP" && [ -s "$FFMPEG_ZIP" ]; then
                mkdir -p "$FFMPEG_TEMP_DIR"
                
                if unzip -o "$FFMPEG_ZIP" -d "$FFMPEG_TEMP_DIR" > /dev/null; then
                    find "$FFMPEG_TEMP_DIR" -type f -name "ffmpeg.exe" -exec mv -f {} "$BIN_DIR/" \;
                    find "$FFMPEG_TEMP_DIR" -type f -name "ffprobe.exe" -exec mv -f {} "$BIN_DIR/" \;
                    
                    rm -rf "$FFMPEG_ZIP" "$FFMPEG_TEMP_DIR"

                    if [ -f "$BIN_DIR/ffmpeg.exe" ] && [ -f "$BIN_DIR/ffprobe.exe" ]; then
                        echo "$REMOTE_DATE" > "$FFMPEG_VERSION_FILE"
                        echo "    ✅ ffmpeg.exe ve ffprobe.exe başarıyla güncellendi!"
                    else
                        echo "    ❌ Hata: FFmpeg/FFprobe dosyaları klasöre taşınamadı."
                    fi
                else
                    echo "    ❌ FFmpeg ZIP arşivi açılamadı veya bozuk indirildi."
                    rm -rf "$FFMPEG_ZIP" "$FFMPEG_TEMP_DIR"
                fi
            else
                echo "    ❌ FFmpeg indirme işlemi başarısız oldu veya 0 byte indi."
            fi
        else
            echo "    ✅ ffmpeg ve ffprobe zaten en güncel Auto-Build sürümünde."
        fi
    fi
fi

echo ""
echo "========================================================"
echo " İşlem Tamamlandı! Tüm araçlar /$PROJECT_NAME/bin/ klasöründe."
echo "========================================================"