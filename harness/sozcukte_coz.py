"""Sözcükte Yapı (kök, yapım eki) sorularını motorla çözer.

`fiil_coz.py`nin genellemesi ama **varsayılan mantık kesin**, olası değil: bu domainde
neredeyse her isim/sıfat kökü -lA/-CA/-GI gibi üretken bir yapım ekiyle sahte bir fiil
okuması da kazanıyor ("sokak" → "sokakla-r" gibi, motor gramer olarak üretilebilir her
zinciri döner). "Olası" mantık (fiil_coz.py'nin `_kategoriler` varsayılanı) bu yüzden
"hem yapım hem çekim eki almış" tipi sorularda yanlış seçeneği de aday yapar. Burada
VAR, bir kelimenin *her* okumasının aranan öneki taşımasını ister (aynı fiil_coz.py'nin
`_ekfiil_var_mi` mantığı, genellenmiş). YOK ise tam tersi: *hiçbir* okumasında öneğin
hiç geçmemesini ister — tek kelimelik seçeneklerde bu otomatik olarak "olası"yla aynı
sonucu verir (birleşim boşsa her okuma da boştur), birden çok kelimelik seçeneklerde
(atasözü/cümle) ayrışır.

**Bu dosyaya soru eklemeden önce her seferinde elle ölçülmeli, VE paragraf↔soru
eşleşmesi iki kez kontrol edilmeli.** 2026-08-07 oturumunda paragraf/soru numarası
sırası (kaynak PDF'te paragraf her zaman kendi soru numarasından hemen önce gelir) iki
kez yanlış okundu — biri kullanıcı tarafından düzeltildi (1988/soru 4), biri kendi
kendine düzeltilirken YENİ bir kaymaya yol açtı (2018/soru 26 önce doğru test edilip
sonra yanlışlıkla "yanlış paragrafla" tekrarlanıp BAŞARISIZ sanıldı — üçüncü turda
doğru paragrafla tekrar denenince aslında ÇALIŞTIĞI görüldü). Ders: bu kaynakta
transkripsiyon hatası riski yüksek, her yeni soru eklenmeden önce paragraf metni
kaynak PDF'ten taze okunmalı, önceki bir oturumun transkripsiyonuna güvenilmemeli.

Desteklenen `tip` / `ozellik` kombinasyonları:

    var / SIFATFIIL   EK.SIFATFIIL.* kesin var — "yapım ekiyle türetilmiş sıfat"
                       sorularında (fiilimsi ekleri MEB'in kendi kaynağına göre de
                       fiilden isim yapım ekidir, bkz. sozcukte-yapi.pdf s.19)
    var / IYELIK      EK.IYELIK.* kesin var — "bir varlığın neye ait olduğunu
                       belirten ek" sorularında
    yok / YAPIM       EK.YAPIM.* kesin yok — "yapım eki almamıştır" / "yapısı
                       bakımından farklıdır (yapım eki içermez)" / "yalnızca çekim
                       eki almıştır" sorularında. Sözlükleşme riski yüksek — bazı
                       paragraflarda temiz çalışıyor (1999/7, 2010/12, 2018/26),
                       bazılarında hiç ayırt etmiyor (2018/26'nın YANLIŞ paragrafla
                       ilk denemesi gibi) — her paragraf ayrı ölçülmeli.
    coklu_iyelik23    Numaralanmış tek kelimelerden hangileri HEM 2. HEM 3. tekil
                       kişi iyelik eki gösterebiliyor (olası, kelimenin kendi içinde
                       çift okunaklı olması aranıyor — iki farklı kelimenin biri
                       2. biri 3. göstermesi değil). `ogeler`/`secenekler` ayrımı
                       fiil_coz.py'nin `coklu_var` deseniyle aynı.
    kategori_yok      Ortak bir `metin` (dize/paragraf) üzerinde, seçenek başına bir
                       kategori adı (`kategoriler`) veriliyor; hangi kategori metinde
                       hiç geçmiyor. `soru_coz.py`'nin SES.* için yaptığı
                       "kategori_yok"un morfolojik genellemesi — kapalı sınıf
                       kategoriler (edat gibi) için sabit kelime listesiyle,
                       diğerleri için ek_kimlikleri önekiyle çözülür.

Desteklenmeyen, denenip BAŞARISIZ olan (sözlükleşme veya gerçek dilbilgisel
belirsizlik yüzünden — kod eklenmedi):

    "Birden çok yapım eki" (2 kere ölçüldü, 1997/3 ve 1999/6 — motorun sözlüğü ilk
    yapım basamağını hep yutuyor: "korku+lu" değil "korku"+lu, "örtü+lü" değil
    "örtü"+lü görünüyor, max her zaman 1)
    "3. çoğul kişi iyelik eki" tek başına (2019/27 — `-lArI` yüzeyi HER taşıyan
    kelimede aynı 3 yönlü belirsizliği taşıyor, ayırt edici değil)
    "Belirtme durumu eki" tek başına, iyelik-3 ile çakışan bağlamlarda (2019/28,
    2020/29 — klasik "kitabı" belirsizliği, motor kesin diyemiyor)

Çalıştırma:  .venv/bin/python -m harness.sozcukte_coz
"""

