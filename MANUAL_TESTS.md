# Elle test rehberi

Bu listeyi kendi bilgisayarınızda uygulayın. Özel e-posta, kişi, takvim, sohbet veya anahtar değerini Cursor sohbetine yapıştırmayın. Sonuç olarak yalnız durum kodu, ekran adı ve "oldu / olmadı" yazın.

## Yerel çekirdek

- [ ] `START_NOVA.bat` API ve arayüzü açar. Anahtarsız `/health` 401 döner.
- [ ] Ayarlara kendi anahtarınızı yazınca bağlantı durumu "Bağlı" olur.
- [ ] Yeni konuşma açılır, bir cümle gönderilir, yanıt gelir, kenar çubukta görünür.
- [ ] Aynı oturumu yeniden açınca geçmiş durur. Başka oturumda eski cümleler karışmaz.
- [ ] "bunu hatırla:" ile kaydettiğiniz cümle, yeni oturumda sorulunca bulunur.
- [ ] Anahtarı silip gönderince hata görünür ve özel içerik ağ günlüğüne düşmez.

## Gmail, kişiler, takvim

- [ ] `python scripts/authorize_google.py gmail` tarayıcı açmadan adımları yazar.
- [ ] Siz `--launch` çalıştırmadan Gmail ekranı 503 veya bağlı değil durumu gösterir.
- [ ] Yetkiden sonra "bugün gelen" ve "dün gönderdiğim" ayrı sonuç verir. Tam metin yalnız düğmeyle açılır.
- [ ] Kişiler ve takvim, kendi salt okunur yetkileri olmadan 403 verir.
- [ ] Takvim değişikliği kodu görünür; kodu yazmadan kayıt oluşmaz.

## Ses

- [ ] Basılı tutunca mikrofon ister, bırakınca durur.
- [ ] İptal, kaydı ve okumayı keser.
- [ ] Masaüstünde basılı tutunca kısa bir Türkçe ve bir İngilizce cümle metne döner. İngilizce örnek dosya canlı çevrildi; kendi Türkçe kaydınız henüz doğrulanmadı.
- [ ] Cevap okuma açıksa İngilizce ses duyulur. Türkçe Windows sesi kurulu değildir.
- [ ] Telefon ses ekranı, m4a kaydının kabul edilmediğini yazar. Sohbetteki ses düğmesi cevabı okur.

## Otomasyon

- [ ] Yetkisiz otomatik iş 422 alır.
- [ ] Günlük Gmail özeti, takvim hatırlatması, brifing, web araştırması veya hatırlatma oluştururken kapsamı ve salt okunur erişimi açıkça seçersiniz.
- [ ] Süre dolunca bildirim geçmişi oluşur. Aynı pencere ikinci kez yazılmaz.
- [ ] Yetkiyi kaldırınca iş durur.
- [ ] Hiçbir otomatik iş e-posta veya takvim yazmaz.

## Sosyal

- [ ] Platform kartları kişisel gelen kutusunun okunmadığını yazar.
- [ ] Onay kutusu kapalıyken gönderim olmaz.
- [ ] Telegram bot belirteci yokken gönderim 409 döner.
- [ ] WhatsApp ve Instagram için işletme hesabı, ücret uyarısı ve genel webhook olmadığı görünür.

## Google kişileri ve takvim

Bu adımlar tarayıcı açar. NOVA bunları kendiliğinden çalıştırmaz. Ek OAuth izni vermeden önce kapsamın salt okunur olduğunu kontrol edin.

1. `backend` klasöründe `..\.venv\Scripts\python.exe scripts\authorize_google.py contacts` komutunu çalıştırın. Tarayıcı açılmaz. People API satırını okuyun.
2. Aynı komuta yalnız siz `--launch` eklerseniz tarayıcı açılır. Hesabınızı seçin. Belirteç `token_contacts.json` dosyasına yazılır. Dosyayı açmayın ve içeriğini sohbete yapıştırmayın.
3. Takvim için aynı iki adımı `calendar` ile tekrarlayın. Belirteç `token_calendar.json` olur. Kapsam `calendar.readonly` kalmalıdır.
4. Uygulamada Kişiler ve Takvim ekranlarını açın. Sonuç olarak yalnız “oldu / olmadı” yazın. İsim, telefon, etkinlik başlığı veya saat yapıştırmayın.
5. Takvim değişikliği bir onay kodu göstermeden kaydolmamalıdır. Kodu yazmak yazma izni de ister. Bu izni ayrıca onaylamadan vermeyin.

## Gmail canlı kontrol

1. `..\.venv\Scripts\python.exe scripts\authorize_google.py gmail` tarayıcı açmadan adımları yazar.
2. `--launch` yalnız sizin kararınızdır. Kapsam `gmail.readonly` olmalıdır. Belirteç `token.json` olur. İçeriğini paylaşmayın.
3. Ayarlara kendi API anahtarınızı yazın. Anahtarı sohbete yazmayın.
4. “bugün gelen” ve “dün gönderdiğim” için sohbete kısa istek yazın. Cursor'a yalnız durum kodunu ve “sonuç geldi / gelmedi” bilgisini iletin. Konu, gönderen ve gövde yapıştırmayın.
5. Tam metin yalnız siz düğmeye basınca açılır. Gönderme yoktur.

## Tailscale ile özel telefon erişimi

Tailscale bu bilgisayarda kurulu değildir ve kurulmadı. Kurmaya karar verirseniz:

1. Tailscale istemcisini yalnız kendi tailnet hesabınızla kurun. Servisi `0.0.0.0` adresine bağlamayın.
2. PostgreSQL `127.0.0.1:5434` üzerinde kalır. `5432`, `5433` ve `5434` portlarını tailnet'e veya internete açmayın.
3. FastAPI'yi herkese açmak yerine, tailnet içinde `tailscale serve` kullanın. Örnek niyet: yalnız tailnet'ten `https://<makine>.<tailnet>.ts.net` adresini `http://127.0.0.1:8001` hedefine bağlamak. Komutu çalıştırmadan önce hedefi kontrol edin.
4. Telefonda Expo ayarlarına bu tailnet adresini ve API anahtarını yazın. Anahtar SecureStore'da kalır. Adresi ve anahtarı sohbete yazmayın.
5. Telefondan bir sohbet gönderin. Sonuç olarak yalnız “bağlandı / bağlanmadı” yazın.

## Android paketi

APK üretilmedi. Java 17, platformlar `android-30`, `android-33`, `android-34`, `android-35` ve build-tools `34.0.0`, `35.0.1`, `36.0.0` duruyor. `adb.exe` SDK içindedir fakat PATH üzerinde değildir. `ANDROID_HOME` tanımsızdır. Sistem ortam değişkenini değiştirmek onay ister. Bir kabukta denemek için:

```bat
set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
set PATH=%ANDROID_HOME%\platform-tools;%PATH%
cd mobile
npx expo start
```

Bağlı bir cihaz veya emülatör yoksa paket oluşmaz. iOS için macOS ve Xcode gerekir.

## Kapatma

- [ ] `STOP_NOVA.bat` başlığı `NOVA API`, `NOVA UI` veya `NOVA AI` olan pencereleri kapatır.
- [ ] `nova-vector-db` çalışmaya devam eder ve hacmi silinmez. Kayıt sayıları değişmez.
