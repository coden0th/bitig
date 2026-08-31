# BitigAI — Proje Bağlamı

TYT Türkçe için ÖSYM formatına uygun soru ve **kanıta dayalı** açıklamalı çözüm üreten sistem.
Deterministik motor katmanı (BMM v2) yazıldı ve ölçülüyor. Model eğitimi gündemde değil.

Bu dosya, oturum başında bilmen gerekenleri içerir. Kararlar burada; tekrar sorma.

---

## 1. Temel ilkeler

Bunlar tasarım tercihi değil, karar kuralı. Bir öneri bunlarla çelişiyorsa öneri yanlıştır.

1. **Tespit değil türetim.** Yüzey biçimine bakıp "burada ne olmuş olabilir" diye tahmin etme.
   Kök + ek dizisinden ileriye türet, yüzeyle karşılaştır. Eşleşen türetim doğru çözümlemedir.
   Dil bilgisi olayı, türetim sırasında tetiklenen kuralın kendisidir — tahmin değil.

2. **Motor üretici değil hakem.** Motorlar üretim sırasında yardımcı olarak değil, üretimden
   sonra çalışan doğrulama kapıları olarak konumlanır. Kalite tavanı üretende değil filtrededir.

3. **Ölçülmeyen iyileşmez.** Altın küme ve test harness'ı, kod yazmadan önceki adım.
   Tek bir "doğruluk" yüzdesi yok; **kural bazında precision / recall** var.

4. **Katmanları ayır.** Motor saf dilbilim üretir, politika bilmez. ÖSYM istisnaları ayrı,
   veri odaklı, sürümlenebilir bir katmanda durur.

5. **Deterministik çekirdek, model çevrede.** Çekirdek mantık asla LLM'e bırakılmaz.
   Modelin yeri: test kümesi üretimi, düşmanca negatif örnek yazımı, anlaşmazlık taraması,
   bağlam/hikâye metni yazımı.

**Alt-token kuralı:** Tokenizer'ın altına inen hiçbir iş modele verilmez (hece, ses olayı,
ek çözümlemesi, yazım). Hepsi tool call.

> İlke 5 deneysel olarak doğrulandı: GLM-5.2 ses olayı hakemliğinde motora karşı sınandı,
> 5 çelişkide 5'inde de motor haklı çıktı. Model `güdük` ve `yudum` sözcüklerinde **v1'in
> yaptığı hatanın aynısını** yaptı — çünkü aynı şeyi yapıyor: yüzeye bakıp örüntü eşleştirmek.

---


> Ayrıntılı geliştirme günlüğü, ölçüm sonuçları, mimari kararlar ve
> "pahalıya öğrenilmiş" teknik dersler artık `docs/decisions.md`'de —
> bölüm numaraları (2, 3, 4, 5, 6, 7, 9, 11, 12, 13) orada aynen korunmuştur.
> Güncel ölçüm sonuçları için `RESULTS.md`, mimari için `ARCHITECTURE.md`'ye bak.

---

## 8. Kod kuralları

- **Türkçe metin işleme:** `.lower()` kullanma. `bitig.fonetik.kucult()` / `buyut()` var.
- **Altdizi eşleşmesiyle kural tetikleme yasak.** Morfolojik sınırla veya türetimle çalış.
- **Kütüphanelerin ekran/string çıktısını parse etme.** Yapısal API kullan.
- **Sabit listeler koda gömülmez**, veri dosyasına gider. Tek kaynak.
  Ek tanımları `veri/ekler.json`, kural haritası `veri/kural_haritasi.json`, sözlük
  düzeltmeleri `veri/tyt_override.json`, ÖSYM istisnaları `veri/osym_politikasi.json`.
- **Modül import edilirken yan etki olmasın** — `print`, ağ indirmesi, ağır yükleme yok.
  Tembel yükleme kullan; şu an import 35 ms ve 0 karakter stdout.
- **API cümle seviyesinde.** `cozumle(cumle)` dış API'dir; `kelimeyi_cozumle` test içindir.
- **Her kural için önce test.** Pozitif ve negatif örnek olmadan kural eklenmez.
- **Motor politikayı bilmez.** `bitig/cozumleyici.py` ve `sozlesme.py` içine "osym" sızarsa
  test kırılır (`testler/test_osym.py`).
- Alan terimleri Türkçe kalır (`ses_olayi`, `kok`, `ekler`). Zemberek öznitelik değerleri
  (`Voicing`, `LastVowelDrop`) **çevrilmez** — kaynak dosyanın içeriğidir; `Oznitelik` sınıfı
  Türkçe adlı sabitler sunar.

---

## 10. Yapma

- Çekirdek mantığı LLM'e devretme. "Model bunu genelde doğru yapıyor" gerekçe değil —
  soru üretiminde eşik %95 değil %100. Yanlış cevap anahtarı sessizce yayılır.
- Yeni kuralı, yanlış pozitifini ölçmeden ekleme.
- Telif hakkı olan yayınevi sorularını eğitim ya da veri kaynağı olarak kullanma.
  Temiz kaynaklar: ÖSYM çıkmış sorular, MEB/EBA materyalleri, anlaşmalı kurum verisi.
- Model üretimli çözümü doğrulamadan kaydetme.
- Belirsiz çözümlemeyi tek bir okumaya indirgeme.
- **`veri/zemberek/` altındaki dosyaları değiştirme.** Upstream kopyadır; düzeltmeler
  `veri/tyt_override.json`'a yazılır (`kaldir` / `ekle` / `oznitelik_ekle`).
- **Kullanıcı istemeden commit atma.** Depo yereldir, uzak sunucu yoktur.

---

