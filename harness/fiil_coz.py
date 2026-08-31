"""Fiiller (çatı, fiilimsi, birleşik çekim) sorularını motorla çözer.

`soru_coz.py`nin genellemesi: orada tek `olay` (SES.*) alanına bakılıyordu, burada
`ek_kimlikleri` içindeki bir önek kümesine (`EK.CATI.*`, `EK.SIFATFIIL.*`...) bakılıyor.
Aynı "aptal" yöntem: aday kümesi tek seçeneğe düşerse cevap, düşmezse BELİRSİZ.

Bu dosyaya her tip eklenmeden önce `harness/fiil_coz` ölçümü elle yapılmalı — Fiiller
domaininde sözlükleşme (özellikle İŞTEŞ çatıda: "tanışmak", "barışmak", "buluşmak" gibi
fiiller sözlükte çıplak kök, türetim izi yok) Sözcükte Yapı kadar ciddi olabilir. Bkz.
docs/decisions.md §5, 2026-08-06 oturumu notları.

Desteklenen `ozellik` değerleri (`veri/ekler.json`'daki önek kümeleriyle eşleşir):

    FIILIMSI          EK.SIFATFIIL / EK.ISIMFIIL / EK.ZARFFIIL (herhangi biri)
    FIILIMSI_UCU_DE    üçü birden aynı cümlede (bkz. coz_farkli_tur ile karıştırma)
    BIRLESIK_CEKIM    EK.BIRLESIK.* (hikâye/rivayet/şart birleşimi — hem fiil kipi
                       üstünde hem isim/sıfat yüklemi üstünde, 2026-08-06'dan beri ikisi de)
    EKFIIL            Ek-fiilin *kendisi* var mı (bildirme/hikâye/rivayet/şart, ya da
                       kip'siz isim/sıfat üstündeki çıplak kişi eki: "öğrenciyim").
                       Sade fiil çekimindeki kişi eki ("geliyorum") SAYILMAZ — kip var
                       ama BIRLESIK/BILDIRME yoksa bu ek-fiil değil, düz çekimdir.

Desteklenmeyenler (bilerek dışarıda tutuldu, ölçüldü, kaynağı not düşüldü):

    CATI.ISTES        sözlükleşme riski yüksek (tanış/barış/buluş çıplak kök)
    CATI.EDILGEN tek başına  edilgen/dönüşlü ayrımı bağlama bağlı (bkz. bitig/ekler.json
                       EK.CATI.DONUSLU.* — motor artık ikisini de üretiyor, seçmiyor)

Çalıştırma:  .venv/bin/python -m harness.fiil_coz
"""

from __future__ import annotations

import re
import sys
from collections import Counter

from bitig.cozumleyici import kelimeyi_cozumle
from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku

SORU_DOSYASI = "fiil_sorulari.jsonl"

# En uzun rakam önce: "IV" "III" ile başlıyor gibi görünüp yanlış eşleşmesin.
_ROMA_DUZENI = re.compile(r"\b(IV|III|II|I|V)\b")

_OZELLIK_ONEKLERI: dict[str, tuple[str, ...]] = {
    "FIILIMSI": ("EK.SIFATFIIL", "EK.ISIMFIIL", "EK.ZARFFIIL"),
    "BIRLESIK_CEKIM": ("EK.BIRLESIK",),
}

# Fiilimsi alt-türü sorularında ("hangisi farklı türden") her önek tek bir
# kategoriye eşlenir; kategori kümesinin kendisi karşılaştırılır.
_FIILIMSI_ALT_TUR_ONEKLERI: dict[str, str] = {
    "EK.SIFATFIIL": "sıfat-fiil",
    "EK.ISIMFIIL": "isim-fiil",
    "EK.ZARFFIIL": "zarf-fiil",
}


def _kategoriler(kelimeler: list[str], onekler: tuple[str, ...]) -> set[str]:
    """Kelime listesindeki tüm okumalarda geçen ek_kimlikleri, önekle süzülmüş.

    Kelime kelime çalışır, cümle bağlamı gerekmez — bu yüzden seçenekler artık
    sırasız kelime listesi olarak saklanır (bkz. `altin/fiil_sorulari.jsonl`)."""
    bulunan: set[str] = set()
    for kelime in kelimeler:
        for okuma in kelimeyi_cozumle(kelime).okumalar:
            for kimlik in okuma.ek_kimlikleri:
                if any(kimlik.startswith(on) for on in onekler):
                    bulunan.add(kimlik)
    return bulunan


