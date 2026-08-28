---
created: 2026-08-28
kind: idea
source: operator, during Phase 51 Wave 2 transcript-style exploration
resolves_phase: null
priority: low
---

# Reader-selectable transcript style ("switcher")

Offer the reader a choice of transcript presentation styles, each matched to a familiar
messaging interface (the operator named Telegram, WhatsApp, iPhone Messages, Android
Messages), so people can read in the environment most familiar to them.

**Operator was explicit that this is NOT a priority.** Filed to preserve the rationale,
not to schedule work.

## Why it was raised

It connects to a founding purpose of the project — making oral arguments easier to read.
The operator offered two hypotheses and labelled both as unverified:

1. Different people would want to read with different visuals.
2. Matching a familiar interface would increase engagement and discovery.

Neither is confirmed. If this is ever picked up, they are the things to test first — the
feature is only worth building if the first hypothesis holds, and only worth promoting if
the second does.

## Why it is cheap to reach later

Phase 51 plan 51-07 builds the **run-grouping layer** (turns grouped by consecutive
speaker before layout) regardless of this item, because the selected style D-19 needs it
for its corner grouping and its sticky rail. Run grouping is also the prerequisite every
familiar messaging idiom needs, since they all collapse consecutive messages somehow.

So the groundwork lands anyway. A switcher would be a rendering variant over an existing
grouped model rather than a rewrite — provided 51-07 keeps grouping separate from
presentation, which D-19 requires it to.

Four candidate styles were already designed and rendered in Figma during Phase 51 and
survive in the file's `transcript-style-exploration` section: A (avatar in bubble header),
B2 (avatar in outside rail — the selected style), C (two tracks with a centre spine), and
D (reading-first, no bubbles). Any switcher work should start from those rather than from
a blank page.

See [[transcript-long-utterance-paragraph-splitting]] — the other deferred item from the
same conversation.
