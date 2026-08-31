"""EBA / OGM Materyal kitap sayfalarını indirir.

Kitap sayfaları JPEG görüntü olarak sunulur; uygulamanın kendisi Angular SPA
olduğu için HTML'den içerik çıkmaz. Doğrudan CDN'den çekmek tek pratik yol.

**Dosya numarası ile kitap sayfası arasında kayma vardır.** Bu kitapta
`dosya = kitap sayfası + 2` (kitap s.45 → 47.jpg). Kayma her kitapta farklı
olabilir; içindekiler sayfasıyla bir sayfayı karşılaştırıp doğrulayın.

İndirilen görüntüler depoya konmaz — MEB'in materyalidir, biz yalnızca
sorularını altın kümeye aktarırız (`altin/sorular.jsonl`).

Kullanım:
    .venv/bin/python -m harness.eba_indir --kitap tyt/tde --sayfa 47 56 --hedef /tmp/eba
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from pathlib import Path

CDN = "https://ogm-large-cdn.eba.gov.tr/ogm-materyal/konu-pekistirme"
AJAN = "Mozilla/5.0"


def indir(kitap: str, ilk: int, son: int, hedef: Path, bekleme: float = 0.4) -> int:
    hedef.mkdir(parents=True, exist_ok=True)
    sayi = 0
    for no in range(ilk, son + 1):
        yol = hedef / f"{no}.jpg"
        if yol.exists():
            print(f"  {no}.jpg  (zaten var)")
            continue
        url = f"{CDN}/{kitap}/files/mobile/{no}.jpg"
        istek = urllib.request.Request(url, headers={"User-Agent": AJAN})
        try:
            with urllib.request.urlopen(istek, timeout=60) as yanit:
                veri = yanit.read()
        except Exception as hata:  # noqa: BLE001 — hangi sayfa düştü görünsün
            print(f"  {no}.jpg  HATA: {hata}")
            continue
        yol.write_bytes(veri)
        print(f"  {no}.jpg  {len(veri) // 1024} KB")
        sayi += 1
        time.sleep(bekleme)  # sunucuyu yormamak için
    return sayi


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kitap", default="tyt/tde", help="CDN yolundaki kitap kimliği")
    ap.add_argument("--sayfa", nargs=2, type=int, required=True, metavar=("İLK", "SON"))
    ap.add_argument("--hedef", type=Path, required=True)
    arg = ap.parse_args(argv)

    print(f"{arg.kitap}  sayfa {arg.sayfa[0]}-{arg.sayfa[1]} → {arg.hedef}")
    sayi = indir(arg.kitap, arg.sayfa[0], arg.sayfa[1], arg.hedef)
    print(f"\n{sayi} yeni sayfa indirildi.")
    print("Görüntüler okunup sorular altin/sorular.jsonl biçimine aktarılmalı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