def _fiilimsi_alt_turleri(kelimeler: list[str]) -> set[str]:
    """Kelime listesinde *olası* (en az bir okumada) geçen fiilimsi alt-türleri."""
    turler: set[str] = set()
    for kelime in kelimeler:
        for okuma in kelimeyi_cozumle(kelime).okumalar:
            for on, ad in _FIILIMSI_ALT_TUR_ONEKLERI.items():
                if any(kimlik.startswith(on) for kimlik in okuma.ek_kimlikleri):
                    turler.add(ad)
    return turler


def _okuma_ekfiil_mi(ekler: tuple[str, ...]) -> bool:
    """`EK.KIP.*` varken salt `EK.KISI.Z.*` sade fiil çekimidir ("geliyorum") — ek-fiil
    sayılmaz. `EK.BILDIRME`/`EK.BIRLESIK.*` her zaman sayılır (kip üstünde de olsa
    birleşik zaman kurar, o da ek-fiilin görevidir)."""
    if any(e == "EK.BILDIRME" or e.startswith("EK.BIRLESIK") for e in ekler):
        return True
    has_kip = any(e.startswith("EK.KIP.") for e in ekler)
    has_kisiz = any(e.startswith("EK.KISI.Z") for e in ekler)
    return has_kisiz and not has_kip


def _ekfiil_var_mi(kelimeler: list[str]) -> bool:
    """Ek-fiilin kendisi var mı — cümlede **kesin** ek-fiil taşıyan bir kelime var mı.

    "Kesin" burada kelime düzeyinde: bir kelimenin *her* okuması ek-fiil göstermeli.
    Sebep: ISIM_KOK durumu hem çıplak isim/sıfat kökleri hem de sıfat-fiil çıktısı
    ("gördüğüm") için ortak kullanılıyor; "any okuma" mantığı bu yüzden fiilimsili
    kelimelerde bile sahte bir ek-fiil okuması buluyordu (`beğendiğim` gibi). Kesin
    mantığı bunu eler çünkü aynı kelimenin iyelik okuması hep rakip olarak kalır.
    """
    for kelime in kelimeler:
        s = kelimeyi_cozumle(kelime)
        if not s.okumalar:
            continue
        if all(_okuma_ekfiil_mi(okuma.ek_kimlikleri) for okuma in s.okumalar):
            return True
    return False


def _ozellik_var_mi(kelimeler: list[str], ozellik: str) -> bool:
    if ozellik == "EKFIIL":
        return _ekfiil_var_mi(kelimeler)
    if ozellik == "FIILIMSI_UCU_DE":
        return _fiilimsi_alt_turleri(kelimeler) == set(_FIILIMSI_ALT_TUR_ONEKLERI.values())
    onekler = _OZELLIK_ONEKLERI[ozellik]
    return bool(_kategoriler(kelimeler, onekler))


def coz_var_yok(soru: dict) -> tuple[str, set[str]]:
    """`tip: var|yok` sorularını çözer. `soru_coz.coz` ile aynı mantık."""
    ozellik = soru["ozellik"]
    tasiyan = {
        harf
        for harf, kelimeler in soru["kelimeler"].items()
        if _ozellik_var_mi(kelimeler, ozellik)
    }
    tumu = set(soru["kelimeler"])
    adaylar = tasiyan if soru["tip"] == "var" else tumu - tasiyan

    if not adaylar:
        return "BOS", adaylar
    if len(adaylar) > 1:
        return "BELIRSIZ", adaylar
    return ("DOGRU" if adaylar == {soru["cevap"]} else "YANLIS"), adaylar


