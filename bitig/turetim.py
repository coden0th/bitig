"""Türetim şelalesi: gövde + ek → yeni gövde, ve tetiklenen ses olayları.

Motorun kalbi. Bir olay burada, kural fiilen uygulandığı anda doğar; kanıtı da
o anda toplanır. Hiçbir yerde yüzeye bakılıp "acaba burada ne olmuş" diye
tahmin yürütülmez — v1'in yaptığı buydu ve yanlış pozitiflerin kaynağıydı.

Kural sırası keyfî değildir, sözlükteki gerçek köklerle doğrulanmıştır:

    1. Son ünlü düşmesi   (LastVowelDrop)   kayıt → kayt
    2. Ünsüz yumuşaması   (Voicing)         kayt  → kayd     [tıp → tıb]
    3. Ünsüz türemesi     (Doubling)        tıb   → tıbb

`kayıt` (LastVowelDrop+Voicing) 1→2 sırasını, `tıp` (Doubling+Voicing) 2→3
sırasını zorunlu kılar. Sıra bozulursa bu iki sözcük yanlış türetilir.
"""

from __future__ import annotations

from dataclasses import dataclass

from bitig import fonetik
from bitig.sozlesme import Olay, olay_olustur
from bitig.sozluk.girdi import Oznitelik

#: Arketip sembolleri.
UYUM_GENIS = "A"  # a/e
UYUM_DAR = "I"  # ı/i/u/ü
BENZESME_D = "D"  # d/t
BENZESME_C = "C"  # c/ç
BENZESME_G = "G"  # g/k  (sev-gi ama as-kı)

#: Benzeşen sembol → ötümlü biçimi. Sert biçim `fonetik.sertlestir` ile bulunur.
_BENZESEN = {BENZESME_D: "d", BENZESME_C: "c", BENZESME_G: "g"}


@dataclass(frozen=True, slots=True)
class Ek:
    """Morfotaktik graftan gelen tek ek tanımı."""

    kimlik: str
    ad: str
    arketip: str
    hedef: str
    #: Ekin **kendi** kök öznitelikleri. Ek uygulandıktan sonra gövdenin son
    #: morfemi bu ek olduğu için, sonraki ekin göreceği öznitelikler bunlardır.
    #:
    #: Örnek: `-AcAk` ekinin `Voicing`i vardır — gel+ecek+im → "geleceğim".
    #: Yumuşayan `k` köke değil eke aittir. Çoğu ek boş küme taşır ve bu
    #: sayede "burun+lar+ım" gibi dizilerde kök öznitelikleri doğru biçimde
    #: devreden çıkar (burunlarım, "burunlrım" değil).
    oznitelikler: frozenset[str] = frozenset()
    #: Ekin gelebilmesi için gövdede bulunması gereken öznitelikler.
    #: Geniş zaman iki biçimlidir ve hangisinin geleceğini kök belirler:
    #: `-(I)r` yalnızca `Aorist_I`, `-(A)r` yalnızca `Aorist_A` köklerine gelir
    #: (gel-ir ama at-ar). Kısıt kodda değil burada, veride durur.
    gerektirir: frozenset[str] = frozenset()
    #: Ekin gelebilmesi için gövdede bulunmaMAsı gereken öznitelikler.
    #: `gerektirir`in simetriği. Yapım ekleri harf adlarına (`ge`, `te`, `re`…)
    #: bağlanmasın diye kullanılır: "ge" + "-lA" uydurma bir "gele-" fiili
    #: üretip "geliyor"a sahte bir ünlü daralması okuması ekliyordu.
    yasaklar: frozenset[str] = frozenset()
    #: Bu ek ünlü daralmasını tetikler mi? Yalnızca `-Iyor` içindir.
    #: `ProgressiveVowelDrop` özniteliği tek başına yetmez: "ara" bu özniteliği
    #: taşır ama "arayacak"ta daralma yoktur, "arıyor"da vardır. Yani kuralı
    #: kök ile ekin **birlikte** karşılaması gerekir.
    daraltir: bool = False
    #: Bu ek gövdenin son ünsüzünü düşürür mü? Yalnızca küçültme eki `-CIk`
    #: içindir (ufak → ufacık). `SonUnsuzDuser` özniteliği tek başına yetmez:
    #: aynı köke gelen başka bir ek (`-tan` gibi) düşürmeyi tetiklememeli.
    #: Kural, ünlü daralmasıyla aynı desende: kök ile ekin **birlikte**
    #: karşılaması gerekir — bkz. `daraltir`.
    dusurur_unsuz: bool = False

    def uygulanabilir_mi(self, govde_oznitelikleri: frozenset[str]) -> bool:
        return self.gerektirir <= govde_oznitelikleri and not (
            self.yasaklar & govde_oznitelikleri
        )

    @property
    def kaynastirma_harfi(self) -> str:
        """Gövde ünlüyle bitiyorsa araya girecek ünsüz. Yoksa boş dizgi."""
        return self.arketip[1] if self.arketip.startswith("+") else ""


