"""Bağlam duyarlı okuma seçici — Faz 2, madde 1.

Motor bir kelimenin **tüm** geçerli okumalarını üretir ve aralarında seçim
yapmaz (CLAUDE.md §1 İlke 1-2). Ama soru çözme/tutoring akışında öğrenciye
"bu cümlede X neden Y'dir" diye tek bir açıklama vermek gerekir — işte o
seçimi bu modül yapar.

**Motor asla bypass edilmez.** Model yeni bir okuma uydurmaz; yalnızca
motorun zaten ürettiği kapalı kümeden (`KelimeSonucu.okumalar`) birini,
cümledeki somut bir ifadeye bağlayarak işaretler. Bu yüzden `bitig/`
içinde DEĞİL, dışında yaşar — üretim hattı hiçbir model çağrısı yapmaz ve
yapmayacak (CLAUDE.md §1 İlke 5, `harness/model.py`'nin kendi kuralıyla
aynı). Motor çıktısına da dokunulmaz: `bitig/osym.py`'deki `gorus()` ile
aynı desen — ayrı, salt-okunur bir sonuç nesnesi üretilir.

**Kritik sınır:** `BaglamSecimi.kaynak` her zaman `Kaynak.SEZGISEL`dir.
Bu bir türetim kanıtı değil — `kesin_olaylar`a hiçbir zaman giremez, tek
başına otomatik soru üretiminde dayanak olamaz (CLAUDE.md §1 İlke 3, docs/decisions.md §7).
Yalnızca soru ÇÖZME/tutoring akışında kullanılır.

**Jenerik, elle yazılmamış açıklama.** Her okumanın insan-okunur açıklaması
`veri/ekler.json`'daki `ad` alanlarından üretilir — belirsizlik türü başına
elle metin yazmaya gerek yok (2026-08-07'de küçük ölçekte doğrulandı: hâl
eki/iyelik, çatı, isim/sıfat belirsizliklerinin üçünde de aynı jenerik
şablon çalıştı, bkz. docs/decisions.md §6).

Çalıştırma / ölçüm:  .venv/bin/python -m harness.baglam_coz
"""

from __future__ import annotations

from dataclasses import dataclass

from bitig.cozumleyici import kelimeyi_cozumle
from bitig.morfotaktik import graf
from bitig.sozlesme import Kaynak, KelimeSonucu, Okuma
from harness.model import sor

_EK_ADLARI: dict[str, str] = {
    ek.kimlik: ek.ad for gecisler in graf().gecisler.values() for ek in gecisler
}

_SISTEM = (
    "Sen bir Türkçe dilbilgisi hakemisin. Sana bir cümle, içindeki bir sözcük "
    "ve o sözcüğün motor tarafından üretilmiş, numaralanmış olası okumaları "
    "verilecek. Görevin YENİ bir yorum üretmek DEĞİL — yalnızca verilen "
    "okumalardan cümledeki bağlama en uygun olanın numarasını seçmek ve tek "
    "cümlelik bir gerekçe yazmak. Yanıtını tam olarak şu biçimde ver:\n"
    "NUMARA: gerekçe"
)

_SABLON = """Cümle: "{cumle}"
Sözcük: "{kelime}"

Olası okumalar:
{okumalar}

Bu cümlede "{kelime}" hangi okumayla kullanılmış?"""


def okuma_aciklamasi(okuma: Okuma) -> str:
    """Bir okumanın insan-okunur açıklaması. `ekler.json`'daki `ad` alanından
    üretilir — belirsizlik türüne özel elle yazım gerekmez."""
    parcalar = [f"{okuma.kok} ({okuma.tur})"]
    parcalar.extend(_EK_ADLARI.get(kimlik, kimlik) for kimlik in okuma.ek_kimlikleri)
    return " + ".join(parcalar)


@dataclass(frozen=True, slots=True)
class BaglamSecimi:
    """Motorun ürettiği kapalı okuma kümesinden bağlama göre yapılan seçim.

    Motor çıktısına dokunulmaz — bu, `KelimeSonucu`'nun yanında duran ayrı
    bir nesnedir, onu değiştirmez. `kaynak` her zaman `Kaynak.SEZGISEL`.
    """

    kelime: str
    cumle: str
    secilen_indeks: int
    gerekce: str
    kaynak: Kaynak = Kaynak.SEZGISEL

    def secilen_okuma(self, sonuc: KelimeSonucu) -> Okuma:
        return sonuc.okumalar[self.secilen_indeks]


class BaglamHatasi(RuntimeError):
    pass


def sec(cumle: str, kelime: str, sonuc: KelimeSonucu | None = None) -> BaglamSecimi | None:
    """Belirsiz bir kelimenin okumaları arasından bağlama göre seçim yapar.

    `sonuc` verilmezse `kelimeyi_cozumle` ile hesaplanır. Kelimenin tek
    (ya da hiç) okuması varsa seçecek bir şey yoktur, `None` döner — model
    gereksiz yere çağrılmaz.
    """
    if sonuc is None:
        sonuc = kelimeyi_cozumle(kelime)
    if len(sonuc.okumalar) < 2:
        return None

    aciklamalar = [okuma_aciklamasi(ok) for ok in sonuc.okumalar]
    okuma_metni = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(aciklamalar))
    istem = _SABLON.format(cumle=cumle, kelime=kelime, okumalar=okuma_metni)

    yanit = sor(istem, sistem=_SISTEM, sicaklik=0.0, azami_belirtec=4000).strip()
    if ":" not in yanit:
        raise BaglamHatasi(f"beklenmeyen model yanıtı: {yanit!r}")
    numara_metni, gerekce = yanit.split(":", 1)
    numara = "".join(c for c in numara_metni if c.isdigit())
    if not numara:
        raise BaglamHatasi(f"model bir numara vermedi: {yanit!r}")
    indeks = int(numara) - 1
    if not (0 <= indeks < len(sonuc.okumalar)):
        raise BaglamHatasi(f"model geçersiz bir okuma numarası seçti: {numara}")

    return BaglamSecimi(kelime=kelime, cumle=cumle, secilen_indeks=indeks, gerekce=gerekce.strip())
