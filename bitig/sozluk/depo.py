"""Sözlük deposu: dosyaların yüklenmesi, çıkarım ve kök indeksi.

Yükleme **tembeldir**. Modülün import edilmesi hiçbir dosya okumaz; ilk sorgu
geldiğinde yüklenir. Motor servis olarak da çalışacağı için bu bir tercih değil
gerekliliktir (bkz. docs/decisions.md §6).

Zemberek dosyaları kaynak veridir ve **değiştirilmez**. BitigAI'nin düzeltmeleri
`veri/tyt_override.json` içinde, aynı satır grameriyle ayrı tutulur; böylece tek
bir ayrıştırıcı ve tek bir doğruluk kaynağı kalır.
"""

from __future__ import annotations

import json
from pathlib import Path

from bitig.sozluk import oznitelik
from bitig.sozluk.ayristirici import AyristirmaHatasi, ayristir
from bitig.sozluk.girdi import SozlukGirdisi

#: Proje kökü — bu dosya `bitig/sozluk/depo.py` olduğu için iki üst dizin.
PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
VERI_DIZINI = PROJE_KOKU / "veri"
ZEMBEREK_DIZINI = VERI_DIZINI / "zemberek"
OVERRIDE_YOLU = VERI_DIZINI / "tyt_override.json"

#: Varsayılan olarak yüklenen sözlükler. `proper-from-corpus.dict` korpustan
#: türetildiği ve gürültülü olduğu için dışarıda bırakılmıştır; gerekirse
#: `Sozluk(dosyalar=...)` ile açıkça verilir.
VARSAYILAN_DOSYALAR = (
    "master-dictionary.dict",
    "non-tdk.dict",
    "proper.dict",
    "abbreviations.dict",
)


class SozlukHatasi(RuntimeError):
    pass


class Sozluk:
    """Kök sorgulanabilir sözlük. Tembel yüklenir, tek örnek paylaşılabilir."""

    def __init__(
        self,
        dosyalar: tuple[str, ...] = VARSAYILAN_DOSYALAR,
        dizin: Path = ZEMBEREK_DIZINI,
        override_yolu: Path | None = OVERRIDE_YOLU,
    ) -> None:
        self._dosyalar = dosyalar
        self._dizin = dizin
        self._override_yolu = override_yolu
        self._indeks: dict[str, tuple[SozlukGirdisi, ...]] | None = None
        #: Ayrıştırılamayan satırlar. Sessizce yutulmaz, sayılır ve sunulur.
        self.bozuk_satirlar: list[tuple[str, int, str]] = []

    # --- Yükleme ---

    def _yukle(self) -> dict[str, tuple[SozlukGirdisi, ...]]:
        birikim: dict[str, list[SozlukGirdisi]] = {}
        for dosya_adi in self._dosyalar:
            yol = self._dizin / dosya_adi
            if not yol.exists():
                raise SozlukHatasi(f"sözlük dosyası yok: {yol}")
            self._dosyadan_oku(yol, birikim)

        if self._override_yolu is not None and self._override_yolu.exists():
            self._override_uygula(self._override_yolu, birikim)

        return {kok: tuple(girdiler) for kok, girdiler in birikim.items()}

    def _dosyadan_oku(self, yol: Path, birikim: dict[str, list[SozlukGirdisi]]) -> None:
        with yol.open(encoding="utf-8") as dosya:
            for satir_no, satir in enumerate(dosya, start=1):
                try:
                    girdi = ayristir(satir)
                except AyristirmaHatasi as hata:
                    self.bozuk_satirlar.append((yol.name, satir_no, str(hata)))
                    continue
                if girdi is not None:
                    self._ekle(birikim, girdi)

    @staticmethod
    def _ekle(birikim: dict[str, list[SozlukGirdisi]], girdi: SozlukGirdisi) -> None:
        # Çıkarım burada uygulanır: depodan çıkan her girdi öznitelikleri tamdır.
        zengin = oznitelik.zenginlestir(girdi)
        birikim.setdefault(zengin.kok, []).append(zengin)

    def _override_uygula(self, yol: Path, birikim: dict[str, list[SozlukGirdisi]]) -> None:
        """TYT düzeltmelerini uygular.

        `kaldir` önce, `ekle` sonra işlenir; böylece bir girdinin değiştirilmesi
        "kaldır + ekle" olarak yazılabilir.
        """
        from dataclasses import replace

        veri = json.loads(yol.read_text(encoding="utf-8"))

        for kok in veri.get("kaldir", []):
            birikim.pop(kok, None)

        for satir in veri.get("ekle", []):
            girdi = ayristir(satir)
            if girdi is None:
                raise SozlukHatasi(f"override satırı boş: {satir!r}")
            self._ekle(birikim, girdi)

        # Mevcut bir girdiye öznitelik eklemek. "kaldır + ekle"den ayrı tutulur:
        # "de" kökünde fiil, isim ve bağlaç girdileri bir arada durur; tümünü
        # silip yeniden yazmak diğerlerini de riske atardı. Burada yalnızca
        # eşleşen (kök, tür) çiftine dokunulur.
        for kayit in veri.get("oznitelik_ekle", []):
            kok, tur = kayit["kok"], kayit["tur"]
            eklenecek = frozenset(kayit["oznitelikler"])
            girdiler = birikim.get(kok)
            if not girdiler:
                raise SozlukHatasi(f"öznitelik eklenecek kök sözlükte yok: {kok!r}")
            eslesen = [i for i, g in enumerate(girdiler) if g.tur == tur]
            if not eslesen:
                raise SozlukHatasi(f"öznitelik eklenecek girdi yok: {kok!r} ({tur})")
            for i in eslesen:
                mevcut = girdiler[i]
                girdiler[i] = replace(mevcut, oznitelikler=mevcut.oznitelikler | eklenecek)

    @property
    def indeks(self) -> dict[str, tuple[SozlukGirdisi, ...]]:
        if self._indeks is None:
            self._indeks = self._yukle()
        return self._indeks

    # --- Sorgu ---

    def ara(self, kok: str) -> tuple[SozlukGirdisi, ...]:
        """Kök biçimine birebir eşleşen tüm girdiler.

        Birden fazla dönebilir ve bu bir sorun değildir: "yemek" hem fiil
        ("ye-") hem isimdir. Belirsizlik burada da atılmaz.
        """
        return self.indeks.get(kok, ())

    def __contains__(self, kok: object) -> bool:
        return isinstance(kok, str) and kok in self.indeks

    def __len__(self) -> int:
        return sum(len(g) for g in self.indeks.values())

    def kokler(self):
        return self.indeks.keys()


_varsayilan: Sozluk | None = None


def varsayilan_sozluk() -> Sozluk:
    """Süreç ömrü boyunca paylaşılan tek sözlük örneği. İlk çağrıda yüklenir."""
    global _varsayilan
    if _varsayilan is None:
        _varsayilan = Sozluk()
    return _varsayilan