@dataclass(frozen=True, slots=True)
class EkYuzeyi:
    """Arketipin belirli bir gövdeye göre çözülmüş hâli."""

    yuzey: str
    #: Araya giren kaynaştırma ünsüzü (varsa).
    kaynastirma: str = ""
    #: Gövdeye eklenen ilk ses ünlü mü? Gövde değişimlerinin koşulu budur.
    unluyle_basliyor: bool = False
    #: Benzeşme uygulandıysa (D→t, C→ç) değişimden önceki ses.
    benzesen_once: str = ""
    benzesen_sonra: str = ""


def ek_yuzeyi_coz(
    arketip: str,
    govde: str,
    oznitelikler: frozenset[str] = frozenset(),
    uyum_unlusu: str | None = None,
) -> EkYuzeyi:
    """Arketipi gövdeye göre somut yüzeye çevirir.

    Ünlü uyumu **soldan sağa, artımlı** çözülür: her arketip ünlüsü kendinden
    önce gelen son ünlüye bakar. `(I)mIz` ekinde ikinci `I`, birincinin ürettiği
    ünlüye uyar (kitap → kitab-ımız).

    `InverseHarmony` taşıyan köklerde başlangıç ünlüsü karşıtına çevrilir;
    sonraki ünlüler yine normal uyumla ilerler (saat → saat-i, saat-imiz).
    """
    govde_unlu_bitiyor = fonetik.unluyle_bitiyor(govde)
    son_unlu = uyum_unlusu if uyum_unlusu is not None else fonetik.son_unlu(govde)
    if Oznitelik.TERS_UYUM in oznitelikler:
        son_unlu = fonetik.unluyu_ters_cevir(son_unlu)
    son_harf = govde[-1] if govde else ""

    parcalar: list[str] = []
    kaynastirma = ""
    benzesen_once = benzesen_sonra = ""
    ilk_ses = ""

    kalan = arketip

    # 1. Kaynaştırma: "+X" öneki yalnızca gövde ünlüyle bitiyorsa görünür.
    if kalan.startswith("+"):
        harf = kalan[1]
        kalan = kalan[2:]
        if govde_unlu_bitiyor:
            kaynastirma = harf
            parcalar.append(harf)
            ilk_ses = harf

    # 2. Yardımcı ünlü: "(X)" yalnızca gövde ünsüzle bitiyorsa görünür.
    if kalan.startswith("("):
        kapanis = kalan.index(")")
        icerik = kalan[1:kapanis]
        kalan = kalan[kapanis + 1 :]
        if not govde_unlu_bitiyor:
            for sembol in icerik:
                ses = _sembolu_coz(sembol, son_unlu)
                parcalar.append(ses)
                if ses in fonetik.UNLULER:
                    son_unlu = ses
                ilk_ses = ilk_ses or ses

    # 3. Kalan semboller.
    for sembol in kalan:
        if sembol in _BENZESEN:
            # Benzeşme yalnızca ekin ilk sesindeyken gövdeye bakar.
            onceki = parcalar[-1] if parcalar else son_harf
            yumusak = _BENZESEN[sembol]
            ses = fonetik.sertlestir(yumusak) if fonetik.otumsuz_mu(onceki) else yumusak
            if ses != yumusak:
                benzesen_once, benzesen_sonra = yumusak, ses
        else:
            ses = _sembolu_coz(sembol, son_unlu)
        parcalar.append(ses)
        if ses in fonetik.UNLULER:
            son_unlu = ses
        ilk_ses = ilk_ses or ses

    return EkYuzeyi(
        yuzey="".join(parcalar),
        kaynastirma=kaynastirma,
        unluyle_basliyor=bool(ilk_ses) and ilk_ses in fonetik.UNLULER,
        benzesen_once=benzesen_once,
        benzesen_sonra=benzesen_sonra,
    )


def _sembolu_coz(sembol: str, son_unlu: str | None) -> str:
    if sembol == UYUM_GENIS:
        return fonetik.uyumla_a(son_unlu)
    if sembol == UYUM_DAR:
        return fonetik.uyumla_i(son_unlu)
    return sembol


