"""Türkçe harf ve ses altyapısı.

Motorun en alt katmanı. Üstteki her katman (sözlük, türetim, çözümleyici) buradaki
sınıflandırmalara dayanır, kendi harf tablosunu tutmaz.

Python'un `str.lower()` / `str.upper()` metodları bu modülde bilinçli olarak
kullanılmaz: varsayılan Unicode kuralı "I" → "i" ve "İ" → "i̇" (i + birleşen nokta)
üretir; Türkçe'de ikisi de yanlıştır. `kucult()` / `buyut()` kullanılacak.

Harf sınıflandırması Zemberek `TurkishAlphabet` tablosuyla aynıdır (Apache-2.0,
bkz. NOTICE). Şapkalı harfler dahildir: â kalın, î ince, û ince+yuvarlak.
"""

from __future__ import annotations

# --- Alfabe -----------------------------------------------------------------

KUCUK_HARFLER = "abcçdefgğhıijklmnoöprsştuüvyzâîû"
BUYUK_HARFLER = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZÂÎÛ"

# Türkçe'de bulunmayan ama alıntı sözcüklerde geçen harfler
YABANCI_HARFLER = "qwx"

_KUCULT = str.maketrans(BUYUK_HARFLER + "QWX", KUCUK_HARFLER + YABANCI_HARFLER)
_BUYUT = str.maketrans(KUCUK_HARFLER + YABANCI_HARFLER, BUYUK_HARFLER + "QWX")


def kucult(metin: str) -> str:
    """Türkçe'ye duyarlı küçük harfe çevirim. I→ı, İ→i."""
    return metin.translate(_KUCULT)


def buyut(metin: str) -> str:
    """Türkçe'ye duyarlı büyük harfe çevirim. ı→I, i→İ."""
    return metin.translate(_BUYUT)


# --- Ünlüler ----------------------------------------------------------------

UNLULER = frozenset("aeıioöuüâîû")

#: Ön (ince) ünlüler. Büyük ünlü uyumunu belirler.
INCE_UNLULER = frozenset("eiöüîû")
#: Art (kalın) ünlüler.
KALIN_UNLULER = frozenset("aıouâ")

#: Yuvarlak ünlüler. Küçük ünlü uyumunu belirler.
YUVARLAK_UNLULER = frozenset("oöuüû")
DUZ_UNLULER = frozenset("aeıiâî")

#: Dar ünlüler. `I` arketipinin çözüldüğü küme.
DAR_UNLULER = frozenset("ıiuü")
GENIS_UNLULER = frozenset("aeoö")


# --- Ünsüzler ---------------------------------------------------------------

#: Ötümsüz (sert) ünsüzler — "fıstıkçışahap".
OTUMSUZ_UNSUZLER = frozenset("çfhkpsşt")

#: Sürekli ünsüzler. Sürekli olmayanlar (b c ç d g k p t) süreksiz/patlamalıdır.
SUREKLI_UNSUZLER = frozenset("fğhjlmnrsşvyz")

#: Ünsüz yumuşamasında son sesin aldığı biçim.
#: k→ğ genel kuraldır; "nk" ile biten gövdelerde k→g olur (renk → rengi),
#: bu istisna `yumusat()` içinde gövdeye bakılarak uygulanır.
YUMUSAMA = {"ç": "c", "g": "ğ", "k": "ğ", "p": "b", "t": "d"}

#: Ünsüz sertleşmesinde (benzeşme) son sesin aldığı biçim.
SERTLESME = {"b": "p", "c": "ç", "d": "t", "g": "k", "ğ": "k"}

#: Ötümsüz süreksiz (patlamalı) ünsüzler. Ünsüz yumuşamasının koşulu budur.
#: `g` bu kümede **değildir**: "katalog → kataloğu" gibi vakalar ayrı bir
#: sözcük-sonu kuralıyla ("og") yürür, genel yumuşama kuralıyla değil.
SUREKSIZ_OTUMSUZLER = frozenset("çkpt")

#: Yumuşama haritasında karşılığı olan tüm sesler (`g` dahil).
YUMUSAYABILIR = frozenset(YUMUSAMA)


def unlu_mu(harf: str) -> bool:
    return harf in UNLULER


def unsuz_mu(harf: str) -> bool:
    return harf in KUCUK_HARFLER and harf not in UNLULER


def otumsuz_mu(harf: str) -> bool:
    """Ötümsüz (sert) ünsüz mü? Ünsüz benzeşmesini tetikleyen koşul."""
    return harf in OTUMSUZ_UNSUZLER


def surekli_mi(harf: str) -> bool:
    return harf in SUREKLI_UNSUZLER


def ince_mi(harf: str) -> bool:
    return harf in INCE_UNLULER


def yuvarlak_mi(harf: str) -> bool:
    return harf in YUVARLAK_UNLULER


# --- Sözcük düzeyi sorgular -------------------------------------------------


def unlu_sayisi(kelime: str) -> int:
    """Sözcükteki ünlü sayısı.

    Sözlük öznitelik çıkarımında "tek heceli mi" ölçütü budur; Türkçe'de
    hece sayısı ünlü sayısına eşittir.
    """
    return sum(1 for h in kelime if h in UNLULER)


def son_unlu(kelime: str) -> str | None:
    """Sözcüğün son ünlüsü. Ünlü yoksa None. Ünlü uyumunun dayanağı."""
    for harf in reversed(kelime):
        if harf in UNLULER:
            return harf
    return None


