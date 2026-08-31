"""Fiil çekimi (Dilim 2) testleri.

Ad çekiminde olduğu gibi her kural pozitif **ve** negatifiyle sınanır. Buradaki
negatifler v1'in en kötü hatasını hedefler: `hediye`/`diyet`/`niyet` sözcükleri
"diye" altdizisi yüzünden ünlü daralması alıyordu.
"""

import pytest

from bitig.cozumleyici import kelimeyi_cozumle
from bitig.turetim import ek_yuzeyi_coz


def olaylar(kelime: str) -> set[str]:
    return {olay.kural_id for olay in kelimeyi_cozumle(kelime).olaylar}


def olay(kelime: str, kural_id: str):
    for okuma in kelimeyi_cozumle(kelime).okumalar:
        for o in okuma.olaylar:
            if o.kural_id == kural_id:
                return o
    raise AssertionError(f"{kelime!r} için {kural_id} yok")


# --- SES.DAR.01 Ünlü daralması ---------------------------------------------


@pytest.mark.parametrize(
    "kelime", ["başlıyor", "bekliyor", "arıyor", "diyor", "yiyor", "anlıyor", "zorluyorsun"]
)
def test_daralma_pozitif(kelime):
    assert "SES.DAR.01" in olaylar(kelime)


@pytest.mark.parametrize("kelime", ["okuyor", "yürüyor", "büyüyor", "koruyor"])
def test_zaten_dar_unlude_daralma_bildirilmez(kelime):
    """`oku` + -Iyor yapısal olarak `ok`a düşer — yoksa "okuuyor" olurdu — ama
    ortada DARALMA yoktur: `u` zaten dardır.

    Kural "geniş ünlü (a, e) daralır" biçimindedir. Çıkmış bir ÖSYM sorusunda
    (EBA) "okuyor" tam olarak ünlü daralmasının OLMADIĞI seçenek olarak
    sorulmuştur; motor önce yanlış cevap veriyordu.

    Mekanizma ile öğretilen adın ayrı olmasının pratik sonucu budur: düşme
    gerçekleşir ama olay bildirilmez.
    """
    assert "SES.DAR.01" not in olaylar(kelime)
    assert not kelimeyi_cozumle(kelime).cozumlenemedi  # yine de çözümlenir


@pytest.mark.parametrize(
    "kelime,gerekce",
    [
        ("geliyor", "'i' yardımcı ünlü — kök ünsüzle bitiyor, daralma yok"),
        ("yazıyor", "yardımcı ünlü"),
        ("görüyor", "yardımcı ünlü"),
        ("yedim", "ek ünsüzle başlıyor"),
        ("dedim", "ek ünsüzle başlıyor"),
        ("hediye", "isim — v1 'diye' altdizisiyle daralma diyordu"),
        ("diyet", "isim"),
        ("niyet", "isim"),
        ("sandalye", "isim"),
        ("arayacak", "-AcAk daraltmaz, sadece kaynaştırma"),
    ],
)
def test_daralma_negatif(kelime, gerekce):
    assert "SES.DAR.01" not in olaylar(kelime), gerekce


def test_daralma_uyumu_daralmis_govdeye_gore_cozulur():
    """`söyle` → `söyl` (son ünlü ö) → "söylüyor".

    Özgün köke (son ünlü `e`) bakılsaydı "söyliyor" çıkardı. Bu, ünlü
    düşmesinin tam tersidir: orada uyum özgün köke göre çözülür (hapis→hapsi).
    İki kuralın zıt davranması bu motorun ayırt ettiği inceliklerden biri.
    """
    assert "SES.DAR.01" in olaylar("söylüyor")
    assert "SES.DAR.01" in olaylar("özlüyor")
    assert kelimeyi_cozumle("söyliyor").cozumlenemedi


def test_daralma_govdede_unlu_birakmadiginda_uyum_ozgun_kokten():
    """`de` → `d`: gövdede ünlü kalmaz, uyumun dayanağı yok.
    Özgün kökün `e`sine dönülmezse varsayılan `ı`ya düşer ve "dıyor" çıkar."""
    assert "SES.DAR.01" in olaylar("diyor")
    assert kelimeyi_cozumle("dıyor").cozumlenemedi


