"""Türetim şelalesi testleri.

Her kural için pozitif **ve** negatif örnek zorunludur (docs/decisions.md §6). Negatifi
olmayan kural, v1'in yaptığı gibi sessizce yanlış pozitif üretir.

Ayrıca kural sırasını sabitleyen testler var: sıra keyfî değil, sözlükteki
gerçek köklerin (kayıt, tıp) zorunlu kıldığı bir düzen.
"""

import pytest

from bitig.cozumleyici import kelimeyi_cozumle
from bitig.morfotaktik import graf
from bitig.turetim import ek_yuzeyi_coz
from bitig.sozluk.girdi import Oznitelik


def olaylar(kelime: str) -> set[str]:
    """Kelimenin tüm okumalarında doğan kural kimlikleri."""
    return {olay.kural_id for olay in kelimeyi_cozumle(kelime).olaylar}


def tek_okuma(kelime: str, kural_id: str):
    """Verilen kuralı üreten ilk olayı döner. Kanıt denetimleri için."""
    for okuma in kelimeyi_cozumle(kelime).okumalar:
        for olay in okuma.olaylar:
            if olay.kural_id == kural_id:
                return olay
    raise AssertionError(f"{kelime!r} için {kural_id} olayı yok")


# --- Ek yüzeyinin çözülmesi -------------------------------------------------


@pytest.mark.parametrize(
    "arketip,govde,beklenen",
    [
        ("lAr", "kitap", "lar"),
        ("lAr", "ev", "ler"),
        ("+yI", "kitap", "ı"),  # ünsüzden sonra kaynaştırma yok
        ("+yI", "masa", "yı"),  # ünlüden sonra y girer
        ("+yA", "masa", "ya"),
        ("+sI", "ev", "i"),
        ("+sI", "masa", "sı"),
        ("(I)m", "kitap", "ım"),  # ünsüzden sonra yardımcı ünlü
        ("(I)m", "masa", "m"),  # ünlüden sonra yok
        ("(I)mIz", "kitap", "ımız"),  # ikinci I, birincinin ünlüsüne uyar
        ("(I)mIz", "göz", "ümüz"),
        ("DA", "ev", "de"),
        ("DA", "kitap", "ta"),  # benzeşme
        ("DAn", "ağaç", "tan"),
        ("+nIn", "masa", "nın"),
        ("+nIn", "ev", "in"),
    ],
)
def test_ek_yuzeyi_coz(arketip, govde, beklenen):
    assert ek_yuzeyi_coz(arketip, govde).yuzey == beklenen


def test_ters_uyum_ek_unlusunu_cevirir():
    """saat → saati (saatı değil). InverseHarmony kökün ünlüsünü değil,
    ekin uyacağı sınıfı tersine çevirir."""
    duz = ek_yuzeyi_coz("+yI", "saat")
    ters = ek_yuzeyi_coz("+yI", "saat", frozenset({Oznitelik.TERS_UYUM}))
    assert duz.yuzey == "ı"
    assert ters.yuzey == "i"


# --- SES.YUM.01 Ünsüz yumuşaması -------------------------------------------


@pytest.mark.parametrize(
    "kelime", ["kitabı", "ağacı", "kanadı", "çocuğu", "rengi", "kâğıdı", "güdüğü", "kabı"]
)
def test_yumusama_pozitif(kelime):
    assert "SES.YUM.01" in olaylar(kelime)


@pytest.mark.parametrize(
    "kelime,gerekce",
    [
        ("güdük", "ek almamış — v1 buna olay basıyordu"),
        ("kitap", "çıplak kök"),
        ("sepeti", "NoVoicing"),
        ("diyeti", "NoVoicing"),
        ("niyeti", "NoVoicing"),
        ("saati", "NoVoicing + InverseHarmony"),
        ("topu", "tek heceli"),
        ("kitapta", "ek ünsüzle başlıyor, koşul yok"),
        ("kitaplarım", "araya çoğul girdi, gövde artık kök değil"),
    ],
)
def test_yumusama_negatif(kelime, gerekce):
    assert "SES.YUM.01" not in olaylar(kelime), gerekce


