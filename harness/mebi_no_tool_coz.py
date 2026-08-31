"""DENEYSEL: `mebi_agent_coz_osym.py` ile AYNI 39 gerçek ÖSYM sorusunu, bu kez
HİÇBİR ARAÇ vermeden (ne motor ne RAG) GLM-5.2'ye doğrudan sorar.

Amaç: ezber testi. Bu sorular gerçek, herkese açık geçmiş sınav soruları —
GLM'in eğitim verisinde (forum/PDF bankası/video çözüm olarak) geçmiş olması
olası. Araçsızken de yüksek doğruluk çıkarsa, araçlı koşudaki başarı büyük
ölçüde ezberden geliyor demektir; araçsızken belirgin düşerse, araçlı koşunun
gerçek bir katkısı olduğuna işaret eder (kesin kanıt değil ama güçlü sinyal).

Aynı ilkeler geçerli: sonuç hiçbir yere geri beslenmez, yalnızca rapor edilir.

Çalıştırma:  .venv/bin/python -m harness.mebi_no_tool_coz
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from harness import model
from harness.mebi_agent_coz_osym import SORULAR

_CEVAP_DUZENI = re.compile(r"NİHAİ CEVAP\s*[:：]\s*([A-EIVX]+)", re.IGNORECASE)

SISTEM_ISTEMI = """Sen bir TYT Türkçe sınav sorusu çözücüsüsün. Sana tam bir soru \
(gerekirse paragraf/dizeler + soru kökü + seçenekler) verilecek. Hiçbir araç yok — \
yalnızca kendi bilgine dayanarak cevapla.

Cevap biçimine dikkat et:
- Soru A) B) C) D) E) seçenekli ise cevabı bir HARF olarak ver.
- Soru yalnızca (I) (II) (III) (IV) (V) ile numaralanmış cümle/sözcük sunuyorsa ve \
ayrı bir A-E listesi yoksa, cevabı doğrudan o ROMA RAKAMI olarak ver.

Son cevabını YALNIZCA şu formatta, başka hiçbir şey eklemeden ver:
NİHAİ CEVAP: <A/B/C/D/E ya da I/II/III/IV/V>"""

ILERLEME_YOLU = Path(
    "/tmp/claude-1000/-home-emir-Belgeler-Yazilim-BitigAI/"
    "6194d298-ca12-44ae-aeb9-7bca05e10b6b/scratchpad/mebi_no_tool_ilerleme.jsonl"
)


def coz(soru: dict) -> str | None:
    for _ in range(3):
        yanit = model.sor(istem=soru["metin"], sistem=SISTEM_ISTEMI, sicaklik=0.0, azami_belirtec=20000)
        eslesme = _CEVAP_DUZENI.search(yanit)
        if eslesme:
            return eslesme.group(1).upper()
    return None


def main() -> int:
    if not model.anahtar_var_mi():
        print(model.anahtar_yardimi(), file=sys.stderr)
        return 2

    dogru = yanlis = bos = 0
    print(f"\n{len(SORULAR)} soru — ARAÇSIZ (ezber testi)\n", flush=True)
    print(f"{'kimlik':<10} {'bek':>4} {'bul':<4} durum", flush=True)
    print("─" * 36, flush=True)

    ILERLEME_YOLU.parent.mkdir(parents=True, exist_ok=True)
    with ILERLEME_YOLU.open("w", encoding="utf-8") as ilerleme:
        for soru in SORULAR:
            try:
                bulunan = coz(soru)
            except model.ModelHatasi as hata:
                print(f"{soru['kimlik']:<10} HATA: {hata}", flush=True)
                ilerleme.write(json.dumps({"kimlik": soru["kimlik"], "hata": str(hata)}, ensure_ascii=False) + "\n")
                ilerleme.flush()
                continue

            if bulunan is None:
                bos += 1
                durum = "∅ FORMAT"
            elif bulunan == soru["cevap"].upper():
                dogru += 1
                durum = "✓ DOGRU"
            else:
                yanlis += 1
                durum = "✗ YANLIS"

            print(f"{soru['kimlik']:<10} {soru['cevap']:>4} {bulunan or '?':<4} {durum}", flush=True)
            ilerleme.write(
                json.dumps(
                    {"kimlik": soru["kimlik"], "beklenen": soru["cevap"], "bulunan": bulunan, "durum": durum},
                    ensure_ascii=False,
                )
                + "\n"
            )
            ilerleme.flush()

    toplam = len(SORULAR)
    print("─" * 36, flush=True)
    print(f"  doğru {dogru}  ·  yanlış {yanlis}  ·  format hatası {bos}  (toplam {toplam})", flush=True)
    if toplam:
        print(f"\n  soru başarımı (ARAÇSIZ): {dogru / toplam * 100:.1f}%", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
