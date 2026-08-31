"""DENEYSEL: GLM-5.2'ye motor + MEBİ konu özeti araçları verip gerçek ÖSYM
Sözcükte Yapı sorularını UÇTAN UCA çözdürme testi.

**Bu bir üretim mekanizması DEĞİL.** `harness/sozcukte_coz.py`'nin aksine burada
motor bir aday üretici/hakem olarak değil, modelin ÇAĞIRABİLECEĞİ bir araç olarak
duruyor — nihai cevabı model veriyor. CLAUDE.md §1 ilke 5'in ("çekirdek mantık
LLM'e bırakılmaz") dışında, bilinçli bir istisna: buradaki amaç bir soruyu
"çözmek" değil, motor+RAG ile desteklenmiş bir modelin `sozcukte_coz.py`'nin
mekanize edemediği (kategori seçenekli, sözlükleşme gerektiren) soru tiplerinde
ne kadar ileri gidebildiğini ÖLÇMEK. Sonuç asla bir altın kümeye, motora ya da
üretim hattına geri beslenmez — yalnızca rapor edilir.

Araçlar:
  konu_getir(konu_adi)   → `veri/mebi_konu_ozetleri.json`'dan konu metni
  kelimeyi_coz(kelime)   → `bitig.cozumleyici.kelimeyi_cozumle` çıktısı

Test kümesi: `klasikhoca.com`'un 29 gerçek TYT/ÖSYM Sözcükte Yapı sorusundan
(1994-2020) `harness/sozcukte_coz.py`nin ÇÖZEMEDİĞİ 22'si — bkz. docs/decisions.md §5.
Sorular tam metin (paragraf/dize + soru kökü + seçenekler) olarak, kopyala-
yapıştır biçiminde modele veriliyor; motor/RAG çağırma kararı tamamen modele ait.

Ağ gerektirir, ücretlidir. Normal `pytest`e dahil değildir, elle çalıştırılır.

Çalıştırma:  .venv/bin/python -m harness.mebi_agent_coz
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bitig.cozumleyici import kelimeyi_cozumle
from harness import model

MEBI_YOLU = Path(__file__).resolve().parent.parent / "veri" / "mebi_konu_ozetleri.json"

_CEVAP_DUZENI = re.compile(r"NİHAİ CEVAP\s*[:：]\s*([A-EIVX]+)", re.IGNORECASE)

SISTEM_ISTEMI = """Sen bir TYT Türkçe sınav sorusu çözücüsüsün. Sana tam bir soru \
(gerekirse paragraf/dizeler + soru kökü + seçenekler) verilecek.

Elindeki iki araç:
1. kelimeyi_coz: bir kelimenin GERÇEK morfolojik ayrıştırmasını verir (motor çıktısı, \
kesindir — kendi tahminini bunun üstüne koyma, motor ne diyorsa odur; birden fazla \
okuma dönebilir, hepsini dikkate al).
2. konu_getir: MEB'in resmî konu özeti kitabından bir konunun kural/tanım/örnek metnini \
verir (örn. "Ses Bilgisi 2", "Fiilimsiler", "Cümlenin Ögeleri", "Zamir").

Kurallar:
- Sorudaki altı çizili/numaralanmış her kelimeyi kelimeyi_coz ile kontrol et, tahmin etme.
- Kuraldan emin değilsen konu_getir ile ilgili konuyu oku.
- Araç çağırma bütçen sınırlı (en fazla ~12 çağrı). Her seçenek için tek tek kelimeyi_coz \
çağırman genelde yeterli — konu_getir'i yalnızca gerçekten kuraldan emin olamadığında kullan.
- Sorunun cevap biçimine dikkat et, İKİ farklı biçim olabilir:
  1) Soru A) B) C) D) E) şeklinde beş seçenek veriyorsa, cevabı bir HARF olarak ver.
  2) Soru yalnızca metin içinde (I) (II) (III) (IV) (V) ile numaralanmış cümle/sözcükler \
