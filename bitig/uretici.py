"""Üretici: kök + ek dizisi → yüzey.

Çözümleyici bu modülün budanmış aramasıdır; ikisi aynı `turetim.uygula`
şelalesini kullanır. Bu yüzden üretici ayrı bir doğruluk kaynağı değildir —
motorun **tek** doğruluk kaynağıdır, çözümleyici ondan türer.

İki işe yarar:

1. **Gidiş-dönüş taraması.** Üretilen her yüzey geri çözümlenir; aynı okuma
   geri bulunamıyorsa ortada bug vardır. Elle yazılmış altın küme gerektirmeden
   yüz binlerce vaka tarar (bkz. `harness/gidis_donus.py`).
2. **Soru üretimi.** Faz 3'te "istenen ses olayını içeren sözcük üret" işi
   doğrudan buradan çıkar: olay listesine bakıp filtrelemek yeter.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from bitig.morfotaktik import graf
from bitig.sozlesme import Olay
from bitig.sozluk.girdi import SozlukGirdisi
from bitig.turetim import uygula

#: Bir kökten üretilecek en fazla yüzey. Morfotaktik graf çevrimli olduğu için
#: (çatı ekleri kendi durumlarına döner) üst sınır olmadan üretim patlar.
VARSAYILAN_TAVAN = 400


@dataclass(frozen=True, slots=True)
class Uretim:
    """Tek bir türetim yolunun sonucu."""

    kok: str
    tur: str
    yuzey: str
    ek_kimlikleri: tuple[str, ...]
    ekler: tuple[str, ...]
    turetim_izi: tuple[str, ...]
    olaylar: tuple[Olay, ...]

    @property
    def kural_kimlikleri(self) -> frozenset[str]:
        return frozenset(o.kural_id for o in self.olaylar)


def uret(
    girdi: SozlukGirdisi,
    azami_ek: int = 3,
    tavan: int = VARSAYILAN_TAVAN,
) -> Iterator[Uretim]:
    """Bir sözlük girdisinden üretilebilecek yüzeyleri sırayla verir.

    Çıplak kök de bir üretimdir (ek dizisi boş): "kitap", "gel" kendi başlarına
    geçerli sözcüklerdir.

    Genişlik öncelikli gezilir; `tavan` aşılınca kesilir. Kesme sessizdir ve
    bilinçlidir: tarama aracının amacı her yolu görmek değil, geniş ve dengeli
    bir örneklem görmek.
    """
    g = graf()
    baslangic = g.baslangic(girdi.tur)
    if baslangic is None:
        return

    uretilen = 0
    kuyruk: list[tuple[str, str, frozenset, tuple, tuple, tuple, tuple]] = [
        (baslangic, girdi.kok, girdi.oznitelikler, (), (), (girdi.kok,), ())
    ]

    while kuyruk and uretilen < tavan:
        durum, yuzey, govde_oz, kimlikler, ekler, iz, olaylar = kuyruk.pop(0)

        if g.bitebilir_mi(durum):
            uretilen += 1
            yield Uretim(
                kok=girdi.kok,
                tur=girdi.tur,
                yuzey=yuzey,
                ek_kimlikleri=kimlikler,
                ekler=ekler,
                turetim_izi=iz,
                olaylar=olaylar,
            )

        if len(kimlikler) >= azami_ek:
            continue

        for ek in g.ekler(durum):
            # bkz. cozumleyici.py'deki aynı satırın yorumu: gövdenin o anki
            # son morfemine bakılır, çıplak köke değil.
            if not ek.uygulanabilir_mi(govde_oz):
                continue
            yeni_yuzey, ek_yuzeyi, yeni_olaylar = uygula(yuzey, govde_oz, ek)
            kuyruk.append(
                (
                    ek.hedef,
                    yeni_yuzey,
                    ek.oznitelikler,
                    kimlikler + (ek.kimlik,),
                    ekler + (ek_yuzeyi,),
                    iz + (yeni_yuzey,),
                    olaylar + yeni_olaylar,
                )
            )
