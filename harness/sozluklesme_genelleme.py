"""DENEYSEL: Qwen3.6:27B'nin Q3-1997'de ("korkulu" = kork+u+lu) gösterdiği
"motorun çıplak kök dediği kelimenin aslında gizli fiil kökenli olduğunu
kendi bilgisinden fark etme" davranışı GERÇEKTEN mi genelleşiyor, yoksa
tanınmış/ezberlenmiş TEK bir soruyu mu yansıtıyor?

Bağlam: docs/decisions.md §5 "sözlükleşme duvarı" — motorun sözlüğü bazı kökleri
çıplak (türetimsiz) gösterir ama gerçek/ÖSYM'nin kabul ettiği köken
farklıdır. Belgelenen iki somut örnek kümesi kullanılıyor:

1. 1999/5 "Çayönü kazısında" parçası — kazı/buluntu/aşama gizli FİİL
   kökenli (kaz+ı, bul+un+tu, aş+ma) ama sözlükte çıplak İSİM; yalnızca
   `av` gerçek basit isim kökü. Motorun isim_coz.py'de tam bu yüzden
   ayırt edemediği, belgelenmiş bir çift.
2. Sözcükte Yapı sayfa 57-58 sekiz kelime — ekin/çeviri/ışık/yatak/
   yorgun/sevinç hepsi gizli FİİL kökenli (ek+in, çevir+i, ış+ık, yat+ak,
   yor+gun, sev+inç) ama sözlükte çıplak duruyor.

Kontrol grubu: av, masa, kalem — gerçekten basit, fiilden türememiş isim
kökleri (motor da doğru söylüyor, model de "İSİM" demeli).

Model her kelime için tek başına (bağlamsız, önceki sorulardan bağımsız)
soruluyor — bir önceki sorunun cevabından ipucu sızmasın diye. Sonuç
hiçbir altın kümeye/motora geri beslenmez, yalnızca ölçülür.

Çalıştırma:  .venv/bin/python -m harness.sozluklesme_genelleme
"""

from __future__ import annotations

import re
import sys

from harness import model
from harness.mebi_agent_coz import ARACLAR, _arac_calistir

_CEVAP_DUZENI = re.compile(r"NİHAİ CEVAP\s*[:：]\s*(FİİL|İSİM)", re.IGNORECASE)

SISTEM_ISTEMI = """Sen bir Türkçe tarihsel/etimolojik köken uzmanısın. SADECE \
TÜRKÇE yaz. Sana bir kelime verilecek. Görevin: bu kelimenin GERÇEK, \
TARİHSEL/ETİMOLOJİK kökünün bir FİİL mi yoksa bağımsız bir İSİM mi \
olduğunu belirlemek — motorun (kelimeyi_coz) o kelimeyi çıplak/türetimsiz \
bir kök olarak gösterip göstermediğine BAKMAKSIZIN. Sözlükte çıplak kök \
olarak duran birçok kelime aslında tarihsel olarak bir fiilden türemiştir \
(sözlükleşmiş türetim) — bunu senin bilgin belirlemeli, motor değil. \
İstersen kelimeyi_coz aracını çağırıp motorun ne dediğini görebilirsin \
ama nihai kararı kendi dilbilgisi bilgine göre ver.

Son cevabını YALNIZCA şu formatta ver:
NİHAİ CEVAP: FİİL
veya
NİHAİ CEVAP: İSİM"""

#: (kelime, beklenen, kaynak) — kaynak docs/decisions.md §5'teki belgelenmiş örnek.
KELIMELER: list[tuple[str, str, str]] = [
    ("kazı", "FİİL", "1999/5 Çayönü kazısında — kaz+ı"),
    ("buluntu", "FİİL", "1999/5 Çayönü kazısında — bul+un+tu"),
    ("aşama", "FİİL", "1999/5 Çayönü kazısında — aş+ma"),
    ("av", "İSİM", "1999/5 Çayönü kazısında — gerçek basit isim kökü (kontrol)"),
    ("ekin", "FİİL", "Sözcükte Yapı s.57-58 — ek+in"),
    ("çeviri", "FİİL", "Sözcükte Yapı s.57-58 — çevir+i"),
    ("ışık", "FİİL", "Sözcükte Yapı s.57-58 — ış+ık"),
    ("yatak", "FİİL", "Sözcükte Yapı s.57-58 — yat+ak"),
    ("yorgun", "FİİL", "Sözcükte Yapı s.57-58 — yor+gun"),
    ("sevinç", "FİİL", "Sözcükte Yapı s.57-58 — sev+inç"),
    ("masa", "İSİM", "kontrol — gerçek basit isim kökü"),
    ("kalem", "İSİM", "kontrol — gerçek basit isim kökü (alıntı ama türetimsiz)"),
]

