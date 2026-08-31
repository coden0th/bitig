"""MEBİ TYT Konu Özetleri - Türkçe PDF'ini konu bazında düz metne çevirir.

Kaynak: ogm-large-cdn.eba.gov.tr/ogm-materyal/mebi-konu-ozetleri/tyt-turkce/tyt-turkce.pdf
(2026, MEB Ortaöğretim Genel Müdürlüğü / MEBİ, ISBN 978-975-11-8474-0, 128 sayfa).

Metin çıkarımı elle (görsel okuma + transkripsiyon) değil, `pypdf` ile PROGRAMATİK
yapılır — bu oturumda paragraf/soru sırası iki kez elle yanlış okunduğu için (bkz.
docs/decisions.md §5, Sözcükte Yapı bölümü) manuel transkripsiyona artık güvenilmiyor.

Konu sınırları PDF'in kendi İçindekiler'inden (basılı sayfa numaraları) türetilir.
Basılı sayfa → PDF fiziksel sayfası dönüşümü sabit bir kaymayla yapılır (+2) — bu,
birden çok sayfa elle karşılaştırılarak doğrulandı (örn. basılı "36" = PDF sayfa 38).

Çalıştırma:  .venv/bin/python -m harness.mebi_pdf_ayikla
Çıktı:       veri/mebi_konu_ozetleri.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pypdf import PdfReader

PDF_YOLU = Path(
    "/tmp/claude-1000/-home-emir-Belgeler-Yazilim-BitigAI/"
    "6194d298-ca12-44ae-aeb9-7bca05e10b6b/scratchpad/tyt-turkce-mebi.pdf"
)
CIKTI_YOLU = Path(__file__).resolve().parent.parent / "veri" / "mebi_konu_ozetleri.json"

BASILI_PDF_KAYMASI = 2  # PDF fiziksel sayfası = basılı sayfa numarası + 2

# (konu adı, basılı başlangıç sayfası) — İçindekiler'den (s.8) birebir.
ICINDEKILER: list[tuple[str, int]] = [
    ("Sözcükte Anlam 1", 9),
    ("Sözcükte Anlam 2", 10),
    ("Sözcükte Anlam 3", 12),
    ("Sözcükte Anlam 4", 14),
    ("Cümlede Anlam 1", 15),
    ("Cümlede Anlam 2", 17),
    ("Cümlede Anlam 3", 19),
    ("Paragrafta Anlam 1", 22),
    ("Paragrafta Anlam 2", 26),
    ("Paragrafta Anlam 3", 31),
    ("Paragrafın Yapısı", 33),
    ("Ses Bilgisi 1", 36),
    ("Ses Bilgisi 2", 38),
    ("Yazım Kuralları 1", 39),
    ("Yazım Kuralları 2", 46),
    ("Yazım Kuralları 3", 50),
    ("Noktalama İşaretleri 1", 55),
    ("Noktalama İşaretleri 2", 59),
    ("Noktalama İşaretleri 3", 63),
    ("Biçim Bilgisi 1", 67),
    ("Biçim Bilgisi 2 (Sözcüğün Yapısı)", 73),
    ("İsim", 76),
    ("Sıfat", 79),
    ("Zamir", 83),
    ("İsim ve Sıfat Tamlamaları", 88),
    ("Zarf", 91),
    ("Edat, Bağlaç, Ünlem", 95),
    ("Fiilde Kip", 99),
    ("Ek-Fiil", 101),
    ("Fiilde Yapı", 103),
    ("Fiilimsiler", 105),
    ("Fiilde Çatı", 108),
    ("Cümlenin Ögeleri", 112),
    ("Cümle Türleri", 116),
    ("Anlatım Bozuklukları 1", 119),
    ("Anlatım Bozuklukları 2", 122),
]


def _pdf_sayfa(basili: int) -> int:
    return basili + BASILI_PDF_KAYMASI


def main() -> int:
    if not PDF_YOLU.exists():
        print(f"PDF bulunamadı: {PDF_YOLU}", file=sys.stderr)
        return 2

    okuyucu = PdfReader(str(PDF_YOLU))
    toplam = len(okuyucu.pages)
    print(f"{toplam} sayfa okunuyor...")

    tum_sayfalar = [okuyucu.pages[i].extract_text() or "" for i in range(toplam)]

    konular: dict[str, dict] = {}
    for i, (ad, basili_bas) in enumerate(ICINDEKILER):
        pdf_bas = _pdf_sayfa(basili_bas)
        if i + 1 < len(ICINDEKILER):
            pdf_son = _pdf_sayfa(ICINDEKILER[i + 1][1]) - 1
        else:
            pdf_son = toplam  # son konu, kitabın sonuna kadar

        parcalar = tum_sayfalar[pdf_bas - 1 : pdf_son]
        metin = "\n\n".join(p.strip() for p in parcalar if p.strip())
        konular[ad] = {
            "basili_sayfa_araligi": [basili_bas, basili_bas + (pdf_son - pdf_bas)],
            "metin": metin,
        }

    cikti = {
        "kaynak": (
            "MEBİ TYT Konu Özetleri - Türkçe, 2026, MEB Ortaöğretim Genel "
            "Müdürlüğü/MEBİ, ISBN 978-975-11-8474-0"
        ),
        "kaynak_url": (
            "https://ogm-large-cdn.eba.gov.tr/ogm-materyal/mebi-konu-ozetleri/"
            "tyt-turkce/tyt-turkce.pdf"
        ),
        "konular": konular,
    }

    CIKTI_YOLU.parent.mkdir(parents=True, exist_ok=True)
    CIKTI_YOLU.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(konular)} konu yazıldı: {CIKTI_YOLU}")
    for ad, veri in konular.items():
        print(f"  {ad:<38} {len(veri['metin']):>6} karakter")

    return 0


if __name__ == "__main__":
    sys.exit(main())
