"""ÖSYM politika katmanı.

Motor saf dilbilim üretir ve bu dosyayı bilmez (CLAUDE.md §1.4). Politika, motorun
çıktısının **üzerine** uygulanır ve onu değiştirmez; iki görüşü yan yana koyar.

Neden iki görüş:

    çevresi   dilbilim → olay yok     ("çevre" bugün bağımsız bir köktür)
              ÖSYM     → ünlü düşmesi (çevir + e; sözcüğün tarihine bakar)

İkisi de kendi çerçevesinde doğrudur. Motorun ÖSYM'ye göre "düzeltilmesi" yanlış
olurdu: o zaman dilbilimsel doğruluğu kaybederdik ve kural ÖSYM her yorum
değiştirdiğinde motorun içinde aranırdı. v1'in Kural 9'undaki ÖSYM notu tam
olarak bu hataydı.

`mod` hangi görüşün *geçerli* sayılacağını belirler, diğerini silmez:

    OSYM     → sınav bağlamı; ÖSYM'nin saydığı olaylar geçerli
    DILBILIM → varsayılan; motorun ürettiği geçerli

Her iki modda da `ayrisiyor_mu` doğruysa çıktıda ikisi de görünür. Kullanıcıya
"burada ÖSYM farklı düşünüyor" diyebilmek, sessizce birini seçmekten iyidir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from bitig.sozlesme import KelimeSonucu, kural_adi

POLITIKA_YOLU = Path(__file__).resolve().parent.parent / "veri" / "osym_politikasi.json"


class Mod(StrEnum):
    #: Motorun dilbilimsel çıktısı geçerli. Varsayılan.
    DILBILIM = "dilbilim"
    #: ÖSYM'nin saydığı olaylar geçerli. Sınav/soru üretimi bağlamı.
    OSYM = "osym"


@dataclass(frozen=True, slots=True)
class PolitikaNotu:
    """Politikanın motordan ayrıldığı tek bir nokta."""

    kural_id: str
    olay: str
    #: "eklendi" | "kaldirildi"
    yon: str
    kok: str
    coz: str
    gerekce: str
    kaynak: str

    def __str__(self) -> str:
        ok = "+" if self.yon == "eklendi" else "−"
        return f"{ok} {self.olay} ({self.coz}) — {self.gerekce}"


@dataclass(frozen=True, slots=True)
class Gorus:
    """Bir sözcüğün iki çerçevedeki okunuşu."""

    kelime: str
    dilbilim: frozenset[str]
    osym: frozenset[str]
    notlar: tuple[PolitikaNotu, ...] = ()

    @property
    def ayrisiyor_mu(self) -> bool:
        return self.dilbilim != self.osym

    def gecerli(self, mod: Mod = Mod.DILBILIM) -> frozenset[str]:
        return self.osym if mod is Mod.OSYM else self.dilbilim

    def sozluge(self) -> dict:
        return {
            "kelime": self.kelime,
            "dilbilim": sorted(self.dilbilim),
            "osym": sorted(self.osym),
            "ayrisiyor": self.ayrisiyor_mu,
            "notlar": [
                {
                    "kural_id": n.kural_id,
                    "olay": n.olay,
                    "yon": n.yon,
                    "coz": n.coz,
                    "gerekce": n.gerekce,
                    "kaynak": n.kaynak,
                }
                for n in self.notlar
            ],
        }


@lru_cache(maxsize=1)
def politika() -> dict:
    return json.loads(POLITIKA_YOLU.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _sozluklesmis() -> dict[str, list[dict]]:
    kayitlar: dict[str, list[dict]] = {}
    for kayit in politika().get("sozluklesmis_turetim", []):
        kayitlar.setdefault(kayit["kok"], []).append(kayit)
    return kayitlar


@lru_cache(maxsize=1)
def _saymaz() -> dict[str, list[dict]]:
    kayitlar: dict[str, list[dict]] = {}
    for kayit in politika().get("saymaz", []):
        kayitlar.setdefault(kayit["kok"], []).append(kayit)
    return kayitlar


def gorus(sonuc: KelimeSonucu) -> Gorus:
    """Motor çıktısına ÖSYM politikasını uygular; iki görüşü birden döner.

    Motor çıktısına dokunulmaz — `sonuc` değişmez, yeni bir nesne üretilir.
    """
    dilbilim = frozenset(sonuc.olasi_olaylar)
    osym = set(dilbilim)
    notlar: list[PolitikaNotu] = []

    kokler = {o.kok for o in sonuc.okumalar}

    for kok in sorted(kokler):
        for kayit in _sozluklesmis().get(kok, []):
            if kayit["olay"] in osym:
                continue  # motor zaten buluyor, politikaya gerek yok
            osym.add(kayit["olay"])
            notlar.append(
                PolitikaNotu(
                    kural_id=kayit["olay"],
                    olay=kural_adi(kayit["olay"]),
                    yon="eklendi",
                    kok=kok,
                    coz=kayit["coz"],
                    gerekce=kayit["gerekce"],
                    kaynak=kayit["kaynak"],
                )
            )
        for kayit in _saymaz().get(kok, []):
            if kayit["olay"] not in osym:
                continue
            osym.discard(kayit["olay"])
            notlar.append(
                PolitikaNotu(
                    kural_id=kayit["olay"],
                    olay=kural_adi(kayit["olay"]),
                    yon="kaldirildi",
                    kok=kok,
                    coz=kayit.get("coz", ""),
                    gerekce=kayit["gerekce"],
                    kaynak=kayit["kaynak"],
                )
            )

    return Gorus(
        kelime=sonuc.kelime,
        dilbilim=dilbilim,
        osym=frozenset(osym),
        notlar=tuple(notlar),
    )
