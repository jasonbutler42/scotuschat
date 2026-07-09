---
title: SCOTUS Chat Foundation
date: 2026-07-09
status: internal draft
---

# SCOTUS Chat Foundation

## Purpose

SCOTUS Chat exists because Supreme Court oral argument transcripts are public,
important, and harder to read than they need to be.

The project presents oral arguments as structured conversations so readers can
follow speaker identity, turn-taking, and conversational flow without constantly
decoding dense transcript formatting. It is built first to solve the creator's
own accessibility and comprehension needs, with the hope that the same format
helps others who experience similar friction when reading legal transcripts.

## Origin

The project began with a concrete reading problem: the creator wanted to read
the transcript for *Obergefell v. Hodges*, but the traditional transcript format
made it difficult to track who was speaking and how the argument was unfolding.
Past prototypes showed that a chat-style presentation made the material easier
to follow.

That origin matters. SCOTUS Chat is not primarily a legal analysis product, a
news product, or a civic education platform. It is an access-oriented reading
interface for public legal material.

## Core Thesis

SCOTUS Chat reduces the cognitive overhead of reading Supreme Court oral
argument transcripts.

It does this by clarifying structure, not meaning. The interface may help
readers understand who is speaking, which role they hold, which side they are
associated with, and how the exchange moves between the bench and advocates. It
must not tell readers what to think about the argument.

## Primary Audience

The primary audience is the creator: someone who wants to read Supreme Court
oral arguments but finds traditional transcript formatting cognitively taxing.

The broader audience hypothesis is that SCOTUS Chat may also help people who
want or need a clearer way to follow oral arguments, especially readers for whom
traditional transcript formatting creates cognitive friction. This may include
neurodivergent readers, students, researchers, journalists, educators, and
curious members of the public.

This broader accessibility claim should remain an internal hypothesis until it
has been tested with people outside the creator's own use case.

## Reader Burdens The Product Should Reduce

SCOTUS Chat should reduce the effort required to:

- Track who is speaking.
- Remember speaker roles and identities.
- Distinguish bench speakers from advocates.
- Follow the back-and-forth flow of an oral argument.
- Re-enter context after attention shifts.
- Move through long, dense legal material without losing orientation.

These burdens should be reduced through interface structure and source-linked
context, not through interpretation or summarization.

## Current Product Responses

The current product addresses these burdens through:

- A two-sided conversation layout that separates bench and advocates.
- Speaker names and avatars attached to individual utterances.
- Visual distinction between speakers beyond name text alone.
- Speaker popovers that provide biographic and case-specific context on demand.
- Argument-level metadata that orients readers before and during reading.

These choices should be understood as accessibility and orientation decisions,
not decorative choices.

## Neutrality Principle

SCOTUS Chat should be neutral in presentation even though no creator is free of
personal perspective or bias.

The neutrality standard is practical and product-specific: the site should
present source material, speaker identity, roles, and procedural context without
editorial framing, political commentary, ranking, sentiment, or argumentative
emphasis.

The product should be transparent about what it does:

- It restructures public oral argument transcripts for readability.
- It identifies speakers and roles.
- It provides factual context that helps readers follow the conversation.

The product should also be clear about what it does not do:

- It does not summarize the legal arguments.
- It does not explain which side is right.
- It does not identify the most important exchanges.
- It does not infer intent, tone, ideology, or persuasion.
- It does not use layout, color, or copy to favor one speaker or side.

## Accessibility Position

Accessibility is part of the internal truth of SCOTUS Chat, but public claims
should be made carefully.

For now, it is appropriate to describe the public product in terms of clarity,
readability, orientation, and lower cognitive friction. Stronger claims about
serving neurodivergent readers, reducing working memory overload, or improving
accessibility for ADHD or AuDHD users should wait until the product has been
tested with people who share those needs.

A future research mini-project should test whether the layout reduces working
memory burden and improves transcript comprehension for readers who struggle
with traditional transcript formats.

## Public Messaging Boundaries

Good public messaging should sound plain, careful, and useful:

- "Read Supreme Court oral arguments as structured conversations."
- "Follow who said what, without losing the thread."
- "Public transcripts, reformatted for clarity."
- "Speaker identity, roles, and argument flow made easier to track."

Messaging should avoid claims that imply editorial judgment or legal analysis:

- "The most important moments from the Court."
- "AI-powered analysis of Supreme Court arguments."
- "Understand what the Justices really think."
- "See who won the argument."
- "Track ideology, sentiment, or persuasion."

## Design Implications

Homepage and public-page design should prioritize immediate orientation over
promotion. The site should feel like a trustworthy reading tool and archive, not
a punditry product or a generic AI demo.

Design decisions should support:

- Fast access to arguments.
- Clear distinction between cases, arguments, terms, speakers, and roles.
- Low-friction browsing and search.
- Calm visual density appropriate for long reading sessions.
- Equal treatment of all speakers and sides.
- Minimal copy that explains the format without overselling the product.

The homepage should not need a dramatic featured-case editorial hero to justify
the product. The strongest promise is simpler: this is the public transcript,
presented so the conversation is easier to follow.

## Working Statement

SCOTUS Chat presents Supreme Court oral arguments as structured conversations,
making it easier to follow who said what without adding commentary,
interpretation, or political framing.
