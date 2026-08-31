"""Noktalama denetimi — Faz 2 madde 4.

Noktalama sorularının çoğu söylem/anlam düzeyinde (bir öbeğin "ara söz" mü
"eş görevli öge" mi olduğunu ayırt etmek gibi) — motorun kapsamı dışında,
modelin işi (`baglam.py` deseniyle ayrı ele alınacak). Ama bir alt tür motorun
ek-kimlik altyapısına doğrudan bağlanıyor:

    SART_SONRASI_VIRGUL   şart ekli (`EK.KIP.SART` — kavrayamasak, ise / ya
                           da `EK.BIRLESIK.SART` — edersek gibi isim/sıfat
                           yüklemi üstünde) bir kelimeden hemen sonra virgül
                           gelmesi anlatım/noktalama hatasıdır.
    KESME_YANLIS_IYELIK   büyük harfle başlayan (özel ad kullanımı) bir
                           kelimede kesme işaretinden sonra 3. tekil kişi
                           DIŞINDA bir iyelik eki varsa kesme yanlıştır (TDK:
                           "Boğaz Köprümüzün", kesmesiz — bkz. aşağı).
    ZARFFIIL_ARDISIK_VIRGUL_EKSIK
                           art arda gelen (aralarında başka bir zarf-fiil
                           daha olan) zarf-fiil ekli kelimeler arasında
                           virgül eksikse hata ("...yer alıp herhangi bir
                           yıkıma maruz kalmadan..." → "alıp,"dan sonra
                           virgül gerekir — gerçek bir ÖSYM sorusuyla
                           doğrulandı, bkz. aşağı).

**`KESME_YANLIS_IYELIK` — TDK'nin resmi kuralıyla doğrulandı** (tdk.gov.tr/
icerik/yazim-kurallari/kesme-isareti): "Özel adlara getirilen iyelik, durum
ve bildirme ekleri kesme işaretiyle ayrılır" ama "sonda 3. teklik kişi
iyelik eki varsa ve başka ek gelirse kesme işareti konmaz" (Boğaz
Köprümüzün, Amik Ovamızın, Kuşadamızdaki). Sözlüğümüzde özel ad için ayrı
bir bayrak YOK (yükleme sırasında küçük harfe normalleştiriliyor, bkz.
docs/decisions.md §9) — bu yüzden asıl sinyal **metindeki büyük harf**tir, sözlük
değil: kelime büyük harfle başlıyorsa özel ad kullanımı sayılır.

**Mekanize edilmeyen, TDK'de doğrulanmış ama uygulanamayan bir istisna:**
"Kurum, kuruluş, kurul, birleşim, oturum ve iş yeri adlarına gelen ekler
kesmeyle ayrılmaz" (Türk Dil Kurumundan). Bir özel adın "kurum adı" olup
olmadığı anlamsal bir bilgi — sözlüğümüz bunu hiç taşımıyor (İsim Soylu
Sözcükler'deki kapalı-sınıf sorunuyla aynı engel). Bu istisna uygulanmadan
bırakıldı; nadiren yanlış pozitife yol açabilir (bir kurum adı 3.tekil-dışı
iyelik alırsa hem "kurum istisnası" hem "iyelik istisnası" aynı anda devreye
girer, ikisi de kesmesiz olmasını gerektirir, çakışma yok — ama kurum adı
3.tekil iyelik alıp kesme TAŞIRSA, kurum istisnası kesmenin hiç olmamasını
isterken bizim kuralımız "3.tekil iyelik, kesme doğru" der; bu nadir ve
bilinçli kabul edilmiş bir sınırdır).

**Mekanize edilmeyen, ayrı bir yön:** kesme EKSİK olduğunda (Haziranında →
Haziran'ında, ay adı özel sayılıyor) tespit henüz yapılmıyor — bu ay adı
listesi gibi ayrı bir veri gerektirir, ölçülmeden eklenmedi.

**İstisna, gerçek bir ÖSYM sorusunda bulundu (ogm-materyal.txt, Noktalama
Q5):** virgülden sonra kısa bir pencerede BAŞKA bir şart-ekli kelime daha
varsa, bu virgül aslında iki EŞ GÖREVLİ şart cümleciğini ayırıyor demektir
— o zaman doğru kullanımdır, bulgu üretilmez. ("Hemen o anda
kavrayamasak, dile dökemesek de..." — ilk virgül burada doğrudur.)

Motorun kendisi değişmedi; yalnızca var olan `EK.KIP.SART`/`EK.BIRLESIK.SART`
kimliklerini + metindeki noktalama konumunu (`isim_coz.py` ile aynı span
tabanlı yöntem) okuyan yeni bir harness-seviyesi katman.
"""

from __future__ import annotations

from dataclasses import dataclass

from bitig.cozumleyici import _KELIME_DESENI, cozumle

_SART_ONEKLERI = ("EK.KIP.SART", "EK.BIRLESIK.SART")
#: İstisna araması için virgülden sonra kaç kelime ileriye bakılır.
_ISTISNA_PENCERESI = 6


@dataclass(frozen=True, slots=True)
class NoktalamaBulgusu:
    tur: str
    kelime: str


