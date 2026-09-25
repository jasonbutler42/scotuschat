---
created: 2026-09-25T00:00:00.000Z
title: One 2003 utterance is attributed to Harlan II, who left the bench in 1971
area: pipeline
priority: low
files:

  - pipeline/commands/import_convokit.py
---

## Problem

Surfaced 2026-09-25 alongside
[[2026-09-25-harlan-i-carries-harlan-ii-utterances]]. Pre-existing upstream
(Oyez/ConvoKit) data error.

`j__john_m_harlan2` (John M. Harlan II) carries 3,357 utterances. 3,356 are
dated 1958–1970, inside his tenure. **One** is dated 2003:

```
conversation_id: 23103
case_id:         2003_02-628
text:            "Ms. Zinn, I thought that you said in response to my
                  question that this... this waiver... t"
```

Harlan II's tenure was 1955-03-28 → 1971-09-23 (retired), per
`data/corpus/supreme_court_justices_sections.csv`. This utterance is 31+
years outside it, and outside Harlan I's tenure too.

## Why it matters

Lower impact than the 803-utterance sibling — it is a single record — but it
is the same class of defect, and it lands the same way: a justice's speaker
card showing words he did not say, in a case argued decades after he left the
Court. Absent data renders as absent in this project; wrong data must not
render as fact.

## Constraint on any fix

Same as the sibling todo: **do not edit the corpus source files.** The
correction is a derived-layer override.

## Suggested approach

The correct speaker is whichever justice actually asked this question in
`2003_02-628` — determining that needs the Oyez record for that argument and
is not inferable from the corpus alone. Until it is established, the honest
derived value is `<UNKNOWN>` rather than a guess.

If the tenure-bounded reattribution rule proposed in the sibling todo is
built, this record is caught by it automatically: the date matches no sitting
justice named Harlan, so the rule refuses to guess and falls through to
unknown — which is the right outcome here.
