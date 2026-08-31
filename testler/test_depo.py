"""Depo testleri: yükleme, indeks, override, tembellik.

Buradaki `test_gercek_sozluk_*` testleri asıl veriye karşı çalışır. Yavaş
değiller (~1 sn) ve ayrıştırıcıdaki bir gerilemeyi 56 bin satırda anında
yakaladıkları için ayrı işaretlenmediler.
"""

import json

import pytest

from bitig.sozluk.depo import Sozluk, varsayilan_sozluk
from bitig.sozluk.girdi import Oznitelik, Tur


@pytest.fixture(scope="module")
def sozluk() -> Sozluk:
    return varsayilan_sozluk()


# --- Gerçek veriye karşı ----------------------------------------------------


def test_gercek_sozluk_tamami_ayristirilir(sozluk):
    """Tek bir satır bile sessizce düşmemeli. Veri hatası görünür olmalı."""
    assert sozluk.bozuk_satirlar == []


def test_gercek_sozluk_boyutu_makul(sozluk):
    # Beklenen mertebe ~35 bin girdi. Ciddi bir sapma yükleme hatasıdır.
    assert 30_000 < len(sozluk) < 45_000


def test_koseli_parantez_noktalama_girdisi_okunur(sozluk):
    """Sözlükte kelimenin kendisi "[" olan bir kayıt var. Ayrıştırıcının
    alan ayırıcısını sondan araması bu yüzden gerekli."""
    assert sozluk.ara("[")


# --- Belirsizlik korunuyor mu ----------------------------------------------


def test_yemek_hem_fiil_hem_isim(sozluk):
    """"yemek" hem "ye-" fiili hem yiyecek adıdır. İkisi de dönmeli;
    v1 `analizler[0][0]` diyerek birini siliyordu."""
    fiiller = [g for g in sozluk.ara("ye") if g.tur == Tur.FIIL]
    isimler = [g for g in sozluk.ara("yemek") if g.tur == Tur.ISIM]
    assert fiiller and isimler


def test_de_uc_ayri_tur(sozluk):
    turler = {g.tur for g in sozluk.ara("de")}
    assert {Tur.FIIL, Tur.BAGLAC} <= turler


# --- Çıkarım depodan çıkarken uygulanmış mı --------------------------------


@pytest.mark.parametrize(
    "kok,oznitelik",
    [
        ("kitap", Oznitelik.YUMUSAMA),
        ("renk", Oznitelik.YUMUSAMA),
        ("burun", Oznitelik.SON_UNLU_DUSER),
        ("saat", Oznitelik.TERS_UYUM),
    ],
)
def test_depodan_cikan_girdi_oznitelikleri_tam(sozluk, kok, oznitelik):
    assert any(oznitelik in g.oznitelikler for g in sozluk.ara(kok))


@pytest.mark.parametrize("kok", ["diyet", "niyet", "saat"])
def test_yumusamasi_yasak_kokler(sozluk, kok):
    girdiler = [g for g in sozluk.ara(kok) if g.tur == Tur.ISIM]
    assert girdiler
    assert all(Oznitelik.YUMUSAMA not in g.oznitelikler for g in girdiler)


def test_bilinmeyen_kok_bos_doner(sozluk):
    assert sozluk.ara("zzzqqq") == ()
    assert "zzzqqq" not in sozluk


# --- Tembellik --------------------------------------------------------------


def test_yukleme_tembel(tmp_path):
    """Nesne kurulurken dosyaya dokunulmamalı — motor servis olarak yüklenecek."""
    s = Sozluk(dosyalar=("yok-boyle-bir-dosya.dict",), dizin=tmp_path)
    assert s._indeks is None  # kurulum tek başına yükleme yapmadı
    with pytest.raises(Exception):
        s.ara("kitap")  # ilk sorguda yüklemeye kalkıp patlar


# --- Override ---------------------------------------------------------------


def test_override_ekler_ve_kaldirir(tmp_path):
    dizin = tmp_path / "zemberek"
    dizin.mkdir()
    (dizin / "mini.dict").write_text("kitap\nmasa\n", encoding="utf-8")

    override = tmp_path / "override.json"
    override.write_text(
        json.dumps({"kaldir": ["masa"], "ekle": ["bitig [P:Noun; A:NoVoicing]"]}),
        encoding="utf-8",
    )

    s = Sozluk(dosyalar=("mini.dict",), dizin=dizin, override_yolu=override)
    assert s.ara("kitap")  # dokunulmamış
    assert not s.ara("masa")  # kaldırıldı
    assert Oznitelik.YUMUSAMA_YOK in s.ara("bitig")[0].oznitelikler  # eklendi


def test_override_dosyasi_gecerli_json_ve_semasi_dogru():
    """Depoda duran gerçek override dosyası her zaman yüklenebilir olmalı."""
    from bitig.sozluk.depo import OVERRIDE_YOLU

    veri = json.loads(OVERRIDE_YOLU.read_text(encoding="utf-8"))
    assert isinstance(veri.get("kaldir", []), list)
    assert isinstance(veri.get("ekle", []), list)
