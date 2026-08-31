"""BMM v2 için yerel deneme sitesi — tüm motorları tarayıcıdan denemek için.

Dış bağımlılık yok (yalnızca stdlib `http.server`). Üretim bağımlılığının
sıfır olması ilkesiyle uyumlu (CLAUDE.md §1) — bu bir demo/geliştirme aracı,
`harness/` ile aynı katmanda durur, `bitig/` içine girmez.

Çalıştırma:

    .venv/bin/python web_server.py
    # sonra tarayıcıda http://localhost:8765

`/api/baglam` DIŞINDAKİ her uç nokta ağsızdır. `/api/baglam` GLM'e (z.ai) gider,
ücretlidir ve `~/.config/bitigai/zai.key` gerektirir — arayüzde ayrıca
işaretlenmiştir, varsayılan olarak tetiklenmez.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bitig.cozumleyici import cozumle, kelimeyi_cozumle
from bitig.osym import gorus as osym_gorus

import anlatim
import atasozu
import hece
import isim_soylu
import noktalama
import yazim

PORT = int(os.environ.get("PORT", "8765"))
HOST = os.environ.get("HOST", "127.0.0.1")
STATIK_DIZIN = Path(__file__).resolve().parent / "web"


def _motor(gövde: dict) -> dict:
    """Motoru çalıştırır, sonra ÖSYM politika katmanını (bitig/osym.py) üstüne
    uygular — motoru DEĞİŞTİRMEZ, yalnızca ÖSYM'nin farklı düşündüğü
    kelimelere `osym_gorus` alanı ekler (bkz. `Gorus.ayrisiyor_mu`).
    """
    cumle = gövde.get("cumle", "")
    sonuc = cozumle(cumle)
    veri = sonuc.sozluge()
    for k_govde, k in zip(veri["kelimeler"], sonuc.kelimeler):
        g = osym_gorus(k)
        if g.ayrisiyor_mu:
            k_govde["osym_gorus"] = g.sozluge()
    return veri


def _anlatim(gövde: dict) -> dict:
    cumle = gövde.get("cumle", "")
    bulgular = anlatim.tara(cumle)
    return {"bulgular": [{"tur": b.tur, "kanit": list(b.kanit)} for b in bulgular]}


def _noktalama(gövde: dict) -> dict:
    metin = gövde.get("metin", "")
    bulgular = noktalama.tara(metin)
    return {"bulgular": [{"tur": b.tur, "kelime": b.kelime} for b in bulgular]}


def _yazim(gövde: dict) -> dict:
    kelime = gövde.get("kelime", "").strip()
    if not kelime:
        return {"denetim": [], "tdk": None}
    denetim = yazim.denetle(kelime)
    tdk = yazim.tdk_gecerli_mi(kelime)
    # doğrudan çözülüyor mu — kullanıcı hem doğru hem yanlış yazımı deneyebilsin
    dogrudan = kelimeyi_cozumle(kelime)
    return {
        "cozulebiliyor_mu": not dogrudan.cozumlenemedi,
        "denetim": [
            {"aday": d.aday, "duzeltme": d.duzeltme, "kural_id": d.kural_id} for d in denetim
        ],
        "tdk": (
            {"gecerli": tdk.gecerli, "yonlendirme": tdk.yonlendirme} if tdk is not None else None
        ),
    }


def _atasozu(gövde: dict) -> dict:
    sorgu = gövde.get("sorgu", "").strip()
    mod = gövde.get("mod", "tam")
    if not sorgu:
        return {"kayitlar": []}
    kayitlar = atasozu.bul(sorgu) if mod == "tam" else atasozu.ara(sorgu)
    return {
        "kayitlar": [{"soz": k.soz, "anlam": k.anlam, "tur": k.tur} for k in kayitlar[:50]],
        "toplam": len(kayitlar),
    }


def _isim_soylu(gövde: dict) -> dict:
    cumle = gövde.get("cumle", "")
    sonuclar = isim_soylu.cumleyi_coz(cumle)
    return {
        "kelimeler": [
            (
                {
                    "kelime": s.kelime,
                    "tur": s.tur,
                    "alt_kategori": s.alt_kategori,
                    "gerekce": s.gerekce,
                }
                if s is not None
                else None
            )
            for s in sonuclar
        ]
    }


def _hece(gövde: dict) -> dict:
    cumle = gövde.get("cumle", "")
    sonuclar = []
    for kelime, heceler in hece.cumleyi_hecele(cumle):
        buyuk = hece.buyuk_unlu_uyumu(kelime)
        kucuk = hece.kucuk_unlu_uyumu(kelime)
        sonuclar.append(
            {
                "kelime": kelime,
                "heceler": list(heceler),
                "buyuk_uyum": {
                    "uyuyor": buyuk.uyuyor,
                    "kanit": list(buyuk.kanit) if buyuk.kanit else None,
                },
                "kucuk_uyum": {
                    "uyuyor": kucuk.uyuyor,
                    "kanit": list(kucuk.kanit) if kucuk.kanit else None,
                },
            }
        )
    return {"kelimeler": sonuclar}


def _baglam(gövde: dict) -> dict:
    """Bilerek devre dışı — public demo hiçbir model çağrısı yapmaz.

    `baglam` modülü burada BİLEREK içe aktarılmıyor: bu uç noktaya istek
    gelirse motora/ağa hiç dokunmadan sabit bir ret mesajı döner. Yerelde
    denemek için: `python -m harness.baglam_coz` (bkz. web/index.html'deki
    "Bağlamsal Seçici" sekmesi — orada nasıl çalıştırılacağı ve donmuş bir
    örnek anlatılıyor, canlı çağrı yapılmıyor).
    """
    return {
        "devre_disi": True,
        "mesaj": "Bu uç public demoda devre dışı — model çağrısı gerektiriyor.",
    }


_ROTALAR = {
    "/api/motor": _motor,
    "/api/anlatim": _anlatim,
    "/api/noktalama": _noktalama,
    "/api/yazim": _yazim,
    "/api/atasozu": _atasozu,
    "/api/isim_soylu": _isim_soylu,
    "/api/hece": _hece,
    "/api/baglam": _baglam,
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - stdlib imzası
        print(f"  {self.address_string()} - {format % args}")

    def _json_yaz(self, veri: dict, durum: int = 200) -> None:
        gövde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        self.send_response(durum)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(gövde)))
        self.end_headers()
        self.wfile.write(gövde)

    def do_GET(self) -> None:  # noqa: N802 - stdlib imzası
        yol = "/index.html" if self.path == "/" else self.path
        dosya = STATIK_DIZIN / yol.lstrip("/")
        if dosya.is_file() and STATIK_DIZIN in dosya.resolve().parents:
            icerik = dosya.read_bytes()
            tur = "text/html" if dosya.suffix == ".html" else "text/plain"
            if dosya.suffix == ".css":
                tur = "text/css"
            if dosya.suffix == ".js":
                tur = "application/javascript"
            self.send_response(200)
            self.send_header("Content-Type", f"{tur}; charset=utf-8")
            self.send_header("Content-Length", str(len(icerik)))
            self.end_headers()
            self.wfile.write(icerik)
            return
        self._json_yaz({"hata": "bulunamadı"}, 404)

    def do_POST(self) -> None:  # noqa: N802 - stdlib imzası
        işleyici = _ROTALAR.get(self.path)
        if işleyici is None:
            self._json_yaz({"hata": "bilinmeyen uç nokta"}, 404)
            return
        uzunluk = int(self.headers.get("Content-Length", 0))
        ham = self.rfile.read(uzunluk) if uzunluk else b"{}"
        try:
            gövde = json.loads(ham) if ham else {}
        except json.JSONDecodeError:
            self._json_yaz({"hata": "geçersiz JSON"}, 400)
            return
        try:
            sonuc = işleyici(gövde)
        except Exception as e:
            self._json_yaz({"hata": f"{type(e).__name__}: {e}"}, 500)
            return
        self._json_yaz(sonuc)


def main() -> None:
    sunucu = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"BMM v2 deneme sitesi: http://{HOST}:{PORT}")
    print("Durdurmak için Ctrl+C")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sunucu.server_close()


if __name__ == "__main__":
    main()
