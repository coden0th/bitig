"""`noktalama.py` testleri — ağ gerektirmez, tamamen deterministik.

Ölçümü `harness/noktalama_coz.py` yapar (`altin/noktalama_sorulari.jsonl`,
3/3, gerçek ÖSYM/MEB kaynağından + TDK'nin resmi kural sayfasıyla doğrulandı).
"""

from __future__ import annotations

from noktalama import kesme_yanlis_iyelik_bul, sart_sonrasi_virgul_bul, tara, zarffiil_ardisik_virgul_eksik_bul


def test_sart_sonrasi_virgul_pozitif_fiil_kipi():
    bulgular = sart_sonrasi_virgul_bul(
        "Deneyimler bize ne kadar akılla ısrar edersek, ilhamdan o kadar uzaklaştığımızı söylüyor."
    )
    assert len(bulgular) == 1
    assert bulgular[0].tur == "SART_SONRASI_VIRGUL"
    assert bulgular[0].kelime == "edersek"


def test_sart_sonrasi_virgul_pozitif_ekfiil_ise():
    bulgular = sart_sonrasi_virgul_bul(
        "Büyük mimarlarımız ise, daima eserlerinin yanı başında birkaç ağacı eksik etmezlerdi."
    )
    assert len(bulgular) == 1
    assert bulgular[0].kelime == "ise"


def test_sart_sonrasi_virgul_istisna_ardisik_sart():
    """İki eş görevli şart cümleciği art arda geldiğinde aradaki virgül
    doğrudur — bulgu üretilmemeli (gerçek bir ÖSYM sorusuyla bulundu)."""
    assert sart_sonrasi_virgul_bul("Hemen o anda kavrayamasak, dile dökemesek de bazı bilgiler geçer aklımızdan.") == ()


def test_sart_sonrasi_virgul_negatif_virgulsuz():
    assert sart_sonrasi_virgul_bul("Eve gelirsek hep birlikte yemek yeriz.") == ()


def test_sart_sonrasi_virgul_negatif_sartsiz_virgul():
    assert (
        sart_sonrasi_virgul_bul(
            "Eski bilgeler, boş bir kamışa dönüşmekten ve sezginin bu kamışların içinden akmasının mümkün olduğundan bahsediyor."
        )
        == ()
    )


def test_tara_tum_taramalari_calistirir():
    bulgular = tara("Şimdi gitmezsek, geç kalacağız.")
    assert any(b.tur == "SART_SONRASI_VIRGUL" for b in bulgular)


# --- kesme işareti + iyelik --------------------------------------------------


def test_kesme_yanlis_iyelik_pozitif():
    """TDK: 'Konya Ovamız'daki' yanlış — 1. çoğul iyelik, kesme olmamalı."""
    bulgular = kesme_yanlis_iyelik_bul("İlkbahar yağışları, Konya Ovamız'daki buğday verimini arttırdı.")
    assert len(bulgular) == 1
    assert bulgular[0].tur == "KESME_YANLIS_IYELIK"
    assert bulgular[0].kelime == "Ovamız'daki"


def test_kesme_yanlis_iyelik_tdk_resmi_ornekleri():
    """tdk.gov.tr'nin kendi örnekleri (Boğaz Köprümüzün, Amik Ovamızın)."""
    assert kesme_yanlis_iyelik_bul("Boğaz Köprümüz'ün güzelliği herkesi etkiledi.") != ()
    assert kesme_yanlis_iyelik_bul("Amik Ovamız'ın bitki örtüsü zengindir.") != ()


def test_kesme_yanlis_iyelik_negatif_3_tekil_iyelik_ilgili_degil():
    """'Boğaz'dan' doğru — iyelik yok, yalnızca hâl eki."""
    assert kesme_yanlis_iyelik_bul("Dünyanın incisi kabul edilen Boğaz'dan görkemli bir gemi geçti.") == ()


def test_kesme_yanlis_iyelik_negatif_sahte_iyelik_okumasi_elenir():
    """'Hanım'a' doğru (kişi adı + unvan + hâl eki) — motorun sahte bir
    'han+ım' (1.tekil iyelik) okuması var ama 'hanım' okumasında hiç iyelik
    yok, kesin mantık bunu doğru eliyor (yanlış pozitif üretilmemeli)."""
    assert kesme_yanlis_iyelik_bul("Elinizdeki dosyaları Ayşe Hanım'a imzalatmayı unutmayın!") == ()


def test_kesme_yanlis_iyelik_negatif_kucuk_harf_atlanir():
    """Büyük harfle başlamayan (özel ad kullanımı olmayan) kelimeler denenmez."""
    assert kesme_yanlis_iyelik_bul("kitabımız'daki bilgiler yanlıştı.") == ()


# --- zarf-fiil ardışıklığı ----------------------------------------------------
#
# NOT: bu tur için altın kümede gerçek bir ÖSYM sorusu YOK. Kaynak cümle gerçek
# (ogm-materyal.txt, Noktalama Q8 seçenek D) ama o sorunun kendisi "hangi virgül
# hiçbir kategoriye örnek değil" diye soruyordu — "hangi virgül eksik" diye değil.
# D'nin orijinal hâli virgülü zaten doğru koymuş, yani negatif kontrol için
# kullanılabilir; pozitif (virgül eksik) durumu göstermek için virgül BİLİNÇLİ
# OLARAK çıkarılmış bir varyant kullanılıyor — bu ÖSYM'nin cevabı değil, bizim
# kurguladığımız bir sınama, öyle etiketlendi.


def test_zarffiil_ardisik_negatif_gercek_cumle_virgulu_dogru():
    """Gerçek kaynak cümle (ogm-materyal.txt Q8-D) virgülü zaten doğru
    koymuş — bulgu üretilmemeli."""
    assert (
        zarffiil_ardisik_virgul_eksik_bul(
            "Bedestenin Konya gibi bir ovada yer alıp, herhangi bir yıkıma maruz kalmadan günümüze kadar ulaşmış olması dikkatimizi çekti."
        )
        == ()
    )


def test_zarffiil_ardisik_pozitif_kurgusal_virgulsuz_varyant():
    """Yukarıdaki gerçek cümlenin virgülü BİLİNÇLİ OLARAK çıkarılmış hâli —
    ÖSYM kaynaklı değil, yalnızca tespiti sınamak için kurgulandı."""
    bulgular = zarffiil_ardisik_virgul_eksik_bul(
        "Bedestenin Konya gibi bir ovada yer alıp herhangi bir yıkıma maruz kalmadan günümüze kadar ulaşmış olması dikkatimizi çekti."
    )
    assert len(bulgular) == 1
    assert bulgular[0].tur == "ZARFFIIL_ARDISIK_VIRGUL_EKSIK"
    assert bulgular[0].kelime == "alıp"


def test_zarffiil_ardisik_negatif_tek_zarffiil():
    """Tek başına bir zarf-fiil (ikincisi yok) bulgu üretmemeli."""
    assert (
        zarffiil_ardisik_virgul_eksik_bul(
            "Tepe'nin yüksek yerine çıkan insanlar, poşet parçasının üzerine oturarak kendilerini aşağı doğru bırakırlar."
        )
        == ()
    )


def test_zarffiil_ardisik_negatif_zarffiilsiz_cumle():
    assert zarffiil_ardisik_virgul_eksik_bul("Gündelik yaşam tüm canlılığı, akışkanlığı ve sıradanlığı ile artmaktadır.") == ()
