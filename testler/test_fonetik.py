"""Fonetik katmanı testleri.

Bu katman motorun tabanı; buradaki bir hata üstteki her kuralı sessizce bozar.
Özellikle Türkçe küçük/büyük harf dönüşümü v1'in bilinen hatalarındandı.
"""

import pytest

from bitig import fonetik as f


# --- Alfabe tutarlılığı -----------------------------------------------------


def test_kucuk_buyuk_harf_tablolari_hizali():
    assert len(f.KUCUK_HARFLER) == len(f.BUYUK_HARFLER)


def test_turk_alfabesi_29_harf_arti_sapkalilar():
    # 29 harf + â, î, û
    assert len(f.KUCUK_HARFLER) == 32


def test_kucult_buyut_birbirinin_tersi():
    for harf in f.KUCUK_HARFLER:
        assert f.kucult(f.buyut(harf)) == harf


# --- Türkçe'ye duyarlı harf dönüşümü (v1'in hatası) -------------------------


@pytest.mark.parametrize(
    "buyuk,beklenen",
    [
        ("IRMAK", "ırmak"),  # I → ı  (Python .lower() "i" verirdi)
        ("İSTANBUL", "istanbul"),  # İ → i  (Python .lower() "i̇" verirdi)
        ("ÇIĞLIK", "çığlık"),
        ("ÖĞÜT", "öğüt"),
        ("ŞAHAP", "şahap"),
    ],
)
def test_kucult_turkceye_duyarli(buyuk, beklenen):
    assert f.kucult(buyuk) == beklenen


@pytest.mark.parametrize(
    "kucuk,beklenen",
    [
        ("ırmak", "IRMAK"),
        ("istanbul", "İSTANBUL"),
        ("iğne", "İĞNE"),
    ],
)
def test_buyut_turkceye_duyarli(kucuk, beklenen):
    assert f.buyut(kucuk) == beklenen


def test_kucult_python_lower_ile_ayrisiyor():
    # Bu ayrışma modülün varlık sebebi. Aynılaşırlarsa tablo bozulmuş demektir.
    assert f.kucult("IĞDIR") != "IĞDIR".lower()


# --- Ünlü sınıflandırması ---------------------------------------------------


def test_sapkali_unluler_unludur():
    for harf in "âîû":
        assert f.unlu_mu(harf)


def test_sapkali_unlulerin_uyum_sinifi():
    # Zemberek TurkishAlphabet tablosu: â kalın, î ince, û ince+yuvarlak
    assert not f.ince_mi("â")
    assert f.ince_mi("î")
    assert f.ince_mi("û")
    assert f.yuvarlak_mi("û")
    assert not f.yuvarlak_mi("î")


def test_unlu_siniflari_ortusmuyor():
    assert f.INCE_UNLULER | f.KALIN_UNLULER == f.UNLULER
    assert not (f.INCE_UNLULER & f.KALIN_UNLULER)
    assert f.YUVARLAK_UNLULER | f.DUZ_UNLULER == f.UNLULER
    assert not (f.YUVARLAK_UNLULER & f.DUZ_UNLULER)


def test_otumsuz_unsuzler_fistikcisahap():
    assert f.OTUMSUZ_UNSUZLER == set("fıstıkçışahap") - f.UNLULER


# --- Sözcük düzeyi ----------------------------------------------------------


@pytest.mark.parametrize(
    "kelime,sayi",
    [("kitap", 2), ("top", 1), ("a", 1), ("saat", 2), ("kâğıt", 2), ("psikoloji", 4)],
)
def test_unlu_sayisi(kelime, sayi):
    assert f.unlu_sayisi(kelime) == sayi


@pytest.mark.parametrize(
    "kelime,unlu",
    [("kitap", "a"), ("burun", "u"), ("saat", "a"), ("mahkûm", "û"), ("kğ", None)],
)
def test_son_unlu(kelime, unlu):
    assert f.son_unlu(kelime) == unlu


# --- Ses değişimleri --------------------------------------------------------


@pytest.mark.parametrize(
    "kelime,beklenen",
    [
        ("kitap", "kitab"),  # p → b
        ("ağaç", "ağac"),  # ç → c
        ("kanat", "kanad"),  # t → d
        ("çocuk", "çocuğ"),  # k → ğ
        ("renk", "reng"),  # nk istisnası: k → g, ğ değil
        ("ahenk", "aheng"),
    ],
)
def test_yumusat(kelime, beklenen):
    assert f.yumusat(kelime) == beklenen


@pytest.mark.parametrize("kelime", ["masa", "ev", "kalem", "yol"])
def test_yumusayamayan_none_doner(kelime):
    assert f.yumusat(kelime) is None


def test_sertlestir():
    assert f.sertlestir("d") == "t"
    assert f.sertlestir("c") == "ç"
    assert f.sertlestir("l") == "l"  # sertleşemez, aynen döner


# --- Ünlü uyumu -------------------------------------------------------------


@pytest.mark.parametrize(
    "onceki,beklenen",
    [("a", "a"), ("ı", "a"), ("o", "a"), ("u", "a"), ("e", "e"), ("i", "e"), ("ö", "e"), ("ü", "e")],
)
def test_uyumla_a(onceki, beklenen):
    assert f.uyumla_a(onceki) == beklenen


@pytest.mark.parametrize(
    "onceki,beklenen",
    [
        ("a", "ı"),  # kitap → kitabı
        ("ı", "ı"),  # kız → kızı
        ("e", "i"),  # ev → evi
        ("i", "i"),  # dil → dili
        ("o", "u"),  # yol → yolu
        ("u", "u"),  # burun → burnu
        ("ö", "ü"),  # göz → gözü
        ("ü", "ü"),  # gül → gülü
    ],
)
def test_uyumla_i(onceki, beklenen):
    assert f.uyumla_i(onceki) == beklenen


def test_uyumla_sapkalilar():
    """Şapkalı ünlülerin uyum davranışı — harf tablosunun doğrudan sonucu.

    Bunlar ilkel (harf düzeyi) davranışlardır. Sözcük düzeyindeki tartışmalı
    vakalar (mahkûmu / mahkûmü gibi) buraya değil altın kümeye yazılır; gerekirse
    veri tarafında `InverseHarmony` ile düzeltilir — kodda değil.
    """
    assert f.uyumla_i("â") == "ı"  # kâğıt → kâğıdı
    assert f.uyumla_i("û") == "ü"  # û ince+yuvarlak
    assert f.uyumla_a("î") == "e"