def test_yumusama_kaniti():
    olay = tek_okuma("kitabı", "SES.YUM.01")
    assert (olay.kanit.once, olay.kanit.sonra) == ("p", "b")
    assert olay.kanit.konum == 4
    assert olay.kanit.govde == "kitap"
    assert olay.kanit.tetikleyen_ek == "ı"
    assert olay.kaynak == "turetim"


def test_nk_yumusamasi_g_verir_g_yumusagi_degil():
    olay = tek_okuma("rengi", "SES.YUM.01")
    assert (olay.kanit.once, olay.kanit.sonra) == ("k", "g")


# --- SES.UD.01 Ünlü düşmesi -------------------------------------------------


@pytest.mark.parametrize(
    "kelime", ["burnu", "ağzı", "gönlü", "boynu", "alnı", "karnı", "oğlu", "şehri", "hapsi"]
)
def test_unlu_dusmesi_pozitif(kelime):
    assert "SES.UD.01" in olaylar(kelime)


@pytest.mark.parametrize(
    "kelime,gerekce",
    [
        ("burun", "ek almamış"),
        ("burunlar", "ek ünsüzle başlıyor"),
        ("burunlarım", "araya çoğul girdi, gövde artık kök değil"),
        ("kitabı", "LastVowelDrop özniteliği yok"),
    ],
)
def test_unlu_dusmesi_negatif(kelime, gerekce):
    assert "SES.UD.01" not in olaylar(kelime), gerekce


def test_hapsi_uyumu_ozgun_koke_gore_cozer():
    """Ayırt edici vaka. `hapis` uyuma aykırı bir alıntı (a...i).

    Uyum düşmüş gövdeye (`haps`, son ünlü `a`) göre çözülseydi "hapsı" çıkardı.
    Özgün köke (`hapis`, son ünlü `i`) göre çözüldüğü için "hapsi" doğru üretilir.
    """
    assert "SES.UD.01" in olaylar("hapsi")
    assert kelimeyi_cozumle("hapsı").cozumlenemedi


def test_unlu_dusmesi_kaniti():
    olay = tek_okuma("burnu", "SES.UD.01")
    assert olay.kanit.once == "u"
    assert olay.kanit.sonra == ""  # düşme: sonrası yok
    assert olay.kanit.konum == 3
    assert olay.kanit.govde == "burun"


# --- SES.UT.01 Ünsüz türemesi ----------------------------------------------


@pytest.mark.parametrize("kelime", ["hakkı", "affı", "hissi", "sırrı", "zannı", "haddi"])
def test_ikizlesme_pozitif(kelime):
    assert "SES.UT.01" in olaylar(kelime)


@pytest.mark.parametrize("kelime,gerekce", [("hak", "ek yok"), ("haklar", "ünsüzle başlayan ek")])
def test_ikizlesme_negatif(kelime, gerekce):
    assert "SES.UT.01" not in olaylar(kelime), gerekce


def test_ikizlesme_ek_yuzeyine_sizmaz():
    """hak + -ı → hakkı. Ek "ı"dır, "kı" değil.

    Ek yüzeyi dizgi diliminden (`yuzey[len(govde):]`) çıkarılsaydı ikizleşen
    ses eke yazılırdı. Bu yüzden `uygula()` ek yüzeyini ayrıca döndürür.
    """
    okuma = next(o for o in kelimeyi_cozumle("hakkı").okumalar)
    assert okuma.ekler == ("ı",)


# --- SES.UND.01 Ünsüz düşmesi ------------------------------------------------
#
# 2026-08-06: osym-tyt-turkce-sorular.txt'deki gerçek OGM Materyal sorusundan
# bulundu. Yalnızca çıkmış soruyla doğrulanan 4 kök işaretli (tyt_override.json)
# — bunun genel bir fonolojik kural mı yoksa kapalı bir liste mi olduğu
# ölçülmedi, bu yüzden dar tutuldu.


