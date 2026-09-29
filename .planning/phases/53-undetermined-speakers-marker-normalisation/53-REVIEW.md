---
phase: 53-undetermined-speakers-marker-normalisation
reviewed: 2026-09-29T00:00:00Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - alembic/versions/0033_utterance_speaker_and_marker_facts.py
  - api/domain/trust.py
  - api/models/models.py
  - api/schemas/utterance.py
  - api/services/arguments.py
  - api/services/trust.py
  - api/tests/test_published_gate.py
  - api/tests/test_trust_domain.py
  - api/tests/test_trust_public_leak_ban.py
  - api/tests/test_trust_recompute.py
  - app/src/app.css
  - app/src/lib/admin/blockerSentence.js
  - app/src/lib/public/ChatBubble.svelte
  - app/src/lib/public/SpeakerPopover.svelte
  - app/src/lib/public/StageDirection.svelte
  - app/src/lib/public/UndeterminedBubble.svelte
  - app/src/lib/public/UndeterminedSpeakerCard.svelte
  - app/src/routes/admin/arguments/+page.server.ts
  - app/src/routes/admin/arguments/+page.svelte
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/routes/admin/review/+page.server.ts
  - app/src/routes/admin/review/+page.svelte
  - app/src/routes/arguments/[slug]/+page.svelte
  - app/tests/blocker-sentence.test.mjs
  - app/tests/helpers/transcript-page.mjs
  - app/tests/undetermined-bubble.browser.test.mjs
  - app/tests/undetermined-speaker-card.browser.test.mjs
  - pipeline/commands/import_convokit.py
  - pipeline/corpus/stage_directions.py
  - pipeline/tests/test_corpus_stage_directions.py
  - pipeline/tests/test_import_convokit_utterances.py
  - tests/test_schema.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 53: Code Review Report

**Reviewed:** 2026-09-29
**Depth:** standard
**Files Reviewed:** 33
**Status:** issues_found

## Summary

This phase adds source-sentinel-speaker and inaudible-marker plumbing across
the Alembic migration, ORM, trust service, pipeline importer, and public
frontend, plus a matching D-14/D-15 explanation card and D-18 blocker
percentage. I traced the two hardest cases by hand against the actual
code (not just the docstrings) rather than trusting them at face value:

1. **The "double-unknown" row** (sentinel speaker + whole-turn Inaudible
   body, D-13, ~5,860 turns): `_incoming_utterance_rows` in
   `pipeline/commands/import_convokit.py` sets `speaker_id = None` via the
   unattributed-sentinel branch (line ~2180) *before* the per-row
   classification loop runs, so the `_ROW_INAUDIBLE` branch (not
   `inaudible_missing_speaker`, since the `speaker` key really was
   present) still writes `is_inaudible_marker=True` even though
   `speaker_id` ended up `None`. That is correct per D-13 (both flags
   must be true simultaneously), but the function's own docstring claims
   `is_inaudible_marker` is true "only for ... a row that keeps a
   resolved speaker_id" — which is not what the code does for this exact
   case. See IN-01.
2. **The CHECK constraints**: both `ck_utterances_undetermined_unattributed`
   and `ck_utterances_inaudible_marker_not_stage` are satisfied by every
   code path I traced (room event, Inaudible-with-known-speaker,
   Inaudible-with-sentinel-speaker, Inaudible-with-missing-speaker-key),
   and `tests/test_schema.py`/`pipeline/tests/test_import_convokit_utterances.py`
   assert the same cases behaviorally. No defect found here.

The trust-tier math (`exceeds_undetermined_majority`,
`undetermined_share_percent`, the PROVISIONAL-floor branch in
`_load_constituents`) checks out against its own test tables, including
the stage-direction-dilution and NULL-fails-closed edge cases. The
`blockerSentence` extraction into a single shared module is a clean
de-duplication of three previously byte-identical copies.

No BLOCKER-class defects found. Two WARNING-class code-quality issues and
two INFO-class documentation/consistency nits are listed below.

## Warnings

### WR-01: Dead, stale `type Blocker` declaration left in admin/arguments/+page.svelte

**File:** `app/src/routes/admin/arguments/+page.svelte:8`
**Issue:** This file's local `blockerSentence` function (which used to take
`(code, count)` and was typed against `type Blocker = { code: string; count:
number }`) was replaced by an import from `$lib/admin/blockerSentence.js`,
but the local `type Blocker` declaration was left behind. It is now
unreferenced anywhere in the file (confirmed via grep — the only hit is the
declaration itself), and it is also stale relative to the runtime shape:
a blocker can now carry an optional `percent` field
(`{code, count, percent?}`, see `blockerSentence.js`'s `TierBlocker`
typedef), which this unused local type does not model. The sibling files
(`admin/arguments/[id]/+page.svelte`, `admin/review/+page.svelte`) both
removed their equivalent local type entirely when they adopted the shared
import — this file is the one inconsistent holdout.
**Fix:** Delete the dead declaration:
```diff
-	type Blocker = { code: string; count: number };
-
 	let { data, form } = $props();
```

