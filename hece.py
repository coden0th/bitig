"""Heceleme ve ses uyumu — Faz 2.

Hece bölme ve ünlü uyumu (büyük: kalınlık-incelik, küçük: düzlük-yuvarlaklık)
saf fonolojik işlemlerdir — sözlük ya da ek çözümlemesi gerektirmez, yalnızca
`bitig.fonetik`teki temel harf sınıflandırmalarının üzerine kurulur. Bu yüzden
`anlatim.py`/`noktalama.py` gibi repo kökünde durur, `bitig/` DIŞINDA: `bitig/`
yalnızca ek çözümleme hattını taşır (docs/decisions.md §3), heceleme o hattın bir
parçası değil.

**Ölçüm durumu — dürüstçe işaretli (CLAUDE.md §1 ilke 3, "ölçülmeyen
iyileşmez"):** kurallar MEB'in ders kitabı tanımıyla ve TDK'nin resmî yazım
kılavuzuyla birebir örtüşüyor (kaynaklar aşağıda, fonksiyon docstring'lerinde).
Yine de gerçek bir ÖSYM/MEB soru kümesiyle henüz ölçülmedi — bu tür soru
(heceleme/ses uyumu) TYT'de son derece nadir sorulduğu için elde doğrulanabilir
bir kaynak yok; `harness/` altında bir ölçüm aracı, `altin/` altında bir altın
küme YOK. Doğrulama şu an yalnızca (1) kuralın kaynağıyla birebir örtüşmesi ve
(2) geniş bir birim test kümesiyle (`testler/test_hece.py`) sağlanıyor — bir
sonraki adım gerçek bir kaynak bulunursa ölçmek.

**Kesme işareti desteği, TDK'nin resmî kuralıyla doğrulandı
(tdk.gov.tr/icerik/yazim-kurallari/hece-yapisi-ve-satir-sonunda-kelimelerin-bolunmesi):**
"Kesme işareti satır sonuna geldiğinde yalnız kesme işareti kullanılır, ayrıca
çizgi kullanılmaz" — TDK'nin kendi örnekleri (Edirne'nin → Edirne'-nin,
Ankara'dan → Ankara'-dan) kesme işaretinin GÖVDENİN son hecesine yapışık
kaldığını, ekin ise bütün hâlinde ayrı bir birim olarak taşındığını gösteriyor.
`hece_bol` bunu birebir uyguluyor: gövde normal kuralla hecelenir, kesme
işareti gövdenin son hecesine eklenir, ek (kesme işaretinden sonrası) kendi
içinde AYRICA hecelenip gövdeden sonraki birim(ler) olarak eklenir.

**Bilinen, henüz kapatılmamış sınır:** ünlü uyumu istisnaları (alıntı
kelimeler: kalem, kitap, hediye; uyumsuz ekler: -yor, -ken, -leyin, -gil,
-daş) bir VERİ katmanı gerektirir — bu modül yalnızca saf fonolojik kuralı
uygular, istisna listesi bilmez. `kalem` için `buyuk_unlu_uyumu()` "uymuyor"
der (ilk hece kalın `a`, ikinci ince `e`) — bu motor hatası DEĞİL, kuralın
kendisi doğru çalışıyor; ÖSYM'nin böyle bir soruda "kalem"i doğru cevap
sayması ayrı bir konudur (`yazim.py`'nin TDK Track B'siyle aynı disiplinde
ayrı bir istisna katmanı ister, henüz kurulmadı). Aynı şekilde birleşik
kelimelerde ("hanımeli" gibi) MEB büyük ünlü uyumunu aramaz — bu da bir
"birleşik kelime mi" veri katmanı gerektirir, henüz yok.
"""

from __future__ import annotations

from dataclasses import dataclass

from bitig import fonetik
from bitig.cozumleyici import _KELIME_DESENI

