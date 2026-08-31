"""isim_soylu.py — İsim Soylu Sözcükler bağlamsal tür ayrımı testleri.

Bilinçli olarak çözülmeyen (None dönen) durumlar da test edilir — bir
kelimenin gerçekten belirsiz kalması, kodun eksik olduğu anlamına gelmez.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from isim_soylu import kelime_turunu_sec, sozcuklere_ayir  # noqa: E402


def _tur(cumle: str, indeks: int) -> str | None:
    sozcukler = sozcuklere_ayir(cumle)
    sonuc = kelime_turunu_sec(sozcukler, indeks)
    return sonuc.tur if sonuc else None


def test_isaret_sifati_isim_izliyorsa():
    assert _tur("Bu kitabı okudum.", 0) == "Det"
    assert _tur("O ev güzel.", 0) == "Det"
    assert _tur("Şu masayı getir.", 0) == "Det"


def test_isaret_zamiri_isim_izlemiyorsa():
    assert _tur("O geldi.", 0) == "Pron"


def test_cekimli_zamir_bicimleri():
    assert _tur("Bunu okudum.", 0) == "Pron"
    assert _tur("Onu gördüm.", 0) == "Pron"
    assert _tur("Kime söyledin?", 0) == "Pron"


def test_belgisiz_sifat_isim_izliyorsa():
    assert _tur("Bazı öğrenciler geç kaldı.", 0) == "Det"
    assert _tur("Her öğrenci geldi.", 0) == "Det"


def test_belgisiz_zamir_isim_izlemiyorsa():
    assert _tur("Bazılarını tanımıyorum.", 0) is None  # "bazıları" zaten ek'li
    assert _tur("Herkes geldi.", 0) == "Pron"


def test_soru_sifati_adj_okumali():
    # "hangi"/"kaç" motorun sözlüğünde Det değil Adj+Pron/Adj+Verb olarak
    # kayıtlı — mekanizma bunu da yakalamalı.
    assert _tur("Hangi kitabı okudun?", 0) == "Adj"
    assert _tur("Kaç kişi geldi?", 0) == "Adj"
    assert _tur("Kaç tane istersin?", 0) == "Adj"


def test_soru_zamiri_isim_izlemiyorsa():
    assert _tur("Hangisini seçtin?", 0) is None  # "hangisi" zaten ek'li, tek okuma degil


def test_edat_onceki_yonelme_halinde():
    assert _tur("Ona karşı çok naziktim.", 1) == "Postp"
    assert _tur("Sana doğru koştu.", 1) == "Postp"


def test_sifat_kullanimi_isim_izliyorsa():
    assert _tur("Karşı evde kim oturuyor?", 0) == "Adj"


def test_bilinmeyen_bir_zorlanmiyor():
    """'bir' sayı mı belgisizlik sıfatı mı — bilinçli, çözülmeyen belirsizlik
    (bkz. docs/decisions.md §9, isim_coz.py'deki karanlık/keçi gerilimiyle aynı sınıf)."""
    assert _tur("Bir kitap okudum.", 0) is None
    assert _tur("Bir gün gelecek.", 0) is None


def test_ile_edat_baglac_zorlanmiyor():
    """'ile' edat mı bağlaç mı — 'yerine ve konabiliyor mu' testi tam
    sözdizimi çözümlemesi gerektirir, bilerek çözülmüyor."""
    assert _tur("Arkadaşları ile yemeğe gitti.", 1) is None
    assert _tur("Şiir ile hikaye okumayı sever.", 1) is None


def test_cozulemeyen_kelime_none_doner():
    assert kelime_turunu_sec(["zzxyqwabc"], 0) is None