sunuyorsa ve ayrı bir A-E seçenek listesi YOKSA, cevabı doğrudan o ROMA RAKAMI olarak ver \
(harfe çevirme — "V" cevabıysa "V" yaz, "E" yazma).
- Son cevabını YALNIZCA şu formatta, başka hiçbir şey eklemeden ver:
NİHAİ CEVAP: <A/B/C/D/E ya da I/II/III/IV/V>"""

# klasikhoca.com'un 29 gerçek TYT/ÖSYM Sözcükte Yapı sorusundan (1994-2020),
# harness.sozcukte_coz'un ÇÖZEMEDİĞİ 22'si. Kaynak metinler bu oturumda PDF'ten
# dikkatle (paragraf/soru numarası sırası iki kez kontrol edilerek) çıkarıldı.
SORULAR: list[dict] = [
    {
        "kimlik": "Q1-1994", "cevap": "E",
        "metin": """Aşağıdaki cümlelerin hangisindeki altı çizili sözcük ek alırken bu sözcüğün ünsüzlerinden biri düşmüştür?
A) Susuzluktan balkondaki tüm çiçekler sararmış.
B) Yazar, bu romanında çok fazla devrik cümle kullanmış.
C) Soğuktan burnu kıpkırmızı olmuş.
D) Bu konuda senin de fikrini almak istiyorum.
E) Otobüsümüz, adını bilmediğim büyücek bir kasabadan geçti.""",
    },
    {
        "kimlik": "Q2-1995", "cevap": "E",
        "metin": """Aşağıdaki cümlelerin hangisinde altı çizili sözcük hem yapım hem çekim eki almıştır?
A) Aralarında sıkı bir dostluk vardı.
B) Dalgalı denizde yüzmek tehlikelidir.
C) Kapıda bir yabancı var.
D) Dün sokaklar çok kalabalıkmış.
E) İnatçılar çevrelerinde pek sevilmezler.""",
    },
    {
        "kimlik": "Q3-1997", "cevap": "C",
        "metin": """(I) Çağdaş sinemanın (II) ünlü örneklerinden birini dün gece televizyonda izlerken (III) korkulu (IV) dakikalar (V) yaşadım.
Bu cümledeki numaralanmış sözcüklerin hangisinde birden çok yapım eki vardır?
A) I  B) II  C) III  D) IV  E) V""",
    },
    {
        "kimlik": "Q5-1999", "cevap": "C",
        "metin": """Çayönü (I) kazısında çıkarılan (II) buluntular insanlığın, (III) avcılık ve toplayıcılıktan yerleşik yaşama (IV) geçiş (V) aşamasını göstermektedir.
Bu cümledeki altı çizili sözcüklerden hangisinin kökü, sözcük türü yönünden öbürlerinden farklıdır?
A) I  B) II  C) III  D) IV  E) V""",
    },
    {
        "kimlik": "Q6-1999", "cevap": "E",
        "metin": """Aşağıdaki dizelerde altı çizili sözcüklerin hangisinde, birden çok yapım eki kullanılmıştır?
A) Kara gözlüm çok özledim ben seni
B) Varlığımı yalnız ona verdim ben
C) Hava keskin bir kömür kokusuyla dolar
D) Gözleri yaş dolu yorgun bulutlar
E) Bir med zamanı gökyüzü kurşunla örtülü""",
    },
    {
        "kimlik": "Q10-2004", "cevap": "D",
        "metin": """Aşağıdaki cümlelerin hangisinde bir sözcük, ilgi adılından (ilgi zamirinden) sonra yaklaşma durumu eki almıştır?
A) Masadakilerden yalnızca birini al.
B) Bugünkünü ötekilerden daha çok beğendim.
C) Benimkinin sayfalarında renkli resimler var.
D) Bu da her yönüyle seninkine benziyor.
E) Bizimkinde hiçbir eksiklik yok.""",
    },
    {
        "kimlik": "Q11-2009", "cevap": "B",
        "metin": """Salvador Dali'nin bütün resimlerinin yer aldığı sergide, İspanyol ustanın sanat tarihine bıraktığı eşsiz mirası yansıtan iki yüz yetmiş yapıt sanatseverlere tanıtıldı.
