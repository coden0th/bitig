"""`yazim.py` testleri — morfolojik yazım denetimi (Track A) + TDK önbellek
okuma (Track B). İkisi de ağ gerektirmez: Track B'nin ağ tarafı
`harness/tdk_senkron.py`'de, ayrı ve elle çalıştırılır. Toplu doğrulama
(`altin/ad_cekimi.jsonl` + `fiil_cekimi.jsonl`den türetilen 100 vaka, %100
isabet) `harness/yazim_dogrula.py`'nin işi; burada yalnızca her kuraldan
elle seçilmiş, okunabilir birer örnek + sınır durumlar test edilir.
"""

from __future__ import annotations

import pytest

from yazim import denetle, tdk_gecerli_mi


@pytest.mark.parametrize(
    "aday,duzeltme,kural_id",
    [
        ("kitapı", "kitabı", "SES.YUM.01"),  # yumuşama (p→b)
        ("renki", "rengi", "SES.YUM.01"),  # yumuşama, "nk" istisnası (k→g)
        ("fikiri", "fikri", "SES.UD.01"),  # ünlü düşmesi
        ("hisi", "hissi", "SES.UT.01"),  # ünsüz türemesi (ikizleşme)
        ("masaa", "masaya", "SES.KAY.01"),  # kaynaştırma
        ("kitapda", "kitapta", "SES.BEN.01"),  # ünsüz benzeşmesi
        ("başlayor", "başlıyor", "SES.DAR.01"),  # ünlü daralması (düz uyum)
        ("söyleyor", "söylüyor", "SES.DAR.01"),  # ünlü daralması (yuvarlak uyum)
        ("ufakcık", "ufacık", "SES.UND.01"),  # ünsüz düşmesi
    ],
)
def test_denetle_pozitif(aday, duzeltme, kural_id):
    bulgular = denetle(aday)
    assert any(b.duzeltme == duzeltme and b.kural_id == kural_id for b in bulgular)


def test_denetle_dogru_yazimda_bos_doner():
    """Zaten çözülüyorsa (doğru yazılmışsa) aramaya hiç girmez."""
    assert denetle("kitabı") == ()
    assert denetle("masaya") == ()


def test_denetle_tesadufen_gecerli_okuma_yakalayamaz():
    """Bilinen, dürüst bir sınır: 'kapı' hem 'kap'+'ı' (hata, doğrusu kabı)
    hem de bağımsız bir kelime (door) — motor ikincisini bulup aramayı hiç
    başlatmaz. Bu bir hata değil; context olmadan ayırt edilemez (Faz 2 işi)."""
    assert denetle("kapı") == ()


def test_denetle_birden_fazla_bulgu_dondurebilir():
    """'kapıa' hem 'kapıya' (kapı+'ya') hem 'kapına' (kapı+'na') olarak
    çözülebiliyor — belirsizlik atılmaz, ikisi de döner."""
    bulgular = denetle("kapıa")
    duzeltmeler = {b.duzeltme for b in bulgular}
    assert "kapıya" in duzeltmeler
    assert "kapına" in duzeltmeler


def test_denetle_alakasiz_kelimede_bulgu_uretmez():
    assert denetle("masa") == ()
    assert denetle("xyzabc") == ()


# --- Track B: TDK önbelleği (ağsız okuma) -----------------------------------


def test_tdk_gecerli_kelime():
    durum = tdk_gecerli_mi("kapı")
    assert durum is not None
    assert durum.gecerli is True
    assert durum.yonlendirme is None


def test_tdk_gecersiz_kelime():
    durum = tdk_gecerli_mi("restorant")
    assert durum is not None
    assert durum.gecerli is False


def test_tdk_yonlendirmeli_kelime():
    """'çiğ börek' TDK'de bulunuyor ama ilk anlamı 'çi börek'e işaret ediyor
    — yönlendirme bilgi notudur, `gecerli` yine de True kalmalı."""
    durum = tdk_gecerli_mi("çiğ börek")
    assert durum is not None
    assert durum.gecerli is True
    assert durum.yonlendirme == "çi börek"


def test_tdk_onbellekte_olmayan_kelime_none_doner():
    """Önbellekte hiç bulunmayan bir kelime 'geçersiz' ile karıştırılmamalı
    — None, 'bilinmiyor' demektir."""
    assert tdk_gecerli_mi("bu-kelime-hicbir-onbellekte-olmamali-xyz") is None
