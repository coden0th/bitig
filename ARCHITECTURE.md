# Architecture

This document explains how Bitig is built and, more importantly, why. The decision log with
dates and measurements is in `docs/decisions.md`.

---

## 1. Derivation, not detection

The first version of this engine looked at a surface form and tried to infer which
phonological event had occurred. Every one of its false positives traced back to substring
matching: a rule keyed on the letters `diye` fired on `hediye`, `diyet`, and `niyet`.

The current engine never inspects the surface for patterns. It derives forward from a root and
an affix chain, and compares the result to the target. A phonological event is not something
guessed from the output; it is the rule that actually fired during derivation.

**Parsing is therefore not a separate algorithm.** It is a pruned search over the generator:

```
target surface
  ↓
[ lexicon ]          candidate roots and their attributes
  ↓
[ morphotactic graph ]   state → affix → state
  ↓
[ derivation cascade ]   rules fire; events and evidence are created here
  ↓
[ prefix pruning ]       if the generated surface is not a prefix of the target, the branch dies
  ↓
exact matches = valid readings (all of them are returned)
  ↓
[ output contract ]
  ↓
[ exam-board policy layer ]   separate, versioned, applied on top
```

Because the generator is the only source of truth, the engine cannot disagree with itself
about what a form means. That consistency is structural rather than tested for.

The pruning is what keeps the search tractable. It also has to be careful: a stem can change
*retroactively* because of a later affix (`gelme` + `-Iyor` gives `gelmiyor`, so the stem is
not a prefix of the target). Cutting too much kills valid branches; cutting too little raises
per-word cost from about 2 ms to 28 ms. The comparison prefix is trimmed by exactly as much as
the applicable rules can touch, no more.

## 2. Rules are triggered by lexical attributes, never by surface letters

Whether a root voices its final consonant, drops its last vowel, or doubles is a property of
the root recorded in the lexicon (`Voicing`, `LastVowelDrop`, `Doubling`, `InverseHarmony`,
and so on). The letters on the surface never trigger anything.

A detail worth stating because it shaped the loader: of the 28,920 lexicon lines, 18,625 carry
no attribute at all. Their attributes are *inferred* at load time. This is why `NoVoicing` is
the most common attribute in the data. It is not a flag, it is the exception list for the
inference.

## 3. Evidence is mandatory

Every event carries a `Kanit` (evidence) record: the position of the change, the sound before
and after, the affix that triggered it, and the stem it applied to. Evidence is created during
derivation. It is never reconstructed afterwards by looking at the output.

This exists so that explanatory text can be generated from a template over structured data
rather than written by a language model. In a system where a wrong answer key propagates
silently to students, the explanation has to be as verifiable as the answer.

Each event also carries a `Kaynak` (provenance) value, and that field is functional rather
than informational. Only events with provenance `TURETIM` (derived) are eligible for automatic
question generation. `SEZGISEL` (heuristic) events go to a human review queue and can never
enter the guaranteed set.

## 4. Ambiguity is preserved, and it is two-tiered

The engine returns every reading that reaches the target. It does not pick one. Choosing
requires context, and context is not the engine's job.

The output contract distinguishes two levels:

- `kesin_olaylar` (certain events): present in **every** reading. These hold no matter which
  reading turns out to be correct, so they are the only safe basis for automatic question
  generation.
- `olasi_olaylar` (possible events): present in at least one reading.
- `olayda_belirsiz` (event-ambiguous): the readings *disagree* about which events occurred.

The third flag is the operationally important one, and it is a filter rather than a note.
`kitabı` parses two ways but both produce voicing, so it is safe. `masada` parses as
`masa + locative` or `masat + dative`, so its certain set is empty and it is flagged. A word
in that state is a bad item for a phonology question: a student can defend the other reading,
which means the distractor is also correct.

Downstream, a context-sensitive selector may narrow the set for tutoring purposes. It lives
outside the engine package, it never invents a reading (it only picks from the closed set the
engine produced), and its output is always marked heuristic.

## 5. The policy layer sits on top, never inside

The exam board's analysis and synchronic linguistics diverge on some words, and both are
correct within their own frame:

