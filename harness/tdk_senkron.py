"""`veri/tdk_onbellek.json`ı TDK'den gelen sonuçlarla günceller.

**Ağ çağrısı yapar, elle çalıştırılır.** `[[yazim-motoru-plani]]`deki kabul
edilen strateji: önbellek + periyodik tazeleme. Çalışma zamanı (`yazim.py`)
TDK'ye hiç gitmez, yalnızca bu aracın ürettiği yerel dosyaya bakar.

Kullanım:

    # Belirli kelimeleri sorgula/güncelle
    .venv/bin/python -m harness.tdk_senkron kapı restorant restoran

    # Bir dosyadaki kelimeleri (satır başına bir kelime) sorgula
    .venv/bin/python -m harness.tdk_senkron --dosya kelimeler.txt

    # Önbellekteki TÜM kelimeleri yeniden sorgula (periyodik tazeleme)
    .venv/bin/python -m harness.tdk_senkron --tazele

Nezaket için sorgular arasına küçük bir gecikme konur — TDK'yi bombardımana
tutmayız. Zemberek'in ~29 bin kökünü toptan doldurmak (`[[yazim-motoru-plani]]`de
seçenek olarak anıldı) BİLEREK burada otomatik değildir: onu çalıştırmadan
önce kullanıcıyla süre/hacim üzerine ayrıca konuşulmalı (CLAUDE.md "Executing
actions with care").
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from bitig import fonetik
from bitig.cozumleyici import kelimeyi_cozumle
from harness.tdk_istemci import TdkHatasi, sorgula

ONBELLEK_YOLU = Path(__file__).resolve().parent.parent / "veri" / "tdk_onbellek.json"
GECIKME_SN = 0.3


def _onbellek_oku() -> dict:
    return json.loads(ONBELLEK_YOLU.read_text(encoding="utf-8"))


def _onbellek_yaz(veri: dict) -> None:
    veri["senkron_tarihi"] = time.strftime("%Y-%m-%d")
    ONBELLEK_YOLU.write_text(
        json.dumps(veri, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )


def _mastar_ekle(kok: str) -> str:
    """`kok` + doğru büyük ünlü uyumlu mastar eki (-mak/-mek)."""
    return kok + "m" + fonetik.uyumla_a(fonetik.son_unlu(kok)) + "k"


def _bare_fiil_koku_mu(kelime: str) -> bool:
    sonuc = kelimeyi_cozumle(kelime)
    if sonuc.cozumlenemedi:
        return False
    return any(ok.tur == "Verb" and not ok.ekler for ok in sonuc.okumalar)


def _sorgu_terimi(kelime: str) -> str:
    """TDK'ye gidecek gerçek sorgu — fiil kökleri için mastar eklenir.

    TDK sözlüğü fiilleri mastar (-mak/-mek) biçimiyle indeksler, motorumuzun
    kökü ise çıplak gövdedir ("anla" değil "anlamak"). Bu ayrım fark
    edilmeden sorgulanırsa HER fiil kökü yanlışlıkla "geçersiz" çıkar — bu
    oturumda 1696 kelimelik ilk taramada somut olarak gözlendi (306
    "geçersiz"in büyük kısmı bu yüzdendi, bkz. docs/decisions.md §6). Önbellek anahtarı
    yine çıplak kök olarak kalır — yalnızca TDK'ye giden SORGU değişir.
    """
    if _bare_fiil_koku_mu(kelime):
        return _mastar_ekle(kelime)
    return kelime


def senkronla(kelimeler: list[str]) -> dict:
    onbellek = _onbellek_oku()
    kayitlar = onbellek["kelimeler"]

    guncellenen = degisen = hata_sayisi = 0
    for i, kelime in enumerate(kelimeler, start=1):
        sorgu = _sorgu_terimi(kelime)
        try:
            sonuc = sorgula(sorgu)
        except TdkHatasi as e:
            print(f"  ! {kelime!r}: {e}", file=sys.stderr)
            hata_sayisi += 1
            continue

        onceki = kayitlar.get(kelime)
        yeni = {"gecerli": sonuc["gecerli"], "yonlendirme": sonuc["ilk_anlam_yonlendirme"]}
        if sorgu != kelime:
            yeni["sorgulanan"] = sorgu  # şeffaflık: hangi biçim TDK'ye gönderildi
        if onceki != yeni:
            degisen += 1
            if onceki is not None:
                print(f"  ~ {kelime!r}: {onceki} -> {yeni}")
        kayitlar[kelime] = yeni
        guncellenen += 1

        if i < len(kelimeler):
            time.sleep(GECIKME_SN)

    _onbellek_yaz(onbellek)
    print(f"\n{guncellenen} kelime sorgulandı, {degisen} değişti, {hata_sayisi} hata")
    return onbellek


def main() -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("kelimeler", nargs="*", help="sorgulanacak kelimeler")
    ayristirici.add_argument("--dosya", type=Path, help="satır başına bir kelime içeren dosya")
    ayristirici.add_argument(
        "--tazele", action="store_true", help="önbellekteki tüm kelimeleri yeniden sorgula"
    )
    args = ayristirici.parse_args()

    kelimeler: list[str] = list(args.kelimeler)
    if args.dosya:
        kelimeler.extend(
            satir.strip() for satir in args.dosya.read_text(encoding="utf-8").splitlines() if satir.strip()
        )
    if args.tazele:
        kelimeler.extend(_onbellek_oku()["kelimeler"].keys())

    kelimeler = list(dict.fromkeys(kelimeler))  # sırayı koru, tekrarı at
    if not kelimeler:
        ayristirici.print_help()
        return 2

    print(f"{len(kelimeler)} kelime TDK'ye soruluyor (aralarda {GECIKME_SN} sn gecikme)...\n")
    senkronla(kelimeler)
    return 0


if __name__ == "__main__":
    sys.exit(main())
