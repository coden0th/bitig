"""Çözümleyici: ters türetim.

Burada ayrı bir "çözümleme algoritması" yoktur. Çözümleme, **üreticinin budanmış
aramasıdır**: kök adaylarından başlayıp morfotaktik grafta ilerlenir, her adımda
türetim şelalesi çalıştırılır ve üretilen yüzey hedefin öneki değilse dal ölür.
Sona kalan tam eşleşmeler geçerli okumalardır.

Bunun sonucu, motorun "tespit" ile "türetim" arasında tutarsızlığa düşmesinin
yapısal olarak imkânsız olmasıdır: tek doğruluk kaynağı üreticidir.

Belirsizlik atılmaz. Birden çok yol yüzeye ulaşıyorsa hepsi döner.
"""

from __future__ import annotations

import re

from bitig import fonetik
from bitig.morfotaktik import graf
from bitig.sozlesme import CumleSonucu, KelimeSonucu, Okuma, Olay
from bitig.sozluk.depo import Sozluk, varsayilan_sozluk
from bitig.sozluk.girdi import Oznitelik, SozlukGirdisi
from bitig.turetim import Ek, uygula

#: Sözcük ayırıcı. Kesme işareti sözcüğün parçası sayılır (Ali'nin).
_KELIME_DESENI = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)

#: Bir dalda izin verilen en fazla ek sayısı. Ad çekimi grafı zaten sonludur;
#: bu yalnızca veri hatası durumunda sonsuz döngüye karşı emniyet kemeridir.
AZAMI_EK = 6


def _kok_adaylari(yuzey: str, sozluk: Sozluk):
    """Yüzeyin başlangıcıyla uyuşabilecek sözlük girdilerini üretir.

    Kökün türetimde alabileceği biçimler (yumuşamış, ünlüsü düşmüş, ikizleşmiş)
    yüzeyde görünen biçimlerdir; bu yüzden aday taraması **kök biçimi** üzerinden
    değil, kökün üretebileceği gövde biçimleri üzerinden yapılır.

    Tarama uzun önekten kısaya gider; erken ve dar aday kümesi aramayı küçük tutar.
    """
    g = graf()
    for uzunluk in range(len(yuzey), 0, -1):
        onek = yuzey[:uzunluk]
        for girdi in sozluk.ara(onek):
            if g.kok_olabilir_mi(girdi.tur):
                yield girdi

        # Gövdesi değişmiş kökler: yüzeydeki önek kökün kendisi değil,
        # kökün türetilmiş biçimi olabilir. Ters yönde arayamayacağımız için
        # köke geri dönmeyi denemek yerine, sözlükteki kökün üreteceği biçimi
        # ileride türetim doğrulayacak. Burada yalnızca aday kısaltması yapılır.
        for aday_kok in _degismis_govdeden_kok_adaylari(onek):
            for girdi in sozluk.ara(aday_kok):
                if g.kok_olabilir_mi(girdi.tur) and _govde_uretebilir(girdi, onek):
                    yield girdi


#: Yumuşamanın tersi — `fonetik.YUMUSAMA` haritasının tam tersi olmalı.
#: "k" iki kaynaktan gelebilir: genel kural k→ğ ve "nk" istisnası k→g.
#: "g"→"ğ" satırı "katalog/zoolog" tipi sözcükler içindir; eksikliği bu
#: köklerin tüm çekimli biçimlerini çözümlenemez yapıyordu.
_YUMUSAMANIN_TERSI = (("p", "b"), ("ç", "c"), ("t", "d"), ("k", "ğ"), ("k", "g"), ("g", "ğ"))


def _degismis_govdeden_kok_adaylari(govde: str):
    """Yüzeyde görünen gövdeden olası sözlük köklerini üretir (ters çevirim).

    İleri şelale `düşme → yumuşama → ikizleşme` sırasıyla çalıştığı için ters
    çevirim de tam tersi sırayla ve **bileşik** uygulanır. Tek basamaklı ters
    çevirim yetmez: `kaydı` çözümlenirken `kayd` gövdesinden köke ulaşmak için
    önce ötümsüzleştirme (kayd→kayt), sonra ünlünün geri konması (kayt→kayıt)
    gerekir. İki basamağın biri eksikse `kayıt` kökü hiç bulunamaz.

    Bu bir *tahmin* değil aday üretimidir: fazla üretmek zararsızdır, her aday
    `_govde_uretebilir` ile ileri yönde doğrulanır ve tutmayan atılır.
    """
    if not govde:
        return

    for ikizsiz in _ikizlesmeyi_geri_al(govde):
        for otumsuz in _yumusamayi_geri_al(ikizsiz):
            for tam in _unluyu_geri_koy(otumsuz):
                yield tam
                yield from _daralmayi_geri_al(tam)
                yield from _kok_daralmasini_geri_al(tam)
                yield from _unsuz_dusmesini_geri_al(tam)


