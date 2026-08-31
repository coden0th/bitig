"""Kapsam taraması: modelden metin al, motorun çözemediklerini listele.

Bu aracın değeri, **modele hiç güvenmemesidir**. Model yalnızca Türkçe cümle
yazar; hangi kelimede hangi ses olayı olduğuna dair tek bir iddiası kullanılmaz.
Ölçüt tamamen motorun kendi içindedir: çözemediği kelime bir kapsam boşluğudur.

Bu yüzden altın kümeden ve anlaşmazlık taramasından farklı bir hata sınıfı bulur:

    altın küme        → bildiğimiz vakalarda doğru muyuz?
    gidiş-dönüş       → kendi ürettiğimizi geri okuyabiliyor muyuz?
    kapsam taraması   → gerçek Türkçe'nin ne kadarını görebiliyoruz?   ← burası

Çözümlenemeyen her kelime üç şeyden biridir ve üçü de değerlidir:
sözlükte eksik kök, grafta eksik ek, ya da modelin uydurduğu bir sözcük.

Çalıştırma:
    export ZAI_API_KEY='...'
    .venv/bin/python -m harness.kapsam --tur 20
    .venv/bin/python -m harness.kapsam --dosya metin.txt   # model olmadan
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from bitig.cozumleyici import _KELIME_DESENI, kelimeyi_cozumle
from bitig import fonetik
from harness import model as llm

SISTEM = (
    "Sen Türkçe dil bilgisi materyali hazırlayan bir yardımcısın. "
    "Yalnızca istenen metni üret, açıklama ve başlık ekleme."
)

KONULAR = [
    "okul ve eğitim", "doğa ve mevsimler", "bilim ve teknoloji", "sanat ve edebiyat",
    "tarih ve uygarlıklar", "spor", "sağlık ve beslenme", "aile ve gündelik hayat",
    "şehir hayatı ve ulaşım", "hayvanlar", "müzik", "yemek ve mutfak",
    "iş hayatı", "çevre sorunları", "uzay ve gökbilim", "duygular ve ilişkiler",
    "seyahat", "kitaplar ve okuma", "hava durumu", "geleneksel el sanatları",
]


def _istem(konu: str, adet: int) -> str:
    return (
        f"{konu} konusunda {adet} adet Türkçe cümle yaz. "
        "Cümleler TYT Türkçe paragraf sorularındaki gibi doğal ve akıcı olsun. "
        "Çekimli sözcükler bol olsun: iyelik, hâl ekleri, farklı zaman ve kipler kullan. "
        "Her satıra bir cümle yaz, numaralandırma yapma."
    )


def metin_topla(tur_sayisi: int, cumle_basina: int) -> list[str]:
    cumleler: list[str] = []
    for i in range(tur_sayisi):
        konu = KONULAR[i % len(KONULAR)]
        print(f"  [{i + 1}/{tur_sayisi}] {konu} ...", flush=True)
        try:
            yanit = llm.sor(_istem(konu, cumle_basina), sistem=SISTEM)
        except llm.ModelHatasi as hata:
            print(f"      atlandı: {hata}")
            continue
        yeni = llm.satirlari_ayikla(yanit)
        cumleler.extend(yeni)
        print(f"      +{len(yeni)} cümle")
    return cumleler


def tara(cumleler: list[str]) -> tuple[Counter, Counter, list[tuple[str, str]]]:
    sayac = Counter()
    cozulemeyen: Counter = Counter()
    ornekler: list[tuple[str, str]] = []
    gorulen: set[str] = set()

    for cumle in cumleler:
        for eslesme in _KELIME_DESENI.finditer(cumle):
            kelime = eslesme.group()
            anahtar = fonetik.kucult(kelime)
            sayac["kelime"] += 1
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            sayac["farkli"] += 1

            sonuc = kelimeyi_cozumle(kelime)
            if sonuc.cozumlenemedi:
                cozulemeyen[anahtar] += 1
                if len(ornekler) < 400:
                    ornekler.append((kelime, cumle))
            elif sonuc.olayda_belirsiz:
                sayac["olayda_belirsiz"] += 1

    return sayac, cozulemeyen, ornekler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tur", type=int, default=10, help="kaç model çağrısı")
    ap.add_argument("--cumle", type=int, default=40, help="çağrı başına cümle")
    ap.add_argument("--dosya", type=Path, help="model yerine hazır metin dosyası")
    ap.add_argument("--kaydet", type=Path, help="toplanan cümleleri buraya yaz")
    arg = ap.parse_args(argv)

    if arg.dosya:
        cumleler = [s for s in arg.dosya.read_text(encoding="utf-8").splitlines() if s.strip()]
        print(f"{arg.dosya} → {len(cumleler)} satır")
    else:
        if not llm.anahtar_var_mi():
            print(
                llm.anahtar_yardimi() + "\n\nModel olmadan denemek için:  --dosya metin.txt",
                file=sys.stderr,
            )
            return 2
        print(f"Modelden metin toplanıyor ({arg.tur} tur × {arg.cumle} cümle)...")
        cumleler = metin_topla(arg.tur, arg.cumle)

    if arg.kaydet:
        arg.kaydet.write_text("\n".join(cumleler), encoding="utf-8")
        print(f"\ncümleler kaydedildi: {arg.kaydet}")

    sayac, cozulemeyen, ornekler = tara(cumleler)

    toplam = sayac["farkli"]
    eksik = len(cozulemeyen)
    print(f"\n{len(cumleler):,} cümle · {sayac['kelime']:,} sözcük · {toplam:,} farklı sözcük")
    print(f"  çözümlenen        : {toplam - eksik:,}")
    print(f"  ÇÖZÜMLENEMEYEN    : {eksik:,}")
    print(f"  olayda belirsiz   : {sayac['olayda_belirsiz']:,}")
    if toplam:
        print(f"\n  kapsam: {(toplam - eksik) / toplam * 100:.2f}%")

    if cozulemeyen:
        print("\nçözümlenemeyenler (sıklığa göre):")
        for kelime, adet in cozulemeyen.most_common(60):
            print(f"  {kelime:24} ×{adet}")
        print(
            "\nHer biri şunlardan biri: sözlükte eksik kök, grafta eksik ek, "
            "ya da modelin uydurduğu sözcük. Üçü de incelenmeye değer."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