@pytest.mark.parametrize(
    "kelime,kok", [("ufacık", "ufak"), ("küçücük", "küçük"), ("alçacık", "alçak")]
)
def test_unsuz_dusmesi_pozitif(kelime, kok):
    assert "SES.UND.01" in olaylar(kelime)
    kokler = {o.kok for o in kelimeyi_cozumle(kelime).okumalar}
    assert kok in kokler


@pytest.mark.parametrize(
    "kelime,gerekce",
    [
        ("yavrucak", "'yavru' ünlüyle bitiyor, düşecek ünsüz yok"),
        ("kitapçık", "'kitap' SonUnsuzDuser taşımıyor"),
        ("ufaktan", "ek küçültme eki değil, dusurur_unsuz tetiklenmez"),
        ("ufak", "ek yok"),
    ],
)
def test_unsuz_dusmesi_negatif(kelime, gerekce):
    assert "SES.UND.01" not in olaylar(kelime), gerekce


def test_ufacik_hem_sozlukte_hem_turetimde():
    """'ufacık' sözlükte de bağımsız bir girdi olarak durur (çok yaygın sözcük).
    Motor ikisini de döner: sözlük okuması (olaysız) ve türetim okuması
    (SES.UND.01) — belirsizlik atılmaz."""
    sonuc = kelimeyi_cozumle("ufacık")
    kokler = {o.kok for o in sonuc.okumalar}
    assert kokler == {"ufacık", "ufak"}
    assert sonuc.olayda_belirsiz


# --- Kural sırası -----------------------------------------------------------


def test_yumusama_ikizlesmeden_once():
    """tıp → (yumuşama) tıb → (ikizleşme) tıbb → tıbbı.
    Sıra tersine dönseydi "tıppı" gibi bir gövde üretilirdi."""
    assert olaylar("tıbbı") == {"SES.YUM.01", "SES.UT.01"}
    okuma = next(o for o in kelimeyi_cozumle("tıbbı").okumalar)
    assert okuma.turetim_izi == ("tıp", "tıbbı")


def test_unlu_dusmesi_yumusamadan_once():
    """kayıt → (düşme) kayt → (yumuşama) kayd → kaydı."""
    assert olaylar("kaydı") >= {"SES.UD.01", "SES.YUM.01"}


# --- SES.KAY.01 Kaynaştırma -------------------------------------------------


@pytest.mark.parametrize("kelime", ["kapısı", "masaya", "arabası", "kapıyı", "çarşambaya"])
def test_kaynastirma_pozitif(kelime):
    assert "SES.KAY.01" in olaylar(kelime)


@pytest.mark.parametrize("kelime", ["evi", "eve", "gözü", "kitabı"])
def test_kaynastirma_negatif(kelime):
    assert "SES.KAY.01" not in olaylar(kelime)


# --- SES.BEN.01 Ünsüz benzeşmesi -------------------------------------------


@pytest.mark.parametrize("kelime", ["kitapta", "ağaçtan", "çiçekten", "sokakta", "saatte"])
def test_benzesme_pozitif(kelime):
    assert "SES.BEN.01" in olaylar(kelime)


@pytest.mark.parametrize("kelime", ["evde", "evden", "masada", "yolda", "kitaplarda"])
def test_benzesme_negatif(kelime):
    assert "SES.BEN.01" not in olaylar(kelime)


def test_benzesme_kaniti():
    olay = tek_okuma("kitapta", "SES.BEN.01")
    assert (olay.kanit.once, olay.kanit.sonra) == ("d", "t")


# --- Belirsizlik ------------------------------------------------------------


def test_belirsizlik_korunur():
    """"kitabı" hem belirtme hâli hem 3. tekil iyelik okunabilir. İkisi de döner."""
    sonuc = kelimeyi_cozumle("kitabı")
    assert sonuc.belirsiz
    kimlikler = {o.ek_kimlikleri for o in sonuc.okumalar}
    assert ("EK.HAL.BEL",) in kimlikler
    assert ("EK.IYELIK.3T",) in kimlikler