def ilk_unlu(kelime: str) -> str | None:
    for harf in kelime:
        if harf in UNLULER:
            return harf
    return None


def unluyle_bitiyor(kelime: str) -> bool:
    return bool(kelime) and kelime[-1] in UNLULER


def unluyle_basliyor(kelime: str) -> bool:
    return bool(kelime) and kelime[0] in UNLULER


# --- Ses değişimleri --------------------------------------------------------


def yumusat(kelime: str) -> str | None:
    """Sözcüğün son sesini yumuşatır. Yumuşayamıyorsa None döner.

    Bu fonksiyon *koşulu denetlemez* — yumuşamanın gerçekleşip gerçekleşmeyeceği
    kökün `Voicing`/`NoVoicing` özniteliğine bakan türetim katmanının kararıdır.
    Burada yalnızca biçim değişimi yapılır.

        kitap → kitab      ağaç → ağac       renk → reng (nk istisnası)
    """
    if not kelime or kelime[-1] not in YUMUSAMA:
        return None
    # "nk" ile bitenlerde k→g (renk→rengi, ahenk→ahengi), genel kuraldaki k→ğ değil.
    if kelime.endswith("nk"):
        return kelime[:-1] + "g"
    return kelime[:-1] + YUMUSAMA[kelime[-1]]


def son_unluyu_dusur(kelime: str) -> str | None:
    """Son ünlüyü düşürür. Ünlü yoksa None döner.

    `LastVowelDrop` özniteliğinin biçim karşılığı. Düşen ünlü sözcüğün son
    hecesindeki dar ünlüdür, son harf değil:

        burun → burn      ağız → ağz       gönül → gönl
        şehir → şehr      göğüs → göğs     oğul → oğl

    `yumusat()` gibi bu da yalnızca biçim üretir; koşulu türetim katmanı denetler.
    """
    for indeks in range(len(kelime) - 1, -1, -1):
        if kelime[indeks] in UNLULER:
            return kelime[:indeks] + kelime[indeks + 1 :]
    return None


def son_unlu_konumu(kelime: str) -> int:
    """Son ünlünün konumu; ünlü yoksa -1. Kanıttaki `konum` alanı için."""
    for indeks in range(len(kelime) - 1, -1, -1):
        if kelime[indeks] in UNLULER:
            return indeks
    return -1


def sertlestir(harf: str) -> str:
    """Tek sesi sertleştirir (ünsüz benzeşmesi). Sertleşemiyorsa harfi aynen döner."""
    return SERTLESME.get(harf, harf)


# --- Ünlü uyumu -------------------------------------------------------------


#: Kalınlık/incelik ekseninde eşlenik ünlüler. Yuvarlaklık korunur.
_TERS_UNLU = {"a": "e", "e": "a", "ı": "i", "i": "ı", "o": "ö", "ö": "o",
              "u": "ü", "ü": "u", "â": "e", "î": "ı", "û": "u"}


#: Geniş ünlünün dar karşılığı. Kalınlık ve yuvarlaklık korunur.
_DAR_KARSILIK = {"a": "ı", "e": "i", "o": "u", "ö": "ü", "â": "ı"}
#: Dar ünlünün geniş karşılığı — `_DAR_KARSILIK`in tersi, çözümlemede kullanılır.
_GENIS_KARSILIK = {"ı": "a", "i": "e", "u": "o", "ü": "ö"}


def daralt_unlu(unlu: str) -> str | None:
    """Geniş ünlüyü daraltır: a→ı, e→i. Zaten darsa None.

    Ünlü daralmasının biçim karşılığı (de → di, ye → yi).
    """
    return _DAR_KARSILIK.get(unlu)


def genislet_unlu(unlu: str) -> str | None:
    """Dar ünlüyü genişletir: ı→a, i→e. Daralmanın ters çevirimi.

    Yalnızca çözümlemede aday üretmek için kullanılır; ileri türetimde
    böyle bir kural yoktur.
    """
    return _GENIS_KARSILIK.get(unlu)


def unluyu_ters_cevir(unlu: str | None) -> str | None:
    """Ünlüyü karşı kalınlık sınıfına çevirir; yuvarlaklığı korur.

    `InverseHarmony` özniteliğinin karşılığı: alıntı sözcüklerde ek, kökün
    ünlüsüne değil karşıtına uyar. saat → saat-i (saat-ı değil), hâl → hâl-i.
    """
    return _TERS_UNLU.get(unlu) if unlu else unlu


def uyumla_a(onceki_unlu: str | None) -> str:
    """`A` arketipini çözer: geniş-düz ünlü. a / e"""
    if onceki_unlu is None or onceki_unlu in KALIN_UNLULER:
        return "a"
    return "e"


def uyumla_i(onceki_unlu: str | None) -> str:
    """`I` arketipini çözer: dar ünlü. ı / i / u / ü

    Büyük (kalın-ince) ve küçük (düz-yuvarlak) ünlü uyumunun bileşimi.
    """
    if onceki_unlu is None:
        return "ı"
    ince = onceki_unlu in INCE_UNLULER
    yuvarlak = onceki_unlu in YUVARLAK_UNLULER
    if ince:
        return "ü" if yuvarlak else "i"
    return "u" if yuvarlak else "ı"
