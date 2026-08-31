"""Anlaşmazlık harness'ı: BitigAI motoru vs bağımsız bir çözümleyici.

Altın küme elle yazıldığı için küçüktür ve yalnızca düşünebildiğimiz vakaları
kapsar. Anlaşmazlık taraması bu kör noktayı kapatır: bağımsız bir çözümleyiciyle
aynı girdiler çözülür ve **yalnızca çelişkiler** incelenir. Çelişki listesi bir
bug kuyruğudur, doğruluk ölçüsü değildir — zeyrek hakem değil, ikinci görüştür.

zeyrek yalnızca burada, geliştirme bağımlılığı olarak kullanılır. Üretim hattında
hiç yoktur (bkz. CLAUDE.md §1.5 ve plan kararı).

Aynı arayüze ileride LLM hakemi de takılacak: `_dis_gorus()` yerine model
çağrısı konur, gerisi değişmez.

Çalıştırma:
    .venv/bin/python -m harness.anlasmazlik              # altın kümedeki kelimeler
    .venv/bin/python -m harness.anlasmazlik metin.txt    # serbest metin
"""

from __future__ import annotations

import sys
from pathlib import Path

from bitig import fonetik
from bitig.cozumleyici import kelimeyi_cozumle
from bitig.sozluk.ayristirici import MASTAR_EKLERI
from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku

#: Karşılaştırmaya giren sözcük türleri. Motorun kapsamı büyüdükçe bu küme de
#: büyümeli — aksi hâlde kapsam dışı bırakılan okumalar "biz bulamadık" gibi
#: görünüp sahte çelişki üretir.
KAPSANAN_TURLER = {"Noun", "Adj", "Dup", "Num", "Pron", "Verb"}


def _dis_gorus(analiz_edici, kelime: str) -> set[str]:
    """Bağımsız çözümleyicinin bulduğu kökler.

    zeyrek'in yapısal API'si kullanılır; biçimlenmiş metni ayrıştırmak yasaktır
    (docs/decisions.md §6) — zaten kırılgan olurdu.
    """
    kokler: set[str] = set()
    for grup in analiz_edici.analyze(kelime) or []:
        for cozum in grup or []:
            if not cozum.lemma:
                continue
            lemma = fonetik.kucult(cozum.lemma)
            kokler.add(lemma)
            # zeyrek fiil lemmasını mastarlı verir ("gelmek"), biz kökü ("gel").
            # Bu bir temsil farkıdır, görüş ayrılığı değil; normalleştirilmezse
            # her fiil sahte çelişki olarak listelenir.
            if len(lemma) > 3 and lemma.endswith(MASTAR_EKLERI):
                kokler.add(lemma[:-3])
    return kokler


def tara(kelimeler: list[str]) -> list[tuple[str, set[str], set[str]]]:
    import logging

    import zeyrek

    # zeyrek çözümleme sırasında hata ayıklama kayıtlarını basar ("APPENDING
    # RESULT: ..."). Rapor okunmaz hâle geldiği için susturuluyor.
    logging.getLogger("zeyrek").setLevel(logging.WARNING)
    logging.getLogger().setLevel(logging.WARNING)

    analiz_edici = zeyrek.MorphAnalyzer()
    celiskiler = []

    for kelime in kelimeler:
        bizim = {o.kok for o in kelimeyi_cozumle(kelime).okumalar if o.tur in KAPSANAN_TURLER}
        onlarin = _dis_gorus(analiz_edici, kelime)

        # Fiil okumaları bu dilimin kapsamı dışında; onları çelişki saymamak için
        # dış görüşten yalnızca bizim bulabileceğimiz kökleri karşılaştırırız.
        if not bizim and not onlarin:
            continue
        if bizim & onlarin:
            continue  # en az bir kökte anlaşıyorlar, çelişki yok
        celiskiler.append((kelime, bizim, onlarin))

    return celiskiler


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        metin = Path(argv[1]).read_text(encoding="utf-8")
        from bitig.cozumleyici import _KELIME_DESENI

        kelimeler = [e.group() for e in _KELIME_DESENI.finditer(metin)]
    else:
        kelimeler = [
            kayit["kelime"]
            for yol in sorted(ALTIN_DIZINI.glob("*.jsonl"))
            if yol.name not in ("sorular.jsonl", "fiil_sorulari.jsonl", "isim_sorulari.jsonl", "baglam_sorulari.jsonl", "anlatim_sorulari.jsonl", "noktalama_sorulari.jsonl", "sozcukte_yapi_sorulari.jsonl")
            for kayit in kumeyi_oku(yol)
        ]

    print(f"{len(kelimeler)} kelime taranıyor (zeyrek yükleniyor, biraz sürer)...")
    celiskiler = tara(kelimeler)

    print(f"\n{len(celiskiler)} çelişki / {len(kelimeler)} kelime\n")
    for kelime, bizim, onlarin in celiskiler:
        biz_metin = ", ".join(sorted(bizim)) or "—"
        onlar_metin = ", ".join(sorted(onlarin)) or "—"
        print(f"  {kelime:16} biz: {biz_metin:<24} zeyrek: {onlar_metin}")

    if celiskiler:
        print("\nBunlar hata listesi değil, İNCELEME kuyruğudur.")
        print("Her biri için: hangimiz haklıyız? Haklı taraf altın kümeye yazılır.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
