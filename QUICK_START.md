# NOVA hızlı başlangıç

NOVA bu bilgisayarda kalır. PostgreSQL ve FastAPI genel ağa açılmaz.

## Başlatma

1. Ollama yerelde çalışıyor olsun. Model: `llama3.2` ve gömü modeli `nomic-embed-text`.
2. `nova-vector-db` konteyneri duruyorsa `START_NOVA.bat` onu `docker start` ile açar. Hacmi yeniden oluşturmaz.
3. `START_NOVA.bat` API'yi `127.0.0.1:8001` üzerinde, yalnız kapalıysa başlatır. `desktop\release\NOVA AI 1.0.0.exe` varsa onu açar. Paket yoksa geliştirme arayüzünü `127.0.0.1:5173` üzerinde açar.
4. Sağlık kontrolü anahtarsız `401` görürse API ayaktadır. Bağlantı reddi başarısızlıktır.
5. Arayüzde Ayarlar bölümüne API adresini ve `X-API-Key` değerini yazın. Anahtar sekme oturumunda kalır. Paket arayüzü `http://127.0.0.1:4173` adresindedir.

Durdurmak için `STOP_NOVA.bat`. Bu komut NOVA pencerelerini kapatır, veritabanı konteynerini ve hacmini silmez.

Masaüstü kısayolu: `powershell -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1`

## Günlük kullanım

- Sohbet geçmişi oturum kimliğiyle saklanır. Kalıcı hafıza oturumlar arasında aranır.
- Gmail, kişiler ve takvim için `backend` klasöründe `python scripts/authorize_google.py gmail` komutu adımları yazar. `--launch` vermeden tarayıcı açılmaz.
- Ses için basılı tutun. Bırakınca WAV kaydı yerel Whisper'a gider. İptal, kaydı ve sesi durdurur. Sürekli dinleme yoktur.
- Çok dilli taban model kuruludur. İngilizce örnek ses canlı çevrildi. Türkçe bir kayıt henüz canlı denenmedi. Windows'ta yalnız İngilizce SAPI sesleri vardır; Türkçe ses paketi kurulmadı.

## Telefon

`mobile` içinde bağımlılıklar kurulu ve tür denetimi geçti. API adresi ve anahtar SecureStore'dadır. Telefon mikrofonu m4a üretir; yerel tanıma bunu kabul etmez. Cevabı seslendirmek Expo Speech ile çalışır.

Fiziksel telefon `127.0.0.1` adresine ulaşamaz. Tailscale bu bilgisayarda kurulu değildir. Kurmak sizin kararınızdır. PostgreSQL `127.0.0.1:5434` üzerinde kalır ve tailnet'e açılmaz. Ayrıntı `SECURITY.md` ve `MANUAL_TESTS.md` içindedir.