def test_daralma_ekte_de_olabilir():
    """Daralmayı tetikleyen öznitelik `-mA` ekinin kendisindedir:
    gel + me + iyor → gelme → gelm + iyor → "gelmiyor"."""
    assert "SES.DAR.01" in olaylar("gelmiyor")
    assert "SES.DAR.01" in olaylar("gitmiyorum")


def test_de_ye_duzensizligi():
    """`de-` ve `ye-` yalnızca -Iyor'dan önce değil, ünlüyle başlayan HER
    ekten önce daralır. Bu iki fiile özgü bir düzensizliktir ve kodda değil
    `veri/tyt_override.json` içinde işaretlenir."""
    for kelime in ("diyecek", "yiyecek", "diyen", "yiyerek"):
        assert "SES.DAR.01" in olaylar(kelime), kelime
    # Ünsüzle başlayan ekten önce daralmaz:
    assert "SES.DAR.01" not in olaylar("yedim")
    assert "SES.DAR.01" not in olaylar("demiş")


def test_daralma_kaniti_ogretileni_yazar():
    """Kanıt mekanizmayı değil öğretileni gösterir: geniş ünlü daraldı."""
    o = olay("başlıyor", "SES.DAR.01")
    assert (o.kanit.once, o.kanit.sonra) == ("a", "ı")
    assert o.kanit.govde == "başla"

    o = olay("yiyecek", "SES.DAR.01")
    assert (o.kanit.once, o.kanit.sonra) == ("e", "i")


# --- Fiillerde yumuşama, benzeşme, düşme -----------------------------------


@pytest.mark.parametrize("kelime", ["gidiyor", "gidecek", "ediyor", "tadıyor", "güdüyor"])
def test_fiilde_yumusama(kelime):
    assert "SES.YUM.01" in olaylar(kelime)


@pytest.mark.parametrize("kelime", ["satıyor", "tutuyor"])
def test_fiilde_yumusama_negatif(kelime):
    assert "SES.YUM.01" not in olaylar(kelime)


def test_yumusama_ekte_de_olabilir():
    """`-DIk` ve `-AcAk` eklerinin kendi Voicing'i vardır; yumuşayan `k` köke
    değil eke aittir. `koke_ekleniyor` gibi kaba bir kısıt bunu engellerdi."""
    assert "SES.YUM.01" in olaylar("gördüğüm")  # gör + dük + üm
    assert "SES.YUM.01" in olaylar("geleceğim")  # gel + ecek + im
    assert "SES.YUM.01" in olaylar("yapacağız")


def test_git_yumusamasi_ekin_ilk_sesine_bagli():
    """Aynı kök, iki farklı sonuç — kararı ek veriyor."""
    assert olaylar("gidiyor") == {"SES.YUM.01"}  # ek ünlüyle başlar → yumuşar
    assert olaylar("gitti") == {"SES.BEN.01"}  # ek ünsüzle başlar → sertleşir


@pytest.mark.parametrize("kelime", ["geçti", "açtı", "kestik", "çıktı", "baktım", "görüştük"])
def test_fiilde_benzesme(kelime):
    assert "SES.BEN.01" in olaylar(kelime)


@pytest.mark.parametrize("kelime", ["geldi", "yazdı", "buldum", "gördü"])
def test_fiilde_benzesme_negatif(kelime):
    assert "SES.BEN.01" not in olaylar(kelime)


@pytest.mark.parametrize("kelime", ["kavruldu", "ayrıldı", "çevrildi", "savruldu"])
def test_fiilde_unlu_dusmesi(kelime):
    assert "SES.UD.01" in olaylar(kelime)


def test_fiilde_unlu_dusmesi_negatif():
    assert "SES.UD.01" not in olaylar("kavurdu")  # ek ünsüzle başlıyor


# --- Morfotaktik kısıtlar ---------------------------------------------------


