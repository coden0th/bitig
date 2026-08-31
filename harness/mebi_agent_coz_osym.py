"""DENEYSEL: `mebi_agent_coz.py`nin aynı aracı (motor + MEBİ RAG) ile, kullanıcının
`osym-tyt-turkce-sorular.txt` ve `osym-cikmis-sorular.txt` dosyalarındaki gerçek
ÖSYM sorularını çözme testi.

Aynı ilkeler geçerli (bkz. `mebi_agent_coz.py` modül docstring'i): bu bir üretim
mekanizması değil, sonuç hiçbir yere geri beslenmez.

Sorular bu iki dosyadan ELLE (regex değil, çünkü format çok düzensiz — bazı
sorularda seçenek harfi eksik, bazılarında OCR bozukluğu var) çıkarıldı, "Cevap:"
ve "Çözüm:" satırları ATLANARAK — modele asla doğru cevap sızdırılmıyor. Üç soru
(seçenek listesi hiç verilmemiş olanlar) bu yüzden dışarıda bırakıldı, aşağıda
her biri gerekçesiyle not edildi.

Cevap biçimi burada iki türlü olabilir: `A-E` seçenek harfi ya da `I-V` roma
rakamı (numaralanmış cümle/sözcük sorularında seçenekler zaten roma rakamlarının
kendisidir) — `mebi_agent_coz.coz` (ve onun sistem istemi/regex'i) ikisini de
kabul edecek şekilde güncellendi, burada tekrar tanımlanmıyor.

Çalıştırma:  .venv/bin/python -m harness.mebi_agent_coz_osym
"""

from __future__ import annotations

import sys
from pathlib import Path

from harness import model
from harness.mebi_agent_coz import coz

