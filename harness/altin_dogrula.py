"""Altın kümenin kendi tutarlılığını denetler.

Altın küme elle yazılır, dolayısıyla hata içerebilir — ve altın kümedeki bir hata
motordaki hatadan daha tehlikelidir: ölçüyü bozar, yanlış yöne koşturur.

Bu betik motoru hiç çalıştırmaz. Yalnızca kümenin *kendisiyle* ve sözlükle
tutarlı olup olmadığına bakar:

  - kural_id'ler kural haritasında tanımlı mı
  - kök sözlükte var mı
  - beklenen olayı tetikleyecek öznitelik kökte gerçekten var mı
  - kelime köküyle başlıyor mu (ünlü düşmesi/ikizleşme payıyla)

Çalıştırma:  .venv/bin/python -m harness.altin_dogrula
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

from bitig import fonetik
from bitig.sozlesme import kural_haritasi
from bitig.sozluk.depo import varsayilan_sozluk
from bitig.sozluk.girdi import Oznitelik

ALTIN_DIZINI = Path(__file__).resolve().parent.parent / "altin"

#: Bir kuralın tetiklenebilmesi için kökte bulunması gereken öznitelik.
#: "yapisal" olanlar özniteliğe değil gövdenin ses yapısına bağlıdır.
KURAL_ONKOSULU = {
    "SES.YUM.01": Oznitelik.YUMUSAMA,
    "SES.UD.01": Oznitelik.SON_UNLU_DUSER,
    "SES.UT.01": Oznitelik.IKIZLESME,
    "SES.DAR.01": Oznitelik.ARA_UNLU_DUSER,
    "SES.UND.01": Oznitelik.SON_UNSUZ_DUSER,
}


@lru_cache(maxsize=1)
def _EK_OZNITELIKLERI() -> frozenset[str]:
    """Grafta tanımlı eklerin taşıdığı tüm öznitelikler."""
    from bitig.morfotaktik import graf

    return frozenset(
        oz for ekler in graf().gecisler.values() for ek in ekler for oz in ek.oznitelikler
    )


def kumeyi_oku(yol: Path) -> list[dict]:
    kayitlar = []
    for satir_no, satir in enumerate(yol.read_text(encoding="utf-8").splitlines(), 1):
        satir = satir.strip()
        if not satir or satir.startswith("#"):
            continue
        try:
            kayit = json.loads(satir)
        except json.JSONDecodeError as hata:
            raise ValueError(f"{yol.name}:{satir_no} bozuk JSON: {hata}") from hata
        kayit["_satir"] = satir_no
        kayitlar.append(kayit)
    return kayitlar


def denetle(kayitlar: list[dict]) -> list[str]:
    sozluk = varsayilan_sozluk()
    kurallar = kural_haritasi()
    sorunlar: list[str] = []

    def sorun(kayit: dict, mesaj: str) -> None:
        sorunlar.append(f"satır {kayit['_satir']:>3} · {kayit['kelime']:<14} {mesaj}")

    gorulen: dict[str, int] = {}

    for kayit in kayitlar:
        kelime = kayit["kelime"]
        kok = kayit["kok"]
        beklenen = kayit["beklenen"]

        if kelime in gorulen:
            sorun(kayit, f"yinelenen kelime (ilk geçiş: satır {gorulen[kelime]})")
        gorulen[kelime] = kayit["_satir"]

        # 1. Kural kimlikleri haritada tanımlı mı?
        for kural_id in beklenen:
            if kural_id not in kurallar:
                sorun(kayit, f"kural haritasında yok: {kural_id}")

        # 2. Kök sözlükte var mı?
        girdiler = sozluk.ara(kok)
        if not girdiler:
            sorun(kayit, f"kök sözlükte yok: {kok!r}")
            continue

        # 3. Beklenen olayın öznitelik önkoşulu sağlanabiliyor mu?
        #
        #    Öznitelik kökte olabileceği gibi EKTE de olabilir: "gördüğüm"deki
        #    yumuşama `gör` köküne değil `-DIk` ekine aittir, "gelmiyor"daki
        #    daralma `-mA` ekine. Bu yüzden kökün öznitelikleri, grafta tanımlı
        #    tüm eklerin öznitelikleriyle birleştirilerek bakılır.
        #
        #    Bu denetim kaba kalır — hangi ekin fiilen uygulandığını bilemez,
        #    onu ancak motoru çalıştıran `harness.olc` söyler. Buradaki iş
        #    yalnızca "bu olay bu kökle imkânsız" hatalarını yakalamak.
        herhangi = set().union(*(g.oznitelikler for g in girdiler)) | _EK_OZNITELIKLERI()
        for kural_id in beklenen:
            gereken = KURAL_ONKOSULU.get(kural_id)
            if gereken and gereken not in herhangi:
                sorun(
                    kayit,
                    f"{kural_id} bekleniyor ama {kok!r} kökünde {gereken} yok "
                    f"(mevcut: {sorted(herhangi - {'Ext'}) or '-'})",
                )

        # 4. Olay beklenmiyorsa, olaysız bir okuma mümkün olmalı.
        #    Ölçüt girdilerin *kesişimi*dir, birleşimi değil: "sepet" hem
        #    NoVoicing isim hem Voicing sıfat olarak kayıtlıdır; sıfat yolu
        #    "sepedi" üretip yüzeyle eşleşmediği için budanır, dolayısıyla
        #    "sepeti" için olay beklememek doğrudur. Birleşime bakmak bu
        #    kaydı yanlışlıkla hatalı gösterirdi.
        hepsinde = set.intersection(*(set(g.oznitelikler) for g in girdiler))
        if not beklenen and kelime != kok:
            ek = kelime[len(kok) :] if kelime.startswith(kok) else ""
            if ek and fonetik.unluyle_basliyor(ek):
                for oz in (Oznitelik.YUMUSAMA, Oznitelik.SON_UNLU_DUSER, Oznitelik.IKIZLESME):
                    if oz in hepsinde:
                        sorun(
                            kayit,
                            f"olay beklenmiyor ama {kok!r} kökünün TÜM girdilerinde "
                            f"{oz} var ve ek {ek!r} ünlüyle başlıyor — olaysız okuma yok",
                        )

        # 5. Yüzey, kökle makul biçimde ilişkili mi?
        #    Kökün türetimde alabileceği tüm gövde biçimleri denenir: kendisi,
        #    yumuşamışı, son ünlüsü düşmüşü, ikizleşmişi.
        adaylar = {kok, fonetik.yumusat(kok), fonetik.son_unluyu_dusur(kok)}
        if kok:
            adaylar.add(kok + kok[-1])  # ikizleşme: hak → hakk
            yumusak_ikiz = fonetik.yumusat(kok)
            if yumusak_ikiz:
                adaylar.add(yumusak_ikiz + yumusak_ikiz[-1])  # tıp → tıb → tıbb
            if fonetik.unluyle_bitiyor(kok):
                adaylar.add(kok[:-1])  # ünlü daralması: başla → başl, de → d
                dar = fonetik.daralt_unlu(kok[-1])
                if dar:
                    adaylar.add(kok[:-1] + dar)  # kök daralması: ye → yi
            if any(Oznitelik.SON_UNSUZ_DUSER in g.oznitelikler for g in girdiler):
                adaylar.add(kok[:-1])  # ünsüz düşmesi: ufak → ufa(cık)
        if not any(kelime.startswith(a) for a in adaylar if a):
            sorun(kayit, f"kelime kökle ({kok!r}) ilişkili görünmüyor")

    return sorunlar


def main() -> int:
    toplam_sorun = 0
    for yol in sorted(ALTIN_DIZINI.glob("*.jsonl")):
        if yol.name in ("sorular.jsonl", "fiil_sorulari.jsonl", "isim_sorulari.jsonl", "baglam_sorulari.jsonl", "anlatim_sorulari.jsonl", "noktalama_sorulari.jsonl", "sozcukte_yapi_sorulari.jsonl"):
            continue  # farklı şema (soru düzeyi); harness.soru_coz / harness.fiil_coz alanı
        kayitlar = kumeyi_oku(yol)
        sorunlar = denetle(kayitlar)
        pozitif = sum(1 for k in kayitlar if k["beklenen"])
        negatif = len(kayitlar) - pozitif

        print(f"\n{yol.name}: {len(kayitlar)} kayıt ({pozitif} pozitif, {negatif} negatif)")
        dagilim: dict[str, int] = {}
        for kayit in kayitlar:
            for kural_id in kayit["beklenen"]:
                dagilim[kural_id] = dagilim.get(kural_id, 0) + 1
        for kural_id, sayi in sorted(dagilim.items()):
            print(f"   {kural_id}: {sayi}")

        if sorunlar:
            print(f"\n   {len(sorunlar)} SORUN:")
            for s in sorunlar:
                print(f"   ✗ {s}")
            toplam_sorun += len(sorunlar)
        else:
            print("   ✓ tutarlı")

    return 1 if toplam_sorun else 0


if __name__ == "__main__":
    sys.exit(main())
