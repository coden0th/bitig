"""Tamlamalar (isim tamlaması) sorularını motorla çözer.

`soru_coz.py`/`fiil_coz.py`nin genellemesi: burada da aday tek seçeneğe düşerse
cevap, düşmezse BELİRSİZ. Farkı şu: önceki iki modül **tek kelimenin** ek
kimliklerine bakıyordu, burada **bitişik iki kelime arasındaki ilişkiye**
bakılıyor — tamlayan (ilgi hâli, `-In`) ile tamlanan (iyelik-3, `-I/-sI`) aynı
tamlamanın parçası mı?

2026-08-07'de gerçek bir ÖSYM sorusuyla (2023 YKS TYT, "Türkiye'nin başkenti"
örneğiyle prototiplendi) bulundu ve doğrulandı — ayrıca bu arayış sırasında
`bitig/cozumleyici.py`'deki kesme işareti boşluğu da bulundu (ayrı, motor
seviyesinde bir düzeltme, bkz. docs/decisions.md §5).

Desteklenen `ozellik` değerleri:

    TAMLAMA_BELIRTILI   tamlayan (-In) + tamlanan (iyelik-3) bitişik, araya
                        yalnızca sıfat(-gibi) kelime girebilir
    TAMLAMA_BELIRTISIZ  çıplak isim + tamlanan (iyelik-3) bitişik

Bilinen sınır (bilinçli, dar tutuldu):

    Yalnızca 3. TEKİL/ÇOĞUL iyelik (tamlanan) aranıyor. 1./2. kişi tamlama
    ("benim kitabım", "senin evin") de dilbilgisinde ad tamlamasıdır ama
    `-In` (ilgi hâli) ile 2. tekil iyelik (`-In`) yüzeyce özdeştir — "senin
    kardeşinin" gibi zincirleme durumlarda yanlış pozitif riski yaratır.
    3. kişiyle sınırlamak bu riski ortadan kaldırıyor; TYT pasajları da
    ezici çoğunlukla 3. kişi anlatımdır.

    Soru cümlenin **tamamını değil belirli bir ögesini** (örn. "yer
    tamlayıcısı") hedefliyorsa bu modül güvenilir değildir — tüm cümleyi
    tarar, hedeflenmeyen bir kısımda yanlış pozitif üretebilir (bkz.
    2026-08-07 oturum notları, 2023 YKS sorusunun B seçeneği).

Çalıştırma:  .venv/bin/python -m harness.isim_coz
"""

from __future__ import annotations

import re
import sys
from collections import Counter

from bitig.cozumleyici import _KELIME_DESENI, cozumle
from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku

SORU_DOSYASI = "isim_sorulari.jsonl"

_NOKTALAMA = re.compile(r"[,;:.!?()\-–—\"']")

#: Araya girebilecek "sıfat gibi" ekler — kökün kendi türü Adj olmasa da
#: (yapım ekiyle sıfatlaşmış: nem+li) sıfat işlevi görür. `Okuma.tur` her
#: zaman KÖKÜN türüdür, türetilmiş yüzeyin işlevini taşımaz (docs/decisions.md §9).
_SIFAT_ISLEVLI_EK_ONEKLERI = ("EK.YAPIM.LI", "EK.YAPIM.SIZ", "EK.YAPIM.SAL", "EK.SIFATFIIL")


def _okuma_sifat_gibi_mi(okuma) -> bool:
    if okuma.tur in ("Adj", "Adv"):
        return True
    return any(any(k.startswith(on) for on in _SIFAT_ISLEVLI_EK_ONEKLERI) for k in okuma.ek_kimlikleri)


def _sifat_gibi_mi(kelime) -> bool:
    """Olası: en az bir okuma sıfat(-gibi) ise araya girmesine izin verilir.

    `Adv` da dahil: "en derin yerinde" gibi pekiştirilmiş sıfatlarda derece
    zarfı ("en") ile sıfat ("derin") birlikte araya girer — 2026-08-07'de
    gerçek bir ÖSYM sorusunda ("Kalbinin en derin yerinde") yakalandı.
    """
    return any(_okuma_sifat_gibi_mi(ok) for ok in kelime.okumalar)