### WR-02: `_incoming_utterance_rows` docstring overstates when `is_inaudible_marker` is true

**File:** `pipeline/commands/import_convokit.py:2066-2068` (docstring) vs. the actual behavior at lines ~2151-2224
**Issue:** The docstring says:

> `is_inaudible_marker` (D-04: `True` only for a whole-turn Inaudible
> marker row that keeps a resolved speaker_id, i.e. NOT a room event and
> NOT the missing-speaker fallback below)

This is inaccurate for the D-13 "double-unknown" case, which the test
suite explicitly covers
(`test_sentinel_speaker_inaudible_turn_marks_both_flags`,
`pipeline/tests/test_import_convokit_utterances.py:1637-1666`): when the
turn's `speaker` key is present but resolves to a source-sentinel type
(e.g. `u__inaudible`), the code at line ~2179-2180 sets `speaker_id = None`
(no attributable speaker) *before* the per-row loop, yet the row still
takes the `elif row.kind == _ROW_INAUDIBLE` branch (since
`inaudible_missing_speaker` is only set when the `speaker` key was
*absent*, not when it resolved to a sentinel) and writes
`is_inaudible_marker=True` with `speaker_id=None`/`person_id=None`. That
behavior is correct and required by D-13 — the bug is only in the
docstring's claim that this flag implies "a resolved speaker_id". A
maintainer reading only the docstring (not tracing the sentinel branch by
hand, as this review did) would misjudge what the flag actually
guarantees and could ship a regression assuming `is_inaudible_marker=True`
implies `person_id IS NOT NULL`.
**Fix:** Reword the parenthetical, e.g.:
```diff
-    `is_inaudible_marker` (D-04: `True` only for a whole-turn Inaudible
-    marker row that keeps a resolved speaker_id, i.e. NOT a room event and
-    NOT the missing-speaker fallback below) and `verbatim_text` (D-10: the
+    `is_inaudible_marker` (D-04/D-13: `True` for a whole-turn Inaudible
+    marker row that is NOT a room event and NOT the missing-speaker
+    fallback below -- this includes the "double-unknown" case where the
+    turn's speaker resolves to the source's own sentinel type, so
+    `speaker_id`/`person_id` are still `None` even though this flag is
+    `True`; D-13 requires exactly that combination) and `verbatim_text`
+    (D-10: the
```

## Info

### IN-01: `speaker_undetermined` model-level Python default diverges from migration's stated "no database-side default"

**File:** `api/models/models.py:573` (`speaker_undetermined = Column(Boolean, nullable=True, default=False)`) and `:576` (`is_inaudible_marker`, same shape)
**Issue:** The migration docstring (`alembic/versions/0033_...py:10-14`)
and the model's own inline comment both describe these columns as having
"no database-side default" so that "NULL means written before 0033" and
"fails closed". That is true at the DDL layer (no `server_default`), but
the ORM `Column(..., default=False)` is a *Python-side* default: any
future `Utterance(...)` construction elsewhere in the codebase that
forgets to pass `speaker_undetermined=`/`is_inaudible_marker=` will
silently get `False` written to the row (not `NULL`), rather than
surfacing an obviously-missing value. Today every write site in this
phase (`_import_utterances`, `pipeline/commands/parse.py`'s PDF path)
either sets the field explicitly or is out of scope, so there is no
observed defect — this is a latent inconsistency between the documented
intent ("no default, NULL means legacy") and the actual ORM behavior for
any writer added later that doesn't know to set it.
**Fix:** Consider dropping the ORM-level `default=False` (leaving the
column genuinely default-less at every layer, matching the docstring), or
explicitly acknowledge in the column's comment that new code paths get a
Python-side `False`, not `NULL`, so a future reader doesn't assume NULL is
the only "unset" state to check for.

### IN-02: Redundant re-check of `_is_unattributed_speaker_type` in `_incoming_utterance_rows`

**File:** `pipeline/commands/import_convokit.py:2158-2160` and `:2172-2173`
**Issue:** `speaker_undetermined` is computed once via
`_is_unattributed_speaker_type(speakers_index.get(speaker_id) or {})` at
line 2158, then the very same predicate is re-evaluated a few lines later
at line 2173 (`if _is_unattributed_speaker_type(speaker_meta):`) inside the
`else` branch (the not-already-cached path) to decide the
`raw_speaker_label`/`speaker_id` fallback. Both calls read from the same
`speakers_index` entry and can never disagree, so this is a harmless but
avoidable duplicate lookup/computation on every fresh (non-cached)
speaker resolution across the whole corpus import.
**Fix:** Reuse the already-computed `speaker_undetermined` value instead of recomputing it:
```diff
-                    speaker_meta = speakers_index.get(speaker_id) or {}
-                    if _is_unattributed_speaker_type(speaker_meta):
+                    speaker_meta = speakers_index.get(speaker_id) or {}
+                    if speaker_undetermined:
```

---

_Reviewed: 2026-09-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
