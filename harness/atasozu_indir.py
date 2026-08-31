"""Atasözü/deyim sözlüğünü indirir, `veri/atasozu_deyim.json`ı üretir.

**Ağ çağrısı yapar, elle çalıştırılır.** Kaynak `sozcukatlasi.com`'un
`data.json`'ı — TDK'nin kendi resmi atasözü/deyim API'siyle (`sozluk.gov.tr/
atasozu?ara=`) çapraz doğrulandı, içerik birebir aynı (sozcukatlasi TDK
verisini toplu JSON hâlinde sunuyor; TDK'nin kendi API'si yalnızca tekli
arama destekliyor, `gts` uç noktasıyla aynı sınır). Kamu kurumunun resmi
sözlük içeriği, `veri/zemberek/` ile aynı gerekçeyle yerel dondurulmuş kopya
olarak tutuluyor — CLAUDE.md §10 "telif hakkı olan yayınevi" yasağı özel
yayınevi içeriği içindir, bu kamu kaynağıdır.

robots.txt açıkça izin veriyor (`Allow: /`), tek bir statik dosya indiriliyor
(13k ayrı sorgu değil) — TDK Track B'deki "API'yi bombardımana tutmama"
endişesi burada geçerli değil.

Kullanım:
    .venv/bin/python -m harness.atasozu_indir
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

KAYNAK_URL = "https://sozcukatlasi.com/atasozleri-ve-deyimler-sozlugu/data.json"
HEDEF_YOLU = Path(__file__).resolve().parent.parent / "veri" / "atasozu_deyim.json"
BASLIKLAR = {"User-Agent": "Mozilla/5.0 (BitigAI sozluk senkronizasyon araci)"}

_TUR_HARITASI = {"A": "atasozu", "D": "deyim"}


def indir() -> list[dict]:
    istek = urllib.request.Request(KAYNAK_URL, headers=BASLIKLAR)
    with urllib.request.urlopen(istek, timeout=30) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def donustur(ham_veri: list[dict]) -> dict:
    kayitlar = [
        {"soz": k["s"], "anlam": k["a"], "tur": _TUR_HARITASI.get(k["t"], k["t"])} for k in ham_veri
    ]
    return {
        "surum": "1.0.0",
        "aciklama": [
            "Atasözü/deyim sözlüğü — TDK'nin resmi içeriği, yerel dondurulmuş",
            "kopya (`veri/zemberek/` ile aynı desen). Kaynak: sozcukatlasi.com'un",
            "data.json'ı, TDK'nin kendi `sozluk.gov.tr/atasozu` API'siyle çapraz",
            "doğrulandı (içerik birebir aynı — TDK'nin kendi API'si toplu",
            "indirme sunmuyor). Yenileme: `harness/atasozu_indir.py`.",
        ],
        "kaynak_url": KAYNAK_URL,
        "indirme_tarihi": time.strftime("%Y-%m-%d"),
        "kayit_sayisi": len(kayitlar),
        "kayitlar": kayitlar,
    }


def main() -> int:
    print(f"İndiriliyor: {KAYNAK_URL}")
    try:
        ham_veri = indir()
    except urllib.error.URLError as hata:
        print(f"HATA: {hata}", file=sys.stderr)
        return 2

    veri = donustur(ham_veri)
    HEDEF_YOLU.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{veri['kayit_sayisi']} kayıt indirildi -> {HEDEF_YOLU}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
