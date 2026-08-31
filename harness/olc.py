"""Altın kümeye karşı kural bazında precision/recall ölçümü.

Tek bir "doğruluk" yüzdesi raporlanmaz (CLAUDE.md §1.3). Bir motorun %92
doğruluğu, hangi kuralın çöktüğünü gizlediği için işe yaramaz; kural bazında
iki sütun gizlemez.

Ölçüt: bir kelimenin ürettiği olay kümesi = **tüm okumalardaki** olayların
birleşimi. Sebep: belirsizlik korunuyor, ve bir soru üretilirken herhangi bir
okumanın ürettiği olay öğrenciye gösterilebilir hâle gelir; dolayısıyla yanlış
pozitif hangi okumadan gelirse gelsin yanlış pozitiftir.

Çalıştırma:  .venv/bin/python -m harness.olc
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field

from bitig.cozumleyici import kelimeyi_cozumle
from bitig.sozlesme import kural_haritasi
from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku


@dataclass
class Sayac:
    dogru_pozitif: int = 0
    yanlis_pozitif: int = 0
    yanlis_negatif: int = 0
    #: Örnek vakalar — rapor okunurken hangi kelimenin battığı görünsün.
    yp_ornekleri: list[str] = field(default_factory=list)
    yn_ornekleri: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float | None:
        payda = self.dogru_pozitif + self.yanlis_pozitif
        return self.dogru_pozitif / payda if payda else None

    @property
    def recall(self) -> float | None:
        payda = self.dogru_pozitif + self.yanlis_negatif
        return self.dogru_pozitif / payda if payda else None


def _yuzde(deger: float | None) -> str:
    return "  —  " if deger is None else f"{deger * 100:5.1f}"


def olc(kayitlar: list[dict]) -> tuple[dict[str, Sayac], list[str], list[str]]:
    sayaclar: dict[str, Sayac] = defaultdict(Sayac)
    cozumlenemeyen: list[str] = []
    hatali_kelimeler: list[str] = []

    for kayit in kayitlar:
        kelime = kayit["kelime"]
        beklenen = set(kayit["beklenen"])

        sonuc = kelimeyi_cozumle(kelime)
        if sonuc.cozumlenemedi:
            cozumlenemeyen.append(kelime)
            # Çözümlenemeyen kelime tüm beklenen olayları kaçırmış sayılır.
            for kural_id in beklenen:
                sayaclar[kural_id].yanlis_negatif += 1
                sayaclar[kural_id].yn_ornekleri.append(f"{kelime} (çözümlenemedi)")
            continue

        uretilen = {olay.kural_id for olay in sonuc.olaylar}

        # Gerçek morfolojik belirsizlikten doğan olaylar yanlış pozitif sayılmaz.
        # Örnek: "masada" asıl okumada masa+da'dır ama "masat+a" da geçerlidir ve
        # yumuşama üretir. Motor haklıdır; bağlamsız ayrım yapılamaz. Bu vakalar
        # gizlenmez, altın kümede `belirsiz_kabul` ile açıkça yazılır.
        kabul = set(kayit.get("belirsiz_kabul", []))
        uretilen -= kabul - beklenen

        if uretilen != beklenen:
            hatali_kelimeler.append(kelime)

        for kural_id in uretilen & beklenen:
            sayaclar[kural_id].dogru_pozitif += 1
        for kural_id in uretilen - beklenen:
            sayaclar[kural_id].yanlis_pozitif += 1
            sayaclar[kural_id].yp_ornekleri.append(kelime)
        for kural_id in beklenen - uretilen:
            sayaclar[kural_id].yanlis_negatif += 1
            sayaclar[kural_id].yn_ornekleri.append(kelime)

    return sayaclar, cozumlenemeyen, hatali_kelimeler


def rapor(sayaclar: dict[str, Sayac], toplam: int) -> None:
    kurallar = kural_haritasi()
    print(f"\n{'kural':<14} {'ad':<26} {'DP':>4} {'YP':>4} {'YN':>4}  {'prec':>5} {'rec':>5}")
    print("─" * 74)
    for kural_id in sorted(set(sayaclar) | set(kurallar)):
        s = sayaclar.get(kural_id, Sayac())
        if not (s.dogru_pozitif or s.yanlis_pozitif or s.yanlis_negatif):
            continue
        ad = kurallar.get(kural_id, {}).get("ad", "?")
        print(
            f"{kural_id:<14} {ad:<26} {s.dogru_pozitif:>4} {s.yanlis_pozitif:>4} "
            f"{s.yanlis_negatif:>4}  {_yuzde(s.precision):>5} {_yuzde(s.recall):>5}"
        )

    print("─" * 74)
    for kural_id in sorted(sayaclar):
        s = sayaclar[kural_id]
        if s.yp_ornekleri:
            print(f"  {kural_id} yanlış pozitif: {', '.join(s.yp_ornekleri[:8])}")
        if s.yn_ornekleri:
            print(f"  {kural_id} kaçırılan    : {', '.join(s.yn_ornekleri[:8])}")


def main() -> int:
    kotu = 0
    for yol in sorted(ALTIN_DIZINI.glob("*.jsonl")):
        if yol.name in ("sorular.jsonl", "fiil_sorulari.jsonl", "isim_sorulari.jsonl", "baglam_sorulari.jsonl", "anlatim_sorulari.jsonl", "noktalama_sorulari.jsonl", "sozcukte_yapi_sorulari.jsonl"):
            continue  # farklı şema (soru düzeyi); harness.soru_coz / harness.fiil_coz alanı
        kayitlar = kumeyi_oku(yol)
        sayaclar, cozumlenemeyen, hatali = olc(kayitlar)

        print(f"\n=== {yol.name} · {len(kayitlar)} kayıt ===")
        rapor(sayaclar, len(kayitlar))

        tam = len(kayitlar) - len(hatali)
        print(f"\n  olay kümesi birebir doğru: {tam}/{len(kayitlar)}")
        if cozumlenemeyen:
            print(f"  çözümlenemeyen ({len(cozumlenemeyen)}): {', '.join(cozumlenemeyen[:15])}")
        if hatali:
            print(f"  hatalı ({len(hatali)}): {', '.join(hatali[:15])}")

        kotu += len(hatali)

    return 1 if kotu else 0


if __name__ == "__main__":
    sys.exit(main())
