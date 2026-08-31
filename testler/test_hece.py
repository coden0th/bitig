"""`hece.py` testleri — hece bölme + ünlü uyumu.

Ağ gerektirmez, sözlük gerektirmez — saf fonolojik kurallar (MEB + TDK'nin
resmî yazım kılavuzu, bkz. `hece.py` modül docstring'i). Gerçek bir ÖSYM/MEB
soru kümesiyle henüz ölçülmedi (`harness/`de bir araç yok, bu tür soru TYT'de
son derece nadir) — bu yalnızca kuralın kendisinin doğru uygulandığını
doğrular.
"""

from __future__ import annotations

import pytest

from hece import (
    UyumSonucu,
    buyuk_unlu_uyumu,
    cumleyi_hecele,
    hece_bol,
    kucuk_unlu_uyumu,
)


class TestHeceBol:
    @pytest.mark.parametrize(
        "kelime, beklenen",
        [
            ("kalem", ("ka", "lem")),
            ("araba", ("a", "ra", "ba")),
            ("mektup", ("mek", "tup")),
            ("Türkçe", ("Türk", "çe")),
            ("kalpler", ("kalp", "ler")),
            ("aile", ("a", "i", "le")),
            ("okul", ("o", "kul")),
            ("kitaplık", ("ki", "tap", "lık")),
            ("öğretmen", ("öğ", "ret", "men")),
            ("sokaklar", ("so", "kak", "lar")),
        ],
    )
    def test_coklu_heceli_kelimeler(self, kelime, beklenen):
        assert hece_bol(kelime) == beklenen

    @pytest.mark.parametrize("kelime", ["kalp", "tren", "spor", "kral", "ev"])
    def test_tek_heceli_kelimeler_bolunmez(self, kelime):
        assert hece_bol(kelime) == (kelime,)

    def test_bos_dizgi(self):
        assert hece_bol("") == ()

    def test_hece_sayisi_unlu_sayisiyla_esit(self):
        from bitig import fonetik

        for kelime in ["kalem", "araba", "mektup", "kitaplık", "üniversite"]:
            assert len(hece_bol(kelime)) == fonetik.unlu_sayisi(kelime)


class TestKesmeIsaretiIleHeceBol:
    """TDK: 'Kesme işareti satır sonuna geldiğinde yalnız kesme işareti
    kullanılır' — kendi örnekleri (Edirne'nin, Ankara'dan) doğrultusunda."""

    @pytest.mark.parametrize(
        "kelime, beklenen",
        [
            ("Türkiye'nin", ("Tür", "ki", "ye'", "nin")),
            ("Ankara'dan", ("An", "ka", "ra'", "dan")),
            ("Edirne'nin", ("E", "dir", "ne'", "nin")),
            ("Ali'nin", ("A", "li'", "nin")),
            ("İstanbul'un", ("İs", "tan", "bul'", "un")),
        ],
    )
    def test_kesme_isaretli_govde_ek(self, kelime, beklenen):
        assert hece_bol(kelime) == beklenen

    def test_tipografik_kesme_isareti_de_calisir(self):
        assert hece_bol("Ankara’dan") == ("An", "ka", "ra’", "dan")

    def test_cumleyi_hecele(self):
        sonuc = cumleyi_hecele("Türkiye'nin başkenti Ankara'dır.")
        assert sonuc == [
            ("Türkiye'nin", ("Tür", "ki", "ye'", "nin")),
            ("başkenti", ("baş", "ken", "ti")),
            ("Ankara'dır", ("An", "ka", "ra'", "dır")),
        ]

    def test_buyuk_unlu_uyumu_kesme_isaretli_kelimede_calisir(self):
        # apostrof ünlü olmadığı için zaten filtrelenir, ayrı bir kod yolu gerekmez
        sonuc = buyuk_unlu_uyumu("Türkiye'nin")
        assert sonuc.uyuyor is True

    def test_kucuk_unlu_uyumu_kesme_isaretli_kelimede_calisir(self):
        # gerçek bulgu: "Türkiye" (Türk + Arapça kökenli -iye eki) küçük ünlü
        # uyumuna uymuyor (ü→i, yuvarlaktan sonra düz-dar) — kalem/kitap ile
        # aynı sınıf alıntı/özel-ad istisnası, motor hatası değil
        sonuc = kucuk_unlu_uyumu("Türkiye'nin")
        assert sonuc.uyuyor is False
        assert sonuc.kanit == ("ü", "i")


class TestBuyukUnluUyumu:
    @pytest.mark.parametrize(
        "kelime",
        ["sokaklar", "gözlük", "evler", "üzüntü", "araba", "ev"],
    )
    def test_uyumlu_kelimeler(self, kelime):
        sonuc = buyuk_unlu_uyumu(kelime)
        assert sonuc.uyuyor is True
        assert sonuc.kanit is None

    def test_kalem_uymuyor(self):
        # bilinen alıntı-kelime istisnası — bkz. modül docstring'i
        sonuc = buyuk_unlu_uyumu("kalem")
        assert sonuc.uyuyor is False
        assert sonuc.kanit == ("a", "e")

    def test_kitap_uymuyor(self):
        sonuc = buyuk_unlu_uyumu("kitap")
        assert sonuc.uyuyor is False
        assert sonuc.kanit == ("i", "a")

    def test_tek_unluluk_kelime_otomatik_uyumlu(self):
        assert buyuk_unlu_uyumu("ev") == UyumSonucu(uyuyor=True, kanit=None)


class TestKucukUnluUyumu:
    @pytest.mark.parametrize(
        "kelime",
        ["masa", "kuzu", "okul", "büyük", "kalem", "sokak", "orman"],
    )
    def test_uyumlu_kelimeler(self, kelime):
        sonuc = kucuk_unlu_uyumu(kelime)
        assert sonuc.uyuyor is True
        assert sonuc.kanit is None

    def test_komik_uymuyor(self):
        # klasik TYT örneği: yuvarlak "o"dan sonra düz-dar "i" gelemez
        sonuc = kucuk_unlu_uyumu("komik")
        assert sonuc.uyuyor is False
        assert sonuc.kanit == ("o", "i")

    def test_doktor_uymuyor(self):
        sonuc = kucuk_unlu_uyumu("doktor")
        assert sonuc.uyuyor is False
        assert sonuc.kanit == ("o", "o")
