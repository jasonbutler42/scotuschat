---
title: SCOTUS Chat Voice
date: 2026-07-09
status: internal draft
source: POS-002
---

# SCOTUS Chat Voice

This document defines how SCOTUS Chat should sound across public pages,
interface labels, helper text, documentation, and future marketing copy. The
voice should support the product's purpose: helping readers follow Supreme Court
oral arguments without editorial framing or unnecessary cognitive load.

## Voice Summary

SCOTUS Chat should sound plain, careful, calm, and useful.

The voice should feel like a trustworthy reading tool: clear enough for a first
visitor, precise enough for someone using the site seriously, and restrained
enough that it never competes with the transcript.

The product should not sound like a pundit, campaign, legal analyst, AI demo, or
startup pitch.

## Voice Attributes

### Plain

Use ordinary language before legal, technical, or promotional language. The site
can refer to legal concepts when needed, but it should not make readers decode
unnecessary jargon just to understand the product.

Prefer:

- "Read oral arguments as structured conversations."
- "Follow who said what."
- "Browse arguments by term."
- "View the source transcript."

Avoid:

- "Explore jurisprudential discourse."
- "Unlock deep legal intelligence."
- "AI-enhanced constitutional insights."
- "Revolutionizing Supreme Court research."

### Careful

Be precise about what the product does and does not do. Do not overclaim,
generalize beyond the source, or imply analysis where the product provides
structure.

Prefer:

- "Speaker information helps identify who is speaking."
- "Argument roles are shown when available."
- "Public transcripts are reformatted for readability."

Avoid:

- "Understand the case instantly."
- "See what the Justices really think."
- "Discover the key moments."
- "Know which arguments persuaded the Court."

### Calm

Use language that supports sustained reading. Avoid urgency, drama, hype, or
copy that makes legal material feel like breaking news or entertainment.

Prefer:

- "Recent arguments"
- "Browse the archive"
- "Open transcript"
- "Copy link to utterance"

Avoid:

- "Must-read exchange"
- "Explosive moment"
- "The debate everyone is talking about"
- "Don't miss this argument"

### Useful

Copy should help readers act, orient, or understand the interface. If a sentence
mostly advertises the product to itself, it probably does not belong in the UI.

Prefer:

- "Search by case, docket, speaker, or term."
- "Bench speakers appear on the left; advocates appear on the right."
- "Select a speaker to view role and biographic details."

Avoid:

- "A beautiful new way to experience the Court."
- "Built for the future of legal understanding."
- "Your gateway to the Supreme Court."

### Modest

SCOTUS Chat can be confident about its format without claiming to solve every
problem in legal access, civic education, or accessibility.

Prefer:

- "Designed to make oral arguments easier to follow."
- "A clearer way to read public transcripts."
- "Built around speaker identity, roles, and flow."

Avoid:

- "The definitive Supreme Court archive."
- "Legal research, transformed."
- "Making the Court understandable for everyone."
- "The accessibility solution for Supreme Court transcripts."

## Vocabulary Guidance

### Preferred Terms

Use these terms when they accurately describe the product:

- oral argument
- transcript
- public transcript
- source transcript
- structured conversation
- speaker
- utterance
- bench
- advocate
- role
- side
- argument flow
- easier to follow
- clearer reading
- source material
- archive

### Use With Care

These terms may be accurate in some contexts but can create the wrong emphasis:

- accessibility: use publicly only for concrete implemented accessibility
  features or clearly framed design intent; avoid broad outcome claims until
  external research exists.
- AI: use only when explaining the internal parsing pipeline or derived-data
  limitations; do not make AI the public value proposition.
- analysis: avoid unless describing what SCOTUS Chat does not provide.
- summary: avoid for public product features unless a future feature is
  deliberately approved against the principles.
- research: acceptable for user activity, but avoid implying SCOTUS Chat is a
  complete legal research platform.

### Avoided Terms

Avoid terms that imply commentary, persuasion, hype, or hidden insight:

