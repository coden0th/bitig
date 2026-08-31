"""`atasozu.py` testleri — ağ gerektirmez, yerel dondurulmuş kopyayı okur.

İndirme aracının kendisi (`harness/atasozu_indir.py`) ağ gerektirdiği için
burada test edilmez.
"""

from __future__ import annotations

from atasozu import bul, ara


def test_bul_tam_eslesme():
    kayitlar = bul("aba altında er yatar")
    assert len(kayitlar) == 1
    assert kayitlar[0].tur == "atasozu"
    assert "giyim kuşam" in kayitlar[0].anlam


def test_bul_buyuk_kucuk_harf_duyarsiz():
    assert bul("ABA ALTINDA ER YATAR") == bul("aba altında er yatar")


def test_bul_olmayan_soz_bos_doner():
    assert bul("bu söz sözlükte kesinlikle yok xyzabc123") == ()


def test_bul_deyim_turu_dogru():
    kayitlar = bul("aba gibi")
    assert len(kayitlar) == 1
    assert kayitlar[0].tur == "deyim"


def test_ara_alt_dize_kaba_tarama():
    kayitlar = ara("kafayı")
    assert len(kayitlar) > 5
    assert all("kafayı" in k.soz.lower() or "kafayı" in k.soz for k in kayitlar)


def test_kayit_sayisi_beklenen_araliktadir():
    """Sözlük ~13.5k kayıt taşımalı — bir bozulma olursa (boş dosya, kısmi
    indirme) bu test yakalar."""
    from atasozu import _kayitlar

    assert len(_kayitlar()) > 13000
