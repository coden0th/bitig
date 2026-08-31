"""TDK Güncel Türkçe Sözlük API istemcisi — yalnızca senkronizasyon aracı.

**Bu dosya ağ çağrısı yapar, yalnızca `harness/tdk_senkron.py` tarafından
kullanılır.** Üretim hattı (`bitig/`, `yazim.py`) buna hiçbir zaman bağımlı
değildir — çalışma zamanında yalnızca `veri/tdk_onbellek.json`ya bakılır
(`[[yazim-motoru-plani]]`: "üretim bağımlılığı sıfır" ilkesi, canlı TDK API
çağrısı çekirdek akışta reddedilmişti).

API anahtar gerektirmez (genel/açık uç nokta). User-Agent başlığı olmadan
bağlantı reddediliyor — bu istemci tarafında zaten ayarlı.

Çalıştırma:  .venv/bin/python -m harness.tdk_senkron ...  (bu dosya tek başına çalıştırılmaz)
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

TABAN_URL = "https://sozluk.gov.tr/gts"
ZAMAN_ASIMI = 10
#: HTTP başlık değerleri yalnızca latin-1 kabul eder — Türkçe harf yasak.
BASLIKLAR = {"User-Agent": "Mozilla/5.0 (BitigAI sozluk senkronizasyon araci)"}


class TdkHatasi(RuntimeError):
    pass


def sorgula(kelime: str) -> dict:
    """TDK'de kelimeyi arar. Ham API yanıtını yorumlayıp özet döner:

        {"gecerli": bool, "ilk_anlam_yonlendirme": str | None}

    `ilk_anlam_yonlendirme`, kelimenin İLK anlamı doğrudan başka bir madde-
    ye işaret ediyorsa ("► X" biçimi) o hedefi taşır — hem yazım güncellemesi
    (çiğ börek→çi börek) hem eşanlamlı öneri (restoran→lokanta) bu biçimde
    görünüyor, ikisi TDK yanıtından ayırt edilemiyor; bu yüzden yalnızca
    bilgi notu olarak taşınır, `gecerli` alanı gibi karar verici değildir.
    """
    url = TABAN_URL + "?ara=" + urllib.parse.quote(kelime)
    istek = urllib.request.Request(url, headers=BASLIKLAR)
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as yanit:
            veri = json.loads(yanit.read().decode("utf-8"))
    except urllib.error.URLError as hata:
        raise TdkHatasi(f"{kelime!r} sorgulanamadı: {hata}") from hata

    if isinstance(veri, dict) and "error" in veri:
        return {"gecerli": False, "ilk_anlam_yonlendirme": None}

    yonlendirme = None
    if veri and veri[0].get("anlamlarListe"):
        ilk_anlam = veri[0]["anlamlarListe"][0].get("anlam", "")
        if ilk_anlam.startswith("►"):
            yonlendirme = ilk_anlam.lstrip("► ").strip()

    return {"gecerli": True, "ilk_anlam_yonlendirme": yonlendirme}