def uygula(
    govde: str, oznitelikler: frozenset[str], ek: Ek
) -> tuple[str, str, tuple[Olay, ...]]:
    """Gövdeye eki uygular; (yeni yüzey, ekin yüzeyi, olaylar) döner.

    `oznitelikler` gövdenin **o andaki son morfemine** aittir: ilk ekte kökün,
    sonraki eklerde bir önceki ekin öznitelikleridir. Gövde değiştiren kurallar
    (ünlü düşmesi, yumuşama, ikizleşme) bu kümeye bakar. Bu tasarım iki durumu
    aynı anda doğru yapar:

        burun + -lar → burunlar      -lAr'ın özniteliği yok, sonraki ek
        burunlar + -ım → burunlarım   ünlü düşmesi tetikleyemez ✓

        gel + -ecek → gelecek        -AcAk'ın Voicing'i var, sonraki ek
        gelecek + -im → geleceğim     k → ğ yumuşaması tetiklenir ✓

    Kaynaştırma ve benzeşme bu kümeye bakmaz: onlar özniteliğe değil, gövdenin
    o andaki ses yapısına bağlı yapısal kurallardır.

    Ekin yüzeyi ayrıca döndürülür çünkü dizgi diliminden çıkarılamaz: ikizleşme
    ve ünlü düşmesi gövdenin uzunluğunu değiştirir, `yeni_yuzey[len(govde):]`
    ikizleşen sesi yanlışlıkla eke yazar (hak + -ı → "hakkı", ek "kı" değil "ı").

    Ünlü uyumunun hangi gövdeye göre çözüleceği kurala göre değişir ve bu ayrım
    ikisini de doğru yapmanın tek yoludur:

    - **Ünlü düşmesi** (LastVowelDrop): uyum ÖZGÜN köke göre.
      `hapis` → "hapsi"; düşmüş gövde `haps`in son ünlüsü `a` olduğu için ona
      bakılsaydı "hapsı" çıkardı.
    - **Ünlü daralması** (ProgressiveVowelDrop): uyum DARALMIŞ gövdeye göre.
      `söyle` → `söyl` (son ünlü `ö`) → "söylüyor"; özgün köke bakılsaydı
      (son ünlü `e`) "söyliyor" çıkardı.
    """
    olaylar: list[Olay] = []

    # Ünlü daralması ekin yüzeyi çözülmeden ÖNCE uygulanır, çünkü ek uyumunu
    # daralmış gövdeye göre alır:
    #
    #     söyle → söyl (son ünlü ö) → söyl + üyor = söylüyor   ✓
    #     özgün köke (söyle, son ünlü e) bakılsaydı → "söyliyor" ✗
    #
    # Bu, ünlü düşmesinin (LastVowelDrop) tam TERSİDİR; orada uyum özgün köke
    # göre çözülür (hapis → hapsi, "hapsı" değil). İki kural aynı görünüp zıt
    # davrandığı için ayrı ayrı ele alınır — bkz. `_son_unlu_dusmesi`.
    daralmis_govde, daralma_var = _daralt(govde, oznitelikler, ek)
    if not daralma_var:
        daralmis_govde, daralma_var = _kok_daralt(govde, oznitelikler, ek)

    # Daralma gövdedeki tek ünlüyü de silmiş olabilir: "de" → "d", "ye" → "y".
    # Ünlü kalmayınca uyumun dayanağı kalmaz ve varsayılan `ı`ya düşerdi
    # ("dıyor"). Böyle durumlarda uyum özgün kökün ünlüsünden alınır: de → e →
    # "iyor" → "diyor", ye → "yiyor".
    uyum_unlusu = fonetik.son_unlu(daralmis_govde)
    if daralma_var and uyum_unlusu is None:
        uyum_unlusu = fonetik.son_unlu(govde)

    # Ünsüz düşmesi de (ünlü daralması gibi) ek çözülmeden ÖNCE uygulanır:
    # "-CIk" ekinin c/ç benzeşmesi, düşmüş gövdenin son sesine bakar
    # (ufa+cık, "ufakçık" değil — k zaten düşmüş olmalı ki c yumuşak kalsın).
    govde_unsuz_dustu = ek.dusurur_unsuz and Oznitelik.SON_UNSUZ_DUSER in oznitelikler
    if govde_unsuz_dustu:
        onceki_govde = daralmis_govde
        daralmis_govde = daralmis_govde[:-1]

    ek_bilgisi = ek_yuzeyi_coz(ek.arketip, daralmis_govde, oznitelikler, uyum_unlusu)
    yeni_govde = daralmis_govde

    if govde_unsuz_dustu:
        olaylar.append(
            olay_olustur(
                kural_id="SES.UND.01",
                konum=len(daralmis_govde),
                once=onceki_govde[-1],
                sonra="",
                tetikleyen_ek=ek_bilgisi.yuzey,
                govde=onceki_govde,
            )
        )

    if daralma_var:
        # Ünlü DÜŞTÜ diye olay bildirilmez; ünlü DARALDI diye bildirilir.
        # "oku" + -Iyor yapısal olarak "ok"a düşer (yoksa "okuuyor" olurdu) ama
        # ortada daralma yoktur: `u` zaten dar. ÖSYM'nin kuralı "geniş ünlü
        # (a, e) daralır" biçimindedir ve çıkmış sorularda "okuyor" ünlü
        # daralmasının OLMADIĞI seçenek olarak sorulmuştur.
        olay = _daralma_olayi(govde, daralmis_govde, ek_bilgisi)
        if olay.kanit.once in fonetik.GENIS_UNLULER:
            olaylar.append(olay)
    elif ek_bilgisi.unluyle_basliyor:
        yeni_govde, dusme = _son_unlu_dusmesi(yeni_govde, oznitelikler, ek_bilgisi.yuzey)
        olaylar.extend(dusme)

        yeni_govde, yumusama = _unsuz_yumusamasi(yeni_govde, oznitelikler, ek_bilgisi.yuzey)
        olaylar.extend(yumusama)

        yeni_govde, ikizlesme = _unsuz_turemesi(yeni_govde, oznitelikler, ek_bilgisi.yuzey)
        olaylar.extend(ikizlesme)

    if ek_bilgisi.kaynastirma:
        olaylar.append(
            olay_olustur(
                kural_id="SES.KAY.01",
                konum=len(yeni_govde),
                once="",
                sonra=ek_bilgisi.kaynastirma,
                tetikleyen_ek=ek_bilgisi.yuzey,
                govde=yeni_govde,
            )
        )

    if ek_bilgisi.benzesen_once:
        olaylar.append(
            olay_olustur(
                kural_id="SES.BEN.01",
                konum=len(yeni_govde),
                once=ek_bilgisi.benzesen_once,
                sonra=ek_bilgisi.benzesen_sonra,
                tetikleyen_ek=ek_bilgisi.yuzey,
                govde=yeni_govde,
            )
        )

    return yeni_govde + ek_bilgisi.yuzey, ek_bilgisi.yuzey, tuple(olaylar)