Bu cümleyle ilgili olarak aşağıda verilenlerden hangisi yanlıştır?
A) Birden fazla sıfat tamlaması vardır.
B) Yönelme durumu eki alan sözcükler zarf tümleci görevindedir.
C) Sayı sıfatı kullanılmıştır.
D) Yapım eki almış birden fazla sözcük vardır.
E) Bileşik sözcük kullanılmıştır.""",
    },
    {
        "kimlik": "Q13-2010", "cevap": "E",
        "metin": """Mimarinin, inancın ve çok kültürlülüğün şehri Mardin, şimdilerde güncel sanatın doğudaki merkezi olmaya hazırlanıyor.
Bu cümlede aşağıda verilenlerden hangisi yoktur?
A) Ünlü düşmesi
B) Zaman zarfı
C) Sıfatlaştıran -ki
D) Türemiş sözcükler
E) Dönüşlülük zamiri""",
    },
    {
        "kimlik": "Q14-2011", "cevap": "A",
        "metin": """Hiçbir söz, hiçbir varsayım, hiçbir kuram yaşanan somut gerçeklerin yerini tutamaz; bin kez söylenen yağmur sözcüğünün bir damla yağmurun yerini tutamayacağı gibi.
Bu cümlede aşağıda verilenlerden hangisi yoktur?
A) Ek fiil almış sözcük
B) Benzetme edatı
C) Sayı sıfatı
D) Birleşik sözcük
E) Yeterlik fiili""",
    },
    {
        "kimlik": "Q15-2012", "cevap": "E",
        "metin": """İletişim konusunda çağımızda teknolojinin (I) bize sunduğu olanaklardan olabildiğince yararlanmaya çalışırken öte yandan en yakınımızdaki kişilerin seslerini duymakta, dillerini anlamakta (II) zorlanıyoruz. Giderek daha az göz göze geliyoruz. (III) Sevgimizi daha az dile getiriyoruz. Büyük kalabalıklar (IV) içinde yaşayan (V) "yalnız"ların sayısı günden güne artıyor böylece.
Bu parçadaki altı çizili sözcüklerle ilgili olarak aşağıda verilenlerden hangisi yanlıştır?
A) I. sözcük, yönelme durumu eki almış bir zamirdir.
B) II. sözcük, dönüşlülük eki almıştır.
C) III. sözcük, hem yapım eki hem çekim eki almıştır ve cümlede belirtili nesne görevinde kullanılmıştır.
D) IV. sözcük, ad soyludur ve bulunma durumu eki almıştır.
E) V. sözcük, belgisiz sıfattır.""",
    },
    {
        "kimlik": "Q16-2013", "cevap": "E",
        "metin": """Eserlerinde kullandığı özgün biçimler ve canlı renklerle, değişimin birey üzerindeki etkilerini yansıtıyor.
Bu cümleyle ilgili olarak aşağıdakilerden hangisi yanlıştır?
A) Çatısı bakımından etkendir.
B) Nesne, isim tamlamasından oluşmaktadır.
C) Fiilden isim yapma eki almış sözcük vardır.
D) Bulunma durumu eki almış sözcük vardır.
E) İyelik eki alan sözcük yoktur.""",
    },
    {
        "kimlik": "Q17-2013", "cevap": "D",
        "metin": """Aşağıdaki cümlelerin hangisinde "-ıntı,-untu/-üntü" ekinin kullanıldığı sözcük, kökü bakımından diğerlerinden farklıdır?