- explosive
- revealing
- must-read
- winning argument
- losing argument
- key moment
- most important
- what the Justices really think
- sentiment
- ideology tracking
- persuasion score
- AI-powered insight
- deep analysis
- unlock
- revolutionize

## Copy Rules

### Lead With Reader Benefit, Not Technology

The public value is not that the pipeline uses AI. The public value is that the
reader can follow the transcript with less effort.

Prefer:

> Public oral argument transcripts, presented as structured conversations.

Avoid:

> AI-powered transcript analysis for Supreme Court arguments.

### Describe The Format Without Overselling It

The chat format is a reading aid, not a claim that the Court is casual,
simplified, or conversational in substance.

Prefer:

> Read the argument in a chat-style layout that keeps speaker identity and role
> visible.

Avoid:

> Experience Supreme Court arguments like a group chat.

### Name Limits Clearly

When a feature provides derived or parsed information, copy should leave room
for uncertainty and correction.

Prefer:

> Speaker role shown when available.

Avoid:

> Complete speaker profile.

### Keep Calls To Action Functional

Calls to action should describe the action, not manufacture urgency.

Prefer:

- Open argument
- Read transcript
- Browse arguments
- View source
- Copy link
- Search archive

Avoid:

- Start exploring now
- Discover the truth
- Dive into the drama
- Unlock this case

## Example Messaging

### Short Product Description

SCOTUS Chat presents Supreme Court oral arguments as structured conversations,
so readers can follow who said what without added commentary or political
framing.

### Alternate Short Description

A clearer way to read public Supreme Court oral argument transcripts, with
speaker identity, roles, and argument flow easier to track.

### Homepage Support Copy

Browse public Supreme Court oral argument transcripts in a chat-style layout
that keeps speakers, roles, and sides visible as you read.

### About Copy

SCOTUS Chat is an access-oriented reading interface for Supreme Court oral
argument transcripts. It reformats public transcripts into structured
conversations, helping readers follow speaker identity, turn-taking, and
argument flow without adding summaries, analysis, or political commentary.

### What This Is / Is Not

SCOTUS Chat is:

- A clearer interface for public oral argument transcripts.
- A tool for following who said what.
- A source-oriented archive organized around arguments, speakers, and terms.

SCOTUS Chat is not:

- A legal analysis product.
- A political commentary site.
- A case summary service.
- A ranking of important moments or persuasive arguments.

## Interface Copy Examples

### Search Placeholder

Preferred:

> Search cases, dockets, speakers, or terms

Avoid:

> Search the Court's most important arguments

### Empty State

Preferred:

> No arguments match this search.

Avoid:

> Nothing interesting found.

### Share Utility

Preferred:

> Copy link to this utterance

Avoid:

> Share this key moment

### Source Link

Preferred:

> View source transcript

Avoid:

> View original evidence

### Speaker Context

Preferred:

> Speaker details

Avoid:

> About this person's role in the case

## Tone By Surface

### Homepage

The homepage should be concise, orienting, and calm. It should quickly explain
what the site is, then help readers search or browse.

### Argument Page

The argument page should mostly get out of the way. Copy should clarify the
interface only where needed, especially around speaker roles, source links, and
navigation.

### Archive And Browse Pages

Archive copy should be factual and scannable. Avoid framing any case or term as
more important unless the ordering is purely chronological, alphabetical, or
otherwise explicit.

### Admin Interface

Admin copy can be more operational and direct. It should prioritize clarity,
state, and next action over public-facing polish.

## Final Test

Before publishing copy, ask:

1. Does this help the reader understand or act?
2. Is it clear what is source material versus product framing?
3. Does it avoid legal, political, or ideological interpretation?
4. Does it avoid making AI the main story?
5. Does it avoid validated-sounding accessibility claims we have not tested?
6. Would this copy still feel appropriate next to a politically charged case?

If the copy feels clever, dramatic, or promotional, simplify it.