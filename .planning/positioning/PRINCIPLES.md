---
title: SCOTUS Chat Principles
date: 2026-07-09
status: internal draft
source: POS-001
---

# SCOTUS Chat Principles

These principles guide product, design, content, and copy decisions for SCOTUS
Chat. They are intended to be practical: each principle should help answer
whether a future feature, layout choice, label, or piece of public messaging
belongs in the product.

## 1. Clarify Structure, Not Meaning

SCOTUS Chat should make the structure of an oral argument easier to follow. It
should not interpret the legal meaning of the argument for the reader.

The product may clarify:

- Who is speaking.
- Which role a speaker has.
- Which side an advocate represents.
- When the exchange moves between bench and advocates.
- Where the reader is within the argument.
- What factual metadata is attached to the argument.

The product should not:

- Explain which side is right.
- Identify the most important exchanges.
- Infer a Justice's intent or ideology from a question.
- Rank speakers, cases, arguments, or moments by importance.
- Add summaries that could become editorial framing.

## 2. Preserve the Source

The transcript is the authority. SCOTUS Chat may reformat, structure, and
annotate factual metadata around the transcript, but it should not replace the
source material with a derivative interpretation.

Design and product decisions should keep the reader close to the original
argument. When the interface adds context, that context should be factual,
limited, and easy to distinguish from the transcript itself.

This principle favors:

- Clear links back to source PDFs or official records.
- Metadata that helps readers orient themselves.
- Transparent handling of speaker identity and roles.
- Careful labels for derived or parsed data.

This principle argues against:

- Copy that implies SCOTUS Chat is the canonical version of the argument.
- AI-generated descriptions presented as authoritative.
- Hidden transformations that affect transcript meaning.
- Decorative excerpts that make one moment feel more important than others.

## 3. Reduce Cognitive Load

Core reading features in SCOTUS Chat should reduce the mental effort required
to follow a long, dense legal conversation.

The interface should externalize details the reader would otherwise have to
hold in working memory: speaker identity, role, side, argument metadata, and
conversation flow. A reader should not need to memorize who each person is or
manually decode every speaker label to keep reading.

Secondary utility features may support access, citation, sharing, or navigation
without directly making the transcript easier to read. Their standard is that
they must not interrupt, distort, or make the reading experience harder.

This principle supports:

- Persistent, repeated speaker attribution.
- Visual distinction between speakers.
- Bench and advocate separation.
- On-demand speaker context.
- Stable navigation through long transcripts.
- Calm density suitable for sustained reading.
- Quiet utilities that help readers return to, cite, or share a specific source
  location without changing the meaning or prominence of that material.

This principle cautions against:

- Hiding speaker identity behind hover-only interactions.
- Relying on color alone to communicate role or side.
- Making readers remember context from earlier on the page.
- Adding promotional, analytical, or decorative content that interrupts reading.
- Turning utility features into engagement mechanics that compete with the
  transcript itself.

## 4. Treat Speakers Equally

The interface should not use design, copy, ordering, color, or metadata depth to
favor one speaker, side, role, or legal position over another.

Equal treatment does not require every speaker to look identical. It does
require that distinctions serve comprehension rather than persuasion. For
example, separating bench and advocates helps readers understand the structure
of oral argument. Making one side visually more prominent because it is more
interesting, sympathetic, or newsworthy would violate this principle.

This principle supports:

- Consistent speaker components.
- Comparable metadata depth where source data allows it.
- Neutral color and typography choices.
- Role labels that describe function rather than value.

This principle argues against:

- Featured quotes chosen for drama or political resonance.
- Visual emphasis that implies a preferred side.
- Speaker bios that vary in editorial depth based on perceived importance.
- Labels that characterize a speaker's argument beyond their procedural role.

## 5. Be Honest About Bias And Boundaries

SCOTUS Chat should not pretend that its creator has no perspective. Instead, it
should use strict product boundaries to limit where perspective can enter.

The product boundary is this: SCOTUS Chat helps readers follow the public
argument; it does not tell readers how to understand or evaluate the argument.

When uncertainty exists, the product should choose restraint. If a piece of
copy, metadata, layout, or feature could reasonably be read as commentary, it
should be revised, labeled more clearly, or left out.

## 6. Make Accessibility Claims Carefully

Accessibility is central to the origin and intent of SCOTUS Chat, but public
claims should match what has been validated.

It is appropriate to say the interface is designed to make oral arguments
clearer and easier to follow. It is also appropriate internally to hypothesize
that the format may help neurodivergent readers, readers with ADHD or AuDHD,
and people who experience working memory overload with traditional transcripts.

Stronger public claims should wait for research with external users.

Until then, the product should:

- Build from the creator's lived accessibility need.
- Use accessibility-informed design decisions.
- Avoid claiming proven outcomes for groups that have not yet been tested.
- Treat future user research as a way to learn, not as a way to validate a
  predetermined marketing claim.

## 7. Prefer Plain Usefulness Over Promotion

SCOTUS Chat should explain itself plainly and let the product demonstrate its
value. The public site should feel like a trustworthy reading tool and archive,
not a punditry product, campaign site, or generic AI demo.

This principle supports copy that is:

- Direct.
- Calm.
- Specific.
- Modest.
- Useful.

This principle argues against copy that is:

- Breathless.
- Promotional.
- Ideological.
- Overconfident.
- Centered on AI rather than reader benefit.

## 8. Design For Re-Orientation

Readers will lose focus, skim, pause, return later, and enter pages from search.
SCOTUS Chat should make it easy to regain orientation without starting over.

A reader should be able to quickly answer:

- What case or argument am I reading?
- Who is speaking now?
- What role does this speaker have?
- Which side or group is this speaker associated with?
- Where am I in the transcript?
- How do I move to another argument or term?

This principle supports persistent metadata, clear navigation, stable visual
patterns, and contextual details that appear when needed.

## 9. Keep The Product Narrow

SCOTUS Chat should stay focused on making oral argument transcripts easier to
follow. Adjacent features should be judged by whether they support that purpose.

Features that clarify source material, speaker identity, roles, argument
structure, or navigation are likely aligned. Features that analyze ideology,
predict outcomes, score persuasion, generate case summaries, or rank moments are
not aligned with the current product purpose.

Some aligned features may not directly improve the act of reading. For example,
sharing a link to a specific utterance could support citation, reference, or
returning to a source location. Such features can fit the product as long as
they remain subordinate to the transcript, avoid editorial framing, and do not
make the reading experience harder.

Narrowness is not a lack of ambition. It is how the product maintains trust.

## Decision Test

When evaluating a product, design, or copy decision, ask:

1. Does this clarify structure without interpreting meaning?
2. Does this preserve trust in the source transcript?
3. If this is a core reading feature, does it reduce cognitive load for the reader?
4. Does this treat speakers and sides equally?
5. Does this avoid making unvalidated accessibility claims?
6. Does this sound useful rather than promotional?
7. Does this help readers orient or re-orient themselves?
8. If this is a secondary utility, does it avoid interrupting or making the
   reading experience harder?
9. Does this fit the narrow purpose of the product?

If the answer to any of these is unclear, the decision needs more scrutiny
before it becomes part of the public product.
