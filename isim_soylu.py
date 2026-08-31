"""İsim soylu sözcüklerin (zamir/sıfat/edat/bağlaç/zarf) BAĞLAMSAL tür ayrımı.

`bitig/` DIŞINDA — `baglam.py`/`anlatim.py` ile aynı gerekçe: üretim hattı
model çağırmaz kuralı bunun için değil, ama bu da çekirdek morfoloji değil,
morfolojinin ÜSTÜNE kurulu bir bağlam/sözdizimi katmanı (Faz 2/3 sınırında).

**Kritik bulgu:** Motorun kendi sözlüğü, İsim Soylu Sözcükler'in çoğu kapalı
sınıf kelimesi için tür ayrımını ZATEN okuma düzeyinde taşıyor — `bu` hem
`Det` (belirten/sıfat) hem `Pron` (zamir) olarak, `ile` hem `Conj` hem
`Postp` (edat) olarak ayrı okumalar döner. Bu modülün işi YENİ bir
sınıflandırma icat etmek değil: motor birden fazla tur'u aynı anda mümkün
gösterdiğinde (çünkü motor "tespit değil türetim" ilkesiyle hepsini döner,
seçmez), CÜMLE BAĞLAMINA bakarak hangisinin geçerli olduğunu seçmektir.

`veri/kapali_sinif_kelimeler.json`, motorun kaba tur etiketinin (Det/Pron/
Adj/Postp/Conj/Adv) ALTINDA MEB'in kullandığı ince alt sınıflandırmayı
(işaret/belgisiz/soru zamiri, işaret/belgisiz/soru sıfatı...) sağlar.

**Dar tutulan, bilinçli sınır:** Yalnızca CÜMLE İÇİ KONUM sezgisiyle
çözülebilen ayrımlar burada var (izleyen kelime çıplak ad mı, önceki kelime
yönelme hâlinde mi). Anlamsal/söylemsel ayrımlar (`ile` edat mı bağlaç mı —
"yerine 've' konabiliyor mu" testi tam sözdizimi çözümlemesi gerektirir;
`bir` sayı sıfatı mı belgisiz sıfat mı; `yalnız`/`ancak`/`hem` zarf mı bağlaç
mı — iki cümleyi mi bağladığı anlaşılmalı) BİLEREK çözülmeye çalışılmadı,
`None` (belirsiz) döner. Zorlama yok — CLAUDE.md §10: "belirsiz çözümlemeyi
tek bir okumaya indirgeme".

Çalıştırma / test:  .venv/bin/python -m pytest testler/test_isim_soylu.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from bitig import fonetik
from bitig.cozumleyici import kelimeyi_cozumle

VERI_YOLU = Path(__file__).resolve().parent / "veri" / "kapali_sinif_kelimeler.json"

_KELIME_DESENI = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü]+")


@lru_cache(maxsize=1)
def _kapali_sinif() -> dict:
    return json.loads(VERI_YOLU.read_text(encoding="utf-8"))


def sozcuklere_ayir(cumle: str) -> list[str]:
    """Basit kelime ayrımı — noktalama atılır, boşluğa göre bölünür."""
    return _KELIME_DESENI.findall(cumle)


#: Çekimli zamir biçimlerinde (bunu/ona/kimin) motorun ürettiği rakip "sahte
#: isim kökü" okumalarını (bkz. docs/decisions.md §9) elemek için bilinen zamir kökleri.
_ZAMIR_KOKLERI = {"bu", "şu", "o", "kim", "ne", "kendi"}


@lru_cache(maxsize=4096)
def _okuma_ozeti(kelime: str) -> tuple[tuple[str, str, bool], ...]:
    """(kök, tur, ek_var_mi) üçlülerinin kümesi — tekrar sorgulamamak için önbellekli."""
    sonuc = kelimeyi_cozumle(kelime)
    if sonuc.cozumlenemedi:
        return ()
    return tuple((ok.kok, ok.tur, bool(ok.ekler)) for ok in sonuc.okumalar)


def _ad_gibi_mi(kelime: str) -> bool:
    """kelime, herhangi bir okumada (ek almış ya da almamış) Noun/Adj/Num mü.

    Dikkat: "sonraki kelime ÇIPLAK mı" değil, "isim gibi mi" sorusu — çünkü
    işaret sıfatı + isim öbeğinde isim çoğunlukla kendi çekim ekini taşır
    ("bu kitabı", "bu evde") ve yine de sıfat kullanımı geçerlidir.
    """
    return any(tur in ("Noun", "Adj", "Num") for _, tur, _ in _okuma_ozeti(kelime))


def _yonelme_halinde_mi(kelime: str) -> bool:
    sonuc = kelimeyi_cozumle(kelime)
    if sonuc.cozumlenemedi:
        return False
    return any(any(k.startswith("EK.HAL.YON") for k in ok.ek_kimlikleri) for ok in sonuc.okumalar)


@dataclass(frozen=True)
class TurSecimi:
    kelime: str
    tur: str  # motorun kaba etiketi: Det/Pron/Adj/Postp/Conj/Adv/Noun/Num/Interj
    alt_kategori: str | None  # kapali_sinif_kelimeler.json'daki ince tür (varsa)
    gerekce: str


def _alt_kategori(kelime: str, tur: str) -> str | None:
    veri = _kapali_sinif()
    k = fonetik.kucult(kelime)

    def _liste_icinde(liste_key: str) -> str | None:
        for alt, liste in veri[liste_key].items():
            if alt.startswith("_") or not isinstance(liste, list):
                continue
            if k in {fonetik.kucult(w) for w in liste}:
                return alt
        return None

    if tur == "Pron":
        return _liste_icinde("zamir")
    if tur in ("Det", "Adj"):
        return _liste_icinde("sifat")
    if tur == "Adv":
        return _liste_icinde("zarf")
    if tur == "Postp":
        return "edat" if k in {fonetik.kucult(w) for w in veri["edat"]} else None
    if tur == "Conj":
        return "baglac" if k in {fonetik.kucult(w) for w in veri["baglac"]} else None
    return None


def kelime_turunu_sec(sozcukler: list[str], i: int) -> TurSecimi | None:
    """`sozcukler[i]`nin cümle içi konumuna göre hangi türde kullanıldığını seçer.

    Motorun döndürdüğü TÜM tur adayları arasından konum sezgisiyle birini
    seçer. Ayırt edici bir sezgi yoksa (örn. `ile`nin edat/bağlaç ayrımı)
    zorlama yapmadan `None` döner.
    """
    kelime = sozcukler[i]
    ozet = _okuma_ozeti(kelime)
    if not ozet:
        return None

    ciplak_turler = {tur for _, tur, ek_var in ozet if not ek_var}

    # Çekim almış zamir biçimleri (bunu/ona/kimin gibi): motorun ürettiği rakip
    # "sahte isim kökü" okumaları (bkz. docs/decisions.md §9, üretken yapım/kaynaştırma
    # okumaları) yüzünden çıplak Pron okuması hiç kalmaz. Ek'li okumalar arasında
    # kökü bilinen bir zamir kökü olan bir Pron okuması varsa, bu yeterince
    # güvenli — bu kökler (bu/şu/o/kim/ne/kendi) gerçek isim kökü değildir; rakip
    # "bun/şun/on+ek" okumaları motorun üretken kaynaştırma/yapım mekanizmasının
    # yan ürünüdür (bkz. docs/decisions.md §9, "gövde küçülür kuralı" dersiyle aynı sınıf).
    if not ciplak_turler:
        if any(kok in _ZAMIR_KOKLERI and tur == "Pron" for kok, tur, _ in ozet):
            return TurSecimi(kelime, "Pron", _alt_kategori(kelime, "Pron"), "çekimli zamir kökü")
        return None

    sonraki_isim_gibi = i + 1 < len(sozcukler) and _ad_gibi_mi(sozcukler[i + 1])

    # 0) Postp (edat) — önceki kelime yönelme hâlindeyse ("X'e karşı/doğru") edat
    #    kullanımı MEB'in kendi örnek kalıbıyla birebir örtüşüyor; bu, aşağıdaki
    #    genel sıfat sezgisinden ÖNCE kontrol edilmeli (yoksa "ona karşı çok
    #    naziktim" gibi bir cümlede "karşı" sonraki kelime isim-gibiyse yanlışlıkla
    #    sıfat sanılabilir — bkz. testler).
    if "Postp" in ciplak_turler and len(ciplak_turler) > 1 and i > 0 and _yonelme_halinde_mi(sozcukler[i - 1]):
        return TurSecimi(kelime, "Postp", "edat", "önceki kelime yönelme hâlinde, edat kullanımı")

    # 1) Belirten/sıfat (Det ya da Adj — motor ikisini de kullanıyor, örn. "hangi"
    #    Adj+Pron iken "bu" Det+Pron) vs Pron (zamir) — bu/şu/o, kimi, bazı,
    #    birkaç, her, hangi, kaç... Sıfat-gibi bir okuma varsa VE sonraki kelime
    #    isim gibiyse sıfat kazanır (rakip Pron olsun ya da olmasın — "kaç kişi"
    #    örneğinde rakip Verb'dür, yine de sıfat doğru okumadır). Sıfat-gibi
    #    okuma yoksa ya da isim izlemiyorsa ve Pron adaysa zamir kazanır.
    # "Num" (sayı sıfatı) da çıplak adaylar arasındaysa zorlama yapılmaz —
    # "bir" için sayı mı belgisizlik sıfatı mı olduğu ("bir gün" gibi) gerçek,
    # bilinçli bırakılmış bir belirsizlik (bkz. docs/decisions.md §9, "bir" örneği).
    sifat_adaylari = ciplak_turler & {"Det", "Adj"}
    if sifat_adaylari and sonraki_isim_gibi and "Num" not in ciplak_turler:
        secilen = "Det" if "Det" in sifat_adaylari else "Adj"
        return TurSecimi(
            kelime, secilen, _alt_kategori(kelime, secilen),
            "sonraki kelime isim gibi kullanılmış, belirten/sıfat kullanımı",
        )
    if sifat_adaylari and "Pron" in ciplak_turler:
        return TurSecimi(kelime, "Pron", _alt_kategori(kelime, "Pron"), "isim izlemiyor, zamir kullanımı")

    # 2) Postp (edat) ile rakip Noun/Adv arasında, önceki kelime yönelme hâlinde
    #    değilse ve sonraki kelime de isim gibi değilse (rule 1'de zaten sıfat
    #    olarak yakalanmadıysa) konumla ayırt edilemez — belirsiz bırakılır
    #    (isim/zarf ayrımı anlamsal bağlam gerektirir, bkz. modül docstring'i).
    if "Postp" in ciplak_turler and len(ciplak_turler) > 1:
        return None

    # 3) Tek çıplak tur varsa zaten belirsizlik yok.
    if len(ciplak_turler) == 1:
        tur = next(iter(ciplak_turler))
        return TurSecimi(kelime, tur, _alt_kategori(kelime, tur), "tek olası tür")

    return None  # gerçekten belirsiz (örn. `ile` edat/bağlaç) — zorlama yok


def cumleyi_coz(cumle: str) -> list[TurSecimi | None]:
    """Cümledeki her kelime için `kelime_turunu_sec` sonucunu döner (sırayla)."""
    sozcukler = sozcuklere_ayir(cumle)
    return [kelime_turunu_sec(sozcukler, i) for i in range(len(sozcukler))]
