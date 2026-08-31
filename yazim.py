"""Morfolojik yazım denetimi — TDK yazım motoru, Track A (Faz 2/3).

Plan hafızada durur (`[[yazim-motoru-plani]]`): yazım hataları İKİ ayrı
problemdir, tek bir bulanık-eşleştirme (fuzzy-match) motoruna indirgenmez.

    A. **Morfolojik** (`denetle`) — bir ses kuralının unutulması: "kitapı"
       (yumuşama unutulmuş, doğrusu "kitabı"). Motor bunu ZATEN bilir;
       yeni bir kural ya da dış bağımlılık gerekmez.
    B. **Sözlüksel/alıntı kelime** (`tdk_gecerli_mi`) — TDK'nin tarihsel
       kararı olan yazımlar (restorant/restoran, çiğ börek/çi börek). Kural
       değil olgudur; `veri/tdk_onbellek.json` (istisna listesi yerine genel
       bir geçerlilik önbelleği, ama aynı disiplin: canlı TDK API çağrısı
       ÇALIŞMA ZAMANINDA asla yapılmaz — üretim bağımlılığı sıfır ilkesi,
       CLAUDE.md §1). Önbellek `harness/tdk_senkron.py` ile (elle, ağ
       gerektirerek) doldurulur/tazelenir; bu modül yalnızca yerel dosyayı
       okur. Bulanık eşleştirme YOK — yalnızca birebir geçerlilik sorulur.

**Mekanizma — motor asla bypass edilmez.** Aday yazım çözülemiyorsa, HER
ses kuralı için "bu kural unutulmuş olabilir" varsayımıyla yapısal düzeltme
adayları üretilir (ör. yumuşamamış ünsüzü yumuşat) — ama bu adaylardan
hangisinin GERÇEKTEN geçerli olduğuna biz karar vermeyiz, motor karar verir:
yalnızca `kelimeyi_cozumle` ile çözülen VE iddia edilen kuralı üreten
adaylar döner. "Tespit değil türetim" ilkesi burada da geçerli — biz kural
tahmin etmiyoruz, üretici doğruluyor.

Belirsizlik atılmaz: birden fazla düzeltme adayı geçerli çıkabilir (farklı
kurallar, farklı konumlar) — hepsi döner, tek bir "en olası" seçilmez.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from bitig.cozumleyici import kelimeyi_cozumle
from bitig.sozlesme import KelimeSonucu

_UNLULER = "aeıioöuüâîû"

#: Yumuşama unutulmuşsa yüzeyde ötümsüz kalır; düzeltme onu ötümlüleştirir.
_YUMUSAMA_TERSI = {"p": "b", "ç": "c", "t": "d", "k": "ğ"}
#: Benzeşme (sertleşme) unutulmuşsa ekin ilk sesi ötümlü kalır; düzeltme sertleştirir.
_BENZESME_TERSI = {"d": "t", "c": "ç", "g": "k"}
#: Daralma unutulmuşsa geniş ünlü (a/e) kalır; düzeltme daraltır. Hedef dar ünlü
#: gövdenin ünlü uyumu sınıfına göre değişir (a→ı/u, e→i/ü — docs/decisions.md §9:
#: "söylüyor" örneğinde uyum daralmış gövdeye göredir, ö→ü yuvarlak eşleşir).
#: Hangi dar ünlünün doğru olduğunu biz seçmeyiz, hepsini deneriz — motor karar verir.
_DARALMA_ADAYLARI = {"a": "ıu", "e": "iü"}
_KAYNASTIRMA_HARFLERI = "ynsş"


@dataclass(frozen=True, slots=True)
class YazimBulgusu:
    """Motorun doğruladığı tek bir düzeltme adayı."""

    aday: str
    duzeltme: str
    kural_id: str


def _yumusama_adaylari(aday: str) -> Iterator[str]:
    for i, harf in enumerate(aday):
        if harf in _YUMUSAMA_TERSI:
            yield aday[:i] + _YUMUSAMA_TERSI[harf] + aday[i + 1 :]
        #: "k" iki hedefe yumuşayabilir: genel kural k→ğ, "nk" istisnası k→g
        #: (renk→rengi, ahenk→ahengi) — bkz. cozumleyici.py _YUMUSAMANIN_TERSI.
        if harf == "k":
            yield aday[:i] + "g" + aday[i + 1 :]


def _unlu_dusmesi_adaylari(aday: str) -> Iterator[str]:
    for i, harf in enumerate(aday):
        if 0 < i < len(aday) - 1 and harf in _UNLULER:
            yield aday[:i] + aday[i + 1 :]


def _ikizlesme_adaylari(aday: str) -> Iterator[str]:
    for i, harf in enumerate(aday):
        if harf.isalpha() and harf not in _UNLULER:
            yield aday[:i] + harf + aday[i:]


def _kaynastirma_adaylari(aday: str) -> Iterator[str]:
    for i in range(1, len(aday)):
        if aday[i - 1] in _UNLULER and aday[i] in _UNLULER:
            for harf in _KAYNASTIRMA_HARFLERI:
                yield aday[:i] + harf + aday[i:]


def _benzesme_adaylari(aday: str) -> Iterator[str]:
    for i, harf in enumerate(aday):
        if harf in _BENZESME_TERSI:
            yield aday[:i] + _BENZESME_TERSI[harf] + aday[i + 1 :]


def _daralma_adaylari(aday: str) -> Iterator[str]:
    for i, harf in enumerate(aday):
        if harf in _DARALMA_ADAYLARI:
            for dar in _DARALMA_ADAYLARI[harf]:
                yield aday[:i] + dar + aday[i + 1 :]


def _unsuz_dusmesi_adaylari(aday: str) -> Iterator[str]:
    for i, harf in enumerate(aday):
        if harf == "k":
            yield aday[:i] + aday[i + 1 :]


#: Kural kimliği → o kural unutulduğunda üretilecek düzeltme adayları.
#: `veri/kural_haritasi.json`'daki 7 kuralın hepsi burada temsil edilir.
_KURAL_URETECLERI = {
    "SES.YUM.01": _yumusama_adaylari,
    "SES.UD.01": _unlu_dusmesi_adaylari,
    "SES.UT.01": _ikizlesme_adaylari,
    "SES.KAY.01": _kaynastirma_adaylari,
    "SES.BEN.01": _benzesme_adaylari,
    "SES.DAR.01": _daralma_adaylari,
    "SES.UND.01": _unsuz_dusmesi_adaylari,
}


def _kural_uretti_mi(sonuc: KelimeSonucu, kural_id: str) -> bool:
    """Olası mantık: en az bir okumada iddia edilen kural varsa yeterli —
    biz zaten belirli bir kuralı doğrulatmaya çalışıyoruz, okumanın kendisi
    tek/çift olması ayrı bir soru."""
    return any(any(olay.kural_id == kural_id for olay in ok.olaylar) for ok in sonuc.okumalar)


def denetle(aday: str) -> tuple[YazimBulgusu, ...]:
    """Aday yazımı denetler.

    Zaten çözülüyorsa boş döner — muhtemelen doğru (ya da en azından motorun
    bildiği başka geçerli bir kelime; bu fonksiyon sözlüksel/anlamsal
    doğruluğu garanti etmez, yalnızca morfolojik tutarlılığı).

    Çözülemiyorsa her kural için düzeltme adayı üretilir; yalnızca motorun
    ÇÖZDÜĞÜ ve iddia edilen kuralı ÜRETTİĞİ adaylar döner.
    """
    if not kelimeyi_cozumle(aday).cozumlenemedi:
        return ()

    bulgular: list[YazimBulgusu] = []
    denenmis: set[tuple[str, str]] = set()
    for kural_id, uretec in _KURAL_URETECLERI.items():
        for duzeltme in uretec(aday):
            if duzeltme == aday or (kural_id, duzeltme) in denenmis:
                continue
            denenmis.add((kural_id, duzeltme))
            sonuc = kelimeyi_cozumle(duzeltme)
            if not sonuc.cozumlenemedi and _kural_uretti_mi(sonuc, kural_id):
                bulgular.append(YazimBulgusu(aday, duzeltme, kural_id))
    return tuple(bulgular)


# --- Track B: sözlüksel geçerlilik (TDK önbelleği) --------------------------

TDK_ONBELLEK_YOLU = Path(__file__).resolve().parent / "veri" / "tdk_onbellek.json"


@lru_cache(maxsize=1)
def _tdk_onbellek() -> dict[str, dict]:
    if not TDK_ONBELLEK_YOLU.exists():
        return {}
    veri = json.loads(TDK_ONBELLEK_YOLU.read_text(encoding="utf-8"))
    return veri.get("kelimeler", {})


@dataclass(frozen=True, slots=True)
class TdkDurumu:
    """Önbellekten okunan geçerlilik durumu."""

    kelime: str
    gecerli: bool
    #: Kelimenin ilk anlamı başka bir maddeye işaret ediyorsa hedefi — bilgi
    #: notudur, karar verici değildir (bkz. modül docstring'i).
    yonlendirme: str | None


def tdk_gecerli_mi(kelime: str) -> TdkDurumu | None:
    """Önbellekten kelimenin TDK geçerliliğine bakar.

    Ağ çağrısı YAPMAZ — yalnızca `veri/tdk_onbellek.json`ı okur. Kelime
    önbellekte yoksa (hiç sorulmamışsa) `None` döner; bu, "geçersiz" ile
    KARIŞTIRILMAMALI — yalnızca "bilinmiyor" demektir. Önbelleğe eklemek
    için: `python -m harness.tdk_senkron <kelime>`.
    """
    kayit = _tdk_onbellek().get(kelime)
    if kayit is None:
        return None
    return TdkDurumu(kelime=kelime, gecerli=kayit["gecerli"], yonlendirme=kayit.get("yonlendirme"))