_AZAMI_BELIRTEC = int(__import__("os").environ.get("DIAGNOSTIK_AZAMI_BELIRTEC", "12000"))
_AZAMI_TUR = int(__import__("os").environ.get("DIAGNOSTIK_AZAMI_TUR", "8"))
_SICAKLIK = float(__import__("os").environ.get("DIAGNOSTIK_SICAKLIK", "0.0"))
_REASONING_EFFORT = __import__("os").environ.get("DIAGNOSTIK_REASONING_EFFORT")
_FREQ_PENALTY = __import__("os").environ.get("DIAGNOSTIK_FREQ_PENALTY")

_EKSTRA: dict = {}
if _REASONING_EFFORT:
    _EKSTRA["reasoning_effort"] = _REASONING_EFFORT
if _FREQ_PENALTY:
    _EKSTRA["frequency_penalty"] = float(_FREQ_PENALTY)


def sor(kelime: str) -> tuple[str | None, list[str]]:
    istem = f"'{kelime}' kelimesinin gerçek/tarihsel kökü fiil midir isim midir?"
    for _ in range(3):
        yanit, _gecmis = model.arac_ile_sor(
            istem=istem,
            araclar=ARACLAR,
            arac_calistir=_arac_calistir,
            sistem=SISTEM_ISTEMI,
            sicaklik=_SICAKLIK,
            azami_belirtec=_AZAMI_BELIRTEC,
            azami_tur=_AZAMI_TUR,
            ekstra=_EKSTRA or None,
        )
        eslesme = _CEVAP_DUZENI.search(yanit)
        if eslesme:
            return eslesme.group(1).upper(), []
    return None, []


def main() -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    if not model.anahtar_var_mi():
        print(model.anahtar_yardimi(), file=sys.stderr)
        return 2

    print(f"Uç nokta: {__import__('os').environ.get('ZAI_BASE_URL', '(varsayılan)')}")
    print(f"Model: {__import__('os').environ.get('ZAI_MODEL', '(varsayılan)')}\n")

    dogru = yanlis = bos = 0
    fiil_dogru = fiil_toplam = 0
    kontrol_dogru = kontrol_toplam = 0

    print(f"{'kelime':<12} {'bek':<5} {'bul':<5} {'kaynak'}")
    print("─" * 70)

    for kelime, beklenen, kaynak in KELIMELER:
        print(f"{kelime:<12} ... soruluyor", end="\r")
        bulunan, _ = sor(kelime)

        if beklenen == "FİİL":
            fiil_toplam += 1
        else:
            kontrol_toplam += 1

        if bulunan is None:
            bos += 1
            durum = "∅"
        elif bulunan == beklenen:
            dogru += 1
            durum = "✓"
            if beklenen == "FİİL":
                fiil_dogru += 1
            else:
                kontrol_dogru += 1
        else:
            yanlis += 1
            durum = "✗"

        print(f"{kelime:<12} {beklenen:<5} {bulunan or '?':<5} {durum} {kaynak}")

    print("─" * 70)
    toplam = len(KELIMELER)
    print(f"  toplam doğru {dogru}/{toplam}  ·  yanlış {yanlis}  ·  format hatası {bos}")
    print(f"  gizli-fiil-kökenli grup (asıl test): {fiil_dogru}/{fiil_toplam} doğru")
    print(f"  kontrol grubu (basit isim kökü): {kontrol_dogru}/{kontrol_toplam} doğru")
    print()
    if fiil_dogru == fiil_toplam and fiil_toplam > 0:
        print("  → Gizli-fiil-kökenli grupta %100: genelleme güçlü görünüyor")
        print("    (ama tek oturumluk küçük örneklem, kesin kanıt değil).")
    elif fiil_dogru == 0:
        print("  → Gizli-fiil-kökenli grupta hiç isabet yok: 'korku' büyük")
        print("    olasılıkla EZBERdi, genel bir yetenek değil.")
    else:
        print("  → Karışık sonuç: bazı kelimelerde genelliyor, bazılarında")
        print("    değil — tutarsız, güvenilir bir kural olarak kullanılamaz")
        print("    (tam olarak motorun kendi sözlükleşme tutarsızlığı gibi).")

    print("\n  NOT: bu sonuç tanı amaçlıdır, hiçbir altın kümeye/motora geri beslenmez.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
