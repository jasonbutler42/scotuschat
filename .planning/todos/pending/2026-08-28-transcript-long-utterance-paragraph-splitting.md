---
created: 2026-08-28
kind: improvement
source: operator, during Phase 51 Wave 2 transcript-style exploration
resolves_phase: null
priority: medium
---

# Split long utterances into paragraphs using the source PDF's own breaks

Opening arguments run very long — a single utterance can fill more than a screen. The
source PDF transcripts already break these into paragraphs. Use those breaks rather than
rendering one undifferentiated block.

**Operator explicitly deferred this to a future improvement.** Filed so the connection to
the transcript design is not lost.

## Why it matters to the design

The operator raised it while deciding the transcript style (D-19, Phase 51). It is the
reason the selected style parks the rail avatar at the bottom and makes it sticky: a
top-anchored avatar scrolls off screen entirely during an opening argument, taking the
speaker's identity with it.

The operator's words: *"the way the pdf transcripts break up opening arguments into
paragraphs is the exact use case."*

## Why it is additive, not a redesign

The style selected in D-19 already renders **multi-paragraph runs** — a run of N
utterances by one speaker is laid out as N bubbles inside one grouped shape, with squared
adjoining corners and a single rail slot. A long utterance split into N paragraphs is
structurally the same thing.

So when this is picked up it is a **parsing change feeding an existing renderer**: teach
the parse step to emit paragraph boundaries within a single utterance, and the transcript
view already knows how to lay them out. No visual redesign required.

Open question for whoever takes it: whether split paragraphs are modelled as one utterance
with N paragraphs, or N utterances sharing a speaker turn. The renderer handles both
identically; the difference matters for the apolitical constraint (an utterance count must
not become a derived per-speaker statistic on any public surface) and for anything that
counts or addresses utterances.

Note the corpus-first posture: this is PDF-transcript work, and PDF ingest is currently
deferred — see the corpus-first scope constraint before scheduling.

See [[transcript-style-switcher]] — the other deferred item from the same conversation.
