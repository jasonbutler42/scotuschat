---
created: 2026-09-25T00:00:00.000Z
title: 803 Harlan II utterances are attributed to Harlan I (j__john_m_harlan) in the source corpus
area: pipeline
priority: medium
files:

  - pipeline/commands/import_convokit.py
  - data/corpus/justice_identity_mapping.csv
---

## Problem

Surfaced 2026-09-25 while sanity-checking corpus coverage during Phase 52
execution. Pre-existing upstream (Oyez/ConvoKit) data error — not introduced
by Phase 52, and not fixed by it.

`data/corpus/utterances.jsonl` attributes **803 utterances** to speaker id
`j__john_m_harlan`, named `John M. Harlan` in `speakers.json` — Harlan I.
Every one of those 803 is dated **1955–1970**:

```
 1955:49  1956:127  1957:69  1958:41  1959:74  1962:29  1963:189
 1964:145 1965:2    1966:15  1968:11  1969:29  1970:23
```

Per the project's own `data/corpus/supreme_court_justices_sections.csv`:

| Person | Tenure |
|---|---|
| John Marshall Harlan (I) | 1877-12-10 → 1911-10-14 (Died) |
| John Marshall Harlan II  | 1955-03-28 → 1971-09-23 (Retired) |

All 803 fall **inside Harlan II's tenure** and 44+ years **after Harlan I's
death**. They are Harlan II's words on the wrong person.

`j__john_m_harlan2` separately carries 3,357 utterances, so the corpus splits
one justice's record across two speaker ids with no overlap in reality.

## Why it matters

Phase 52 (D-01) makes `oyez_speaker_id` the identity join and gives the two
ids distinct name parts — Harlan I with a blank suffix, Harlan II with `II`.
That is correct as an identity mapping, and it means these 803 utterances
will land firmly on a Harlan I person row. The speaker card for a justice who
died in 1911 will show 803 utterances from the Warren and Burger courts.

Under the apolitical constraint this is a faithfulness defect: the site
presents the record, and here the record it presents is wrong about who spoke.

## Constraint on any fix

**Do not edit `speakers.json` or `utterances.jsonl`.** Raw ingested corpus
files are immutable (CLAUDE.md, Key Constraints); all derived data is
regenerable. The correction belongs in the derived layer — a documented,
tested override applied at resolve/import time, regenerable from the
untouched source.

## Suggested approach

A tenure-bounded reattribution at import: when an utterance's argued date
falls outside the mapped justice's tenure window, and exactly one other
justice sharing that surname was sitting on that date, reattribute to them and
record the override. Fail loudly (do not guess) when the window matches zero
or more than one justice.

That generalises beyond Harlan — it would also catch
[[2026-09-25-harlan-ii-stray-2003-utterance]] — but the Harlan pair is the
only known instance at scale. A narrow hardcoded override for
`j__john_m_harlan` + date >= 1955 is a legitimate smaller first cut if the
general rule proves to have no second customer.

Either way the override set must be explicit and tested, not inferred
silently at runtime.
