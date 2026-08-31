"""`baglam.py`'nin bağlam seçimini gerçek cümlelerde ölçer.

Diğer `harness.*_coz` araçlarından farklı: burada "doğru cevap" sabit bir
ÖSYM cevap anahtarı değil, **beklenen okuma türü** (`beklenen_ipucu` — okuma
açıklamasında geçmesi gereken bir alt dize, örn. "Belirtme hâli"). Model
seçtiği okumanın açıklaması bu ipucunu taşıyorsa DOGRU.

Bu araç **ağ çağrısı yapar ve ücretlidir** — normal `pytest` koşusuna dahil
değildir, elle çalıştırılır. `harness/model.py`'nin anahtar kurulumunu
gerektirir.

Çalıştırma:  .venv/bin/python -m harness.baglam_coz
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from baglam import BaglamHatasi, okuma_aciklamasi, sec
from bitig.cozumleyici import kelimeyi_cozumle
from harness.model import ModelHatasi, anahtar_var_mi, anahtar_yardimi

ALTIN_DIZINI = Path(__file__).resolve().parent.parent / "altin"
SORU_DOSYASI = "baglam_sorulari.jsonl"


def kumeyi_oku(yol: Path) -> list[dict]:
    with yol.open(encoding="utf-8") as dosya:
        return [json.loads(satir) for satir in dosya if satir.strip()]


def coz(vaka: dict) -> tuple[str, str]:
    """Tek bir vakayı çözer. (durum, ayrıntı) döner.

    durum ∈ DOGRU | YANLIS | HATA
    """
    sonuc = kelimeyi_cozumle(vaka["kelime"])
    try:
        secim = sec(vaka["cumle"], vaka["kelime"], sonuc)
    except (BaglamHatasi, ModelHatasi) as e:
        return "HATA", str(e)

    if secim is None:
        return "HATA", "kelime belirsiz değil (tek/hiç okuma)"

    aciklama = okuma_aciklamasi(secim.secilen_okuma(sonuc))
    if vaka["beklenen_ipucu"] in aciklama:
        return "DOGRU", f"{aciklama}  —  {secim.gerekce}"
    return "YANLIS", f"beklenen {vaka['beklenen_ipucu']!r} ama seçilen: {aciklama}  —  {secim.gerekce}"


def main() -> int:
    if not anahtar_var_mi():
        print(anahtar_yardimi(), file=sys.stderr)
        return 2

    yol = ALTIN_DIZINI / SORU_DOSYASI
    if not yol.exists():
        print(f"soru dosyası yok: {yol}", file=sys.stderr)
        return 2

    vakalar = kumeyi_oku(yol)
    sayac = {"DOGRU": 0, "YANLIS": 0, "HATA": 0}

    print(f"\n{len(vakalar)} vaka çözülüyor\n")

    for vaka in vakalar:
        durum, ayrinti = coz(vaka)
        sayac[durum] += 1
        isaret = {"DOGRU": "✓", "YANLIS": "✗", "HATA": "!"}[durum]
        print(f"{isaret} {vaka['kimlik']:<20} {durum:<8} {ayrinti}")

    toplam = len(vakalar)
    print("─" * 70)
    print(f"  doğru {sayac['DOGRU']}  ·  yanlış {sayac['YANLIS']}  ·  hata {sayac['HATA']}")
    if toplam:
        print(f"\n  başarım: {sayac['DOGRU'] / toplam * 100:.1f}%")

    return 1 if (sayac["YANLIS"] or sayac["HATA"]) else 0


if __name__ == "__main__":
    sys.exit(main())
