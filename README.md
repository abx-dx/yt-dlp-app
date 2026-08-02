# Video İndirici (MediaDownloader)

Video İndirici (MediaDownloader), Windows odaklı taşınabilir bir arayüz sunan bir uygulamadır. Python + Tkinter ile geliştirilen GUI, indirme operasyonlarını Deno yardımcı betiği (`yt.ts`) aracılığıyla yürütür: Python arayüzü kullanıcı etkileşimini yönetir; Deno betiği ise `yt-dlp` çağrılarını oluşturur, çıktıyı işler ve anlık (unbuffered) çıktı akışı sağlar.

Bu README, depoda yapılan son değişiklikler (portable build, çapraz platform ikili desteği, `update-bin` ve `build-portable` betikleri, Deno entegrasyonu vb.) göz önünde bulundurularak hazırlanmıştır.

---

## İçindekiler
- [Öne Çıkan Özellikler](#öne-çıkan-özellikler)  
- [Gereksinimler](#gereksinimler)  
- [Proje Yapısı ve Önemli Dosyalar](#proje-yapısı-ve-önemli-dosyalar)  
- [Hızlı Başlatma (Portable & Geliştirme)](#hızlı-başlatma-portable--geliştirme)  
- [Profiller ve Deno Betiği (yt.ts)](#profiller-ve-deno-betiği-ytts)  
- [Güncelleme & Paketleme Araçları](#güncelleme--paketleme-araçları)  
- [Çapraz Platform Davranışları ve Notlar](#çapraz-platform-davranışları-ve-notlar)  
- [Hata Ayıklama ve Sık Karşılaşılan Sorunlar](#hata-ayıklama-ve-sık-karşılaşılan-sorunlar)  
- [Lisans ve Yasal Uyarılar / Sorumlu Kullanım](#lisans-ve-yasal-uyarılar--sorumlu-kullanım)  

---

## Öne Çıkan Özellikler
- Taşınabilir paketleme: `MediaDownloader.exe` biçiminde dağıtılabilir paket üretimi.  
- Profil tabanlı indirme: `video` / `audio` / `playlist` profilleri.  
- Deno ile unbuffered stdout/stderr akışı: düşük gecikmeli ilerleme, `FILE_DONE` olayları.  
- `bin/` dizininde yerel ikililerle çalışma: `yt-dlp`, `ffmpeg`, `ffprobe`, `deno`.  
- Otomatik / manuel ikili güncelleme: `update-bin.sh`.  
- Portable paket üretimi: `build-portable.sh` ve GitHub Actions workflow'u.  
- GUI: Türkçe arayüz, sağ-tık (Kes/Kopyala/Yapıştır/Tümünü Seç) içerik menüsü, ilerleme çubuğu, playlist sayaçları.

---

## Gereksinimler
- **Hedef platform:** Windows (birincil hedef). POSIX (Linux/macOS) üzerinde sınırlı destek vardır.  
- **Geliştirme ortamı:**
  - Python 3.8+  
  - PyInstaller (portable exe üretimi)  
  - Deno (≥ 1.x)  
- **Gerekli ikililer (`bin/`):**
  - `yt-dlp`  
  - `ffmpeg`  
  - `ffprobe`  
  - `deno`

> Not: `build-portable.sh` ve `update-bin.sh` betikleri, CI veya yerel ortamda `bin/` dizinine gerekli araçları koymaya yardımcı olur.

---

## Proje Yapısı ve Önemli Dosyalar
- `video_indirici.py` — Python/Tkinter GUI ve uygulama mantığı.  
- `yt.ts` — Deno yardımcı betik: `yt-dlp` argümanlarını oluşturur, playlist bilgilerini okur, `FILE_DONE` olayları ve anlık çıktı akışı sağlar.  
- `settings.ts` — Yapılandırma (ytdlp, ffmpeg, profiller, çerez ayarları).  
- `yt-dlp.conf` — ek `yt-dlp` bayrakları (ör. `--newline`).  
- `update-bin.sh` — `bin/` içindeki ikilileri indirir / günceller.  
- `build-portable.sh` — PyInstaller ile portable paket oluşturur.  
- `.github/workflows/build.yml` — CI workflow (Windows).

---

## Hızlı Başlatma (Portable & Geliştirme)
1. `portable-app` veya uygulama klasörünü açın.  
2. Uygulama exe'si ile aynı dizinde `bin/` klasörünü sağlayın (ör. `portable-app/bin/yt-dlp.exe`).  
3. **Windows:** `MediaDownloader.exe` çalıştırın.  
4. Geliştirme:
   - GUI çalıştırma:  
     `python video_indirici.py`  
   - Self-test (GUI olmadan):  
     `python video_indirici.py --self-test`  
   - Deno betiğini manuel çalıştırma (örnek):  
     `deno run --allow-read --allow-write --allow-run yt.ts video "https://..." --output ./downloads`

---

## Profiller ve Deno Betiği (yt.ts)
- Profiller `settings.ts` içinde tanımlıdır. Örnek:
  - `video`: video+audio birleştirme, çıktı şablonu.  
  - `audio`: yalnızca ses, remux/embed seçenekleri.  
  - `playlist`: playlist odaklı çıktı, padding hesaplaması.  
- GUI'den seçilen profil, Deno betiğine iletilir; Deno uygun `yt-dlp` argümanlarını oluşturur.  
- "Firefox çerezlerini kullan" seçilirse Deno `--cookies-from-browser firefox` ekler; çerezler uygulamada saklanmaz.

---

## Güncelleme & Paketleme Araçları
- **`update-bin.sh`**: `bin/` içindeki ikilileri (yt-dlp, deno, ffmpeg/ffprobe) indirir/günceller; GitHub Releases API'sini kullanır.  
- **`build-portable.sh`**: PyInstaller ile `--onedir` üretir, `bin/` ve `.ts` dosyalarını `portable-app` içine kopyalar; POSIX için `chmod +x` uygular.  
- CI: `.github/workflows/build.yml` Windows üzerinde bu betiği çalıştırır ve `portable-app` artifact'ini yükler.

---

## Çapraz Platform Davranışları ve Notlar
- Python kodu runtime'da `EXE_EXT` / `IS_WINDOWS` belirleyip `bin/` içindeki isimleri platforma göre uyarlıyor.  
- `CREATE_NO_WINDOW` gibi `subprocess` parametreleri yalnızca Windows'ta kullanılır.  
- **Process sonlandırma:**
  - Windows: `taskkill /PID <pid> /T /F`  
  - POSIX: `process.terminate()`  
- Betikler POSIX uyumluluğu düşünülerek genişletildi; ana dağıtım hedefi Windows'tur.

---

## Hata Ayıklama ve Sık Karşılaşılan Sorunlar
- **"Eksik araç dosyası":** `bin/` içinde `yt-dlp`, `ffmpeg`, `ffprobe`, `deno` olduğundan emin olun.  
- **Playlist çıktıları yanlış yerde:** özel output seçtiyseniz GUI veya `--output` ile base dizini doğru gönderin; `yt.ts` padding hesaplar.  
- **Canlı ilerleme gözükmüyor:** `yt.ts` stdout/stderr'yi unbuffered okur; yine de `yt-dlp`'nin `--newline`/`--no-quiet` gibi ayarlarının etkin olduğundan emin olun.  
- **`update-bin.sh` hata veriyorsa:** GitHub API rate-limit veya ağ sorunları olabilir; hata mesajlarını kontrol edin.

---

## Lisans ve Yasal Uyarılar / Sorumlu Kullanım
- Üçüncü taraf bileşenler farklı lisanslar altındadır (`yt-dlp`, FFmpeg, Deno vb.). Dağıtmadan önce lisans uyumluluğunu doğrulayın.  
- Projede lisans/üçüncü taraf notları için `LICENSE` ve `THIRD_PARTY_NOTICES.txt` dosyalarını eklemeyi düşünün.

### Sorumlu Kullanım (Türkçe)
Bu araç yalnızca indirme hakkınız olan içerikler için kullanılmalıdır. Platform kuralları, telif hakları ve bulunduğunuz ülkenin yasaları kullanıcı sorumluluğundadır.

### Responsible Use (English)
This tool should only be used to download content you have the right to download. Compliance with platform terms of service, copyright law, and the laws of your jurisdiction is the user's responsibility.