A) Bu bölgede yapılan kazılarda arkeologlar, eski uygarlıklara ait yeni buluntulara rastladılar.
B) Kişi yersiz kuruntularından kurtulmak için dostlarına, arkadaşlarına daha fazla güvenmeli ve inanmalıdır.
C) İçi süprüntü dolu küreği merdivenlerin dibindeki çöp kutusuna boşaltmak için dışarı çıktı.
D) Kelimeyle kavram, dille düşünce arasındaki bağıntı üstüne yapılan tartışmalar eski çağlara kadar dek gider.
E) Bozuntuya vermeden yanına gittim ve olanları bütün çıplaklığıyla kendisine anlattım.""",
    },
    {
        "kimlik": "Q18-2013", "cevap": "E",
        "metin": """Bugüne (I) kadar eserleri 42 dile çevrilen, Japonya'nın (II) en büyük yazarlarından biri olarak anılan ve yaşayan en büyük 100 yazar arasında (III) gösterilen Murakami; 1991 yılında ABD'yi (IV) ziyaret edip burada ilk imza gününü (V) gerçekleştirdiğinde kitap imzalatmaya sadece 15 kişi gelmişti.
Bu cümledeki numaralanmış sözlerle ilgili olarak aşağıda verilenlerden hangisi yanlıştır?
A) I. sözcük, edattır.
B) II. sözcük, üstünlük bildiren zarftır.
C) III. sözcük, sıfat-fiil eki almıştır.
D) IV. sözcük, birleşik sözcüktür.
E) V. sözcük, fiil soyludur.""",
    },
    {
        "kimlik": "Q20-2014", "cevap": "C",
        "metin": """Duvara mumya gibi vuran gölgeni ara
İnce çıtırtılarla odanda yansın ocak
Hayalinin gölgünde belirsiz bir hatıra
Bir yaban kuşu gibi süzülüp kaybolacak
Bu dizelerle ilgili olarak aşağıda verilenlerden hangisi yanlıştır?
A) Yansıma sözcükten -tı ekiyle türemiş isim vardır.
B) Sıfat-fiil ekiyle türemiş sözcük, ismi nitelemiştir.
C) Belirtili isim tamlamasının başına sayı sıfatı gelmiştir.
D) Zarf-fiil ekiyle türemiş sözcük, fiili nitelemiştir.
E) Emir II. tekil kişi olarak çekimlenmiş fiil vardır.""",
    },
    {
        "kimlik": "Q21-2014", "cevap": "B",
        "metin": """İspanyol edebiyatının altın kalemi Cervantes, Don Kişot adlı ölümsüz eserinde, onuru için savaşan ve ölen, parası ölçüsünde değil, ahlaki erdemleri ölçüsünde saygı gören insan tipini ortaya koyarken aynı zamanda karmaşık bir çağı da özetliyordu.
Bu cümlede aşağıdakilerden hangisi yoktur?
A) İsim tamlaması
B) Sayı sıfatı
C) III. tekil iyelik ekiyle çekimlenmiş sözcük
D) Birden fazla yapım eki almış sözcük
E) Ünlü uyumuna uymayan ek""",
    },
    {
        "kimlik": "Q22-2015", "cevap": "C",
        "metin": """Altmış bin yıl önce Afrika'dan yola çıkan insanlar, durmadan ilerleyerek dünyanın dört bir yanına (I) yerleşmişlerdi. Bu (II) ilerleyişleri ve gittikleri mesafe; iklime, nüfus (III) baskılarına, tekne ve diğer teknolojik icatlara bağlıydı. (IV) Yolculuklarını (V) hızlandıran etkenler arasında elle tutulamayanlar da vardı: hayal gücü, adaptasyon ve bir sonraki tepenin ardında ne olduğuna dair merak.
Bu parçadaki numaralanmış sözcüklerden hangisinin kökü ötekilerden farklıdır?
A) I  B) II  C) III  D) IV  E) V""",
    },
    {
        "kimlik": "Q23-2017", "cevap": "B",
        "metin": """Edebiyat-estetik (I) bağlantısı üzerinde duran Tanpınar, gençlik (II) yıllarından hayatının (III) sonuna kadar denilebilir ki yalnız güzel eserleri (IV) önemsemiş, (V) onlardan daha üstün bir değerin varlığını tanımamıştır.