def test_gercek_kok_belirsizligi():
    """"masada" = masa+da veya masat+a. Motor ikisini de döner; bağlamsız
    ayrım yapılamaz — API'nin cümle seviyesinde olmasının sebebi budur."""
    kokler = {o.kok for o in kelimeyi_cozumle("masada").okumalar}
    assert {"masa", "masat"} <= kokler


# --- Belirsizliğin iki türü -------------------------------------------------


def test_zararsiz_belirsizlik_kesin_olay_uretir():
    """`kitabı` iki okunur (belirtme / iyelik) ama ikisi de yumuşama üretir.

    Bağlamı çözen katman yanlış okumayı seçse bile ses olayı doğru kalır;
    dolayısıyla bu olay bağlamsız güvenle söylenebilir.
    """
    sonuc = kelimeyi_cozumle("kitabı")
    assert sonuc.belirsiz
    assert not sonuc.olayda_belirsiz
    assert sonuc.kesin_olaylar == {"SES.YUM.01"}


def test_tehlikeli_belirsizlik_isaretlenir():
    """`masada` = masa+da (olay yok) veya masat+a (yumuşama).

    Okumalar olaylarda ayrıştığı için doğru cevap bağlama bağlıdır. Motor bunu
    gizlemez: `kesin_olaylar` boş kalır ve `olayda_belirsiz` işaretlenir.
    Otomatik soru üretimi bu maddeyi kullanamaz.
    """
    sonuc = kelimeyi_cozumle("masada")
    assert sonuc.olayda_belirsiz
    assert sonuc.kesin_olaylar == frozenset()
    assert sonuc.olasi_olaylar == {"SES.YUM.01"}


def test_belirsiz_olmayan_kelimede_kesin_esittir_olasi():
    sonuc = kelimeyi_cozumle("kitapta")
    assert not sonuc.belirsiz
    assert sonuc.kesin_olaylar == sonuc.olasi_olaylar == {"SES.BEN.01"}


def test_cozumlenemeyen_kelimede_olay_kumeleri_bos():
    sonuc = kelimeyi_cozumle("zzzqqq")
    assert sonuc.cozumlenemedi
    assert sonuc.kesin_olaylar == frozenset()
    assert sonuc.olasi_olaylar == frozenset()
    assert not sonuc.olayda_belirsiz


# --- Zarflarda aitlik eki (-ki) ----------------------------------------------
#
# 2026-08-06/07: `harness.kapsam`'ı gerçek ÖSYM metnine (osym-tyt-turkce-
# sorular.txt) karşı çalıştırınca bulundu. "Adv" türü çıkışsız `DEGISMEZ`
# durumundaydı; "sonraki", "yarınki" gibi çok yaygın kelimeler hiç
# çözülemiyordu. Kendi dar durumuna (`ZARF_KOK`) taşındı — Soru ekiyle
# (`SORU_EKI_SONRASI`) aynı desen: tam ISIM_KOK değil, yalnızca `-ki` alır.


@pytest.mark.parametrize("kelime,kok", [("sonraki", "sonra"), ("yarınki", "yarın")])
def test_zarfta_aitlik_eki_cozumleniyor(kelime, kok):
    okumalar = kelimeyi_cozumle(kelime).okumalar
    assert any(o.kok == kok and o.tur == "Adv" and "EK.AITLIK" in o.ek_kimlikleri for o in okumalar)


def test_zarf_kok_isim_cekimi_almaz():
    """ZARF_KOK, ISIM_KOK değildir — hâl/iyelik/çoğul eki almamalı."""
    for kelime in ("sonrada", "sonranın", "sonralar"):
        okumalar = kelimeyi_cozumle(kelime).okumalar
        assert not any(o.kok == "sonra" and o.tur == "Adv" for o in okumalar), kelime


