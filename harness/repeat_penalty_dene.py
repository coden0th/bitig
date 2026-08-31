"""DENEYSEL: Ollama'nın OpenAI-uyumlu ucundan (frequency_penalty) değil,
NATIVE /api/chat ucundan gerçek llama.cpp `repeat_penalty`/`repeat_last_n`
parametrelerini deneyip qwen3.6:27b'nin token-bütçesi tükenene kadar süren
tekrarlı "Wait, maybe X? No..." döngüsünü daha iyi kırıp kırmadığını ölçer.

Bağlam: `harness/qwen_ham_diagnostik.py` + `DIAGNOSTIK_FREQ_PENALTY` ile
OpenAI-uyumlu `frequency_penalty` denendi (bkz. sohbet geçmişi) — kısmen
işe yaradı (bazı format hataları düzeldi) ama 22 sorunun 4'ünde hâlâ aynı
tıkanma vardı. `frequency_penalty` Ollama'nın OpenAI-uyumluluk katmanında
ayrı bir sampling parametresi; llama.cpp'nin klasik "aynı token'ı art arda
üretmeyi cezalandır" mekanizması (`repeat_penalty`/`repeat_last_n`) native
`/api/chat` ucundan `options` sözlüğüyle geçilir, OpenAI-uyumlu uçtan hiç
erişilemez. Bu betik SADECE bunu test eder.

`harness/model.py`'ye dokunmuyor (o z.ai/OpenAI-uyumlu şema için) — ayrı,
minimal bir istemci burada, çünkü native Ollama şeması farklı.

Çalıştırma:  python3 -m harness.repeat_penalty_dene
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

from harness.mebi_agent_coz import ARACLAR, SORULAR, _arac_calistir

_CEVAP_DUZENI = re.compile(r"NİHAİ CEVAP\s*[:：]\s*([A-EIVX]+)", re.IGNORECASE)

_BASE_URL = os.environ.get("OLLAMA_NATIVE_URL", "http://127.0.0.1:11434")
_MODEL = os.environ.get("ZAI_MODEL", "qwen3.6:27b")
_REPEAT_PENALTY = float(os.environ.get("REPEAT_PENALTY", "1.3"))
_REPEAT_LAST_N = int(os.environ.get("REPEAT_LAST_N", "256"))
_NUM_PREDICT = int(os.environ.get("NUM_PREDICT", "12000"))
_AZAMI_TUR = int(os.environ.get("AZAMI_TUR", "8"))
_ZAMAN_ASIMI = int(os.environ.get("ZAMAN_ASIMI", "900"))

SISTEM_ISTEMI = """Sen bir TYT Türkçe sınav sorusu çözücüsüsün. SADECE TÜRKÇE \
yaz — hiçbir koşulda başka bir dilde (İngilizce, Çince dahil) tek kelime bile \
üretme. Sana tam bir soru (gerekirse paragraf/dizeler + soru kökü + \
seçenekler) verilecek.

Elindeki iki araç:
1. kelimeyi_coz: bir kelimenin GERÇEK morfolojik ayrıştırmasını verir (motor \
çıktısı, kesindir — kendi tahminini bunun üstüne koyma, motor ne diyorsa \
odur; birden fazla okuma dönebilir, hepsini dikkate al).
2. konu_getir: MEB'in resmî konu özeti kitabından bir konunun kural/tanım/\
örnek metnini verir.

Kurallar:
- Sorudaki altı çizili/numaralanmış her kelimeyi kelimeyi_coz ile kontrol et, tahmin etme.
- Her kelimeyi YALNIZCA BİR KEZ kontrol et ve analiz et — aynı kelimeyi ya da \
seçeneği tekrar tekrar sorgulama/yeniden değerlendirme, bir kere karar verip devam et.
- Kuraldan emin değilsen konu_getir ile ilgili konuyu oku.
- Araç çağırma bütçen sınırlı (en fazla ~12 çağrı).
- Sorunun cevap biçimine dikkat et: A) B) C) D) E) seçenekli sorularda harf, \
yalnızca (I) (II) (III) numaralı sorularda roma rakamı ver.
- Son cevabını YALNIZCA şu formatta ver:
NİHAİ CEVAP: <A/B/C/D/E ya da I/II/III/IV/V>

