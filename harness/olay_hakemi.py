"""Ses olayı anlaşmazlığı: motor vs model, yalnızca çelişkiler.

`anlasmazlik.py` kökleri karşılaştırır; bu araç asıl önemsediğimiz şeyi
karşılaştırır: **hangi ses olayları var**.

Model hakem değildir. Cevabı doğruluk kaynağı olarak kullanılmaz, çünkü eşik
%100'dür ve LLM oraya çıkamaz. Yaptığı iş çelişki üretmektir: motorun ve modelin
ayrıştığı her kelime, ikimizden birinin hatalı olduğu bir vakadır ve insan
incelemesine değer. Anlaşılan vakalar hiç bakılmadan geçilir.

Çelişki listesi bir **bug kuyruğudur**, bir doğruluk yüzdesi değil. Çıkan her
maddede soru şudur: hangimiz haklıyız? Haklı taraf altın kümeye yazılır.

Çalıştırma:
    .venv/bin/python -m harness.olay_hakemi                 # altın kümeler
    .venv/bin/python -m harness.olay_hakemi --dosya metin.txt
    .venv/bin/python -m harness.olay_hakemi --kelime kitabı burnu hakkı
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bitig.cozumleyici import _KELIME_DESENI, kelimeyi_cozumle
from bitig.sozlesme import kural_haritasi
from harness import model as llm
from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku

#: Modelden istenen etiketler → kanonik kural kimlikleri. Model kural
#: kimliğimizi bilmez; Türkçe dil bilgisi adlarıyla konuşur ve burada eşlenir.
ETIKET_HARITASI = {
    "ünsüz yumuşaması": "SES.YUM.01",
    "ünlü düşmesi": "SES.UD.01",
    "ünsüz türemesi": "SES.UT.01",
    "kaynaştırma": "SES.KAY.01",
    "ünsüz benzeşmesi": "SES.BEN.01",
    "ünlü daralması": "SES.DAR.01",
}

TOPLU = 25  # tek çağrıda sorulacak kelime sayısı

SISTEM = (
    "Sen TYT Türkçe dil bilgisi uzmanısın. Yalnızca istenen JSON'u üret; "
    "açıklama, başlık veya kod bloğu işareti ekleme."
)


def _istem(kelimeler: list[str]) -> str:
    etiketler = "\n".join(f"  - {ad}" for ad in ETIKET_HARITASI)
    liste = "\n".join(f"  {k}" for k in kelimeler)
    return (
        "Aşağıdaki her sözcükte hangi ses olaylarının gerçekleştiğini belirle.\n\n"
        f"Kullanabileceğin etiketler (BUNLARIN DIŞINA ÇIKMA):\n{etiketler}\n\n"
        "Kurallar:\n"
        "  - Sözcük ek almamışsa ses olayı YOKTUR, boş liste ver.\n"
        "  - Yalnızca sözcüğün kendi türetiminde gerçekleşen olayları yaz.\n"
        "  - Kaynaştırma ünsüzünü ünsüz türemesi sayma, ayrı etikettir.\n"
        "  - Emin değilsen boş liste ver.\n\n"
        f"Sözcükler:\n{liste}\n\n"
        'Çıktı biçimi (yalnızca JSON): {"sözcük": ["etiket", ...], ...}'
    )


def _model_gorusu(kelimeler: list[str]) -> dict[str, set[str]]:
    ham = llm.sor(_istem(kelimeler), sistem=SISTEM, sicaklik=0.2)
    metin = ham.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        veri = json.loads(metin)
    except json.JSONDecodeError:
        baslangic, bitis = metin.find("{"), metin.rfind("}")
        if baslangic < 0 or bitis < 0:
            raise llm.ModelHatasi(f"JSON çıkarılamadı: {metin[:200]}") from None
        veri = json.loads(metin[baslangic : bitis + 1])

    sonuc: dict[str, set[str]] = {}
    for kelime, etiketler in veri.items():
        kimlikler = set()
        for etiket in etiketler or []:
            anahtar = str(etiket).strip().lower()
            for ad, kimlik in ETIKET_HARITASI.items():
                if ad in anahtar:
                    kimlikler.add(kimlik)
                    break
        sonuc[kelime] = kimlikler
    return sonuc


def tara(kelimeler: list[str]) -> tuple[list[tuple], int, int]:
    kurallar = kural_haritasi()
    celiskiler: list[tuple] = []
    karsilastirilan = 0
    atlanan = 0

    for i in range(0, len(kelimeler), TOPLU):
        obek = kelimeler[i : i + TOPLU]
        print(f"  [{i // TOPLU + 1}/{-(-len(kelimeler) // TOPLU)}] {len(obek)} sözcük...", flush=True)
        try:
            gorus = _model_gorusu(obek)
        except llm.ModelHatasi as hata:
            print(f"      atlandı: {hata}")
            atlanan += len(obek)
            continue

        for kelime in obek:
            if kelime not in gorus:
                atlanan += 1
                continue
            karsilastirilan += 1
            sonuc = kelimeyi_cozumle(kelime)
            bizim = set(sonuc.olasi_olaylar)
            onun = gorus[kelime]
            if bizim != onun:
                celiskiler.append((kelime, bizim, onun, sonuc.olayda_belirsiz))

    return celiskiler, karsilastirilan, atlanan


def _ad(kimlikler: set[str]) -> str:
    kurallar = kural_haritasi()
    return ", ".join(sorted(kurallar.get(k, {}).get("ad", k) for k in kimlikler)) or "—"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dosya", type=Path)
    ap.add_argument("--kelime", nargs="+")
    ap.add_argument("--azami", type=int, default=200, help="taranacak en fazla sözcük")
    arg = ap.parse_args(argv)

    if not llm.anahtar_var_mi():
        print(llm.anahtar_yardimi(), file=sys.stderr)
        return 2

    if arg.kelime:
        kelimeler = arg.kelime
    elif arg.dosya:
        metin = arg.dosya.read_text(encoding="utf-8")
        gorulen, kelimeler = set(), []
        for e in _KELIME_DESENI.finditer(metin):
            if e.group() not in gorulen:
                gorulen.add(e.group())
                kelimeler.append(e.group())
    else:
        kelimeler = [
            kayit["kelime"]
            for yol in sorted(ALTIN_DIZINI.glob("*.jsonl"))
            if yol.name not in ("sorular.jsonl", "fiil_sorulari.jsonl", "isim_sorulari.jsonl", "baglam_sorulari.jsonl", "anlatim_sorulari.jsonl", "noktalama_sorulari.jsonl", "sozcukte_yapi_sorulari.jsonl")
            for kayit in kumeyi_oku(yol)
        ]

    kelimeler = kelimeler[: arg.azami]
    print(f"{len(kelimeler)} sözcük karşılaştırılıyor...")
    celiskiler, karsilastirilan, atlanan = tara(kelimeler)

    print(f"\n{len(celiskiler)} çelişki / {karsilastirilan} karşılaştırma", end="")
    print(f" ({atlanan} atlandı)" if atlanan else "")

    if celiskiler:
        print()
        for kelime, bizim, onun, belirsiz in celiskiler:
            isaret = "  ⚠belirsiz" if belirsiz else ""
            print(f"  {kelime:16}{isaret}")
            print(f"      motor : {_ad(bizim)}")
            print(f"      model : {_ad(onun)}")
        print(
            "\nBu bir hata listesi DEĞİL, inceleme kuyruğudur.\n"
            "Her madde için: hangimiz haklıyız? Haklı taraf altın kümeye yazılır.\n"
            "Model burada hakem değil ikinci görüştür — cevabı doğruluk kaynağı sayılmaz."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
