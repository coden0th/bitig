"""Anlatım bozukluğu tespiti — Faz 2, madde 2 (kelime-listesi kısmı).

Anlatım bozukluğunun çoğu alt türü (mantık hatası, anlam belirsizliği, deyim
yanlışlığı...) saf anlamsal/mantıksal muhakeme gerektirir — model işi, `baglam.py`
deseniyle ayrı ele alınacak. Ama birkaç alt tür **hiç model gerektirmeden**,
sözcük eş-oluşumu (co-occurrence) taramasıyla yakalanabiliyor; bu modül yalnızca
onları kapsar:

    ÇELİŞEN_SÖZCÜKLER        kesinlik + belirsizlik bildiren sözcük aynı cümlede
    YAKLAŞIKLIK_TEKRARI      "yaklaşık"/"kadar"/"civarında" gibi iki (veya daha
                             fazla) yaklaşıklık sözcüğü aynı anda
    EŞANLAMLI_ÇİFT           aynı anlamı taşıyan iki sözcük (biri genelde
                             yabancı kökenli) birlikte kullanılmış
    DEĞİŞMEZ_NİTELİK         ismin doğası gereği zaten taşıdığı bir niteliği
                             yineleyen bitişik sıfat ("beyaz kar")
    GEREKSİZ_ÇOĞUL           çoğulu zaten ima eden bir belirsizlik sıfatından
                             ("birçok", "birkaç") sonra ayrıca çoğul ek
    FIILIMSI_TUR_UYUMSUZ     nesne görevindeki (iyelik+hâl taşıyan) paralel
                             fiilimsi öbekleri farklı türden ("gelişini,
                             kaldığını anlattı" — isim-fiil + sıfat-fiil karışık)

Veri `veri/anlatim_kelime_listeleri.json`'da durur — kodda gömülü liste yok
(CLAUDE.md §8). Listeler bilinçli olarak dar: yalnızca gerçek bir soruyla
doğrulanmış kayıt eklenir (`veri/tyt_override.json` ile aynı disiplin).
`FIILIMSI_TUR_UYUMSUZ` istisnadır — veri değil, doğrudan `ek_kimlikleri`
kimliğine bakar, ayrı bir sözcük listesi gerekmez.

**Denenip eklenmeyenler (2026-08-07):** tamlama türü uyumsuzluğu (Q6/Q14/Q28,
"askerî ve sağlık aracı") ve çatı uyumsuzluğu (Q32, "uygulanır ve öğrenirdi")
motorun mevcut ek-kimlik altyapısıyla test edildi ama **güvenilir** bulunmadı
— ikisi de isim_coz.py'deki `karanlık`/`keçi` geriliminin aynısına düşüyor:
çoğu aday kelime (kişi/belgisiz/klasik/askerî/sağlık gibi) hem isim hem sıfat
okunuyor, "olası" mantık yanlış pozitif, "kesin" mantık yanlış negatif
üretiyor. Çatı uyumsuzluğunda ayrıca "eğlenmek" gibi sözlükleşmiş (artık
üretken olmayan) `-In` kökleri canlı edilgen/dönüşlü ile ayırt edilemiyor —
negatif kontrolde yanlış pozitif üretti (bkz. docs/decisions.md §6). Yüklem/kişi
uyumsuzluğu (Q20, "Ben babamı sen ustanı unutma") 2. tekil emrin motorumuzda
hiç işaretlenmemesi yüzünden (bkz. docs/decisions.md §9 "kapatılmayan tek kalem")
zaten mekanize edilemiyordu. Üçü de eklenmedi.

Motorun (`bitig/`) parçası değildir — burada tespit edilen olaylar morfolojik
değil, sözcük eş-oluşumu tabanlıdır. Yine de `bitig.cozumleyici`'yi salt-okunur
kullanır ve API'sini cümle seviyesinde çağırır (`cozumle()` her taramada bir
kez): eşanlamlı/değişmez-nitelik kontrolleri kelimenin KÖKÜNE bakar (yüzey
biçim değil — "seferinde" kökü "sefer"dir), gereksiz-çoğul kontrolü ise
`EK.COGUL` kimliğine bakar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from bitig import fonetik
from bitig.cozumleyici import cozumle
from bitig.sozlesme import KelimeSonucu

VERI_YOLU = Path(__file__).resolve().parent / "veri" / "anlatim_kelime_listeleri.json"

#: `isim_coz.py`'deki pencere fikriyle aynı: aday ile hedef arasına kaç kelime
#: girebilir. Gereksiz-çoğul ve değişmez-nitelik bitişikliğe yakın olmalı;
#: geniş bir pencere ilgisiz eşleşmeler üretir.
_PENCERE = 2


@lru_cache(maxsize=1)
def _veri() -> dict:
    return json.loads(VERI_YOLU.read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class AnlatimBulgusu:
    """Kelime-listesi taramasının tek bir eşleşmesi."""

    tur: str
    kanit: tuple[str, ...]


def _kok_kumesi(kelime: KelimeSonucu) -> set[str]:
    """Bir kelimenin taşıyabileceği tüm kökler (olası mantık — herhangi bir
    okumada eşleşme yeterli). Çözümlenemeyen kelimede yüzeyin kendisi
    (küçültülmüş) tek adaydır."""
    kokler = {ok.kok for ok in kelime.okumalar}
    return kokler or {fonetik.kucult(kelime.kelime)}


def celisen_sozcuk_var_mi(cumle: str) -> AnlatimBulgusu | None:
    veri = _veri()["celisen_kategoriler"]
    yuzeyler = {fonetik.kucult(k.kelime) for k in cozumle(cumle)}
    kesinlik = yuzeyler & set(veri["kesinlik"]["sozcukler"])
    belirsizlik = yuzeyler & set(veri["belirsizlik"]["sozcukler"])
    if kesinlik and belirsizlik:
        return AnlatimBulgusu("CELISEN_SOZCUKLER", (next(iter(kesinlik)), next(iter(belirsizlik))))
    return None


def yaklasiklik_tekrari_var_mi(cumle: str) -> AnlatimBulgusu | None:
    sozcukler = set(_veri()["yaklasiklik_sozcukleri"]["sozcukler"])
    eslesen = [fonetik.kucult(k.kelime) for k in cozumle(cumle) if fonetik.kucult(k.kelime) in sozcukler]
    if len(eslesen) >= 2:
        return AnlatimBulgusu("YAKLASIKLIK_TEKRARI", tuple(eslesen[:2]))
    return None


def esanlamli_cift_var_mi(cumle: str) -> AnlatimBulgusu | None:
    kelimeler = list(cozumle(cumle))
    tum_kokler: set[str] = set().union(*(_kok_kumesi(k) for k in kelimeler)) if kelimeler else set()
    for kayit in _veri()["esanlamli_ciftler"]:
        a, b = kayit["cift"]
        if a in tum_kokler and b in tum_kokler:
            return AnlatimBulgusu("ESANLAMLI_CIFT", (a, b))
    return None


def degismez_nitelik_tekrari_var_mi(cumle: str) -> AnlatimBulgusu | None:
    kayitlar = {k["isim"]: k["sifat"] for k in _veri()["degismez_nitelikler"]["kayitlar"]}
    kelimeler = list(cozumle(cumle))
    for i in range(len(kelimeler) - 1):
        sifat_kokleri = _kok_kumesi(kelimeler[i])
        isim_kokleri = _kok_kumesi(kelimeler[i + 1])
        for isim_koku in isim_kokleri:
            if isim_koku in kayitlar and kayitlar[isim_koku] in sifat_kokleri:
                return AnlatimBulgusu("DEGISMEZ_NITELIK", (kelimeler[i].kelime, kelimeler[i + 1].kelime))
    return None


def gereksiz_cogul_var_mi(cumle: str) -> AnlatimBulgusu | None:
    sifatlar = set(_veri()["cogul_ima_eden_belirsizlik_sifatlari"]["sozcukler"])
    kelimeler = list(cozumle(cumle))
    for i, kelime in enumerate(kelimeler):
        if fonetik.kucult(kelime.kelime) not in sifatlar:
            continue
        for j in range(i + 1, min(i + 1 + _PENCERE, len(kelimeler))):
            if any("EK.COGUL" in ok.ek_kimlikleri for ok in kelimeler[j].okumalar):
                return AnlatimBulgusu("GEREKSIZ_COGUL", (kelime.kelime, kelimeler[j].kelime))
    return None


#: `EK.ISIMFIIL.*`/`EK.SIFATFIIL.*` yalnızca İYELİK + HÂL de taşıyorsa nesne
#: (veya benzeri nominal öge) görevindedir — zarf-fiil (`EK.ZARFFIIL`) ya da
#: çıplak sıfat-fiil (bir ismi niteleyen, "yürüyen çocuk" gibi) bu şartı hiç
#: sağlamaz, bu yüzden yanlışlıkla eşleşmez (bkz. Q27 seçenek A/D negatif
#: kontrolü — "kalkıp", "yürüyen" burada hiç görünmüyor).
def fiilimsi_tur_uyumsuz_mu(cumle: str) -> AnlatimBulgusu | None:
    turler: dict[str, str] = {}
    for kelime in cozumle(cumle):
        for ok in kelime.okumalar:
            has_iyelik = any(e.startswith("EK.IYELIK") for e in ok.ek_kimlikleri)
            has_hal = any(e.startswith("EK.HAL") for e in ok.ek_kimlikleri)
            if not (has_iyelik and has_hal):
                continue
            if any(e.startswith("EK.ISIMFIIL") for e in ok.ek_kimlikleri):
                turler[kelime.kelime] = "ISIMFIIL"
            elif any(e.startswith("EK.SIFATFIIL") for e in ok.ek_kimlikleri):
                turler[kelime.kelime] = "SIFATFIIL"
    if len(set(turler.values())) > 1:
        kelimeler = tuple(turler)
        return AnlatimBulgusu("FIILIMSI_TUR_UYUMSUZ", kelimeler)
    return None


#: Tüm kelime-listesi taramaları, tek bir yerden çalıştırılabilir sırayla.
TARAMALAR = (
    celisen_sozcuk_var_mi,
    yaklasiklik_tekrari_var_mi,
    esanlamli_cift_var_mi,
    degismez_nitelik_tekrari_var_mi,
    gereksiz_cogul_var_mi,
    fiilimsi_tur_uyumsuz_mu,
)


def tara(cumle: str) -> tuple[AnlatimBulgusu, ...]:
    """Cümleyi tüm kelime-listesi taramalarından geçirir, bulunanları döner."""
    return tuple(b for tarama in TARAMALAR if (b := tarama(cumle)) is not None)