def _daralt(govde: str, oznitelikler: frozenset[str], ek: Ek) -> tuple[str, bool]:
    """Daralma koşulu oluşuyorsa gövdenin son ünlüsünü düşürür.

    Koşul **iki taraflıdır**: gövdede `ProgressiveVowelDrop`, ekte `daraltir`.
    İkisi birden gerekir — "ara" özniteliği taşır ama "arayacak"ta daralma
    yoktur, "arıyor"da vardır.

    Ünsüzle biten fiillerde hiç çalışmaz: "geliyor"daki `i` yardımcı ünlüdür,
    daralma değil. v1 bunu Kural 9'da elle ayırmaya çalışıyordu; burada
    `ProgressiveVowelDrop` özniteliğinin yokluğu zaten ayırıyor.
    """
    if not ek.daraltir or Oznitelik.ARA_UNLU_DUSER not in oznitelikler:
        return govde, False
    if not fonetik.unluyle_bitiyor(govde):
        return govde, False
    return govde[:-1], True


def _kok_daralt(govde: str, oznitelikler: frozenset[str], ek: Ek) -> tuple[str, bool]:
    """de- / ye- fiillerinin geniş ünlüsünü daraltır: de → di, ye → yi.

    `_daralt`tan farkı, ünlünün **düşmemesi** dar biçime dönüşmesidir ve bunun
    ünlüyle başlayan her ekten önce olmasıdır:

        ye + -AcAk  → yi + yecek  → yiyecek
        ye + -An    → yi + yen    → yiyen
        ye + -DI    → yedi                    (ek ünsüzle başlıyor, daralma yok)

    Ek doğrudan ünlüyle başlayabileceği gibi kaynaştırma da alabilir; ikisi de
    "aslında ünlüyle başlıyor" demektir, bu yüzden koşul ikisini birden kapsar.
    """
    if Oznitelik.KOK_DARALIR not in oznitelikler or not fonetik.unluyle_bitiyor(govde):
        return govde, False

    # Ekin gerçekten ünlüyle başlayıp başlamadığını anlamak için arketipe bakılır:
    # "+yAcAk" gövde ünlüyle bittiğinde "yecek" olur ve yüzeyde ünsüzle başlar,
    # ama altta yatan ek ünlüyle başlar.
    cekirdek = ek.arketip[2:] if ek.arketip.startswith("+") else ek.arketip
    if not cekirdek or cekirdek[0] not in (UYUM_GENIS, UYUM_DAR):
        return govde, False

    dar = fonetik.daralt_unlu(govde[-1])
    if dar is None:
        return govde, False
    return govde[:-1] + dar, True


