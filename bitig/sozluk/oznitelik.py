"""Kök özniteliklerinin çıkarımı.

Motorun doğruluk tabanı burasıdır. Sözlükte `kitap` satırı çıplaktır; `Voicing`
özniteliği dosyada **yazmaz**, yükleme anında çıkarılır. `NoVoicing`in sözlükteki
en yaygın öznitelik olmasının sebebi de budur: o bir bayrak değil, buradaki
çıkarımın istisna listesidir (diyet, niyet, sepet...).

Kurallar Zemberek `TurkishDictionaryLoader.inferMorphemicAttributes` ile aynıdır.
Fonksiyon saftır: sözlük dosyasına dokunmaz, tek girdiyle test edilebilir.
"""

from __future__ import annotations

from bitig import fonetik
from bitig.sozluk.girdi import IkincilTur, Oznitelik, SozlukGirdisi, Tur

#: Yumuşamayı sonradan mümkün kılan sözcük sonları. "renk" → "rengi",
#: "katalog" → "kataloğu". Genel ötümsüz-süreksiz kuralının dışında kalırlar.
_YUMUSAYAN_SONLAR = ("nk", "og")


def cikar(girdi: SozlukGirdisi) -> frozenset[str]:
    """Girdinin açık özniteliklerine, çıkarılanları ekleyerek tam kümeyi döner.

    Açıkça yazılmış öznitelikler her zaman kazanır: `diyet [A:NoVoicing]` kaydı
    iki heceli ve `t` ile bitse de yumuşama almaz.
    """
    oznitelikler = set(girdi.oznitelikler)

    if girdi.tur == Tur.FIIL:
        _fiil_oznitelikleri(girdi.kok, oznitelikler)
    elif girdi.tur in Tur.ISIMSILER:
        _isim_oznitelikleri(girdi, oznitelikler)

    return frozenset(oznitelikler)


def _fiil_oznitelikleri(kok: str, oznitelikler: set[str]) -> None:
    """Fiil köküne göre çıkarım. (Dilim 2'de kullanılacak, şimdi eksiksiz duruyor.)"""
    unlu_sayisi = fonetik.unlu_sayisi(kok)

    if fonetik.unluyle_bitiyor(kok):
        # de- + -Iyor → diyor : ünlüyle biten fiilde ara ünlü düşer
        oznitelikler.add(Oznitelik.ARA_UNLU_DUSER)
        oznitelikler.add(Oznitelik.EDILGEN_IN)

    if kok.endswith("l"):
        oznitelikler.add(Oznitelik.EDILGEN_IN)

    if fonetik.unluyle_bitiyor(kok) or (kok.endswith(("l", "r")) and unlu_sayisi > 1):
        oznitelikler.add(Oznitelik.ETTIRGEN_T)

    # Geniş zaman biçimi: tek heceli → -Ar, çok heceli → -Ir.
    # Açıkça yazılmışsa dokunulmaz (gelmek [A:Aorist_I] gibi düzensizler).
    if unlu_sayisi > 1 and Oznitelik.GENIS_ZAMAN_A not in oznitelikler:
        oznitelikler.add(Oznitelik.GENIS_ZAMAN_I)
    elif unlu_sayisi == 1 and Oznitelik.GENIS_ZAMAN_I not in oznitelikler:
        oznitelikler.add(Oznitelik.GENIS_ZAMAN_A)


def _isim_oznitelikleri(girdi: SozlukGirdisi, oznitelikler: set[str]) -> None:
    """İsim/sıfat/ikileme için ünsüz yumuşaması çıkarımı.

    v1'in `güdük`/`yudum` yanlış pozitiflerini kapatan yer burasıdır: yumuşama
    yalnızca *çok heceli ve ötümsüz süreksizle biten* köklerde çıkarılır, üstelik
    açık `NoVoicing`/`InverseHarmony` varsa hiç çıkarılmaz.
    """
    kok = girdi.kok
    if not kok:
        return
    unlu_sayisi = fonetik.unlu_sayisi(kok)
    ozel_ad = girdi.ikincil_tur == IkincilTur.OZEL_ISIM
    kisaltma = girdi.ikincil_tur == IkincilTur.KISALTMA

    if (
        unlu_sayisi > 1
        and kok[-1] in fonetik.SUREKSIZ_OTUMSUZLER
        and not ozel_ad
        and not kisaltma
        and Oznitelik.YUMUSAMA_YOK not in oznitelikler
        and Oznitelik.TERS_UYUM not in oznitelikler
    ):
        oznitelikler.add(Oznitelik.YUMUSAMA)

    # "nk"/"og" sonu ayrı bir daldır: ters uyum ve kısaltma denetimi yoktur,
    # ve bu dala giren sözcük varsayılan NoVoicing'i hiç almaz.
    if kok.endswith(_YUMUSAYAN_SONLAR):
        if Oznitelik.YUMUSAMA_YOK not in oznitelikler and not ozel_ad:
            oznitelikler.add(Oznitelik.YUMUSAMA)
    elif unlu_sayisi < 2 and Oznitelik.YUMUSAMA not in oznitelikler:
        # Tek heceliler yumuşamaz: top → topu, saç → saçı.
        oznitelikler.add(Oznitelik.YUMUSAMA_YOK)


def zenginlestir(girdi: SozlukGirdisi) -> SozlukGirdisi:
    """Girdiyi çıkarılmış öznitelikleriyle birlikte döner."""
    from dataclasses import replace

    return replace(girdi, oznitelikler=cikar(girdi))