from __future__ import annotations

import re
import sys

from bitig import fonetik
from bitig.cozumleyici import kelimeyi_cozumle
from harness.altin_dogrula import ALTIN_DIZINI, kumeyi_oku

SORU_DOSYASI = "sozcukte_yapi_sorulari.jsonl"

_ROMA_DUZENI = re.compile(r"\b(IV|III|II|I|V)\b")

_OZELLIK_ONEKLERI: dict[str, tuple[str, ...]] = {
    "SIFATFIIL": ("EK.SIFATFIIL",),
    "IYELIK": ("EK.IYELIK",),
    "YAPIM": ("EK.YAPIM",),
}

#: `kategori_yok` sorularında ek_kimlikleri önekiyle çözülen kategoriler.
_KATEGORI_ONEKLERI: dict[str, tuple[str, ...]] = {
    "İlgi eki": ("EK.HAL.ILG",),
    "Ek eylem": ("EK.BILDIRME", "EK.BIRLESIK"),
    "İyelik eki": ("EK.IYELIK",),
    "Kişi eki": ("EK.KISI",),
}

#: aynı sorularda kapalı sınıf, sabit kelime listesiyle çözülen kategoriler.
#: Genel bir edat/bağlaç sözlüğü DEĞİL — yalnızca ölçülüp doğrulanan tek kayıt.
_KATEGORI_KELIMELERI: dict[str, tuple[str, ...]] = {
    "Benzetme edatı": ("gibi", "kadar"),
}


def _okuma_onek_tasiyor(ek_kimlikleri: tuple[str, ...], onekler: tuple[str, ...]) -> bool:
    return any(kimlik.startswith(onek) for kimlik in ek_kimlikleri for onek in onekler)


def _kesin_var_mi(kelimeler: list[str], onekler: tuple[str, ...]) -> bool:
    """Kelime listesinde, *her* okuması aranan öneki taşıyan bir kelime var mı.

    Kelime kelime çalışır (`kelimeyi_cozumle`), cümle bağlamı gerekmez — bu
    yüzden seçenekler cümle olarak değil, sırasız kelime listesi olarak
    saklanabilir (bkz. `altin/sozcukte_yapi_sorulari.jsonl`, alfabetik
    sıralanmış — kaynak metnin yeniden kurulmasını engellemek için)."""
    for kelime in kelimeler:
        s = kelimeyi_cozumle(kelime)
        if s.okumalar and all(
            _okuma_onek_tasiyor(ok.ek_kimlikleri, onekler) for ok in s.okumalar
        ):
            return True
    return False


def _kesin_yok_mu(kelimeler: list[str], onekler: tuple[str, ...]) -> bool:
    """Kelime listesinde, *hiçbir* okumada aranan önek geçmiyor mu."""
    for kelime in kelimeler:
        s = kelimeyi_cozumle(kelime)
        for ok in s.okumalar:
            if _okuma_onek_tasiyor(ok.ek_kimlikleri, onekler):
                return False
    return True


def coz_var_yok(soru: dict) -> tuple[str, set[str]]:
    onekler = _OZELLIK_ONEKLERI[soru["ozellik"]]
    testet = _kesin_var_mi if soru["tip"] == "var" else _kesin_yok_mu
    adaylar = {
        harf for harf, kelimeler in soru["kelimeler"].items() if testet(kelimeler, onekler)
    }
    if not adaylar:
        return "BOS", adaylar
    if len(adaylar) > 1:
        return "BELIRSIZ", adaylar
    return ("DOGRU" if adaylar == {soru["cevap"]} else "YANLIS"), adaylar