def _daralmayi_geri_al(govde: str):
    """başl → başla, d → de, ar → ara.

    Ünlü daralmasında kökün son ünlüsü tamamen kaybolur, dolayısıyla kök yüzeyde
    hiç görünmez: "başlıyor" içinde "başla" diye bir önek yoktur. Bu yüzden ters
    çevirimde gövdenin **sonuna** geniş ünlü eklenir.

    Dördü de denenir: Türkçede geniş ünlü a/e/o/ö'dür (a/e köklerde çok
    yaygın, o/ö nadir — "çelikço" gibi standart dışı/alıntı köklerde
    görülüyor, 2026-08-07'de tam sözlük taramasıyla bulundu). "okuyor" gibi
    vakalarda bu üretime gerek kalmaz — orada kök (`oku`) zaten yüzeyin
    önekidir ve normal yoldan bulunur.
    """
    if govde and not fonetik.unlu_mu(govde[-1]):
        yield govde + "a"
        yield govde + "e"
        yield govde + "o"
        yield govde + "ö"


def _kok_daralmasini_geri_al(govde: str):
    """yi → ye, di → de. `KokDaralir` kurallarının ters çevirimi.

    Yalnızca `de-` ve `ye-` fiillerini bulmak için gerekir; üretilen diğer
    adaylar sözlükte karşılık bulmaz ya da `_govde_uretebilir` ile elenir.
    """
    if govde and fonetik.unlu_mu(govde[-1]):
        genis = fonetik.genislet_unlu(govde[-1])
        if genis:
            yield govde[:-1] + genis


def _unsuz_dusmesini_geri_al(govde: str):
    """ufa → ufak, küçü → küçük. `SonUnsuzDuser` kurallarının ters çevirimi.

    Küçültme eki (-CIk) öncesinde düşen kök-sonu ünsüz burada geri konur.
    Yalnızca 'k' denenir — bu, `SonUnsuzDuser` işaretli dört kökün (ufak,
    küçük, büyük, alçak) hepsinde tesadüfen aynı ünsüzdür. Fazla üretmek
    zararsızdır: aday `_govde_uretebilir` ile ileri yönde doğrulanır.
    """
    if govde and fonetik.unlu_mu(govde[-1]):
        yield govde + "k"


def _ikizlesmeyi_geri_al(govde: str):
    """hakk → hak, tıbb → tıb. Değişmemiş hâl de bir adaydır."""
    yield govde
    if len(govde) > 1 and govde[-1] == govde[-2]:
        yield govde[:-1]


def _yumusamayi_geri_al(govde: str):
    """kitab → kitap, reng → renk. Değişmemiş hâl de bir adaydır."""
    yield govde
    for sert, yumusak in _YUMUSAMANIN_TERSI:
        if govde.endswith(yumusak):
            yield govde[:-1] + sert


def _unluyu_geri_koy(govde: str):
    """burn → burun, ağz → ağız, kayt → kayıt. Değişmemiş hâl de bir adaydır.

    Dört dar ünlünün hepsi denenir; ünlü uyumuyla daraltılmaz. Düşen ünlü
    kökün önceki ünlüsüne uymak zorunda değildir: `hapis` (a...i) gibi alıntı
    sözcükler uyuma aykırıdır ve uyuma güvenmek onları çözümlenemez yapıyordu.
    """
    yield govde
    if len(govde) >= 2 and not fonetik.unlu_mu(govde[-1]):
        for unlu in fonetik.DAR_UNLULER:
            yield govde[:-1] + unlu + govde[-1]


