"""Motorun çıktı sözleşmesi.

Motorun dışarıya verdiği tek biçim burada tanımlıdır. Üst katmanlar (ÖSYM
politikası, soru üretimi, açıklamalı çözüm şablonu) yalnızca bu tiplere bakar;
motorun iç temsiline hiçbir zaman erişmez.

Sözleşmenin taşıdığı iki karar:

1. **Kanıt zorunludur.** Her olay, hangi konumda hangi sesin ne olduğunu ve
   bunu hangi ekin tetiklediğini taşır. Kanıt türetim sırasında doğar; sonradan
   yüzeye bakılarak yeniden üretilmez.

2. **Belirsizlik atılmaz.** Birden çok geçerli okuma varsa hepsi döner ve
   `belirsiz` işaretlenir. Belirsizlik hata değil, soru malzemesidir.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

KURAL_HARITASI_YOLU = Path(__file__).resolve().parent.parent / "veri" / "kural_haritasi.json"


class Kaynak(StrEnum):
    """Olayın nereden geldiği. **İşlevsel alandır**, bilgi notu değil.

    Yalnızca `TURETIM` otomatik soru olabilir. `SEZGISEL` öğretmen kuyruğuna
    düşer; doğrulanmadan soruya girmez.
    """

    #: Türetim sırasında kuralın fiilen uygulanmasıyla doğdu. Tam güvenilir.
    TURETIM = "turetim"
    #: Sözlükteki açık bir kayıttan geldi (örn. düzensiz biçim).
    SOZLUK = "sozluk"
    #: Kural tam kurulamadı, buluşsal karar verildi. Otomatik soru olamaz.
    SEZGISEL = "sezgisel"


@dataclass(frozen=True, slots=True)
class Kanit:
    """Olayın gerçekleştiğini gösteren somut veri.

    Açıklamalı çözüm metni bu alanlardan şablonla üretilir; model çözüm yazmaz.
    """

    #: Değişimin gerçekleştiği harf konumu (0 tabanlı, üretilmiş yüzeyde).
    konum: int
    #: Değişimden önceki ses. Düşme olaylarında düşen ses.
    once: str
    #: Değişimden sonraki ses. Düşme olaylarında boş dizgi.
    sonra: str
    #: Kuralı tetikleyen ekin yüzey biçimi ("-ı", "-dan"...).
    tetikleyen_ek: str
    #: Kuralın uygulandığı gövde (değişimden önceki hâli).
    govde: str = ""


@dataclass(frozen=True, slots=True)
class Olay:
    """Türetim sırasında tetiklenen tek bir ses olayı."""

    #: Kanonik kural kimliği, `veri/kural_haritasi.json` ile eşleşir.
    kural_id: str
    #: Kuralın okunabilir adı ("Ünsüz Yumuşaması").
    olay: str
    kanit: Kanit
    kaynak: Kaynak = Kaynak.TURETIM
    guven: float = 1.0


@dataclass(frozen=True, slots=True)
class Okuma:
    """Yüzeyle eşleşen tek bir türetim yolu.

    `turetim_izi` her ek uygulandıktan sonraki gövdeyi sırayla tutar. Bir okumanın
    doğruluğu bu izin son elemanının hedef yüzeye eşit olmasıyla tanımlıdır —
    "doğru çözümleme" başka bir ölçüte dayanmaz.
    """

    kok: str
    #: Kökün sözcük türü. Belirsizlik çözümünde ayırt edicidir.
    tur: str
    #: Uygulanan eklerin yüzey biçimleri, sırayla.
    ekler: tuple[str, ...]
    #: Uygulanan eklerin kanonik kimlikleri (`EK.HAL.BEL` gibi).
    ek_kimlikleri: tuple[str, ...]
    turetim_izi: tuple[str, ...]
    olaylar: tuple[Olay, ...] = ()

    @property
    def yuzey(self) -> str:
        return self.turetim_izi[-1] if self.turetim_izi else self.kok


@dataclass(frozen=True, slots=True)
class KelimeSonucu:
    """Tek bir sözcüğün çözümlemesi."""

    kelime: str
    okumalar: tuple[Okuma, ...] = ()

    @property
    def belirsiz(self) -> bool:
        """Birden çok geçerli okuma varsa belirsizdir. Hata değil, veri."""
        return len(self.okumalar) > 1

    @property
    def cozumlenemedi(self) -> bool:
        return not self.okumalar

    @property
    def olaylar(self) -> tuple[Olay, ...]:
        """Tüm okumalardaki olaylar, tekilleştirilmeden.

        Ölçüm ve raporlama için kolaylık. Karar verirken okuma bazında bakılmalı:
        bir olay yalnızca *bazı* okumalarda geçiyor olabilir.
        """
        return tuple(olay for okuma in self.okumalar for olay in okuma.olaylar)

    @property
    def olay_kumeleri(self) -> tuple[frozenset[str], ...]:
        """Her okumanın ürettiği kural kimliği kümesi, okuma sırasıyla."""
        return tuple(frozenset(o.kural_id for o in ok.olaylar) for ok in self.okumalar)

    @property
    def kesin_olaylar(self) -> frozenset[str]:
        """**Her** okumada bulunan kural kimlikleri.

        Motorun bağlam olmadan garanti edebildiği olaylar bunlardır: hangi okuma
        doğru çıkarsa çıksın bu olaylar gerçekleşmiştir. Otomatik soru üretimi
        yalnızca buna dayanabilir.

            kitabı  → {SES.YUM.01}   iki okuma var ama ikisi de yumuşama üretiyor
            masada  → {}             bir okumada olay var, diğerinde yok
        """
        kumeler = self.olay_kumeleri
        return frozenset.intersection(*kumeler) if kumeler else frozenset()

    @property
    def olasi_olaylar(self) -> frozenset[str]:
        """En az bir okumada bulunan kural kimlikleri."""
        kumeler = self.olay_kumeleri
        return frozenset.union(*kumeler) if kumeler else frozenset()

    @property
    def olayda_belirsiz(self) -> bool:
        """Okumalar ürettikleri olaylarda ayrışıyor mu?

        `belirsiz`den ayrı ve daha keskin bir uyarıdır. Sözcüğün birden çok
        okunması tek başına zararsızdır; tehlikeli olan okumaların **farklı ses
        olayları** üretmesidir, çünkü o zaman doğru cevap bağlama bağlıdır.

        Soru üretimi açısından iki ayrı sonuç doğurur:

        1. Bağlamı çözen katman (model) bir okuma seçecekse, seçimi yanlışsa
           cevap anahtarı sessizce yanlış yayılır — docs/decisions.md §7'deki asıl risk.
        2. Ses olayı sorusunda bu sözcük zaten kötü bir maddedir: öğrenci öbür
           okumayı savunabilir, yani "çeldirici de doğru" olur ve soru §5'teki
           çözücü ensemble kapısından geçemez.

        Dolayısıyla bu bayrak yalnızca bilgi değil, bir eleme ölçütüdür.
        """
        return len(set(self.olay_kumeleri)) > 1

    def sozluge(self) -> dict:
        """docs/decisions.md §3'teki JSON sözleşmesine çevirir."""
        return {
            "kelime": self.kelime,
            "okumalar": [
                {
                    "kok": o.kok,
                    "tur": o.tur,
                    "ekler": list(o.ekler),
                    "ek_kimlikleri": list(o.ek_kimlikleri),
                    "turetim_izi": list(o.turetim_izi),
                    "olaylar": [
                        {
                            "olay": olay.olay,
                            "kural_id": olay.kural_id,
                            "kanit": asdict(olay.kanit),
                            "kaynak": str(olay.kaynak),
                            "guven": olay.guven,
                        }
                        for olay in o.olaylar
                    ],
                }
                for o in self.okumalar
            ],
            "belirsiz": self.belirsiz,
            "olayda_belirsiz": self.olayda_belirsiz,
            "kesin_olaylar": sorted(self.kesin_olaylar),
            "olasi_olaylar": sorted(self.olasi_olaylar),
        }