def test_genis_zaman_bicimini_kok_belirler():
    """`-(I)r` yalnızca Aorist_I, `-(A)r` yalnızca Aorist_A köklerine gelir.
    Kısıt kodda değil `veri/ekler.json` içindeki `gerektirir` alanındadır."""
    assert not kelimeyi_cozumle("gelir").cozumlenemedi  # gel [Aorist_I]
    assert not kelimeyi_cozumle("atar").cozumlenemedi  # at  [Aorist_A]
    assert kelimeyi_cozumle("gelar").cozumlenemedi
    assert kelimeyi_cozumle("atır").cozumlenemedi


def test_edilgen_in_unluden_sonra_yardimci_unlu_almaz():
    assert not kelimeyi_cozumle("okunmuş").cozumlenemedi  # oku + n + muş
    assert not kelimeyi_cozumle("okunuyor").cozumlenemedi


# --- Çatı/yapım eki sonrası geniş zaman her zaman dar (Aorist_I) tiptedir ---
#
# 2026-08-07'de bulunan motor hatası: `uygulanabilir_mi` çıplak KÖKÜN
# özniteliklerine bakıyordu, araya giren ekin (gövdenin o anki son morfeminin)
# özniteliklerine değil. "yap" [Aorist_A] olduğu için "yapılır" (edilgen+geniş
# zaman, standart Türkçede TEK doğru biçim) hiç çözülemiyordu — motor yalnızca
# "yapılar" (yanlış) türetmeye çalışıyordu. Çatı/yapım/yeterlilik/kurallı
# birleşik fiil ekleri Türkçede kökün geniş zaman tipini SIFIRLAR, her zaman
# dar tiptedirler (yapar ama yapılır, değil yapılar). Düzeltme iki parçalı:
# (1) bu ekler artık kendi `oznitelikler`inde Aorist_I taşır, (2) kontrol
# `govde_oz`e (o anki son morfem) bakar, çıplak köke değil.


@pytest.mark.parametrize(
    "kelime,beklenen_kok",
    [
        ("yapılır", "yap"),  # edilgen — "yap" [Aorist_A] ama sonuç dar
        ("kırılır", "kır"),  # edilgen — "kır" [Aorist_A]
        ("yaptırır", "yap"),  # ettirgen
        ("kestirir", "kes"),  # ettirgen
        ("yazışır", "yaz"),  # işteş
        ("yıkanır", "yıka"),  # dönüşlü
        ("yapabilir", "yap"),  # yeterlilik
        ("gidiverir", "git"),  # tasvir — tezlik
    ],
)
def test_catili_fiilde_genis_zaman_daima_dar(kelime, beklenen_kok):
    kokler = {o.kok for o in kelimeyi_cozumle(kelime).okumalar}
    assert beklenen_kok in kokler


def test_catili_fiil_yanlis_genis_zaman_bicimini_uretmez():
    """"yapılar" (edilgen + Aorist_A) yanlış Türkçedir; motor bunu ÇATI
    okuması olarak üretmemeli. ("yapılar" başka bir kökten — yapı+lar,
    çoğul isim — geçerli bir okuma taşıyabilir, o ayrı.)"""
    ek_kimlikleri_kumesi = [o.ek_kimlikleri for o in kelimeyi_cozumle("yapılar").okumalar]
    assert not any(
        "EK.CATI.EDILGEN.IL" in ekler and "EK.KIP.GENIS.A" in ekler
        for ekler in ek_kimlikleri_kumesi
    )


@pytest.mark.parametrize(
    "kelime,beklenen_kok",
    [
        ("kitaplaşır", "kitap"),  # isimden fiil -lAş, sözlükleşmemiş türetim
        ("kitaplaştırır", "kitap"),  # -lAş + ettirgen
        ("güzelleşir", "güzel"),
        ("bilgisayarlanır", "bilgisayar"),  # isimden fiil -lAn
    ],
)
def test_isimden_fiil_turetiminde_genis_zaman_cozumleniyor(kelime, beklenen_kok):
    kokler = {o.kok for o in kelimeyi_cozumle(kelime).okumalar}
    assert beklenen_kok in kokler


