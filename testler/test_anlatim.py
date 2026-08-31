"""`anlatim.py` testleri — kelime-listesi tabanlı anlatım bozukluğu taraması.

Ağ gerektirmez (modelsiz mekanizma). Her pozitif vaka gerçek bir ÖSYM/MEB
sorusundan gelir (bkz. `veri/anlatim_kelime_listeleri.json`'daki `gerekce`
alanları); ölçümü `harness/anlatim_coz.py` yapar.
"""

from __future__ import annotations

import pytest

from anlatim import (
    celisen_sozcuk_var_mi,
    degismez_nitelik_tekrari_var_mi,
    esanlamli_cift_var_mi,
    fiilimsi_tur_uyumsuz_mu,
    gereksiz_cogul_var_mi,
    tara,
    yaklasiklik_tekrari_var_mi,
)


@pytest.mark.parametrize(
    "cumle",
    [
        "Fırtına kuşkusuz balıkçıların işini zorlaştıran en önemli engel sanırım.",
        "Mert Bey de açılışa kesin katılacak mıymış, öğrenebilirim belki.",
    ],
)
def test_celisen_sozcuk_pozitif(cumle):
    assert celisen_sozcuk_var_mi(cumle) is not None


@pytest.mark.parametrize(
    "cumle",
    [
        "Oraya gidince muhakkak velinizle de görüşmek isterim.",
        "Üç gün arka arkaya kar etkili olacak gibi.",
    ],
)
def test_celisen_sozcuk_negatif(cumle):
    assert celisen_sozcuk_var_mi(cumle) is None


def test_yaklasiklik_tekrari_pozitif():
    bulgu = yaklasiklik_tekrari_var_mi(
        "Serengeti Milli Parkı'nda yaklaşık bin kadar su aygırının yaşadığı düşünülüyor."
    )
    assert bulgu is not None
    assert bulgu.tur == "YAKLASIKLIK_TEKRARI"


def test_yaklasiklik_tekrari_negatif():
    assert yaklasiklik_tekrari_var_mi("Parkta yaklaşık bin su aygırı yaşıyor.") is None


@pytest.mark.parametrize(
    "cumle,cift",
    [
        (
            "Kütahya'nın soğuğunun ve neminin çok meşhur olduğunu söylüyordu her seferinde her kezinde.",
            ("sefer", "kez"),
        ),
        (
            "Edebiyatın terbiye ve güzel ahlakla ilgili ve alakalı kavramları işlemesi gerekir.",
            ("ilgili", "alaka"),
        ),
        (
            "Suyun sanki bir rüyayı yorumlar gibi akışı taşlara yapışıyor.",
            ("sanki", "gibi"),
        ),
    ],
)
def test_esanlamli_cift_pozitif(cumle, cift):
    bulgu = esanlamli_cift_var_mi(cumle)
    assert bulgu is not None
    assert set(bulgu.kanit) == set(cift)


def test_esanlamli_cift_negatif_tek_taraf():
    """Çiftin yalnızca bir tarafı geçiyorsa eşleşme olmamalı."""
    assert esanlamli_cift_var_mi("Çocuklarınıza alaka göstererek onların dünyasına girin.") is None


def test_degismez_nitelik_pozitif():
    bulgu = degismez_nitelik_tekrari_var_mi("Beyaz kar taneleri usul usul süzülüyordu.")
    assert bulgu is not None
    assert bulgu.tur == "DEGISMEZ_NITELIK"


def test_degismez_nitelik_negatif():
    assert degismez_nitelik_tekrari_var_mi("Kar taneleri usul usul süzülüyordu.") is None


def test_gereksiz_cogul_pozitif():
    bulgu = gereksiz_cogul_var_mi("Dergilerde birçok türlerde metne yer verilir.")
    assert bulgu is not None
    assert bulgu.tur == "GEREKSIZ_COGUL"


def test_gereksiz_cogul_negatif_tekil():
    assert gereksiz_cogul_var_mi("Dergilerde birçok türde metne yer verilir.") is None


def test_gereksiz_cogul_negatif_nicelik_sifati_yok():
    assert gereksiz_cogul_var_mi("Dergilerde çeşitli türlerde metne yer verilir.") is None


def test_fiilimsi_tur_uyumsuzlugu_pozitif():
    bulgu = fiilimsi_tur_uyumsuz_mu("Dün sınıfta size gelişini, sizde kaldığını anlattı durdu.")
    assert bulgu is not None
    assert bulgu.tur == "FIILIMSI_TUR_UYUMSUZ"
    assert set(bulgu.kanit) == {"gelişini", "kaldığını"}


@pytest.mark.parametrize(
    "cumle",
    [
        "Erkenden kalkıp yola çıkmamız gerektiğini size bir kere daha hatırlatmak isterim.",
        "Karşı kaldırımda yürüyen çocukların keyfine diyecek yoktu.",
        "Evin bir an önce boyanarak sahibine teslim edilmesi gerekiyor.",
    ],
)
def test_fiilimsi_tur_uyumsuzlugu_negatif(cumle):
    """Zarf-fiil (kalkıp) ve nesne görevinde olmayan sıfat-fiil (yürüyen,
    bir ismi niteliyor) iyelik+hâl taşımadığından hiç aday sayılmamalı."""
    assert fiilimsi_tur_uyumsuz_mu(cumle) is None


def test_tara_temiz_cumlede_hicbir_bulgu_uretmez():
    assert tara("Bugün hava çok güzeldi, dışarı çıkıp yürüyüş yaptık.") == ()


def test_tara_birden_fazla_bulgu_dondurebilir():
    """Aynı cümlede hem çelişen sözcük hem yaklaşıklık tekrarı olabilir —
    `tara` hiçbirini gizlemeden hepsini döner (motorun 'belirsizlik atılmaz'
    ilkesiyle aynı ruh, docs/decisions.md §3)."""
    bulgular = tara(
        "Yaklaşık bin kadar davetli kuşkusuz geldi sanırım."
    )
    turler = {b.tur for b in bulgular}
    assert "YAKLASIKLIK_TEKRARI" in turler
    assert "CELISEN_SOZCUKLER" in turler
