"""Çıkmış soruları motorla çözer ve cevap anahtarıyla karşılaştırır.

Bu, kelime düzeyindeki ölçümlerden farklı ve daha sert bir sınavdır: motorun
**bir soruyu bitirebilmesi** gerekir. Tek bir kelimede yanlış pozitif üretmek
burada doğrudan yanlış cevaba dönüşür.

Çözme yöntemi şudur ve bilinçli olarak aptaldır — akıl yürütme yok:

    "hangisinde X vardır?"  → X üreten tek seçeneği bul
    "hangisinde X yoktur?"  → X üretmeyen tek seçeneği bul

Motor doğru çalışıyorsa bu kadarı yeter. Birden fazla aday kalıyorsa motor o
soruyu ayırt edememiş demektir ve bu da bir bulgudur: `BELİRSİZ` olarak raporlanır,
sessizce doğru ya da yanlış sayılmaz.

Sorunun `mod` alanı ÖSYM politikasının uygulanıp uygulanmayacağını söyler.
Varsayılan dilbilim modudur; `"mod": "osym"` olan sorular sözlükleşmiş
türetimleri de sayar (bkz. `bitig/osym.py`).

`tip: "kategori_yok"` ayrı bir soru biçimidir: seçenekler cümle değil ses olayı
**kategori adıdır** ("Ünsüz benzeşmesi" gibi), tek bir `metin` (paragraf/dize)
üstünde hangi kategorinin hiç geçmediği aranır. Kategori adı → kural kimliği
eşlemesi `veri/kural_haritasi.json`'daki `ad` alanından çıkarılır — veri
tekrarlanmaz, tek kaynak orada durur.

Çalıştırma:  .venv/bin/python -m harness.soru_coz
"""

from __future__ import annotations

import sys

from bitig import fonetik
from bitig.cozumleyici import kelimeyi_cozumle
from bitig.osym import Mod, gorus
from bitig.sozlesme import kural_haritasi
from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku

SORU_DOSYASI = "sorular.jsonl"


def _olay_var_mi(kelimeler: list[str], olay: str, mod: Mod, kelime_secenegi: bool) -> bool:
    """Kelime listesinde olay geçiyor mu?

    Tek kelimelik seçeneklerde ("yurt", "süt") sözcüğün kendisi çekimsizdir;
    soru "ek getirildiğinde yumuşar mı" diye sorar. Bu yüzden çekimli biçim
    üretilip ona bakılır. Kelime kelime çalışır — cümle bağlamı gerekmez, bu
    yüzden seçenekler artık sırasız kelime listesi olarak saklanır (bkz.
    `altin/sorular.jsonl`).
    """
    if kelime_secenegi:
        from bitig.sozluk.depo import varsayilan_sozluk
        from bitig.uretici import uret

        for kelime in kelimeler:
            for girdi in varsayilan_sozluk().ara(kelime):
                for uretim in uret(girdi, azami_ek=1):
                    if olay in uretim.kural_kimlikleri:
                        return True
        return False

    return any(olay in gorus(kelimeyi_cozumle(kelime)).gecerli(mod) for kelime in kelimeler)


def _kategori_kural_id(ad: str) -> str:
    """Seçenek metnindeki kategori adını (örn. "Ünsüz benzeşmesi") kural
    kimliğine çevirir. Parantez içi alt başlık ("(Sertleşme)" gibi) ve
    büyük/küçük harf yok sayılır; tek kaynak `kural_haritasi.json`'daki `ad`."""
    hedef = fonetik.kucult(ad.split("(")[0].strip())
    for kural_id, tanim in kural_haritasi().items():
        if fonetik.kucult(tanim["ad"].split("(")[0].strip()) == hedef:
            return kural_id
    raise ValueError(f"kural haritasında eşleşen ad yok: {ad!r}")


def coz(soru: dict) -> tuple[str, set[str]]:
    """Soruyu çözer. (durum, adaylar) döner.

    durum ∈ DOGRU | YANLIS | BELIRSIZ | BOS
    """
    mod = Mod.OSYM if soru.get("mod") == "osym" else Mod.DILBILIM

    if soru["tip"] == "kategori_yok":
        kelimeler = soru["kelimeler"]
        tasiyan = {
            harf
            for harf, ad in soru["kategoriler"].items()
            if _olay_var_mi(kelimeler, _kategori_kural_id(ad), mod, False)
        }
        adaylar = set(soru["kategoriler"]) - tasiyan
    else:
        olay = soru["olay"]
        kelime_secenegi = soru.get("kelime_secenegi", False)
        tasiyan = {
            harf
            for harf, kelimeler in soru["kelimeler"].items()
            if _olay_var_mi(kelimeler, olay, mod, kelime_secenegi)
        }
        tumu = set(soru["kelimeler"])
        adaylar = tasiyan if soru["tip"] == "var" else tumu - tasiyan

    if not adaylar:
        return "BOS", adaylar
    if len(adaylar) > 1:
        return "BELIRSIZ", adaylar
    return ("DOGRU" if adaylar == {soru["cevap"]} else "YANLIS"), adaylar


def main() -> int:
    yol = ALTIN_DIZINI / SORU_DOSYASI
    if not yol.exists():
        print(f"soru dosyası yok: {yol}", file=sys.stderr)
        return 2

    sorular = kumeyi_oku(yol)
    sayac = {"DOGRU": 0, "YANLIS": 0, "BELIRSIZ": 0, "BOS": 0}

    print(f"\n{len(sorular)} soru çözülüyor\n")
    print(f"{'kimlik':<12} {'olay':<12} {'bek':>3} {'bul':<10} durum")
    print("─" * 62)

    for soru in sorular:
        durum, adaylar = coz(soru)
        sayac[durum] += 1
        isaret = {"DOGRU": "✓", "YANLIS": "✗", "BELIRSIZ": "?", "BOS": "∅"}[durum]
        print(
            f"{soru['kimlik']:<12} {soru.get('olay', soru['tip']):<12} {soru['cevap']:>3} "
            f"{','.join(sorted(adaylar)) or '—':<10} {isaret} {durum}"
        )

    toplam = len(sorular)
    print("─" * 62)
    print(
        f"  doğru {sayac['DOGRU']}  ·  yanlış {sayac['YANLIS']}  ·  "
        f"ayırt edemedi {sayac['BELIRSIZ']}  ·  aday bulamadı {sayac['BOS']}"
    )
    if toplam:
        print(f"\n  soru başarımı: {sayac['DOGRU'] / toplam * 100:.1f}%")
    print(
        "\n  'ayırt edemedi' yanlış değildir ama iyi de değildir: motor birden çok\n"
        "  seçenekte olay görmüş. Genellikle kapsam boşluğu ya da fazla üretim işareti."
    )

    return 1 if (sayac["YANLIS"] or sayac["BOS"]) else 0


if __name__ == "__main__":
    sys.exit(main())
