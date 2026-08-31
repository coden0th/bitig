# Bitig

A morphological analyzer and rule engine for Turkish, built for the exam-preparation domain.

Bitig parses an inflected Turkish word into its root and affix chain, and reports which
phonological events (consonant voicing, vowel drop, epenthesis, and four others) occurred
during the derivation. Every reported event carries **evidence**: the position in the surface
form, the sound before and after the change, and the affix that triggered it.

Turkish is agglutinative. A single noun can carry a chain of case, possessive, plural, and
copular suffixes, and applying them mutates the stem in ways that English-centric NLP
pipelines and subword tokenizers do not model. Bitig exists because a language model asked to
explain *why* `kitabı` shows consonant voicing will pattern-match on the surface string and
be confidently wrong. This engine derives the answer instead of guessing it.

---

## Demo

[bitig.coskun.tech](https://bitig.coskun.tech) runs the actual engine, not a mockup — one tab
per component:

| Tab | What it does |
|---|---|
| Ana Çözümleyici | Breaks a sentence's words into root + affix chains, with evidence per event |
| Anlatım Bozukluğu | Scans for five narrow, word-list-based usage-error patterns |
| Yazım | Suggests a spelling fix from a missed sound rule; checks a word against a cached TDK lookup |
| Noktalama | Flags a missing comma after a conditional suffix, or a misplaced apostrophe on a proper noun |
| Atasözü / Deyim | Looks up a proverb or idiom in a 13,592-entry local dictionary |
| İsim Soylu | Classifies closed-class words (pronoun, adjective, adverb, ...) from sentence position |
| Hece / Ünlü Uyumu | Syllabifies a word and checks vowel harmony |
| Bağlamsal Seçici | Picks the contextually right reading from the engine's closed candidate set |

Seven of the eight tabs are exactly what's described in this document: local, deterministic,
no network call. The eighth needs a model call to work, so it's disabled server-side in the
public demo — the endpoint refuses the request without touching the network. The tab itself
stays up: it explains the mechanism and walks through one frozen, real example instead of
taking live input. Which parts of this project need a model and which don't is the
architecture itself, not an implementation detail — seeing that split enforced in a running
demo is better evidence than reading about it.

---

## The central idea

**There is no separate parsing algorithm. Parsing is a pruned search over the generator.**

Given a target surface form, Bitig starts from candidate roots, walks the morphotactic graph,
and runs the full derivation cascade at every step. If the generated stem is not a prefix of
the target, the branch dies. Whatever reaches an exact match is a valid reading.

The consequence is structural: the engine cannot become inconsistent between what it
*detects* and what it *derives*, because there is only one source of truth, the generator.
The first version of this project did surface-pattern detection and accumulated a long tail of
false positives from substring matching. That entire class of bug is gone by construction.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design in full.

---

## What it does

```
$ python -m bitig "Kitabı masaya bıraktım"

kitabı
   kesin olaylar: SES.YUM.01
   kitap (Noun)  +  ı
      ekler : EK.HAL.BEL
      izi   : kitap → kitabı
      olay  : SES.YUM.01  Ünsüz Yumuşaması
              kanıt: 'kitap' içinde konum 4, p → b, tetikleyen ek 'ı'
              kaynak: turetim, güven: 1.0
```

Two properties of that output matter more than the parse itself.

**Ambiguity is preserved, not resolved.** `kitabı` has two readings (accusative case and
third-person possessive). Both are returned. The engine is responsible for producing the
complete candidate set, not for choosing between them. Choosing requires context, and the
context layer lives outside the engine and is marked as heuristic so it can never be mistaken
for derivational evidence.

**Ambiguity is two-tiered.** `kesin_olaylar` are events present in *every* reading, so they
hold regardless of which reading is correct. `olayda_belirsiz` flags words whose readings
*disagree* about which events occurred. That flag is not informational, it is a filter:
such a word is a bad item for a phonology question, because a student can defend the other
reading.

---

## Scope

Seven phonological rules: consonant voicing, vowel drop, consonant epenthesis, buffer
consonant insertion, assimilation, vowel narrowing, and consonant drop.

Nominal inflection (including the copula on nominal predicates), verbal inflection (mood,
person, voice, verbal nouns, compound tenses, ability, and the three descriptive compound
verbs), the question clitic, and common derivational suffixes. 95 affix definitions across 17
states in `veri/ekler.json`.

Additional engines built on the same core: syllabification and vowel harmony, orthographic
error detection, punctuation checks, a closed-class word classifier, and a proverb/idiom
lookup layer.

**Deliberately out of scope**, documented rather than faked: liaison across word boundaries,
spelling conventions that involve no derivation, and lexicalized derivations where the
official exam board's analysis diverges from synchronic linguistics. That last category is
handled by a separate policy layer that reports both views rather than overwriting one with
the other.

---

## Results

Headline numbers, with the caveats that belong next to them, are in [RESULTS.md](RESULTS.md).
The short version:

| Measure | Result |
|---|---|
| Past exam questions, phonology | 12 correct, 2 ambiguous, **0 wrong** (of 14) |
| Past exam questions, verbs | 8 / 8 |
| Coverage on clean Turkish text | 97.83%¹ |
| Disagreements with `zeyrek` (independent analyzer) | 2 in 207 words, engine correct in both |
| Round-trip integrity | 100% over 226,583 generations |
| Unit tests | 502 |
| Speed | ~2.5 ms/word, zero production dependencies |

¹ This measure regenerates its own test corpus from a model on every run, so the figure moves
by a decimal point or two between runs; it is not a fixed reference number.

Read the caveats. Of the gold-set entries, 17 of 124 nominal-inflection entries and 4 of 83
verbal-inflection entries currently carry a citation to official curriculum material; the rest
were written during development and are being progressively replaced as sourced material
becomes available. The numbers that do not depend on those labels are marked as such in
RESULTS.md.

---

## Install and run

```bash
git clone https://github.com/coden0th/bitig
cd bitig
python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# fetch third-party data that is not redistributed here (see below)
.venv/bin/python -m harness.atasozu_indir

.venv/bin/python -m bitig "Kitabı masaya bıraktım"
.venv/bin/python -m bitig --json "burnu"
.venv/bin/python -m pytest testler/ -q
```

The engine package (`bitig/`) uses only the Python standard library. Nothing in it makes a
network call or a model call, by design and enforced by test. The development and measurement
tooling under `harness/` is where optional dependencies and any model access live.

---

## Repository layout

```
bitig/          the engine. pure stdlib, no network, no model calls
  cozumleyici.py    pruned search over the generator
  uretici.py        the single source of truth for derivation
  turetim.py        the rule cascade; events and evidence are born here
  morfotaktik.py    the affix graph, interpreted from data
  sozlesme.py       output contract
  osym.py           exam-board policy layer, applied on top, never inside
  sozluk/           lexicon loading and attribute inference
veri/           data. affix graph, rule map, lexicon overrides, policy records
harness/        measurement and development tooling. may use network
web/            the live demo's frontend — a single static HTML page
web_server.py   the demo's backend. stdlib http.server, wraps the engines above;
                the one model-calling endpoint is disabled server-side
testler/        unit tests
altin/          gold sets; see altin/README.md for the source-text redaction policy
docs/           design decisions and change log
```

---

## Data and attribution

**Zemberek lexicon** (`veri/zemberek/`) is redistributed here under the Apache License 2.0.
Source: [github.com/ahmetaa/zemberek-nlp](https://github.com/ahmetaa/zemberek-nlp). The files
are an unmodified upstream copy; corrections are applied at load time from
`veri/tyt_override.json` rather than by editing the source. The license text is included at
`veri/zemberek/LICENSE.zemberek`.

**Proverb and idiom data** is not redistributed. `harness/atasozu_indir.py` fetches it at
setup time from its source. Run it once before using `atasozu.py`.

**Curriculum text and past exam questions** used during development are not included in this
repository. Most gold-set records were reduced to an alphabetized word list instead of the
original sentence or passage — the engine's checks run word by word, so this changes nothing
about what is measured, only what is stored. A small number of records measure something about
sentence structure itself (word adjacency, a window of a few words, punctuation position) and
could not be reduced this way; those keep their full text and are marked with a
`redakte_edilemez` field stating why. See [`altin/README.md`](altin/README.md) for the full
account and the exact record list.

---

## License

The code in this repository is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
Bundled third-party data retains its own license as described above.

---

## Development notes

This project was built with heavy use of AI coding assistants. The architecture, the rule
system, the measurement design, and the decisions recorded in `docs/decisions.md` are mine,
and I am happy to walk through any of them. `CLAUDE.md` holds the working agreement used
during development and is kept in the repository because the source docstrings reference it.

Author: Emir Coşkun. Contact: emir@coskun.tech