# --- Kesme işareti (özel ad + ek) --------------------------------------------
#
# 2026-08-07: Tamlamalar için gerçek ÖSYM sorusu (Türkiye'nin başkenti) test
# edilirken bulundu. `kelimeyi_cozumle` yalnızca `fonetik.kucult()` uyguluyordu
# (büyük→küçük harf); kesme işaretini hiç çıkarmıyordu. Üretici kesme işaretini
# ASLA üretmez (saf yazım kuralı, fonetik olay değil) — bu yüzden "Türkiye'nin"
# hedefi hiçbir üretilmiş yüzeyle tam eşleşmiyordu: `COZULEMEDI`. Muhtemelen bu
# oturumdaki her kapsam ölçümünü sessizce aşağı çekiyordu (özel ad + ek son
# derece yaygın bir kalıp).


@pytest.mark.parametrize(
    "kelime,kok",
    [
        ("Türkiye'nin", "türkiye"),
        ("Ankara'da", "ankara"),
        ("İstanbul'da", "istanbul"),
        ("Ali'nin", "ali"),
    ],
)
def test_kesme_isaretli_ozel_ad_cozumleniyor(kelime, kok):
    okumalar = kelimeyi_cozumle(kelime).okumalar
    assert okumalar
    assert any(o.kok == kok for o in okumalar)


def test_kesme_isareti_orijinal_yazimda_kalir():
    """Eşleştirme hedefinden çıkar ama `kelime` alanı özgün yazımı korur."""
    sonuc = kelimeyi_cozumle("Türkiye'nin")
    assert sonuc.kelime == "Türkiye'nin"


# --- Fiilden isim (-IcI) — 2026-08-07 motor hatası düzeltmesi ---------------
#
# `EK.YAPIM.ICI`nin arketipi "(I)cI" idi ("yalnızca gövde ünsüzle bitiyorsa
# görünen yardımcı ünlü" sözdizimi) ama bu ek TAM TERSİNE, ÜNLÜYLE biten
# gövdede kaynaştırma-y'ye ihtiyaç duyuyor (oku+YUcu, izle+Yici) — doğrusu
# "+yIcI" (EK.SIFATFIIL.AN'daki "+yAn" ile aynı sözdizimi). Eski hâliyle
# "oku"+"-ıcı" hiç kaynaştırma eklemeden "okucu" üretiyordu (yanlış, doğrusu
# okuyucu) — bu, Türkçenin en üretken eklerinden biri olduğu için (okuyucu,
# yazıcı, satıcı, izleyici, düzenleyici, taşıyıcı, koruyucu... hepsi) geniş
# çaplı bir kapsam boşluğuydu, `harness.kapsam` gerçek/temiz metinde bulundu.


@pytest.mark.parametrize(
    "kelime,kok",
    [
        ("okuyucu", "oku"),  # ünlüyle biten gövde — kaynaştırma-y gerekir
        ("izleyici", "izle"),
        ("belirleyici", "belirle"),
        ("dinleyicinin", "dinle"),
        ("taşıyıcısı", "taşı"),
        ("koruyucu", "koru"),
        ("yazıcı", "yaz"),  # ünsüzle biten gövde — kaynaştırma-y görünmez
        ("satıcı", "sat"),
    ],
)
def test_fiilden_isim_ici_cozumleniyor(kelime, kok):
    kokler = {o.kok for o in kelimeyi_cozumle(kelime).okumalar}
    assert kok in kokler


def test_fiilden_isim_ici_unsuzle_bitende_kaynastirma_yok():
    """Ünsüzle biten gövdede (yaz) kaynaştırma-y GÖRÜNMEMELİ — sahte
    "yazyıcı" gibi bir biçim üretilmemeli, yalnızca ünlü-final gövdelerde
    kaynaştırma eklenir."""
    assert kelimeyi_cozumle("yazyıcı").cozumlenemedi


# --- Graf bütünlüğü ---------------------------------------------------------


def test_graf_yuklenir_ve_durumlari_tutarli():
    g = graf()
    assert g.bitebilir_mi(g.baslangic("Noun"))  # çıplak kök geçerli sözcük
    assert g.bitebilir_mi(g.baslangic("Verb"))  # çıplak fiil kökü = 2. tekil emir
    for durum, ekler in g.gecisler.items():
        for ek in ekler:
            assert ek.hedef in g.bitebilir or g.ekler(ek.hedef), f"{ek.kimlik} çıkmaz"