@dataclass(frozen=True, slots=True)
class CumleSonucu:
    """Motorun dış API'sinin döndüğü tip.

    API bilinçli olarak cümle seviyesindedir: bağlam olmadan doğru çözümleme
    seçilemez, bu yüzden tek kelimelik bir imza dışarı verilmez (docs/decisions.md §6).
    """

    cumle: str
    kelimeler: tuple[KelimeSonucu, ...] = ()

    def __iter__(self):
        return iter(self.kelimeler)

    def __len__(self) -> int:
        return len(self.kelimeler)

    def sozluge(self) -> dict:
        return {
            "cumle": self.cumle,
            "kelimeler": [k.sozluge() for k in self.kelimeler],
        }

    def json(self, **kwargs) -> str:
        return json.dumps(self.sozluge(), ensure_ascii=False, **kwargs)


# --- Kural haritası ---------------------------------------------------------


@lru_cache(maxsize=1)
def kural_haritasi() -> dict[str, dict]:
    """`veri/kural_haritasi.json` içindeki kural tanımları. Tembel okunur."""
    veri = json.loads(KURAL_HARITASI_YOLU.read_text(encoding="utf-8"))
    return veri["kurallar"]


def kural_adi(kural_id: str) -> str:
    """Kimliğin okunabilir adı. Tanımsız kimlik sessizce geçmez."""
    kurallar = kural_haritasi()
    if kural_id not in kurallar:
        raise KeyError(f"kural haritasında yok: {kural_id}")
    return kurallar[kural_id]["ad"]


def olay_olustur(
    kural_id: str,
    konum: int,
    once: str,
    sonra: str,
    tetikleyen_ek: str,
    govde: str = "",
    kaynak: Kaynak = Kaynak.TURETIM,
    guven: float = 1.0,
) -> Olay:
    """Kural haritasına bağlı, kanıtı tam bir olay üretir.

    Olaylar bu fonksiyondan geçerek doğar; böylece haritada karşılığı olmayan
    bir `kural_id` motora sızamaz.
    """
    return Olay(
        kural_id=kural_id,
        olay=kural_adi(kural_id),
        kanit=Kanit(
            konum=konum, once=once, sonra=sonra, tetikleyen_ek=tetikleyen_ek, govde=govde
        ),
        kaynak=kaynak,
        guven=guven,
    )