Önemli: Her seçeneği yalnızca bir kez değerlendir, tekrarlama. Kararsız kalsan \
bile elindeki bilgiyle en olası cevabı seç ve yaz — sonsuza kadar aynı \
seçenekleri yeniden gözden geçirme."""


_THINK = os.environ.get("THINK")  # "false"/"true"/"low"/"medium"/"high" ya da boş=varsayılan


def _native_cagri(mesajlar: list[dict]) -> dict:
    govde = {
        "model": _MODEL,
        "messages": mesajlar,
        "tools": ARACLAR,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "repeat_penalty": _REPEAT_PENALTY,
            "repeat_last_n": _REPEAT_LAST_N,
            "num_predict": _NUM_PREDICT,
        },
    }
    if _THINK is not None:
        govde["think"] = {"true": True, "false": False}.get(_THINK, _THINK)
    istek = urllib.request.Request(
        f"{_BASE_URL}/api/chat",
        data=json.dumps(govde).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(istek, timeout=_ZAMAN_ASIMI) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def coz(soru: dict) -> tuple[str | None, list[dict]]:
    mesajlar = [
        {"role": "system", "content": SISTEM_ISTEMI},
        {"role": "user", "content": soru["metin"]},
    ]
    for _tur in range(_AZAMI_TUR):
        yanit = _native_cagri(mesajlar)
        mesaj = yanit["message"]
        mesajlar.append(mesaj)

        tool_calls = mesaj.get("tool_calls") or []
        if not tool_calls:
            icerik = (mesaj.get("content") or "") + "\n" + (mesaj.get("thinking") or "")
            eslesme = _CEVAP_DUZENI.search(icerik)
            if eslesme:
                return eslesme.group(1).upper(), mesajlar
            return None, mesajlar

        for cagri in tool_calls:
            ad = cagri["function"]["name"]
            args = cagri["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            sonuc = _arac_calistir(ad, args)
            mesajlar.append({"role": "tool", "content": sonuc})

    return None, mesajlar


def main() -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    hedef_kimlikler = os.environ.get("HEDEF_SORULAR", "").split(",")
    hedef_kimlikler = [k.strip() for k in hedef_kimlikler if k.strip()]
    if hedef_kimlikler:
        sorular = [s for s in SORULAR if s["kimlik"] in hedef_kimlikler]
    else:
        sorular = SORULAR

    print(f"Model: {_MODEL}  ·  repeat_penalty={_REPEAT_PENALTY}  repeat_last_n={_REPEAT_LAST_N}  num_predict={_NUM_PREDICT}\n")
    print(f"{len(sorular)} soru\n")
    print(f"{'kimlik':<12} {'bek':>3} {'bul':<4} durum")
    print("─" * 50)

    dogru = yanlis = bos = 0
    for soru in sorular:
        print(f"{soru['kimlik']:<12} ... çözülüyor", end="\r")
        try:
            bulunan, _mesajlar = coz(soru)
        except Exception as hata:  # noqa: BLE001 - tanı betiği, geniş yakalama kasıtlı
            print(f"{soru['kimlik']:<12} HATA: {hata}")
            continue

        if bulunan is None:
            bos += 1
            durum = "∅ FORMAT"
            if os.environ.get("DUMP_BASARISIZ"):
                with open(f"/root/basarisiz_{soru['kimlik']}.json", "w", encoding="utf-8") as f:
                    json.dump(_mesajlar, f, ensure_ascii=False, indent=2)
        elif bulunan == soru["cevap"]:
            dogru += 1
            durum = "✓ DOGRU"
        else:
            yanlis += 1
            durum = "✗ YANLIS"

        print(f"{soru['kimlik']:<12} {soru['cevap']:>3} {bulunan or '?':<4} {durum}")

    print("─" * 50)
    print(f"  doğru {dogru}  ·  yanlış {yanlis}  ·  format hatası {bos}  (toplam {len(sorular)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
