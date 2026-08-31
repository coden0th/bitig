# BitigAI — Karar günlüğü

Bu dosya, motorun geliştirme sürecindeki tarihli kararları, ölçümleri ve
"pahalıya öğrenilmiş" teknik dersleri kaydeder. `CLAUDE.md`'nin (proje kökü)
yalın "yapay zekâ çalışma anlaşması" olarak kalması için buraya taşındı —
bölüm numaraları CLAUDE.md'deki özgün numaralarıyla AYNEN korunmuştur (1, 8, 10
CLAUDE.md'de kaldığı için burada görünmez), böylece kod içindeki
`CLAUDE.md §N` atıfları sadece dosya adı değişikliğiyle `docs/decisions.md §N`
olarak okunabilir.

---

## 2. Mevcut durum

Motor çalışıyor ve ölçülüyor. Üretim bağımlılığı **sıfır** (`bitig/` saf standart kütüphane).

| Ölçüm | Sonuç | Komut |
|---|---|---|
| Altın küme (ad çekimi) | 124/124, 6 kuralda %100 prec/rec | `python -m harness.olc` |
| Altın küme (fiil çekimi) | 83/83 | aynı |
| **Çıkmış ÖSYM soruları (ses bilgisi)** | **12/14 doğru, 2 belirsiz, 0 yanlış** | `python -m harness.soru_coz` |
| **Çıkmış ÖSYM soruları (fiiller: çatı/fiilimsi)** | **8/8** | `python -m harness.fiil_coz` |
| **Çıkmış ÖSYM soruları (tamlamalar)** | **2/3 doğru, 1 bilinçli belirsiz** (bkz. §5) | `python -m harness.isim_coz` |
| Gidiş-dönüş bütünlüğü | %100 (her motor değişikliğinden sonra yeniden doğrulandı) | `python -m harness.gidis_donus` |
| Kapsam (`osym-tyt-turkce-sorular.txt`, gerçek metin) | %90.25 (geniş zaman + isim-fiil -yIş düzeltmesinden sonra) — **GLM ölçümüyle (%96.86) doğrudan karşılaştırılamaz**, bu dosya kısmen OCR bozuk (bkz. §5) | `python -m harness.kapsam --dosya osym-tyt-turkce-sorular.txt` |
| zeyrek anlaşmazlığı | 181 kelimede 2 (ikisinde de biz haklıyız) | `python -m harness.anlasmazlik` |
| Birim testler | 502 | `python -m pytest testler/ -q` |
| Kapsam (temiz model metni) | **%97.66** (GLM'in %96.86'sıyla karşılaştırılabilir) | `python -m harness.kapsam --tur 10 --cumle 40` |
| **Bağlam duyarlı seçici (Faz 2.1, ağ gerektirir)** | **5/6** | `python -m harness.baglam_coz` |
| **Anlatım bozukluğu — kelime listesi (Faz 2.2, ağ gerektirmez)** | **6/6** | `python -m harness.anlatim_coz` |
| **TDK yazım motoru — Track A morfolojik (Faz 2.3, ağ gerektirmez)** | **100/100** | `python -m harness.yazim_dogrula` |
| **TDK yazım motoru — Track B sözlüksel (Faz 2.3, önbellek ağsız/senkron ağlı)** | 1705 kelime önbellekte (%97.8 geçerli) | `python -m harness.tdk_senkron --tazele` |
| **Noktalama — şart eki virgülü + kesme/iyelik (Faz 2.4, ağ gerektirmez)** | **3/3** | `python -m harness.noktalama_coz` |
| **Atasözü/deyim sözlüğü (Faz 2.5, sorgu ağsız/indirme ağlı)** | 13.592 kayıt | `python -m harness.atasozu_indir` |
| **İsim Soylu Sözcükler — bağlamsal tür çözücü** | **19/19** (elle kurulmuş test cümleleri) | `python -m pytest testler/test_isim_soylu.py` |
| **Çıkmış ÖSYM soruları (Sözcükte Yapı, askıda domain, ağ gerektirmez)** | **7/7** (29 gerçek sorudan 7'si mekanize edildi, tamamı tarandı, bkz. §5) | `python -m harness.sozcukte_coz` |

Hepsi `.venv/bin/python` ile çalıştırılır. Hız ~2.5 ms/kelime (graf genişledikçe 1.9'dan
yükseldi), ilk sorguda ~0.5 sn sözlük yüklemesi.

### Kapsam

Ad çekimi (nominal ek-fiil dahil: bildirme/hikâye/rivayet/şart + kişi ekleri isim/sıfat
yüklemi üstünde de çözülüyor) · fiil çekimi (kip — istek kipi dahil, kişi, çatı —
edilgen/dönüşlü/ettirgen/işteş, fiilimsi, birleşik kip, yeterlilik, kurallı birleşik fiil —
tezlik/süreklilik/yaklaşma) · soru eki "mi" (ek-fiil alır) · yaygın yapım ekleri (küçültme
-CIk dahil), zarflarda aitlik eki (-ki: sonraki, yarınki). `veri/ekler.json` içinde 95 ek
tanımı, 17 durum.

Yedi kural: `SES.YUM.01` (yumuşama), `SES.UD.01` (ünlü düşmesi), `SES.UT.01` (ünsüz türemesi),
`SES.KAY.01` (kaynaştırma), `SES.BEN.01` (benzeşme), `SES.DAR.01` (ünlü daralması),
`SES.UND.01` (ünsüz düşmesi — 2026-08-06 eklendi, bkz. §9).

---

## 3. Mimari

```
cümle
  ↓
[ sözlük deposu ]     kök adayları + öznitelikler   bitig/sozluk/
  ↓
[ morfotaktik graf ]  durum → ek → durum            bitig/morfotaktik.py + veri/ekler.json
  ↓
[ türetim şelalesi ]  kurallar; olay + kanıt burada doğar   bitig/turetim.py
  ↓
[ ön-ek budaması ]    üretilen yüzey hedefin öneki değilse dal ölür
  ↓
tam eşleşenler = geçerli okumalar (hepsi döner)      bitig/cozumleyici.py
  ↓
[ çıktı sözleşmesi ]                                 bitig/sozlesme.py
  ↓
[ ÖSYM politika katmanı ]  ayrı, sürümlenebilir      bitig/osym.py + veri/osym_politikasi.json
```

**Çözümleme ayrı bir algoritma değil, üreticinin budanmış aramasıdır.** Tek doğruluk kaynağı
üretici (`bitig/uretici.py`) olduğu için "tespit" ile "türetim" arasında tutarsızlık imkânsız.

### Kuralları ne tetikler

v1'in bütün yanlış pozitiflerinin kökü altdizi eşleşmesiydi (`"diye" in kelime` → hediye,
diyet, niyet). Yeni motorda kuralı **kökün sözlüksel özniteliği** tetikler, yüzeydeki harf
dizisi değil. Öznitelikler Zemberek sözlüğünden gelir (`Voicing`, `NoVoicing`, `LastVowelDrop`,
`Doubling`, `InverseHarmony`, `ProgressiveVowelDrop`, `Aorist_I/A`…).

**Kritik:** Sözlüğün 28.920 satırının 18.625'i çıplaktır — öznitelik dosyada yazmaz, yükleme
anında **çıkarılır** (`bitig/sozluk/oznitelik.py`). `NoVoicing`in en yaygın öznitelik olmasının
sebebi budur: o bir bayrak değil, çıkarımın istisna listesidir (diyet, niyet, sepet).

### Belirsizlik iki katmanlıdır

Motor okuma seçmez, hepsini döner. Ama sözleşme ikisini ayırt eder:

- `kesin_olaylar` — **her** okumada bulunanlar. Bağlamsız garanti edilebilir.
  **Otomatik soru üretimi yalnızca buna dayanabilir.**
- `olasi_olaylar` — en az bir okumada bulunanlar.
- `olayda_belirsiz` — okumalar olaylarda ayrışıyor mu? Bu bir **eleme ölçütüdür**: öğrenci
  öbür okumayı savunabileceği için o sözcük ses olayı sorusunda kötü bir maddedir.

Örnek: `kitabı` iki okunur ama ikisi de yumuşama üretir → risksiz. `masada` = masa+da / masat+a
→ `kesin_olaylar` boş, `olayda_belirsiz` işaretli.

### ÖSYM politika katmanı

ÖSYM'nin bakışı ile dilbilimsel çözümleme bazı yerlerde ayrılır ve **ikisi de kendi çerçevesinde
doğrudur**:

```
çevresi   dilbilim → olay yok       ("çevre" bugün bağımsız bir kök)
          ÖSYM     → ünlü düşmesi   (çevir + e; sözcüğün tarihine bakar)
```

Motoru ÖSYM'ye göre "düzeltmek" yanlış olurdu. Bunun yerine **çıktı her iki görüşü birden
taşır**; `Mod.OSYM` / `Mod.DILBILIM` yalnızca hangisinin *geçerli* sayılacağını seçer, diğerini
silmez. Kullanıcı "burada ÖSYM farklı düşünüyor" uyarısını görür.

Politikaya kayıt eklemek için **çıkmış bir soru gerekir** — `kaynak` alanı testle zorunlu.
Şu an iki kayıt var, ikisi de sözlükleşmiş türetim: `çevre` = çevir+e, `oyna` = oyun+a.

---

## 4. Ölçüm araçları

Beş araç, **beş farklı hata sınıfı**. Hepsi `harness/` altında, hepsi `python -m harness.X`.

| Araç | Ne sorar |
|---|---|
| `olc` | Altın kümede, bildiğimiz vakalarda doğru muyuz? Kural bazında prec/recall. |
| `altin_dogrula` | Altın kümenin **kendisi** tutarlı mı? Motoru hiç çalıştırmaz. |
| `gidis_donus` | Kendi ürettiğimizi geri okuyabiliyor muyuz? **Etiketsiz**, en geniş kapsam. |
| `kapsam` | Gerçek Türkçe'nin ne kadarını görüyoruz? Çözülemeyen = boşluk. |
| `soru_coz` / `fiil_coz` / `isim_coz` | Çıkmış soruyu bitirebiliyor muyuz? En sert sınav —
  sırasıyla ses bilgisi, fiiller, tamlamalar. |
| `anlasmazlik` / `olay_hakemi` | zeyrek / GLM ile çelişkiler → inceleme kuyruğu. |

**Altın kümeler hâlâ kısmen Claude'un yazdığı.** Motor bu kümelerdeki eksikleri üç kez kendisi
buldu (`masada`, `biliyor`, `ayırdı`). Gerçek ÖSYM verisi geldikçe değiştirilmeli — `%99.99`
hedefi ancak öyle anlamlı olur.

### GLM / z.ai

Anahtar `~/.config/bitigai/zai.key` dosyasında (ortam değişkeni Bash çağrıları arasında
yaşamıyor). Varsayılanlar doğrulandı: model `glm-5.2`, base URL `https://api.z.ai/api/paas/v4`.

**Model girdi üretir, etiket üretmez.** `kapsam` modele hiç güvenmez (sadece cümle yazdırır);
`olay_hakemi` çelişkileri insana kuyruklar. Eşiğin %100 olduğu bir sistemde LLM çıktısı
doğruluk kaynağı olamaz.

---

## 5. EBA soru boru hattı

**`osym-tyt-turkce-sorular.txt`** (repo kökünde, git-takipsiz) — kullanıcının sağladığı,
**gerçek 2025/2026 TYT ÖSYM sınav soruları** + OGM Materyal'in bir kısmının OCR/elle
transkripsiyonu. ÖSYM'nin kendi çıkmış soruları, EBA/OGM'den bile daha otoriter bir kaynak
(bkz. §10 "temiz kaynaklar" sıralaması). OGM kısmı bazı yerlerde bozuk (OCR hataları, garip
karakterler) — o kısımlar için görüntüden okuma (aşağıdaki yöntem) hâlâ tercih edilir. Ama
dosyanın **başındaki gerçek sınav soruları** eşsiz: `SES.UND.01` kuralı (ünsüz düşmesi:
ufak→ufacık) buradan bulundu. Gerçek sınav sorularının bir kısmı (iyelik eki tespiti gibi)
tamlama/sözdizimi bilgisi gerektiriyor — motorun kapsamı dışında (Faz 3), zorlanmadı.

MEB'in OGM Materyal kitapları temiz kaynaktır (CLAUDE.md §8). Uygulama Angular SPA'dır ve
HTML'den içerik çıkmaz, **ama sayfalar JPEG olarak CDN'de durur ve doğrudan okunabilir**:

```
https://ogm-large-cdn.eba.gov.tr/ogm-materyal/konu-pekistirme/tyt/tde/files/mobile/{n}.jpg
```

- **Dosya numarası = kitap sayfası + 2** (kitap s.45 → `47.jpg`). Her kitapta farklı olabilir.
- İndirme: `python -m harness.eba_indir --sayfa 50 56 --hedef /tmp/eba`
- Görüntüler Read ile okunur; soru, seçenek, çözüm ve cevap net çıkar.
- Görüntüler depoya **konmaz** (`.gitignore`). Yalnızca sorular `altin/sorular.jsonl`'a aktarılır.

TYT Türkçe içindekiler (kitap sayfası): Sözcükte Anlam 9 · Cümlede Anlam 21 · Paragrafta Anlam 33
· **Ses Bilgisi 45** · Sözcükte Yapı 55 · Yazım Kuralları 65 · Noktalama 87 · İsim Soylu
Sözcükler 109 · Fiiller 123 · Tamlamalar 135 · Cümlenin Ögeleri 147 · Cümle Türleri 159 ·
Anlatım Bozuklukları 169 · **Cevap Anahtarı 179**.

**Aktarılanlar:** sayfa 47-56 (kitap 45-54, Ses Bilgisi 1-4), 127-138 (kitap 125-136, Fiiller
1. Test), + cevap anahtarı (s.179-180). `altin/sorular.jsonl` 12 soru, `altin/fiil_sorulari.jsonl`
3 soru. **Sıradaki iş:** Fiiller 1. Test'in geri kalanı (Q1 kip sırası, Q12 sözde özne — ikisi
de motor+basit sinyalle değil, bağlam/model katmanı gerektiriyor, bkz. aşağı) ve 2-4. Testler.

**Sözcükte Yapı (57-66) askıya alındı — 2026-08-06 ölçümü:** Sözcükte Yapı sayfa 57-58'deki
8 "kök türü / yapı sınıflandırması" sorusu elle motora soruldu, cevap anahtarıyla
karşılaştırıldı. Yalnızca 1/8 temiz eşleşti. Sebep: bu domainde sözlükleşmiş türetim
(`çevre`/`oyna`/`diye` deseni) **istisna değil, kural**. Sözlükte çıplak kök olarak duran ama
MEB/ÖSYM'nin türemiş saydığı kelimeler tek bir soruda bile üst üste çıktı: `ekin` (ek+in),
`doğal` (doğa+l), `çeviri` (çevir+i), `ışık` (ış+ık), `yatak` (yat+ak), `yorgun` (yor+gun),
`karanlık`, `sevinç` (sev+inç), `sözcük` (söz+cük). İki kelime ("Gündüzdün", "oyuncusuydu")
motor tarafından hiç çözülemedi — ayrı bir kapsam boşluğu. Bir soru tipi (çekim ekinin
"işlevce" hangi okumada kastedildiği, bağlama bakan referans çözümlemesi) zaten motorun
kapsamı dışında (Faz 2/3). Sonuç: güvenilir bir çözücü için ÖSYM politika katmanına onlarca/
yüzlerce kelimelik bir sözlükleşme envanteri gerekir — bu, ayrı ve büyük bir iş. Şimdilik
motoru ÖSYM'ye göre "düzeltmeye" kalkışmadan bırakıldı; devam edilecekse önce bu envanter
inşa edilmeli.

