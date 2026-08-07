# Video İndirici (MediaDownloader)

Video İndirici (MediaDownloader), taşınabilir bir arayüz sunan bir uygulamadır. Uygulamanın ana çalışma zamanı artık Python odaklıdır: Python/Tkinter GUI ve yeni "toolbox" paketimiz (toolbox/*.py) yt-dlp'yi doğrudan çalıştırır ve çıktısını gerçek zamanlı olarak işler. Bu düzenleme Deno tabanlı yardımcı betiği (yt.ts / settings.ts / deno.json) kaldırıp yerini Python içindeki modüllere bırakmıştır; ancak dağıtılan `bin/` araçları (yt-dlp, ffmpeg, ffprobe, deno) hâlâ desteklenir ve deno binary hâlâ keşfedilir/korunur (geliştirici ihtiyaçları için).

Bu README, depoda yapılan son değişiklikler (toolbox entegrasyonu, portable build güncellemeleri, Deno kaldırılması/yeniden yönlendirme, ffmpeg güncelleme iyileştirmeleri vb.) göz önünde bulundurularak güncellendi.

---

## İçindekiler
- [Öne Çıkan Özellikler](#öne-çıkan-özellikler)  
- [Gereksinimler](#gereksinimler)  
- [Proje Yapısı ve Önemli Dosyalar](#proje-yapısı-ve-önemli-dosyalar)  
- [Hızlı Başlatma (Portable & Geliştirme)](#hızlı-başlatma-portable--geliştirme)  
- [Profiller ve İç Mimari (toolbox)](#profiller-ve-iç-mimari-toolbox)  
- [Güncelleme & Paketleme Araçları](#güncelleme--paketleme-araclari)  
- [Çapraz Platform Davranışları ve Notlar](#çapraz-platform-davranışları-ve-notlar)  
- [Hata Ayıklama ve Sık Karşılaşılan Sorunlar](#hata-ayiklama-ve-sik-karsilasilan-sorunlar)  
- [Lisans ve Yasal Uyarılar / Sorumlu Kullanım](#lisans-ve-yasal-uyarilar--sorumlu-kullanım)

---

## Öne Çıkan Özellikler
- Taşınabilir paketleme: `MediaDownloader` biçiminde dağıtılabilir paket üretimi.  
- Profil tabanlı indirme: `video` / `audio` / `playlist` profilleri; video için tavan çözünürlüğü seçeneği.  
- Python-side unbuffered stdout handling: yt-dlp çıktısı anlık (low-latency) olarak parse edilir ve GUI'ye olaylar halinde iletilir.  
- `bin/` dizinindeki yerel ikililerle çalışma: `yt-dlp`, `ffmpeg`, `ffprobe`, `deno` (opsiyonel).  
- Otomatik / manuel ikili güncelleme desteklenir (`update-bin.sh`).  
- Portable paket üretimi: `build-portable.sh` ve GitHub Actions workflow'u.  
- Yeni modüler kod: `toolbox` paketi içinde komut oluşturma, çıktı parse, profil çözümleme, playlist meta okuma, runner, ve araç yönetimi.

---

## Gereksinimler
- Hedef platform: Windows (birincil hedef). POSIX (Linux/macOS) üzerinde sınırlı destek vardır.  
- Geliştirme ortamı:
  - Python 3.8+  
  - PyInstaller (portable exe üretimi)  
- Gerekli ikililer (`bin/`):
  - `yt-dlp`, `ffmpeg`, `ffprobe` (ve isteğe bağlı `deno`)

Not: Deno tabanlı `yt.ts` betiği bu sürümde projeden kaldırıldı; eğer daha önce kullandıysanız Deno ile ilgili adımlar artık gerekli değil. Ancak tooling sırasında `deno` binary'si hâlâ keşfedilir (araç listesinin bir parçası olarak korunmuştur).

---

## Proje Yapısı ve Önemli Dosyalar
- `video_indirici.py` — Python/Tkinter GUI ve uygulama mantığı, artık `toolbox` ile entegre.  
- `toolbox/` — yeni Python modülleri:
  - `command.py` — komut oluşturma ve cookie argleri
  - `cookies.py` — tarayıcı çerezleri argümanları
  - `metadata.py` — FILE_DONE raporlama, boyut/kbps formatlama
  - `output.py` — çıktı yolu işleme
  - `parser.py` — yt-dlp çıktısını parse ederek tipli olaylar üretir
  - `playlist.py` / `playlist_info.py` — playlist/album çözümleme ve metadata
  - `profiles.py` — ön tanımlı profiller ve format oluşturma
  - `runner.py` — yt-dlp sürecini başlatır, stdout'u işler ve Event nesneleri üretir
  - `tools.py` — uygulama dizini ve bin/ keşfi; subprocess env hazırlama
- `build-portable.sh` — PyInstaller ile portable paket oluşturur ve yeni toolbox/kopyalama mantığına göre çalışır.  
- `update-bin.sh` — `bin/` içindeki ikilileri indirir/günceller.  
- `.gitignore` — eklenen geçici/dosya biçimleri (örn. `.cache/`).

---

## Hızlı Başlatma (Portable & Geliştirme)
1. `portable-app` veya uygulama klasörünü açın.  
2. Uygulama exe'si ile aynı dizinde `bin/` klasörünü sağlayın (ör. `portable-app/bin/yt-dlp.exe`).  
3. Windows: `MediaDownloader.exe` çalıştırın.  
4. Geliştirme:
   - GUI çalıştırma:  
     `python video_indirici.py`  
   - Self-test (GUI olmadan):  
     `python video_indirici.py --self-test`  
   - Not: Deno/yt.ts artık projede yok; `deno run ...` adımları gerekmiyor.

---

## Profiller ve İç Mimari (toolbox)
- Profiller `toolbox.profiles` içinde tanımlıdır:
  - `video`: video+audio birleştirme; çıktı şablonu ve tavan çözünürlüğü (kullanıcı seçeneği).
  - `audio`: tek ses çıkışı, remux/embed seçenekleri.
  - `playlist`: playlist/album odaklı çıktı ve metadata argümanları.
- `toolbox.command.build_command` komut listesi inşa eder; `toolbox.runner.YtDlpRunner` süreci yönetir ve `toolbox.parser.OutputParser` çıktıyı parse ederek GUI için güçlü olaylar üretir.
- `toolbox.tools.Tools.discover()` uygulama dizinini ve `bin/` yollarını çözer; PATH'e `bin/` eklenir ki subprocess'lar ikilileri bulabilsin.

---

## Güncelleme & Paketleme Araçları
- `update-bin.sh`: `bin/` içindeki ikilileri (yt-dlp, deno, ffmpeg/ffprobe) indirir/günceller; GitHub Releases API'sini veya uygun kaynakları kullanır.  
- `build-portable.sh`: PyInstaller ile `--onedir` üretir, `bin/` içindeki ikilileri paket içine kopyalar; TypeScript dosyaları artık kopyalanmıyor (projedeki `.ts` yardımcı dosyeleri kaldırıldı veya python'a taşındı).  
- CI: `.github/workflows/build.yml` Windows üzerinde bu betiği çalıştırır ve `portable-app` artifact'ini yükler.

---

## Çapraz Platform Davranışları ve Notlar
- Python kodu runtime'da platformu tespit eder ve bin/ içindeki ikili adlarını/platform davranışlarını uyarlayabilir.
- `CREATE_NO_WINDOW` gibi subprocess parametrizasyonları yalnızca Windows'ta kullanılır.
- Process sonlandırma:
  - Windows: `taskkill /PID <pid> /T /F`  
  - POSIX: `process.terminate()`  

---

## Hata Ayıklama ve Sık Karşılaşılan Sorunlar
- "Eksik araç dosyası": `bin/` içinde `yt-dlp`, `ffmpeg`, `ffprobe` olduğundan emin olun. GUI araç kontrolü penceresinden de durum kontrolü yapabilirsiniz.
- Playlist çıktıları yanlış yerde: özel çıktı seçtiyseniz GUI veya çıktı parametresinin doğru gönderildiğini kontrol edin; toolbox.playlist padding ve base dir hesaplıyor.
- Canlı ilerleme gözükmüyor: yt-dlp çıktısı artık Python tarafında parse ediliyor; yine de `yt-dlp` sürümü veya bayraklar (örn. `--newline`) etkileyebilir.
- `update-bin.sh` hata veriyorsa: GitHub API rate-limit veya ağ sorunları olabilir; hata mesajlarını kontrol edin.

---

## Lisans ve Yasal Uyarılar / Sorumlu Kullanım
- Üçüncü taraf bileşenler farklı lisanslar altındadır (`yt-dlp`, FFmpeg, Deno vb.). Dağıtmadan önce lisans uyumluluğunu doğrulayın.  
- Bu araç yalnızca indirme hakkınız olan içerikler için kullanılmalıdır. Platform kuralları, telif hakları ve bulunduğunuz ülkenin yasaları kullanıcı sorumluluğundadır.

---