"""Üretici ve gidiş-dönüş bütünlüğü testleri.

`harness/gidis_donus.py` tam sözlüğü tarar ve dakikalar sürer. Buradaki testler
onun küçük, hızlı ve **kalıcı** hâlidir: taramanın bulduğu hata sınıfları bir
daha sessizce geri gelmesin diye.

Gidiş-dönüş ölçütü etikete dayanmaz — motor kendi ürettiğini geri okuyabiliyor
mu diye sorar. Bu yüzden altın kümenin göremediği kör noktaları yakalar; iki
gerçek hata (özel adlar, g→ğ ters çevirimi) tam olarak böyle bulundu.
"""

import pytest

from bitig.cozumleyici import kelimeyi_cozumle
from bitig.sozluk.depo import varsayilan_sozluk
from bitig.uretici import uret


def _girdi(kok: str, tur: str | None = None):
    girdiler = varsayilan_sozluk().ara(kok)
    assert girdiler, f"sözlükte yok: {kok}"
    if tur:
        girdiler = [g for g in girdiler if g.tur == tur]
        assert girdiler, f"{kok} için {tur} girdisi yok"
    return girdiler[0]


def gidis_donus(kok: str, tur: str | None = None, azami_ek: int = 2) -> list[str]:
    """Kökten üretilen her yüzeyi geri çözümler; kurtarılamayanları döner."""
    girdi = _girdi(kok, tur)
    kayiplar = []
    for uretim in uret(girdi, azami_ek=azami_ek, tavan=80):
        sonuc = kelimeyi_cozumle(uretim.yuzey)
        kurtarildi = any(
            o.kok == uretim.kok
            and o.tur == uretim.tur
            and o.ek_kimlikleri == uretim.ek_kimlikleri
            and frozenset(x.kural_id for x in o.olaylar) == uretim.kural_kimlikleri
            for o in sonuc.okumalar
        )
        if not kurtarildi:
            kayiplar.append(f"{uretim.yuzey} ({'+'.join(uretim.ek_kimlikleri) or '∅'})")
    return kayiplar


# --- Üretici ---------------------------------------------------------------


def test_ciplak_kok_de_bir_uretimdir():
    uretimler = list(uret(_girdi("kitap"), azami_ek=1))
    assert any(u.yuzey == "kitap" and not u.ek_kimlikleri for u in uretimler)


def test_uretici_beklenen_bicimleri_uretir():
    yuzeyler = {u.yuzey for u in uret(_girdi("kitap"), azami_ek=1)}
    assert {"kitap", "kitaplar", "kitabı", "kitaba", "kitapta", "kitaptan"} <= yuzeyler


def test_uretici_fiil_cekimi():
    yuzeyler = {u.yuzey for u in uret(_girdi("gel", "Verb"), azami_ek=1)}
    assert {"gel", "geldi", "geliyor", "gelecek", "gelmiş", "gelir"} <= yuzeyler


def test_uretici_olaylari_tasir():
    uretimler = {u.yuzey: u for u in uret(_girdi("kitap"), azami_ek=1)}
    assert uretimler["kitabı"].kural_kimlikleri == {"SES.YUM.01"}
    assert uretimler["kitapta"].kural_kimlikleri == {"SES.BEN.01"}
    assert uretimler["kitaplar"].kural_kimlikleri == frozenset()


def test_uretici_tavani_uyar():
    assert len(list(uret(_girdi("kitap"), azami_ek=3, tavan=10))) == 10


# --- Gidiş-dönüş bütünlüğü --------------------------------------------------


@pytest.mark.parametrize(
    "kok,tur",
    [
        ("kitap", None),  # yumuşama
        ("burun", None),  # ünlü düşmesi
        ("hak", None),  # ikizleşme
        ("kapı", None),  # kaynaştırma
        ("saat", None),  # ters uyum
        ("renk", None),  # nk istisnası
        ("tıp", None),  # yumuşama + ikizleşme birlikte
        ("gel", "Verb"),
        ("git", "Verb"),  # fiilde yumuşama
        ("başla", "Verb"),  # daralma
        ("de", "Verb"),  # kök daralması
        ("ye", "Verb"),
        ("kavur", "Verb"),  # fiilde ünlü düşmesi
        ("oku", "Verb"),
    ],
)
def test_gidis_donus_bozulmadan_geri_okunur(kok, tur):
    kayiplar = gidis_donus(kok, tur)
    assert not kayiplar, f"{kok}: geri okunamayan {len(kayiplar)} biçim → {kayiplar[:5]}"


def test_ozel_adlar_cozumlenir():
    """Sözlükte özel adlar büyük harfle durur, çözümleyici metni küçültür.
    Kök normalleştirilmezse 26 binden fazla özel ad hiç bulunamaz —
    gidiş-dönüş taramasının ilk turda yakaladığı hata buydu."""
    assert not kelimeyi_cozumle("Susurluk").cozumlenemedi
    assert not kelimeyi_cozumle("susurlukta").cozumlenemedi
    assert not kelimeyi_cozumle("Ankara").cozumlenemedi


def test_og_ile_biten_kokler_cozumlenir():
    """`zoolog` → `zooloğu` (g→ğ). Ters çevirim tablosunda `g→ğ` satırı
    eksikti; ileri şelale doğru üretiyor ama çözümleyici geri okuyamıyordu."""
    sonuc = kelimeyi_cozumle("zooloğu")
    assert "zoolog" in {o.kok for o in sonuc.okumalar}
    assert "SES.YUM.01" in {x.kural_id for x in sonuc.olaylar}
    assert "katalog" in {o.kok for o in kelimeyi_cozumle("kataloğa").okumalar}