**Üç ek kaynak tarandı, sonuç değişmedi (2026-08-07):** `sozcukte-yapi.txt`'de listelenen üç
kaynak (kunduz.com blog yazısı, dopinghafiza.com blog yazısı, EBA'nın 41 sayfalık "Ekler ve
Sözcüğün Yapısı" PDF'i — `ogmmateryal.eba.gov.tr/panel/upload/kitap/sr2wvi0dbjy.pdf`)
incelendi. Üçü de **saf teori**: kök/yapım eki/çekim eki tanımları, ~10-20 kelimelik kısıtlı
örnek listeleri (basit: kitap/araba/kedi; türemiş: evcil/kitaplık/arabalı; birleşik:
sütlaç/pazartesi/ağabey/kapkaç), toplam yalnızca 2 örnek soru. Zaten bilinen kuralları
(kök+yapım+çekim sırası, basit/türemiş/birleşik tanımı) doğruluyorlar — bunlar motorda zaten
doğru işliyor. **Hiçbiri sözlükleşme envanteri açığını kapatmıyor.** Tek yeni ayrıntı: PDF
"gövdeden türemiş sözcük" sorularının en az iki yapım eki gerektirdiğini vurguluyor (Saygılı,
Birincilik, Atılgan) — mekanik olarak `ek_kimlikleri` zincirinden sayılabilir bir ölçüt ama
zincirin ilk adımı çoğu zaman sözlükleşmiş bir kökte başladığı için (`saygı`, `sevgi` gibi
-GI ekli isimler sözlükte çıplak) aynı duvara çarpıyor. Sonuç: ilerlemek için hâlâ teori değil
veri gerekiyor — kök→sözlükleşmiş-mi sınıflandırma listesi. Bu üç kaynağa tekrar bakmaya
gerek yok.

**Gerçek ÖSYM soru bankası bulundu, ilk ölçülebilir kazanım geldi (2026-08-07, aynı gün
devam):** İnternette elle aranarak `klasikhoca.com`'da **29 gerçek TYT/ÖSYM Sözcükte Yapı
sorusu (1994-2020) + cevap anahtarı** bulundu (Google Drive PDF, kullanıcı tarafından
doğrulandı — gerçek). Bu, teori değil veri: her soru kelime bazında bir MEB/ÖSYM etiketi
taşıyor. Motora tek tek elle değil **kod üzerinden** (`bitig.cozumleyici` doğrudan) soruldu;
manuel dilbilgisi muhakemesi burada bilerek kullanılmadı çünkü proje ilkesi tam olarak bunu
yasaklıyor (model/insan tahmini v1'in hatasını tekrarlar).

**Tüm 29 soru tek tek tarandı (üçüncü ve son tur, aynı gün).** Yol boyunca paragraf↔soru
numarası eşleşmesi **iki kez** yanlış okundu (biri kullanıcı tarafından düzeltildi — 1988/
soru 4; biri kendi kendine "düzeltilirken" yeni bir kaymaya yol açtı — 2018/soru 26 ilk
turda doğru test edilip DOĞRU çıkmışken, "düzeltme" sırasında yanlış paragrafla tekrarlanıp
BAŞARISIZ sanıldı; PDF baştan sona tekrar okunup kesin kural netleştirildikten sonra —
**paragraf metni her zaman kendi soru numarasından hemen önce gelir, istisnasız** — üçüncü
turda hem Q26 hem geri kalan tüm sorular doğru eşleşmeyle yeniden test edildi). Sonuç:
**29 sorudan 7'si mekanize edildi**, `harness/sozcukte_coz.py` + `altin/sozcukte_yapi_sorulari.jsonl`
(`SOZYAPI-01`…`SOZYAPI-07`) → **7/7**.

Çalışan dört mekanizma türü (hepsi kelime-düzeyinde **kesin** — bir kelimenin *her* okuması
göstermeli/hiç göstermemeli, `fiil_coz.py`nin `_ekfiil_var_mi` desenindeki gibi; "olası"
mantık motorun üretken yapım ekleri yüzünden neredeyse her zaman yanlış pozitif verir):

| Ölçüt | Soru | Mekanizma |
|---|---|---|
| `SIFATFIIL` kesin var | 2000/9 (atasözü) | sıfat-fiil ekiyle türetilmiş sıfat |
| `IYELIK` kesin var | 1988/4 | "varlığın neye ait olduğu" eki |
| `YAPIM` kesin yok | 1999/7, 2010/12, 2018/26 | yapım eki hiç yok / yalnız çekim |
| `coklu_iyelik23` | 2000/8 | kelime kendi içinde 2./3. tekil iyelik arası belirsiz mi |
| `kategori_yok` | 2013/19 | ortak metinde bir dilbilgisi kategorisi hiç yok mu (ek-önekli + kapalı-sınıf-kelime karışık) |

**`YAPIM` kesin-yok mekanizması veri-bağımlı, genel bir kural değil:** aynı ölçüt üç
paragrafta (1999/7, 2010/12, 2018/26) temiz çalıştı ama 1997/3 ve 1999/6'da ("birden çok
yapım eki var mı") HİÇ ayırt edemedi — motorun sözlüğü ilk yapım basamağını hep yutuyor
(`korku`+lu değil `kork`+u+lu, `örtü`+lü değil `ört`+ü+lü; en fazla 1 yapım eki görünüyor,
hiçbir seçenekte 2 değil). Ayrım şu: "hiç yapım yok mu" sorusu bazı sözlükleşmiş
paragraflarda tesadüfen ayırt edici kalıyor (çünkü rakip kelimelerin bazıları GERÇEKTEN
üretken bir yapım taşıyor), ama "en az 2 yapım var mı" sorusu SİSTEMATİK olarak başarısız
oluyor çünkü zincirin İLK basamağı hemen her zaman sözlükleşmiş. `sozcukte_coz.py`'ye
yalnızca ölçülüp doğrulanan üç paragraf eklendi, genel bir "YAPIM sayısı" ölçütü **eklenmedi**.

**Denenip kalıcı olarak BAŞARISIZ bulunan (gerçek dilbilgisel belirsizlik, sözlükleşme
değil):**
- **"3. çoğul kişi iyelik eki"** (2019/27, Dede Korkut parçası, `anlatılarının` vb.) — `-lArI`
  yüzeyi taşıyan HER kelime aynı 3 yönlü belirsizliği gösteriyor (3.çoğul iyelik / çoğul+
  belirtme / çoğul+3.tekil iyelik), 5 adayın 5'i de aynı sonucu veriyor — ayırt edici değil.
- **"Belirtme durumu eki"** tek başına, iyelik-3 ile çakışan bağlamlarda (2019/28 `Oyuncular`
  parçası, 2020/29 `Her sene` parçası) — klasik "kitabı" belirsizliği (`-I` hem belirtme hem
  iyelik-3 olabilir), motor kesin diyemiyor, 4-5 aday aynı anda "olası" çıkıyor.
- **"Hem yapım hem çekim eki almış"** (1995/2) — motorun üretkenliği (`-lA`/`-CA`/`-GI` gibi
  ekler hemen her isim köküne sahte bir fiil-yapan okuma da ekliyor, `sokak`→`sokakla-r` gibi)
  hem "olası" hem "kesin" mantıkta yanlış seçeneği de aday yapıyor ya da doğru seçeneği eliyor.
- **"-(ı)ntı/-(u)ntu/-(ü)ntü ekiyle kökü farklı olan"** (2013/17) — bu ek motorda hiç
  tanınmıyor (`buluntu`/`kuruntu`/`süprüntü`/`bağıntı` hepsi çıplak kök), ayırt edilemez.
- **"Kökü sözcük türü yönünden farklı"** (1999/5, `Çayönü kazısında` parçası) — ÖSYM'nin
  beklediği ayrım **etimolojik**: `kazı`(kaz+ı), `buluntu`(bul+un+tu), `aşama`(aş+ma) hepsi
  gizli FİİL kökenli ama sözlükte çıplak isim; yalnızca `av` gerçek isim kökü. Motor
  `geçiş`i (gerçekten Verb kök) farklı sanır — sözlükleşme duvarının temiz bir kanıtı.
- **"Ünsüzlerinden biri düşmüş"** (1994/1, cevap `büyücek`) — zaten bilinen "büyücek sınırı"
  (bkz. `OGM-UND-01`) ile birebir örtüştü, yeni bilgi vermedi ama kaynağın gerçekliğini
  doğruladı.

**Ayrı, çözülmemiş bir motor tuhaflığı bulundu (2004/soru 10, düşük öncelik):** "İlgi
adılından sonra yaklaşma durumu eki" sorusunda `seninkine` (doğru cevap) beklendiği gibi
`EK.AITLIK`+`EK.HAL.YON` birlikteliği gösteriyor, ama `Masadakilerden` da AYNI birlikteliği
gösteriyor — ek_kimlikleri içinde `EK.HAL.YON` görünüyor, oysa yüzey `-den` (ayrılma) ile
bitiyor, `-e/-a` (yaklaşma) ile değil. Muhtemelen `-daki` türetiminin ara adımlarından biri
(`masat+a+ki...` zinciri) yanlışlıkla iz bırakıyor. Ayrı bir araştırma gerektiriyor,
düşük öncelik, bu turda eklenmedi.

**Kategori seçenekli sorular (11,13,14,15,16,18,20,21,24 — her biri farklı dilbilgisi
boyutunu bir arada soran "A-E hangisi yanlış/yok" formatı) çoğunlukla önceden belgeli
mimari sınıra takıldı** (isim tamlaması/öge dizilişi gibi sözdizimi gerektiren maddeler +
kapalı sınıf kelime türleri aynı soruda karışık). Tek istisna 2013/19 (`kategori_yok` olarak
eklendi, yukarı bkz.) — o sorunun 5 kategorisinin 4'ü doğrudan ek_kimlikleri önekiyle,
1'i ("benzetme edatı") küçük bir kapalı-sınıf kelime listesiyle (yalnızca `gibi`/`kadar`,
genel bir edat sözlüğü değil) çözülebildi. 21'in bazı maddeleri (iyelik-3, birden-fazla-
yapım) kısmen doğrulandı ama "sayı sıfatı" (kapalı sınıf, `bir` sayı/belirsizlik-sıfatı
çakışması) güvenilir çözülemediği için tüm soru eklenmedi.

**Genel sonuç:** Sözcükte Yapı hâlâ ÖSYM'nin sorduğu her biçimi kapsamıyor (7/29) ama artık
gerçek, doğrulanabilir bir soru kaynağı ve dört çalışan mekanizma var. Sözlükleşme duvarının
**tutarsızlığı** somutlaştı (`biçim`/`anlatı`, `kazı`/`av` gibi yapısal olarak özdeş kelime
çiftleri farklı davranıyor) — önceden sanıldığı gibi tek yönlü bir "hangi kökler
sözlükleşmiş" listesi yetmez, envanter işi düşünülenden daha ince taneli olmalı. İkinci
ders: bu kaynağın kendisi bile (paragraf/soru numarası sırası) dikkatli okunmazsa yanlış
eşleştirmeye yol açıyor — yeni bir soru eklemeden önce paragraf metni kaynak PDF'ten
**yeniden** okunmalı, önceki bir transkripsiyona güvenilmemeli.

**İsim Soylu Sözcükler (109-122) askıya alındı — 2026-08-07 ölçümü:** Sayfa 109-118
(çözümlü sorular + Test 1-2, ~35 soru) elle tarandı. Sözcükte Yapı'yla aynı kategoride bir
engel, farklı sebeple: bu domain neredeyse tamamen (1) **kapalı sınıf sözlüğü** gerektiren
sorulardan (zamir türü: kişi/işaret/belgisiz/soru/dönüşlü/ilgi; sıfat türü: niteleme/sayı/
belgisiz/işaret/soru; zarf türü: zaman/yer-yön/miktar/durum/soru; edat/bağlaç/ünlem tespiti —
bunlar türetim değil, sabit kapalı kelime listesi işi, motorun kök+ek türetim mekanizmasıyla
ilgisi yok) ve (2) **anlamsal/bağlamsal** sorulardan oluşuyor ("ile" edatı hangi anlamda,
"kadar/gibi" benzerlik mi eşitlik mi, ünlem hangi duyguyu taşıyor, soyut mu somut mu — motor
bunları hiçbir zaman bilemez). Üstüne, sorular ezici çoğunlukla "kategori seçenekli/
numaralanmış sözcük" formatında (tek pasajda 5 farklı sınıf soruluyor) — Fiiller'de zaten
atladığımız aynı mimari uyumsuzluk. Tek istisna (hâl ekleri: belirtme/yönelme/ayrılma/iyelik/
tamlayan) gerçekten morfolojik ama o da çoğunlukla aynı çoklu-kategori formatında geliyor.
Sonuç: **kod değil veri işi** — kapalı sınıf kelime listeleri (~100-150 kelime, gerçekten
kapalı sınıflar) hazırlanmadan ilerlemek zor. Şimdilik bırakıldı.

**Kapalı sınıf veri katmanı kondu (2026-08-08) — engel kısmen kalktı, iş bitmedi.**
`ogm-large-cdn.eba.gov.tr/ogm-materyal/mebi-konu-ozetleri/tyt-turkce/tyt-turkce.pdf` (MEBİ TYT
Konu Özetleri - Türkçe, 2026, 128 sayfa, ISBN 978-975-11-8474-0) bulundu — Sözcükte Yapı için
yine aynı sözlükleşme duvarına çarpan teori (s.73, önceki 41 sayfalık PDF'le neredeyse birebir
aynı örnekler: dağcı/saygılı/birincilik) ama Zamir/Sıfat/Zarf/Edat/Bağlaç bölümleri (s.83-98)
MEB'in kendi "başlıca X" kapalı listelerini veriyor — tam burada eksik olan veri.
`veri/kapali_sinif_kelimeler.json`'a aktarıldı: kişi/işaret/belgisiz/soru zamirleri, işaret/
soru/belgisiz sıfatları, soru zarfları, edat (10 kelimelik resmî liste: gibi/ile/kadar/göre/
üzere/diye/karşı/doğru/dolayı/ötürü), bağlaç (13 kelimelik resmî liste). **Bu tek başına bir
çözücü değil, veri katmanı.** MEB'in kendi kaynağı bile aynı kelimenin (`bu/şu/o`, `ne`, `bir`,
`ile`, `yalnız`, `-ki`) birden fazla kategoriye girdiğini "DİKKAT" kutularıyla ayrıca vurguluyor
— bunlar `_cakisan_kelimeler` alanına dürüstçe kaydedildi. Gerçek bir çözücü için bağlamsal
ayrım gerekiyor (izleyen kelime çıplak isim mi → sıfat; kelimenin kendisi hâl eki alıyor mu →
zamir; iki cümleyi mi bağlıyor → bağlaç).

**Bağlamsal çözücü yazıldı (`isim_soylu.py`, aynı gün, ikinci yarı) — beklenenden kolay
çıktı.** Motorun sözlüğü, kapalı sınıf kelimelerin çoğu için tür ayrımını ZATEN okuma
düzeyinde taşıyor — `bu` hem `Det` (belirten/sıfat) hem `Pron` (zamir), `ile` hem `Conj`
hem `Postp` (edat) olarak ayrı okumalar dönüyor. Modülün işi yeni bir sınıflandırma icat
etmek değil, motorun birden fazla tur'u aynı anda mümkün gösterdiği durumlarda (motor
"tespit değil türetim" ilkesiyle hiçbirini elemez) CÜMLE KONUMUNA bakarak seçim yapmak:
sonraki kelime isim gibi kullanılmışsa (kendi çekim ekini taşısa bile, örn. "bu kitabı")
sıfat/belirten kazanır; izlemiyorsa zamir kazanır; önceki kelime yönelme hâlindeyse
("ona karşı/doğru") edat kazanır. `veri/kapali_sinif_kelimeler.json` bu kaba tur etiketinin
altında MEB'in ince alt sınıflandırmasını (işaret/belgisiz/soru zamiri, vb.) sağlıyor.

19 elle kurulmuş test cümlesinde 19/19 doğru (`testler/test_isim_soylu.py`, 12 test,
normal `pytest`e dahil). **Bilinçli olarak çözülmeyen, dürüstçe `None` dönen durumlar:**
`ile`'nin edat/bağlaç ayrımı ("yerine 've' konabiliyor mu" testi tam sözdizimi gerektirir),
`bir`in sayı sıfatı mı belgisizlik sıfatı mı olduğu (`Num` da çıplak aday olduğunda
zorlanmıyor — `isim_coz.py`'deki karanlık/keçi gerilimiyle aynı sınıf bilinçli belirsizlik),
ve kelimenin kendisi zaten çekimli olup tek okumaya düşmediği durumlar (`hangisini`,
`bazılarını`). Önceki oturumda taranan EBA sayfa 109-118 sorularıyla (35 soru) henüz
yeniden denenmedi — o materyal bu oturumda elde değildi, gelecek bir turda tekrar
sağlanıp ölçülmeli.

**Ayrıca `ad_cekimi.jsonl`/`fiil_cekimi.jsonl` altın kümelerine bu kaynaktan sekiz yeni kayıt
eklendi (2026-08-08):** Ses Bilgisi 2 (s.38) tablosundan sekiz aday (sarkaca/derdi/kalbim/
sırrımız/kimseye/pencerenin/kapısı/seçti) motora tek tek soruldu, sekizi de doğrulandı — MEB'in
kendi kanonik örnekleri motorun ürettiğiyle birebir örtüşüyor. İki aday (`minicik`/`sağlıcak`,
Ünsüz Düşmesi tablosundan) reddedildi: motorun `SES.UND.01` kök listesi bilinçli dar tutulduğu
için (yalnızca çıkmış soruyla doğrulanan 4 kök) bu kökler henüz listede yok, motor olayı
üretmiyor — sözlük genişletmesi ayrı bir karar, bu turda yapılmadı. `ad_cekimi.jsonl` 109→115
(bir yinelenen kayıt fark edilip mevcut `kapısı` girdisine kaynak eklenerek birleştirildi),
`fiil_cekimi.jsonl` 79→80. Regresyon: `harness.olc` 115/115 + 80/80, `harness.altin_dogrula`
✓ tutarlı, 446/446 test, `gidis_donus --ornek 300` %100.0000. Ayrıca dört harness betiğinin
(`olc.py`, `altin_dogrula.py`, `anlasmazlik.py`, `olay_hakemi.py`) `*.jsonl` glob hariç tutma
listesine `sozcukte_yapi_sorulari.jsonl` eksikti (önceki oturumda eklenen dosya) — bu turda
fark edilip dördü de düzeltildi, aynı "yeni soru dosyası eklerken glob listesini güncelle"
dersi (bkz. §9) bir kez daha doğrulandı.

### Tamlamalar (isim tamlaması) — 2026-08-07 ölçümü, kısmen çalışan çözücü eklendi

İsim Soylu Sözcükler'in aksine bu domain **morfolojik**: belirtili tamlama tamlayanda ilgi
hâli (`-In`), tamlanan iyelik-3 (`-I/-sI`) alır; belirtisiz tamlamada tamlayan çıplak isimdir.
İkisi de zaten var olan `EK.HAL.ILG` / `EK.IYELIK.3T/3C` ek kimlikleriyle motor tarafından
üretiliyor — yeni bir dilbilgisi kuralı gerekmedi, yalnızca **iki bitişik kelime arasındaki
ilişkiyi** tarayan yeni bir harness katmanı: `harness/isim_coz.py`. `soru_coz.py`/`fiil_coz.py`
tek kelimenin ek kimliklerine bakıyordu; burada tamlayan adayından başlayıp birkaç kelime
içinde tamlanan aranıyor (araya yalnızca sıfat(-gibi) veya çıplak isim girebilir, noktalama
sert sınır).

**Prototipleme sırasında bulunan, motor seviyesinde bir boşluk (ayrı, kesme işareti):**
"Türkiye'nin başkenti" gibi kesme işaretli özel ad + ek kombinasyonu hiç çözülmüyordu —
`bitig/cozumleyici.py`'ye düzeltme yapıldı, bkz. §5 "yedinci tur" (yukarıda). Tamlama işiyle
ilgisiz ama bu arayış sırasında bulundu, önce düzeltildi.

**Çözücünün kendi geliştirme sürecinde çözülen üç kenar durum:**
1. **Ara sıfat tanınmıyordu** ("ormanın nemli zemininden"): `Okuma.tur` her zaman KÖKÜN türüdür
   (nem=Noun), türetilmiş yüzeyin işlevini taşımaz (CLAUDE.md §9). Düzeltme: `EK.YAPIM.LI/SIZ/
   SAL`/`EK.SIFATFIIL` önekleri de "sıfat gibi" sayılıyor.
2. **Noktalama körlüğü** ("İnsan, doğumundan..."): `cozumle()`'nin kelime listesinde noktalama
   yok, virgülle ayrılmış kelimeler bitişik görünüyordu. Düzeltme: `_KELIME_DESENI` span'leriyle
   orijinal metinde noktalama kontrolü.
3. **Derece zarfı + sıfat** ("en derin yerinde"): "en" (`Adv`, `Adj` okuması yok) araya girme
   testini geçemiyordu. Düzeltme: `Adv` da "sıfat gibi" kabul edildi (derece zarfları sıfattan
   önce gelir).

**Çözülmemiş, kabul edilmiş gerilim — isim/sıfat çift okumalı kökler:** Türkçe'de `karanlık`,
`keçi`, `doğru` gibi birçok kök hem çıplak isim hem çıplak sıfat olarak sözlükte iki ayrı girdi
taşır. "Kızların... karanlık gözleri" cümlesinde `karanlık` sıfat işlevinde ama isim okuması
da var — **olası** mantık (herhangi bir okuma çıplak isimse tamlayan say) bunu yanlışlıkla
tamlayan sayıp yanlış pozitif üretiyor (`EBA-TT1-06`, seçenek C). Bunu düzeltmek için **kesin**
mantığa (kelimenin *her* okuması çıplak isim olmalı) geçildi — ama bu kez "taşlı bir keçi
yolundan" cümlesinde `keçi` (gerçekten isim, "dağ keçisi" anlamında) da aynı sebeple (ayrıca
bir Adj homografı var) elendi, gerçek bir tamlamayı kaçırdı (`EBA-TCS-08`, seçenek C). İki
soru **aynı mantıkla aynı anda kazanılamıyor** — biri düzelirken diğeri bozuluyor. Sözlük
dosyasındaki girdi *sırasının* (isim önce mi sıfat önce mi) bir ipucu olabileceği denendi
(`keçi`: isim satırı 12717, sıfat satırı 27104 — isim önce; `karanlık`: sıfat satırı 12194,
isim satırı 27339 — sıfat önce) ama bu sıralamanın "asıl anlam" değil dosyanın **derleme
kaynağı/bölümü** olduğu anlaşıldı (iki girdi arasında ~15.000 satır fark var, aynı bölümden
gelmiyorlar) — gerçek bir dilbilimsel sinyal değil, tesadüfi bir dosya yapısı artığı, bu yüzden
kural olarak kullanılmadı. **Karar:** `_tamlayansiz_isim_mi` **olası** mantıkta bırakıldı (net
olarak daha az riskli görüldü — bkz. kod içi yorum); `EBA-TT1-06` altın kümede *bilinçli
beklenen BELİRSİZ* olarak `not` alanıyla işaretlendi (tıpkı `OGM-UND-01`'in `büyücek` sınırı
gibi, bkz. §10 "belirsiz çözümlemeyi tek okumaya indirgeme"). Gerçek çözüm bağlamsal isim/sıfat
ayrımı gerektirir — Faz 2/3'ün "bağlam duyarlı katman" işi, harness seviyesinde zorlanmadı.

