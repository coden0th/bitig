"""`yazim.py`nin toplu doğruluğunu ölçer.

Yöntem: `altin/ad_cekimi.jsonl` + `altin/fiil_cekimi.jsonl`'daki HER doğru
kelime için, motorun kendi ürettiği `Kanit` (once/sonra/konum) tersine
çevrilerek "kural unutulmuş" hâli (yanlış yazım) programatik olarak
yeniden inşa edilir — elle yazılmış bir test kümesi değil, motorun kendi
doğruladığı 188 kayıttan türetilir. `yazim.denetle()` bu yanlış yazımdan
doğru yazımı ve doğru kuralı bulabiliyor mu diye bakılır.

İki vaka türü ayrılır:
  - **tesadüfen geçerli**: yanlış yazım BAŞKA bir okumayla zaten çözülüyor
    (örn. "kapı" hem kap+ı hatası hem de bağımsız "kapı" kelimesi) — bu
    durumda `denetle()` tasarım gereği aramaya hiç girmez (dürüst bir sınır,
    bkz. `yazim.py` docstring'i). Ayrı sayılır, başarısızlık sayılmaz.
  - **gerçek vaka**: yanlış yazım hiçbir şekilde çözülmüyor, `denetle()`nin
    doğru düzeltmeyi bulması beklenir.

Çalıştırma:  .venv/bin/python -m harness.yazim_dogrula
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from bitig.cozumleyici import kelimeyi_cozumle
from yazim import denetle

ALTIN_DIZINI = Path(__file__).resolve().parent.parent / "altin"
DOSYALAR = ("ad_cekimi.jsonl", "fiil_cekimi.jsonl")


def _yanlis_yazim_uret(kelime: str, kural_id: str) -> str | None:
    """Motorun kendi Kanit'ini tersine çevirerek "kural unutulmuş" yazımı üretir."""
    sonuc = kelimeyi_cozumle(kelime)
    for okuma in sonuc.okumalar:
        for olay in okuma.olaylar:
            if olay.kural_id != kural_id:
                continue
            k = olay.kanit
            if not k.sonra:  # düşme (UD/UND): düşen ses geri konur
                return kelime[: k.konum] + k.once + kelime[k.konum :]
            if len(k.sonra) > len(k.once) and k.sonra.endswith(k.once):
                # türeme/ikizleşme (UT/KAY): eklenen kısım çıkarılır
                baslangic = k.konum - len(k.sonra) + 1
                return kelime[:baslangic] + k.once + kelime[baslangic + len(k.sonra) :]
            # ikame (YUM/BEN/DAR): eski ses geri konur
            return kelime[: k.konum] + k.once + kelime[k.konum + len(k.sonra) :]
    return None


def main() -> int:
    toplam = dogru = tesadufi = 0
    basarisiz: list[tuple[str, str, str]] = []

    for dosya_adi in DOSYALAR:
        yol = ALTIN_DIZINI / dosya_adi
        with yol.open(encoding="utf-8") as dosya:
            for satir in dosya:
                kayit = json.loads(satir)
                for kural_id in kayit.get("beklenen", []):
                    yanlis = _yanlis_yazim_uret(kayit["kelime"], kural_id)
                    if yanlis is None or yanlis == kayit["kelime"]:
                        continue
                    toplam += 1
                    if not kelimeyi_cozumle(yanlis).cozumlenemedi:
                        tesadufi += 1
                        continue
                    bulgular = denetle(yanlis)
                    if any(b.duzeltme == kayit["kelime"] and b.kural_id == kural_id for b in bulgular):
                        dogru += 1
                    else:
                        basarisiz.append((yanlis, kayit["kelime"], kural_id))

    gecerli_vaka = toplam - tesadufi
    print(f"\n{toplam} vaka türetildi ({tesadufi} tesadüfen geçerli okumaya sahip, hariç tutuldu)")
    print(f"{gecerli_vaka} gerçek vakadan {dogru} doğru bulundu")
    if basarisiz:
        print("\nbaşarısız olanlar:")
        for yanlis, dogru_yazim, kural_id in basarisiz:
            print(f"  {yanlis!r} -> beklenen {dogru_yazim!r} ({kural_id}), bulunamadı")

    if gecerli_vaka:
        print(f"\n  isabet: {dogru / gecerli_vaka * 100:.1f}%")

    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())
