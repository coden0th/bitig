"""Deneme arayüzü.

    .venv/bin/python -m bitig "Kitabı masaya bıraktım"
    .venv/bin/python -m bitig --json "burnu"
    echo "ağzı açık kaldı" | .venv/bin/python -m bitig

Motorun dış API'si `bitig.cozumleyici.cozumle(cumle)`; bu dosya yalnızca onu
insan gözüyle bakılabilir hâle getirir.
"""

from __future__ import annotations

import sys

from bitig.cozumleyici import cozumle
from bitig.sozlesme import KelimeSonucu


def _yaz(kelime: KelimeSonucu) -> None:
    if kelime.cozumlenemedi:
        print(f"\n{kelime.kelime}")
        print("   çözümlenemedi (Dilim 1 yalnızca ad çekimini kapsar; fiiller henüz yok)")
        return

    if kelime.olayda_belirsiz:
        isaret = "  ⚠ OLAYDA BELİRSİZ — bağlam olmadan karar verilemez"
    elif kelime.belirsiz:
        isaret = "  [belirsiz, ama okumalar aynı olayları üretiyor]"
    else:
        isaret = ""
    print(f"\n{kelime.kelime}{isaret}")
    if kelime.okumalar:
        kesin = ", ".join(sorted(kelime.kesin_olaylar)) or "yok"
        print(f"   kesin olaylar: {kesin}")

    for okuma in kelime.okumalar:
        ekler = " + ".join(okuma.ekler) if okuma.ekler else "∅"
        kimlikler = ", ".join(okuma.ek_kimlikleri) or "—"
        print(f"   {okuma.kok} ({okuma.tur})  +  {ekler}")
        print(f"      ekler : {kimlikler}")
        print(f"      izi   : {' → '.join(okuma.turetim_izi)}")
        if not okuma.olaylar:
            print("      olay  : yok")
        for olay in okuma.olaylar:
            k = olay.kanit
            degisim = f"{k.once or '∅'} → {k.sonra or '∅'}"
            print(
                f"      olay  : {olay.kural_id}  {olay.olay}\n"
                f"              kanıt: {k.govde!r} içinde konum {k.konum}, "
                f"{degisim}, tetikleyen ek {k.tetikleyen_ek!r}\n"
                f"              kaynak: {olay.kaynak}, güven: {olay.guven}"
            )


def main(argv: list[str]) -> int:
    json_modu = "--json" in argv
    girdiler = [a for a in argv[1:] if not a.startswith("--")]

    if not girdiler:
        if sys.stdin.isatty():
            print(__doc__)
            return 0
        girdiler = [satir for satir in sys.stdin.read().splitlines() if satir.strip()]

    for cumle in girdiler:
        sonuc = cozumle(cumle)
        if json_modu:
            print(sonuc.json(indent=2))
            continue
        print(f"── {cumle}")
        for kelime in sonuc:
            _yaz(kelime)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