def _govde_uretebilir(girdi: SozlukGirdisi, hedef_govde: str) -> bool:
    """Girdi, verilen gövde biçimini üretebilir mi? Aday budaması için hızlı süzgeç.

    İleri şelalenin ürettiği tüm gövde biçimleri toplanır ve hedef bunların
    arasında aranır. Kuralların her biri isteğe bağlı olduğu için (ek ünsüzle
    başlarsa hiçbiri çalışmaz) ara biçimler de geçerli adaydır.
    """
    if girdi.kok == hedef_govde:
        return True

    bicimler = {girdi.kok}

    if Oznitelik.ARA_UNLU_DUSER in girdi.oznitelikler and fonetik.unluyle_bitiyor(girdi.kok):
        bicimler.add(girdi.kok[:-1])

    if Oznitelik.KOK_DARALIR in girdi.oznitelikler and fonetik.unluyle_bitiyor(girdi.kok):
        dar = fonetik.daralt_unlu(girdi.kok[-1])
        if dar:
            bicimler.add(girdi.kok[:-1] + dar)

    if Oznitelik.SON_UNLU_DUSER in girdi.oznitelikler:
        dusmus = fonetik.son_unluyu_dusur(girdi.kok)
        if dusmus:
            bicimler.add(dusmus)

    if Oznitelik.SON_UNSUZ_DUSER in girdi.oznitelikler and girdi.kok:
        bicimler.add(girdi.kok[:-1])

    if Oznitelik.YUMUSAMA in girdi.oznitelikler:
        for bicim in tuple(bicimler):
            yumusak = fonetik.yumusat(bicim)
            if yumusak:
                bicimler.add(yumusak)

    if Oznitelik.IKIZLESME in girdi.oznitelikler:
        for bicim in tuple(bicimler):
            if bicim:
                bicimler.add(bicim + bicim[-1])

    return hedef_govde in bicimler


#: Yalnızca SON KARAKTERİ değiştirebilen/silebilen öznitelikler.
_SON_HARFI_DEGISTIREN = frozenset(
    {Oznitelik.ARA_UNLU_DUSER, Oznitelik.KOK_DARALIR, Oznitelik.YUMUSAMA}
)


def _budama_oneki(yuzey: str, oznitelikler: frozenset[str]) -> str:
    """Budamada güvenle karşılaştırılabilecek önek.

    Bir gövde, kendisinden SONRA gelen ek yüzünden geriye dönük değişebilir:
    `gelme` + `-Iyor` → `gelmiyor` (son ünlü düşer), `gelecek` + `-im` →
    `geleceğim` (son ünsüz yumuşar). Gövdenin tamamını hedefin öneki saymak bu
    yüzden geçerli dalları öldürür — "gelmiyor".startswith("gelme") yanlıştır.

    Kesilecek kısım kuralın gerçekten dokunabildiği kadarıyla sınırlı tutulur;
    fazla kesmek budamayı zayıflatıp aramayı yavaşlatır:

    - daralma, kök daralması, yumuşama → yalnızca **son karakter** değişir
    - ünlü düşmesi → son ünlüden itibarası değişir (burun → burn)
    - ikizleşme → gövde uzar, kısalmaz; önek bozulmaz, kesim gerekmez
    """
    if Oznitelik.SON_UNLU_DUSER in oznitelikler:
        konum = fonetik.son_unlu_konumu(yuzey)
        return yuzey[:konum] if konum >= 0 else yuzey
    if oznitelikler & _SON_HARFI_DEGISTIREN:
        return yuzey[:-1]
    return yuzey