# Kaynak: osym-tyt-turkce-sorular.txt, osym-cikmis-sorular.txt (repo kökü,
# kullanıcı tarafından derlenmiş gerçek ÖSYM/YKS/EBA soruları). "Cevap:"/"Çözüm:"
# satırları çıkarıldı. Üç soru (seçenek listesi verilmemiş) atlandı:
#   - "sözcüklerin türü ... sırasıyla verilmiştir?" (Tanpınar parçası) — A-E listesi
#     transkripsiyonda hiç yok, yalnızca doğru sıra yazılmış.
#   - "İşte ben hep böyle garip mahzun..." dizeleri — seçenek listesi yok.
#   - (ilk iki soruyla aynı worksheet'in bir tekrarı, "Yurt/Süt/Renk/Kurt/Tat" —
#     dosyada iki kez birebir geçiyor, ikincisi atlandı, gereksiz tekrar.)
SORULAR: list[dict] = [
    {
        "kimlik": "OSYM-01", "cevap": "II",
        "metin": """Mektup, gerek bizim edebiyatımızın gerek dünya edebiyatının önemli bir edebî türü(I). En azından insanlığın interneti(II) ve buna bağlı olarak elektronik postayı icat etmesine kadar öyleydi. Artık ne posta güvercinleri(III) ne de şarkılara konu olmuş postacılar kaldı. O renk renk hatta kokulu mektup kâğıtları(IV) ve zarflar da nadir rastlanan nostaljik aksesuarlardan biri(V) hâlini aldı.
Bu parçada numaralanmış sözcüklerden hangisi iyelik eki almamıştır?""",
    },
    {
        "kimlik": "OSYM-02", "cevap": "V",
        "metin": """(I) Çağımızda tahammülsüz ve sabırsız olmaya yönlendirilen kitlelerin her alanı kuşatan hızlı tüketim anlayışı, kitaplara da bir raf ömrü biçti. (II) Hayatımıza "kitap piyasası", "kitap pazarı" gibi kavramlar girmeye; kitaplar herhangi bir market ürünü gibi reklam edilmeye başladı. (III) Satış yarışı içine sokulan kitaplar hızlı tüketim malzemeleriyle aynı mekânlarda görülür oldu. (IV) Raf ömürlerinin satış rakamlarına göre belirlendiği bu düzende satışı düşük olan kitapların ömrü, günlerle hatta saatlerle sınırlandı. (V) Öyle ki az satan bir eseri kitapçılarda bulmak doğal olarak imkânsız hâle geldi.
Bu parçada numaralanmış cümlelerin hangisinde isim-fiil, sıfat-fiil ve zarf-fiil bulunmaktadır?""",
    },
    {
        "kimlik": "OSYM-03", "cevap": "II",
        "metin": """(I) Ünlü seyyah ve tarihçi İbn Battuta, bir grup insanla birlikte 28 yıl sürecek bir seyahate çıkar. (II) Yolculuk süreci tamamlandığında tecrübe ve izlenimlerinin büyük bir bölümünü kitaplaştırır. (III) Seyahatname türünün ilk örnekleri arasında sayılan bu eser, kaynaklarda Er-Rıhle olarak da geçer. (IV) Kitap, XIV. yüzyıl İslam dünyasının sosyokültürel ve siyasi tarihi için paha biçilmez bir belgedir. (V) İbn Battuta'nın tespitleri, zamanının tarih yazımına göre alışılmadık tarzda, insan odaklı bir yaklaşımla ortaya konulmuştur.
Bu parçada numaralanmış cümlelerin hangisinde sıfat-fiil yoktur?""",
    },
    {
        "kimlik": "OSYM-04", "cevap": "A",
        "metin": """Bir şair, başkalarının şiirlerinde geçen sözcükleri(I) kullanabilir. O şiirlerin konularını, izleklerini(II) yeniden işleyebilir. Bu, metinler arası ilişkilerin(III) ve sanattaki evrensel bakışın doğal bir sonucudur. Ama bu özellik, onu "taklitçi" yahut "değersiz" saymayı gerektirmez(IV). Yeter ki o, bu kullanış ve işleyişte başkalarından ayrılsın(V).
Bu parçadaki altı çizili sözcüklerle ilgili aşağıdakilerden hangisi söylenemez?
A) I. sözcük, üçüncü çoğul kişi iyelik eki almıştır.
B) II. sözcük, belirtme durumu eki almıştır.
C) III. sözcük, tamlayan eki almıştır.
D) IV. sözcük, olumsuz geniş zaman eki almıştır.
E) V. sözcük, üçüncü tekil kişi emir eki almıştır""",
    },
    {
        "kimlik": "OSYM-05", "cevap": "E",
        "metin": """Bir sözcüğün türetilirken veya çekim eki aldığında sonundaki ünsüzün düşmesine "ünsüz düşmesi" denir.
Aşağıda verilen "-cik, -cek" eki almış sözcüklerden hangisi ünsüz düşmesine örnek olarak gösterilemez?
A) ufacık
B) küçücük
C) büyücek
D) alçacık
E) yavrucak""",
    },
    {
        "kimlik": "OSYM-06", "cevap": "A",
        "metin": """Aşağıdaki dizelerin hangisinde "ulama" vardır?
A) Zebun oldum dört yanıma bakarım.
B) Yedi yıldır ben bu derdi çekerim.
C) Bunları söyleyen ben değilim ki!
D) Yenemedim yavrucağımı aldı felek.
E) Meydanda oynanan toptur, oyundur.""",
    },
    {
        "kimlik": "OSYM-07", "cevap": "E",
        "metin": """Aşağıdakilerin hangisinde ünlü düşmesi vardır?
A) Soruyu çözemeyince başını kaşıdı.
B) Arkadaşım midesinden rahatsızdı.
C) Akşam olunca ortalıktan el ayak çekildi.
D) Yüzüne hasret kaldık.
E) Omzuma çuvalımı atıp çıktım.""",
    },
    {
        "kimlik": "OSYM-08", "cevap": "D",
        "metin": """Aşağıdaki cümlelerin hangisinde ünsüz yumuşaması yoktur?
A) Onun penceresinden her gün sokağı izleyip dururdu.
B) Senin geldiğini görünce mutluluktan gözlerinin içi güldü.
C) Okulun duvarına bayrağı asmak için epeyce uğraşmışlar.
D) Yapılan antlaşmalar milletlerarası hukuka uygun olmalıdır.
E) Bütün gün bunları yiyerek sağlığını tamamen riske atıyorsun.""",
    },
    {
        "kimlik": "OSYM-09", "cevap": "A",
        "metin": """Çocuklar gerek ev gerekse okulda çevrelerindeki(I) bireyleri taklit ederek öğrenmektedir. Böylece çocuğun kişiliği(II) okul öncesi dönemde şekillenmekte, yetişkinlik(III) çağındaki davranışları üzerinde etkili olacak alışkanlıkların edinilmesi özellikle bu yıllara dayanmaktadır(IV). Aynı şekilde çocuğun bu yaşlarda kazandığı(V) yemek yeme alışkanlığı da hayatının daha sonraki dönemlerini etkileyerek ileride ortaya çıkabilecek beslenme sorunlarını önlemede temel çözüm yolunu oluşturmaktadır.
Bu parçada numaralanmış sözcüklerdeki ses olayları ikişerli eşleştirildiğinde aşağıdakilerden hangisi dışta kalır?
A) I
B) II
C) III
D) IV
E) V""",
    },
    {
        "kimlik": "OSYM-10", "cevap": "A",
        "metin": """Gel gurbet dağlarına bırak hüznünü
Geceler ellerinde ışısın gene
Unut "elveda" dediğin günü
Yeniden gir ikili hikâyemize
Bu dörtlükte aşağıdaki ses olaylarından hangileri vardır?
A) Ünlü düşmesi - ünsüz yumuşaması
B) Kaynaştırma - ünlü daralması
C) Ünsüz benzeşmesi - ünlü daralması
D) Ünsüz yumuşaması - ünsüz türemesi
E) Ünlü daralması - ünlü türemesi""",
    },
    {
        "kimlik": "OSYM-11", "cevap": "C",
        "metin": """Ünlü ile biten kelime veya eklere, yine ünlü ile başlayan ekler getirilirse araya "n-s-ş-y" kaynaştırma ünsüzlerinden biri girer.
Aşağıdakilerden hangisi, diğerlerinden farklı bir kaynaştırma ünsüzü içermektedir?
A) Kim kafayı üşütmek ister ki!
B) Kapıyı kim açık bırakmış?
C) Yedişer kişilik gruplar oluşturuldu.
D) Gez dünyayı gör Konya'yı!
E) Doğruyu, her yerde söylemek doğru değildir.""",
    },
    {
        "kimlik": "OSYM-12", "cevap": "D",
        "metin": """"y" ünsüzü kendinden önceki düz-geniş "a,e" ünlülerini daraltarak ı-i-u-ü'ye dönüştürür.
Aşağıdakilerin hangisinde bu kurala örnek kullanım yoktur?
A) Şimdi söylediklerini daha iyi anlıyorum.
B) Biraz acele et, imtihan on dakika sonra başlıyor.
C) Serhat, saatlerdir seni bekliyor.
D) Yarınki kutlamada sen de şiir okuyor musun?
E) Çocuğu istemediği bir konuda niçin zorluyorsun?""",
    },
    {
        "kimlik": "OSYM-13", "cevap": "D",
        "metin": """Dudak ünsüzlerinden "b", kendinden önceki "n"yi "m"ye dönüştürür.
Aşağıda verilen altı çizili sözcüklerin hangisinde bu kurala uyulmamıştır?
A) Perşembe günü gelirim dediyse gelir.
B) Ambarlarımızı bu sezon iyice doldurduk.
C) Cambazları heyecanla seyrediyordu.
D) "İstanbul'un taşı toprağı altındır." dedi.
E) Ateş çemberinden geçmek zor olur.""",
    },
    {
        "kimlik": "OSYM-14", "cevap": "D",
        "metin": """Aşağıdaki cümlelerde geçen altı çizili kelimelerin hangisinde ünsüz yumuşaması yoktur?
A) Bu işin layıkı olduğunu ortaya koydu.
B) Çocuğu niye çekiştirip duruyorsunuz?
C) Hâlâ inadından vazgeçmiş değil.
D) Kasabalı saatini, filozof Kant'a göre ayarlardı.
E) Elindeki kâğıdı önüne gelene gösteriyor, bir şeyler soruyordu.""",
    },
    {
        "kimlik": "OSYM-15", "cevap": "A",
        "metin": """Aşağıdaki cümlelerden hangisinde ünsüz düşmesine örnek olabilecek bir kullanım vardır?
A) Çocuğa bak! Sanki büyümüş de küçülmüş.
B) Artık büyük bir huzur içindeyiz.
C) Siz de balığı tavada mı kızartıyorsunuz?
D) Nasıl oldu da önündeki koca ağacı görmedin?
E) Küçük çocuk "ille de balon isterim!" diye tutturdu.""",
    },
    {
        "kimlik": "OSYM-16", "cevap": "E",
        "metin": """Aşağıdaki cümlelerin hangisinde ünsüz yumuşaması vardır?
A) İstanbul'un yazıhanesinde çalışıyordu.
B) Onunla hep köşedeki pastanede buluşurduk.
C) Bu postanede on kişi çalışıyorduk.
D) Kahvaltımız her zaman tarhana çorbasıydı.
E) İşe geç kaldığımız zamanlar olurdu.""",
    },
    {
        "kimlik": "OSYM-17", "cevap": "C",
        "metin": """Ölürsem yazıktır sana kanmadan
Kollarım boynunda halkalanmadan
Bir günüm geçmiyor seni anmadan
Derdine katlandım hiç usanmadan.
Bu dizelerde aşağıdakilerden hangisinin örneği yoktur?
A) Ünsüz yumuşaması
B) Ünlü daralması
C) Ünsüz türemesi
D) Ünsüz benzeşmesi
E) Ünlü düşmesi""",
    },
    {
        "kimlik": "OSYM-18", "cevap": "B",
        "metin": """Aşağıdaki cümlelerin hangisinde kaynaştırma ünsüzü yoktur?
A) Pireye kızıp yorgan yakma!
B) Neşeli ol ki daima genç kalasın.
C) Baba koruk yer, oğlunun dişi kamaşır.
D) Sütten ağzı yanan, yoğurdu üfleyerek yer.
E) Bir elin nesi var, iki elin sesi var.""",
    },
    {
        "kimlik": "OSYM-19", "cevap": "A",
        "metin": """Aşağıdaki altı çizili sözcüklerden hangisinde ünsüz yumuşaması vardır?
A) Kale burcuna ilkin, Hasan çıktı.
B) Yine, gürültüden dikkati dağılmıştı.
C) O dönemde sanata verilen değer yüksekti.
D) Son kitabının ismi "Destursuz Bağa Girenler" idi.
E) Kopardığı gülleri dikkatlice sepetine yerleştiriyordu.""",
    },
    {
        "kimlik": "OSYM-20", "cevap": "C",
        "metin": """Ardahan Kalesi'nin yanı başındaki bu eski mahalle, kentin tarihsel çekirdeğini oluşturuyor.
Bu cümledeki ses olayları aşağıdakilerin hangisinde vardır?
A) Ünsüz benzeşmesi - ünlü düşmesi
B) Ünlü daralması - ünsüz düşmesi
C) Ünsüz değişimi - ünsüz benzeşmesi
D) Ünsüz düşmesi - ünsüz değişimi
E) Ünlü daralması - ünsüz sertleşmesi""",
    },
    {
        "kimlik": "OSYM-21", "cevap": "B",
        "metin": """İnsan yapımı bir kanunu uygulamaktan vazgeçtiğinizde büyük bir fark doğmayabilir ancak evrensel bir kanunu değiştirmeye kalktığınızda tüm evreni değiştirmeniz gerekir.
Bu cümlede altı çizili sözcüklerdeki ortak ses olayı aşağıdakilerden hangisidir?
A) Ünsüz yumuşaması
B) Ünsüz benzeşmesi
C) Ünlü daralması
D) Ünsüz türemesi
E) Ünsüz değişimi""",
    },
    {
        "kimlik": "OSYM-22", "cevap": "C",
        "metin": """Seçkin bir kimse değilim
İsmimin baş harflerinde kimliğim
Bağışlanmamı dilerim
Bu dizelerde aşağıdaki ses olaylarından hangileri vardır?
A) Ünsüz benzeşmesi - ünlü değişimi
B) Ünlü düşmesi - ünsüz türemesi
C) Ünsüz benzeşmesi - ünsüz değişimi
D) Ünsüz değişimi - ünsüz düşmesi
E) Ünlü düşmesi - ulama""",
    },
    {
        "kimlik": "OSYM-23", "cevap": "D",
        "metin": """Aşağıdaki cümlelerin hangisinde ünlü düşmesi yoktur?
A) Rıhtımdan ayrılan gemi gittikçe ufaldı.
B) Yaşlı adam çocukları kaldırımda oynamaları konusunda uyardı.
C) Gözleri ışıl ışıl parlayan insanlarla çevresi sarılmıştı.
D) Yaralanmış küçücük serçeyi eline aldı.
E) Hayata geçirilmeye değer gördüğü ilginç bir fikri vardı.""",
    },
    {
        "kimlik": "OSYM-24", "cevap": "B",
        "metin": """Aşağıdaki sözcüklerin hangisine ünlü ile başlayan bir ek getirildiğinde sözcüğün sonundaki sert ünsüz yumuşamaz?
A) Yurt
B) Süt
C) Renk
D) Kurt
E) Tat""",
    },
    {
        "kimlik": "OSYM-25", "cevap": "A",
        "metin": """İlham bize dışarıdan verilen gizemli bir güç müdür yoksa içeriden saflaşarak, kalpten güçlü bir istekle odaklanarak, sufi deyişle -boş bir kamışa dönüşerek- güncel, nesnel aklın bir adım daha üstüne yükselerek bizim ulaştığımız bir bilgi seviyesi midir?
Bu parçada aşağıdaki ses olaylarından hangisi yoktur?
A) Ünlü daralması
B) Ünsüz benzeşmesi
C) Ünsüz değişimi
D) Ünsüz düşmesi
E) Ünlü düşmesi""",
    },
    {
        "kimlik": "OSYM-26", "cevap": "A",
        "metin": """Daha güneş batmamışken ortalığı kaplayan bu karanlıklar
Nasıl da ben gibi nasıl da ben gibi
Bu aksak ayak, çatlak ses
Nasıl da kararan gün gibi gün gibi
Gençlik hevesi başta
Solmuş yapraklar ayakta
Sessiz karanlıklarda ben ne diye telaşta
Bu dizelerde aşağıdaki ses olaylarından hangisi yoktur?
A) Ünsüz türemesi
B) Ünsüz değişimi
C) Ünsüz benzeşmesi
D) Ünlü daralması""",
    },
    {
        "kimlik": "OSYM-27", "cevap": "E",
        "metin": """Deniz; ucu bucağı sınırsız olan ve bu yönüyle de insanda sonsuzluk duygusu çağrıştıran tabiata ait bir mekândır. Sonsuzluğu çağrıştıran bu mekân aynı zamanda bolluğu da simgelemektedir.
Bu parçada aşağıdaki ses olaylarından hangisi yoktur?
A) Ünsüz yumuşaması
B) Ünlü düşmesi
C) Ünsüz sertleşmesi
D) Kaynaştırma
E) Ünsüz türemesi""",
    },
    {
        "kimlik": "OSYM-28", "cevap": "C",
        "metin": """Yeşil pencerenden bir gül at bana,
Işıklarla dolsun kalbimin içi.
Geldim işte mevsim gibi kapına
Gözlerimde bulut, saçlarımda çiy.
Açılan bir gülsün sen yaprak yaprak,
Ben aşkımla bahar getirdim sana;
Tozlu yollarından geçtiğim uzak
İklimlerden şarkılar getirdim sana.
Bu dizelerde aşağıdaki ses olaylarından hangisi yoktur?
A) Ünlü değişimi
B) Ünsüz benzeşmesi
C) Ünlü daralması
D) Ünsüz yumuşaması
E) Ulama""",
    },
    {
        "kimlik": "OSYM-29", "cevap": "E",
        "metin": """İstanbul'u dinliyorum, gözlerim kapalı
Önce hafiften bir rüzgâr esiyor;
Yavaş yavaş sallanıyor
Yapraklar, ağaçlarda;
Uzaklarda, çok uzaklarda,
Sucuların hiç durmayan çıngırakları
İstanbul'u dinliyorum, gözlerim kapalı
Bu dizelerde aşağıdakilerden hangisi yoktur?
A) Ulama
B) Ünlü daralması
C) Ünsüz benzeşmesi
D) Kaynaştırma
E) Ünsüz ikizleşmesi""",
    },
    {
        "kimlik": "OSYM-30", "cevap": "E",
        "metin": """Gönlümde hep o zanla beraber çağıldadı,
Bildim nedir ufuktaki sonsuzluğun tadı!
Bir gün dedim ki istemem artık ne yer ne yâr?
Çıktım sürekli gurbete, gezdim diyar diyar;
Gittim o son diyara ki serhaddidir yerin,
Hâlâ dilimdedir tuzu engin denizlerin!
Bu dizelerde aşağıdaki ses olaylarından hangisi yoktur?
A) Ünsüz benzeşmesi
B) Ünsüz yumuşaması
C) Ünsüz türemesi
D) Ünlü düşmesi
E) Ünsüz düşmesi""",
    },
    {
        "kimlik": "OSYM-31", "cevap": "B",
        "metin": """İnce bir saman tozu döndükçe düven
Koltuğa minderlere yağsın masaya
Gel büzül eşiğinde Sonsuz'a güven
Alnını bölük pörçük yazlara daya.
Bu dörtlükte aşağıdakilerden hangisi yoktur?
A) Ünlü düşmesi
B) Ünlü türemesi
C) Ünsüz benzeşmesi
D) Ulama
E) Ünsüz yumuşaması""",
    },
    {
        "kimlik": "OSYM-32", "cevap": "E",
        "metin": """Aşağıdaki dizelerden hangisinde farklı bir ses olayı vardır?
A) Evet kimsesizdik ama umudumuz vardı
Üç ev görsek bir şehir sanıyorduk
B) Gölgemiz tortop ayak ucumuzda
Sevinsek de sonunu biliyoruz
C) Ayağının suya değdiği yerde bir gökyüzü
Çıra benizli soğuk ay ışığı
D) Geyiğin gözleri pırıl pırıl gecede
İmdat ateşleri gibi ürkek telaşlı
E) Ama siz zavallısınız ben de zavallıyım
Eskimiş şeylerle avunamıyoruz""",
    },
    {
        "kimlik": "OSYM-33", "cevap": "B",
        "metin": """I. İnsan, doğumundan itibaren bir geleneğin içinde yer alır.
II. Yağmurdan sonra ormanın nemli zemininden yüzlerce mantar fışkırmış.
III. Arabalar, yağmurdan kayganlaşan yolda güçlükle ilerliyordu.
IV. Konak, büyükçe bir gölün kıyısına inşa edilmişti.
V. Rengârenk kamyon kasalarından buğday taneleri dökülüyor.
Numaralanmış cümlelerin yer tamlayıcılarıyla ilgili aşağıdakilerden hangisi söylenemez?
A) I. cümlenin yer tamlayıcısında belirtili isim tamlaması vardır.
B) II. cümlenin yer tamlayıcısında edat vardır.
C) III. cümlenin yer tamlayıcısında sıfat-fiil vardır.
D) IV. cümlenin yer tamlayıcısında sıfat tamlaması vardır.
E) V. cümlenin yer tamlayıcısında belirtisiz isim tamlaması vardır""",
    },
    {
        "kimlik": "OSYM-34", "cevap": "III",
        "metin": """(I) Okyanusların ısınmasına aşırı avlanma, kitlesel turizm ve kirliliğin eklenmesiyle yeryüzünün cennet köşelerinden üzüntü veren haberler gelmeye devam ediyor. (II) Örneğin Avustralya'daki Büyük Set Resifi, gerçekleşen iklim değişikliğiyle yakından ilişkili bu olumsuz etkileri en üst seviyede yaşıyor. (III) Mercan resiflerinin beyazlayarak ölmesi okyanusların iklim değişikliğine gösterdiği en açık tepkilerden biri. (IV) Kızıldeniz'in bir ucundaki Akabe Körfezi'nden gelen haberler ise ümit verici. (V) Körfezin yarı kapalı bir havzada bulunması ve aldığı yıllık yağışın azlığı sayesinde buradaki mercan resifleri çok sağlıklı.
Bu parçada numaralanmış cümlelerin hangisinde hem isim-fiil hem sıfat-fiil hem de zarf-fiil yer almaktadır?""",
    },
    {
        "kimlik": "OSYM-35", "cevap": "C",
        "metin": """Sevgili günlük,
Nerede olursam olayım yağmur peşimde, yağdıkça yağıyor. Yağmurun küçücük damlaları içinde saklanan ilham perileri aklıma düştüğünden mi, yağmur sonrası toprak kokusunu sevdiğimden mi benimle geliyor? Kim bilir?
Bu parçada aşağıdaki ses olaylarından hangisi yoktur?
A) Ünsüz benzeşmesi
B) Ünlü düşmesi
C) Ünlü daralması
D) Ünsüz yumuşaması
E) Ünsüz düşmesi""",
    },
    {
        "kimlik": "OSYM-36", "cevap": "E",
        "metin": """Trenin son vagonuna gelene kadar bir sonraki vagonda nelerle karşılaşılacağı ile ilgili merak ve beklentiler yaşamın sürükleyici güçlerindendir; tıpkı heyecanlı bir film izlemek gibi. Son vagon, yolculuğa dair beklentilerin de sonudur; heyecan diner ve deneyimlenmemiş duygulardan uzaklaşılır.
Bu parçada aşağıdaki durum eklerinden hangisi yoktur?
A) İlgi
B) Ayrılma
C) Yönelme
D) Bulunma
E) Belirtme""",
    },
    {
        "kimlik": "OSYM-37", "cevap": "D",
        "metin": """Vücudumuzdaki proteinlerin üçte birini oluşturan kolajen ----.
Bu cümle aşağıdakilerden hangisiyle tamamlanırsa öge dizilişi "özne - zarf tümleci - belirtisiz nesne - yüklem" şeklinde olur?
A) aynı zamanda bilinen en sağlam malzemelerden biridir
B) başta kemik ve deri olmak üzere tüm dokularda bulunur
C) genç ve pürüzsüz bir cilde sahip olmamıza yardımcı olur
D) bulunduğu dokudaki işlevine göre karmaşık yapılar ortaya çıkarır
E) hayli uzun ömürlü olmakla birlikte belli bir yaşam süresine sahiptir""",
    },
    {
        "kimlik": "OSYM-38", "cevap": "D",
        "metin": """İnsan; daha güçlü canlılara karşı tek başına kendini koruyamaz, tek başına ihtiyaçlarını karşılayamaz dolayısıyla bir arada yaşamak tabii ve zaruridir.
Bu cümlede aşağıdakilerden hangisi yoktur?
A) Niteleme sıfatını niteleyen zarf
B) Yönelme durumuyla kullanılan edat
C) Yeterlilik bildiren olumsuz fiil
D) Üçüncü çoğul iyelik eki almış isim
E) Belirtme durumu eki almış zamir""",
    },
    {
        "kimlik": "OSYM-39", "cevap": "D",
        "metin": """(I) Süper kahramanların çizgi romanlarda güçlerine kavuşmaları, genellikle belli başlı şekillerde olmaktadır. (II) Bilinmeyen bir dünyadan ya da doğrudan uzaydan gelen insanüstü güçlere sahip süper kahramanlar, en yaygın bilinen örneklerdendir. (III) İkinci sıradakiler radyoaktif etki sonucu güçlerine kavuşan süper kahramanlardır. (IV) Radyoaktif bir hayvan tarafından ısırılan karakter, bir süper kahramana dönüşüp onu ısıran hayvanın özelliklerine sahip olur. (V) Başvurulan yöntemlerden bir diğeri de deney kazaları sonucu ortaya çıkan kahramanlardır.
Bu parçada numaralanmış cümlelerle ilgili aşağıdakilerden hangisi yanlıştır?
A) I. cümlenin öznesi, belirtili isim tamlamasıdır.
B) II. cümlenin öznesi, sıfat tamlamasıdır.
C) III. cümlenin yüklemi, sıfat tamlamasıdır.
D) IV. cümlenin öznesi, belirtisiz isim tamlamasıdır.
E) V. cümlenin yüklemi, sıfat tamlamasıdır.""",
    },
]


