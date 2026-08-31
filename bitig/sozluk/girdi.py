"""Sözlük girdisinin tipi ve sabitleri.

Öznitelik ve tür değerleri Zemberek `.dict` dosyalarındaki dizgilerin **aynısıdır**,
Türkçeleştirilmez. Sebep: bu değerler bizim yazdığımız veri değil, kaynak dosyanın
kendi içeriğidir; çevirmek kaynakla aramıza sessizce kayabilecek bir eşleme katmanı
sokar. Bunun yerine Türkçe adlı sabitler tanımlanır — kodda `Oznitelik.YUMUSAMA`
yazılır, dizgi sabiti elle yazılmaz.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class Tur:
    """Birincil sözcük türü (Zemberek PrimaryPos değerleri)."""

    ISIM = "Noun"
    SIFAT = "Adj"
    FIIL = "Verb"
    ZARF = "Adv"
    ZAMIR = "Pron"
    BAGLAC = "Conj"
    EDAT = "Postp"
    UNLEM = "Interj"
    SAYI = "Num"
    IKILEME = "Dup"
    BELIRTEC = "Det"
    SORU = "Ques"
    NOKTALAMA = "Punc"

    #: Öznitelik çıkarımında isim gibi davranan türler.
    ISIMSILER = frozenset({ISIM, SIFAT, IKILEME})


class IkincilTur:
    OZEL_ISIM = "Prop"
    KISALTMA = "Abbrv"


class Oznitelik:
    """Kök öznitelikleri (Zemberek RootAttribute değerleri).

    Türetim kurallarını tetikleyen bayraklar. v1'in altdizi taramasının yerini
    bunlar alır: kuralı yüzeydeki harf dizisi değil, kökün özniteliği tetikler.
    """

    # Ses olaylarını tetikleyenler
    YUMUSAMA = "Voicing"  # kitap → kitabı
    YUMUSAMA_YOK = "NoVoicing"  # diyet → diyeti (yumuşamaz)
    SON_UNLU_DUSER = "LastVowelDrop"  # burun → burnu
    IKIZLESME = "Doubling"  # hak → hakkı
    TERS_UYUM = "InverseHarmony"  # saat → saati (kalın kök, ince ek)
    ARA_UNLU_DUSER = "ProgressiveVowelDrop"  # de- + -Iyor → diyor  (Dilim 2)

    #: BitigAI'nin kendi özniteliği (Zemberek'te karşılığı yok).
    #: Kökün geniş ünlüsü, ünlüyle başlayan HER ekten önce daralır.
    #: Yalnızca `de-` ve `ye-` fiilleri taşır: diyecek, yiyen, diyerek.
    #: Bu iki fiil Türkçe'nin bilinen düzensizliğidir; kural değil istisnadır,
    #: bu yüzden kodda değil `veri/tyt_override.json` içinde işaretlenir.
    KOK_DARALIR = "KokDaralir"

    #: BitigAI'nin kendi özniteliği (Zemberek'te karşılığı yok).
    #: Kökün son ünsüzü ("k"), küçültme eki (-CIk) geldiğinde tamamen düşer:
    #: ufak → ufacık, küçük → küçücük. Bunun HER k-sonlu sözcükte geçerli
    #: genel bir fonolojik kural mı yoksa kapalı bir liste mi olduğu ölçülmedi
    #: — bu yüzden yalnızca çıkmış soruyla doğrulanan kökler için
    #: `tyt_override.json` üzerinden işaretlenir (NoVoicing'in aynadaki eşi:
    #: geniş bir kuralı riske atmak yerine dar bir istisna listesiyle başla).
    SON_UNSUZ_DUSER = "SonUnsuzDuser"

    # Fiil çekimi (Dilim 2'de kullanılacak)
    GENIS_ZAMAN_I = "Aorist_I"
    GENIS_ZAMAN_A = "Aorist_A"
    EDILGEN_IN = "Passive_In"
    ETTIRGEN_T = "Causative_t"

    # Morfotaktik kısıtlar
    EK_ALMAZ = "NoSuffix"
    ORTUK_COGUL = "ImplicitPlural"
    ORTUK_YONELME = "ImplicitDative"
    BIRLESIK_IYELIK = "CompoundP3sg"
    BIRLESIK_KOK = "CompoundP3sgRoot"
    ISIM_N_KAYNASTIRMA = "NounConsInsert_n"

    # Bilgi amaçlı
    TDK_DISI = "Ext"
    TEKLIFSIZ = "Informal"
    KESME_YOK = "NoQuote"


@dataclass(frozen=True, slots=True)
class SozlukGirdisi:
    """Tek bir sözlük kaydı.

    `yuzey` sözlükteki yazılıştır ("demek"), `kok` türetimin başladığı biçimdir
    ("de"). İsimlerde ikisi aynıdır; fiillerde mastar eki atılmıştır.
    """

    yuzey: str
    kok: str
    tur: str
    ikincil_tur: str | None = None
    oznitelikler: frozenset[str] = field(default_factory=frozenset)
    #: Aynı yazılışın kaçıncı anlamı (dosyadaki `Index:` alanı).
    sira: int = 0
    telaffuz: str | None = None
    #: `CompoundP3sg` girdilerinde bileşiği oluşturan kökler (`Roots:aş-ev`).
    bilesik_kokler: tuple[str, ...] = ()

    @property
    def kimlik(self) -> str:
        """Girdiyi tekilleştiren kimlik. Aynı yüzeyin farklı türleri ayrışır."""
        return f"{self.yuzey}_{self.tur}_{self.sira}"

    def var_mi(self, oznitelik: str) -> bool:
        return oznitelik in self.oznitelikler
