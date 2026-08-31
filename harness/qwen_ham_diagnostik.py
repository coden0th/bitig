"""DENEYSEL: Ham (ince ayarsız) Qwen3-8B'nin araç çağırma sırasında Çince'ye
kayıp kaymadığını test eder.

Bağlam: kullanıcı kendi ince ayarında Qwen ailesinde araç çağırırken Çince
üretime kayma gördü (bkz. sohbet geçmişi, model-secim-dosyasi artifact'i §0).
Bu betik o belirtinin TEMEL MODELDE de var olup olmadığını ayırt eder —
varsa model/şablon sorunu, yoksa (muhtemel) ince ayar tarifi (veri hacmi/
öğrenme oranı) sorunu.

Motor+RAG mimarisi `harness/mebi_agent_coz.py` ile birebir aynı (aynı ARACLAR,
aynı yardımcı fonksiyonlar) — yalnızca sistem istemi bu tanının odağına göre
daraltıldı ve soru kümesi küçültüldü (bütçe: $5/akşam, hızlı sonuç öncelikli).

`harness/model.py` z.ai için yazılmıştı ama tamamen ortam değişkeni tabanlı —
bu yüzden hiç değiştirilmeden herhangi bir OpenAI-uyumlu uç noktaya (Ollama,
vLLM) yönlendirilebilir:

    export ZAI_BASE_URL='https://<POD-ID>-11434.proxy.runpod.net/v1'
    export ZAI_MODEL='qwen3:8b'
    export ZAI_API_KEY='ollama'   # Ollama anahtarı denetlemez, herhangi bir dizge olur

Çalıştırma:  .venv/bin/python -m harness.qwen_ham_diagnostik

Ağ gerektirir. Normal pytest'e dahil değildir. Sonuç hiçbir altın kümeye/
motora geri beslenmez — yalnızca rapor edilir (bkz. mebi_agent_coz.py'nin
aynı ilkesi).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from harness import model
from harness.mebi_agent_coz import ARACLAR, SORULAR, _arac_calistir

_CEVAP_DUZENI = re.compile(r"NİHAİ CEVAP\s*[:：]\s*([A-EIVX]+)", re.IGNORECASE)

#: CJK Birleşik İdeografları + genişletmeleri + Hiragana/Katakana. Herhangi
#: bir model/araç mesajında bu aralıktan bir karakter görülmesi, kullanıcının
#: bildirdiği "Çince'ye kayma" belirtisinin objektif, otomatik tespitidir —
#: elle transkript okumaya gerek kalmadan evet/hayır cevabı verir.
_CJK_DESENI = re.compile(
    r"[一-鿿㐀-䶿豈-﫿぀-ヿ]"
)

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

#: Bütçe/hız için tam 29'luk kümeden değil, mebi_agent_coz'un kendi
#: kümesinden ilk 8 soru — hepsi araç-çağırma yoğun (çok kelimeli/numaralı).
#: BASLANGIC, yarıda kesilen bir koşuyu belirli bir soru numarasından devam
#: ettirebilmek için (örn. Q1 zaten kaydedildiyse Q2'den başlamak).
_BASLANGIC = int(__import__("os").environ.get("DIAGNOSTIK_BASLANGIC", "0"))
_SAYI = int(__import__("os").environ.get("DIAGNOSTIK_SORU_SAYISI", "8"))
SORU_ALT_KUMESI = SORULAR[_BASLANGIC : _BASLANGIC + _SAYI]

ILERLEME_YOLU = Path(
    "/tmp/claude-1000/-home-emir-Belgeler-Yazilim-BitigAI/"
    "6194d298-ca12-44ae-aeb9-7bca05e10b6b/scratchpad/qwen_ham_ilerleme.jsonl"
)


def _cince_tara(gecmis: list[dict]) -> list[str]:
    """Tüm mesaj geçmişinde (asistan içeriği + araç çağrısı argümanları) CJK
    karakteri arar. Bulunanları, hangi mesajda geçtiğiyle birlikte döner."""
    bulunanlar: list[str] = []
    for mesaj in gecmis:
        parcalar: list[str] = []
        icerik = mesaj.get("content")
        if icerik:
            parcalar.append(str(icerik))
        # Qwen3'ün "thinking" modu ayrı bir alanda akıl yürütüyor (Ollama'nın
        # OpenAI-uyumlu yanıtında `reasoning`) — kayma orada da olabilir.
        akil_yurutme = mesaj.get("reasoning")
        if akil_yurutme:
            parcalar.append(str(akil_yurutme))
        for cagri in mesaj.get("tool_calls") or []:
            parcalar.append(cagri.get("function", {}).get("arguments", ""))
        for parca in parcalar:
            eslesmeler = _CJK_DESENI.findall(parca)
            if eslesmeler:
                ornek = parca[:120].replace("\n", " ")
                bulunanlar.append(f"[{mesaj.get('role')}] {''.join(eslesmeler)} — bağlam: {ornek!r}")
    return bulunanlar


#: RunPod'un proxy'si Cloudflare arkasında — tek istek ~100 sn'yi aşarsa
#: HTTP 524 ile kesiliyor (kendi ZAMAN_ASIMI'mız 180 sn olsa bile Cloudflare
#: önce vazgeçiyor). "Thinking" modlu, yavaş üreten modeller (gemma4 gibi)
#: için cevap/tur bütçesi ortam değişkeniyle daraltılabilir — varsayılan,
#: Cloudflare'in penceresine daha rahat sığan, daha dar bir bütçedir.
_AZAMI_BELIRTEC = int(__import__("os").environ.get("DIAGNOSTIK_AZAMI_BELIRTEC", "4000"))
_AZAMI_TUR = int(__import__("os").environ.get("DIAGNOSTIK_AZAMI_TUR", "8"))
#: Canlı mod — her tur düşünce/cevap metnini token geldikçe basar (döngü/
#: takılma teşhisi için). Varsayılan kapalı: normal koşularda tablo çıktısını
#: karıştırmaz.
_CANLI = __import__("os").environ.get("DIAGNOSTIK_CANLI", "0") == "1"

#: gemma4:12b'nin bilinen "thinking'de döngüye takılma" sorununu (google-
#: deepmind/gemma#727) azaltmak için üç deneysel kaldıraç — hepsi ortam
#: değişkeniyle açılır, varsayılanda kapalı (Qwen gibi bu sorunu göstermeyen
#: modelleri etkilememesi için):
#:   1. sıcaklık > 0: saf greedy (0.0) düşük sıcaklıkta döngüye girme riski
#:      daha yüksek — topluluk gözlemi.
#:   2. reasoning_effort: Ollama'nın OpenAI-uyumlu ucu destekliyor (docs.
#:      ollama.com/api/openai-compatibility), düşünme bütçesini daraltır.
#:   3. frequency_penalty: topluluğun repeat_penalty önerisinin OpenAI-uyumlu
#:      karşılığı — aynı token dizisini tekrar üretmeyi cezalandırır.
_SICAKLIK = float(__import__("os").environ.get("DIAGNOSTIK_SICAKLIK", "0.0"))
_REASONING_EFFORT = __import__("os").environ.get("DIAGNOSTIK_REASONING_EFFORT")  # "low"/"medium"/"none"
_FREQ_PENALTY = __import__("os").environ.get("DIAGNOSTIK_FREQ_PENALTY")

_EKSTRA: dict = {}
if _REASONING_EFFORT:
    _EKSTRA["reasoning_effort"] = _REASONING_EFFORT
if _FREQ_PENALTY:
    _EKSTRA["frequency_penalty"] = float(_FREQ_PENALTY)


def coz(soru: dict) -> tuple[str | None, list[dict], list[str]]:
    for deneme in range(3):
        yanit, gecmis = model.arac_ile_sor(
            istem=soru["metin"],
            araclar=ARACLAR,
            arac_calistir=_arac_calistir,
            sistem=SISTEM_ISTEMI,
            sicaklik=_SICAKLIK,
            azami_belirtec=_AZAMI_BELIRTEC,
            azami_tur=_AZAMI_TUR,
            canli=_CANLI,
            ekstra=_EKSTRA or None,
        )
        cince = _cince_tara(gecmis)
        eslesme = _CEVAP_DUZENI.search(yanit)
        if eslesme:
            return eslesme.group(1).upper(), gecmis, cince
        if deneme < 2:
            continue
    return None, gecmis, cince


def main() -> int:
    # Arka planda çalıştırılıp çıktı dosyaya yönlendirildiğinde Python'un
    # varsayılanı toplu (block) arabellekleme — satır satır akmaz, süreç
    # bitene kadar hiçbir ilerleme görünmez. Canlı izleme için satır tabanlı
    # arabelleğe zorlanıyor.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass  # eski Python: sessizce atla, işlevsellik etkilenmez

    if not model.anahtar_var_mi():
        print(model.anahtar_yardimi(), file=sys.stderr)
        print(
            "\nRunPod/Ollama için ZAI_API_KEY'e herhangi bir dizge yeterli "
            "(Ollama anahtar denetlemez): export ZAI_API_KEY='ollama'",
            file=sys.stderr,
        )
        return 2

    print(f"Uç nokta: {__import__('os').environ.get('ZAI_BASE_URL', '(varsayılan z.ai — RunPod ayarlanmamış!)')}")
    print(f"Model: {__import__('os').environ.get('ZAI_MODEL', '(varsayılan)')}")
    print(f"Sıcaklık: {_SICAKLIK}  ·  ekstra: {_EKSTRA or '(yok)'}\n")

    dogru = yanlis = bos = 0
    cince_kayan_sorular: list[str] = []

    print(f"{len(SORU_ALT_KUMESI)} soru (mebi_agent_coz kümesinden {_BASLANGIC}. sıradan itibaren {len(SORU_ALT_KUMESI)} tanesi)\n")
    print(f"{'kimlik':<12} {'bek':>3} {'bul':<4} {'çince?':>7} durum")
    print("─" * 55)

    ILERLEME_YOLU.parent.mkdir(parents=True, exist_ok=True)
    with ILERLEME_YOLU.open("w", encoding="utf-8") as ilerleme:
        for soru in SORU_ALT_KUMESI:
            print(f"{soru['kimlik']:<12} ... çözülüyor", end="\r")
            try:
                bulunan, gecmis, cince = coz(soru)
            except model.ModelHatasi as hata:
                print(f"{soru['kimlik']:<12} HATA: {hata}")
                ilerleme.write(json.dumps({"kimlik": soru["kimlik"], "hata": str(hata)}, ensure_ascii=False) + "\n")
                ilerleme.flush()
                continue

            if cince:
                cince_kayan_sorular.append(soru["kimlik"])

            if bulunan is None:
                bos += 1
                durum = "∅ FORMAT"
            elif bulunan == soru["cevap"]:
                dogru += 1
                durum = "✓ DOGRU"
            else:
                yanlis += 1
                durum = "✗ YANLIS"

            print(
                f"{soru['kimlik']:<12} {soru['cevap']:>3} {bulunan or '?':<4} "
                f"{'EVET' if cince else 'hayır':>7}   {durum}"
            )
            if cince:
                for satir in cince:
                    print(f"    ÇİNCE BULUNDU: {satir}")

            ilerleme.write(
                json.dumps(
                    {
                        "kimlik": soru["kimlik"],
                        "beklenen": soru["cevap"],
                        "bulunan": bulunan,
                        "durum": durum,
                        "cince_kayma": cince,
                        "son_mesaj": gecmis[-1].get("content", ""),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            ilerleme.flush()

    toplam = len(SORU_ALT_KUMESI)
    print("─" * 55)
    print(f"  doğru {dogru}  ·  yanlış {yanlis}  ·  format hatası {bos}  (toplam {toplam})")
    print()
    if cince_kayan_sorular:
        print(f"  ⚠ ÇİNCE'YE KAYMA TESPİT EDİLDİ: {', '.join(cince_kayan_sorular)}")
        print("    → Belirti temel modelde de var — ince ayar tarifi tek suçlu değil,")
        print("      şablon/model uyuşmazlığı ihtimali de araştırılmalı.")
    else:
        print("  ✓ HİÇ ÇİNCE KARAKTERİ GÖRÜLMEDİ.")
        print("    → Ham model temiz — önceki kaymanın nedeni muhtemelen ince ayar")
        print("      tarifi (veri hacmi/çeşitliliği, öğrenme oranı, epoch sayısı).")
    print("\n  NOT: bu sonuç tanı amaçlıdır, hiçbir altın kümeye/motora geri beslenmez.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
