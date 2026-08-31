"""Sözlük katmanı testleri: satır grameri + öznitelik çıkarımı.

Bu dosya motorun kabul kapısıdır. v1'in yanlış pozitiflerinin tamamı burada
negatif vaka olarak duruyor: `güdük`, `yudum`, `sepet`, `diyet`, `niyet`, `saat`.
Bu testler geçtiği sürece türetim katmanı o kelimelerde kural tetikleyemez —
çünkü tetikleyecek öznitelik ortada yoktur.
"""

import pytest

from bitig.sozluk import oznitelik
from bitig.sozluk.ayristirici import AyristirmaHatasi, ayristir
from bitig.sozluk.girdi import IkincilTur, Oznitelik, Tur


def oz(satir: str) -> frozenset[str]:
    """Satırı ayrıştırıp çıkarımla zenginleştirilmiş öznitelik kümesini döner."""
    girdi = ayristir(satir)
    assert girdi is not None
    return oznitelik.cikar(girdi)


# --- Satır grameri ----------------------------------------------------------


def test_ciplak_satir_gecerli_girdi():
    # Sözlüğün 18.625 satırı böyle. Eksik kayıt değil, çıkarıma bırakılmış kayıt.
    girdi = ayristir("kitap")
    assert girdi is not None
    assert (girdi.yuzey, girdi.kok, girdi.tur) == ("kitap", "kitap", Tur.ISIM)
    assert girdi.oznitelikler == frozenset()  # dosyada yazan: hiçbir şey


def test_tam_alanli_satir():
    girdi = ayristir("kayıp [P:Adj; A:Voicing, LastVowelDrop; Index:2]")
    assert girdi.tur == Tur.SIFAT
    assert girdi.oznitelikler == {Oznitelik.YUMUSAMA, Oznitelik.SON_UNLU_DUSER}
    assert girdi.sira == 2


def test_mastar_ekli_satir_fiil_olur_ve_kok_kisalir():
    girdi = ayristir("demek")
    assert girdi.tur == Tur.FIIL
    assert girdi.kok == "de"  # mastar eki atılır, türetim buradan başlar


def test_acik_tur_mastari_ezer():
    # "yemek [P:Noun]" yiyecek anlamındadır; kök kısaltılmaz.
    girdi = ayristir("yemek [P:Noun]")
    assert girdi.tur == Tur.ISIM
    assert girdi.kok == "yemek"


def test_ikincil_tur_ozel_isim_cikarimi():
    assert ayristir("Ankara").ikincil_tur == IkincilTur.OZEL_ISIM
    assert ayristir("kitap").ikincil_tur is None


def test_bilesik_kokler():
    girdi = ayristir("acemborusu [A:CompoundP3sg; Roots:acem-boru]")
    assert girdi.bilesik_kokler == ("acem", "boru")


def test_telaffuz_alani_kucuk_harfli_anahtarla_da_okunur():
    assert ayristir("gram [Pr:gıram]").telaffuz == "gıram"


def test_bos_ve_yorum_satirlari_atlanir():
    assert ayristir("") is None
    assert ayristir("   ") is None
    assert ayristir("## açıklama") is None


@pytest.mark.parametrize("satir", ["kitap [P:Noun", "kitap [Noun]", "kitap [Index:x]"])
def test_bozuk_satir_sessizce_yutulmaz(satir):
    with pytest.raises(AyristirmaHatasi):
        ayristir(satir)


# --- Yumuşama çıkarımı: POZİTİF --------------------------------------------


@pytest.mark.parametrize(
    "satir",
    [
        "kitap",  # çok heceli + p  → kitabı
        "ağaç",  # çok heceli + ç  → ağacı
        "kanat",  # çok heceli + t  → kanadı
        "çocuk",  # çok heceli + k  → çocuğu
        "kâğıt",  # şapkalı da olsa kural aynı → kâğıdı
    ],
)
def test_yumusama_cikarilir(satir):
    assert Oznitelik.YUMUSAMA in oz(satir)


def test_nk_ve_og_sonu_tek_heceli_olsa_da_yumusar():
    assert Oznitelik.YUMUSAMA in oz("renk")  # renk → rengi
    assert Oznitelik.YUMUSAMA_YOK not in oz("renk")


# --- Yumuşama çıkarımı: NEGATİF (v1'in yanlış pozitifleri) ------------------


@pytest.mark.parametrize(
    "satir,gerekce",
    [
        ("diyet [A:NoVoicing]", "sözlükte açıkça yasaklı"),
        ("niyet [A:NoVoicing]", "sözlükte açıkça yasaklı"),
        ("sepet [A:NoVoicing]", "sözlükte açıkça yasaklı"),
        ("saat [A:InverseHarmony, NoVoicing]", "ters uyum + açık yasak"),
        ("yudum [P:Adj]", "ötümsüz süreksizle bitmiyor (m)"),
        ("top", "tek heceli"),
        ("saç", "tek heceli"),
        ("hediye", "ünlüyle bitiyor"),
        ("çarşamba", "ünlüyle bitiyor"),
    ],
)
def test_yumusama_cikarilmaz(satir, gerekce):
    assert Oznitelik.YUMUSAMA not in oz(satir), gerekce