@pytest.mark.parametrize(
    "kelime,beklenen_kok",
    [
        ("yürüyüş", "yürü"),  # ünlüyle biten gövde — kaynaştırma-y gerekir
        ("okuyuş", "oku"),
        ("söyleyiş", "söyle"),
    ],
)
def test_isim_fiil_is_unluyle_biten_govdeye_kaynastirmayla_eklenir(kelime, beklenen_kok):
    """`EK.ISIMFIIL.IS`in arketipi "Iş" idi, ünsüzle biten gövdede (geliş,
    bakış) çalışıyordu ama ünlüyle bitende hiç kaynaştırma-y eklemiyordu.
    "+yIş" olarak düzeltildi (2026-08-07)."""
    kokler = {o.kok for o in kelimeyi_cozumle(kelime).okumalar}
    assert beklenen_kok in kokler


def test_isim_fiil_is_unsuzle_biten_govdede_degismedi():
    """Kaynaştırma-y yalnızca ünlüyle biten gövdede görünür; ünsüzle biten
    gövdede (gel, bak) eskisi gibi çıplak "-Iş" kalmalı — regresyon kontrolü."""
    assert not kelimeyi_cozumle("geliş").cozumlenemedi
    assert not kelimeyi_cozumle("bakış").cozumlenemedi


@pytest.mark.parametrize(
    "kelime,kok",
    [
        ("yazıldı", "yaz"),  # edilgen
        ("yazdırdı", "yaz"),  # ettirgen
        ("gelince", "gel"),  # zarf-fiil
        ("gelmeden", "gel"),  # zarf-fiil
        ("yazmak", "yaz"),  # isim-fiil
        ("gelecekti", "gel"),  # birleşik kip (hikâye)
        ("geliyormuş", "gel"),  # birleşik kip (rivayet)
        ("gelirse", "gel"),  # birleşik kip (şart)
        ("gelmeliyiz", "gel"),  # gereklilik
    ],
)
def test_2b_ekleri_cozumleniyor(kelime, kok):
    kokler = {o.kok for o in kelimeyi_cozumle(kelime).okumalar}
    assert kok in kokler


def test_isim_fiil_mak_cekim_almaz():
    """"yazmaya" = yazma + ya olarak çözümlenir, yazmak + a olarak değil.
    -mAk grafta çıkmaz durumdur; bu modern çözümlemeye uygundur."""
    okumalar = kelimeyi_cozumle("yazmaya").okumalar
    assert okumalar
    assert all("EK.ISIMFIIL.MAK" not in o.ek_kimlikleri for o in okumalar)


# --- Ek-fiil (isim/sıfat yüklemi) -------------------------------------------
#
# 2026-08-06 oturumunda bulundu: ek-fiilin hikâye/rivayet/şart/kişi ekleri
# yalnızca FİİL kipi üstünden geliyordu (KIP_ZAMIR/KIP_IYELIK). İsim/sıfat
# yüklemi üstündeki hâli ("menekşeydi", "öğrenciyim") hiç çözülemiyordu —
# EBA Fiiller testlerinin üçte biri tam olarak bu kelimelerde tıkandı.
# `veri/ekler.json`de EK.KISI.Z.*, EK.BILDIRME, EK.BIRLESIK.* ekleri artık
# ISIM_KOK/HAL_SONRASI/IYELIK_SONRASI/IYELIK3_SONRASI/COGUL_SONRASI'ndan da
# kaynaklanıyor.


@pytest.mark.parametrize(
    "kelime,kok",
    [
        ("öğrenciyim", "öğrenci"),  # isim kökü + kişi eki (ek-fiil geniş zaman)
        ("öğrencisin", "öğrenci"),
        ("öğrenciyiz", "öğrenci"),
        ("evdeyim", "ev"),  # hâl eki sonrası + kişi eki
        ("kitabımdır", "kitap"),  # iyelik sonrası + bildirme
        ("menekşeydi", "menekşe"),  # isim kökü + hikâye birleşik
        ("arkadaşımdı", "arkadaş"),  # iyelik sonrası + hikâye birleşik
        ("bahçesiyse", "bahçe"),  # iyelik (3.tekil) sonrası + şart birleşik
        ("öğrenciymiş", "öğrenci"),  # isim kökü + rivayet birleşik
    ],
)
def test_nominal_ekfiil_cozumleniyor(kelime, kok):
    kokler = {o.kok for o in kelimeyi_cozumle(kelime).okumalar}
    assert kok in kokler