Bu parçadaki numaralanmış sözcüklerden hangileri hem yapım hem de çekim eki almıştır?
A) I ve II  B) I ve IV  C) II ve IV  D) III ve V  E) IV ve V""",
    },
    {
        "kimlik": "Q24-2017", "cevap": "D",
        "metin": """Hayatta çalışmaktan hiç korkmadım ama yaşlanmak zor iş. Her gün yeniden kurulan dünyaya biraz daha eskimiş olarak uyanıveriyor kendi içinde insan.
Bu parçayla ilgili olarak aşağıdakilerden hangisi söylenemez?
A) İsim ve fiil cümleleri vardır.
B) Tezlik fiili kullanılmıştır.
C) İsimden fiil yapan ek vardır.
D) Geçişli yüklem vardır.
E) Dönüşlülük zamiri kullanılmıştır.""",
    },
    {
        "kimlik": "Q25-2018", "cevap": "D",
        "metin": """Gelecekteki bilişsel sistemlerin çevreyle (I) etkileşim hâlinde olması bekleniyor. Canlı organizmaların sinir sistemlerinden (II) esinlenerek geliştirilen bu mekanizmaların en önemli özelliği, klasik (III) işlemcilerin aksine hafıza ve işlemci birimlerinin bir arada olmasıdır. İnsan beynine benzer (IV) biçimde çalışan elektronik cihazlar henüz tasarlanmamış olsa da yakın zamanda bu konuda önemli gelişmeler (V) yaşanması bekleniyor.
Bu parçada numaralanmış sözcüklerden hangileri isim kökünden türemiştir?
A) I ve II  B) I ve III  C) II ve IV  D) III ve V  E) IV ve V""",
    },
    {
        "kimlik": "Q27-2019", "cevap": "E",
        "metin": """Dede Korkut (I) anlatılarının üçüncü hikâyesi olan Bey Böyrek, neredeyse tüm Türk (II) halklarının sözlü edebiyatında yer almaktadır. Bu anlatı, Oğuz (III) boylarının arasında Bamsı Beyrek, Altay Türklerinde ise Alıp Manaş, Başkurt ve Tatarlarda Alıpmenşen olarak bilinir. Bu destanın birbirine yakın (IV) biçimlerinin bu kadar geniş bir coğrafyada yaşaması, bu toplulukların ortak bir düşünce tarihine (V) sahip olduklarının güzel bir göstergesidir.
Bu parçada numaralanmış sözcüklerin hangisi "üçüncü çoğul kişi iyelik eki" almıştır?
A)I  B) II  C) III  D) IV  E) V""",
    },
    {
        "kimlik": "Q28-2019", "cevap": "B",
        "metin": """Oyuncular, herhangi bir rolü canlandırdığında izleyicilerinden (I) gözleri önüne serilen (II) sahneleri ciddiye almalarını beklerler. Kendilerinden, (III) izledikleri karakterlerin sahipmiş gibi görünen niteliklere gerçekten sahip (IV) olduklarına, yapmakta oldukları işin yol açacağı sonuçların gerçekleşeceğine ve genelde her şeyin göründüğü gibi olduğuna (V) inanmaları istenir.
Bu parçada numaralanmış sözcüklerin hangisi, "belirtme durumu eki" almıştır?
A)I  B) II  C) III  D) IV  E) V""",
    },
    {
        "kimlik": "Q29-2020", "cevap": "A",
        "metin": """Her sene, (I) zamanı gelince İstanbul'un mahallelerinden Boğaz'ın (II) köylerine göçler başlardı. Eski İstanbullular; Boğaziçi'nin kenarlarına (III) yapılmış ve eski erkân sedirleriyle, kerevet, şilte ve halılar üstünde yer (IV) minderleri gibi eski eşyalarla döşenmiş geniş odalı, gönül ferahlatıcı yalılara (V) taşınırlardı.