def _iyelik_2ve3_belirsiz_mi(kelime: str) -> bool:
    """Kelimenin kendisi hem 2. hem 3. tekil kişi iyelik okuması taşıyor mu."""
    s = kelimeyi_cozumle(kelime)
    if s.cozumlenemedi:
        return False
    var2 = any(
        any(kk.startswith("EK.IYELIK.2") for kk in ok.ek_kimlikleri) for ok in s.okumalar
    )
    var3 = any(
        any(kk.startswith("EK.IYELIK.3") for kk in ok.ek_kimlikleri) for ok in s.okumalar
    )
    return var2 and var3


def _roma_kumesi(metin: str) -> frozenset[str]:
    return frozenset(_ROMA_DUZENI.findall(metin))


def coz_coklu_iyelik(soru: dict) -> tuple[str, set[str]]:
    hedef_kume = {
        numara
        for numara, kelime in soru["ogeler"].items()
        if _iyelik_2ve3_belirsiz_mi(kelime)
    }
    eslesen = {
        harf
        for harf, secenek_metni in soru["secenekler"].items()
        if _roma_kumesi(secenek_metni) == hedef_kume
    }
    if not eslesen:
        return "BOS", eslesen
    if len(eslesen) > 1:
        return "BELIRSIZ", eslesen
    return ("DOGRU" if eslesen == {soru["cevap"]} else "YANLIS"), eslesen


def _kategori_metinde_var_mi(kelimeler: list[str], kategori: str) -> bool | None:
    """None: kategori tanınmıyor (soru bu yüzden çözülemez)."""
    if kategori in _KATEGORI_ONEKLERI:
        onekler = _KATEGORI_ONEKLERI[kategori]
        for kelime in kelimeler:
            s = kelimeyi_cozumle(kelime)
            for ok in s.okumalar:
                if _okuma_onek_tasiyor(ok.ek_kimlikleri, onekler):
                    return True
        return False
    if kategori in _KATEGORI_KELIMELERI:
        hedefler = _KATEGORI_KELIMELERI[kategori]
        return any(fonetik.kucult(kelime) in hedefler for kelime in kelimeler)
    return None


def coz_kategori_yok(soru: dict) -> tuple[str, set[str]]:
    kelimeler = soru["kelimeler"]
    adaylar: set[str] = set()
    for harf, kategori in soru["kategoriler"].items():
        var = _kategori_metinde_var_mi(kelimeler, kategori)
        if var is None:
            return "BOS", set()
        if not var:
            adaylar.add(harf)
    if not adaylar:
        return "BOS", adaylar
    if len(adaylar) > 1:
        return "BELIRSIZ", adaylar
    return ("DOGRU" if adaylar == {soru["cevap"]} else "YANLIS"), adaylar


def coz(soru: dict) -> tuple[str, set[str]]:
    if soru["tip"] == "coklu_iyelik23":
        return coz_coklu_iyelik(soru)
    if soru["tip"] == "kategori_yok":
        return coz_kategori_yok(soru)
    return coz_var_yok(soru)


def main() -> int:
    yol = ALTIN_DIZINI / SORU_DOSYASI
    if not yol.exists():
        print(f"soru dosyası yok: {yol}", file=sys.stderr)
        return 2

    sorular = kumeyi_oku(yol)
    sayac = {"DOGRU": 0, "YANLIS": 0, "BELIRSIZ": 0, "BOS": 0}

    print(f"\n{len(sorular)} soru çözülüyor\n")
    print(f"{'kimlik':<14} {'bek':>3} {'bul':<10} durum")
    print("─" * 50)

    for soru in sorular:
        durum, adaylar = coz(soru)
        sayac[durum] += 1
        isaret = {"DOGRU": "✓", "YANLIS": "✗", "BELIRSIZ": "?", "BOS": "∅"}[durum]
        print(
            f"{soru['kimlik']:<14} {soru['cevap']:>3} "
            f"{','.join(sorted(adaylar)) or '—':<10} {isaret} {durum}"
        )

    toplam = len(sorular)
    print("─" * 50)
    print(
        f"  doğru {sayac['DOGRU']}  ·  yanlış {sayac['YANLIS']}  ·  "
        f"ayırt edemedi {sayac['BELIRSIZ']}  ·  aday bulamadı {sayac['BOS']}"
    )
    if toplam:
        print(f"\n  soru başarımı: {sayac['DOGRU'] / toplam * 100:.1f}%")

    return 1 if (sayac["YANLIS"] or sayac["BOS"]) else 0


if __name__ == "__main__":
    sys.exit(main())