#: Yuvarlak ünlüden sonra izin verilen ünlüler: düz-geniş (a,e) ∪ dar-yuvarlak
#: (u,ü). `fonetik`teki sınıflandırmaların kesişimiyle türetilir — yeni bir
#: harf kümesi elle yazılmaz (CLAUDE.md §8: sabit liste kodda gömülmez).
_YUVARLAKTAN_SONRA_IZINLI = (fonetik.DUZ_UNLULER & fonetik.GENIS_UNLULER) | (
    fonetik.YUVARLAK_UNLULER & fonetik.DAR_UNLULER
)

#: Kesme işaretinin her iki Unicode biçimi (ASCII ve tipografik) — motorun
#: geri kalanıyla aynı liste (`bitig/cozumleyici.py::_KESME_ISARETI_TABLOSU`).
_KESME_ISARETLERI = "'’"


def _hece_bol_cekirdek(kelime: str) -> tuple[str, ...]:
    """Saf fonolojik hece bölme — kesme işareti İÇERMEYEN bir gövde/ek için.

    İki ünlü arasındaki ünsüz kümesinin yalnızca SON ünsüzü sonraki heceye
    bağlanır; öndeki ünsüzler önceki hecede kalır (TDK: "iki ünlü arasındaki
    ünsüz kendinden sonraki ünlüyle hece kurar"; art arda gelen iki ünsüzde
    "ilki önceki, ikincisi sonraki ünlüyle hece kurar" — genel hâli n
    ünsüze genişletilmiş).

        kalem   → ka-lem     (1 ünsüz → sonraki heceye)
        mektup  → mek-tup    (2 ünsüz → sonuncusu sonraki heceye)
        Türkçe  → Türk-çe    (2 ünsüz → sonuncusu sonraki heceye)
        aile    → a-i-le     (0 ünsüz → sınır doğrudan ünlüler arasında)
        kalp    → kalp       (tek ünlü, bölünmez)
    """
    if not kelime:
        return ()
    kucuk = fonetik.kucult(kelime)
    unlu_konumlari = [i for i, harf in enumerate(kucuk) if fonetik.unlu_mu(harf)]
    if not unlu_konumlari:
        return (kelime,)

    sinirlar: list[int] = []
    for onceki, sonraki in zip(unlu_konumlari, unlu_konumlari[1:]):
        unsuz_sayisi = sonraki - onceki - 1
        if unsuz_sayisi <= 1:
            sinir = onceki + 1  # ünsüz yok ya da tek ünsüz: sonraki heceye gider
        else:
            sinir = sonraki - 1  # kümenin son ünsüzü hariç öndekiler önceki hecede kalır
        sinirlar.append(sinir)

    heceler: list[str] = []
    baslangic = 0
    for sinir in sinirlar:
        heceler.append(kelime[baslangic:sinir])
        baslangic = sinir
    heceler.append(kelime[baslangic:])
    return tuple(heceler)


def hece_bol(kelime: str) -> tuple[str, ...]:
    """Kelimeyi hecelerine böler (MEB kuralı + TDK'nin kesme işareti kuralı).

    Kesme işareti taşımayan kelimeler doğrudan `_hece_bol_cekirdek`e gider.
    Kesme işaretli kelimelerde (`Türkiye'nin`, `Ankara'dan`) gövde ve ek AYRI
    AYRI hecelenir, kesme işareti gövdenin son hecesine eklenir — TDK'nin
    kendi örnekleriyle birebir (modül docstring'ine bkz.):

        Türkiye'nin → Tür-ki-ye'-nin
        Ankara'dan  → An-ka-ra'-dan
        1996'da     → 1996'-da   (rakamlar ünlü/ünsüz sınıflamasına girmediği
                                   için gövde tek "hece" gibi ele alınır)

    Kelimenin kendisi büyük/küçük harf farkı gözetmeksizin işlenir ama
    dönen parçalar ORİJİNAL yazımı korur (özel adlar dahil).
    """
    if not kelime:
        return ()
    for isaret in _KESME_ISARETLERI:
        konum = kelime.find(isaret)
        if konum == -1:
            continue
        govde, ek = kelime[:konum], kelime[konum + 1 :]
        govde_heceleri = _hece_bol_cekirdek(govde)
        if not govde_heceleri:
            return (kelime,)  # kesme işareti kelime başında — bozuk girdi, zorlama yok
        ek_heceleri = _hece_bol_cekirdek(ek) if ek else ()
        govde_son = govde_heceleri[-1] + isaret
        return govde_heceleri[:-1] + (govde_son,) + ek_heceleri
    return _hece_bol_cekirdek(kelime)


