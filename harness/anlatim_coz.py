"""`anlatim.py`'nin kelime-listesi taramalarını gerçek ÖSYM/MEB sorularında ölçer.

`soru_coz.py`/`fiil_coz.py`/`isim_coz.py` ile aynı "aday tek seçeneğe düşerse
cevap" mantığı, ama iki soru biçimi var:

    tip: "var"    numaralı seçeneklerin her biri bir CÜMLE; hangisinde
                  `tur` alanında belirtilen anlatım-bozukluğu türü var.
    tip: "sebep"  tek bir `metin`; seçenekler ÖSYM'nin SEBEP ETİKETLERİ
                  ("Gereksiz sözcük kullanımı" gibi). Bizim iç tur kodlarımız
                  (`anlatim.py`) ÖSYM'nin kullandığı etiketten daha ince
                  taneli olabilir — `_OSYM_ETIKETI` eşlemesi burada durur.

Çalıştırma:  .venv/bin/python -m harness.anlatim_coz
"""

from __future__ import annotations

import sys

from anlatim import tara
from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku

SORU_DOSYASI = "anlatim_sorulari.jsonl"

#: İç tur kodlarımızdan ÖSYM'nin kullandığı sebep etiketine eşleme. Birden
#: fazla iç tur aynı ÖSYM etiketi altında sorulabiliyor (üç ayrı "gereksiz
#: sözcük" alt türümüz de ÖSYM'de tek bir etiket altında toplanıyor).
_OSYM_ETIKETI = {
    "CELISEN_SOZCUKLER": "Çelişen sözcüklerin bir arada kullanılması",
    "YAKLASIKLIK_TEKRARI": "Gereksiz sözcük kullanımı",
    "ESANLAMLI_CIFT": "Gereksiz sözcük kullanımı",
    "DEGISMEZ_NITELIK": "Gereksiz sözcük kullanımı",
    "GEREKSIZ_COGUL": "Gereksiz ek kullanımı",
}


def _turler(metin: str) -> set[str]:
    return {b.tur for b in tara(metin)}


def _secenek_metni(soru: dict, harf: str) -> str:
    """Seçeneğin tara() edilecek metnini döner.

    Çoğu kayıt artık kaynak cümleyi değil, sırasız bir `kelimeler` listesi
    taşıyor (bkz. `altin/README.md`) — `tara()`'nın kelime-listesi taramaları
    sıradan bağımsız olduğu için bunları boşlukla birleştirip vermek orijinal
    cümleyi vermekle aynı sonucu üretir. Yalnızca sıraya/mesafeye bakan iki
    kayıt (`redakte_edilemez` alanı olanlar) hâlâ `secenekler` içinde tam
    metin taşır.
    """
    if "kelimeler" in soru:
        return " ".join(soru["kelimeler"][harf])
    return soru["secenekler"][harf]


def coz_var(soru: dict) -> tuple[str, set[str]]:
    harfler = soru["kelimeler"] if "kelimeler" in soru else soru["secenekler"]
    tasiyan = {harf for harf in harfler if soru["tur"] in _turler(_secenek_metni(soru, harf))}
    if not tasiyan:
        return "BOS", tasiyan
    if len(tasiyan) > 1:
        return "BELIRSIZ", tasiyan
    return ("DOGRU" if tasiyan == {soru["cevap"]} else "YANLIS"), tasiyan


def coz_sebep(soru: dict) -> tuple[str, set[str]]:
    metin = " ".join(soru["kelimeler"]) if "kelimeler" in soru else soru["metin"]
    etiketler = {_OSYM_ETIKETI[t] for t in _turler(metin) if t in _OSYM_ETIKETI}
    eslesen = {harf for harf, etiket in soru["secenekler"].items() if etiket in etiketler}
    if not eslesen:
        return "BOS", eslesen
    if len(eslesen) > 1:
        return "BELIRSIZ", eslesen
    return ("DOGRU" if eslesen == {soru["cevap"]} else "YANLIS"), eslesen


def coz(soru: dict) -> tuple[str, set[str]]:
    if soru["tip"] == "sebep":
        return coz_sebep(soru)
    return coz_var(soru)


def main() -> int:
    yol = ALTIN_DIZINI / SORU_DOSYASI
    if not yol.exists():
        print(f"soru dosyası yok: {yol}", file=sys.stderr)
        return 2

    sorular = kumeyi_oku(yol)
    sayac = {"DOGRU": 0, "YANLIS": 0, "BELIRSIZ": 0, "BOS": 0}

    print(f"\n{len(sorular)} soru çözülüyor\n")
    print(f"{'kimlik':<24} {'tip':<8} {'bek':>3} {'bul':<10} durum")
    print("─" * 70)

    for soru in sorular:
        durum, adaylar = coz(soru)
        sayac[durum] += 1
        isaret = {"DOGRU": "✓", "YANLIS": "✗", "BELIRSIZ": "?", "BOS": "∅"}[durum]
        print(
            f"{soru['kimlik']:<24} {soru['tip']:<8} {soru['cevap']:>3} "
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
