"""DENEYSEL: `mebi_agent_coz.py`'nin aynı aracı (motor + MEBİ RAG) ile, hiçbir
gerçek sınavdan ALINMAMIŞ, bu oturumda özgün yazılmış Ses Bilgisi sorularını
çözme testi.

Amaç: ezber-karşıtı kontrol. `mebi_agent_coz_osym.py`'deki sorular gerçek,
yayımlanmış ÖSYM sorularıydı — GLM'in eğitim verisinde geçmiş olabilirler.
Burada aşağıdaki her cümle özgün yazıldı, hiçbir kaynaktan kopyalanmadı; hedef
kelime motora TEK TEK sorularak (`kelimeyi_cozumle`, olay kümesi) doğrulandı —
bkz. her sorunun altındaki not. Model bu cümleleri daha önce hiç görmüş olamaz;
yüksek doğruluk çıkarsa bu, ezber değil gerçek (araç-destekli) muhakeme
olduğuna dair çok daha güçlü bir kanıttır.

Aynı ilkeler geçerli: sonuç hiçbir yere geri beslenmez, yalnızca rapor edilir.

Çalıştırma:  .venv/bin/python -m harness.mebi_agent_coz_ozgun
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness import model
from harness.mebi_agent_coz import coz

# Her soru bu oturumda özgün yazıldı. Hedef kelimeler `kelimeyi_cozumle` ile
# tek tek doğrulandı (bkz. sohbet kaydı) — kural_id parantez içinde belirtilmiş.
SORULAR: list[dict] = [
    {
        "kimlik": "OZGUN-01", "cevap": "A",  # köpeğin: SES.YUM.01
        "metin": """Aşağıdaki cümlelerin hangisinde altı çizili sözcükte ünsüz yumuşaması vardır?
A) Sokaktaki köpeğin ürkek bakışları herkesi üzüyordu.
B) Bahçedeki güllerin kokusu her yeri sarmıştı.
C) Kitaplarını dikkatle raftan indirdi.
D) Sabahları erkenden kalkardı.
E) Masanın üstündeki kalemi aldı.""",
    },
    {
        "kimlik": "OZGUN-02", "cevap": "B",  # kaçtı: SES.BEN.01
        "metin": """Aşağıdaki cümlelerin hangisinde altı çizili sözcükte ünsüz benzeşmesi (sertleşmesi) vardır?
A) Öğretmen soruyu tahtaya yazdı.
B) Çocuk top peşinde koşup kaçtı.
C) Kardeşim bana kitabı verdi.
D) Öğrenci kitabı dikkatle okudu.
E) Elindeki anahtarı masaya koydu.""",
    },
    {
        "kimlik": "OZGUN-03", "cevap": "A",  # öğrencinin: SES.KAY.01
        "metin": """Aşağıdaki cümlelerin hangisinde altı çizili sözcükte kaynaştırma ünsüzü vardır?
A) Öğrencinin defteri masada duruyordu.
B) Odada garip bir sessizlik vardı.
C) Kalemin ucu kırılmıştı.
D) Duvarı yeni boyamışlardı.
E) Pencerede bir kuş öterdi.""",
    },
    {
        "kimlik": "OZGUN-04", "cevap": "A",  # yaşıyor: SES.DAR.01
        "metin": """Aşağıdaki cümlelerin hangisinde altı çizili sözcükte ünlü daralması vardır?
A) Uzun zamandır bu şehirde yaşıyor.
B) Her sabah parkta koşuyor.
C) Yeni fikirler üzerine çalışıyor.
D) Müzikle ilgili bir şeyler seviyor.
E) Bu konuda derinden düşünüyor.""",
    },
    {
        "kimlik": "OZGUN-05", "cevap": "A",  # hissi: SES.UT.01
        "metin": """Aşağıdaki cümlelerin hangisinde altı çizili sözcükte ünsüz türemesi vardır?
A) Bu olay içindeki hissi altüst etmişti.
B) Masanın üstündeki kalemi aldı.
C) Duvardaki resmi dikkatle inceledi.
D) Elindeki anahtarı kaybetmişti.
E) Bahçedeki kolu kırık sandalyeyi tamir etti.""",
    },
    {
        "kimlik": "OZGUN-06", "cevap": "A",  # burnu: SES.UD.01
        "metin": """Aşağıdaki cümlelerin hangisinde altı çizili sözcükte ünlü düşmesi vardır?