def test_guduk_yumusama_YETENEGI_tasir_ama_bu_olay_demek_degildir():
    """v1'in `güdük` hatasının doğru okunuşu.

    `güdük` iki heceli ve `k` ile biter; Türkçe'de gerçekten yumuşar: *güdüğü*.
    Yani öznitelik doğrudur, v1'in listesi de sezgi olarak yanlış değildi.

    v1'in hatası ölçüm noktasındaydı: `"güd" in kelime` dediği için, **ek almamış**
    `güdük` sözcüğüne de ünsüz yumuşaması olayı basıyordu. Oysa ortada yumuşamış
    bir ses yok — kelime kökün kendisi.

    Bu ayrım motorun varlık sebebidir: olayı öznitelik doğurmaz, özniteliğin
    *fiilen uygulanmış bir ekle* buluşması doğurur. Dolayısıyla bu testin
    karşılığı türetim katmanındadır (bkz. test_turetim: güdük → olay yok,
    güdüğü → SES.YUM.01).
    """
    assert Oznitelik.YUMUSAMA in oz("güdük [P:Adj]")


def test_tek_heceli_novoicing_alir():
    assert Oznitelik.YUMUSAMA_YOK in oz("top")
    assert Oznitelik.YUMUSAMA_YOK in oz("saç")


def test_ozel_isim_yumusamaz():
    # "Sinop" özel addır: Sinop'u, Sinob'u değil.
    assert Oznitelik.YUMUSAMA not in oz("Sinop [P:Noun,Prop]")


def test_kisaltma_yumusamaz():
    assert Oznitelik.YUMUSAMA not in oz("TSK [P:Noun,Abbrv]")


def test_acik_oznitelik_cikarimi_ezer():
    """`diyet` iki heceli ve `t` ile biter — çıkarım kuralı yumuşama derdi.
    Sözlükteki açık `NoVoicing` bunu bastırır. v1'de bu mekanizma hiç yoktu."""
    assert Oznitelik.YUMUSAMA in oz("diyet")  # açık öznitelik olmasaydı...
    assert Oznitelik.YUMUSAMA not in oz("diyet [A:NoVoicing]")  # ...ama var.


# --- Bayrakla tetiklenen diğer olaylar --------------------------------------


@pytest.mark.parametrize("satir", ["burun [A:LastVowelDrop]", "ağız [A:LastVowelDrop]"])
def test_son_unlu_dusmesi_bayrakla_gelir(satir):
    assert Oznitelik.SON_UNLU_DUSER in oz(satir)


def test_ikizlesme_bayrakla_gelir():
    assert Oznitelik.IKIZLESME in oz("hak [A:Doubling]")


def test_ikizlesme_cikarilmaz():
    # "hak" bayrağı olmasa ikizleşme *çıkarılamaz* — çıkarım kuralı yoktur.
    assert Oznitelik.IKIZLESME not in oz("hak")


# --- Fiil çıkarımı (Dilim 2'de kullanılacak) --------------------------------


def test_unluyle_biten_fiil_ara_unlu_duser():
    """`de-` ve `ye-` bu bayrağı alır; `hediye`/`diyet` isimdir, almaz.
    v1'in en kötü hatası (`"diye" in kelime`) burada kökten çözülür."""
    assert Oznitelik.ARA_UNLU_DUSER in oz("demek")
    assert Oznitelik.ARA_UNLU_DUSER in oz("yemek")
    assert Oznitelik.ARA_UNLU_DUSER in oz("aramak")
    assert Oznitelik.ARA_UNLU_DUSER not in oz("hediye")
    assert Oznitelik.ARA_UNLU_DUSER not in oz("diyet [A:NoVoicing]")
    assert Oznitelik.ARA_UNLU_DUSER not in oz("gelmek")


def test_genis_zaman_bicimi():
    assert Oznitelik.GENIS_ZAMAN_A in oz("gelmek")  # tek heceli → gel-ir? hayır: -Ar
    assert Oznitelik.GENIS_ZAMAN_I in oz("aramak")  # çok heceli → ara-r/-Ir
    # Açıkça yazılmışsa çıkarım ezmez.
    assert Oznitelik.GENIS_ZAMAN_A in oz("kapatmak [A:Aorist_A]")
    assert Oznitelik.GENIS_ZAMAN_I not in oz("kapatmak [A:Aorist_A]")


def test_fiil_kurallari_isme_uygulanmaz():
    assert Oznitelik.GENIS_ZAMAN_A not in oz("kitap")
    assert Oznitelik.EDILGEN_IN not in oz("masa")