def _tamlayan_mi(kelime) -> bool:
    """Olası: en az bir okumada ilgi hâli varsa tamlayan adayıdır."""
    return any("EK.HAL.ILG" in ok.ek_kimlikleri for ok in kelime.okumalar)


def _tamlayansiz_isim_mi(kelime) -> bool:
    """Olası: en az bir okuma çıplak isim ise tamlayan adayıdır.

    **Bilinen, çözülmemiş gerilim:** Türkçe'de isim/sıfat çift okumalı
    kelimeler yaygın (`keçi`, `karanlık`, `doğru`...). Olası mantık gerçek
    tamlamaları (`keçi yolundan`) doğru buluyor ama sıfat olarak kullanılan
    çift okumalı kelimelerde (`karanlık gözleri`) yanlış pozitif riski
    taşıyor. Kesin mantık (her okuma isim) denendi, tersi hataya yol açtı
    (`keçi yolundan` kaçırıldı) — net kazanç yok. Bu, gerçek bağlamsal
    isim/sıfat ayrımı gerektiren bir sınır (Faz 2/3), harness'ta çözülmedi.
    2026-08-07 oturum notları.
    """
    return any(ok.tur == "Noun" and not ok.ek_kimlikleri for ok in kelime.okumalar)


def _tamlanan_mi(kelime) -> bool:
    """Olası: en az bir okumada iyelik-3 varsa tamlanan adayıdır."""
    return any(
        "EK.IYELIK.3T" in ok.ek_kimlikleri or "EK.IYELIK.3C" in ok.ek_kimlikleri
        for ok in kelime.okumalar
    )


def _kelime_spanlari(metin: str) -> list[tuple[str, tuple[int, int]]]:
    return [(e.group(), e.span()) for e in _KELIME_DESENI.finditer(metin)]


def _noktalama_var_mi(metin: str, bitis: int, baslangic: int) -> bool:
    return bool(_NOKTALAMA.search(metin[bitis:baslangic]))


def _tamlama_bul(metin: str, tamlayan_kontrol, pencere: int = 3) -> list[tuple[str, str]]:
    """`tamlayan_kontrol`i sağlayan bir kelimeden başlayıp `pencere` kelime
    içinde tamlanan (iyelik-3) arar. Araya yalnızca sıfat(-gibi) kelime ya
    da (belirtisiz tamlama için) başka bir çıplak isim girebilir; noktalama
    işareti sert bir sınırdır."""
    kelimeler = list(cozumle(metin))
    spanlar = _kelime_spanlari(metin)
    bulunanlar: list[tuple[str, str]] = []
    for i, k in enumerate(kelimeler):
        if not tamlayan_kontrol(k):
            continue
        for j in range(i + 1, min(i + 1 + pencere, len(kelimeler))):
            if _noktalama_var_mi(metin, spanlar[j - 1][1][1], spanlar[j][1][0]):
                break
            arada_sorunlu = any(
                not (_sifat_gibi_mi(kelimeler[m]) or _tamlayansiz_isim_mi(kelimeler[m]))
                for m in range(i + 1, j)
            )
            if arada_sorunlu:
                break
            aday = kelimeler[j]
            if _tamlanan_mi(aday):
                bulunanlar.append((k.kelime, aday.kelime))
                break
    return bulunanlar


def _ozellik_var_mi(metin: str, ozellik: str) -> bool:
    if ozellik == "TAMLAMA_BELIRTILI":
        return bool(_tamlama_bul(metin, _tamlayan_mi))
    if ozellik == "TAMLAMA_BELIRTISIZ":
        return bool(_tamlama_bul(metin, _tamlayansiz_isim_mi))
    if ozellik == "TAMLAMA_ANY":
        return bool(_tamlama_bul(metin, _tamlayan_mi)) or bool(_tamlama_bul(metin, _tamlayansiz_isim_mi))
    raise ValueError(f"bilinmeyen ozellik: {ozellik}")