def test_nominal_ekfiil_ilgi_halinden_gelmez():
    """Tamlayan eki (ilgi hâli) kaynak listesine bilerek eklenmedi — 'kedinin'
    tek başına yüklem çekimi almaz. Aşırı üretimi sınırlayan negatif örnek."""
    assert kelimeyi_cozumle("kedininim").cozumlenemedi


# --- İstek kipi --------------------------------------------------------------
#
# 2026-08-06: `ekler.json`de hiç yoktu ("alalım" fiil bile sayılmıyordu). 1./2.
# kişi eklendi (tekil+çoğul); 3. kişi ("-A", "-AlAr") bilerek dışarıda bırakıldı
# — çok kısa/çakışmaya açık bir arketip, gerçek soruda hiç görülmedi.


@pytest.mark.parametrize(
    "kelime,kok,kural_id",
    [
        ("alalım", "al", "EK.KIP.ISTEK.1C"),
        ("okuyalım", "oku", "EK.KIP.ISTEK.1C"),
        ("geleyim", "gel", "EK.KIP.ISTEK.1T"),
        ("okuyayım", "oku", "EK.KIP.ISTEK.1T"),
        ("gelesin", "gel", "EK.KIP.ISTEK.2T"),
        ("gelesiniz", "gel", "EK.KIP.ISTEK.2C"),
    ],
)
def test_istek_kipi_cozumleniyor(kelime, kok, kural_id):
    okumalar = kelimeyi_cozumle(kelime).okumalar
    assert any(o.kok == kok and kural_id in o.ek_kimlikleri for o in okumalar)


# --- Gerçek belirsizlikler --------------------------------------------------


def test_bilemek_belirsizligi():
    """"biliyor" = bil-iyor (bilmek) veya bile-iyor (bilemek/bileylemek).
    İkincisi daralma üretir. Bağlamsız ayrılamaz: 'bıçağı biliyor'."""
    sonuc = kelimeyi_cozumle("biliyor")
    assert {"bil", "bile"} <= {o.kok for o in sonuc.okumalar}
    assert sonuc.olayda_belirsiz
    assert sonuc.kesin_olaylar == frozenset()


@pytest.mark.parametrize("kelime", ["atıldı", "yazıldı", "söndürüldü", "dinlendi"])
def test_edilgen_donuslu_belirsizligi(kelime):
    """`-Il/-In` hem edilgen hem dönüşlü çatı kurar; ayrım bağlama bağlıdır.

    "Atıldı" cümle içinde "kovuldu" (edilgen) da "kendini attı" (dönüşlü) da
    okunabilir. Motor ikisini de üretir, seçmez — seçim bağlam katmanının işi.
    """
    kimlikler = {
        k for o in kelimeyi_cozumle(kelime).okumalar for k in o.ek_kimlikleri
    }
    catı_ekleri = {k for k in kimlikler if k.startswith("EK.CATI.EDILGEN") or k.startswith("EK.CATI.DONUSLU")}
    edilgen = {k for k in catı_ekleri if "EDILGEN" in k}
    donuslu = {k for k in catı_ekleri if "DONUSLU" in k}
    assert edilgen and donuslu


def test_ayirt_belirsizligi():
    """"ayırdı" = ayır-dı (fiil) veya ayırt-ı (isim, yumuşamalı)."""
    sonuc = kelimeyi_cozumle("ayırdı")
    assert {"ayır", "ayırt"} <= {o.kok for o in sonuc.okumalar}
    assert sonuc.olayda_belirsiz


# --- Kurallı birleşik fiil (tezlik, süreklilik, yaklaşma) -------------------
#
# 2026-08-06: yalnızca yeterlilik/yetersizlik vardı. Çatı ekleriyle aynı graf
# deseni (FIIL_KOK → FIIL_KOK) kullanılarak eklendi — ayrı bir "ikinci fiil
# kökü döngüsü" gerekmedi, tahmin edilenden daha ucuz çıktı.