def cumleyi_hecele(cumle: str) -> list[tuple[str, tuple[str, ...]]]:
    """Cümledeki her kelimeyi (kesme işaretiyle birlikte) ayırıp heceler.

    Kelime ayrımı motorun kendi deseniyle aynı (`bitig.cozumleyici._KELIME_
    DESENI`) — tek kaynak, noktalama otomatik elenir, kesme işaretli kelimeler
    tek parça sayılır (`Türkiye'nin` iki kelime değil bir kelimedir).
    """
    return [(e.group(), hece_bol(e.group())) for e in _KELIME_DESENI.finditer(cumle)]


@dataclass(frozen=True, slots=True)
class UyumSonucu:
    """Bir ünlü uyumu denetiminin sonucu.

    `kanit`, uyumu bozan ilk ardışık ünlü çiftidir (varsa) — açıklamalı
    çözüm için doğrudan kullanılabilir, "neden uymuyor" ayrıca hesaplanmaz.
    """

    uyuyor: bool
    kanit: tuple[str, str] | None


def _unluleri_cikar(kelime: str) -> list[str]:
    kucuk = fonetik.kucult(kelime)
    return [harf for harf in kucuk if fonetik.unlu_mu(harf)]


def buyuk_unlu_uyumu(kelime: str) -> UyumSonucu:
    """Kalınlık-incelik uyumu: her hecenin ünlüsü, kendinden ÖNCEKİ hecenin
    ünlüsüyle aynı sınıftan (ikisi de kalın ya da ikisi de ince) olmalı.

        sokaklar → uyuyor    (o-a-a, hepsi kalın)
        kalem    → uymuyor   (a kalın, e ince) — bilinen alıntı-kelime istisnası
    """
    unluler = _unluleri_cikar(kelime)
    if len(unluler) < 2:
        return UyumSonucu(uyuyor=True, kanit=None)
    for onceki, sonraki in zip(unluler, unluler[1:]):
        if fonetik.ince_mi(onceki) != fonetik.ince_mi(sonraki):
            return UyumSonucu(uyuyor=False, kanit=(onceki, sonraki))
    return UyumSonucu(uyuyor=True, kanit=None)


def kucuk_unlu_uyumu(kelime: str) -> UyumSonucu:
    """Düzlük-yuvarlaklık uyumu: düz ünlüden sonra düz ünlü gelir; yuvarlak
    ünlüden sonra yalnızca düz-geniş (a, e) ya da dar-yuvarlak (u, ü) gelir.

        masa   → uyuyor    (a-a, düz-düz)
        okul   → uyuyor    (o-u, yuvarlak → dar-yuvarlak)
        komik  → uymuyor   (o-i, yuvarlak → düz-dar, izinli değil) — bilinen
                            alıntı-kelime istisnası, klasik TYT örneği
    """
    unluler = _unluleri_cikar(kelime)
    if len(unluler) < 2:
        return UyumSonucu(uyuyor=True, kanit=None)
    for onceki, sonraki in zip(unluler, unluler[1:]):
        if onceki in fonetik.DUZ_UNLULER:
            izinli = fonetik.DUZ_UNLULER
        else:
            izinli = _YUVARLAKTAN_SONRA_IZINLI
        if sonraki not in izinli:
            return UyumSonucu(uyuyor=False, kanit=(onceki, sonraki))
    return UyumSonucu(uyuyor=True, kanit=None)