A) Soğuktan burnu kıpkırmızı olmuştu.
B) Masanın üstündeki kalemi aldı.
C) Elindeki anahtarı kaybetmişti.
D) Duvarı yeni boyamışlardı.
E) Kolu kırık sandalyeyi tamir etti.""",
    },
    {
        "kimlik": "OZGUN-07", "cevap": "E",  # yatağı(YUM) kaçtı(BEN) öğrencinin(KAY) burnu(UD) var; DAR yok
        "metin": """Öğrencinin defteri masada duruyordu. Çocuk top peşinde koşup kaçtı. Soğuktan burnu kıpkırmızı olmuştu. Çocuk erkenden yatağı topladı.
Bu parçada aşağıdaki ses olaylarından hangisi yoktur?
A) Ünsüz yumuşaması
B) Ünsüz benzeşmesi
C) Kaynaştırma
D) Ünlü düşmesi
E) Ünlü daralması""",
    },
    {
        "kimlik": "OZGUN-08", "cevap": "B",  # hissi(UT) yasıyor(DAR) yatağı(YUM) öğrencinin(KAY) var; BEN yok
        "metin": """Bu olay içindeki hissi derinden üzdü. Uzun zamandır bu şehirde yaşıyor. Çocuk erkenden yatağı topladı. Öğrencinin defteri masada duruyordu.
Bu parçada aşağıdaki ses olaylarından hangisi yoktur?
A) Kaynaştırma
B) Ünsüz benzeşmesi
C) Ünlü daralması
D) Ünsüz türemesi
E) Ünsüz yumuşaması""",
    },
]

ILERLEME_YOLU = Path(
    "/tmp/claude-1000/-home-emir-Belgeler-Yazilim-BitigAI/"
    "6194d298-ca12-44ae-aeb9-7bca05e10b6b/scratchpad/mebi_agent_ozgun_ilerleme.jsonl"
)


def main() -> int:
    if not model.anahtar_var_mi():
        print(model.anahtar_yardimi(), file=sys.stderr)
        return 2

    dogru = yanlis = bos = 0
    print(f"\n{len(SORULAR)} soru — ÖZGÜN (ezber-karşıtı kontrol), araçlı\n", flush=True)
    print(f"{'kimlik':<10} {'bek':>4} {'bul':<4} {'arac':>4} durum", flush=True)
    print("─" * 40, flush=True)

    ILERLEME_YOLU.parent.mkdir(parents=True, exist_ok=True)
    with ILERLEME_YOLU.open("w", encoding="utf-8") as ilerleme:
        for soru in SORULAR:
            try:
                bulunan, gecmis = coz(soru)
            except model.ModelHatasi as hata:
                print(f"{soru['kimlik']:<10} HATA: {hata}", flush=True)
                ilerleme.write(json.dumps({"kimlik": soru["kimlik"], "hata": str(hata)}, ensure_ascii=False) + "\n")
                ilerleme.flush()
                continue

            arac_sayisi = sum(1 for m in gecmis if m.get("role") == "tool")
            if bulunan is None:
                bos += 1
                durum = "∅ FORMAT"
            elif bulunan == soru["cevap"].upper():
                dogru += 1
                durum = "✓ DOGRU"
            else:
                yanlis += 1
                durum = "✗ YANLIS"

            print(f"{soru['kimlik']:<10} {soru['cevap']:>4} {bulunan or '?':<4} {arac_sayisi:>4}   {durum}", flush=True)

            arac_dokumu = [
                {"arac": c["function"]["name"], "girdi": c["function"]["arguments"]}
                for m in gecmis
                if m.get("role") == "assistant" and m.get("tool_calls")
                for c in m["tool_calls"]
            ]
            ilerleme.write(
                json.dumps(
                    {
                        "kimlik": soru["kimlik"],
                        "beklenen": soru["cevap"],
                        "bulunan": bulunan,
                        "durum": durum,
                        "arac_cagri_sayisi": arac_sayisi,
                        "arac_dokumu": arac_dokumu,
                        "son_mesaj": gecmis[-1].get("content", ""),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            ilerleme.flush()

    toplam = len(SORULAR)
    print("─" * 40, flush=True)
    print(f"  doğru {dogru}  ·  yanlış {yanlis}  ·  format hatası {bos}  (toplam {toplam})", flush=True)
    if toplam:
        print(f"\n  soru başarımı (ÖZGÜN, araçlı): {dogru / toplam * 100:.1f}%", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
