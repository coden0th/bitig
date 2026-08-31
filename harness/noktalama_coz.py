"""`noktalama.py`'nin taramalarını gerçek ÖSYM/MEB sorularında ölçer.

`anlatim_coz.py` ile aynı "aday tek seçeneğe düşerse cevap" mantığı: her
seçenek bir CÜMLE, hangisinde `tur` alanında belirtilen noktalama hatası var.

Çalıştırma:  .venv/bin/python -m harness.noktalama_coz
"""

from __future__ import annotations

import sys

from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku
from noktalama import tara

SORU_DOSYASI = "noktalama_sorulari.jsonl"


def _turler(metin: str) -> set[str]:
    return {b.tur for b in tara(metin)}


def coz(soru: dict) -> tuple[str, set[str]]:
    tasiyan = {harf for harf, metin in soru["secenekler"].items() if soru["tur"] in _turler(metin)}
    if not tasiyan:
        return "BOS", tasiyan
    if len(tasiyan) > 1:
        return "BELIRSIZ", tasiyan
    return ("DOGRU" if tasiyan == {soru["cevap"]} else "YANLIS"), tasiyan


def main() -> int:
    yol = ALTIN_DIZINI / SORU_DOSYASI
    if not yol.exists():
        print(f"soru dosyası yok: {yol}", file=sys.stderr)
        return 2

    sorular = kumeyi_oku(yol)
    sayac = {"DOGRU": 0, "YANLIS": 0, "BELIRSIZ": 0, "BOS": 0}

    print(f"\n{len(sorular)} soru çözülüyor\n")
    print(f"{'kimlik':<20} {'tur':<20} {'bek':>3} {'bul':<10} durum")
    print("─" * 70)

    for soru in sorular:
        durum, adaylar = coz(soru)
        sayac[durum] += 1
        isaret = {"DOGRU": "✓", "YANLIS": "✗", "BELIRSIZ": "?", "BOS": "∅"}[durum]
        print(
            f"{soru['kimlik']:<20} {soru['tur']:<20} {soru['cevap']:>3} "
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
