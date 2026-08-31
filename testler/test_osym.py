"""ÖSYM politika katmanı testleri.

Katmanın varlık sebebi: ÖSYM'nin ses olaylarına bakışı ile dilbilimsel
çözümleme bazı noktalarda ayrılır ve **ikisi de kendi çerçevesinde doğrudur**.

    çevresi   dilbilim → olay yok      ("çevre" bugün bağımsız bir kök)
              ÖSYM     → ünlü düşmesi  (çevir + e; sözcüğün tarihine bakar)

Motoru ÖSYM'ye göre "düzeltmek" yanlış olurdu: dilbilimsel doğruluğu kaybeder,
kuralı motorun içine gömerdik. v1'in Kural 9'undaki ÖSYM notu tam olarak bu
hataydı. Bu yüzden politika ayrı katmanda, veri dosyasında ve sürümlenebilir.
"""

import pytest

from bitig.cozumleyici import cozumle, kelimeyi_cozumle
from bitig.osym import Mod, gorus, politika


def olay_kumeleri(kelime: str):
    g = gorus(kelimeyi_cozumle(kelime))
    return g.dilbilim, g.osym


# --- Katmanın motoru kirletmediği ------------------------------------------


def test_motor_politikayi_bilmez():
    """`bitig.sozlesme` ve `bitig.cozumleyici` politika modülüne bağımlı olmamalı.
    Bağımlılık ters yönde: politika motoru sarar, motor politikayı bilmez."""
    import bitig.cozumleyici as c
    import bitig.sozlesme as s

    for modul in (c, s):
        kaynak = modul.__file__
        with open(kaynak, encoding="utf-8") as f:
            assert "osym" not in f.read().lower().replace("ösym", ""), (
                f"{modul.__name__} politika katmanına sızmış"
            )


def test_gorus_motor_ciktisini_degistirmez():
    sonuc = kelimeyi_cozumle("çevresi")
    once = set(sonuc.olasi_olaylar)
    gorus(sonuc)
    assert set(sonuc.olasi_olaylar) == once


# --- İki görüş --------------------------------------------------------------


def test_sozluklesmis_turetimde_ayrisir():
    dilbilim, osym = olay_kumeleri("çevresi")
    assert "SES.UD.01" not in dilbilim  # motor "çevre"yi kök bilir
    assert "SES.UD.01" in osym  # ÖSYM çevir+e görür


def test_oyna_ayni_sinif():
    dilbilim, osym = olay_kumeleri("oynamaları")
    assert "SES.UD.01" not in dilbilim
    assert "SES.UD.01" in osym


def test_diye_ayrisir():
    """'diye' sözlükte türetimsiz bağlaç; ÖSYM 'de-' + '-e' (daralma) sayar."""
    dilbilim, osym = olay_kumeleri("diye")
    assert "SES.DAR.01" not in dilbilim
    assert "SES.DAR.01" in osym


@pytest.mark.parametrize("kelime", ["kitabı", "burnu", "hakkı", "kitapta", "hediye"])
def test_cogu_sozcukte_ayrisma_yok(kelime):
    """Politika istisnadır, kural değil. Sözcüklerin ezici çoğunluğunda
    iki görüş aynıdır; ayrışma listesi kısa kalmalı."""
    g = gorus(kelimeyi_cozumle(kelime))
    assert not g.ayrisiyor_mu


def test_ayrismada_gerekce_ve_kaynak_zorunlu():
    g = gorus(kelimeyi_cozumle("çevresi"))
    assert g.notlar
    for not_ in g.notlar:
        assert not_.gerekce and not_.kaynak
        assert not_.yon in ("eklendi", "kaldirildi")


def test_mod_hangi_gorusun_gecerli_oldugunu_secer():
    g = gorus(kelimeyi_cozumle("çevresi"))
    assert g.gecerli(Mod.DILBILIM) == g.dilbilim
    assert g.gecerli(Mod.OSYM) == g.osym
    assert g.gecerli() == g.dilbilim  # varsayılan dilbilim


def test_iki_gorus_de_ciktida_durur():
    """Ayrışma gizlenmez: mod ne olursa olsun her iki küme de çıktıda kalır,
    böylece kullanıcıya 'burada ÖSYM farklı düşünüyor' denebilir."""
    d = gorus(kelimeyi_cozumle("çevresi")).sozluge()
    assert d["ayrisiyor"] is True
    assert d["dilbilim"] and d["osym"]
    assert d["notlar"]


# --- Gerçek ÖSYM sorusu -----------------------------------------------------


def test_cikmis_soru_osym_modunda_cozulur():
    """OGM Materyal (EBA) ses bilgisi testi, soru 12:
    "Aşağıdaki cümlelerin hangisinde ünlü düşmesi yoktur?"  Cevap: D

    Dilbilim modunda üç aday kalır (motor tek başına cevaplayamaz).
    ÖSYM modunda tam olarak doğru cevap çıkar.
    """
    secenekler = {
        "A": "Rıhtımdan ayrılan gemi gittikçe ufaldı",
        "B": "Yaşlı adam çocukları kaldırımda oynamaları konusunda uyardı",
        "C": "Gözleri ışıl ışıl parlayan insanlarla çevresi sarılmıştı",
        "D": "Yaralanmış küçücük serçeyi eline aldı",
        "E": "Hayata geçirilmeye değer gördüğü ilginç bir fikri vardı",
    }

    def olaysiz(mod):
        return {
            harf
            for harf, cumle in secenekler.items()
            if not any("SES.UD.01" in gorus(k).gecerli(mod) for k in cozumle(cumle))
        }

    assert olaysiz(Mod.OSYM) == {"D"}
    assert "D" in olaysiz(Mod.DILBILIM)  # doğru cevap adaylar arasında


# --- Veri bütünlüğü ---------------------------------------------------------


def test_politika_kayitlarinin_kaynagi_var():
    """Her kural çıkmış bir soruya dayanmalı. 'Bence ÖSYM böyle düşünür'
    yeterli değil — ölçüsüz kural, v1'in gömülü listelerine dönüştür."""
    veri = politika()
    for bolum in ("sozluklesmis_turetim", "saymaz"):
        for kayit in veri.get(bolum, []):
            assert kayit.get("kaynak"), f"{bolum}/{kayit.get('kok')}: kaynak yok"
            assert kayit.get("gerekce"), f"{bolum}/{kayit.get('kok')}: gerekçe yok"
            assert kayit.get("olay", "").startswith("SES.")
