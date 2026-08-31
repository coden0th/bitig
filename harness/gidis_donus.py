"""Gidiş-dönüş taraması: üret → geri çözümle → aynı okumayı bul.

Altın küme elle yazılır, dolayısıyla küçüktür ve yalnızca **düşünebildiğimiz**
vakaları kapsar. Bu taramanın değeri, doğruluk ölçütünü elle yazılmış etiketten
kurtarmasıdır: motor bir yüzeyi kendisi üretir, sonra o yüzeyi geri çözümler.
Ürettiği okumayı geri bulamıyorsa ortada — etikete bakmadan — kesin bir bug
vardır. Yüz binlerce vaka, sıfır elle emek.

Üç bozukluk türü ayrı ayrı sayılır:

  KAYIP     üretilen yüzey hiç çözümlenemiyor        → çözümleyicide kör nokta
  OKUMA     çözümleniyor ama o türetim yolu yok      → aday üretimi eksik
  OLAY      yol bulunuyor ama olay kümesi tutmuyor   → şelale tutarsız

Not: tarama motorun **kendi içinde tutarlı** olduğunu gösterir, Türkçe'ye uygun
olduğunu değil. İkisi ayrı sorulardır; dil doğruluğu altın kümenin ve
anlaşmazlık taramasının işidir. Bu araç onların bulamayacağı sınıfı bulur.

Çalıştırma:
    .venv/bin/python -m harness.gidis_donus                 # 2000 kök örneklem
    .venv/bin/python -m harness.gidis_donus --hepsi         # tüm sözlük
    .venv/bin/python -m harness.gidis_donus --ornek 500 --azami-ek 2
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections import Counter

from bitig.cozumleyici import kelimeyi_cozumle
from bitig.sozluk.depo import varsayilan_sozluk
from bitig.uretici import uret

#: Örneklem tekrarlanabilir olsun; aynı tohum aynı kökleri seçer.
TOHUM = 20260806


def tara(
    ornek: int | None,
    azami_ek: int,
    tavan: int,
    ayrinti: int,
) -> tuple[Counter, list[str]]:
    sozluk = varsayilan_sozluk()

    girdiler = [g for grup in sozluk.indeks.values() for g in grup]
    if ornek is not None and ornek < len(girdiler):
        girdiler = random.Random(TOHUM).sample(girdiler, ornek)

    sayac = Counter()
    ornekler: list[str] = []

    for girdi in girdiler:
        for uretim in uret(girdi, azami_ek=azami_ek, tavan=tavan):
            sayac["uretim"] += 1
            sonuc = kelimeyi_cozumle(uretim.yuzey)

            if sonuc.cozumlenemedi:
                sayac["KAYIP"] += 1
                _kaydet(ornekler, ayrinti, f"KAYIP  {uretim.yuzey:22} ← {girdi.kok} {'+'.join(uretim.ek_kimlikleri) or '∅'}")
                continue

            eslesen = [
                o
                for o in sonuc.okumalar
                if o.kok == uretim.kok
                and o.tur == uretim.tur
                and o.ek_kimlikleri == uretim.ek_kimlikleri
            ]
            if not eslesen:
                sayac["OKUMA"] += 1
                bulunanlar = ", ".join(
                    f"{o.kok}+{'+'.join(k.split('.', 1)[1] for k in o.ek_kimlikleri) or '∅'}"
                    for o in sonuc.okumalar[:3]
                )
                _kaydet(
                    ornekler,
                    ayrinti,
                    f"OKUMA  {uretim.yuzey:22} ← {girdi.kok} {'+'.join(uretim.ek_kimlikleri) or '∅'}"
                    f"   bulunan: {bulunanlar}",
                )
                continue

            if not any(
                frozenset(x.kural_id for x in o.olaylar) == uretim.kural_kimlikleri
                for o in eslesen
            ):
                sayac["OLAY"] += 1
                bulunan = sorted(frozenset(x.kural_id for x in eslesen[0].olaylar))
                _kaydet(
                    ornekler,
                    ayrinti,
                    f"OLAY   {uretim.yuzey:22} ← {girdi.kok}"
                    f"   üretilen: {sorted(uretim.kural_kimlikleri)}  çözümlenen: {bulunan}",
                )
                continue

            sayac["TAMAM"] += 1

    return sayac, ornekler


def _kaydet(ornekler: list[str], tavan: int, satir: str) -> None:
    if len(ornekler) < tavan:
        ornekler.append(satir)


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--ornek", type=int, default=2000, help="taranacak kök sayısı")
    ayristirici.add_argument("--hepsi", action="store_true", help="tüm sözlüğü tara")
    ayristirici.add_argument("--azami-ek", type=int, default=3)
    ayristirici.add_argument("--tavan", type=int, default=120, help="kök başına en fazla yüzey")
    ayristirici.add_argument("--ayrinti", type=int, default=40, help="gösterilecek örnek sayısı")
    arg = ayristirici.parse_args(argv)

    baslangic = time.perf_counter()
    sayac, ornekler = tara(
        ornek=None if arg.hepsi else arg.ornek,
        azami_ek=arg.azami_ek,
        tavan=arg.tavan,
        ayrinti=arg.ayrinti,
    )
    sure = time.perf_counter() - baslangic

    toplam = sayac["uretim"]
    bozuk = sayac["KAYIP"] + sayac["OKUMA"] + sayac["OLAY"]
    print(f"\n{toplam:,} üretim taranmış ({sure:.1f} sn, {sure / max(toplam, 1) * 1000:.2f} ms/vaka)")
    print(f"  TAMAM  {sayac['TAMAM']:>8,}")
    print(f"  KAYIP  {sayac['KAYIP']:>8,}   üretilen yüzey hiç çözümlenemedi")
    print(f"  OKUMA  {sayac['OKUMA']:>8,}   çözümlendi ama o türetim yolu bulunamadı")
    print(f"  OLAY   {sayac['OLAY']:>8,}   yol bulundu ama olay kümesi tutmadı")
    oran = (toplam - bozuk) / toplam * 100 if toplam else 100.0
    print(f"\n  gidiş-dönüş bütünlüğü: {oran:.4f}%")

    if ornekler:
        print(f"\nörnekler (ilk {len(ornekler)}):")
        for satir in ornekler:
            print(f"  {satir}")

    return 1 if bozuk else 0


if __name__ == "__main__":
    sys.exit(main())
