"""DENEYSEL: `mebi_no_tool_coz.py`'nin aynı araçsız yöntemi, `mebi_agent_coz_ozgun.py`'nin
ÖZGÜN (hiçbir sınavdan alınmamış) 8 sorusu üzerinde.

4 hücreli karşılaştırmanın son parçası:
  gerçek soru   + araçlı   → mebi_agent_coz_osym.py
  gerçek soru   + araçsız  → mebi_no_tool_coz.py
  özgün soru    + araçlı   → mebi_agent_coz_ozgun.py
  özgün soru    + araçsız  → BU DOSYA

Çalıştırma:  .venv/bin/python -m harness.mebi_no_tool_coz_ozgun
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness import model
from harness.mebi_agent_coz_ozgun import SORULAR
from harness.mebi_no_tool_coz import SISTEM_ISTEMI, coz

ILERLEME_YOLU = Path(
    "/tmp/claude-1000/-home-emir-Belgeler-Yazilim-BitigAI/"
    "6194d298-ca12-44ae-aeb9-7bca05e10b6b/scratchpad/mebi_no_tool_ozgun_ilerleme.jsonl"
)


def main() -> int:
    if not model.anahtar_var_mi():
        print(model.anahtar_yardimi(), file=sys.stderr)
        return 2

    dogru = yanlis = bos = 0
    print(f"\n{len(SORULAR)} soru — ÖZGÜN, ARAÇSIZ\n", flush=True)
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
        print(f"\n  soru başarımı (ÖZGÜN, ARAÇSIZ): {dogru / toplam * 100:.1f}%", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