Bu parçada altı çizili sözcüklerle ilgili aşağıda verilenlerden hangisi yanlıştır?
A) I. sözcük belirtme durumu eki almıştır.
B) II. sözcük iyelik eki almıştır.
C) III. sözcük sıfat-fiil eki almıştır.
D) IV. sözcük çokluk eki almıştır.
E) V. sözcük geniş zaman eki almıştır.""",
    },
]

ARACLAR = [
    {
        "type": "function",
        "function": {
            "name": "kelimeyi_coz",
            "description": (
                "BitigAI'nin morfolojik çözümleme motoruna bir Türkçe kelime sorar. "
                "Kelimenin olası TÜM kök+ek ayrıştırmalarını (okuma), her okumanın kök "
                "türünü (Noun/Verb/Adj/Adv/Pron/Num), aldığı eklerin kimliklerini "
                "(EK.HAL.BEL=belirtme hâli, EK.IYELIK.3T=3.tekil iyelik, EK.YAPIM.LI=yapım "
                "eki -lI, EK.SIFATFIIL.AN=sıfat-fiil -An gibi) ve tetiklenen ses olaylarını "
                "döner. Bu motorun çıktısı kesindir, kelimenin gerçek morfolojik yapısını "
                "yansıtır."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "kelime": {
                        "type": "string",
                        "description": "Çözümlenecek tek bir Türkçe kelime.",
                    }
                },
                "required": ["kelime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "konu_getir",
            "description": (
                "MEB'in resmî 'MEBİ TYT Konu Özetleri - Türkçe' kitabından bir konunun tam "
                "metnini (kural, tanım, tablo, örnek) döner. Konu adları: Ses Bilgisi 1, "
                "Ses Bilgisi 2, Yazım Kuralları 1/2/3, Noktalama İşaretleri 1/2/3, Biçim "
                "Bilgisi 1, Biçim Bilgisi 2 (Sözcüğün Yapısı), İsim, Sıfat, Zamir, İsim ve "
                "Sıfat Tamlamaları, Zarf, Edat/Bağlaç/Ünlem, Fiilde Kip, Ek-Fiil, Fiilde "
                "Yapı, Fiilimsiler, Fiilde Çatı, Cümlenin Ögeleri, Cümle Türleri."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "konu_adi": {
                        "type": "string",
                        "description": "Yukarıdaki listeden bir konu adı (birebir ya da yakın eşleşme).",
                    }
                },
                "required": ["konu_adi"],
            },
        },
    },
]


def _mebi_konulari() -> dict:
    return json.loads(MEBI_YOLU.read_text(encoding="utf-8"))["konular"]


def _konu_metni(konu_adi: str) -> str:
    konular = _mebi_konulari()
    if konu_adi in konular:
        return konular[konu_adi]["metin"]
    aranan = konu_adi.strip().lower()
    for ad, veri in konular.items():
        if aranan in ad.lower() or ad.lower() in aranan:
            return veri["metin"]
    return "Konu bulunamadı. Geçerli konu adları: " + ", ".join(konular)


def _kelime_ozet(kelime: str) -> str:
    sonuc = kelimeyi_cozumle(kelime.strip())
    if sonuc.cozumlenemedi:
        return f"'{kelime}' motorla çözülemedi (sözlükte kök bulunamadı ya da geçersiz ek zinciri)."
    satirlar = [f"'{kelime}' için {len(sonuc.okumalar)} okuma:"]
    for i, ok in enumerate(sonuc.okumalar):
        ekler = ", ".join(ok.ek_kimlikleri) or "(ek yok, çıplak kök)"
        satirlar.append(f"  okuma {i + 1}: kök={ok.kok!r} tür={ok.tur} ekler=[{ekler}]")
    return "\n".join(satirlar)


def _arac_calistir(ad: str, argumanlar: dict) -> str:
    if ad == "kelimeyi_coz":
        return _kelime_ozet(argumanlar.get("kelime", ""))
    if ad == "konu_getir":
        return _konu_metni(argumanlar.get("konu_adi", ""))
    return f"bilinmeyen araç: {ad}"


def coz(soru: dict) -> tuple[str | None, list[dict]]:
    # GLM bazen bir turda ne araç çağrısı ne de biçime uygun içerik döndürüyor
    # (boş yanıt ya da format dışı metin, gözlemlendi) — birkaç tekrar bu tür
    # aksaklıkları eler.
    for deneme in range(3):
        yanit, gecmis = model.arac_ile_sor(
            istem=soru["metin"],
            araclar=ARACLAR,
            arac_calistir=_arac_calistir,
            sistem=SISTEM_ISTEMI,
            sicaklik=0.0,
            azami_belirtec=20000,
            azami_tur=18,
        )
        eslesme = _CEVAP_DUZENI.search(yanit)
        if eslesme:
            return eslesme.group(1).upper(), gecmis
        if deneme < 2:
            continue  # biçime uygun cevap yok, bir kez daha dene
    return None, gecmis


ILERLEME_YOLU = Path(
    "/tmp/claude-1000/-home-emir-Belgeler-Yazilim-BitigAI/"
    "6194d298-ca12-44ae-aeb9-7bca05e10b6b/scratchpad/mebi_agent_ilerleme.jsonl"
)


def main() -> int:
    if not model.anahtar_var_mi():
        print(model.anahtar_yardimi(), file=sys.stderr)
        return 2
    if not MEBI_YOLU.exists():
        print(f"MEBİ veri dosyası yok: {MEBI_YOLU} — önce harness.mebi_pdf_ayikla çalıştır", file=sys.stderr)
        return 2

    dogru = yanlis = bos = 0
    print(f"\n{len(SORULAR)} soru (klasikhoca — sozcukte_coz'un çözemedikleri)\n", flush=True)
    print(f"{'kimlik':<12} {'bek':>3} {'bul':<4} {'arac_cagrisi':>4} durum", flush=True)
    print("─" * 50, flush=True)

    ILERLEME_YOLU.parent.mkdir(parents=True, exist_ok=True)
    with ILERLEME_YOLU.open("w", encoding="utf-8") as ilerleme:
        for soru in SORULAR:
            try:
                bulunan, gecmis = coz(soru)
            except model.ModelHatasi as hata:
                print(f"{soru['kimlik']:<12} HATA: {hata}", flush=True)
                ilerleme.write(
                    json.dumps({"kimlik": soru["kimlik"], "hata": str(hata)}, ensure_ascii=False) + "\n"
                )
                ilerleme.flush()
                continue

            arac_sayisi = sum(1 for m in gecmis if m.get("role") == "tool")
            if bulunan is None:
                bos += 1
                durum = "∅ FORMAT"
            elif bulunan == soru["cevap"]:
                dogru += 1
                durum = "✓ DOGRU"
            else:
                yanlis += 1
                durum = "✗ YANLIS"

            print(
                f"{soru['kimlik']:<12} {soru['cevap']:>3} {bulunan or '?':<4} "
                f"{arac_sayisi:>4}   {durum}",
                flush=True,
            )

            arac_dokumu = [
                {
                    "arac": c["function"]["name"],
                    "girdi": c["function"]["arguments"],
                }
                for m in gecmis
                if m.get("role") == "assistant" and m.get("tool_calls")
                for c in m["tool_calls"]
            ]
            ilerleme.write(
                json.dumps(
                    {
                        "kimlik": soru["kimlik"],
                        "beklenen": soru["cevap"],
                        "bulunan": bulunan,
                        "durum": durum,
                        "arac_cagri_sayisi": arac_sayisi,
                        "arac_dokumu": arac_dokumu,
                        "son_mesaj": gecmis[-1].get("content", ""),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            ilerleme.flush()

    toplam = len(SORULAR)
    print("─" * 50, flush=True)
    print(f"  doğru {dogru}  ·  yanlış {yanlis}  ·  format hatası {bos}  (toplam {toplam})", flush=True)
    if toplam:
        print(f"\n  soru başarımı: {dogru / toplam * 100:.1f}%", flush=True)
    print(
        "\n  NOT: bu sonuç deneyseldir, hiçbir altın kümeye/motora geri beslenmez "
        "(bkz. modül docstring'i)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