def _daralma_olayi(ozgun_govde: str, daralmis_govde: str, ek_bilgisi: EkYuzeyi) -> Olay:
    """Daralma olayını kanıtıyla üretir.

    Mekanizma ile öğretilen ad birbirinden ayrıdır ve kanıt **öğretileni**
    yazar. Öğrenciye öğretilen sonuçtur: geniş ünlü daraldı (a→ı, e→i). Bu
    yüzden `once` daralan geniş ünlü, `sonra` onun yerini alan dar ünlüdür.

    Dar ünlünün nereden geldiği iki kuralda farklıdır:

    - `_daralt` (başla → başl + ıyor): gövdenin ünlüsü tamamen düşer, dar ünlü
      **ekten** gelir → ekin ilk ünlüsüne bakılır.
    - `_kok_daralt` (ye → yi + yecek): ünlü düşmez, **gövdede** dar biçime
      dönüşür → daralmış gövdenin son ünlüsüne bakılır.
    """
    konum = len(ozgun_govde) - 1
    if len(daralmis_govde) == len(ozgun_govde):
        sonra = daralmis_govde[konum]  # kök daraldı, ünlü yerinde durdu
    else:
        sonra = fonetik.ilk_unlu(ek_bilgisi.yuzey) or ""  # ünlü düştü, ek doldurdu
    return olay_olustur(
        kural_id="SES.DAR.01",
        konum=konum,
        once=ozgun_govde[konum],
        sonra=sonra,
        tetikleyen_ek=ek_bilgisi.yuzey,
        govde=ozgun_govde,
    )


def _son_unlu_dusmesi(
    govde: str, oznitelikler: frozenset[str], ek_yuzeyi: str
) -> tuple[str, list[Olay]]:
    """burun + -u → burnu. Koşul: `LastVowelDrop` özniteliği."""
    if Oznitelik.SON_UNLU_DUSER not in oznitelikler:
        return govde, []
    konum = fonetik.son_unlu_konumu(govde)
    dusmus = fonetik.son_unluyu_dusur(govde)
    if dusmus is None or konum < 0:
        return govde, []
    return dusmus, [
        olay_olustur(
            kural_id="SES.UD.01",
            konum=konum,
            once=govde[konum],
            sonra="",
            tetikleyen_ek=ek_yuzeyi,
            govde=govde,
        )
    ]


def _unsuz_yumusamasi(
    govde: str, oznitelikler: frozenset[str], ek_yuzeyi: str
) -> tuple[str, list[Olay]]:
    """kitap + -ı → kitabı. Koşul: `Voicing` özniteliği.

    `NoVoicing` denetimi burada yapılmaz: sözlük katmanı zaten `Voicing` ile
    `NoVoicing`i birbirini dışlayacak biçimde üretir. İki yerde denetlemek
    kuralı iki kaynağa bölerdi.
    """
    if Oznitelik.YUMUSAMA not in oznitelikler:
        return govde, []
    yumusak = fonetik.yumusat(govde)
    if yumusak is None:
        return govde, []
    konum = len(govde) - 1
    return yumusak, [
        olay_olustur(
            kural_id="SES.YUM.01",
            konum=konum,
            once=govde[konum],
            sonra=yumusak[konum],
            tetikleyen_ek=ek_yuzeyi,
            govde=govde,
        )
    ]


def _unsuz_turemesi(
    govde: str, oznitelikler: frozenset[str], ek_yuzeyi: str
) -> tuple[str, list[Olay]]:
    """hak + -ı → hakkı. Koşul: `Doubling` özniteliği.

    Yumuşamadan **sonra** çalışır: tıp → (yumuşama) tıb → (ikizleşme) tıbb.
    """
    if Oznitelik.IKIZLESME not in oznitelikler or not govde:
        return govde, []
    son = govde[-1]
    return govde + son, [
        olay_olustur(
            kural_id="SES.UT.01",
            konum=len(govde),
            once=son,
            sonra=son + son,
            tetikleyen_ek=ek_yuzeyi,
            govde=govde,
        )
    ]