def coz_farkli_tur(soru: dict) -> tuple[str, set[str]]:
    """`tip: farkli_tur` — hangi seçeneğin fiilimsi alt-türü azınlıkta kalıyor.

    Her seçenekte kesin olarak hangi alt-tür(ler) geçiyor bulunur (kelime başına: o
    kelimenin *her* okumasında ortak olan alt-türler — belirsiz kelimeler için hiçbiri
    kesin sayılmaz). Beş seçenekte en yaygın alt-tür çoğunluk, ondan yoksun olan tek
    seçenek cevaptır.
    """
    onekler = tuple(_FIILIMSI_ALT_TUR_ONEKLERI)
    secenek_turleri: dict[str, set[str]] = {}
    for harf, kelimeler in soru["kelimeler"].items():
        turler: set[str] = set()
        for kelime in kelimeler:
            okuma_turleri = [
                {
                    _FIILIMSI_ALT_TUR_ONEKLERI[on]
                    for on in onekler
                    if any(kimlik.startswith(on) for kimlik in okuma.ek_kimlikleri)
                }
                for okuma in kelimeyi_cozumle(kelime).okumalar
            ]
            okuma_turleri = [t for t in okuma_turleri if t]
            if not okuma_turleri:
                continue
            kesin = set.intersection(*okuma_turleri) if len(okuma_turleri) > 1 else okuma_turleri[0]
            turler |= kesin
        secenek_turleri[harf] = turler

    sayac = Counter(tur for turler in secenek_turleri.values() for tur in turler)
    if not sayac:
        return "BOS", set()
    coğunluk_turu, _ = sayac.most_common(1)[0]
    azinlikta = {h for h, turler in secenek_turleri.items() if coğunluk_turu not in turler}

    if not azinlikta:
        return "BOS", azinlikta
    if len(azinlikta) > 1:
        return "BELIRSIZ", azinlikta
    return ("DOGRU" if azinlikta == {soru["cevap"]} else "YANLIS"), azinlikta


def _roma_kumesi(metin: str) -> frozenset[str]:
    return frozenset(_ROMA_DUZENI.findall(metin))


def coz_coklu(soru: dict) -> tuple[str, set[str]]:
    """`tip: coklu_var|coklu_yok` — numaralanmış cümlelerden hangi alt kümenin

    kriteri sağladığını bulur, sonra hangi seçeneğin metni ("I ve III", "Yalnız
    II"...) tam olarak o kümeyi anlattığını arar. `ogeler` (I→cümle) ile
    `secenekler` (A→birleşim metni) ayrı sözlüklerdir.
    """
    ozellik = soru["ozellik"]
    hedef_kume = {
        numara
        for numara, kelimeler in soru["ogeler"].items()
        if _ozellik_var_mi(kelimeler, ozellik)
    }
    if soru["tip"] == "coklu_yok":
        hedef_kume = set(soru["ogeler"]) - hedef_kume

    eslesen = {
        harf
        for harf, secenek_metni in soru["secenekler"].items()
        if _roma_kumesi(secenek_metni) == hedef_kume
    }

    if not eslesen:
        return "BOS", eslesen
    if len(eslesen) > 1:
        return "BELIRSIZ", eslesen
    return ("DOGRU" if eslesen == {soru["cevap"]} else "YANLIS"), eslesen


def coz(soru: dict) -> tuple[str, set[str]]:
    if soru["tip"] == "farkli_tur":
        return coz_farkli_tur(soru)
    if soru["tip"] in ("coklu_var", "coklu_yok"):
        return coz_coklu(soru)
    return coz_var_yok(soru)


def main() -> int:
    yol = ALTIN_DIZINI / SORU_DOSYASI
    if not yol.exists():
        print(f"soru dosyası yok: {yol}", file=sys.stderr)
        return 2

    sorular = kumeyi_oku(yol)
    sayac = {"DOGRU": 0, "YANLIS": 0, "BELIRSIZ": 0, "BOS": 0}

    print(f"\n{len(sorular)} soru çözülüyor\n")
    print(f"{'kimlik':<12} {'tip':<12} {'bek':>3} {'bul':<10} durum")
    print("─" * 62)

    for soru in sorular:
        durum, adaylar = coz(soru)
        sayac[durum] += 1
        isaret = {"DOGRU": "✓", "YANLIS": "✗", "BELIRSIZ": "?", "BOS": "∅"}[durum]
        print(
            f"{soru['kimlik']:<12} {soru['tip']:<12} {soru['cevap']:>3} "
            f"{','.join(sorted(adaylar)) or '—':<10} {isaret} {durum}"
        )

    toplam = len(sorular)
    print("─" * 62)
    print(
        f"  doğru {sayac['DOGRU']}  ·  yanlış {sayac['YANLIS']}  ·  "
        f"ayırt edemedi {sayac['BELIRSIZ']}  ·  aday bulamadı {sayac['BOS']}"
    )
    if toplam:
        print(f"\n  soru başarımı: {sayac['DOGRU'] / toplam * 100:.1f}%")

    return 1 if (sayac["YANLIS"] or sayac["BOS"]) else 0


if __name__ == "__main__":
    sys.exit(main())
