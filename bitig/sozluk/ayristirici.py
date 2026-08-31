"""Zemberek `.dict` satır grameri.

Satır biçimi:

    kelime
    kelime [P:BirincilTür,İkincilTür; A:Öznitelik1,Öznitelik2; Index:1; Pr:telaffuz]

Köşeli parantezli bölüm tamamen isteğe bağlıdır — `master-dictionary.dict`'in
28.920 satırının 18.625'i çıplaktır. Çıplak satır eksik kayıt değildir: türü ve
öznitelikleri `oznitelik.cikar()` tarafından çıkarımla belirlenir.
"""

from __future__ import annotations

from bitig import fonetik
from bitig.sozluk.girdi import IkincilTur, SozlukGirdisi, Tur

#: Mastar ekleri. Bir girişi fiil yapan ve kökten atılan bölüm.
MASTAR_EKLERI = ("mak", "mek")

#: Yorum satırı önekleri.
YORUM_ONEKLERI = ("##", "#")


class AyristirmaHatasi(ValueError):
    """Satır grameri bozuksa atılır. Sessizce yutulmaz — veri hatası görünür olmalı."""


def _alanlari_ayikla(govde: str) -> dict[str, str]:
    """`P:Noun; A:Voicing; Index:1` biçimindeki bölümü sözlüğe çevirir."""
    alanlar: dict[str, str] = {}
    for parca in govde.split(";"):
        parca = parca.strip()
        if not parca:
            continue
        if ":" not in parca:
            raise AyristirmaHatasi(f"anahtar:değer bekleniyordu: {parca!r}")
        anahtar, _, deger = parca.partition(":")
        # Dosyada `Pr:` ve `pr:` birlikte geçiyor; anahtar büyük/küçük duyarsız.
        alanlar[anahtar.strip().lower()] = deger.strip()
    return alanlar


def _listele(deger: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in deger.split(",") if p.strip())


def _fiil_mi(kelime: str) -> bool:
    """Mastar ekiyle biten küçük harfli sözcük fiildir.

    Zemberek `TurkishDictionaryLoader` ölçütü: küçük harfli, 3 karakterden uzun,
    "mak"/"mek" ile biter. Büyük harf denetimi Türkçe'ye duyarlı yapılır.
    """
    return (
        len(kelime) > 3
        and kelime.endswith(MASTAR_EKLERI)
        and fonetik.kucult(kelime) == kelime
    )


def ayristir(satir: str) -> SozlukGirdisi | None:
    """Tek satırı çözümler. Boş satır ve yorum için None döner.

    Öznitelik *çıkarımı* burada yapılmaz — bu fonksiyon yalnızca dosyada açıkça
    yazılanı okur. Çıkarım `oznitelik.cikar()` işidir; ikisinin ayrı durması
    çıkarım kurallarını sözlük dosyasından bağımsız test edilebilir kılar.
    """
    satir = satir.strip()
    if not satir or satir.startswith(YORUM_ONEKLERI):
        return None

    # Alan bloğu " [" ile başlar ve satır sonundaki "]" ile biter. Ayırıcıyı
    # sondan aramak gerekir: sözlükte kelimenin kendisi "[" olan bir noktalama
    # girdisi vardır (`[ [P:Punc]`), baştan arama onu bozar.
    if satir.endswith("]") and " [" in satir:
        kelime, _, kalan = satir.rpartition(" [")
        kelime = kelime.strip()
        alanlar = _alanlari_ayikla(kalan.removesuffix("]"))
    elif satir.endswith("]") and satir.startswith("["):
        raise AyristirmaHatasi(f"kelime alanı boş: {satir!r}")
    else:
        if "[" in satir or satir.endswith("]"):
            raise AyristirmaHatasi(f"bozuk alan bloğu: {satir!r}")
        kelime = satir
        alanlar = {}

    if not kelime:
        raise AyristirmaHatasi(f"kelime alanı boş: {satir!r}")

    turler = _listele(alanlar.get("p", ""))
    birincil = turler[0] if turler else None
    ikincil = turler[1] if len(turler) > 1 else None

    # Tür yazılmamışsa çıkarılır: mastar ekliyse fiil, değilse isim.
    if birincil is None:
        birincil = Tur.FIIL if _fiil_mi(kelime) else Tur.ISIM
    if ikincil is None and kelime and fonetik.kucult(kelime) != kelime:
        ikincil = IkincilTur.OZEL_ISIM

    # Fiillerde türetim mastarsız kökten başlar: "demek" → "de"
    kok = kelime[:-3] if birincil == Tur.FIIL and kelime.endswith(MASTAR_EKLERI) else kelime

    # Kök küçük harfe çevrilir: büyük harf bir YAZIM kuralıdır, morfolojik bir
    # özellik değil. Sözlükte özel adlar büyük harfle durur ("Susurluk"), oysa
    # çözümleyici metni küçülterek çalışır; normalleştirilmezse bu girdiler hiç
    # bulunamaz. Özgün yazılış `yuzey` alanında korunur, `ikincil_tur` de zaten
    # bu satırdan ÖNCE büyük harften çıkarılmıştır.
    kok = fonetik.kucult(kok)

    sira_ham = alanlar.get("index", "0")
    try:
        sira = int(sira_ham)
    except ValueError as hata:
        raise AyristirmaHatasi(f"Index sayı değil: {sira_ham!r}") from hata

    return SozlukGirdisi(
        yuzey=kelime,
        kok=kok,
        tur=birincil,
        ikincil_tur=ikincil,
        oznitelikler=frozenset(_listele(alanlar.get("a", ""))),
        sira=sira,
        telaffuz=alanlar.get("pr"),
        bilesik_kokler=tuple(alanlar["roots"].split("-")) if "roots" in alanlar else (),
    )
