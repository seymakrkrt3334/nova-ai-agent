# NOVA son durum

Tarih: 2026-11-18. Gizli dosyalar okunmadı. Veritabanı satırları silinmedi. Docker hacmi yeniden oluşturulmadı. Servisler genel ağa açılmadı. OAuth tarayıcısı açılmadı. E-posta veya sosyal ileti gönderilmedi.

## Kurulan

- Whisper.cpp CPU ikilisi `voice/unpack/Release/whisper-cli.exe`. Çok dilli `ggml-base.bin` indirildi ve SHA1 `465707469ff3a37a2b9b8d8f89f2f99de7299dac` ile doğrulandı.
- Yerel tanıma `VOICE_STT_PROVIDER=whisper` ve `voice/transcribe_wav.py` ile bağlandı. Komut `-l auto -t 4 -ng` kullanır: dil otomatik, 4 iş parçacığı, GPU kapalı.
- Electron 33.2.1 ve electron-builder kuruldu. Taşınabilir paket: `desktop/release/NOVA AI 1.0.0.exe`. İmza atlanmadı çünkü imza bilgisi yok; paket imzasızdır.
- Masaüstü kısayolu `NOVA AI.lnk` hedefi `START_NOVA.bat` ve dosya duruyor.
- Expo bağımlılıkları `mobile` içinde kurulu. `npx tsc --noEmit` çıkış kodu 0.

## Test edilen

- `python -m pytest tests -q` → 54 passed. Gmail, Ollama, veritabanı ve sosyal gönderim sahtedir.
- Masaüstü üretim derlemesi `vite build` ve Electron paketlemesi çıkış kodu 0.
- Anahtarsız `/health` 401. Ollama `/api/tags` 200. Kurulu modeller: `llama3.2:latest`, `nomic-embed-text:latest`, `gemma2:2b`, `gemma2:latest`, `qwen2.5:latest`. Denetim anında bellekte yüklü model yoktu.
- `nova-vector-db` `127.0.0.1:5434` üzerinde bağlantı kabul ediyor. Sayım: 4 hafıza, 22 konuşma, 0 otomasyon, 0 sosyal ileti. Satır silinmedi.
- Windows SAPI sesleri: `en-US Microsoft David Desktop`, `en-US Microsoft Zira Desktop`. Kısa İngilizce cümle seslendirildi.
- Paket arayüzü `http://127.0.0.1:4173` üzerinde 200 döndü. Dil değişimi, ayarlar ve anahtarsız entegrasyon ekranı tarayıcıda kontrol edildi. E-posta içeriği istenmedi.

## Canlı doğrulanan

- Genel JFK örnek sesi İngilizce metne çevrildi: “And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.”
- `START_NOVA.bat` çıkış kodu 0 verdi, ayakta olan API'yi yeniden başlatmadı ve masaüstü paketini açtı. Beş `NOVA AI` süreci ve paket süreci görüldü.
- `STOP_NOVA.bat` NOVA pencerelerini kapatır. Veritabanı konteynerini ve hacmini durdurmaz.
- Kısayol hedefi yerinde.

## Engellenen

- Türkçe Windows sesi yok. Dil paketi kurulmadı; bu sistem genelinde bir değişiklik ister ve onayınız gerekir.
- Türkçe konuşma, Türkçe bir kayıtla canlı denenmedi. Model çok dillidir ve dil seçimi otomatiktir.
- Telefon kaydı m4a üretir. Yerel Whisper yalnız WAV, FLAC, MP3 ve OGG okur. Telefon mikrofonu bu yüzden metne çevrilmez. Cevabı seslendirmek Expo Speech ile durur.
- Google kişileri, takvim ve Gmail canlı verisi, tarayıcı yetkisi siz çalıştırmadan doğrulanmadı. Kapsamlar salt okunurdur.
- Tailscale kurulu değil. Kurulmadı. PostgreSQL ve FastAPI genel ağa açılmadı.
- Android APK üretilmedi. Java 17 ve SDK var. `ANDROID_HOME` tanımsız, `adb` PATH üzerinde değil.
- iOS derlemesi macOS ve Xcode ister.
- WhatsApp ve Instagram gelen kutusu genel webhook ister. Port açılmadı.
- Masaüstü npm denetiminde 29 uyarı var. `npm audit fix --force` çalıştırılmadı.

## 16 GB bellek

Sohbet `num_ctx` 4096, `num_predict` 400 ve `num_thread` 8 ile sınırlı. Sosyal taslak 2048 bağlam kullanır. Whisper GPU kullanmaz. Ek Ollama modelleri diskte durur; sohbet için `llama3.2` ve gömü için `nomic-embed-text` yeterlidir. Modeller silinmedi.

## Elle kalanlar

`MANUAL_TESTS.md` içindeki Google, Gmail ve Tailscale adımlarını siz çalıştırın. Özel içeriği bu sohbete yapıştırmayın. Sonuç olarak yalnız durum kodu ve “oldu / olmadı” yazın.