**Bilinen, dar tutulmuş sınır:** yalnızca 3. TEKİL/ÇOĞUL iyelik (tamlanan) aranıyor — 1./2.
kişi tamlama (`-In` hem ilgi hâli hem 2. tekil iyelik yüzeyce özdeş) zincirleme durumlarda
yanlış pozitif riski taşır, bilinçli dışarıda bırakıldı. Soru cümlenin **belirli bir ögesini**
(örn. "yer tamlayıcısı") hedefliyorsa bu modül güvenilmez — tüm cümleyi tarar (2023 YKS
sorusunun B seçeneği bu yüzden eklenmedi).

**`farkli_tur` mekanizması eklendi (2026-08-07, kaynak `ogm-materyal.txt`, MEB'in ÖSYM-tarzı
hazırladığı sorular):** "Bu parçadaki altı çizili tamlamalardan hangisi ötekilerden
farklıdır?" tipi — `harness/fiil_coz.py`'deki aynı isimli mekanizmanın tamlama karşılığı.
Fark: orada fiilimsi alt-türü (3 kategori) çoğunluğu aranıyordu, burada tek bir ikili özellik
var (öbeğin son kelimesi tamlanan/iyelik-3 taşıyor mu). Beş öbekten dördü ("savaş oyunu",
"zemin avantajı", "hayal gücü", "öngörebilme yeteneği") son kelimede iyelik-3 taşıyor
(belirtisiz ad tamlaması); "eşit güçte" taşımıyor (çıplak isim + hâl eki, araya iyelik
girmiyor — sıfat tamlaması + hâl eki, ad tamlaması değil). Motor bunu tek denemede doğru
buldu (`OGM-TAMLAMA-01`). Bu, "numaralanmış sözcük" ailesiyle karıştırılmamalı: soru_coz.py'nin
o kısıtı (§5'te belgeli) tek bir kelimenin PARAGRAF İÇİNDEKİ konumunu bulmaya çalışmaktan
doğuyordu; burada her öbek zaten doğrudan, tam metniyle veriliyor — konum arama yok, bu yüzden
güvenli.

Aynı dosyadaki ilk soru ("Bu cümledeki ögelerin dizilişi...") eklenmedi: özne/nesne/yer
tamlayıcısı ayrımı tam cümle sözdizimi çözümlemesi gerektiriyor — Faz 3'ün "Cümlenin ögeleri"
işi, motorun kapsamı dışında (bkz. §6).

**Sonuç:** `altin/isim_sorulari.jsonl` 3 kayıt, `harness.isim_coz` 2 doğru + 1 beklenen
belirsiz + 0 yanlış. Mekanizma küçük ölçekte doğrulandı ama altın küme henüz çok dar —
daha fazla gerçek soru eklendikçe genişletilecek.

Soru formatı için `altin/sorular.jsonl`'a bak. Cümle/dize seçenekli sorular tercih edilir:
motor her seçenekteki her kelimeyi çözer, altı çizili işaretine ihtiyaç duymaz. İki tip
soru **atlanır**, ikisi de kopyalamada/format eşleşmesinde bozuluyor:
- "Numaralanmış sözcük" (I, II, III… işaretli **tek sözcük**, "hangisinde farklı bir ses olayı
  vardır" tipi) — kopyalamada bozulur. **Numaralanmış tam CÜMLE** farklıdır ve sorun değildir
  (Fiiller Q6/Q7/Q11 gibi) — her numara zaten kopyalanabilir tam bir cümle, tek kelimenin
  paragraf içinde konumunu elle bulmaya gerek yok.
- "Altı çizili sözcüklerden hangisinde X vardır/yoktur" tipi — soru tek bir sözcüğü hedefler
  ama `soru_coz.py` tüm cümleyi tarar; cümledeki başka bir sözcük olayı taşıyorsa (örn.
  "kitabının") yanlış BELİRSİZ çıkar. Denendi, iki örnek (`EBA-T1-08`, `EBA-T4-09`) bu yüzden
  çıkarıldı — bkz. 2026-08-06 oturumu.
- Paragraf + "hangi ses olayı yoktur" ve seçenekleri **tek tek cümle değil kategori adı**
  olan sorular da (örn. "A) Ünsüz benzeşmesi  B) Ünlü düşmesi …") aynı sebeple atlanır:
  `soru_coz.py` tek bir `olay` alanına göre seçenek metnini tarar, çoklu-kategori seçimini
  desteklemiyor. Kapsam genişletilirse bu format harness'a eklenebilir.

### Fiiller (çatı/fiilimsi) — 2026-08-06 ölçümü

Sözcükte Yapı'nın aksine bu domain **kısmen** sağlam çıktı. `harness/fiil_coz.py`,
`altin/fiil_sorulari.jsonl` — aynı "aday tek seçeneğe düşerse cevap" mantığı, `SES.*` yerine
`ek_kimlikleri` önekine bakıyor (`EK.SIFATFIIL/ISIMFIIL/ZARFFIIL` = fiilimsi,
`EK.BIRLESIK.*` = birleşik çekim). 13 Fiiller 1.Test sorusu tek tek elle motora soruldu:

| Soru tipi | Durum | Sebep |
|---|---|---|
| Fiilimsi türü farklı olan (Q2) | ✓ çalışıyor | fiilimsi ekleri hep üretken, sözlükleşmiyor |
| Birleşik çekimli fiil (Q6) | ✓ çalışıyor | ek-fiilin FİİL üstündeki hâli (`EK.BIRLESIK.*`) sağlam |
| Fiilimsi yok (Q9) | ✓ çalışıyor | aynı mekanizma |
| İşteş fiil örneği (Q8) | ✗ atlandı | **Sözcükte Yapı ile aynı sözlükleşme hastalığı**: `tanışmak`,
  `barışmak`, `buluşmak` gibi çok yaygın işteş fiiller sözlükte çıplak kök, `-Iş` türetim izi yok |
| Ek-fiil var/yok (Q7) | **✓ çözüldü (dördüncü tur)** | nominal ek-fiil eklendi, bkz. aşağı.
  `EBA-FT1-07` doğrulandı. Q4 ("iki görev bir arada") hâlâ eklenmedi — ayrı, daha karmaşık bir
  ölçüt (aynı cümlede hem nominal hem fiil-kipli ek-fiil örneği arıyor), düşük öncelik |
| Kipler sırasıyla (Q1) | kısmi | tek kelimede belirsiz (`gelişmiş` sıfat-fiil mi kip mi) ama
  elemeyle çözülebilir; istek kipi artık var ama kip-etiket-eşleştirme çözücüsü henüz yazılmadı |
| Sözde özne / "tarafından" (Q12) | ✗ atlandı | basit metin deseni yetmiyor — üç seçenekte de
  literal "tarafından" yok, ayrım örtülü/anlamsal |
| Zaman kayması (Q3), geçişlilik (Q10) | kapsam dışı | sırasıyla anlamsal ve değerlik-sözlüğü
  gerektiriyor (Faz 3) |
| Edilgen fiil hangisi (Q11, numaralanmış cümle) | **motor artık dürüst belirsiz** | bkz. altta |
| "-im eki ek-fiil görevinde mi" (Test2 Q11) | ✗ atlandı (sebep değişti) | nominal ek-fiil artık
  çözülüyor ama bu soru tek bir `-im` örneğini hedefliyor; cümledeki BAŞKA bir kelime
  (`ederdi`, gerçek birleşik çekim) yanlış pozitif veriyor — "altı çizili tek sözcük" ailesiyle
  aynı kategori hata, bkz. §5 |

**Edilgen/dönüşlü ayrımı — `veri/ekler.json`'a düzeltme yapıldı:** `-Il/-In` eki motor
tarafından hep "edilgen" etiketleniyordu; `EK.CATI.DONUSLU.IL/IN` yoktu. Yani `atıldı` gibi
kelimeler her zaman edilgen sayılıyordu, dönüşlü okuma (`Q11`'de "hemen atıldı" = kendini attı)
hiç üretilmiyordu — bu bir belirsizlik değil, düpedüz eksikti. Eklendi (2026-08-06); artık
`-Il/-In` alan her fiil hem edilgen hem dönüşlü okuma üretiyor (test:
`testler/test_fiil.py::test_edilgen_donuslu_belirsizligi`). Gidiş-dönüş yeniden doğrulandı
(%100), ses bilgisi altın kümesi etkilenmedi (SES.* olayları `ek_kimlikleri`nden ayrı izlenir).

**Çoklu-seçim mekanizması eklendi (2026-08-06, ikinci tur):** `harness/fiil_coz.py`'ye
`coklu_var`/`coklu_yok` tipi eklendi — numaralanmış cümlelerin ("I ve III", "Yalnız II" gibi
birleşim metinli seçenekler) çözülebilmesi için. `ogeler` (numara→cümle) ile `secenekler`
(harf→birleşim metni) ayrı sözlükler; roma rakamı ayrıştırma `\b(IV|III|II|I|V)\b` deseniyle
(uzun eşleşme önce). `EBA-FT2-01` bununla doğrulandı.

**Denenip eklenmeyenler (2. Test taraması):**
- "İsim-fiil ve sıfat-fiil birlikte kullanılmamıştır" (Test2 Q2) — `-ecek` eki hem gelecek
  zaman kipi hem sıfat-fiil olabiliyor; "herhangi bir okumada var mı" taraması `görülecektir`
  gibi açıkça kip olan bir kullanımda bile sıfat-fiil okumasını buluyor (yanlış pozitif).
  `kesin` (her okumada ortak) mantığına geçmeden güvenilmez.
- Kip-etiket eşleştirmesi (Test1 Q1, Test2 Q7: "parantez içindeki kipe uygun mu") — henüz
  bir çözücü yazılmadı (kip adı ↔ `EK.KIP.*` eşlemesi + karşılaştırma mekanizması gerekiyor),
  ama altındaki iki kapsam boşluğu beşinci turda kapandı: istek kipi artık var, soru eki "mi"
  doğru modellendi. Yalnızca 2. tekil emirin işaretsizliği kalıcı bir sınır (bkz. aşağı).
- "-im eki ek-fiil görevinde mi" (Test2 Q11) — nominal ek-fiil kapsam boşluğu kapandığından beri
  `miyim` doğru çözülüyor, ama soru format olarak hâlâ uymuyor (bkz. beşinci tur notu aşağı).
- "Türemiş yapılı rivayet birleşik fiil yoktur" (Test2 Q13) — hem "türemiş yapı" hem "rivayet
  birleşik" birlikte aranıyor; elle çözümlemede bile tek bir seçenek net çıkmadı (iki seçenek
  aynı anda kritere aykırı görünüyor) — soru muhtemelen doğru ama analiz güvenilir değil,
  eklenmedi.

**3. ve 4. Test taraması (2026-08-06, üçüncü tur) — tam katalog:**
Sayfa 131-138 (kitap 129-136) elle taranıp mevcut mekanizmalarla eşleşen tek yeni tip bulundu:
"numaralanmış cümlelerin hangisinde **tüm fiilimsi çeşitlerinin** (sıfat-fiil+isim-fiil+zarf-fiil)
örneği bir arada var" (Test3 Q6) — `FIILIMSI_UCU_DE` özelliği olarak eklendi, `EBA-FT3-06`
doğrulandı. Geri kalan ~25 soru şu kalıplardan birine düştüğü için eklenmedi:

| Kalıp | Örnek | Neden atlandı |
|---|---|---|
| "Kategori seçenekli" çoklu-kavram listesi (5 farklı kavram, her biri ayrı bir ölçüt) | Test1 Q8, Test2 Q8/Q9/Q12, Test4 Q1/Q2/Q3/Q7/Q8/Q9/Q11 | `fiil_coz.py` tek bir `ozellik`i N cümlede tarar; burada N *farklı* ölçüt tek pasajda aranıyor — farklı bir mimari gerekir (bkz. aşağı) |
| Geçişlilik / nesne (kaç fiil geçişli) | Test2 Q9/Q10, Test3 Q9/Q10, Test4 Q10 | değerlik sözlüğü yok, Faz 3 |
| Anlam kayması (zaman kullanımının bağlamla çelişmesi) | Test1 Q3, Test4 (çeşitli) | anlamsal, morfolojik değil |
| Kurallı birleşik fiil | Test1 Q4, Test4 Q8 | **kapsam boşluğu beşinci turda kapandı** (tezlik/süreklilik/yaklaşma artık var) — ama bu iki soru yine de eklenmedi, format "kategori seçenekli" (yukarıki satır) |
| Yardımcı eylemle kurulan birleşik fiil (dikkat etmek, kaybolmak gibi çok-kelimeli/kalıplaşmış) | Test2 Q8, Test4 Q11 | motor tek kelime çözümlüyor, çok-kelimeli birleşik fiil yapısı hiç modellenmiyor |
| Sözde özne / örtülü özne ("tarafından" ötesi) | Test3 Q12 | anlamsal/örtülü, basit desen yetmiyor |
| Fiilimsi **sırası** (3 fiilimsinin hangi sırayla geçtiği) | Test3 Q7 | tek başına yeni bir mekanizma gerektirir, düşük öncelik |

**Gerçek ÖSYM sorusuyla dış doğrulama (2026-08-07):** `osym-cikmis-sorular.txt`'ye eklenen
2023 YKS TYT sorusu ("hem isim-fiil hem sıfat-fiil hem de zarf-fiil yer almaktadır" —
numaralanmış I-V tam cümle, EBA/OGM kaynaklı değil, gerçek sınav) `FIILIMSI_UCU_DE`
mekanizmasıyla tek denemede temiz DOGRU verdi (`YKS2023-FIILIMSI-01`, cevap III). Bu,
mekanizmanın yalnızca EBA'nın kendi soru havuzuna değil bağımsız bir ÖSYM kaynağına da
genellediğini gösteriyor — daha güçlü bir doğrulama. Aynı dosyadaki diğer 6 yeni soru
incelendi, hiçbiri eklenmedi: "yer tamlayıcısı" sorusu zaten bilinen sub-constituent-hedefleme
sınırına giriyor (bkz. Tamlamalar bölümü); iki soruda ("ses olayları hangisi yoktur", "durum
ekleri hangisi yoktur") seçenek metinleri hiç verilmemiş (yalnızca "Cevap: X"); bir soru
("sözcük türü sırası") kapalı-sınıf + numaralanmış-tek-sözcük formatında (İsim Soylu
Sözcükler'in askıya alınma sebebiyle aynı); bir soru öge dizilişi (özne/nesne/yüklem, Faz 3);
bir soru "kategori seçenekli" (A-E her biri farklı bir dilbilgisi ölçütü, tek pasaj) formatında
— bu üç mimari uyumsuzluk zaten belgeli (bkz. yukarı, "Kategori seçenekli" satırı).

**`ogm-materyal.txt` taraması (2026-08-07, MEB'in ÖSYM-tarzı hazırladığı sorular):** Kullanıcının
eklediği 9 sorudan 1'i (fiilimsi hepsi-bir-arada, Charles Dickens parçası) `FIILIMSI_UCU_DE`
ile tek denemede DOGRU verdi — OCR yazım hataları (`hâllerine`, `İngiltere'den`, `deneyimleri`,
`ilişkilerini`, `külyutmaz` gibi) elle düzeltilerek eklendi (`OGM-FIILIMSI-01`). `fiil_coz`
artık 8/8. Diğer 8 soru eklenmedi, hepsi net gerekçelerle:
- **Öge dizilişi** (2 soru, özne/nesne/yer tamlayıcısı sırası) — Faz 3 "Cümlenin Ögeleri",
  tam sözdizimi çözümlemesi gerektiriyor.
- **Cümle yapısı farklı olan** (Dadaruh parçası) — "basit/birleşik/sıralı cümle" ayrımı kaç
  bağımsız yargı (tam yüklem) olduğunu saymayı gerektiriyor; bu Cümle Türleri/Faz 3 işi,
  fiilimsi varlığından ayrı bir mekanizma ister.
- **"Kökünün türü bakımından farklı"** (Çevresel/uygulamaları/varlığını/düşük/kısıtlanıyor) —
  Sözcükte Yapı ile aynı sözlükleşme engeli: `düşük` sözlükte çıplak Noun/Adj olarak duruyor
  (`düş`+`ük` türetimi yok), `varlığını`/`kısıtlanıyor` da motorda birden fazla kök türü
  (Noun/Adj/Verb) üretiyor — ÖSYM'nin beklediği TEK doğru kök türü sözlükleşmiş bir kabule
  dayanıyor, motor dürüstçe belirsiz.
- **"Tamlama türü bakımından farklı"** ("Bastıkları yerleri" diğer 4 isim+iyelik tamlamasından
  farklı, çünkü tamlayanı bir sıfat-fiil öbeği) — ilginç bir örnek ama `farkli_tur`
  mekanizmasıyla YAKALANAMADI: "yerleri" de (yer+ler+i) olası mantıkla iyelik-3 okuması
  taşıyor, tüm 5 seçenek "tamlanan var" çıkıyor (BOŞ sonuç). Gerçek ayrım farklı bir özellik
  gerektiriyor (tamlayanın kendisi fiilimsi mi) — tek örnekle yeni bir mekanizma kurmak riskli
  görüldü, eklenmedi. Daha fazla benzer örnek gelirse değerlendirilebilir.
- **Ses bilgisi + "Ulama" seçeneği** (Niğde şiiri) — "Ulama" bizim 7 kuralımızdan biri değil
  (kelime sınırını aşan bir telaffuz olayı, §6'da zaten kapsam dışı ilan edildi) — beş
  seçenekten biri hiç değerlendirilemediği için soru eksik kalıyor. Üstüne seçenek metinleri
  de OCR'da bozuk ("Unlü", "Unsiz yumusamasi" — düzeltme işaretleri kaybolmuş), tekrar
  kontrol edilmeden eklenmedi.
- **Sözcük türü sırası** (Anton Çehov parçası) — İsim Soylu Sözcükler'le aynı kapalı-sınıf
  engeli (zamir/sıfat/zarf ayrımı), zaten askıya alınmış domain.

**Genel sonuç:** Fiiller'de iş yapan mekanizmalar (fiilimsi var/yok/farklı-tür/hepsi-bir-arada,
birleşik çekim var/yok, tekli+çoklu seçim) **tekrar tekrar doğrulandı** ve güvenilir. Kalan
sorular çoğunlukla iki nedenden tıkanıyor: (1) çok-kavramlı "kategori listesi" formatı — bunun
için `fiil_coz.py`'ye tamamen farklı bir çözücü (tek pasaj + N farklı ölçüt) yazmak gerekir,
bu oturumun kapsamı dışında bırakıldı; (2) gerçek kapsam boşlukları — **nominal ek-fiil,
istek kipi, kurallı birleşik fiilin üç alt türü ve soru eki "mi"** hepsi kapatıldı (aşağı).
Yalnızca **çok-kelimeli birleşik fiil / değerlik sözlüğü** (Faz 3) ve **2. tekil emirin
işaretsizliği** (bilinçli, düşük öncelik) hâlâ açık.

### Motor eklemeleri (2026-08-06, dördüncü tur) — "fool-proof" geçişi

Kullanıcı isteği: ölçülen kapsam boşluklarını tahmin etmeden, veriyle motora ekle.

**1. Nominal ek-fiil.** `EK.KISI.Z.*` (5 kişi eki), `EK.BILDIRME`, `EK.BIRLESIK.HIKAYE/RIVAYET/
SART` daha önce yalnızca fiil kipi durumlarından (`KIP_ZAMIR`/`KIP_IYELIK`) besleniyordu. İsim/
sıfat yüklemi üstündeki hâli (`öğrenciyim`, `menekşeydi`, `arkadaşımdı`, `bahçesiyse`,
`kitabımdır`) **hiç çözülemiyordu** — bu, Fiiller sorularının üçte birinin tıkandığı nokta
olduğu için en yüksek öncelikliydi. Çözüm: bu ekler artık `ISIM_KOK`, `HAL_SONRASI`,
`IYELIK_SONRASI`, `IYELIK3_SONRASI`, `COGUL_SONRASI` durumlarından da kaynaklanıyor
(`veri/ekler.json`). Testler: `testler/test_fiil.py` "Ek-fiil (isim/sıfat yüklemi)" bölümü
(9 pozitif + 1 negatif — `ILGI_SONRASI` bilerek dışarıda bırakıldı, "kedininim" hâlâ çözülemez).

**Beklenmeyen yan etki — mimariyi öğreten bir bulgu:** `ISIM_KOK` durumu yalnızca çıplak isim/
sıfat kökleri için değil, **sıfat-fiil çıktısı için de ortak kullanılıyor** (`EK.SIFATFIIL.DIK`
ve `.ACAK`'ın `hedef`i de `ISIM_KOK`). Bu yüzden `beğendiğim` gibi kelimeler artık *sahte* bir
ek-fiil okuması da kazandı (beğen-dik + ek-fiil kişi eki gibi okunabiliyor, anlamsız ama
yapısal olarak üretilebilir). Motor "tespit değil türetim" ilkesi gereği bunu engellemedi —
üretilebilen her okuma döner. Çözüm motorda değil **harness'ta**: `harness/fiil_coz.py`'nin
`EKFIIL` ölçütü *olası* (herhangi bir okuma) değil **kesin** (kelimenin *her* okuması ek-fiil
göstermeli) mantığıyla yazıldı, çünkü sahte okumanın yanında hep gerçek (iyelik) okuma da var
ve kesin mantığı bunu eler. **Ders:** paylaşılan durumlara (`ISIM_KOK` gibi) yeni kaynak eklemek
o durumu besleyen *her* ekin çıktısını etkiler — yalnızca hedeflenen ekler için değil, o duruma
akan bütün yollar için düşünülmeli.

**2. İstek kipi.** `EK.KIP.ISTEK.1T/2T/1C/2C` eklendi (`+yAyIm`, `+yAsIn`, `+yAlIm`, `+yAsInIz`).
3. kişi (`-A`, `-AlAr`) bilerce dışarıda bırakıldı — çok kısa/çakışmaya açık bir arketip, hiçbir
gerçek soruda görülmedi. Test: `test_istek_kipi_cozumleniyor` (6 pozitif).

### Motor eklemeleri (2026-08-07, beşinci tur) — Fiiller boşlukları tamamlandı

**4. Kurallı birleşik fiil (tezlik/süreklilik/yaklaşma).** Dördüncü turda "ikinci bir tam
fiil kökü gerektirir, ayrı bir iş" diye bırakılmıştı — yanlış tahmindi. Çatı ekleriyle
(`EK.CATI.*`) **aynı graf deseni** (`kaynak: FIIL_KOK`, `hedef: FIIL_KOK`) yeterli çıktı,
tıpkı zaten var olan `EK.YETERLILIK` (+yAbil) gibi. Eklenenler: `EK.TASVIR.TEZLIK` (+yIver:
gidiver, bakıver), `EK.TASVIR.SUREKLILIK.GEL/DUR/KAL/GOR` (+yAgel/dur/kal/gör: süregel,
bakadur, şaşakal, tutagör), `EK.TASVIR.YAKLASMA` (+yAyaz: düşeyaz). Yumuşama gibi diğer ses
olayları müdahalesiz otomatik doğru çıkıyor (git→gidiver ama bak→bakıver, sözlükteki mevcut
Voicing özniteliğinden). Test: `test_kuralli_birlesik_fiil_cozumleniyor` (6), `test_tasvir_
eki_ustune_kip_gelir`.

**5. Soru eki "mi".** `Ques` türü çıkışsız `DEGISMEZ` durumundaydı; artık kendi durumu
(`SORU_EKI_SONRASI`) var — yalnızca ek-fiil ekleri (`EK.KISI.Z.*`, `EK.BILDIRME`,
`EK.BIRLESIK.*`) oradan kaynaklanıyor, tam `ISIM_KOK` değil (yanlışlıkla "minin"/"milik" gibi
sahte isim çekimleri üretilmiyor — test: `test_soru_eki_isim_cekimi_almaz`). `miyim` artık
**doğru sebeple** çözülüyor (önceden "mi" notası tesadüfiydi, o okuma hâlâ ayrı bir aday
olarak duruyor ama artık gerçek `Ques` okuması da var). Test2 Q11 yine de eklenmedi — neden
artık kapsam boşluğu değil, format uyumsuzluğu: soru tek bir `-im` örneğini hedefliyor,
cümledeki başka bir kelime (`ederdi`) hâlâ yanlış pozitif veriyor (`EKFIIL` cümle geneline bakar).

**Kapatılmayan tek kalem: 2. tekil emir** (sıfır ek, "sakla!"). Bilinçli bırakıldı: eklenecek
bir *ek* yok — emir zaten ek yokluğuyla işaretleniyor, "pozitif" bir etiket ancak zayıf ekli
okumaya sentetik bir imza uydurarak eklenebilirdi ki bu hem riskli (başka okumalarla
karışabilir) hem şu an kullanacak bir çözücü yok (kip-etiket-eşleştirme mekanizması hâlâ
yazılmadı). Ölçülmeden kural eklenmez ilkesi burada "ölçülmeden ek de eklenmez"e genişledi.

**Regresyon (her iki tur sonrası da tekrarlandı):** `pytest` 329→**348/348**, `harness.olc`
109/109 + 79/79, `harness.altin_dogrula` ✓, `harness.soru_coz` 11/13 doğru + 2 belirsiz,
`harness.fiil_coz` 6/6, `harness.gidis_donus --ornek 500` %100 (53.670 üretim, her ekleme
sonrası tekrar). Hız 1.9→2.7 ms/kelimeye düştü (graf iki turda da genişledi) — kabul edilebilir.

### Kapsam taraması gerçek metinle (2026-08-07, altıncı tur)

`harness.kapsam --dosya osym-tyt-turkce-sorular.txt` — model çağrısı yapmadan, ücretsiz.
Sonuç **%89.18**, önceki GLM ölçümüyle (%96.86) **doğrudan karşılaştırılamaz** (bu dosya
kısmen OCR bozuk: Roma rakamları, tek harf seçenek işaretleri, bozuk kelimeler gürültü
yapıyor). Gürültü ayıklanınca üç gerçek bulgu çıktı, biri düzeltildi:

- **`-ki` aitlik eki zarflara hiç uygulanamıyordu** (`sonraki`, `yarınki` `COZULEMEDI`) —
  `Adv` türü çıkışsız `DEGISMEZ` durumundaydı, tıpkı `Ques`'in beşinci turdaki hâli gibi.
  Aynı desenle düzeltildi: kendi dar durumu (`ZARF_KOK`) — yalnızca `EK.AITLIK` kaynaklanır,
  tam `ISIM_KOK` değil (`sonrada`/`sonranın` gibi sahte hâl/iyelik çekimleri üretilmiyor).
  Test: `test_zarfta_aitlik_eki_cozumleniyor`, `test_zarf_kok_isim_cekimi_almaz`.
  Kapsam %89.18→%89.36. `bugünkü`/`dünkü` hâlâ çözülemiyor — bunlar `-ki` değil düzensiz
  `-kü` alan iki kelimelik kapalı bir istisna, dar fayda için eklenmedi.
- **`reklam` sözlükte hiç yok** — gerçek sözlük boşluğu (Zemberek kaynağında eksik), motorun
  mekanizmasıyla ilgisi yok, düzeltilmedi (kaynak dosyaya dokunulmaz, bkz. §8).
- **`siyasi` çözülemiyor ama `siyasî` (düzeltme işaretli) çözülüyor** — sözlük yalnızca eski
  yazımı biliyor. Düzeltilmedi: düzeltme işaretini körlemesine düşürmek riskli, çünkü
  `hâlâ` (hâlâ/henüz) ile `hala` (babanın kız kardeşi) gibi anlamca ayrışan çiftler var.
  Hangi kelimelerde güvenli olduğunu belirlemek ayrı, dikkatli bir iş — ölçülmeden yapılmadı.

**Regresyon:** `pytest` 348→**351/351**, `harness.olc`/`altin_dogrula`/`soru_coz`/`fiil_coz`
değişmedi (yalnızca zarf durumu etkilendi), `gidis_donus --ornek 500` %100 (56.407 üretim).

### Kesme işareti düzeltmesi (2026-08-07, yedinci tur) — büyük olası etkili

Tamlamalar için gerçek bir ÖSYM sorusu ("Türkiye'nin başkenti...") elle denenirken bulundu:
**kesme işaretli özel ad + ek kombinasyonu hiç çözülmüyordu** (`Türkiye'nin`, `Ankara'da`,
`Ali'nin` — hepsi `COZULEMEDI`). Kanıt: aynı kelimeler kesme işaretsiz (`türkiyenin`,
`ankarada`) sorunsuz çözülüyordu. Sebep: `kelimeyi_cozumle` yalnızca `fonetik.kucult()`
uyguluyordu (büyük→küçük harf), kesme işaretini hedeften hiç çıkarmıyordu — ama **üretici
kesme işaretini asla üretmez** (saf yazım kuralı, fonetik bir olay değil), bu yüzden hedef
hiçbir üretilmiş yüzeyle tam eşleşmiyordu.

**Düzeltme:** `cozumleyici.py`'de `_KESME_ISARETI_TABLOSU` — eşleştirme hedefinden kesme
işareti çıkarılıyor (`kelime` alanı özgün yazımı koruyor). Tek satırlık, dar kapsamlı bir
değişiklik ama etkisi geniş olabilir: özel ad + ek kalıbı gerçek Türkçe metinde son derece
yaygın, bu muhtemelen **şu ana kadarki her kapsam ölçümünü** (GLM'in %96.86'sı dahil)
sessizce aşağı çekiyordu. Test: `test_kesme_isaretli_ozel_ad_cozumleniyor`,
`test_kesme_isareti_orijinal_yazimda_kalir`.

`TDK'nin`/`3'ün` hâlâ çözülemiyor — ama bunlar ayrı, ilgisiz boşluklar: "tdk" kısaltması
sözlükte yok, sayılar zaten kelime deseninin (`_KELIME_DESENI`, `\d` hariç) kapsamı dışı.

**Regresyon:** `pytest` 351→**356/356**, `harness.olc`/`altin_dogrula`/`soru_coz`/`fiil_coz`
değişmedi, `gidis_donus --ornek 500` %100 (56.407 üretim). Kapsam (osym-tyt dosyası)
%89.36→**%89.98** — bu dosyada mütevazı (kısmen OCR bozuk), temiz metinde muhtemelen
daha büyük. GLM ile temiz metinde yeniden ölçüm hâlâ yapılmadı.

### Kategori seçenekli sorular (2026-08-07, sekizinci tur)

**Ses olayı — artık desteklenir.** `osym-cikmis-sorular.txt`'ye gerçek 2023 YKS sorusu
eklendi ("Bu parçada aşağıdaki ses olaylarından hangisi yoktur?" — seçenekler A-E ses olayı
**kategori adı**, tek pasaj). Daha önce §5'te "kapsam genişletilirse eklenebilir" diye not
düşülen tam bu format. `soru_coz.py`'ye `tip: "kategori_yok"` eklendi — seçenek metni
(`"Ünsüz benzeşmesi"` gibi) `veri/kural_haritasi.json`'daki `ad` alanından kural kimliğine
çözülür (yeni bir veri kopyası değil, var olan tek kaynağın yeniden kullanımı), tüm pasaj
`_olay_var_mi` ile taranır, hiç görülmeyen kategori cevap olur. `YKS2023-KATEGORI-01` tek
denemede temiz DOGRU verdi (5 kategoriden 4'ü pasajda var, yalnız "Ünlü daralması" yok —
cevap anahtarıyla birebir). `soru_coz` artık 12/14 (2 eski BELİRSİZ değişmedi).

**Durum (hâl) ekleri — aynı desen denendi, bu örnekte başarısız, gerçek bir dilbilimsel
sınır bulundu.** Kullanıcının eklediği başka bir gerçek soru ("Bu parçada aşağıdaki durum
eklerinden hangisi yoktur?", seçenekler İlgi/Ayrılma/Yönelme/Bulunma/Belirtme, cevap:
Belirtme yok) için aynı mimariyle `harness/hal_coz.py` yazıldı — kategori adı → ek kimliği
eşlemesi bu kez `veri/ekler.json`'daki `ad` alanından (yine tek kaynak). Sonuç: **başarısız**,
ama motor hatası değil — gerçek bir keşif. `karşılaşılacağı`, `sonudur` gibi kelimelerde motor
`EK.HAL.BEL` (belirtme hâli) okumasını üretiyor ama **her seferinde** yanında birebir aynı
konumda bir `EK.IYELIK.3T` (3. tekil iyelik) okuması da çıkıyor — çünkü "-I/-sI" yüzeyi
Türkçede 3. tekilde belirtme hâli ile iyelik-3'ü **yapısal olarak ayırt edilemez** kılar
(tam olarak "kitabı" belirsizliğinin aynısı — aşağıdaki "Model katmanı planı" notuna bkz —
burada yeni bir domainde ortaya çıktı). "Olası" (herhangi bir okuma) taramasıyla bu yüzden
Belirtme hemen her pasajda "var" görünüyor — soru tam olarak Belirtme'nin **yok** olduğunu
sorduğu için mekanizma bu örnekte çöktü. Diğer dört kategori (İlgi/Ayrılma/Yönelme/Bulunma)
bu çakışmayı taşımıyor (elle doğrulandı: `duygulardan`, `vagonda` gibi kelimeler temiz, tek
okuma üretiyor) ama tek bir gerçek örnekle bütün domaini güvenilir ilan etmek "ölçülmeyen
iyileşmez" ilkesine aykırı olurdu. **Karar:** `hal_coz.py` depoda kalıyor (mekanizma kendi
içinde doğru, veri tekrarı yok) ama altın küme dosyası (`hal_sorulari.jsonl`) **bilinçli
olarak oluşturulmadı** — bu soru eklenip BELİRSİZ/YANLIŞ görünmesindense hiç eklenmemesi
tercih edildi. Gerçek çözüm bağlamsal isim/sıfat-fiil ayrımı gerektirir (Faz 2/3), tıpkı
"kitabı" ve isim_coz.py'deki keçi/karanlık gerilimi gibi.

**Fiiller'e dış doğrulama.** Aynı `osym-cikmis-sorular.txt` taramasında bulunan bir 2023 YKS
sorusu ("hem isim-fiil hem sıfat-fiil hem de zarf-fiil yer almaktadır") mevcut
`FIILIMSI_UCU_DE` mekanizmasıyla (fiil_coz.py) tek denemede DOGRU verdi — EBA dışı, bağımsız
bir kaynakla mekanizmanın genellediğini doğruladı. `fiil_coz` artık 7/7 (`YKS2023-FIILIMSI-01`).

**Regresyon:** `pytest` 356/356, `harness.olc`/`altin_dogrula` değişmedi, `harness.soru_coz`
12/14 (2 belirsiz), `harness.fiil_coz` 7/7.

### Motor hatası düzeltmesi (2026-08-07, dokuzuncu tur) — geniş zaman kısıtı yanlış gövdeye bakıyordu

**Bulunuş:** `harness.kapsam` çıktısındaki çözülemeyenler taranırken `kitaplaştırır` (OCR
bozukluğu değil, gerçek bir kelime) dikkat çekti. Kök araştırması motor seviyesinde ciddi bir
mantık hatası ortaya çıkardı — bu bir kapsam boşluğu değil, **CLAUDE.md §9'un kendi ilkesini
çiğneyen bir kod hatasıydı**.

**Hata:** `bitig/cozumleyici.py` ve `bitig/uretici.py`'de bir ekin uygulanabilirliği
(`gerektirir`/`yasaklar`, örn. "-(I)r yalnızca Aorist_I köklerine gelir") **çıplak KÖKÜN**
özniteliklerine bakılarak denetleniyordu (`girdi.oznitelikler`), o anki gövdenin son
morfemine (`govde_oz`) değil — tam da "Öznitelikler köke değil, gövdenin o anki son morfemine
aittir" ilkesinin ihlali. Kod içinde bunu "doğru" gösteren yanlış bir yorum bile vardı ("geniş
zaman eki kökün düzensizliğine bakar, araya giren ekin değil").

**Etkisi sanılandan büyük çıktı.** `kitaplaşır`/`kitaplaştırır` (isimden fiil -lAş, sözlükte
karşılığı olmayan türetim) gibi nadir örneklerle başladı ama asıl önemlisi: **edilgen, dönüşlü,
ettirgen, işteş, yeterlilik ve kurallı birleşik fiil eki almış HER fiil**, kökü Aorist_A
tipindeyse (`yap`, `kır`, `at`...) geniş zamanda **hiç çözülemiyordu** —
`yapılır`/`kırılır`/`yaptırır` gibi çok sıradan kelimeler bile. Bu şimdiye kadar hiçbir altın
kümede yakalanmamıştı çünkü çoğu yaygın çatı türevi (`atıl`, `karşılaş`, `hastalan`...) AYRICA
sözlükte kendi başına bir fiil girdisi olarak duruyor — o girdi üzerinden çözülüp asıl hatayı
gizliyordu. Gerçek Türkçe kuralı: çatı/yapım eki almış fiiller kökün geniş zaman tipine
bakmaksızın **her zaman dar (Aorist_I)** tiptedir (yapar ama yapılır, yapılar değil) — bu,
motorun kendisinin bilmediği ama TYT müfredatının ezber kuralı olarak öğrettiği bir gerçek.

**Düzeltme, iki parçalı (CLAUDE.md §9'daki "gövde küçülür kuralı" dersiyle aynı desen —
tek bir yerde düzeltmek yetmiyor):**
1. `veri/ekler.json`: `EK.CATI.EDILGEN.IL/IN`, `EK.CATI.DONUSLU.IL/IN`, `EK.CATI.ISTES`,
   `EK.CATI.ETTIRGEN.DIR/T`, `EK.YETERLILIK`, `EK.TASVIR.*` (tezlik/süreklilik/yaklaşma,
   6 ek) ve isimden fiil `EK.YAPIM.LA/LAN/LAS` artık kendi `oznitelikler`inde `Aorist_I`
   taşıyor — bu ekler gövdenin geniş zaman tipini SIFIRLAR, kökten miras almaz.
2. `bitig/cozumleyici.py` (~satır 269) ve `bitig/uretici.py` (~satır 91): kontrol artık
   `govde_oz`e bakıyor, `girdi.oznitelikler`e değil. Yanlış yorum düzeltildi.

**Ayrı, ilişkisiz ikinci hata aynı taramada bulundu:** `EK.ISIMFIIL.IS` (-yIş, "gidiş/yapış")
arketipi çıplak `"Iş"` idi — ünsüzle biten gövdede (`geliş`, `bakış`) sorunsuz ama ünlüyle
bitende (`yürü`, `oku`, `söyle`) kaynaştırma-y hiç eklenmiyordu, `yürüyüş`/`okuyuş`/`söyleyiş`
gibi çok sıradan kelimeler çözülemiyordu. `"+yIş"` yapıldı (diğer kaynaştırmalı eklerle aynı
"+X" sözdizimi, bkz. `turetim.py:ek_yuzeyi_coz`).

**Neden gidiş-dönüş bunu hiç yakalamadı:** `--hepsi` taraması SÖZLÜKTEKİ köklerden üretim
yapıyor; sorunun kalbi tam olarak **sözlükte kendi başına bulunmayan, canlı türetilen**
fiillerdi (`kitaplaş`, ya da `yapıl` sözlükte olsa bile ONUN ÜZERİNDEN değil `yap`+edilgen
ZİNCİRİNDEN üretim yapan dal) — round-trip taraması her kökü kendi başına dener, çok basamaklı
zincirin ORTASINDAKİ kısıt hatasını görmez çünkü o kökün kendi Aorist tipi zaten doğru
sonucu üretir. Hata yalnızca **çıplak kökten türetilen çok basamaklı bir zincirde** görünür
hâle gelir — gidiş-dönüşün mimari körlüğü, "kesin/olası" ayrımına benzer başka bir ders.

**Regresyon:** `pytest` 356→**373/373** (17 yeni test, `testler/test_fiil.py`), `harness.olc`
109/109 + 79/79, `harness.altin_dogrula` ✓, `harness.soru_coz` 12/14, `harness.fiil_coz` 7/7,
`harness.isim_coz` 1/2 + 1 belirsiz — **hiçbiri değişmedi**, hiçbir altın kümede regresyon yok.
Kapsam (osym-tyt dosyası) %89.98→**%90.25**. `gidis_donus --ornek 2000` (yalnızca aorist
düzeltmesi) 226.583 üretim, **%100.0000** bütünlük; `--ornek 800` (iki düzeltme de dahil,
tekrar) 90.251 üretim, yine **%100.0000** — 0 kayıp, hiçbir regresyon yok.

**Model katmanı planı — Faz 2 madde 1 olarak uygulandı (2026-08-07), bkz. §6.**

### Temiz metin kapsam ölçümü + üç motor düzeltmesi (2026-08-07, onuncu tur)

**Kapsam ölçümü tamamlandı.** `harness.kapsam --tur 10 --cumle 40` (modelden temiz,
OCR'sız metin) → 390 cümle, 3.724 farklı sözcük, **%97.66**. Bu, GLM'in önceki ölçümüyle
(%96.86) karşılaştırılabilir — hatta biraz üstünde — ve `osym-tyt-turkce-sorular.txt`'nin
%89.98'inin o dosyanın kısmi OCR bozukluğundan kaynaklandığını doğruluyor (temiz metinde
gerçek kapsam çok daha yüksek).

**`çelikço` kenar durumu düzeltildi.** Kök nedeni: "çelikço" (sözlükte "Ext" işaretli,
nadir/standart dışı) "o" ile bitiyor — Türkçenin GENİŞ ünlüleri a/e/o/ö'dür ama
`_daralmayi_geri_al` (ünlü daralmasının ters çevirimi, çözümleyicide kök adayı üretir)
yalnızca a/e deniyordu ("daralma geniş ünlüyle biten fiillerde olur, a/e yeterli" varsayımı
— a/e köklerde ezici çoğunlukta olsa da o/ö nadiren de olsa mümkün). Düzeltme: dört geniş
ünlü de (a/e/o/ö) deneniyor artık, motor hangisinin geçerli olduğuna karar veriyor (tespit
değil türetim ilkesi burada da korunuyor — biz tahmin etmiyoruz, adayları üretip motora
soruyoruz).

**`reklam` sözlüğe eklendi.** `veri/tyt_override.json`'ın `ekle` alanına tek satır
("reklam") — daha önce Zemberek kaynağında eksik olduğu bilinen, sıradan bir isim kökü.

**Kritik motor hatası bulundu ve düzeltildi — `-IcI` (fiilden isim, "okuyucu" tipi).**
Kapsam taramasında `belirleyici`, `izleyicinin`, `sınayıcı`, `dinleyicinin`, `taşıyıcısı`,
`koruyucu` gibi ÇOK SAYIDA kelime aynı anda çözülemeyince ortak kök arandı: `EK.YAPIM.ICI`
(-IcI eki) hiç çözülmüyordu — "oku" bile (hiçbir ek zinciri olmadan, çıplak `-ıcı` ile)
"okucu" üretiyordu, "okuyucu" değil! Sebep: arketip `"(I)cI"` yazılmıştı — bu sözdizimi
"yalnızca gövde ÜNSÜZLE bitiyorsa görünen yardımcı ünlü" anlamına gelir (`EK.KIP.GENIS.I`
gibi "(I)r" eklerinde doğru kullanım budur). Ama `-IcI` TAM TERSİNE, gövde ÜNLÜYLE
bittiğinde kaynaştırma-y'ye ihtiyaç duyuyor (oku+**y**ucu, izle+**y**ici) — doğrusu
`"+yIcI"` (`EK.SIFATFIIL.AN`'daki `"+yAn"` ile birebir aynı sözdizimi, oku+**y**an ile
aynı desen). Düzeltildi.

**Etki büyük olabilir.** `-IcI` Türkçenin en üretken eklerinden biri — hemen her fiil kökü
alabilir (okuyucu, yazıcı, satıcı, alıcı, verici, izleyici, düzenleyici, taşıyıcı,
üretici, tüketici, geliştirici, sağlayıcı, uygulayıcı...). Ünsüzle biten kökler zaten
doğru çalışıyordu (yaz→yazıcı, kaynaştırma gerekmediği için sorun görünmüyordu), yalnızca
ÜNLÜYLE biten kökler etkileniyordu — ama bu Türkçede son derece yaygın bir gövde sınıfı.
Bu, hiçbir altın kümede yakalanmamıştı çünkü altın kümeler bu ekin ünlü-final gövdelerini
hiç test etmiyordu; yalnızca gerçek/temiz model metniyle yapılan kapsam taraması buldu —
"ölçülmeyen iyileşmez" ilkesinin bir kez daha somut kanıtı.

**Ayrı, ilişkisiz bir bulgu — düzeltilmedi:** `kavur` kökü de `-IcI` (kavurucu) ve hatta
düz geniş zamanda (`kavurur`) hâlâ çözülemiyor — ama bu YUKARIDAKİ düzeltmeyle ilgisiz,
önceden var olan bir sorun. `kavur` sözlükte `LastVowelDrop` taşıyor ("kavrulmuş",
"kavrulur" gibi EDİLGEN biçimlerde gerçekten düşme oluyor, doğru) ama bu öznitelik
YANLIŞLIKLA aorist/-IcI gibi düşmemesi gereken eklerde de tetikleniyor. Tek kök etkiliyor,
düşük öncelik, bu turda düzeltilmedi (kapsamı genişletmeden önce ayrı bir araştırma
gerektiriyor — hangi eklerin düşmeyi tetiklemesi/tetiklememesi gerektiği netleşmeli).

**Regresyon:** `pytest` 437→**446/446** (9 yeni test, `testler/test_turetim.py`),
`harness.olc` 109/109 + 79/79, `harness.altin_dogrula` ✓, `harness.soru_coz`/`fiil_coz`/
`isim_coz` değişmedi, `gidis_donus --ornek 1000` iki kez çalıştırıldı (çelikço sonrası ve
-IcI sonrası), ikisinde de **%100.0000** (113.294 üretim, 0 kayıp) — hiçbir regresyon yok.

### Yeni EBA kaynak taraması + 12 yeni altın küme kaydı (2026-08-09, on birinci tur)

Kullanıcının `ogmmateryallink.txt`'ye eklediği 8 link (7 EBA PDF + 1 web sayfası) tek tek
tarandı — amaç ad_cekimi/fiil_cekimi altın kümelerinin hâlâ büyük ölçüde Claude yazımı
olan kısmını gerçek MEB kaynağıyla değiştirmek (§6 madde 4).

**`mculdxo1bts.pdf` (Noktalama + Ses Bilgisi, 64s) — yüksek değerli, tam işlendi.** Ses
Bilgisi bölümü (s.48-64) programatik (pypdf) çıkarılıp 11 alt kural + örnek kök listesi
motora tek tek soruldu. **12 yeni kelime doğrulandı ve altın kümeye eklendi** (mevcutta
olmayanlar, `bileği`/`sınıfta`/`aklı`/`benzi`/`şıkkı`/`reddi`/`arabaya`/`ikisi`/`elbisesi`
→ `ad_cekimi.jsonl`; `kesti`/`dinliyor`/`oynuyor` → `fiil_cekimi.jsonl`). `ad_cekimi.jsonl`
115→**124**, `fiil_cekimi.jsonl` 80→**83**. Regresyon: `harness.olc` 124/124 + 83/83,
`harness.altin_dogrula` ✓ tutarlı, `pytest` 458/458 — hiçbir değişiklik yok, sıfır regresyon.

Tarama sırasında iki apaçık anomali araştırıldı, ikisi de **motor hatası değil** çıktı:
- **`araba` çıplak hâliyle beklenmedik SES.YUM.01 gösteriyordu** — gerçek bir homograf
  çakışması: `araba` (taşıt, isim, olaysız) ile `Arap+a` (bir Arap'a, yönelme hâli,
  yumuşama) yüzeyce birebir aynı. Çekimli hâli (`arabaya`) kullanılınca çakışma ortadan
  kalkıyor, yalnızca istenen SES.KAY.01 çıkıyor — bug değil, yanlış test girdisi.
- **`omuzu` beklenen ünlü-düşmesi okumasını üretmiyor, sahte bir `o`+ek ayrıştırması
  veriyordu** — çünkü standart Türkçe'de düşmesiz "omuzu" değil düşmüş "omzu" doğrudur;
  motorun bu yüzeyde omuz-kökenli okuma ÜRETMEMESİ aslında doğru davranış. Sahte `o` ayrıştırması
  ayrı, zararsız bir homograf artığı — düzeltilmedi, düşük öncelik.

**Bir gerçek, sistematik boşluk doğrulandı (düzeltilmedi):** kaynağın "ünsüz türemesi"
örnekleri arasındaki yardımcı-fiilli birleşik fiiller (`hissetmek`, `affetmek`, `zannetmek`,
`hallolmak`, `kaydetmek`, `reddetmek`) motorda **tamamen sözlükleşmiş çıplak Verb kökü**
olarak duruyor (`ekler`/`olaylar` boş) — SES.UT.01'in bu alt-deseni bu kelimelerde asla
tetiklenemiyor. Sözcükte Yapı'daki sözlükleşme duvarının (§5) bir SES.* kuralını da
etkileyen ilk somut örneği. Altın kümeye eklenmedi (motor doğrulayamıyor).

**Geri kalan 5 link tarandı, hiçbiri altın kümeye yeni madde vermedi — hepsi net gerekçeyle:**

| Kaynak | Sayfa | Sonuç |
|---|---|---|
| `hk0k3tz0ehw.pdf` (Fiiller) | 43 | Saf teori (ek fiil/fiilde yapı/fiilimsi/çatı) — `fiil_coz.py`'nin zaten kapsadığı alanla birebir örtüşüyor, yeni kelime listesi yok. İçinde 2 gerçek gömülü ÖSYM sorusu var (2020-TYT dahil) ama ikisi de "numaralanmış TEK sözcük" formatında (bkz. §5, kopyalamada bozulur diye zaten atlanan format) — eklenmedi. |
| `jhha50lsh3r.pdf` (İsim Soylu Sözcükler) | 40 | `veri/kapali_sinif_kelimeler.json`'daki MEB listesiyle (zamir/sıfat/zarf/edat/bağlaç) neredeyse birebir aynı içerik — zaten kapsanmış. Bir gömülü gerçek soru var, yine "numaralanmış tek sözcük" + kapalı-sınıf/anlamsal karışımı (İsim Soylu'nun zaten belgeli mimari sınırı) — eklenmedi. |
| `jtcsf1jtdgt.pdf` (Yazım Kuralları) | 52 | Farklı bir domain: büyük/küçük harf, bitişik/ayrı yazım, sayı yazımı, düzeltme işareti — bunlar **morfolojik değil, imla kuralı** (yazım.py Track A'nın kapsadığı ses-olayı-unutma hatası değil, TDK Track B'nin kapsadığı sözlük geçerliliği de değil, üçüncü bir kategori: yazım KONVANSİYONU). Düzeltme işareti bölümündeki eşsesli çift listesi (adet/âdet, adem/âdem, aşık/âşık, alem/âlem) §5'teki "siyasi/siyasî" boşluğuna ileride faydalı olabilir ama bu, yeni bir mekanizma gerektiren ayrı bir iş — Faz 1'i kapatmaya girmiyor, not düşüldü. |
| `1pww1q03g5z.pdf` (Anlatım Bozuklukları) | 30 | `anlatim.py`'nin zaten mekanize ettiği 5 türle örtüşmüyor; kalan türler (mantık hatası, yapısal bozukluk, eylemsi eksikliği, yüklem eksikliği) hep anlamsal/sözdizimsel — zaten "modelin işi" diye sınıflandırılmış (§6 Faz 2). Cevap anahtarlı temiz bir soru bulunamadı, `ogm-materyal.txt`'deki 40 sorudan daha düşük değerli. |
| `turkedebiyati.org/isim-cekim-ekleri/` | web | Saf teori + örnek yüzey (ör. "kitab-ım"), ses olayı sistematik gösterilmiyor, sınav sorusu yok. MEB/EBA kaynaklarının altında bir kaynak (§5 sıralaması), yeni bir şey vermiyor. |

**Sonuç:** Faz 1 madde 4 tamamen kapanmadı (ad_cekimi/fiil_cekimi hâlâ ağırlıkla Claude
yazımı — 124/12 ve 83/3 oranında yeni MEB-kaynaklı) ama bu turda taranabilir tüm yeni
kaynaklar (7 PDF + 1 web sayfası) tüketildi; geri kalanı yeni bir kaynak bulunmadan
ilerlemez. `sr2wvi0dbjy.pdf` zaten önceki oturumda tüketilmişti (Sözcükte Yapı, §5).

---

## 6. Öncelik sırası

### Şu anki faz — ölçüyü gerçek yapmak
1. ~~EBA sayfalarını aktar~~ — Ses Bilgisi + Fiiller yapıldı. Sözcükte Yapı **kısmen açıldı**
   (29 gerçek ÖSYM sorusundan 7/29 mekanize edildi, bkz. §5) — geri kalan 22 gerçek
   dilbilgisel belirsizlik/sözlükleşme/mimari sınıra takılı, kapanması olası değil.
   İsim Soylu Sözcükler için de kapalı sınıf verisi + bağlamsal çözücü kondu (`isim_soylu.py`,
   19/19 elle kurulmuş testte), ama gerçek ÖSYM sorularıyla (EBA sayfa 109-118) henüz
   ölçülmedi — o materyal bu oturumda elde değildi.
2. ~~Tam sözlük gidiş-dönüş taraması~~ — **2026-08-07 tamamlandı**, `çelikço` kenar-durumu
   da **aynı gün düzeltildi** (bkz. §5 sonundaki "onuncu tur").
3. ~~Kapsamdaki kalan boşluk (temiz metin)~~ — **2026-08-07 tamamlandı.** Modelden temiz
   (OCR'sız) metin toplanıp ölçüldü: **%97.66** — GLM'in önceki ölçümüyle (%96.86)
   karşılaştırılabilir, hatta biraz üstünde. `osym-tyt-turkce-sorular.txt`'deki düşük
   sayının (%89.98) o dosyanın kısmi OCR bozukluğundan kaynaklandığı doğrulandı. Bkz. §5
   sonundaki "onuncu tur" — bu taramadan kritik bir motor hatası da bulundu.
4. **Hâlâ açık, ama kaynak tükendi.** Altın kümelerin Claude yazımı kısımlarını ÖSYM/MEB
   maddeleriyle değiştirmeye devam ediliyor — 2026-08-09'da `mculdxo1bts.pdf`den (bkz. §5
   "on birinci tur") 12 yeni kayıt eklendi (`ad_cekimi.jsonl` 115→124,
   `fiil_cekimi.jsonl` 80→83). Aynı turda taranan geri kalan 5 kaynak (7 EBA PDF'i +
   1 web sayfası) hiçbir yeni madde vermedi — hepsi ya zaten kapsanmış teoriydi ya da
   "numaralanmış tek sözcük" gibi bilinen bir mimari sınıra takıldı (ayrıntı §5). Çekirdek
   altın kümeler hâlâ ağırlıkla Claude yazımı (124 kayıttan 12'si, 83 kayıttan 3'ü şu an
   gerçek MEB kaynaklı) — ilerlemek için **yeni bir kaynak** gerekiyor, elde tüketilmemiş
   kaynak kalmadı.
5. ~~İsim Soylu Sözcükler ve Tamlamalar EBA sayfaları~~ — İsim Soylu Sözcükler için
   `isim_soylu.py` bağlamsal çözücüsü kondu (bkz. madde 1), Tamlamalar için
   `harness/isim_coz.py` yazıldı (**2/3** doğru, 1 bilinçli belirsiz — isim/sıfat çift
   okumalı köklerde çözülmemiş bir gerilim var, bkz. §5). Altın küme hâlâ dar (3 kayıt),
   genişletilebilir.

### Faz 2 — bağlam ve dil bilgisi genişlemesi
Sözcük türü/görevi motoru (**bağlam duyarlı** — belirsizliği daraltan katman) · anlatım
bozukluğu üretici motoru · noktalama motorunun üretim yönüne çevrilmesi · heceleme/ses uyumu ·
atasözü-deyim genişletmesi · çözücü ensemble.

> Belirsizlik şu an bilinçli olarak korunuyor. `kitabı` hem belirtme hem iyelik okunuyor ve
> ikisi de dönüyor. Doğru olanı seçmek Faz 2'nin işi; motor aday kümesini eksiksiz vermekle
> yükümlü, seçmekle değil.

**1. Bağlam duyarlı okuma seçici — başlandı (2026-08-07).** `baglam.py` (repo kökü, `bitig/`
DIŞINDA — üretim hattı hiçbir model çağrısı yapmaz kuralı gereği, `harness/model.py`'yle aynı
gerekçe). Motor çıktısına dokunmaz (`bitig/osym.py`'deki `gorus()` ile aynı desen): ayrı,
salt-okunur bir `BaglamSecimi` nesnesi üretir, `kaynak` her zaman `Kaynak.SEZGISEL` —
`kesin_olaylar`a asla giremez, yalnızca soru çözme/tutoring akışında kullanılır.

**Jenerik açıklama, elle yazım yok:** her okumanın insan-okunur açıklaması (`okuma_aciklamasi()`)
`veri/ekler.json`'daki `ad` alanlarından üretilir ("kitap (Noun) + Belirtme hâli" gibi) — modele
belirsizlik türü başına elle İngilizce/Türkçe metin yazmak gerekmedi. Önce iki elle-yazılmış
prototipte (kapalı iki-seçenek: `karanlık`/`keçi`) doğrulandı, sonra jenerik N-okuma biçimiyle
(kaynaştırma/hâl-iyelik, çatı, isim/sıfat — 3 farklı belirsizlik türü) tekrar denendi, ikisi de
aynı isabetle çalıştı.

**Ölçüm:** `harness/baglam_coz.py` + `altin/baglam_sorulari.jsonl` (6 vaka) — **ağ çağrısı
yapar, ücretlidir, normal `pytest`e dahil değil**, elle çalıştırılır. Sonuç: 5/6 doğru.
Tek hata (`BAGLAM-KIRILDI-01`, "Cam yere düşünce hemen kırıldı") **tesadüfi değil, iki kez
aynı çıktıyla tekrarlandı**: model "dönüşlü"yü "kendiliğinden/dışarıdan etken belirtilmemiş"
ile karıştırıyor, oysa dönüşlü çatı öznenin eylemi **kendi üzerinde bilinçli** yapmasını
gerektirir (cansız özne "cam" için linguistik olarak uygunsuz) — GLM'in ses olayı
hakemliğinde v1'in hatasını tekrarladığı bulgusuyla ([[glm-testinden-cikan-bulgu]]) aynı
desen: model bazen ince dilbilgisi ayrımlarında güvenilmez. `okuma_aciklamasi`'nin ağ
gerektirmeyen kısmı `testler/test_baglam.py`'de test edilir (5 test, normal pytest'e dahil).

Model'e **asla** açık uçlu "bu olay var mı" sorulmaz — yalnızca motorun sunduğu kapalı okuma
kümesinden numarayla seçim yaptırılır (`sıcaklık=0.0`, `NUMARA: gerekçe` biçimi zorunlu).

**2. Anlatım bozukluğu — kelime-listesi kısmı başlandı (2026-08-07).** Kullanıcının
`ogm-materyal.txt`'ye eklediği 40 gerçek ÖSYM/MEB sorusu tek tek incelendi (bkz. sohbet
kaydı). Sonuç: bu alan **iki katmanlı** — çoğu alt tür (mantık hatası, anlam belirsizliği,
deyim yanlışlığı, yanlış anlamda kullanılan sözcük) saf anlamsal muhakeme gerektiriyor
(model işi, henüz yapılmadı), ama **beş alt tür hiç model gerektirmeden, salt kelime
eş-oluşumu taramasıyla** yakalanabiliyor — bunlar için `anlatim.py` yazıldı (repo kökü,
`baglam.py` gibi `bitig/` dışında ama bu kez ağ çağrısı da yok, tamamen deterministik):

| İç tur kodu | Örnek | ÖSYM etiketi |
|---|---|---|
| `CELISEN_SOZCUKLER` | "kuşkusuz ... sanırım" (kesinlik+belirsizlik aynı cümlede) | Çelişen sözcüklerin bir arada kullanılması |
| `YAKLASIKLIK_TEKRARI` | "yaklaşık bin kadar" | Gereksiz sözcük kullanımı |
| `ESANLAMLI_CIFT` | "ilgili ve alakalı", "her seferinde her kezinde" | Gereksiz sözcük kullanımı |
| `DEGISMEZ_NITELIK` | "beyaz kar" (kar zaten beyazdır) | Gereksiz sözcük kullanımı |
| `GEREKSIZ_COGUL` | "birçok türlerde" ("birçok" zaten çoğulu ima eder) | Gereksiz ek kullanımı |

Veri `veri/anlatim_kelime_listeleri.json`'da durur (`tyt_override.json` ile aynı disiplin:
her kayıt gerçek bir soruyla doğrulanmış, `gerekce` alanı kaynağı taşır). Listeler
**bilinçli olarak dar** — genel bir eşanlamlılar sözlüğü değil. Tek bir düşük-güvenli aday
(`kanıksanan`/`kabul edilen`) bulundu ama kendi kendine "düşük güven" diye işaretlenip
**eklenmedi** — dosyanın kendi "her giriş doğrulanmıştır" ilkesini çiğnemesin diye.

`GEREKSIZ_COGUL` kontrolü `bitig.cozumleyici`'yi kullanır (`EK.COGUL` kimliğine bakar) —
diğer dördü saf kök/yüzey eş-oluşumu. Ölçüm: `harness/anlatim_coz.py` +
`altin/anlatim_sorulari.jsonl` (5 vaka, **ağ gerektirmez**, normal `pytest`e dahil değil
ama ücretsiz — istenirse CI'a bile eklenebilir) → **5/5**. `testler/test_anlatim.py`'de
17 birim testi (normal pytest'e dahil).

**Motora bağlı dördüncü tür eklendi, üçü denendi ve güvenilmez bulundu (2026-08-07, aynı
tur, devam):**

- **`FIILIMSI_TUR_UYUMSUZ` — eklendi.** Nesne görevindeki (İYELİK + HÂL taşıyan) paralel
  fiilimsi öbekleri farklı türden olursa (isim-fiil + sıfat-fiil karışık) anlatım
  bozukluğudur — "gelişini (isim-fiil), kaldığını (sıfat-fiil) anlattı" (Q27, cevap B).
  Veri gerekmez, doğrudan `EK.ISIMFIIL.*`/`EK.SIFATFIIL.*` + `EK.IYELIK.*` + `EK.HAL.*`
  birlikte varlığına bakar — İYELİK+HÂL şartı zarf-fiili (`kalkıp`, ek almaz) ve bir ismi
  niteleyen çıplak sıfat-fiili (`yürüyen çocuk`, iyelik/hâl almaz) otomatik eler, negatif
  kontrolde ikisi de temiz çıktı (bkz. `harness.anlatim_coz`, `ANLATIM-FIILIMSI-01`, 6/6).
- **Tamlama türü uyumsuzluğu (Q6/Q14/Q28) — denendi, eklenmedi.** "askerî ve sağlık
  aracı" gibi örneklerde tamlayan adaylarının (kişi/belgisiz/klasik/askerî/sağlık) çoğu
  hem isim hem sıfat okunuyor — tam olarak isim_coz.py'deki `karanlık`/`keçi` gerilimi.
  "Olası" mantık yanlış pozitif, "kesin" mantık yanlış negatif üretiyor. Tek bir gerçek
  örnekle (üstelik üçü de aynı riski taşıyor) yeni bir mekanizma kurmak riskli görüldü.
- **Çatı uyumsuzluğu (Q32) — denendi, eklenmedi.** "uygulanır ve öğrenirdi" (edilgen +
  aktif karışık, kurallar öznesi mantıken "öğrenemez") doğru yakalandı ama negatif
  kontrolde (`"...yemek yer, sohbet eder, eğlenirdi"`) yanlış pozitif üretti: "eğlenmek"
  sözlükte yalnızca `-In` (edilgen/dönüşlü) ekli köklerden türüyor gibi görünüyor
  (`eğle`+`-In`), gerçekte artık üretken olmayan sözlükleşmiş bir kök — motor bunu canlı
  edilgenden ayırt edemiyor. Aynı "sözlükleşme istisna değil kural" engeli (bkz. Sözcükte
  Yapı, §5).
- **Yüklem/kişi uyumsuzluğu (Q20, şiir) — hiç denenmedi, zaten mekanize edilemez.** Hata
  2. tekil emrin ("unutma") "Ben" ile uyuşmamasından kaynaklanıyor ama 2. tekil emir
  motorumuzda **hiç işaretlenmiyor** (sıfır ek, §9'daki "kapatılmayan tek kalem" — bilinçli
  bırakılmıştı, burada da aynı sınır geçerli).

**Sonuç:** `anlatim.py` 6 tur, `harness.anlatim_coz` 6/6, `testler/test_anlatim.py` 21 test.
Kalan üç alt tür (tamlama, çatı, yüklem) modelin işi olarak kalıyor — hiçbiri şu an
motorun ek-kimlik/sözlük altyapısıyla güvenilir biçimde çözülemiyor.

**3. TDK yazım motoru — Track A (morfolojik) tamamlandı (2026-08-07).** Plan hafızada
zaten tam tasarlanmıştı ([[yazim-motoru-plani]]): yazım hataları İKİ ayrı problem, tek
bir bulanık-eşleştirme motoruna indirgenmez.

- **Track A (bu turda yapıldı) — morfolojik hatalar** (yumuşama/ünlü düşmesi/kaynaştırma
  vb. unutulması: "kitapı" yerine "kitabı"). `yazim.py` (repo kökü, ağ gerektirmez,
  tamamen deterministik). Mekanizma: aday yazım çözülemiyorsa, HER ses kuralı için
  "bu kural unutulmuş olabilir" varsayımıyla yapısal düzeltme adayları üretilir (ör.
  yumuşamamış ünsüzü yumuşat) — ama **biz karar vermeyiz, motor karar verir**: yalnızca
  `kelimeyi_cozumle` ile çözülen VE iddia edilen kuralı üreten adaylar döner. Tespit değil
  türetim ilkesi burada da tam uygulanıyor.
- **Ölçüm, elle yazılmış test kümesi olmadan:** `harness/yazim_dogrula.py` altın kümedeki
  (`ad_cekimi.jsonl` + `fiil_cekimi.jsonl`, 188 kayıt) HER doğru kelimenin motorun kendi
  ürettiği `Kanit` (once/sonra/konum) tersine çevrilerek "yanlış yazımı" programatik
  üretir — 121 vaka türedi. Sonuç: **100/100 gerçek vaka doğru bulundu** (21 vaka
  "tesadüfen geçerli okumaya sahip" olduğu için ayrı tutuldu — örn. "kapı" hem "kap+ı"
  hatası hem bağımsız bir kelime, motor ikincisini bulup aramayı hiç başlatmıyor; bu
  dürüst bir sınır, `baglam.py`'nin bağlamsal seçici işi, hata değil).
- **Prototipleme sırasında bulunan iki eksik, düzeltildi:** (1) yumuşama yalnızca k→ğ
  deniyordu, "-nk" istisnası (renk→rengi, k→g) eksikti — eklendi. (2) daralma yalnızca
  düz ünlü uyumunu (a→ı, e→i) deniyordu, yuvarlak uyumu ("söylüyor", CLAUDE.md §9'daki
  daralmış-gövdeye-göre-uyum kuralı) kaçırıyordu — artık her iki ünlü için TÜM dar
  aday (a→ı/u, e→i/ü) üretilip motora bırakılıyor, hangisinin doğru olduğunu biz
  seçmiyoruz.
- **Track B tamamlandı (aynı gün, ikinci yarı) — sözlüksel/alıntı kelime hataları**
  (restorant/restoran, çiğ börek/çi börek gibi TDK'nin tarihsel kararları + genel "bu
  kelime TDK'de var mı" sorgusu — kullanıcının isteğiyle kapsam genişledi, yalnızca
  bilinen istisna çiftleriyle sınırlı kalmadı). Üç parça, plandaki ayrım aynen korunarak:
  - `harness/tdk_istemci.py` — **ağ çağrısı yapan tek yer**, `sozluk.gov.tr/gts` uç
    noktasını sorgular (User-Agent başlığı zorunlu, yoksa bağlantı reddediliyor;
    başlık değeri saf ASCII olmalı — Türkçe harfli User-Agent latin-1 kodlamasında
    çöktü, düzeltildi). Anahtar gerekmez, uç nokta genel.
  - `veri/tdk_onbellek.json` — yerel dondurulmuş kopya (`veri/zemberek/` deseniyle
    aynı). `gecerli` (bool, birebir — bulanık eşleştirme yok) + `yonlendirme` (bilgi
    notu, karar verici değil — TDK'nin "► X" işareti hem yazım güncellemesini hem
    eşanlamlı öneriyi aynı biçimde taşıyor, ikisi API yanıtından ayırt edilemiyor:
    "çiğ börek"→"çi börek" yazım, "restoran"→"lokanta" öneri, ikisi de "► " ile
    geliyor).
  - `harness/tdk_senkron.py` — önbelleği dolduran/tazeleyen CLI (`--dosya`, `--tazele`
    seçenekleriyle), sorgular arası nezaket gecikmesi (0.3 sn). Zemberek'in ~29 bin
    kökünü toptan doldurmak **bilinçli olarak otomatik değil** — hacim/süre üzerine
    önce kullanıcıyla konuşulmalı (gidiş-dönüş `--hepsi` taramasıyla aynı ihtiyat).
  - `yazim.py::tdk_gecerli_mi()` — **ağ gerektirmez**, yalnızca önbelleği okur.
    Önbellekte yoksa `None` döner ("bilinmiyor"), bunu `gecerli=False` ("bilinip
    reddedilmiş") ile karıştırmaz.
  - Uçtan uca doğrulandı: `yanlız` (yaygın hata) → geçersiz, `yalnız` (doğrusu) →
    geçerli, `aktivite` → geçerli ama TDK "etkinlik"i öneriyor (yonlendirme bilgi
    notu olarak görünüyor, `gecerli`yi etkilemiyor).

`testler/test_yazim.py` 17 test (Track A: her kuraldan elle seçilmiş okunabilir örnek +
sınır durumlar; Track B: önbellek okuma, tümü ağsız — senkron aracının kendisi ağ
gerektirdiği için test edilmez, elle çalıştırılır).

**Track B önbelleği hacimli genişletildi + kritik bir sorgu hatası bulunup düzeltildi
(2026-08-08).** Gerçek kaynak metinlerden (`osym-tyt-turkce-sorular.txt`,
`osym-cikmis-sorular.txt`, `ogm-materyal.txt`) motorla kök çıkarılıp (çıplak yüzey değil,
her yüzeyin `kelimeyi_cozumle` ile bulunan kökü) 1696 yeni kelime TDK'ye soruldu — **9 →
1705 kelime, 0 hata**. İlk turda 306 kelime "geçersiz" çıktı; örnekleri incelenince (anla,
başla, bekle, oku, bil...) neredeyse hepsinin **fiil kökü** olduğu görüldü. Sebep: **TDK
sözlüğü fiilleri mastar (-mak/-mek) biçimiyle indeksliyor, motorumuzun kökü ise çıplak
gövde** — "anla" TDK'de yok ama "anlamak" var, doğrulandı (`anla`→geçersiz, `anlamak`→
geçerli). Bu, Track B'nin fiil köklerinde SİSTEMATİK olarak yanlış "geçersiz" ürettiği
anlamına geliyordu. Düzeltme: `harness/tdk_senkron.py::_sorgu_terimi()` — sorgulanan
kelime çıplak bir fiil köküyse (motorda ek'siz `Verb` okuması varsa), TDK'ye giden sorgu
`fonetik.uyumla_a(fonetik.son_unlu(kok))` ile doğru büyük ünlü uyumlu mastar eki eklenerek
oluşturulur (`anla`→`anlamak`, `bekle`→`beklemek`); **önbellek anahtarı yine çıplak kök**
olarak kalır, yalnızca TDK'ye giden sorgu değişir. Hangi kelimede mastar eklendiği
şeffaflık için kayda `sorgulanan` alanıyla not düşülür. Tüm önbellek `--tazele` ile
yeniden sorgulandı.

**Bilinen, kabul edilmiş sınır:** bazı çıplak kökler hem fiil hem başka bir tür olarak
homograf (`bin` = 1000 sayısı VEYA "binmek" fiilinin emri) — mekanizma bu durumda her
zaman fiil yorumunu seçip mastar ekler, sayı/isim anlamı için ayrı bir geçerlilik kontrolü
yapılmaz. Nadir bir durum, önbellek tek bir `gecerli` değeri tuttuğu için (iki anlamı ayrı
ayrı taşıyamıyor) kabul edilen bir basitleştirme, ölçülmeden genişletilmedi. Somut örnek:
`ay` (ay/moon, isim) ve `aş` (yemek, isim) sorguları "aymak"/"aşmak" fiillerine kaydı —
`gecerli` alanı ikisinde de doğru kaldı (tesadüfen ikisi de geçerli fiil kökleri) ama `aş`ın
önceki doğru `yonlendirme`si ("yemek (I)") kayboldu, isimle ilgisiz bir fiil sorgusuyla
değişti. `gecerli` alanı (tek karar kaynağı) etkilenmedi, yalnızca bilgi notu (`yonlendirme`)
bu nadir homograf durumunda daha az isabetli.

**Nihai sonuç:** `--tazele` ile tüm 1705 kelime yeniden sorgulandı, **449 kayıt değişti**
(neredeyse tamamı yanlış-negatiften doğruya), geçersiz sayısı 306'dan **37'ye** düştü
(%97.8 geçerli). 0 hata, `pytest` 458/458 temiz.

**4. Noktalama — ilk alt tür eklendi (2026-08-07).** `ogm-materyal.txt`'ye eklenen
Noktalama İşaretleri bölümü (kitap s.87-96, ~40 soru) tarandı: çoğu söylem/anlam
düzeyinde (bir öbeğin "ara söz" mü "eş görevli öge" mi olduğunu ayırt etmek gibi) —
motorun kapsamı dışında, modelin işi. Ama bir alt tür doğrudan motorun ek-kimlik
altyapısına bağlanıyor: **şart eki sonrası virgül yasağı**. `noktalama.py` (repo
kökü, ağ gerektirmez) — `EK.KIP.SART` (kavrayamasak, ise) ya da `EK.BIRLESIK.SART`
(edersek, isim/sıfat yüklemi üstünde) taşıyan bir kelimeden hemen sonra virgül
gelmesi hatadır.

**Gerçek bir soruda bulunan istisna, mekanizmaya dahil edildi:** virgülden sonra
kısa bir pencerede BAŞKA bir şart-ekli kelime daha varsa, bu virgül iki EŞ GÖREVLİ
şart cümleciğini ayırıyor demektir — doğru kullanım, bulgu üretilmez ("Hemen o anda
kavrayamasak, dile dökemesek de..." — ilk virgül burada doğrudur). Bu istisna
olmadan mekanizma bu cümlede yanlış pozitif verirdi.

Ölçüm: `harness/noktalama_coz.py` + `altin/noktalama_sorulari.jsonl` → **2/2**.
İkinci vaka (`NOKTALAMA-SART-02`) dürüstçe not düşüldü: kaynak cümleler gerçek bir
ÖSYM sorusundan (kısa çizgi hakkında, cevap B) ama BİZİM sorduğumuz soru farklı
("hangisinde şart-sonrası-virgül hatası var") — o sorunun cevap anahtarını
çözdüğümüz iddia edilmiyor, yalnızca gerçek cümleler üzerinde bağımsız bir
doğrulama. `testler/test_noktalama.py` 6 test.

**Kesme işareti doğruluğu — eklendi, TDK'nin resmi kural sayfasıyla doğrulandı
(tdk.gov.tr/icerik/yazim-kurallari/kesme-isareti, 2026-08-07).** `KESME_YANLIS_IYELIK`:
büyük harfle başlayan bir kelimede kesme işaretinden sonra 3. tekil kişi DIŞINDA
bir iyelik eki varsa hata (TDK: "Boğaz Köprümüzün", "Amik Ovamızın" — kesmesiz).

**Önemli mimari bulgu — sözlükte özel ad bayrağı hiç yok.** `boğaz`/`konya`/`haziran`
gibi kökler yükleme sırasında küçük harfe normalleştiriliyor (CLAUDE.md §9), özel ad
olduklarını gösteren ayrı bir öznitelik taşınmıyor. Bu yüzden asıl sinyal **metindeki
büyük harf**tir, sözlük değil — kelime büyük harfle başlamıyorsa hiç denenmez.

**Kesin mantık gerekti, ölçülerek bulundu:** "Hanım'a" (D seçeneği, doğru kullanım)
motorun sahte bir "han+ım" (1.tekil iyelik) okumasını da üretiyor — "olası" mantık
(herhangi bir okumada iyelik varsa) burada yanlış pozitif verirdi. Düzeltme: yalnızca
kelimenin **her** okuması iyelik taşıyorsa VE hepsi 3.tekil-dışıysa tetiklenir; "hanım"
okumasında hiç iyelik olmadığı için doğru şekilde elendi.

**Mekanize edilmeyen, TDK'de doğrulanmış ama uygulanamayan bir istisna:** "Kurum,
kuruluş, kurul, birleşim, oturum ve iş yeri adlarına gelen ekler kesmeyle ayrılmaz"
(Türk Dil Kurumundan). Bir özel adın "kurum adı" olup olmadığı anlamsal bir bilgi,
sözlüğümüz taşımıyor — İsim Soylu Sözcükler'deki kapalı-sınıf engeliyle aynı, bilinçli
olarak uygulanmadı (nadir bir yanlış-negatif riski kabul edildi).

**Ayrı bir yön, henüz yapılmadı:** kesme EKSİK olduğunda tespit (Haziranında →
Haziran'ında — TDK: ay adlarına gelen ekler de kesmeyle ayrılır). Ay adı listesi gibi
küçük ek bir veri gerektirir, ölçülmeden eklenmedi.

**Bilinen, kabul edilmiş sözlük boşluğu:** TDK'nin kendi örneği "Kuşadamızdaki"
kesmesiz hâliyle bile çözülemiyor — "Kuşadası" sözlükte "kuş"+"ada" değil, iyelik
gömülü bağımsız bir kök olarak duruyor. Motor mantığının hatası değil, `reklam`
örneğiyle aynı sınıf bir sözlük kapsam boşluğu.

Ölçüm: `harness/noktalama_coz.py` + `altin/noktalama_sorulari.jsonl` → **3/3**.
`testler/test_noktalama.py` 11 test.

**Zarf-fiil ardışıklığı eklendi (aynı gün) — ama altın kümeye GİRMEDİ, dürüst bir
ayrım.** `ZARFFIIL_ARDISIK_VIRGUL_EKSIK`: art arda gelen (aralarında başka zarf-fiil
daha olan) `EK.ZARFFIIL` ekli kelimeler arasında virgül eksikse hata ("yer alıp
herhangi bir yıkıma maruz kalmadan..." → "alıp,"dan sonra virgül gerekir). Kaynak
cümle gerçek (`ogm-materyal.txt`, Noktalama Q8 seçenek D) ama o sorunun kendisi
"hangi virgül HİÇBİR kategoriye örnek değil" diye soruyordu, "hangi virgül EKSİK"
diye değil — D'nin orijinal hâli virgülü zaten doğru koymuş. Bu yüzden genuine bir
ÖSYM cevap anahtarı eşleşmesi yok; altın kümeye zorlama yapılmadı. Test kapsamı
yerine geçti: gerçek cümle NEGATİF kontrol (virgül zaten doğru, bulgu üretilmemeli),
virgülü bilinçli olarak çıkarılmış bir varyant POZİTİF kontrol (açıkça "ÖSYM'nin
cevabı değil, bizim kurguladığımız bir sınama" diye etiketlendi) —
`testler/test_noktalama.py` artık 15 test. Gerçek bir "eksik virgül" sorusu
bulunursa altın kümeye o zaman eklenir.

**Geri kalanı** (eş görevli öge sıralaması, noktalı virgül/iki nokta seçimi, üç
nokta kullanım amacı, tırnak işareti, ara söz tespiti) modelin işi.

**5. Atasözü/deyim sözlüğü — veri katmanı kuruldu (2026-08-07).** Kullanıcının
önerdiği yöntem: `sozcukatlasi.com/atasozleri-ve-deyimler-sozlugu/data.json`
tek seferde 13.592 kayıt (2.391 atasözü + 11.201 deyim) veriyor. TDK'nin kendi
resmi API'siyle (`sozluk.gov.tr/atasozu?ara=`) çapraz doğrulandı — içerik
birebir aynı, sozcukatlasi TDK verisini toplu JSON hâline getirmiş (TDK'nin
kendi API'si `gts` gibi yalnızca tekli arama destekliyor, bulk export yok).
robots.txt izin veriyor, tek statik dosya — TDK Track B'deki "API'yi
bombardımana tutmama" kaygısı burada geçerli değil, onay beklenmeden indirildi.

`harness/atasozu_indir.py` (ağ, elle çalıştırılır, periyodik tazeleme) →
`veri/atasozu_deyim.json` (yerel dondurulmuş kopya, `veri/zemberek/` deseni,
2.5 MB). `atasozu.py` (repo kökü, **ağ gerektirmez**) — şimdilik yalnızca
sorgu katmanı: `bul()` (tam eşleşme) ve `ara()` (alt dize taraması).
`testler/test_atasozu.py` 6 test.

**Henüz yapılmayan, planlanan bağlantı:** anlatım bozukluğunun "deyim
yanlışlığı" alt türü (`anlatim.py`'nin "denenip eklenmeyenler" listesinde
duruyordu, ogm-materyal.txt Q10 — "kafanız darda kalmayınca" gibi bozuk bir
deyim) artık bu sözlükle mekanize edilebilir olabilir. Zorluk: deyimler
metne ÇEKİMLENMİŞ hâlde girer ("kafayı yedi", "kafayı yiyeceksin") — düz
metin taramasıyla tespit için motorun morfolojik normalleştirmesi
(çekimli fiili sözlük hâline döndürme) ayrıca gerekiyor, henüz kurulmadı.

**Kullanıcının düzeltmesi (2026-08-07):** YKS'de atasözü/deyimin asıl
kullanım alanı soru üretiminde nadir — daha çok **Paragrafta Anlam**
sorularında geçiyor (paragrafın içine bir atasözü/deyim yerleştirilir, "Bu
parçayla aynı anlamı taşıyan cümle hangisidir?" diye sorulur, şıklar başka
cümlelerdir). Bu, PARAGRAF ↔ CÜMLE **anlam eşleştirmesi** — derin anlamsal
kıyaslama gerektirir, morfolojik motorun değil modelin/Faz 3'ün işi. Sözlük
verisi (`atasozu.py`) yine de destekleyici bir bileşen olarak durabilir
(örn. paragrafta geçen deyimi tanıyıp anlamını modele bağlam olarak vermek)
ama BAŞLI BAŞINA bir mekanizma hedefi değil — düşük öncelikli, ölçülmeden
üstüne inşa edilmedi.

**6. Heceleme/ses uyumu (2026-08-12, ilk iskelet + aynı gün güçlendirme).**
`hece.py` (repo kökü, `anlatim.py` deseniyle: ağsız, sözlük gerektirmez,
yalnızca `bitig.fonetik` üzerine kurulu). Dört fonksiyon: `hece_bol()` (MEB
kuralı — iki ünlü arasındaki ünsüz kümesinin yalnızca SON ünsüzü sonraki
heceye bağlanır), `buyuk_unlu_uyumu()` (kalınlık-incelik, zincir kuralı: her
hece bir öncekiyle aynı sınıfta mı), `kucuk_unlu_uyumu()` (düzlük-yuvarlaklık:
düzden sonra düz, yuvarlaktan sonra düz-geniş ya da dar-yuvarlak),
`cumleyi_hecele()` (cümle seviyesi kullanım — motorun kendi `_KELIME_DESENI`
deseniyle kelime ayrımı, tek kaynak). `_YUVARLAKTAN_SONRA_IZINLI` kümesi elle
yazılmadı, `fonetik`teki mevcut sınıflandırmaların kesişimiyle türetildi.

**Kesme işareti desteği eklendi, TDK'nin resmî sayfasıyla doğrulandı**
(tdk.gov.tr/icerik/yazim-kurallari/hece-yapisi-ve-satir-sonunda-kelimelerin-bolunmesi):
"Kesme işareti satır sonuna geldiğinde yalnız kesme işareti kullanılır, ayrıca
çizgi kullanılmaz" — TDK'nin kendi örnekleri (`Edirne'nin` → `Edirne'-nin`,
`Ankara'dan` → `Ankara'-dan`) kesme işaretinin GÖVDENİN son hecesine yapışık
kaldığını gösteriyor. `hece_bol` bunu birebir uyguluyor: gövde normal kuralla
hecelenir, kesme işareti gövdenin son hecesine eklenir, ek kendi içinde ayrıca
hecelenip sonraki birim(ler) olarak eklenir (`Türkiye'nin` → `Tür-ki-ye'-nin`).
Büyük/küçük ünlü uyumu fonksiyonlarının **zaten** kesme işaretli kelimelerde
doğru çalıştığı görüldü (apostrof zaten ünlü sınıflandırmasına girmediği için
otomatik filtreleniyor) — ayrı bir kod yolu gerekmedi.

**İki gerçek, öğretici bulgu ortaya çıktı (motor hatası değil, kuralın
tutarlı uygulanmasının doğal sonucu):**
- `Türkiye'nin` küçük ünlü uyumuna **uymuyor** (ü→i, yuvarlaktan sonra
  düz-dar) — "Türkiye" (Türk + Arapça kökenli -iye eki) `kalem`/`kitap` ile
  aynı sınıf bir alıntı/özel-ad istisnası. Büyük uyuma (kalınlık-incelik)
  uyuyor (tüm ünlüler ince) — iki uyum ekseni birbirinden bağımsız, biri
  tutması diğerinin tutacağını garanti etmez.
- `başkenti` büyük ünlü uyumuna **uymuyor** (a→e) — `başkent` (baş+kent)
  birleşik bir kelime; MEB birleşik kelimelerde büyük ünlü uyumunu aramaz,
  motor bunu bilmiyor (birleşik-kelime veri katmanı yok) ama en azından
  durumu SESSİZCE gizlemiyor, gerçek fonolojik uyumsuzluğu doğru raporluyor.

Web deneme sitesine 8. sekme olarak eklendi (`/api/hece`, `web/index.html`)
— her kelime için heceler + iki uyum sonucu (kanıtla birlikte) gösteriliyor.

**Hâlâ ölçülmedi, dürüstçe işaretli.** 44 birim testi (`testler/test_hece.py`,
kesme işareti dahil) yalnızca kuralın (MEB hece bölme + TDK satır-sonu kesme
işareti kuralı) doğru uygulandığını doğruluyor. **`harness/` altında bir
ölçüm aracı, `altin/` altında bir altın küme YOK** — bu tür soru (heceleme/
ses uyumu) TYT'de son derece nadir sorulduğu için elde doğrulanabilir gerçek
bir ÖSYM kaynağı yok; ilerlemek için önce böyle bir kaynak bulunmalı. Kalan
bilinen sınır: ünlü uyumu istisnaları ve birleşik-kelime muafiyeti (kalem/
kitap/hediye/başkent gibi) bir VERİ katmanı (kök→istisna sınıflandırması)
gerektirir, henüz yok — `yazim.py`'nin TDK Track B'siyle aynı disiplinde
ayrı bir iş.

### Faz 3 — kurulum, anlam, üretim hattı
Cümlenin ögeleri · fiil çatısı + değerlik sözlüğü · yazım/kesme motoru · sözcükte anlam motoru ·
uçtan uca hat · benzersizlik kapısı.

### Motorun kapsamı dışında kalan TYT konuları
Gerçek sorular şunları da soruyor ama bunlar **türetim motorunun işi değil**:
- **Ulama** (`dört_yanıma`) → kelime sınırını aşar, telaffuz katmanı
- **n→m** (`Perşembe`, `İstanbul`) → yazım kuralı, türetimde bir şey olmaz. v1'in Kural 10'u
  bunu motora sokmaya çalışıyordu, kategori hatasıydı.
- **Sözlükleşmiş türetim** (`çevre`, `oyna`) → ÖSYM politika katmanına gider, motora değil

---

## 7. Doğrulama kapıları

Soru üretiminde her madde bu kapılardan geçer. Çoğu MEB'in bağlam temelli soru yazım
kılavuzundaki kontrol listesinden, hepsi makineyle denetlenebilir:

- Seçenek–metin birebir örtüşmesi yok (n-gram kontrolü)
- Seçenek uzunluk ve biçim dengesi; doğru cevap en uzun seçenek değil
- "Hepsi / hiçbiri" yasağı · çift olumsuzluk denetimi
- Aynı bağlama bağlı sorularda ipucu zinciri yok
- **`olayda_belirsiz` maddeler elenir** — motor bu bayrağı zaten üretiyor
- **Çözücü ensemble:** soru 3-5 çözücüye körlemesine çözdürülür.
  - hepsi doğru + aynı gerekçe → geçerli ama muhtemelen kolay
  - güçlü bir çözücü farklı şıkkı savunabiliyor → **çeldirici de doğru**, soru elenir
  - hiçbiri bulamıyor → soru bozuk veya cevap anahtarı yanlış
- **Benzersizlik kapısı:** korpusa ve geçmiş üretime karşı n-gram + gömme benzerliği

---

## 9. Pahalıya öğrenilmiş incelikler

Bunlar teste bağlı. Değiştirmeden önce ilgili testi oku.

**Ünlü uyumu hangi gövdeye bakar — kurala göre değişir:**
- Ünlü düşmesi (`LastVowelDrop`): **özgün** köke. `hapis` → "hapsi"; düşmüş gövde `haps`in
  son ünlüsü `a` olduğu için ona bakılsaydı "hapsı" çıkardı.
- Ünlü daralması (`ProgressiveVowelDrop`): **daralmış** gövdeye. `söyle` → `söyl` (son ünlü
  `ö`) → "söylüyor"; özgün köke bakılsaydı "söyliyor" çıkardı.

**Öznitelikler köke değil, gövdenin o anki son morfemine aittir.** `geleceğim`de yumuşayan `k`
`-AcAk` ekine aittir. Aynı mekanizma `burunlarım`ı da doğru yapar (`-lAr`ın özniteliği yok).

**Kural sırası:** ünlü düşmesi → yumuşama → ikizleşme. `kayıt` 1→2'yi, `tıp` 2→3'ü zorunlu kılar.

**Mekanizma ile öğretilen ad ayrıdır.** `oku` + `-Iyor` yapısal olarak ünlüyü düşürür (yoksa
"okuuyor" olurdu) ama **daralma bildirilmez**: `u` zaten dardır. Kural "geniş ünlü (a,e) daralır"
biçimindedir. Bunu bir ÖSYM sorusu yakalattı; motor önce yanlış cevap veriyordu.

**Budama, gövdenin geriye dönük değişebileceğini bilmeli.** `gelme` + `-Iyor` → `gelmiyor`;
gövde hedefin öneki değil. Fazla kesmek hızı 28 ms/kelimeye çıkarıyor, doğru kesmek 1.9 ms.

**Ters çevirim ileri şelalenin tam aynası olmalı ve bileşik uygulanmalı.** `kaydı` çözümlenirken
`kayd` → `kayt` → `kayıt` iki basamak gerekir.

**Özel adlar küçük harfe normalleştirilir** (`ayristirici.py`). Büyük harf yazım kuralıdır;
normalleştirilmezse 26 binden fazla özel ad hiç bulunamaz.

**Paylaşılan durumlara (`ISIM_KOK` gibi) yeni kaynak eklemek, o durumu besleyen HER ekin
çıktısını etkiler.** 2026-08-06: nominal ek-fiil eklerken `ISIM_KOK`'a kaynak eklendi;
`EK.SIFATFIIL.DIK/ACAK`'ın `hedef`i de `ISIM_KOK` olduğu için `beğendiğim` gibi kelimeler
sahte bir ek-fiil okuması kazandı. Motor bunu engellemedi (tespit değil türetim — üretilebilen
her okuma döner); çözüm harness'ta: `EKFIIL` ölçütü *olası* değil **kesin** (kelimenin *her*
okuması aynı şeyi göstermeli) mantığıyla yazıldı. Yeni bir ek eklerken hangi durumları
beslediğine bakılmalı — genelde birden fazla ek aynı durumu paylaşır.

**Yeni bir "gövde küçülür" kuralı (ünsüz düşmesi gibi) hem ileri hem geri çevirime eklenmeli.**
Üretici (`uretici.py`) doğru çalışsa bile çözümleyici (`cozumleyici.py`) hedef yüzeyden geriye
doğru kök adayı üretirken bu düşmeyi bilmezse (`_degismis_govdeden_kok_adaylari`), kelime hiç
çözülemez — `ufacık` başta böyleydi, `ufak` adayı hiç denenmiyordu çünkü "ufak" harfiyen
"ufacık"ın öneki değil (k düşmüş). Aynı mekanizma `_govde_uretebilir`e de (aday doğrulama)
eklenmeli, yoksa aday bulunsa bile elenir. **Üç ayrı yer, tek kural — biri eksik kalırsa
motor sessizce "çözülemedi" der, yanlış cevap vermez ama kapsam boşluğu doğurur.**

**"-CIk" küçültme eki gibi ÜNSÜZLE başlayan bir ek, yumuşama/ikizleşme/ünlü-düşmesi
zincirine (hepsi `ek_bilgisi.unluyle_basliyor` şartına bağlı) hiç girmez.** Gövdeyi
değiştiren yeni bir kural ekleniyorsa ve ek ünsüzle başlıyorsa, ayrı bir dal gerekir —
`daralma_var`/ünlü-daralması gibi ek çözülmeden ÖNCE işlenmeli (çünkü ekin kendi
benzeşmesi güncel gövdenin son sesine bakar: "ufak"→"ufa" düşmeden C→ç yerine c kalmalı,
"ufacık" değil "ufakçık" çıkardı).

**İsim/sıfat çift okumalı köklerde "olası" ile "kesin" mantığı birbirini iptal edebilir —
sözlük satır sırası bunu çözmeye yaramaz.** `harness/isim_coz.py` yazılırken `karanlık`
(isim+sıfat, isim okuması yanlış pozitife yol açıyor) "kesin" mantıkla düzeltildi ama aynı
düzeltme `keçi`nin (isim+sıfat, burada isim okuması *doğru*) doğru tamlamasını kaçırttı.
Sözlükteki iki girdinin *sırasının* (hangisi önce yazılmış) "asıl anlam"ı yansıttığı denendi —
yanlış çıktı: sıra dosyanın derleme bölümünü yansıtıyor (iki girdi arasında binlerce satır
fark olabiliyor), gerçek bir dilbilimsel sinyal değil. **Ders:** çift okumalı bir kökte hangi
okumanın "asıl" olduğu saf sözlük/morfoloji bilgisiyle çözülemez, bağlam gerekir — zorlamak
yerine hangi taraf daha az riskliyse (`olası`) o seçilip kalan vaka bilinçli BELİRSİZ
bırakılmalı (`not` alanıyla belgelenmeli, `OGM-UND-01` deseni).

---

## 11. Arka plan: 2028 değişikliği

MEB, 2028'den itibaren YKS'de Maarif Modeli'ne uygun **beceri temelli / bağlam temelli**
soruların yer alacağını açıkladı. Sınav sistemi ve puanlama aynı; değişen soruların kurgusu.
Türkçe'de paragraf ve dil bilgisi omurgası kalıyor, metinler uzuyor. 2026-2027 eski formatta.

MEB'in **Bağlam Temelli Çoktan Seçmeli Soru Yazım Kılavuzu** (tymm.meb.gov.tr) bu projenin
fiilî şartnamesi. Kural ID haritasındaki `meb_kodu` alanları bu kod sistemi için ayrıldı,
şimdilik boş.

---

## 12. Sonraki hedef

Türkçe hattı oturduktan sonra **TYT Matematik**. Aynı altyapı (kapılar, ensemble, benzersizlik,
kural ID, öğretmen kuyruğu) derse bağımlı değil, olduğu gibi taşınır. Matematikte doğrulama
bedava (CAS) ve çeldiriciler yanlış çözüm yolunun kodlanmasıyla üretilir.

Faz 1 bittiğinde tek konuluk kısa bir matematik denemesi planlanıyor.

---

## 13. Model destekli çözücü deneyi (GLM ajanı) — 2026-08-08

**Amaç ve çerçeve.** Kullanıcının önerisi: motoru ve MEB'in konu özeti kaynağını GLM-5.2'ye
**araç** olarak verip (RAG + tool calling), `sozcukte_coz.py`'nin mekanize edemediği soru
tiplerinde (kategori seçenekli, sözlükleşme gerektiren) modelin ne kadar ileri gidebildiğini
**test amaçlı** ölçmek — kesin çözüm olarak değil. Bu, CLAUDE.md §1 ilke 5'in ("çekirdek
mantık LLM'e bırakılmaz") bilinçli, sınırlı bir istisnası: sonuç hiçbir altın kümeye, motora
ya da üretim hattına geri beslenmedi, yalnızca ölçüldü ve rapor edildi.

**Kritik bağlam — bu bir üretim kararı DEĞİL.** Kullanıcının asıl planı GLM-5.2 gibi pahalı/
frontier modelleri üretimde kullanmak değil: maliyeti düşük tutup küçük modellerle (azami
~24B) başlamak, bu modelleri motor+RAG ile "güçlendirmek" (fine-tune), gelir arttıkça kademeli
büyütmek. GLM-5.2 burada yalnızca **keşif aracıydı** — altyapıyı doğrulamak ve hata sınıflarını
bulmak için; "24B ne kadar iyi olmalı" sorusunun cevabı değil.

### Kurulan altyapı

- **`harness/mebi_pdf_ayikla.py`** — MEBİ TYT Konu Özetleri - Türkçe PDF'ini (2026, MEB
  Ortaöğretim Genel Müdürlüğü, 128 sayfa, `ogm-large-cdn.eba.gov.tr/ogm-materyal/
  mebi-konu-ozetleri/tyt-turkce/tyt-turkce.pdf`) **programatik** (pypdf ile, elle
  transkripsiyon değil) 36 konuya ayırıp `veri/mebi_konu_ozetleri.json`'a yazar. Elle
  transkripsiyon bu oturumda iki kez paragraf/soru sırasını yanlış okuduğu için (bkz. §5,
  Sözcükte Yapı) artık tercih edilmiyor — programatik çıkarım tam sayfa numarası kaymasıyla
  (+2, basılı sayfa → PDF fiziksel sayfası) doğrulanmış durumda.
- **`harness/model.py::arac_ile_sor()`** — OpenAI uyumlu `tools` şemasıyla çok turlu, araç
  çağırabilen sohbet döngüsü (mevcut tek-atımlık `sor()`e ek, onu bozmadan). GLM'in ayrı bir
  `reasoning_content` alanı olduğu ve bunun `max_tokens` bütçesini (varsayılan 4000'den
  16-20000'e çıkarıldı) hızla tükettiği bu oturumda bulundu — düşük bütçede model hiç
  `tool_calls` ya da `content` döndürmeden `finish_reason: length` ile bitiyordu.
- **`harness/mebi_agent_coz.py`** — iki araç: `kelimeyi_coz` (motor çıktısı: kök/tür/
  ek_kimlikleri) ve `konu_getir` (MEBİ konu metni). Sistem istemi hem `A-E` hem de yalnız
  `I-V` (numaralanmış cümle/sözcük, seçenek listesi olmayan) cevap biçimini kabul edecek
  şekilde düzeltildi (aşağıya bkz.).
- **`veri/kapali_sinif_kelimeler.json`** — aynı MEBİ kaynağından (s.83-98) çıkarılan Zamir/
  Sıfat/Zarf/Edat/Bağlaç kapalı sınıf listeleri (85 kelime) — İsim Soylu Sözcükler'in veri
  boşluğunu kısmen kapatıyor, ama tek başına çözücü değil (bkz. §5).

### Bulunan, düzeltilen hatalar

1. **Roma rakamı ↔ harf karışıklığı (gerçek istem tasarım hatası, benim hatam).** Sistem
   istemi "cevabı A-E harfi olarak ver" diye sabitti; ama bazı gerçek ÖSYM soruları yalnızca
   (I)-(V) numaralı cümle sunuyor, seçenek harfi hiç yok. Model doğru cümleyi (V) bulup
   mecburen "5. harf = E" diye yanlış eşledi. İstem her iki biçimi de kabul edecek şekilde
   düzeltildi, `_CEVAP_DUZENI` regex'i `[A-EIVX]+` oldu.
2. **Halüsinasyon — aracın döndürmediği bir olayı iddia etme (tekrarlayan desen, 3 ayrı
   örnekte gözlendi).** Motor `kesin` olarak "olay yok" dediği hâlde model kendi kendine
   olay uydurdu: (a) klasikhoca Q1'de "fikrini" için var olmayan bir "r ünsüzü düşmesi"
   iddia etti (gerçek olay ünlü düşmesi, motor hiçbir olay göstermiyordu); (b) özgün
   OZGUN-08'de "üzdü" için motor `olaylar=[]` derken model "ünsüz benzeşmesi var" dedi; (c)
   aynı soruda "hissi"nin HER İKİ okumasının da (belirtme + iyelik) türeme taşıdığını motor
   açıkça gösterirken model "iyelik okumasında türeme yok" diye yanlış ayrım yaptı. Üçü de
   **araç doğru çağrılmış, çıktı doğru, ama modelin yorumu çıktıyla çelişiyor** — klasik
   halüsinasyon, araç erişimiyle otomatik çözülmüyor.
3. **Numaralı öğe karışıklığı.** klasikhoca Q3/Q5'te model paragraftaki (I)-(V) işaretlerini
   yanlış kelimeye bağladı (bir soruda numaralanmamış bir kelimeyi sorguladı, başka bir
   soruda doğru yapım-eki sayımını yanlış roma rakamına yazdı). Aynı bu oturumun kendisinde
   (Q4/Q5/Q25/Q26/Q27/Q28/Q29 paragraf-soru eşleşmesi) iki kez yapılan hatayla aynı sınıf —
   düzeltme önerisi (deterministik regex ile numaralı öğeleri önceden çıkarıp modele ayrı bir
   liste olarak sunmak) tasarlandı ama uygulanmadı, ölçülmedi.
4. **Geçici API tutarsızlığı.** Sıcaklık 0.0 olsa da GLM bazen bir turda ne araç çağrısı ne
   biçime uygun içerik döndürmüyor (`finish_reason` boş/kısa). Tekrar denemede (aynı soru,
   aynı parametreler) doğru sonuç geldi — sistematik değil, `coz()`'a 3 denemelik bir tekrar
   mekanizması eklendi.

### Dört hücreli ezber/genelleme testi

Kullanıcının sorusu: "gerçek ÖSYM sorularındaki başarı ezberden mi geliyor?" Bu sorular
herkese açık, geçmiş sınav soruları — GLM'in eğitim verisinde geçmiş olabilir. İki eksen:
gerçek (`osym-tyt-turkce-sorular.txt` + `osym-cikmis-sorular.txt`, kullanıcının derlediği 39
soru, `Cevap:`/`Çözüm:` satırları modele hiç gösterilmeden) vs. **özgün** (bu oturumda ilk kez
yazılan, hiçbir kaynaktan gelmeyen 8 Ses Bilgisi sorusu — her biri motorla tek tek doğrulanıp
hedef ses olayının SEÇENEKLER ARASINDA tek/benzersiz olduğu koddan kontrol edildi); araçlı vs.
araçsız (`harness/mebi_no_tool_coz*.py`, hiç `tools` verilmeden doğrudan cevap).

| | Gerçek (yayımlanmış) | Özgün (hiç yayımlanmamış) |
|---|---|---|
| **Araçlı** (`mebi_agent_coz_osym.py` / `mebi_agent_coz_ozgun.py`) | ~13-14/17 (%76-82, yarıda kesildi) | 7/8 (%87.5) |
| **Araçsız** (`mebi_no_tool_coz.py` / `mebi_no_tool_coz_ozgun.py`) | 11/13 (%85, yarıda kesildi) | 6/8 (%75, format hatası hariç %86) |

**Yorum:** Dört hücre de birbirine yakın (%75-87) — ne ezber ne araç erişimi keskin bir fark
yaratmıyor. En olası açıklama: GLM-5.2 frontier-sınıf bir model olduğu için TYT seviyesi
standart ses bilgisi kurallarını (yumuşama, benzeşme, kaynaştırma...) zaten derinlemesine
biliyor — ne özgün cümleleri "ezberleyebiliyor" ne de araçlara muhtaç. **Bu sonuç küçük
(24B) modele genellenemez** — o modelin aynı "zaten bilme" tabanı olmayacağı için araçlı/
araçsız farkının çok daha keskin çıkması bekleniyor; bugünkü deney bunu ölçmedi, yalnızca
altyapıyı ve hata sınıflarını doğruladı.

### Sıradaki plan (konuşuldu, henüz uygulanmadı)

- **Sentetik eğitim verisi, ucuz.** GLM-5.2'ye pahalı çok-turlu akıl yürütme yaptırmak yerine:
  ucuz/hızlı bir model (ya da altın kümeler + gidiş-dönüş üretimi) çok sayıda cümle üretir →
  **motor** doğru `ek_kimlikleri`/cevabı garanti eder → "ideal araç izi" programatik sentezlenir
  (GLM'e sormadan, çünkü zaten biliniyor). GLM-5.2 yalnızca motorun çözemediği zor/kenar
  durumlarda (damıtma kaynağı olarak) kullanılır — maliyeti küçük tutar.
  Bu, "tespit değil türetim" ilkesiyle birebir örtüşüyor.
  - Fine-tune verisinde özellikle bastırılması gereken davranış: **"yalnızca aracın
    döndürdüğünü söyle, üstüne yorum/tahmin katma"** — bugün 3 kez gözlenen halüsinasyon
    deseni.
- **Açıklama üretimi, iki katmanlı.** Motorun çözdüğü kısımlar için **şablon tabanlı**
  (motorun `Kanit` nesnesinden — önce/sonra/konum/tetikleyen_ek — doğal dile çeviri,
  garantili doğru, hiç model gerekmez); modelin çözdüğü zor kısımlar için modelin kendi
  akıl yürütme izi (`son_mesaj`) — ama yalnızca nihai cevap VE gerekçe aracın çıktısıyla
  tutarlıysa güvenilir sayılmalı, körlemesine değil.
  Bu, projenin en baştaki hedefiyle ("kanıta dayalı açıklamalı çözüm") doğrudan örtüşüyor —
  şablon açıklayıcı, fine-tune planından bağımsız olarak da öncelikli bir sonraki adım olabilir.
- **Ölçek planı:** küçük/ucuz model (≤24B) ile başla, motor+RAG ile güçlendir, gelir
  geldikçe büyüt. Türkçe bitince aynı desen (kapılar + motor/CAS eşdeğeri + öğretmen kuyruğu)
  matematiğe taşınacak (§12).

**Kalıcı dosyalar (deneysel, `harness/` altında, hiçbiri normal `pytest`e dahil değil, ağ
gerektirir/ücretlidir):** `mebi_pdf_ayikla.py`, `mebi_agent_coz.py`, `mebi_agent_coz_osym.py`,
`mebi_agent_coz_ozgun.py`, `mebi_no_tool_coz.py`, `mebi_no_tool_coz_ozgun.py`.
`veri/mebi_konu_ozetleri.json`, `veri/kapali_sinif_kelimeler.json` kalıcı veri.

### RunPod GPU kiralama ile gerçek model karşılaştırması — 2026-08-24/25

**Çerçeve:** §13'ün "küçük/ucuz model ile başla" planının ön çalışması — gerçek para (RunPod,
$10 bütçe, RTX 4090 24GB) harcanarak birden fazla açık ağırlıklı model, motor+araç altyapısıyla
(`mebi_agent_coz.py`'nin `ARACLAR`/`SORULAR`'ı, klasikhoca'nın 22 gerçek Sözcükte Yapı sorusu)
tek tek test edildi. Amaç kesin bir seçim değil, hangi modelin/hangi sunucu yığınının bu iş için
gerçekçi olduğunu **ölçerek** görmek.

**Altyapı bulguları (tekrar kullanılabilir):**
- vLLM'in bare `pip install vllm` (0.27.1) kurulumu her zaman en yeni torch+CUDA13 paket
  zincirini çekiyor. Pod'un NVIDIA sürücüsü CUDA 13'ü destekliyorsa (580.x+) sorunsuz; 570.x
  gibi CUDA 13'ü desteklemeyen bir sürücüde torch'u sonradan cu128'e zorlamak vLLM'in kendi
  önceden derlenmiş `_C_stable_libtorch` uzantısını (hâlâ `libcudart.so.13` bekliyor) kırıyor —
  **düzeltme torch'ta değil, baştan CUDA 13 destekleyen bir pod/sürücü seçmekte.**
- Gemma3-12B-it + vLLM + tool-calling (bitsandbytes 4-bit kuantizasyon, `--enable-auto-tool-
  choice --tool-call-parser pythonic`, vLLM deposundaki `tool_chat_template_gemma3_pythonic.
  jinja`) **çalışır hâle getirildi** — tek engel `flashinfer`'in JIT derlemesinin `ninja`'yı
  PATH'te bulamamasıydı (`.venv/bin/vllm serve` çağrısı venv'i PATH'e eklemiyor, `export
  PATH=.venv/bin:$PATH` sonra düz `vllm serve` gerekiyor).
- Ollama CLI, SSH proxy üzerinden pipe'lanan komutlarda (`ollama list`/`rm`/`pull` non-
  interaktif) bir terminal arkaplan-rengi sorgusu (`ESC]11;?`) gönderip yanıt gelmediği için
  asılı kalıyor — **HTTP API'yi kullan** (`/api/tags`, `/api/delete`, `/v1/chat/completions`),
  CLI'ı script içinde değil.
- `bitig/`+`harness/model.py` sıfır bağımlılık olduğu için pod'da **venv bile gerekmiyor**,
  sistem Python'uyla doğrudan çalışıyor — venv yalnızca vLLM/bitsandbytes gibi gerçek paket
  gerektiren işler için kuruldu.

**Model karşılaştırması (aynı 22 soruluk Sözcükte Yapı kümesi, `harness/qwen_ham_diagnostik.py`,
sıcaklık 0.0):**

| Model | Sunucu | Sonuç (8 soruluk alt küme, aksi belirtilmedikçe) |
|---|---|---|
| Gemma3-12B-it | vLLM (bitsandbytes) | 3/8 doğru, 0 format hatası, Çince yok |
| Qwen3:8B | Ollama | 2/8 doğru, 1 format hatası, Çince yok |
| Qwen3.6:27B (varsayılan ayar) | Ollama | 5/8 doğru, 2 format hatası, Çince yok |
| **Qwen3.6:27B (mitigasyonlu, tam 22 soru)** | Ollama | **12 doğru, 6 yanlış, 4 format hatası** |

Qwen3.6:27B üç modelin en güçlüsü çıktı. 8'lik örneklemler istatistiksel olarak zayıf (1-2
soruluk farklar anlamlı değil) — tek güvenilir karşılaştırma tam 22 soruluk son satır.

**"Format hatası"nın kök nedeni bulundu — döngü değil, bütçe paylaşımı.** İlk yorum ("model
sonsuz döngüye giriyor", Gemma4'teki bilinen hatayla ~[[glm-testinden-cikan-bulgu]] aynı
kategori sanıldı) **yanlış çıktı**. Gerçek neden: Ollama'nın hem OpenAI-uyumlu ucunda
(`reasoning` alanı) hem native `/api/chat` ucunda (`thinking` alanı) model önce uzun bir
"thinking" bloğu üretiyor, SONRA `content`i yazıyor — ama `num_predict`/`azami_belirtec`
**ikisinin toplamını** sınırlıyor. Minimal tekrar üretimle doğrulandı: `num_predict=50` ile
basit bir soruda bile `done_reason="length"`, `eval_count=50`, `content=""`, `thinking`
kesilmiş — yani düşünme bittiğinde zaten bütçe tükenmiş oluyor, cevaba hiç sıra gelmiyor. Zor
sorularda tek başına düşünme 80.000+ karaktere (Türkçe'nin tokenizer verimsizliği yüzünden
tahmin edilenden fazla token) çıkabiliyor.

**Düzeltme kısmen işe yaradı, tam çözmedi.** Token bütçesini 4000→12000 çıkarmak +
`frequency_penalty=0.3` + `reasoning_effort=low` (OpenAI-uyumlu uçtan) 22 sorunun 18'ini
(4 hariç) düzeltti/etkiledi — önceden başarısız olan `Q10-2004`/`Q13-2010` tam bu ayarlarla
tekrar denenince DOĞRU çıktı (izole testte, canlı modda doğrulandı). Ama **4 soru
(`Q6-1999`, `Q11-2009`, `Q14-2011`, `Q27-2019`) hiçbir kombinasyonla çözülemedi** — sırayla
denendi: native `repeat_penalty=1.3`/`repeat_last_n=256` (`/api/chat`'ten, OpenAI-uyumlu
`frequency_penalty`'den farklı, gerçek llama.cpp mekanizması) → 4/4 hâlâ format hatası;
`think=false` (düşünmeyi tamamen kapat) → 2 format hatası + 2 yanlış (düşünmeden de
tıkanabiliyor, sorun yalnızca "düşünme uzunluğu" değil); `num_predict=24000` (bütçeyi 2 katına
çıkar) → yine 4/4 format hatası, hiç iyileşme yok. **Sonuç:** bu 4 soru modelin gerçek bir
sınırı, parametre ayarıyla düzeltilecek bir yapılandırma hatası değil.

**Sözlükleşme genelleme testi (`harness/sozluklesme_genelleme.py`) — model motorun bilinen
açığını ne kadar telafi edebiliyor?** Q3-1997 çözülürken model, motorun `korku`yu çıplak isim
kökü göstermesine rağmen kendi bilgisinden bunun tarihsel olarak `kork+u+lu` (fiil kökenli)
olduğunu fark edip doğru cevabı (C) verdi — CLAUDE.md §5'in belgelediği sözlükleşme duvarını
model kendi muhakemesiyle aştı. Bunun saf ezber mi (yalnızca ünlü "korku" örneği) yoksa gerçek
bir genelleme mi olduğunu ölçmek için §5'te belgelenmiş 12 kelime (9'u gizli-fiil-kökenli:
kazı/buluntu/aşama/ekin/çeviri/ışık/yatak/yorgun/sevinç, 3'ü kontrol/gerçek-basit-kök:
av/masa/kalem) bağlamsız, tek tek soruldu. **Sonuç: 11/12 doğru (gizli-fiil grubunda 8/9,
kontrol grubunda 3/3).** Tek hata — ironik biçimde — `kazı`nın kendisi (aynı cümledeki
`buluntu`/`aşama`yı doğru bildi ama `kazı`yı yanlış isim sandı). **Yorum:** saf ezber değil
(9 kelimenin çoğu "korku" kadar ünlü değil, gerçek genelleme var), ama %89 bile projenin
%100 eşiğinin altında ve hata tam da en kritik örnekte — model **aday/damıtma kaynağı**
olarak kullanılabilir (§13'ün zaten öngördüğü rol), doğrudan cevap anahtarı olarak değil.

**Genel sonuç:** Qwen3.6:27B şu ana kadar test edilen en güçlü aday (Gemma3-12B ve Qwen3:8B'den
belirgin şekilde önde), ama üretim için hâlâ güvenilmez (%67 doğru, kalıcı format-hatası
sınıfı var). vLLM+Gemma3 tool-calling tarifi artık kanıtlanmış ve tekrar kullanılabilir.
Kalıcı dosyalar (deneysel, ağ+ücretli): `harness/qwen_ham_diagnostik.py` (env değişkeni
tabanlı, `ZAI_BASE_URL`'i herhangi bir OpenAI-uyumlu uca yönlendirir),
`harness/sozluklesme_genelleme.py`, `harness/repeat_penalty_dene.py` (Ollama native
`/api/chat`, `think`/`repeat_penalty` deneyi için).
