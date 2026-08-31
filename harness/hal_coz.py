"""Durum (hâl) ekleri sorularını motorla çözer.

`soru_coz.py`'nin `kategori_yok` biçimiyle aynı fikir — tek bir pasajda,
seçeneklerin adlandırdığı kategorilerden hangisi hiç geçmiyor — ama farklı
bir kanıt katmanına bakar: ses olayı (`kural_kimlikleri`) değil, sözcüğün
aldığı **hâl eki** (`ek_kimlikleri`). Ayrı bir modül, çünkü ikisi ayrı
sözleşme alanları (docs/decisions.md §3 "belirsizlik iki katmanlıdır" bölümündeki
ayrımın kanıt kaynağı farklıdır).

Kategori adı → ek kimliği eşlemesi `veri/ekler.json`'daki `ad` alanından
çıkarılır (tek kaynak, veri tekrarlanmaz) — `soru_coz.py`'nin ses olayı
adları için `kural_haritasi.json` kullanmasıyla aynı desen. Bir kategori adı
(örn. "Belirtme") kaynaştırma-n'li ve n'siz biçim olmak üzere birden fazla
ek kimliğine karşılık gelebilir (`EK.HAL.BEL` / `EK.HAL.BEL.N`) — ikisi de
aynı hâl, yalnızca sesbilgisel koşullu farklı görünüm.

Çalıştırma:  .venv/bin/python -m harness.hal_coz
"""

from __future__ import annotations

import sys

from bitig import fonetik
from bitig.cozumleyici import cozumle
from bitig.morfotaktik import graf
from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku

SORU_DOSYASI = "hal_sorulari.jsonl"


def _hal_kimlikleri(ad: str) -> frozenset[str]:
    """Seçenek metnindeki kategori adını ("Belirtme" gibi) eşleşen tüm ek
    kimliklerine çevirir (temel + kaynaştırma-n'li biçim)."""
    hedef = fonetik.kucult(ad.split()[0].strip())
    eslesen = {
        ek.kimlik
        for gecisler in graf().gecisler.values()
        for ek in gecisler
        if ek.kimlik.startswith("EK.HAL.") and fonetik.kucult(ek.ad.split()[0]) == hedef
    }
    if not eslesen:
        raise ValueError(f"hâl ekleri arasında eşleşen ad yok: {ad!r}")
    return frozenset(eslesen)


def _hal_var_mi(metin: str, kimlikler: frozenset[str]) -> bool:
    return any(
        kimlik in kimlikler
        for kelime in cozumle(metin)
        for okuma in kelime.okumalar
        for kimlik in okuma.ek_kimlikleri
    )


def coz(soru: dict) -> tuple[str, set[str]]:
    """`tip: kategori_yok` sorularını çözer. `soru_coz.coz` ile aynı mantık."""
    metin = soru["metin"]
    tasiyan = {
        harf
        for harf, ad in soru["secenekler"].items()
        if _hal_var_mi(metin, _hal_kimlikleri(ad))
    }
    adaylar = set(soru["secenekler"]) - tasiyan

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
    print(f"{'kimlik':<20} {'bek':>3} {'bul':<10} durum")
    print("─" * 62)

    for soru in sorular:
        durum, adaylar = coz(soru)
        sayac[durum] += 1
        isaret = {"DOGRU": "✓", "YANLIS": "✗", "BELIRSIZ": "?", "BOS": "∅"}[durum]
        print(
            f"{soru['kimlik']:<20} {soru['cevap']:>3} "
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

    return 1 if (sayac["YANLIS"] or sayac["BOS"]) else 0


if __name__ == "__main__":
    sys.exit(main())
