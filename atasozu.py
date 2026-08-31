"""Atasözü/deyim sözlüğü — Faz 2 madde 5, veri erişim katmanı.

`veri/atasozu_deyim.json`ı okur — **ağ gerektirmez**, çalışma zamanında
yalnızca yerel dondurulmuş kopyaya bakılır (`harness/atasozu_indir.py`
periyodik olarak, elle tazeler — `veri/zemberek/` ve TDK önbelleğiyle aynı
desen, bkz. `[[yazim-motoru-plani]]`).

Bu modül şimdilik yalnızca **sorgu** katmanıdır (tam eşleşme, kökü değil
yüzeyi arar — deyimler çekimlenmiş biçimde metne geçer, "kafayı yedi" gibi,
bu yüzden düz metin taramasında tespit için motorun morfolojik normalleştirme
desteği ayrıca gerekir; o, henüz yapılmadı). Şu an sunduğu:

    bul(soz)          tam eşleşen kayıt(lar) — birden fazla anlam olabilir
    ara(alt_dize)      sözün İÇİNDE geçen tüm kayıtlar (kaba arama)

Faz 2'nin planladığı asıl kullanım: anlatım bozukluğunun "deyim yanlışlığı"
alt türü (`anlatim.py`'de "denenip eklenmeyenler" listesinde duruyordu —
deyim sözlüğü olmadığı için mekanize edilemiyordu, bkz. docs/decisions.md §6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from bitig import fonetik

VERI_YOLU = Path(__file__).resolve().parent / "veri" / "atasozu_deyim.json"


@dataclass(frozen=True, slots=True)
class AtasozuKaydi:
    soz: str
    anlam: str
    tur: str  # "atasozu" | "deyim"


@lru_cache(maxsize=1)
def _kayitlar() -> tuple[AtasozuKaydi, ...]:
    if not VERI_YOLU.exists():
        return ()
    veri = json.loads(VERI_YOLU.read_text(encoding="utf-8"))
    return tuple(AtasozuKaydi(**k) for k in veri["kayitlar"])


@lru_cache(maxsize=1)
def _indeks() -> dict[str, tuple[AtasozuKaydi, ...]]:
    indeks: dict[str, list[AtasozuKaydi]] = {}
    for kayit in _kayitlar():
        indeks.setdefault(fonetik.kucult(kayit.soz), []).append(kayit)
    return {k: tuple(v) for k, v in indeks.items()}


def bul(soz: str) -> tuple[AtasozuKaydi, ...]:
    """Tam eşleşen kayıt(lar)ı döner (birden fazla anlam/tür olabilir)."""
    return _indeks().get(fonetik.kucult(soz), ())


def ara(alt_dize: str) -> tuple[AtasozuKaydi, ...]:
    """`alt_dize`yi İÇİNDE barındıran tüm kayıtlar — kaba, sıralı bir tarama."""
    hedef = fonetik.kucult(alt_dize)
    return tuple(k for k in _kayitlar() if hedef in fonetik.kucult(k.soz))
