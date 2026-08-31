"""Morfotaktik graf: hangi ek hangi durumdan sonra gelebilir.

Graf `veri/ekler.json` dosyasında durur. Bu modül onu yalnızca **yorumlar**;
hiçbir ek tanımı burada gömülü değildir (docs/decisions.md §6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from bitig.turetim import Ek

EKLER_YOLU = Path(__file__).resolve().parent.parent / "veri" / "ekler.json"


@dataclass(frozen=True, slots=True)
class Graf:
    #: Sözcük türü → o türün çekiminin başladığı durum. İsimler ve fiiller
    #: ayrı alt graflarda ilerler; ortak kod ikisini de aynı biçimde yürütür.
    baslangic_durumlari: dict[str, str]
    #: Durum → o durumdan çıkabilecek ekler.
    gecisler: dict[str, tuple[Ek, ...]]
    #: Sözcüğün bitebileceği durumlar.
    bitebilir: frozenset[str]

    def ekler(self, durum: str) -> tuple[Ek, ...]:
        return self.gecisler.get(durum, ())

    def bitebilir_mi(self, durum: str) -> bool:
        return durum in self.bitebilir

    def baslangic(self, tur: str) -> str | None:
        """Bu türün çekimi hangi durumdan başlar? Graf dışı türlerde None."""
        return self.baslangic_durumlari.get(tur)

    def kok_olabilir_mi(self, tur: str) -> bool:
        return tur in self.baslangic_durumlari


@lru_cache(maxsize=1)
def graf() -> Graf:
    """Grafı tembel yükler ve süreç boyunca paylaşır."""
    veri = json.loads(EKLER_YOLU.read_text(encoding="utf-8"))

    gecisler: dict[str, list[Ek]] = {}
    for ham in veri["ekler"]:
        ek = Ek(
            kimlik=ham["kimlik"],
            ad=ham["ad"],
            arketip=ham["arketip"],
            hedef=ham["hedef"],
            oznitelikler=frozenset(ham.get("oznitelikler", ())),
            gerektirir=frozenset(ham.get("gerektirir", ())),
            yasaklar=frozenset(ham.get("yasaklar", ())),
            daraltir=ham.get("daraltir", False),
            dusurur_unsuz=ham.get("dusurur_unsuz", False),
        )
        for kaynak in ham["kaynak"]:
            if kaynak not in veri["durumlar"]:
                raise ValueError(f"{ek.kimlik}: tanımsız kaynak durum {kaynak!r}")
            gecisler.setdefault(kaynak, []).append(ek)
        if ham["hedef"] not in veri["durumlar"]:
            raise ValueError(f"{ek.kimlik}: tanımsız hedef durum {ham['hedef']!r}")

    baslangiclar = veri["baslangic_durumlari"]
    for tur, durum in baslangiclar.items():
        if durum not in veri["durumlar"]:
            raise ValueError(f"{tur}: tanımsız başlangıç durumu {durum!r}")

    return Graf(
        baslangic_durumlari=baslangiclar,
        gecisler={durum: tuple(ekler) for durum, ekler in gecisler.items()},
        bitebilir=frozenset(d for d, o in veri["durumlar"].items() if o.get("bitebilir")),
    )
