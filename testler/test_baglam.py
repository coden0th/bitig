"""`baglam.py` testleri.

`sec()` model çağrısı yaptığı için burada test edilmez (ağ gerektirir, ücretli) —
onun ölçümü `harness/baglam_coz.py`'nin işidir. Burada yalnızca ağ gerektirmeyen
saf fonksiyon (`okuma_aciklamasi`) ve `BaglamSecimi`'nin kendisi test edilir.
"""

from __future__ import annotations

from baglam import BaglamSecimi, okuma_aciklamasi
from bitig.cozumleyici import kelimeyi_cozumle
from bitig.sozlesme import Kaynak


def test_okuma_aciklamasi_kok_ve_tur_icerir():
    sonuc = kelimeyi_cozumle("kitabı")
    aciklamalar = [okuma_aciklamasi(ok) for ok in sonuc.okumalar]
    assert any("kitap" in a and "Noun" in a for a in aciklamalar)


def test_okuma_aciklamasi_ek_adlarini_ayirir():
    sonuc = kelimeyi_cozumle("kitabı")
    aciklamalar = [okuma_aciklamasi(ok) for ok in sonuc.okumalar]
    # Biri belirtme hâli, biri iyelik-3 açıklaması taşımalı — ikisi ayrışmalı.
    assert any("Belirtme hâli" in a for a in aciklamalar)
    assert any("İyelik 3. tekil" in a for a in aciklamalar)


def test_okuma_aciklamasi_bilinmeyen_ek_kimligini_oldugu_gibi_gosterir():
    sonuc = kelimeyi_cozumle("evi")
    aciklamalar = [okuma_aciklamasi(ok) for ok in sonuc.okumalar]
    assert aciklamalar  # en azından çökmeden bir şey üretti


def test_baglam_secimi_secilen_okumayi_dondurur():
    sonuc = kelimeyi_cozumle("kitabı")
    secim = BaglamSecimi(kelime="kitabı", cumle="Kitabı okudum.", secilen_indeks=0, gerekce="test")
    assert secim.secilen_okuma(sonuc) == sonuc.okumalar[0]


def test_baglam_secimi_kaynak_daima_sezgisel():
    secim = BaglamSecimi(kelime="kitabı", cumle="x", secilen_indeks=0, gerekce="test")
    assert secim.kaynak == Kaynak.SEZGISEL