ILERLEME_YOLU = Path(
    "/tmp/claude-1000/-home-emir-Belgeler-Yazilim-BitigAI/"
    "6194d298-ca12-44ae-aeb9-7bca05e10b6b/scratchpad/mebi_agent_osym_ilerleme.jsonl"
)


def main() -> int:
    import json

    if not model.anahtar_var_mi():
        print(model.anahtar_yardimi(), file=sys.stderr)
        return 2

    dogru = yanlis = bos = 0
    print(f"\n{len(SORULAR)} soru (osym-tyt-turkce-sorular.txt + osym-cikmis-sorular.txt)\n", flush=True)
    print(f"{'kimlik':<10} {'bek':>4} {'bul':<4} {'arac':>4} durum", flush=True)
    print("─" * 44, flush=True)

    ILERLEME_YOLU.parent.mkdir(parents=True, exist_ok=True)
    with ILERLEME_YOLU.open("w", encoding="utf-8") as ilerleme:
        for soru in SORULAR:
            try:
                bulunan, gecmis = coz(soru)
            except model.ModelHatasi as hata:
                print(f"{soru['kimlik']:<10} HATA: {hata}", flush=True)
                ilerleme.write(json.dumps({"kimlik": soru["kimlik"], "hata": str(hata)}, ensure_ascii=False) + "\n")
                ilerleme.flush()
                continue

            arac_sayisi = sum(1 for m in gecmis if m.get("role") == "tool")
            if bulunan is None:
                bos += 1
                durum = "∅ FORMAT"
            elif bulunan == soru["cevap"].upper():
                dogru += 1
                durum = "✓ DOGRU"
            else:
                yanlis += 1
                durum = "✗ YANLIS"

            print(f"{soru['kimlik']:<10} {soru['cevap']:>4} {bulunan or '?':<4} {arac_sayisi:>4}   {durum}", flush=True)

            arac_dokumu = [
                {"arac": c["function"]["name"], "girdi": c["function"]["arguments"]}
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
    print("─" * 44, flush=True)
    print(f"  doğru {dogru}  ·  yanlış {yanlis}  ·  format hatası {bos}  (toplam {toplam})", flush=True)
    if toplam:
        print(f"\n  soru başarımı: {dogru / toplam * 100:.1f}%", flush=True)
    print("\n  NOT: bu sonuç deneyseldir, hiçbir altın kümeye/motora geri beslenmez.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