@pytest.mark.parametrize(
    "kelime,kok,kural_id",
    [
        ("gidiver", "git", "EK.TASVIR.TEZLIK"),
        ("bakıver", "bak", "EK.TASVIR.TEZLIK"),
        ("okuyuver", "oku", "EK.TASVIR.TEZLIK"),
        ("bakadur", "bak", "EK.TASVIR.SUREKLILIK.DUR"),
        ("tutagörsün", "tut", "EK.TASVIR.SUREKLILIK.GOR"),
        ("düşeyazdım", "düş", "EK.TASVIR.YAKLASMA"),
    ],
)
def test_kuralli_birlesik_fiil_cozumleniyor(kelime, kok, kural_id):
    okumalar = kelimeyi_cozumle(kelime).okumalar
    assert any(o.kok == kok and kural_id in o.ek_kimlikleri for o in okumalar)


def test_tasvir_eki_ustune_kip_gelir():
    """Kurallı birleşik fiil, tam bir fiil kökü gibi davranır: üstüne normal
    kip/kişi zinciri eklenebilir. 'süregeliyor' hem bütünsel okuma (süregel
    çıplak kök) hem türetim okuması (sür+egel+iyor) taşır — belirsizlik."""
    sonuc = kelimeyi_cozumle("süregeliyor")
    kokler = {o.kok for o in sonuc.okumalar}
    assert "sür" in kokler
    turetim_okuma = next(o for o in sonuc.okumalar if o.kok == "sür")
    assert "EK.TASVIR.SUREKLILIK.GEL" in turetim_okuma.ek_kimlikleri
    assert "EK.KIP.SIMDIKI" in turetim_okuma.ek_kimlikleri


# --- Soru eki ("mi") ---------------------------------------------------------
#
# 2026-08-06: "mi" (Ques) çıkışsız DEGISMEZ durumundaydı, ek-fiil hiç
# çözemiyordu ("miyim" tamamen COZULEMEDI idi). Kendi durumuna (SORU_EKI_
# SONRASI) taşındı — yalnızca ek-fiil ekleri kaynaklanır, tam ISIM_KOK değil
# (yanlışlıkla "minin"/"milik" gibi sahte isim çekimleri üretilmemeli).


@pytest.mark.parametrize("kelime,kural_id", [("miyim", "EK.KISI.Z.1T"), ("miydi", "EK.BIRLESIK.HIKAYE"), ("miymiş", "EK.BIRLESIK.RIVAYET")])
def test_soru_eki_ekfiil_alir(kelime, kural_id):
    okumalar = kelimeyi_cozumle(kelime).okumalar
    assert any(o.kok == "mi" and o.tur == "Ques" and kural_id in o.ek_kimlikleri for o in okumalar)


def test_soru_eki_isim_cekimi_almaz():
    """SORU_EKI_SONRASI, ISIM_KOK değildir — hâl/iyelik/yapım eki almamalı.

    ("miler" burada YOK: EK.KISI.Z.3C ile EK.COGUL yüzeyce aynıdır (-lAr),
    tıpkı "öğrenciler"in hem çoğul hem 3. çoğul ek-fiil okunması gibi —
    bu gerçek bir belirsizlik, engellenecek bir şey değil.)
    """
    for kelime in ("minin", "milik", "mimiz"):
        okumalar = kelimeyi_cozumle(kelime).okumalar
        assert not any(o.kok == "mi" and o.tur == "Ques" for o in okumalar), kelime


# --- Ek yüzeyi --------------------------------------------------------------


@pytest.mark.parametrize(
    "arketip,govde,beklenen",
    [
        ("Iyor", "gel", "iyor"),
        ("Iyor", "yaz", "ıyor"),
        ("Iyor", "gör", "üyor"),
        ("+yAcAk", "gel", "ecek"),
        ("+yAcAk", "ara", "yacak"),
        ("(I)r", "gel", "ir"),
        ("(I)r", "oku", "r"),
        ("(A)r", "at", "ar"),
        ("(I)n", "oku", "n"),
        ("(I)n", "gel", "in"),
        ("mAdAn", "gel", "meden"),
    ],
)
def test_fiil_ek_yuzeyleri(arketip, govde, beklenen):
    assert ek_yuzeyi_coz(arketip, govde).yuzey == beklenen