```
çevresi   linguistics → no event        ("çevre" is an independent root today)
          exam board  → vowel drop      (çevir + e; it reasons etymologically)
```

Correcting the engine toward the exam board would be the wrong move twice over. It would lose
linguistic correctness, and it would bury a policy that changes over time inside code that
should not change at all. The first version made exactly this mistake.

So policy is a separate, data-driven, versioned layer. It reads engine output and produces a
*new* object holding both views; it never mutates the engine's result. A mode flag selects
which view counts as authoritative, and the other is still visible, so the user can be told
"the exam board disagrees here" instead of being silently handed one answer.

Adding a policy record requires citing a real past exam question. The source field is enforced
by test.

This is visible in the running demo, not just in the source. Try `Evin çevresi güzeldi.` in the
Ana Çözümleyici tab at [bitig.coskun.tech](https://bitig.coskun.tech): both views show up side
by side, with the citation behind the exam board's reading.

## 6. The core is deterministic; models live at the edge

No code inside `bitig/` makes a model call or a network call. This is enforced by test, not by
convention.

The threshold for a question-generation system is not 95%, it is 100%: a wrong answer key
propagates silently and is worse than no question. So anything below the tokenizer (syllables,
phonological events, affix segmentation, orthography) is a tool call, never a model judgment.

Where models are used, the role is strictly to **produce inputs, not labels**:

- generate large volumes of Turkish sentences, which the engine then parses; whatever it
  cannot parse is a coverage gap
- write adversarial candidates, words that look like they carry an event but do not
- act as a second opinion whose disagreements are queued for human review

This split was validated rather than assumed. In an arbitration test on phonological events,
a frontier model disagreed with the engine five times and was wrong all five. On two of those
words it reproduced the exact error the first version of this engine made, and for the same
reason: it was looking at the surface and matching patterns.

## 7. Data lives in data files

Affix definitions, the rule map, lexicon corrections, policy records, and closed-class word
lists are all data, loaded lazily, with a single canonical source each. No fixed list is
embedded in code. The upstream lexicon is never edited; corrections are expressed as
add/remove/attribute-add records in an override file.

Module import has no side effects: no printing, no network, no heavy loading. Import currently
costs about 35 ms.

---

## Constraints worth knowing before changing anything

These were expensive to learn and each is pinned by a test.

**Which stem vowel harmony reads depends on the rule.** Vowel drop harmonizes against the
*original* root; vowel narrowing harmonizes against the *narrowed* stem. Getting this backwards
produces plausible-looking wrong forms in both directions.

**Attributes belong to the stem's current last morpheme, not to the root.** In `geleceğim` the
voicing belongs to the `-AcAk` suffix, not to the verb root. Violating this caused a real bug:
the aorist constraint was checked against the bare root, so every verb carrying a voice or
derivational suffix whose root was of the wrong aorist class failed to parse at all. Very
ordinary words were affected. It went unnoticed for a long time because most common derived
verbs also exist as standalone lexicon entries, and those entries masked the failure.

**Rule order is fixed:** vowel drop, then voicing, then doubling. The reverse transformation
used during candidate generation must mirror this exactly, and compose across steps, or roots
that undergo two changes become unreachable.

**A new stem-shrinking rule has to be added in three places**, not one: forward generation,
reverse candidate generation, and candidate validation. Miss one and the engine silently
reports "unparseable" instead of giving a wrong answer. That is the safe failure mode, but it
is still a coverage hole.

**Adding a source to a shared graph state affects every affix that feeds it.** When the
nominal copula was wired into the noun-root state, participles gained a spurious copular
reading, because participles target the same state. The engine did not suppress it, correctly:
every derivable reading is returned. The fix belonged in the measurement layer, which switched
that criterion from "any reading" to "every reading".

**For roots with both noun and adjective entries, "any reading" and "every reading" logic
cancel each other out.** One real question is only solved by the strict version and another
only by the permissive one. Lexicon line order was tested as a tie-breaker and rejected: the
ordering reflects which section of the source file an entry came from, not which sense is
primary. The resolution is to pick the less risky side, leave the remaining case deliberately
ambiguous, and document it, rather than to force a rule that has no linguistic basis.
