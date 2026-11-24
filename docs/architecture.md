# NOVA mimarisi

Masaüstü Vite arayüzü, Electron paketi ve Expo mobil istemci `X-API-Key` ile yerel FastAPI servisine konuşur. Servis Ollama (`llama3.2` ve `nomic-embed-text`) ve yerel pgvector hafızasını kullanır. Gmail salt okunur OAuth kapsamıyla bağlanır. CORS `5173` ve `4173` yerel kaynaklarına izin verir. Electron statik dosyayı yalnız `127.0.0.1:4173` üzerinde sunar.

`/chat` isteği önce açık hafıza kaydını ve bekleyen takvim onayını ayırır. Diğer mesajlarda model, doğrulanmış katalogdan en fazla üç adım seçer: sohbet, hafıza, salt okunur Gmail, web, kişiler ve takvim önerisi. Gmail sorgusu serbest metin değildir. Araç çıktısı özete veri olarak gider, talimat olarak gitmez. Web adresleri özel ağlara ve meta veri uçlarına açılmaz.

Gmail kapsamı `gmail.readonly` olarak kalır. Kişiler `contacts.readonly`, takvim okuma `calendar.readonly` kapsamını ayrı belirteç dosyasında bekler. Takvim yazma `calendar.events` kapsamı tanımlıdır fakat otomatik istenmez; değişiklik onay kodu olmadan servise gitmez. E-posta gönderme yoktur.

Ses kaydı yalnız bas-konuş eylemiyle başlar. Masaüstü 16 kHz WAV gönderir. Whisper.cpp çok dilli taban modeli CPU üzerinde çalışır. WAV dışı yük 415 döner. Telefonun m4a kaydı kabul edilmez. Seslendirme tarayıcının veya Expo Speech’in yerel motorundadır ve durdurulabilir. Windows'ta kurulu sesler İngilizcedir. Otomasyon satırları `automations` tablosundadır. Süresi gelen iş `awaiting_confirmation` olur; onay, istemi sohbete taşır ve aracı kendisi çalıştırmaz.

Sosyal katman yalnız resmi Bot, WhatsApp Business Cloud ve Instagram Messaging API'lerini tanır. Gönderim onay ister. Kişisel gelen kutusu okunmaz.

Salt okunur otomasyon, oluşturma anındaki yetki ve kapsam eşleşirse zamanlayıcıda çalışır. Yazma işlemleri onayda kalır. Aynı zaman penceresi yeniden çalışmaz.

Üretim için servis yerel arabirimde kalır ve API anahtarı zorunludur. Telefon erişimi Tailscale gibi özel bir ağla sınırlıdır. PostgreSQL herkese açık yayınlanmaz.