def _dallari_gez(
    girdi: SozlukGirdisi, hedef: str
) -> list[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[Olay, ...]]]:
    """Bir kök adayından hedefe ulaşan tüm ek dizilerini bulur.

    Budama: her adımda üretilen yüzey hedefin öneki değilse dal terk edilir.
    Aramanın patlamamasının tek sebebi budur.
    """
    g = graf()
    baslangic = g.baslangic(girdi.tur)
    if baslangic is None:
        return []

    sonuclar = []
    # (durum, yuzey, gövdenin son morfeminin öznitelikleri,
    #  ek_yuzeyleri, ek_kimlikleri, iz, olaylar)
    yigin: list[tuple[str, str, frozenset, tuple, tuple, tuple, tuple]] = [
        (baslangic, girdi.kok, girdi.oznitelikler, (), (), (girdi.kok,), ())
    ]

    while yigin:
        durum, yuzey, govde_oz, ekler, kimlikler, iz, olaylar = yigin.pop()

        if yuzey == hedef and g.bitebilir_mi(durum):
            sonuclar.append((ekler, kimlikler, iz, olaylar))
            # Devam edilmez: daha uzun bir dal hedefi zaten aşar.
            continue

        # Dikkat: burada `hedef.startswith(yuzey)` denetimi YAPILMAZ. Kökün
        # kendisi hedefin öneki olmayabilir — gövdeyi değiştiren kurallar (yumuşama,
        # ünlü düşmesi, ikizleşme) ancak ek uygulanırken çalışır. "kitap" kökü
        # "kitabı" hedefinin öneki değildir ama geçerli bir yoldur. Budama
        # aşağıda, ek uygulandıktan SONRAKİ yüzeye bakarak yapılır.
        if len(ekler) >= AZAMI_EK:
            continue

        for ek in g.ekler(durum):
            # Ekin öznitelik önkoşulu (`gerektirir`/`yasaklar`) gövdenin O ANKİ
            # son morfemine göre denetlenir, çıplak köke göre değil — docs/decisions.md
            # §9'daki genel kural burada da geçerli. Geniş zaman -(I)r/-(A)r
            # ayrımı çıplak fiil kökünün düzensizliğine bakar (git-er mi gid-ar
            # mı) ama çatı/yapım eki araya girdiğinde (edilgen, dönüşlü, ettirgen,
            # işteş, yeterlilik, kurallı birleşik fiil, isimden fiil -lA/-lAn/-lAş)
            # sonuç HER ZAMAN dar (Aorist_I) tipe döner — "yapar" ama "yapılır",
            # değil "yapılar"; bu yüzden bu ekler kendi `oznitelikler`inde
            # Aorist_I taşır ve govde_oz bunu köküne bakılmaksızın yansıtır.
            if not ek.uygulanabilir_mi(govde_oz):
                continue
            yeni_yuzey, ek_yuzeyi, yeni_olaylar = uygula(yuzey, govde_oz, ek)
            if not hedef.startswith(_budama_oneki(yeni_yuzey, ek.oznitelikler)):
                continue  # ← asıl budama
            yigin.append(
                (
                    ek.hedef,
                    yeni_yuzey,
                    # Gövdenin son morfemi artık bu ek: sonraki kuralları
                    # kökün değil, ekin öznitelikleri belirler.
                    ek.oznitelikler,
                    ekler + (ek_yuzeyi,),
                    kimlikler + (ek.kimlik,),
                    iz + (yeni_yuzey,),
                    olaylar + yeni_olaylar,
                )
            )

    return sonuclar


#: Kesme işareti özel ad/sayı/kısaltmayı ekten ayıran saf bir yazım kuralıdır
#: (Türkiye'nin, 3'ün, TDK'nin) — fonetik bir olay değildir, üretici asla
#: üretmez. Eşleştirme hedefinden çıkarılır; `kelime` alanında özgün yazım kalır.
_KESME_ISARETI_TABLOSU = str.maketrans("", "", "'’")


def kelimeyi_cozumle(kelime: str, sozluk: Sozluk | None = None) -> KelimeSonucu:
    """Tek sözcüğü çözümler.

    Dış API değildir — bağlam olmadan doğru okuma seçilemeyeceği için motorun
    dışarıya verdiği imza `cozumle(cumle)`dir. Bu fonksiyon test ve ölçüm içindir.
    """
    sozluk = sozluk or varsayilan_sozluk()
    hedef = fonetik.kucult(kelime).translate(_KESME_ISARETI_TABLOSU)

    okumalar: list[Okuma] = []
    gorulen: set[tuple] = set()

    for girdi in _kok_adaylari(hedef, sozluk):
        for ekler, kimlikler, iz, olaylar in _dallari_gez(girdi, hedef):
            imza = (girdi.kok, girdi.tur, kimlikler)
            if imza in gorulen:
                continue
            gorulen.add(imza)
            okumalar.append(
                Okuma(
                    kok=girdi.kok,
                    tur=girdi.tur,
                    ekler=ekler,
                    ek_kimlikleri=kimlikler,
                    turetim_izi=iz,
                    olaylar=olaylar,
                )
            )

    return KelimeSonucu(kelime=kelime, okumalar=tuple(okumalar))


def cozumle(cumle: str, sozluk: Sozluk | None = None) -> CumleSonucu:
    """Motorun dış API'si. Cümle seviyesindedir (docs/decisions.md §6)."""
    sozluk = sozluk or varsayilan_sozluk()
    kelimeler = tuple(
        kelimeyi_cozumle(eslesme.group(), sozluk) for eslesme in _KELIME_DESENI.finditer(cumle)
    )
    return CumleSonucu(cumle=cumle, kelimeler=kelimeler)
