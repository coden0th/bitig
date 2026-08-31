# Gold sets

Most records in these files no longer store the source sentence, passage, or option text
verbatim. Using exam material to *measure* the engine and *republishing* that material are
different things — the measurements needed to keep running, the source text did not need to
stay in the repository.

Where a record's option or passage text was reduced to that option's/passage's own set of
words, sorted alphabetically (field `kelimeler` instead of `secenekler`/`metin`), instead of
the original sentence. The engine's checks that use these records run word by word — a word's
morphological analysis does not depend on its position in the sentence — so the sorted word
list produces the exact same result as the original sentence would. Verified by rerunning
every affected harness before and after: identical output, question for question.

## The 8 exceptions

Eight records still carry the full original text, because what they measure is not a
per-word property but something about the text's structure: adjacency between two specific
words, a window of a few words, or the character immediately following a word (punctuation
placement). None of that survives word-list reduction. Each of these records carries a
`redakte_edilemez` field stating in Turkish which structural property is needed and pointing
at the function that needs it, together with its `kaynak` (source) field — this is a
documented decision, not an oversight:

- `isim_sorulari.jsonl` — all 3 records (adjacent-word tamlama detection, or word-order for a
  last-word check)
- `noktalama_sorulari.jsonl` — all 3 records (punctuation-position checks; one of the three
  is technically word-level and could be reduced, but was left with the other two for file
  consistency — its `redakte_edilemez` field says so explicitly)
- `anlatim_sorulari.jsonl` — 2 of 6 records (adjacent-word and word-window checks); the other
  4 were reduced

## Files with no exam text at all

`ad_cekimi.jsonl` and `fiil_cekimi.jsonl` never held sentence-level text — single inflected
words only. `baglam_sorulari.jsonl` holds short sentences written for this project, not
sourced from an exam.
