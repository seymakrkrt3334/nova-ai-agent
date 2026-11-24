# NOVA güvenlik notu

Bu not kod incelemesine ve otomatik testlere dayanır. Canlı bir sızma testi değildir. Gizli dosyalar okunmadan yazıldı.

## Kimlik doğrulama

Tüm API uçları `X-API-Key` ister. Karşılaştırma sabit zamanlıdır. Anahtar yoksa servis 503, yanlış anahtarsa 401 döner. Masaüstü anahtarı `sessionStorage`, mobil anahtar Expo SecureStore içindedir. Betikler anahtarı içermez.

## CORS

İzin verilen kaynaklar `http://127.0.0.1:5173`, `http://localhost:5173`, `http://127.0.0.1:4173` ve `http://localhost:4173`. Yöntemler GET, POST, PATCH ve DELETE. Başlıklar `Content-Type` ve `X-API-Key`. Joker kaynak yoktur. Electron paketi arayüzü yalnız `127.0.0.1:4173` üzerinden sunar.

## Gizliler ve OAuth

`.env`, `credentials.json` ve `token*.json` repoya girmez. Ayar nesnesinin temsili `Settings(redacted)` olur. Google betiği `--launch` olmadan tarayıcı açmaz ve yazma kapsamı istemez. Gmail okuma yolu, belirteç yoksa zamanlayıcıdan tarayıcı açmaz. Belirteç dosyasının içeriği durum ucunda gösterilmez.

## SQL ve SSRF

Sorgular parametrelidir. Web okuma, özel ağ, yerel adres ve meta veri uçlarını reddeder. Sosyal gönderim adresleri sabit resmi alan adlarıdır ve yönlendirme izlenmez. Sohbet kimliği sınırlı karakter kümesine alınır.

## Araçlar ve istem enjeksiyonu

Model yalnız kayıtlı araçları seçebilir. E-posta gönderme aracı yoktur. Araç çıktısı özete veri olarak gider. Sosyal taslak, gelen metni talimat saymaz. Varsayılan taslak modeli çağırmaz.

## Otomasyon

Otomatik çalışma yalnız oluşturma anında `authorize` ve eşleşen salt okunur kapsam varsa açılır. Yazma ve onaysız işler onay bekler. Aynı pencere anahtarı ikinci kez çalışmaz. Yetki kaldırma otomatik bayrağı kapatır. Zamanlayıcı yanıt gövdesine iş istemini koymaz.

## Hafıza

Kişisel bilgi açık onay olmadan kaydedilmez. Hafıza araması oturumdan bağımsızdır. Sohbet geçmişi oturumla sınırlanabilir. Sistem rolündeki geçmiş satırlar modele tekrar verilmez.

## Ağ

API `127.0.0.1:8001` üzerinde kalır. PostgreSQL `127.0.0.1:5434` üzerindedir. Tailscale bu bilgisayarda kurulu değildir. Kurulursa FastAPI yalnız tailnet içinde `tailscale serve` ile açılır. PostgreSQL tailnet'e de açılmaz. WhatsApp ve Instagram webhook'u için genel port açılmaz.

## Bağımlılıklar

Electron kurulumu masaüstü ağacında 29 uyarı bildirdi: 4 orta, 24 yüksek, 1 kritik. Mobil Expo kurulumunda 51 uyarı göründü. `npm audit fix --force` çalıştırılmadı. Whisper taban modeli ve imzasız Electron paketi indirildi. Paket kod imzası taşımaz. Windows SmartScreen uyarı verebilir.
