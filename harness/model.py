"""Test üretimi için LLM istemcisi (z.ai / GLM).

Yalnızca geliştirme ve ölçüm tarafında kullanılır. Üretim hattı (`bitig/`) hiçbir
model çağrısı yapmaz ve yapmayacak (CLAUDE.md §1.5, docs/decisions.md §7).

**Modelin rolü girdi üretmektir, etiket üretmek değil.** Eşiğin %100 olduğu bir
sistemde LLM çıktısı doğruluk kaynağı olamaz. Ama aday bulmakta kıyaslanamaz
derecede iyidir; bu yüzden model şunu yapar:

    "Bana bin tane Türkçe cümle yaz."      → motor çözer, çözemedikleri bug'dır
    "Ses olayı varmış GİBİ duran ama       → tuzak adayları; hakemlik ister
     olmayan kelimeler yaz."

Şunu yapmaz: bir kelimenin hangi ses olayını taşıdığına karar vermek. O karar
motorundur; model yalnızca ikinci görüş verir ve çelişkiler incelenir.

Anahtar sohbete ya da koda yazılmaz. İki kaynaktan okunur, bu sırayla:

    1. ZAI_API_KEY ortam değişkeni
    2. ~/.config/bitigai/zai.key dosyası   (depo DIŞINDA, tek satır)

Dosya yolu ikinci seçenektir çünkü ortam değişkeni yalnızca onu tanımlayan
kabukta yaşar; başka bir terminalden ya da betikten çalıştırıldığında görünmez.
Dosya her yerden okunur ve depoya sızma riski taşımaz.

    mkdir -p ~/.config/bitigai
    printf '%s' 'ANAHTAR' > ~/.config/bitigai/zai.key
    chmod 600 ~/.config/bitigai/zai.key

İsteğe bağlı ayarlar:

    export ZAI_MODEL='glm-5.2'
    export ZAI_BASE_URL='https://api.z.ai/api/paas/v4'
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

VARSAYILAN_BASE_URL = "https://api.z.ai/api/paas/v4"
VARSAYILAN_MODEL = "glm-5.2"
ANAHTAR_DOSYASI = Path.home() / ".config" / "bitigai" / "zai.key"
#: Bazı modeller (uzun "thinking" izi üreten, örn. gemma4) tek bir üretimde
#: 180 sn'yi rahatça aşabiliyor — 2026-08-23'te gemma4:12b ile gözlendi.
#: Ortam değişkeniyle ayarlanabilir yapıldı.
ZAMAN_ASIMI = int(os.environ.get("ZAI_ZAMAN_ASIMI", "180"))

#: `urllib`'in varsayılan User-Agent'ı ("Python-urllib/3.x") bazı sağlayıcıların
#: (RunPod'un Cloudflare arkasındaki proxy'si dahil) bot-engelleme kurallarına
#: takılıyor — 2026-08-23'te RunPod uç noktasında HTTP 403 (Cloudflare hata
#: kodu 1010) olarak gözlendi, aynı istek `curl` ile sorunsuz geçiyordu.
_USER_AGENT = "curl/8.5.0"


class ModelHatasi(RuntimeError):
    pass


def _anahtar() -> str | None:
    ortam = os.environ.get("ZAI_API_KEY")
    if ortam:
        return ortam.strip()
    yol = Path(os.environ.get("ZAI_API_KEY_FILE", ANAHTAR_DOSYASI))
    if yol.exists():
        icerik = yol.read_text(encoding="utf-8").strip()
        if icerik:
            return icerik
    return None


def anahtar_var_mi() -> bool:
    return _anahtar() is not None


def anahtar_yardimi() -> str:
    return (
        "API anahtarı bulunamadı. Şunlardan biri gerekli:\n"
        "  export ZAI_API_KEY='...'\n"
        f"  ya da tek satır hâlinde:  {ANAHTAR_DOSYASI}\n"
        "    mkdir -p ~/.config/bitigai\n"
        "    printf '%s' 'ANAHTAR' > ~/.config/bitigai/zai.key\n"
        "    chmod 600 ~/.config/bitigai/zai.key"
    )


def _ayarlar() -> tuple[str, str, str]:
    anahtar = _anahtar()
    if not anahtar:
        raise ModelHatasi(anahtar_yardimi())
    base = os.environ.get("ZAI_BASE_URL", VARSAYILAN_BASE_URL).rstrip("/")
    model = os.environ.get("ZAI_MODEL", VARSAYILAN_MODEL)
    return anahtar, base, model


def sor(
    istem: str,
    sistem: str | None = None,
    sicaklik: float = 1.0,
    azami_belirtec: int = 8000,
) -> str:
    """Modele tek bir istem gönderir, metin yanıtı döner.

    OpenAI uyumlu `/chat/completions` uç noktası kullanılır. Standart kütüphane
    dışında bağımlılık eklenmez — bu araç için bir SDK'ya gerek yok.
    """
    anahtar, base, model = _ayarlar()

    mesajlar = []
    if sistem:
        mesajlar.append({"role": "system", "content": sistem})
    mesajlar.append({"role": "user", "content": istem})

    govde = json.dumps(
        {
            "model": model,
            "messages": mesajlar,
            "temperature": sicaklik,
            "max_tokens": azami_belirtec,
        }
    ).encode("utf-8")

    istek = urllib.request.Request(
        f"{base}/chat/completions",
        data=govde,
        headers={
            "Authorization": f"Bearer {anahtar}",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as yanit:
            veri = json.loads(yanit.read().decode("utf-8"))
    except urllib.error.HTTPError as hata:
        ayrinti = hata.read().decode("utf-8", errors="replace")[:500]
        raise ModelHatasi(f"HTTP {hata.code}: {ayrinti}") from hata
    except urllib.error.URLError as hata:
        raise ModelHatasi(f"bağlantı kurulamadı: {hata.reason}") from hata
    except TimeoutError as hata:
        # Bağlantı kurulduktan SONRA yanıt okuma zaman aşımına uğrarsa
        # (örn. çok uzun "thinking" izi üreten yavaş bir model) urllib bunu
        # URLError'a sarmayabilir, çıplak TimeoutError sızabilir — 2026-08-23'te
        # gemma4:12b ile gözlendi, betiği tamamen çökertiyordu.
        raise ModelHatasi(f"yanıt zaman aşımına uğradı ({ZAMAN_ASIMI} sn)") from hata

    try:
        return veri["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as hata:
        raise ModelHatasi(f"beklenmeyen yanıt biçimi: {str(veri)[:400]}") from hata


def _cagri(
    mesajlar: list[dict],
    araclar: list[dict],
    sicaklik: float,
    azami_belirtec: int,
    ekstra: dict | None = None,
) -> dict:
    anahtar, base, model = _ayarlar()
    govde_sozluk = {
        "model": model,
        "messages": mesajlar,
        "tools": araclar,
        "temperature": sicaklik,
        "max_tokens": azami_belirtec,
    }
    if ekstra:
        govde_sozluk.update(ekstra)
    govde = json.dumps(govde_sozluk).encode("utf-8")
    istek = urllib.request.Request(
        f"{base}/chat/completions",
        data=govde,
        headers={
            "Authorization": f"Bearer {anahtar}",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as yanit:
            return json.loads(yanit.read().decode("utf-8"))
    except urllib.error.HTTPError as hata:
        ayrinti = hata.read().decode("utf-8", errors="replace")[:500]
        raise ModelHatasi(f"HTTP {hata.code}: {ayrinti}") from hata
    except urllib.error.URLError as hata:
        raise ModelHatasi(f"bağlantı kurulamadı: {hata.reason}") from hata
    except TimeoutError as hata:
        raise ModelHatasi(f"yanıt zaman aşımına uğradı ({ZAMAN_ASIMI} sn)") from hata


def _cagri_akisli(
    mesajlar: list[dict],
    araclar: list[dict],
    sicaklik: float,
    azami_belirtec: int,
    yaz,
    ekstra: dict | None = None,
) -> dict:
    """`_cagri` ile aynı sözleşmeyi (aynı `veri["choices"][0]["message"]` biçimini)
    döner ama yanıtı SSE (`stream: true`) ile parça parça okur ve her parçayı
    geldikçe `yaz(metin)` ile bastırır — canlı izleme ve "döngüye mi takıldı"
    teşhisi için (2026-08-23, gemma4:12b'nin uzun "thinking" izini gözlemlemek
    amacıyla eklendi).

    Ollama/OpenAI SSE biçimi: her satır `data: {...}` ya da `data: [DONE]`.
    `delta.reasoning` (varsa) ve `delta.content` ayrı ayrı akar; `delta.
    tool_calls` parçalı gelebilir (fonksiyon adı/argümanları birden çok
    parçaya bölünmüş olabilir), indekse göre biriktirilir.
    """
    anahtar, base, model = _ayarlar()
    govde_sozluk = {
        "model": model,
        "messages": mesajlar,
        "tools": araclar,
        "temperature": sicaklik,
        "max_tokens": azami_belirtec,
        "stream": True,
    }
    if ekstra:
        govde_sozluk.update(ekstra)
    govde = json.dumps(govde_sozluk).encode("utf-8")
    istek = urllib.request.Request(
        f"{base}/chat/completions",
        data=govde,
        headers={
            "Authorization": f"Bearer {anahtar}",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )

    icerik_parcalari: list[str] = []
    akil_yurutme_parcalari: list[str] = []
    tool_calls_biriken: dict[int, dict] = {}
    bitis_nedeni = None

    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as yanit:
            for ham_satir in yanit:
                satir = ham_satir.decode("utf-8", errors="replace").strip()
                if not satir.startswith("data:"):
                    continue
                veri_str = satir[len("data:") :].strip()
                if veri_str == "[DONE]":
                    break
                try:
                    parca = json.loads(veri_str)
                except json.JSONDecodeError:
                    continue
                secim = (parca.get("choices") or [{}])[0]
                delta = secim.get("delta", {})
                if delta.get("reasoning"):
                    akil_yurutme_parcalari.append(delta["reasoning"])
                    yaz(delta["reasoning"])
                if delta.get("content"):
                    icerik_parcalari.append(delta["content"])
                    yaz(delta["content"])
                for tc in delta.get("tool_calls") or []:
                    idx = tc.get("index", 0)
                    kayit = tool_calls_biriken.setdefault(idx, {"id": None, "name": "", "arguments": ""})
                    if tc.get("id"):
                        kayit["id"] = tc["id"]
                    fonk = tc.get("function") or {}
                    if fonk.get("name"):
                        kayit["name"] += fonk["name"]
                    if fonk.get("arguments"):
                        kayit["arguments"] += fonk["arguments"]
                if secim.get("finish_reason"):
                    bitis_nedeni = secim["finish_reason"]
    except urllib.error.HTTPError as hata:
        ayrinti = hata.read().decode("utf-8", errors="replace")[:500]
        raise ModelHatasi(f"HTTP {hata.code}: {ayrinti}") from hata
    except urllib.error.URLError as hata:
        raise ModelHatasi(f"bağlantı kurulamadı: {hata.reason}") from hata
    except TimeoutError as hata:
        raise ModelHatasi(f"yanıt zaman aşımına uğradı ({ZAMAN_ASIMI} sn)") from hata

    mesaj: dict = {"role": "assistant", "content": "".join(icerik_parcalari) or None}
    if akil_yurutme_parcalari:
        mesaj["reasoning"] = "".join(akil_yurutme_parcalari)
    if tool_calls_biriken:
        mesaj["tool_calls"] = [
            {
                "id": kayit["id"] or f"call_{idx}",
                "type": "function",
                "function": {"name": kayit["name"], "arguments": kayit["arguments"]},
            }
            for idx, kayit in sorted(tool_calls_biriken.items())
        ]
    return {"choices": [{"message": mesaj, "finish_reason": bitis_nedeni}]}


def arac_ile_sor(
    istem: str,
    araclar: list[dict],
    arac_calistir,
    sistem: str | None = None,
    sicaklik: float = 0.0,
    azami_belirtec: int = 4000,
    azami_tur: int = 8,
    canli: bool = False,
    ekstra: dict | None = None,
) -> tuple[str, list[dict]]:
    """Çok turlu, OpenAI uyumlu `tools` ile araç çağırabilen sohbet döngüsü.

    Deneysel — yalnızca `harness/` altında, ölçüm amaçlı kullanılır (bkz. modül
    docstring'i). Motor **doğruluk kaynağı olarak** çağrılıyor olsa bile, modelin
    ürettiği NİHAİ cevap yine de doğrulanmadan hiçbir yere kaydedilmez.

    `araclar`: OpenAI `tools` şeması (`[{"type": "function", "function": {...}}, ...]`).
    `arac_calistir(ad, argumanlar) -> str`: bir araç çağrısını yürütüp metin sonucu
    döner; hatalar da metne çevrilip modele geri verilir (model kendi düzeltsin).

    `canli=True` ise her turun düşünce/cevap metni AKIŞLI olarak (token geldikçe)
    stdout'a basılır — modelin bir döngüye takılıp takılmadığını canlı izlemek
    için (2026-08-23'te gemma4:12b'nin uzun "thinking" izini teşhis etmek amacıyla
    eklendi). Araç çağrıları da (ad + argüman) her tur başında/sonunda ayrıca
    yazdırılır.

    `ekstra`: OpenAI-uyumlu istek gövdesine olduğu gibi eklenecek ek alanlar
    (örn. `{"reasoning_effort": "low", "frequency_penalty": 0.3}`) — Ollama'nın
    OpenAI-uyumlu uç noktası bunları destekliyor (bkz. docs.ollama.com/api/
    openai-compatibility). 2026-08-23'te gemma4:12b'nin "thinking" modunda
    döngüye takılmasını (bilinen bir sorun, google-deepmind/gemma#727) azaltmak
    için eklendi.

    Döner: `(son_metin_yanıt, tüm_mesaj_geçmişi)` — geçmiş, hangi araçların ne
    sırayla çağrıldığını denetlemek/loglamak için.
    """
    mesajlar: list[dict] = []
    if sistem:
        mesajlar.append({"role": "system", "content": sistem})
    mesajlar.append({"role": "user", "content": istem})

    for tur_no in range(azami_tur):
        if canli:
            print(f"\n--- tur {tur_no + 1}/{azami_tur} ---", flush=True)
            veri = _cagri_akisli(
                mesajlar,
                araclar,
                sicaklik,
                azami_belirtec,
                yaz=lambda p: print(p, end="", flush=True),
                ekstra=ekstra,
            )
            print()  # tur sonunda satır sonu
        else:
            veri = _cagri(mesajlar, araclar, sicaklik, azami_belirtec, ekstra=ekstra)
        try:
            mesaj = veri["choices"][0]["message"]
        except (KeyError, IndexError) as hata:
            raise ModelHatasi(f"beklenmeyen yanıt biçimi: {str(veri)[:400]}") from hata

        mesajlar.append(mesaj)
        cagrilar = mesaj.get("tool_calls")
        if not cagrilar:
            return mesaj.get("content") or "", mesajlar

        for cagri in cagrilar:
            ad = cagri["function"]["name"]
            try:
                argumanlar = json.loads(cagri["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                argumanlar = {}
            if canli:
                print(f"[araç çağrısı] {ad}({argumanlar})", flush=True)
            try:
                sonuc = arac_calistir(ad, argumanlar)
            except Exception as hata:  # model kendi düzeltebilsin diye hata da metne çevrilir
                sonuc = f"HATA: {hata}"
            if canli:
                print(f"[araç sonucu] {str(sonuc)[:300]}", flush=True)
            mesajlar.append(
                {
                    "role": "tool",
                    "tool_call_id": cagri["id"],
                    "content": str(sonuc),
                }
            )

    raise ModelHatasi(f"azami tur sayısına ({azami_tur}) ulaşıldı, model karar veremedi")


def satirlari_ayikla(metin: str) -> list[str]:
    """Model yanıtından temiz satır listesi çıkarır.

    Model numaralandırma, tire, kod bloğu gibi süsler ekleyebilir; bunlar
    temizlenir. Yanıtın biçimine güvenmek yerine ayıklamak, istemi kırılgan
    kurallarla doldurmaktan daha sağlamdır.
    """
    satirlar = []
    for ham in metin.splitlines():
        satir = ham.strip().strip("`")
        if not satir or satir.startswith("#"):
            continue
        # "1. ", "12) ", "- ", "* " gibi önekleri at
        while satir and (satir[0].isdigit() or satir[0] in "-*.)"):
            yeni = satir.lstrip("0123456789").lstrip(".)-* ")
            if yeni == satir:
                break
            satir = yeni
        if satir:
            satirlar.append(satir)
    return satirlar