def _sart_ekli_mi(kelime) -> bool:
    """Olası mantık: en az bir okumada şart eki varsa yeterli."""
    return any(
        any(kimlik.startswith(onek) for onek in _SART_ONEKLERI)
        for okuma in kelime.okumalar
        for kimlik in okuma.ek_kimlikleri
    )


def _kelime_spanlari(metin: str) -> list[tuple[str, tuple[int, int]]]:
    return [(e.group(), e.span()) for e in _KELIME_DESENI.finditer(metin)]


def sart_sonrasi_virgul_bul(metin: str) -> tuple[NoktalamaBulgusu, ...]:
    """Şart ekli bir kelimeden hemen sonra virgül geliyorsa (ve ardından
    ikinci bir şart-ekli kelime YOKSA) bulgu döner."""
    kelimeler = list(cozumle(metin))
    spanlar = _kelime_spanlari(metin)
    bulgular: list[NoktalamaBulgusu] = []

    for i, kelime in enumerate(kelimeler):
        if not _sart_ekli_mi(kelime):
            continue
        bitis = spanlar[i][1][1]
        if bitis >= len(metin) or metin[bitis] != ",":
            continue

        istisna = any(
            _sart_ekli_mi(kelimeler[j]) for j in range(i + 1, min(i + 1 + _ISTISNA_PENCERESI, len(kelimeler)))
        )
        if istisna:
            continue

        bulgular.append(NoktalamaBulgusu("SART_SONRASI_VIRGUL", kelime.kelime))

    return tuple(bulgular)


def _kesme_konumu(kelime: str) -> int | None:
    for i, harf in enumerate(kelime):
        if harf in "'’":
            return i
    return None


def kesme_yanlis_iyelik_bul(metin: str) -> tuple[NoktalamaBulgusu, ...]:
    """Büyük harfle başlayan, kesme işareti taşıyan bir kelimede kesme
    sonrası ek zinciri 3. tekil DIŞINDA bir iyelik içeriyorsa bulgu döner.

    Kesin mantık: yalnızca kelimenin HER okuması iyelik taşıyorsa ve
    hepsi 3. tekil dışındaysa tetiklenir — bir kısım okumada iyelik hiç
    yoksa (örn. "Hanım'a"nın sahte "han+ım" okuması gibi tek bir okumada
    rastlantısal iyelik çıkması) yanlış pozitif üretilmez.
    """
    bulgular: list[NoktalamaBulgusu] = []
    for kelime in cozumle(metin):
        yuzey = kelime.kelime
        if not yuzey or not yuzey[0].isupper() or _kesme_konumu(yuzey) is None:
            continue
        if not kelime.okumalar:
            continue

        iyelik_durumlari = []
        for okuma in kelime.okumalar:
            iyelikler = [k for k in okuma.ek_kimlikleri if k.startswith("EK.IYELIK")]
            if not iyelikler:
                iyelik_durumlari.append(None)
            else:
                iyelik_durumlari.append(all(k in ("EK.IYELIK.3T", "EK.IYELIK.3C") for k in iyelikler))

        if iyelik_durumlari and all(d is False for d in iyelik_durumlari):
            bulgular.append(NoktalamaBulgusu("KESME_YANLIS_IYELIK", yuzey))

    return tuple(bulgular)


#: İki zarf-fiil arasında aralarında virgül aranacak en fazla kelime sayısı.
_ZARFFIIL_PENCERESI = 6


def _zarffiil_ekli_mi(kelime) -> bool:
    """Olası mantık: en az bir okumada zarf-fiil eki varsa yeterli."""
    return any(
        any(kimlik.startswith("EK.ZARFFIIL") for kimlik in okuma.ek_kimlikleri) for okuma in kelime.okumalar
    )


def zarffiil_ardisik_virgul_eksik_bul(metin: str) -> tuple[NoktalamaBulgusu, ...]:
    """Zarf-fiil ekli bir kelimeden kısa bir pencere içinde İKİNCİ bir
    zarf-fiil ekli kelime geliyorsa (art arda gelen zarf-fiil zinciri),
    aralarına virgül gerekir — yoksa bulgu döner."""
    kelimeler = list(cozumle(metin))
    spanlar = _kelime_spanlari(metin)
    bulgular: list[NoktalamaBulgusu] = []

    for i, kelime in enumerate(kelimeler):
        if not _zarffiil_ekli_mi(kelime):
            continue
        ikinci_var_mi = any(
            _zarffiil_ekli_mi(kelimeler[j]) for j in range(i + 1, min(i + 1 + _ZARFFIIL_PENCERESI, len(kelimeler)))
        )
        if not ikinci_var_mi:
            continue

        bitis = spanlar[i][1][1]
        virgul_var = bitis < len(metin) and metin[bitis] == ","
        if not virgul_var:
            bulgular.append(NoktalamaBulgusu("ZARFFIIL_ARDISIK_VIRGUL_EKSIK", kelime.kelime))

    return tuple(bulgular)


#: Tüm noktalama taramaları, tek bir yerden çalıştırılabilir sırayla.
TARAMALAR = (sart_sonrasi_virgul_bul, kesme_yanlis_iyelik_bul, zarffiil_ardisik_virgul_eksik_bul)


def tara(metin: str) -> tuple[NoktalamaBulgusu, ...]:
    return tuple(bulgu for tarama in TARAMALAR for bulgu in tarama(metin))