def coz_farkli_tur(soru: dict) -> tuple[str, set[str]]:
    """`tip: farkli_tur` — hangi seçeneğin son kelimesi tamlanan (iyelik-3)
    bakımından azınlıkta kalıyor. `harness/fiil_coz.py`'deki aynı isimli
    mekanizmanın tamlama karşılığı: orada fiilimsi alt-türü çoğunluğu
    aranıyordu, burada tek bir ikili özellik var (tamlanan var/yok) — her
    seçenek kısa bir öbek (`"savaş oyunu"`, `"eşit güçte"` gibi), yalnızca
    öbeğin SON kelimesi `_tamlanan_mi` ile sınanır. Örnek: "eşit güçte" içinde
    "güç" çıplak isim + hâl eki alıyor (araya iyelik girmiyor) — sıfat
    tamlaması, ad tamlaması değil; diğer dört seçenekte son kelime iyelik-3
    taşıyor (belirtisiz ad tamlaması). 2026-08-07, OGM Materyal'de gerçek bir
    ÖSYM-tarzı soruyla bulundu.
    """
    secenek_durumu: dict[str, bool] = {}
    for harf, metin in soru["secenekler"].items():
        kelimeler = list(cozumle(metin))
        if not kelimeler:
            continue
        secenek_durumu[harf] = _tamlanan_mi(kelimeler[-1])

    sayac = Counter(secenek_durumu.values())
    if not sayac:
        return "BOS", set()
    coğunluk, _ = sayac.most_common(1)[0]
    azinlikta = {h for h, v in secenek_durumu.items() if v != coğunluk}

    if not azinlikta:
        return "BOS", azinlikta
    if len(azinlikta) > 1:
        return "BELIRSIZ", azinlikta
    return ("DOGRU" if azinlikta == {soru["cevap"]} else "YANLIS"), azinlikta


def coz(soru: dict) -> tuple[str, set[str]]:
    """`tip: var|yok` sorularını çözer. `soru_coz.coz` ile aynı mantık."""
    if soru["tip"] == "farkli_tur":
        return coz_farkli_tur(soru)

    ozellik = soru["ozellik"]
    tasiyan = {
        harf
        for harf, metin in soru["secenekler"].items()
        if _ozellik_var_mi(metin, ozellik)
    }
    tumu = set(soru["secenekler"])
    adaylar = tasiyan if soru["tip"] == "var" else tumu - tasiyan

    if not adaylar:
        return "BOS", adaylar
    if len(adaylar) > 1:
        return "BELIRSIZ", adaylar
    return ("DOGRU" if adaylar == {soru["cevap"]} else "YANLIS"), adaylar


def main() -> int:
    yol = ALTIN_DIZINI / SORU_DOSYASI
    if not yol.exists():
        print(f"soru dosyası yok: {yol}", file=sys.stderr)
        return 2

    sorular = kumeyi_oku(yol)
    sayac = {"DOGRU": 0, "YANLIS": 0, "BELIRSIZ": 0, "BOS": 0}

    print(f"\n{len(sorular)} soru çözülüyor\n")
    print(f"{'kimlik':<12} {'ozellik':<20} {'bek':>3} {'bul':<10} durum")
    print("─" * 70)

    for soru in sorular:
        durum, adaylar = coz(soru)
        sayac[durum] += 1
        isaret = {"DOGRU": "✓", "YANLIS": "✗", "BELIRSIZ": "?", "BOS": "∅"}[durum]
        print(
            f"{soru['kimlik']:<12} {soru.get('ozellik', soru['tip']):<20} {soru['cevap']:>3} "
            f"{','.join(sorted(adaylar)) or '—':<10} {isaret} {durum}"
        )

    toplam = len(sorular)
    print("─" * 70)
    print(
        f"  doğru {sayac['DOGRU']}  ·  yanlış {sayac['YANLIS']}  ·  "
        f"ayırt edemedi {sayac['BELIRSIZ']}  ·  aday bulamadı {sayac['BOS']}"
    )
    if toplam:
        print(f"\n  soru başarımı: {sayac['DOGRU'] / toplam * 100:.1f}%")

    return 1 if (sayac["YANLIS"] or sayac["BOS"]) else 0


if __name__ == "__main__":
    sys.exit(main())
