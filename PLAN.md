# NOVA planı

Özel, yerel öncelikli kişisel asistan. Bu dosya kilometre taşlarını ve kabul kriterlerini tutar. Mevcut veritabanı hacimleri, OAuth izinleri ve gizli dosyalar bu planda değiştirilmez.

## Bu tur

Faz 1–12 kodu duruyor. Son test: `python -m pytest tests -q` → 54 passed. Gmail, Ollama, kişiler, takvim, web ve resmi sosyal gönderim testlerde sahtedir. Çok dilli Whisper taban modeli ve imzasız Windows paketi kuruldu. İngilizce örnek ses canlı çevrildi. OAuth tarayıcısı açılmadı. Veritabanı satırları silinmedi. Gmail kapsamı salt okunurdur.

## Faz 1 — Mevcut sistemi denetle ve güvenli biçimde düzelt

Kabul kriterleri:

- İçe aktarmalar, bağımlılıklar, şema ve uçlar gizli dosya içeriği okunmadan karşılaştırılır.
- `requirements.txt` çalışan kodun kullandığı paketleri listeler; kullanılmayan uzak model paketleri listeden çıkar.
- Ayarlar `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_EMBED_MODEL`, `DATABASE_URL` ve `NOVA_API_KEY` adlarıyla tek yerden okunur. Ayar çıktısı gizli değer göstermez.
- Gmail araması boş, aşırı uzun veya geçersiz limit ile dış servise gitmez. Hata cevabı ayrıntı sızdırmaz.
- Hafıza vektörü 768 boyutlu sonlu sayılardan oluşur. Metin ve kategori sınırları şemayla uyumludur.
- Şema dosyası yalnız `CREATE ... IF NOT EXISTS` içerir ve mevcut hacme uygulanmadan durur.
- API anahtarı olmayan istekler `/health` ve `/chat` üzerinde reddedilir.
- Testler gerçek Gmail, Ollama ve veritabanı yerine sahte hizmet kullanır.

## Faz 2 — Araç kaydı ve sınırlı yürütme

Kabul kriterleri:

- İlk katalog `chat`, `gmail_search`, `memory_search` ve `memory_save` ile başladı. Gönderme aracı yok. Takvim yazma ancak sonraki fazdaki onay koduyla önerilir.
- Model kararı JSON olarak doğrulanır. Bilinmeyen araç veya bozuk JSON sohbete düşer.
- Gmail sorgusu serbest metin olarak kabul edilmez. Konum ve zaman aralığı kullanıcının ifadesinden kurulur; konu ve gönderen tırnak içinde kalır.
- "Bugün gönderilmiş" isteği gelen kutusuna zorlanmaz.
- Araç döngüsü en fazla 3 adımdır, ardından sonuç özetlenir.
- Model, açık kayıt isteği olmadan hafızaya yazamaz. Açık kayıtta saklanan metin kullanıcının yazdığı metindir.
- Yönlendirici, e-posta gövdesini görmez. Özet istemi araç çıktısını talimat değil veri kabul eder.
- Model servisi yoksa cevap 503 olur ve iç hata metni istemciye dönmez.

## Faz 3 — Kalıcı hafıza

Kabul kriterleri:

- Anlamsal arama mesafe eşiği ve kaynak bilgisi döndürür.
- Sohbetler oturum kimliğiyle saklanır, listelenir ve silinebilir.
- Kayıt düzenleme `updated_at` alanını günceller.
- Kullanıcı hafızayı dışa aktarabilir ve kategorilere göre silebilir.
- Dış içerik hafıza talimatı olarak çalıştırılmaz.

## Faz 4 — Gmail

Kabul kriterleri:

- Sayfalama belirteci ile devam edilir.
- Tam ileti yalnız açık istekte ve salt okunur kapsamla alınır.
- Arama, özet ve yanıt taslağı üretilir.
- Gönderme ayrı OAuth onayı ve kullanıcı onayı olmadan yoktur.

## Faz 5 — Kişiler ve Takvim

Kabul kriterleri:

- En dar Google kapsamları kullanılır.
- Okuma ve taslak serbesttir. Oluşturma, değiştirme ve silme açık onay ister.
- Kapsam değişikliği ayrıca onaylanmadan yapılmaz.

## Faz 6 — Web arama

Kabul kriterleri:

- Sağlayıcı ayarla seçilir ve anahtar repoya girmez.
- Sonuçlar kaynak adresiyle döner.
- Sayfa içeriği talimat olarak yürütülmez.

## Faz 7 — Masaüstü sohbet arayüzü

Kabul kriterleri:

- Koyu mor, dar ve geniş ekranda kullanılabilir sohbet.
- Konuşmalar, hafıza, entegrasyonlar ve ayarlar aynı API anahtarıyla çalışır.
- Arayüz gizli değerleri kalıcı olarak göstermez.

## Faz 8 — Expo mobil uygulama

Kabul kriterleri:

- API adresi yapılandırılır. Fiziksel cihazda `localhost` kullanılmaz.
- API anahtarı güvenli depolamadadır.
- Sohbet, hata ve boş durumlar uçtan uca denenir.

## Faz 9 — Yerel ses

Kabul kriterleri:

- Metinden sese ve sesten metne yerel motorlarla, mümkün olan platformda çalışır.
- Ses kaydı açık kullanıcı eylemiyle başlar.

## Faz 10 — Zamanlanmış işler

Kabul kriterleri:

- İşler listelenir, durdurulur ve silinir.
- Dış yan etki içeren iş onay ister.
- Çalışma kayıtları gizli içerik dökmez.

## Faz 11 — WhatsApp ve Instagram

Kabul kriterleri:

- Yalnız resmi API'ler değerlendirilir.
- Resmi olmayan istemci, oturum devralma veya platform kısıtını aşma uygulanmaz.
- Desteklenmeyen yüzey dokümante edilip bırakılır.

## Faz 12 — Test, kurulum ve dağıtım

Kabul kriterleri:

- Sahte entegrasyonlarla otomatik testler tekrar çalıştırılabilir.
- Kurulum betiği gizli dosya üretmez ve mevcut hacmi silmez.
- Dağıtım notu servisi herkese açık bağlamayı önermez.

## Faz 11 — Resmi sosyal yüzeyler

Kabul kriterleri:

- Yalnız Telegram Bot API, WhatsApp Business Cloud API ve Instagram Messaging API tanımlanır.
- Kişisel hesaplar için resmi olmayan istemci yoktur.
- Gönderim açık onay olmadan yapılmaz.
- Platform kısıtları, hesap türü ve olası ücret belgede durur.

## Faz 12 — Günlük kullanım

Kabul kriterleri:

- Arayüz, ses, otomasyon ve entegrasyon durumları aynı yerel API'ye bağlıdır.
- Salt okunur otomasyon yalnız oluşturma sırasında verilen yetkiyle çalışır. Yazma işlemi ayrıca onay ister.
- Başlatma betiği mevcut konteyneri yeniden oluşturmaz.
- Gizli dosyalar rapora girmez.

## Bilinçli olarak ertelenenler

- Docker hacimlerini yeniden oluşturmak.
- OAuth tarayıcısını açmak veya kapsamı genişletmek.
- E-posta, kişi, takvim veya sosyal ileti göndermek.
- Türkçe Windows ses paketini kurmak.
- Tailscale kurmak veya bir portu tailnet dışına açmak.
- Android APK üretmek.
- Sürekli mikrofon dinlemek.
- FastAPI ya da PostgreSQL portunu herkese açmak.
- Ücretli API açmak.
